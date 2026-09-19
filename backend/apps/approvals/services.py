import re

from django.conf import settings
from django.db import transaction

from apps.employees.models import Employee
from apps.leaves.models import LeaveApplication

from .models import ApprovalAction, ApproverAssignment, EmployeeApprover

HOD_DESIGNATION_RE = re.compile(r'\bhod\b', re.IGNORECASE)
INCHARGE_RE = re.compile(r'\bi\s*/\s*c\b', re.IGNORECASE)
REGISTRAR_EMAIL = 'registrar@gcuniversity.ac.in'


class ApprovalError(Exception):
    def __init__(self, message, status=400, errors=None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.errors = errors or {}


def designation_looks_like_hod(designation):
    """True when designation contains HOD as a word (case-insensitive).

    Matches 'HOD', 'Professor & HOD', 'Associate Professor & HOD',
    'HOD, Department of …'.
    """
    return bool(HOD_DESIGNATION_RE.search(designation or ''))


def looks_like_hod(employee):
    """True when designation contains HOD as a word (case-insensitive).

    Matches 'HOD', 'Professor & HOD', 'Associate Professor & HOD',
    'HOD, Department of …'. Does not require an ApproverAssignment.
    """
    if employee is None:
        return False
    return designation_looks_like_hod(employee.designation)


def applicant_is_hod(employee):
    """True when this applicant has a single approver: the VC.

    Designation containing HOD as a word is sufficient. An ApproverAssignment
    with role HOD is not required; assignment is only a fallback for people
    who hold the role without HOD in their title.
    """
    if employee is None:
        return False
    if looks_like_hod(employee):
        return True
    return ApproverAssignment.objects.filter(
        employee=employee,
        role=ApproverAssignment.Role.HOD,
    ).exists()


def hod_sort_key(employee):
    designation = employee.designation or ''
    incharge = 0 if not INCHARGE_RE.search(designation) else 1
    return (incharge, employee.emp_id)


def get_vc():
    assignment = (
        ApproverAssignment.objects.filter(role=ApproverAssignment.Role.VC)
        .select_related('employee')
        .first()
    )
    if assignment and assignment.employee.is_active:
        return assignment.employee
    return None


def find_hod(employee):
    queryset = ApproverAssignment.objects.filter(
        role=ApproverAssignment.Role.HOD,
        employee__status=Employee.Status.ACTIVE,
    ).select_related('employee')

    sub = (employee.sub_department or '').strip()
    dept = (employee.department or '').strip()

    if sub:
        match = queryset.filter(sub_department__iexact=sub).order_by('employee__emp_id').first()
        if match:
            return match.employee

    if dept:
        match = queryset.filter(
            department__iexact=dept, sub_department=''
        ).order_by('employee__emp_id').first()
        if match:
            return match.employee
        match = queryset.filter(department__iexact=dept).order_by(
            'sub_department', 'employee__emp_id'
        ).first()
        if match:
            return match.employee

    return None


def roles_for_employee(employee):
    empty = {
        'is_hod': False,
        'is_vc': False,
        'is_approver': False,
        'roles': [],
        'inbox_count': 0,
    }
    if employee is None:
        return empty

    roles = list(
        ApproverAssignment.objects.filter(employee=employee)
        .values_list('role', flat=True)
        .distinct()
    )
    if EmployeeApprover.objects.filter(approver_1=employee).exists():
        if ApproverAssignment.Role.APPROVER_1 not in roles:
            roles.append(ApproverAssignment.Role.APPROVER_1)
    if EmployeeApprover.objects.filter(approver_2=employee).exists():
        if ApproverAssignment.Role.APPROVER_2 not in roles:
            roles.append(ApproverAssignment.Role.APPROVER_2)
    inbox_count = LeaveApplication.objects.filter(
        status=LeaveApplication.Status.PENDING,
        waiting_on=employee,
    ).count()
    return {
        'is_hod': ApproverAssignment.Role.HOD in roles,
        'is_vc': ApproverAssignment.Role.VC in roles,
        'is_approver': any(
            role in roles for role in ApproverAssignment.STAFF_ROLES
        ),
        'roles': roles,
        'inbox_count': inbox_count,
    }


def inbox_queryset(employee):
    return (
        LeaveApplication.objects.filter(
            status=LeaveApplication.Status.PENDING,
            waiting_on=employee,
        )
        .select_related('employee', 'leave_type', 'waiting_on')
        .prefetch_related('approval_actions__actor')
    )


def _set_waiting(application, step, waiting_on, notify=True):
    application.current_step = step
    application.waiting_on = waiting_on
    application.save(
        update_fields=['chain_type', 'current_step', 'waiting_on', 'status', 'updated_at']
    )
    if notify:
        _notify_waiting(application)
    return application


def _clear_waiting(application, status=None, notify=True):
    application.current_step = ''
    application.waiting_on = None
    update_fields = ['chain_type', 'current_step', 'waiting_on', 'updated_at']
    if status is not None:
        application.status = status
        update_fields.append('status')
    application.save(update_fields=update_fields)
    if notify and status in (
        LeaveApplication.Status.APPROVED,
        LeaveApplication.Status.REJECTED,
    ):
        _notify_applicant(application)
    return application


def _notify_waiting(application):
    from apps.notifications.services import notify_employee

    if not application.waiting_on_id:
        return
    notify_employee(
        application.waiting_on,
        'Leave request awaiting your decision',
        f'{application.employee.name} applied for {application.leave_type.name}.',
        '/approvals',
    )


def _notify_applicant(application):
    from apps.notifications.services import notify_employee

    status = application.get_status_display()
    notify_employee(
        application.employee,
        f'Leave {status.lower()}',
        f'Your {application.leave_type.name} request was {status.lower()}.',
        '/leaves',
    )


def _personal_approver_mapping(employee):
    return (
        EmployeeApprover.objects.filter(employee=employee)
        .select_related('approver_1', 'approver_2')
        .first()
    )


def _usable_staff_approver(applicant, approver):
    if approver is None or not approver.is_active:
        return None
    if approver.id == applicant.id:
        return None
    vc = get_vc()
    if vc and approver.id == vc.id:
        return None
    return approver


def _find_staff_approver(employee, role):
    """
    Pick the person who holds `role` for the applicant's department.

    Used when the applicant has no personal EmployeeApprover row. If older
    rows still share a department, prefer that match, lowest emp_id, skipping
    the applicant and the VC.
    """
    vc = get_vc()
    skip_ids = {employee.id}
    if vc:
        skip_ids.add(vc.id)

    queryset = (
        ApproverAssignment.objects.filter(
            role=role,
            employee__status=Employee.Status.ACTIVE,
        )
        .exclude(employee_id__in=skip_ids)
        .select_related('employee')
        .order_by('employee__emp_id')
    )
    dept = (employee.department or '').strip()
    if dept:
        match = queryset.filter(department__iexact=dept).first()
        if match:
            return match.employee
    return None


def find_approver1(employee):
    mapping = _personal_approver_mapping(employee)
    if mapping is not None:
        return _usable_staff_approver(employee, mapping.approver_1)
    return _find_staff_approver(employee, ApproverAssignment.Role.APPROVER_1)


def find_approver2(employee):
    mapping = _personal_approver_mapping(employee)
    if mapping is not None:
        return _usable_staff_approver(employee, mapping.approver_2)
    return _find_staff_approver(employee, ApproverAssignment.Role.APPROVER_2)


def _chain_for_employee(employee):
    if employee.designation_type == Employee.DesignationType.FACULTY:
        return LeaveApplication.ChainType.FACULTY
    return LeaveApplication.ChainType.STAFF


def _route_to_vc_only(application, notify=True):
    """HOD (or VC) applicants skip A1, A2, and department HOD."""
    employee = application.employee
    application.chain_type = _chain_for_employee(employee)
    vc = get_vc()
    if vc and employee.id == vc.id:
        return _clear_waiting(application, status=LeaveApplication.Status.APPROVED, notify=notify)
    if vc:
        return _set_waiting(application, LeaveApplication.Step.VC, vc, notify=notify)
    return _clear_waiting(application, notify=False)


def _route_faculty(application, notify=True):
    employee = application.employee
    application.chain_type = LeaveApplication.ChainType.FACULTY
    vc = get_vc()

    if vc and employee.id == vc.id:
        return _clear_waiting(application, status=LeaveApplication.Status.APPROVED, notify=notify)

    if applicant_is_hod(employee):
        return _route_to_vc_only(application, notify=notify)

    hod = find_hod(employee)
    if hod and hod.id not in {employee.id, getattr(vc, 'id', None)}:
        return _set_waiting(application, LeaveApplication.Step.HOD, hod, notify=notify)

    if vc:
        return _set_waiting(application, LeaveApplication.Step.VC, vc, notify=notify)

    return _clear_waiting(application, notify=False)


def _forward_to_vc(application, notify=True):
    vc = get_vc()
    if vc is None:
        raise ApprovalError('Vice-Chancellor is not configured. Contact the administrator.')
    if vc.id == application.employee_id:
        return _clear_waiting(application, status=LeaveApplication.Status.APPROVED, notify=notify)
    return _set_waiting(application, LeaveApplication.Step.VC, vc, notify=notify)


def _route_staff(application, notify=True):
    employee = application.employee
    application.chain_type = LeaveApplication.ChainType.STAFF
    vc = get_vc()

    if vc and employee.id == vc.id:
        return _clear_waiting(application, status=LeaveApplication.Status.APPROVED, notify=notify)

    # HOD in designation (e.g. "Professor & HOD") must skip personal/dept A1 and A2.
    if applicant_is_hod(employee):
        return _route_to_vc_only(application, notify=notify)

    approver1 = find_approver1(employee)
    approver2 = find_approver2(employee)

    if approver1:
        return _set_waiting(
            application, LeaveApplication.Step.APPROVER_1, approver1, notify=notify
        )

    if approver2:
        return _set_waiting(
            application, LeaveApplication.Step.APPROVER_2, approver2, notify=notify
        )

    if vc:
        return _set_waiting(application, LeaveApplication.Step.VC, vc, notify=notify)

    return _clear_waiting(application, notify=False)


def route_new_application(application, notify=True):
    employee = application.employee
    vc = get_vc()
    if vc and employee.id == vc.id:
        return _route_to_vc_only(application, notify=notify)
    # Check HOD in designation before staff A1/A2 or faculty department HOD.
    if applicant_is_hod(employee):
        return _route_to_vc_only(application, notify=notify)
    if employee.designation_type == Employee.DesignationType.FACULTY:
        return _route_faculty(application, notify=notify)
    return _route_staff(application, notify=notify)


def route_pending_applications(notify=False):
    routed = 0
    queryset = LeaveApplication.objects.filter(
        status=LeaveApplication.Status.PENDING,
        waiting_on__isnull=True,
        current_step='',
    ).select_related('employee')
    for application in queryset:
        route_new_application(application, notify=notify)
        routed += 1

    vc = get_vc()
    misrouted = (
        LeaveApplication.objects.filter(
            status=LeaveApplication.Status.PENDING,
            current_step__in=(
                LeaveApplication.Step.APPROVER_1,
                LeaveApplication.Step.APPROVER_2,
                LeaveApplication.Step.HOD,
            ),
        )
        .select_related('employee')
    )
    for application in misrouted:
        employee = application.employee
        if vc and employee.id == vc.id:
            continue
        if not applicant_is_hod(employee):
            continue
        if vc and application.waiting_on_id == vc.id:
            continue
        route_new_application(application, notify=notify)
        routed += 1
    return routed


@transaction.atomic
def decide_application(application, actor, decision, remarks=''):
    application = (
        LeaveApplication.objects.select_for_update()
        .select_related('employee', 'leave_type', 'waiting_on')
        .get(pk=application.pk)
    )
    decision = (decision or '').strip().upper()
    remarks = (remarks or '').strip()

    if application.status != LeaveApplication.Status.PENDING:
        raise ApprovalError('This application is no longer pending.')
    if application.waiting_on_id != actor.id:
        raise ApprovalError('This application is not waiting on you.', status=403)
    if actor.id == application.employee_id:
        raise ApprovalError('You cannot decide your own leave application.', status=403)
    if decision not in ApprovalAction.Decision.values:
        raise ApprovalError(
            'Decision must be APPROVED or REJECTED.',
            errors={'decision': ['Decision must be APPROVED or REJECTED.']},
        )
    if decision == ApprovalAction.Decision.REJECTED and not remarks:
        raise ApprovalError(
            'Remarks are required when rejecting.',
            errors={'remarks': ['Please give a reason for rejection.']},
        )

    step = application.current_step
    if step not in ApprovalAction.Step.values:
        raise ApprovalError('This application has no approval step to complete.')

    ApprovalAction.objects.create(
        application=application,
        step=step,
        actor=actor,
        decision=decision,
        remarks=remarks,
    )

    if decision == ApprovalAction.Decision.REJECTED:
        return _clear_waiting(application, status=LeaveApplication.Status.REJECTED)

    if step == LeaveApplication.Step.HOD:
        return _forward_to_vc(application)

    if step == LeaveApplication.Step.APPROVER_1:
        vc = get_vc()
        skip_ids = {application.employee_id, actor.id}
        if vc:
            skip_ids.add(vc.id)
        approver2 = find_approver2(application.employee)
        if approver2 and approver2.id not in skip_ids:
            return _set_waiting(application, LeaveApplication.Step.APPROVER_2, approver2)
        return _forward_to_vc(application)

    if step == LeaveApplication.Step.APPROVER_2:
        return _forward_to_vc(application)

    if step == LeaveApplication.Step.VC:
        return _clear_waiting(application, status=LeaveApplication.Status.APPROVED)

    raise ApprovalError('This application has no approval step to complete.')


def assign_vc(employee):
    assignment, _ = assign_approver(ApproverAssignment.Role.VC, employee)
    return assignment


def assign_approver(role, employee, department='', sub_department=''):
    if employee is None or not employee.is_active:
        raise ApprovalError('Approver must be an active employee.', status=404)

    department = (department or '').strip()
    sub_department = (sub_department or '').strip()

    if role == ApproverAssignment.Role.VC:
        return ApproverAssignment.objects.update_or_create(
            role=role,
            defaults={'employee': employee, 'department': '', 'sub_department': ''},
        )

    if role in ApproverAssignment.STAFF_ROLES:
        if not department:
            department = (employee.department or '').strip()
        if not department:
            raise ApprovalError(
                'Department is required for staff approvers.',
                errors={'department': ['Department is required for this role.']},
            )
        return ApproverAssignment.objects.update_or_create(
            role=role,
            employee=employee,
            department=department,
            defaults={'sub_department': ''},
        )

    if role == ApproverAssignment.Role.HOD:
        if not (department or sub_department):
            raise ApprovalError(
                'Department or sub-department is required for an HOD.',
                errors={'department': ['Department or sub-department is required for an HOD.']},
            )
        return ApproverAssignment.objects.update_or_create(
            role=role,
            department=department,
            sub_department=sub_department,
            defaults={'employee': employee},
        )

    raise ApprovalError('Unknown approval role.')


@transaction.atomic
def clear_employee_staff_approvers(mapping, *, clear_approver_1=False, clear_approver_2=False):
    """
    Clear one or both personal approvers for a single employee.
    If both slots are empty afterwards, delete the EmployeeApprover row.
    """
    if mapping is None:
        raise ApprovalError('Employee approver mapping not found.', status=404)
    if not clear_approver_1 and not clear_approver_2:
        raise ApprovalError(
            'Specify Approver 1, Approver 2, or both to remove.',
            errors={'non_field_errors': ['Specify which approver to remove.']},
        )
    if clear_approver_1:
        mapping.approver_1 = None
    if clear_approver_2:
        mapping.approver_2 = None
    if mapping.approver_1_id is None and mapping.approver_2_id is None:
        mapping.delete()
        return None
    mapping.save(update_fields=['approver_1', 'approver_2', 'updated_at'])
    return mapping


@transaction.atomic
def set_employee_staff_approvers(subjects, approver_1, approver_2):
    subjects = list(subjects or [])
    if not subjects:
        raise ApprovalError(
            'Select at least one employee.',
            errors={'emp_ids': ['Select at least one employee.']},
        )
    if approver_1 is None or not approver_1.is_active:
        raise ApprovalError('Approver 1 must be an active employee.', status=404)
    if approver_2 is not None:
        if not approver_2.is_active:
            raise ApprovalError('Approver 2 must be an active employee.', status=404)
        if approver_1.id == approver_2.id:
            raise ApprovalError(
                'Approver 1 and Approver 2 must be different people.',
                errors={'approver2_emp_id': ['Choose a different employee for Approver 2.']},
            )

    seen = set()
    unique_subjects = []
    for employee in subjects:
        if employee.id in seen:
            continue
        seen.add(employee.id)
        if not employee.is_active:
            raise ApprovalError(
                'No active employee found for that ID.',
                errors={'emp_ids': [employee.emp_id]},
                status=404,
            )
        if looks_like_hod(employee):
            continue
        unique_subjects.append(employee)
    if not unique_subjects:
        return []

    existing = {
        row.employee_id: row
        for row in EmployeeApprover.objects.filter(employee__in=unique_subjects)
    }
    to_create = []
    to_update = []
    for employee in unique_subjects:
        row = existing.get(employee.id)
        if row is None:
            to_create.append(
                EmployeeApprover(
                    employee=employee,
                    approver_1=approver_1,
                    approver_2=approver_2,
                )
            )
            continue
        row.approver_1 = approver_1
        row.approver_2 = approver_2
        to_update.append(row)
    if to_create:
        EmployeeApprover.objects.bulk_create(to_create)
    if to_update:
        EmployeeApprover.objects.bulk_update(to_update, ['approver_1', 'approver_2'])
    return list(
        EmployeeApprover.objects.select_related(
            'employee', 'approver_1', 'approver_2'
        ).filter(employee__in=unique_subjects)
    )


@transaction.atomic
def set_department_staff_approvers(department, approver_1, approver_2):
    department = (department or '').strip()
    if not department:
        raise ApprovalError(
            'Department is required.',
            errors={'department': ['Department is required.']},
        )
    if approver_1 is None or approver_2 is None or not approver_1.is_active or not approver_2.is_active:
        raise ApprovalError('Approver 1 and Approver 2 must be active employees.', status=404)
    if approver_1.id == approver_2.id:
        raise ApprovalError(
            'Approver 1 and Approver 2 must be different people.',
            errors={'approver_2_emp_id': ['Choose a different employee for Approver 2.']},
        )

    ApproverAssignment.objects.filter(
        role__in=ApproverAssignment.STAFF_ROLES,
        department__iexact=department,
    ).delete()

    assignment_1, _ = assign_approver(
        ApproverAssignment.Role.APPROVER_1,
        approver_1,
        department=department,
    )
    assignment_2, _ = assign_approver(
        ApproverAssignment.Role.APPROVER_2,
        approver_2,
        department=department,
    )
    return {
        'approver_1': assignment_1,
        'approver_2': assignment_2,
    }


def sync_hod_assignments():
    created = 0
    updated = 0
    skipped = []

    candidates = [
        employee
        for employee in Employee.objects.filter(status=Employee.Status.ACTIVE)
        if looks_like_hod(employee)
    ]
    grouped = {}
    for employee in candidates:
        key = (
            (employee.department or '').strip(),
            (employee.sub_department or '').strip(),
        )
        grouped.setdefault(key, []).append(employee)

    for (department, sub_department), employees in grouped.items():
        chosen = sorted(employees, key=hod_sort_key)[0]
        for extra in employees:
            if extra.id != chosen.id:
                skipped.append(
                    f'{extra.emp_id} ({extra.name}) skipped for '
                    f'{sub_department or department or "unit"}; using {chosen.emp_id}.'
                )
        _, was_created = ApproverAssignment.objects.update_or_create(
            role=ApproverAssignment.Role.HOD,
            department=department,
            sub_department=sub_department,
            defaults={'employee': chosen},
        )
        if was_created:
            created += 1
        else:
            updated += 1

    keep = set(grouped.keys())
    removed = 0
    for assignment in ApproverAssignment.objects.filter(role=ApproverAssignment.Role.HOD):
        key = (assignment.department, assignment.sub_department)
        if key not in keep:
            assignment.delete()
            removed += 1

    return {
        'created': created,
        'updated': updated,
        'removed': removed,
        'skipped': skipped,
        'hod_count': ApproverAssignment.objects.filter(role=ApproverAssignment.Role.HOD).count(),
    }


def resolve_vc_employee(emp_id=None):
    emp_id = (emp_id or getattr(settings, 'VC_EMP_ID', '') or '').strip()
    if emp_id:
        try:
            return Employee.objects.get(emp_id__iexact=emp_id, status=Employee.Status.ACTIVE)
        except Employee.DoesNotExist:
            raise ApprovalError(f'No active employee found for VC_EMP_ID={emp_id}.')

    registrar = Employee.objects.filter(
        email__iexact=REGISTRAR_EMAIL,
        status=Employee.Status.ACTIVE,
    ).first()
    if registrar:
        return registrar
    return None


SENIOR_STAFF_RE = re.compile(
    r'registrar|superintendent|section officer|deputy registrar|'
    r'assistant registrar|office superintendent|administration',
    re.I,
)


def sync_approver1_assignments():
    vc = get_vc()
    departments = [
        (row['department'] or '').strip()
        for row in Employee.objects.filter(
            status=Employee.Status.ACTIVE,
            designation_type=Employee.DesignationType.STAFF,
        )
        .exclude(department='')
        .order_by('department')
        .values('department')
        .distinct()
    ]
    created = 0
    updated = 0
    for department in departments:
        if not department:
            continue
        existing = ApproverAssignment.objects.filter(
            role=ApproverAssignment.Role.APPROVER_1,
            department__iexact=department,
        )
        if existing.exists():
            continue
        hod = (
            ApproverAssignment.objects.filter(
                role=ApproverAssignment.Role.HOD,
                department__iexact=department,
            )
            .select_related('employee')
            .first()
        )
        chosen = None
        if hod and hod.employee.is_active and (vc is None or hod.employee_id != vc.id):
            chosen = hod.employee
        if chosen is None:
            pool = list(
                Employee.objects.filter(
                    status=Employee.Status.ACTIVE,
                    designation_type=Employee.DesignationType.STAFF,
                    department__iexact=department,
                )
            )
            if vc:
                pool = [emp for emp in pool if emp.id != vc.id]
            ranked = sorted(
                pool,
                key=lambda emp: (
                    0 if SENIOR_STAFF_RE.search(emp.designation or '') else 1,
                    emp.emp_id,
                ),
            )
            chosen = ranked[0] if ranked else None
        if chosen is None:
            continue
        _, was_created = assign_approver(
            ApproverAssignment.Role.APPROVER_1,
            chosen,
            department=department,
        )
        if was_created:
            created += 1
        else:
            updated += 1

    return {
        'created': created,
        'updated': updated,
        'removed': 0,
        'approver_count': ApproverAssignment.objects.filter(
            role=ApproverAssignment.Role.APPROVER_1
        ).count(),
    }


def grant_admin(employee):
    from apps.accounts.services import provision_account

    account = provision_account(employee)
    account.is_admin = True
    account.save(update_fields=['is_admin', 'updated_at'])
    user = account.user
    if not user.is_staff:
        user.is_staff = True
        user.save(update_fields=['is_staff'])
    return account


def approver_dashboard(employee):
    from datetime import timedelta

    from django.db.models import Count
    from django.utils import timezone

    inbox = inbox_queryset(employee)
    since = timezone.now() - timedelta(days=30)
    actions = ApprovalAction.objects.filter(actor=employee, created_at__gte=since)
    by_type = (
        inbox.values('leave_type__code', 'leave_type__name')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    return {
        'pending': inbox.count(),
        'decided_last_30_days': actions.count(),
        'approved_last_30_days': actions.filter(decision=ApprovalAction.Decision.APPROVED).count(),
        'rejected_last_30_days': actions.filter(decision=ApprovalAction.Decision.REJECTED).count(),
        'inbox_by_type': [
            {
                'code': row['leave_type__code'],
                'name': row['leave_type__name'],
                'count': row['count'],
            }
            for row in by_type
        ],
    }
