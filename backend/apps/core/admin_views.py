from datetime import datetime
from decimal import Decimal
from io import BytesIO

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Prefetch, Q, Sum
from django.db.models.deletion import ProtectedError
from django.db.models.functions import Lower
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from openpyxl import Workbook
from rest_framework import serializers
from rest_framework.generics import ListAPIView, ListCreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.accounts.models import Account
from apps.accounts.permissions import (
    IsOperatorOrAdmin,
    IsSystemAdmin,
    PasswordChangeNotRequired,
)
from apps.accounts.services import (
    ADMIN_ACCOUNT_Q,
    AccessError,
    apply_account_access,
    provision_account,
)
from apps.approvals.models import ApprovalAction, ApproverAssignment, EmployeeApprover
from apps.approvals.pagination import ApprovalPagination
from apps.approvals.serializers import ApproverAssignmentSerializer, EmployeeApproverSerializer
from apps.approvals.services import (
    ApprovalError,
    assign_approver,
    clear_employee_staff_approvers,
    looks_like_hod,
    set_employee_staff_approvers,
)
from apps.core.responses import fail, ok
from apps.employees.models import Employee
from apps.employees.pagination import EmployeePagination
from apps.employees.serializers import DIRECTORY_FIELDS, EmployeeBriefSerializer, EmployeeDirectorySerializer
from apps.employees.views import (
    apply_optional_blank_filter,
    employee_unit_from_request,
    linked_employee,
    truthy_query_flag,
)
from apps.leaves.models import LeaveApplication, LeaveCredit, LeaveType
from apps.leaves.services import (
    LeaveError,
    credit_leave_days,
    leave_balances,
    sanction_approved_leave,
)

UNSAFE_EMPLOYEE_DELETE = (
    'Cannot delete: this employee has a login account / leave records. Set Inactive instead.'
)


OPERATOR_PERMS = [IsAuthenticated, PasswordChangeNotRequired, IsOperatorOrAdmin]
SYSTEM_ADMIN_PERMS = [IsAuthenticated, PasswordChangeNotRequired, IsSystemAdmin]


class AdminLeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = (
            'id', 'name', 'code', 'description', 'max_days_per_year',
            'applicable_to', 'requires_document', 'is_active', 'sort_order',
        )


class AdminApproverWriteSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=ApproverAssignment.Role.choices)
    emp_id = serializers.CharField(max_length=32)
    department = serializers.CharField(max_length=150, allow_blank=True, required=False)
    sub_department = serializers.CharField(max_length=150, allow_blank=True, required=False)

    def validate(self, attrs):
        role = attrs['role']
        department = (attrs.get('department') or '').strip()
        sub_department = (attrs.get('sub_department') or '').strip()
        if role == ApproverAssignment.Role.VC:
            department = ''
            sub_department = ''
        elif role in ApproverAssignment.STAFF_ROLES:
            sub_department = ''
        elif role == ApproverAssignment.Role.HOD and not (department or sub_department):
            raise serializers.ValidationError(
                {'department': ['Department or sub-department is required for an HOD.']}
            )
        attrs['department'] = department
        attrs['sub_department'] = sub_department
        return attrs


class AdminEmployeeApproverWriteSerializer(serializers.Serializer):
    emp_ids = serializers.ListField(
        child=serializers.CharField(max_length=32),
        allow_empty=False,
        max_length=500,
    )
    approver1_emp_id = serializers.CharField(max_length=32)
    approver2_emp_id = serializers.CharField(max_length=32, required=False, allow_blank=True)

    def to_internal_value(self, data):
        if hasattr(data, 'copy'):
            incoming = data.copy()
        else:
            incoming = dict(data)
        raw = None
        if hasattr(data, 'getlist'):
            listed = [value for value in data.getlist('emp_ids') if value not in (None, '')]
            if listed:
                raw = listed
        if raw is None:
            raw = incoming.get('emp_ids') if hasattr(incoming, 'get') else None
        emp_ids = []
        if isinstance(raw, str):
            emp_ids = [
                part.strip()
                for part in raw.replace(';', ',').split(',')
                if part.strip()
            ]
        elif isinstance(raw, (list, tuple)):
            for item in raw:
                if isinstance(item, str) and (',' in item or ';' in item):
                    emp_ids.extend(
                        part.strip()
                        for part in item.replace(';', ',').split(',')
                        if part.strip()
                    )
                elif item not in (None, ''):
                    emp_ids.append(item)
        elif raw not in (None, ''):
            emp_ids = [raw]
        incoming['emp_ids'] = emp_ids
        return super().to_internal_value(incoming)

    def validate(self, attrs):
        seen = set()
        emp_ids = []
        for raw in attrs.get('emp_ids') or []:
            emp_id = (raw or '').strip()
            if not emp_id:
                continue
            key = emp_id.lower()
            if key in seen:
                continue
            seen.add(key)
            emp_ids.append(emp_id)
        if not emp_ids:
            raise serializers.ValidationError(
                {'emp_ids': ['Select at least one employee.']}
            )
        approver1_emp_id = (attrs.get('approver1_emp_id') or '').strip()
        approver2_emp_id = (attrs.get('approver2_emp_id') or '').strip()
        if not approver1_emp_id:
            raise serializers.ValidationError(
                {'approver1_emp_id': ['Approver 1 is required.']}
            )
        if approver2_emp_id and approver1_emp_id.lower() == approver2_emp_id.lower():
            raise serializers.ValidationError(
                {'approver2_emp_id': ['Approver 1 and Approver 2 must be different people.']}
            )
        attrs['emp_ids'] = emp_ids
        attrs['approver1_emp_id'] = approver1_emp_id
        attrs['approver2_emp_id'] = approver2_emp_id
        return attrs


class AdminEmployeeApproverPatchSerializer(serializers.Serializer):
    clear_approver_1 = serializers.BooleanField(required=False, default=False)
    clear_approver_2 = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        if not attrs.get('clear_approver_1') and not attrs.get('clear_approver_2'):
            raise serializers.ValidationError(
                'Specify Approver 1, Approver 2, or both to remove.'
            )
        return attrs


class AdminEmployeeApproverRowSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    employee = EmployeeBriefSerializer(source='*', read_only=True)
    is_hod_title = serializers.SerializerMethodField()
    approver_1 = serializers.SerializerMethodField()
    approver_2 = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = ('id', 'employee', 'is_hod_title', 'approver_1', 'approver_2')

    def _mapping(self, employee):
        mappings = self.context.get('mappings')
        if mappings is not None:
            return mappings.get(employee.id)
        return personal_approver_mapping(employee)

    def get_id(self, employee):
        mapping = self._mapping(employee)
        return mapping.id if mapping else None

    def get_is_hod_title(self, employee):
        return looks_like_hod(employee)

    def get_approver_1(self, employee):
        if looks_like_hod(employee):
            return None
        mapping = self._mapping(employee)
        person = mapping.approver_1 if mapping else None
        return EmployeeBriefSerializer(person).data if person else None

    def get_approver_2(self, employee):
        if looks_like_hod(employee):
            return None
        mapping = self._mapping(employee)
        person = mapping.approver_2 if mapping else None
        return EmployeeBriefSerializer(person).data if person else None


def employee_approver_row(employee, mapping):
    return {
        'id': mapping.id if mapping else None,
        'employee': EmployeeBriefSerializer(employee).data,
        'approver_1': (
            EmployeeBriefSerializer(mapping.approver_1).data
            if mapping and mapping.approver_1_id
            else None
        ),
        'approver_2': (
            EmployeeBriefSerializer(mapping.approver_2).data
            if mapping and mapping.approver_2_id
            else None
        ),
    }


class AdminEmployeePatchSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150, required=False)
    email = serializers.EmailField(required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=Employee.Status.choices, required=False)
    department = serializers.CharField(max_length=150, required=False, allow_blank=True)
    sub_department = serializers.CharField(max_length=150, required=False, allow_blank=True)
    designation = serializers.CharField(max_length=150, required=False, allow_blank=True)
    designation_type = serializers.ChoiceField(
        choices=Employee.DesignationType.choices, required=False
    )

    def validate_name(self, value):
        name = (value or '').strip()
        if not name:
            raise serializers.ValidationError('Name is required.')
        return name

    def validate_email(self, value):
        return (value or '').strip().lower()

    def validate_department(self, value):
        return (value or '').strip()

    def validate_sub_department(self, value):
        return (value or '').strip()

    def validate_designation(self, value):
        return (value or '').strip()


class AdminEmployeeCreateSerializer(serializers.Serializer):
    emp_id = serializers.CharField(max_length=32)
    name = serializers.CharField(max_length=150)
    designation = serializers.CharField(max_length=150, allow_blank=True, required=False)
    department = serializers.CharField(max_length=150, allow_blank=True, required=False)
    sub_department = serializers.CharField(max_length=150, allow_blank=True, required=False)
    designation_type = serializers.ChoiceField(
        choices=Employee.DesignationType.choices,
        required=False,
    )

    def validate_emp_id(self, value):
        emp_id = (value or '').strip()
        if not emp_id:
            raise serializers.ValidationError('Employee ID is required.')
        if Employee.objects.filter(emp_id__iexact=emp_id).exists():
            raise serializers.ValidationError('An employee with this ID already exists.')
        return emp_id

    def validate_name(self, value):
        name = (value or '').strip()
        if not name:
            raise serializers.ValidationError('Name is required.')
        return name

    def validate_designation(self, value):
        return (value or '').strip()

    def validate_department(self, value):
        return (value or '').strip()

    def validate_sub_department(self, value):
        return (value or '').strip()

    def validate(self, attrs):
        department = (attrs.get('sub_department') or attrs.get('department') or '').strip()
        attrs['sub_department'] = department
        attrs['department'] = department
        designation = attrs.get('designation') or ''
        if not attrs.get('designation_type'):
            attrs['designation_type'] = infer_designation_type(designation)
        return attrs


def infer_designation_type(designation):
    text = (designation or '').lower()
    if any(token in text for token in ('professor', 'lecturer', 'faculty')):
        return Employee.DesignationType.FACULTY
    return Employee.DesignationType.STAFF


def staff_dept_approver_map():
    dept_map = {}
    assignments = ApproverAssignment.objects.filter(
        role__in=ApproverAssignment.STAFF_ROLES,
        employee__status=Employee.Status.ACTIVE,
    ).select_related('employee')
    for row in assignments:
        key = (row.department or '').strip().lower()
        bucket = dept_map.setdefault(key, {})
        existing = bucket.get(row.role)
        if existing is None or row.employee.emp_id < existing.employee.emp_id:
            bucket[row.role] = row
    return dept_map


def personal_approver_mapping(employee):
    try:
        return employee.personal_approver_map
    except EmployeeApprover.DoesNotExist:
        return None


def personal_approver_prefetch():
    return Prefetch(
        'personal_approver_map',
        queryset=EmployeeApprover.objects.select_related('approver_1', 'approver_2'),
    )


def active_employees_by_emp_id(emp_ids):
    wanted = []
    seen = set()
    for raw in emp_ids or []:
        emp_id = (raw or '').strip()
        key = emp_id.lower()
        if not emp_id or key in seen:
            continue
        seen.add(key)
        wanted.append(emp_id)
    if not wanted:
        return {}, wanted
    rows = Employee.objects.annotate(_lid=Lower('emp_id')).filter(
        _lid__in=list(seen),
        status=Employee.Status.ACTIVE,
    )
    return {row.emp_id.lower(): row for row in rows}, wanted


class AdminResetPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True, trim_whitespace=False, min_length=8)
    confirm_password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError(
                {'confirm_password': 'Passwords do not match.'}
            )
        if attrs['new_password'] == settings.DEFAULT_EMPLOYEE_PASSWORD:
            raise serializers.ValidationError(
                {'new_password': 'Choose a new password; the default password is not allowed.'}
            )
        user = self.context.get('user')
        try:
            validate_password(attrs['new_password'], user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({'new_password': list(exc.messages)})
        return attrs


class AdminEmployeeSerializer(EmployeeDirectorySerializer):
    is_admin = serializers.SerializerMethodField()
    is_operator = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()
    is_hod_title = serializers.SerializerMethodField()
    approver_1 = serializers.SerializerMethodField()
    approver_2 = serializers.SerializerMethodField()

    class Meta(EmployeeDirectorySerializer.Meta):
        fields = DIRECTORY_FIELDS + (
            'is_admin', 'is_operator', 'roles', 'is_hod_title', 'approver_1', 'approver_2',
        )

    def get_is_admin(self, employee):
        account = getattr(employee, 'account', None)
        if account is None:
            return False
        user = getattr(account, 'user', None)
        return bool(
            account.is_admin
            or (user and (user.is_staff or user.is_superuser))
        )

    def get_is_operator(self, employee):
        account = getattr(employee, 'account', None)
        return bool(account and account.is_operator)

    def get_roles(self, employee):
        assignments = getattr(employee, 'approver_assignments', None)
        if assignments is None:
            return []
        return sorted({row.role for row in assignments.all()})

    def get_is_hod_title(self, employee):
        return looks_like_hod(employee)

    def _approver_brief(self, employee, role):
        if looks_like_hod(employee):
            return None
        mapping = personal_approver_mapping(employee)
        if mapping is not None:
            person = mapping.approver_1 if role == ApproverAssignment.Role.APPROVER_1 else mapping.approver_2
            return EmployeeBriefSerializer(person).data if person else None
        dept_map = self.context.get('dept_approvers') or {}
        assignment = dept_map.get((employee.department or '').strip().lower(), {}).get(role)
        if assignment and assignment.employee_id:
            return EmployeeBriefSerializer(assignment.employee).data
        return None

    def get_approver_1(self, employee):
        return self._approver_brief(employee, ApproverAssignment.Role.APPROVER_1)

    def get_approver_2(self, employee):
        return self._approver_brief(employee, ApproverAssignment.Role.APPROVER_2)


class AuditActionSerializer(serializers.ModelSerializer):
    actor_emp_id = serializers.CharField(source='actor.emp_id', read_only=True)
    actor_name = serializers.CharField(source='actor.name', read_only=True)
    applicant_emp_id = serializers.CharField(source='application.employee.emp_id', read_only=True)
    applicant_name = serializers.CharField(source='application.employee.name', read_only=True)
    leave_type = serializers.CharField(source='application.leave_type.code', read_only=True)

    class Meta:
        model = ApprovalAction
        fields = (
            'id', 'step', 'decision', 'remarks', 'created_at',
            'actor_emp_id', 'actor_name', 'applicant_emp_id', 'applicant_name',
            'leave_type', 'application_id',
        )


class AuditPagination(ApprovalPagination):
    def get_paginated_response(self, data):
        return ok(
            'Audit log.',
            {
                'results': data,
                'count': self.page.paginator.count,
                'page': self.page.number,
                'page_size': self.get_page_size(self.request),
            },
        )


class EmployeeApproverPagination(EmployeePagination):
    def get_paginated_response(self, data):
        return ok(
            'Employees and personal approvers.',
            {
                'results': data,
                'count': self.page.paginator.count,
                'page': self.page.number,
                'page_size': self.get_page_size(self.request),
            },
        )


class AdminOverviewView(APIView):
    permission_classes = OPERATOR_PERMS

    def get(self, request):
        return ok(
            'Admin overview.',
            {
                'employees': Employee.objects.count(),
                'active_employees': Employee.objects.filter(status=Employee.Status.ACTIVE).count(),
                'pending_leaves': LeaveApplication.objects.filter(
                    status=LeaveApplication.Status.PENDING
                ).count(),
                'approved_leaves': LeaveApplication.objects.filter(
                    status=LeaveApplication.Status.APPROVED
                ).count(),
                'leave_types': LeaveType.objects.count(),
                'approver_assignments': ApproverAssignment.objects.count(),
                'admin_accounts': Account.objects.filter(ADMIN_ACCOUNT_Q).count(),
            },
        )


class AdminLeaveTypeListView(ListCreateAPIView):
    permission_classes = SYSTEM_ADMIN_PERMS
    serializer_class = AdminLeaveTypeSerializer
    queryset = LeaveType.objects.all()

    def list(self, request, *args, **kwargs):
        return ok('Leave types.', AdminLeaveTypeSerializer(self.get_queryset(), many=True).data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return ok('Leave type created.', serializer.data, status=201)


class AdminLeaveTypeDetailView(APIView):
    permission_classes = SYSTEM_ADMIN_PERMS

    def patch(self, request, pk):
        leave_type = get_object_or_404(LeaveType, pk=pk)
        serializer = AdminLeaveTypeSerializer(leave_type, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return ok('Leave type updated.', serializer.data)


class AdminApproverListView(ListCreateAPIView):
    permission_classes = SYSTEM_ADMIN_PERMS
    serializer_class = ApproverAssignmentSerializer
    queryset = ApproverAssignment.objects.select_related('employee').all()

    def list(self, request, *args, **kwargs):
        return ok(
            'Approver assignments.',
            ApproverAssignmentSerializer(self.get_queryset(), many=True).data,
        )

    def create(self, request, *args, **kwargs):
        serializer = AdminApproverWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            employee = Employee.objects.get(
                emp_id__iexact=serializer.validated_data['emp_id'],
                status=Employee.Status.ACTIVE,
            )
        except Employee.DoesNotExist:
            return fail('No active employee found for that ID.', status=404)
        try:
            assignment, created = assign_approver(
                serializer.validated_data['role'],
                employee,
                department=serializer.validated_data['department'],
                sub_department=serializer.validated_data['sub_department'],
            )
        except ApprovalError as exc:
            return fail(exc.message, errors=exc.errors, status=exc.status)
        message = 'Approver assignment created.' if created else 'Approver assignment updated.'
        return ok(message, ApproverAssignmentSerializer(assignment).data, status=201 if created else 200)


class AdminApproverBulkView(APIView):
    permission_classes = SYSTEM_ADMIN_PERMS

    def post(self, request):
        return _assign_employee_approvers(request)


EMPLOYEE_APPROVER_EXPORT_FILENAME = 'employee-approvers.xlsx'
EMPLOYEE_APPROVER_EXCEL_HEADERS = (
    'Employee ID',
    'Name',
    'Department',
    'Designation',
    'Approver 1',
    'Approver 1 ID',
    'Approver 2',
    'Approver 2 ID',
)


def employee_approver_queryset(request):
    queryset = Employee.objects.annotate(
        has_personal=Exists(
            EmployeeApprover.objects.filter(employee_id=OuterRef('pk'))
        )
    )
    query = (request.query_params.get('q') or '').strip()
    unit = employee_unit_from_request(request)
    designation = (request.query_params.get('designation') or '').strip()
    if query:
        queryset = queryset.filter(
            Q(emp_id__icontains=query) | Q(name__icontains=query)
        )
    if unit:
        queryset = queryset.filter(sub_department__iexact=unit)
    if designation:
        queryset = queryset.filter(designation__iexact=designation)
    return queryset.order_by('-has_personal', 'emp_id')


def employee_approver_mappings(employees):
    return {
        row.employee_id: row
        for row in EmployeeApprover.objects.filter(
            employee_id__in=[employee.id for employee in employees]
        ).select_related('approver_1', 'approver_2')
    }


def employee_approver_excel_row(employee, mapping):
    if looks_like_hod(employee):
        return [
            employee.emp_id,
            employee.name,
            employee.sub_department or '',
            employee.designation or '',
            'Vice-Chancellor only',
            '',
            '',
            '',
        ]
    approver_1 = mapping.approver_1 if mapping else None
    approver_2 = mapping.approver_2 if mapping else None
    return [
        employee.emp_id,
        employee.name,
        employee.sub_department or '',
        employee.designation or '',
        approver_1.name if approver_1 else '',
        approver_1.emp_id if approver_1 else '',
        approver_2.name if approver_2 else '',
        approver_2.emp_id if approver_2 else '',
    ]


class AdminEmployeeApproverListView(APIView):
    permission_classes = SYSTEM_ADMIN_PERMS

    def get(self, request):
        queryset = employee_approver_queryset(request)
        paginator = EmployeeApproverPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        page = list(page)
        mappings = employee_approver_mappings(page)
        return paginator.get_paginated_response(
            AdminEmployeeApproverRowSerializer(
                page, many=True, context={'mappings': mappings}
            ).data
        )

    def post(self, request):
        return _assign_employee_approvers(request)


class AdminEmployeeApproverExportView(APIView):
    permission_classes = SYSTEM_ADMIN_PERMS

    def get(self, request):
        employees = list(employee_approver_queryset(request))
        mappings = employee_approver_mappings(employees)
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = 'Employee-Approver'
        sheet.append(list(EMPLOYEE_APPROVER_EXCEL_HEADERS))
        for employee in employees:
            sheet.append(employee_approver_excel_row(employee, mappings.get(employee.id)))
        buffer = BytesIO()
        workbook.save(buffer)
        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = (
            f'attachment; filename="{EMPLOYEE_APPROVER_EXPORT_FILENAME}"'
        )
        return response


def _assign_employee_approvers(request):
    serializer = AdminEmployeeApproverWriteSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    emp_ids = serializer.validated_data['emp_ids']
    approver1_emp_id = serializer.validated_data['approver1_emp_id']
    approver2_emp_id = serializer.validated_data.get('approver2_emp_id') or ''
    lookup_ids = [approver1_emp_id, *emp_ids]
    if approver2_emp_id:
        lookup_ids.append(approver2_emp_id)
    by_id, _ = active_employees_by_emp_id(lookup_ids)
    approver_1 = by_id.get(approver1_emp_id.lower())
    approver_2 = by_id.get(approver2_emp_id.lower()) if approver2_emp_id else None
    if approver_1 is None:
        return fail(
            'No active employee found for that ID.',
            errors={'approver1_emp_id': [approver1_emp_id]},
            status=404,
        )
    if approver2_emp_id and approver_2 is None:
        return fail(
            'No active employee found for that ID.',
            errors={'approver2_emp_id': [approver2_emp_id]},
            status=404,
        )
    missing_subjects = [emp_id for emp_id in emp_ids if emp_id.lower() not in by_id]
    if missing_subjects:
        return fail(
            'No active employee found for that ID.',
            errors={'emp_ids': missing_subjects},
            status=404,
        )
    subjects = [by_id[emp_id.lower()] for emp_id in emp_ids]
    hods = [employee for employee in subjects if looks_like_hod(employee)]
    staff = [employee for employee in subjects if not looks_like_hod(employee)]
    if not staff:
        return ok(
            'HOD leave is approved only by the Vice-Chancellor. Approver 1 and Approver 2 were not set.',
            {
                'count': 0,
                'emp_ids': [],
                'skipped_hod_emp_ids': [employee.emp_id for employee in hods],
                'assignments': [],
            },
        )
    try:
        rows = set_employee_staff_approvers(staff, approver_1, approver_2)
    except ApprovalError as exc:
        return fail(exc.message, errors=exc.errors, status=exc.status)
    count = len(rows)
    noun = 'employee' if count == 1 else 'employees'
    if approver_2:
        message = f'Set Approver 1 and Approver 2 for {count} selected {noun}.'
    else:
        message = (
            f'Set Approver 1 for {count} selected {noun}. '
            'Leave goes to the Vice-Chancellor after Approver 1.'
        )
    if hods:
        message += ' HOD employees were skipped; they wait only on the Vice-Chancellor.'
    return ok(
        message,
        {
            'count': count,
            'emp_ids': [employee.emp_id for employee in staff],
            'skipped_hod_emp_ids': [employee.emp_id for employee in hods],
            'assignments': EmployeeApproverSerializer(rows, many=True).data,
        },
    )


class AdminEmployeeApproverDetailView(APIView):
    permission_classes = SYSTEM_ADMIN_PERMS

    def patch(self, request, pk):
        mapping = get_object_or_404(
            EmployeeApprover.objects.select_related(
                'employee', 'approver_1', 'approver_2'
            ),
            pk=pk,
        )
        serializer = AdminEmployeeApproverPatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        employee = mapping.employee
        try:
            updated = clear_employee_staff_approvers(
                mapping,
                clear_approver_1=serializer.validated_data.get('clear_approver_1'),
                clear_approver_2=serializer.validated_data.get('clear_approver_2'),
            )
        except ApprovalError as exc:
            return fail(exc.message, errors=exc.errors, status=exc.status)
        message = (
            'Employee approver mapping removed.'
            if updated is None
            else 'Employee approver mapping updated.'
        )
        return ok(message, employee_approver_row(employee, updated))

    def delete(self, request, pk):
        mapping = get_object_or_404(EmployeeApprover, pk=pk)
        mapping.delete()
        return ok('Employee approver mapping removed.')


class AdminApproverDetailView(APIView):
    permission_classes = SYSTEM_ADMIN_PERMS

    def delete(self, request, pk):
        assignment = get_object_or_404(ApproverAssignment, pk=pk)
        assignment.delete()
        return ok('Approver assignment removed.')


class AdminEmployeeListView(ListAPIView):
    permission_classes = SYSTEM_ADMIN_PERMS
    serializer_class = AdminEmployeeSerializer
    pagination_class = EmployeePagination

    def get_queryset(self):
        queryset = Employee.objects.select_related(
            'account',
            'account__user',
        ).prefetch_related('approver_assignments', personal_approver_prefetch())
        params = self.request.query_params
        query = (params.get('q') or '').strip()
        designation_type = (params.get('designation_type') or '').strip().upper()
        group_name = (params.get('group_name') or '').strip()
        unit = employee_unit_from_request(self.request)
        designation = (params.get('designation') or '').strip()
        status_value = (params.get('status') or '').strip()

        if query:
            queryset = queryset.filter(
                Q(emp_id__icontains=query)
                | Q(name__icontains=query)
                | Q(department__icontains=query)
                | Q(sub_department__icontains=query)
                | Q(designation__icontains=query)
            )
        if designation_type in Employee.DesignationType.values:
            queryset = queryset.filter(designation_type=designation_type)
        if group_name:
            queryset = queryset.filter(group_name__iexact=group_name)
        queryset = apply_optional_blank_filter(
            queryset,
            'sub_department',
            unit,
            blank_flag=truthy_query_flag(params, 'blank_department'),
        )
        queryset = apply_optional_blank_filter(
            queryset,
            'designation',
            designation,
            blank_flag=truthy_query_flag(params, 'blank_designation'),
        )
        if status_value in Employee.Status.values:
            queryset = queryset.filter(status=status_value)
        is_admin_param = (self.request.query_params.get('is_admin') or '').strip().lower()
        if is_admin_param in ('1', 'true', 'yes'):
            queryset = queryset.filter(
                Q(account__is_admin=True)
                | Q(account__user__is_staff=True)
                | Q(account__user__is_superuser=True)
            )
        is_operator_param = (self.request.query_params.get('is_operator') or '').strip().lower()
        if is_operator_param in ('1', 'true', 'yes'):
            queryset = queryset.filter(account__is_operator=True)
        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['dept_approvers'] = staff_dept_approver_map()
        return context

    def post(self, request):
        serializer = AdminEmployeeCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        employee = Employee.objects.create(
            emp_id=data['emp_id'],
            name=data['name'],
            designation=data.get('designation') or '',
            designation_type=data['designation_type'],
            department=data.get('department') or '',
            sub_department=data.get('sub_department') or '',
            status=Employee.Status.ACTIVE,
        )
        return ok(
            'Employee added.',
            serialize_admin_employee(employee),
            status=201,
        )


class AdminEmployeeFilterOptionsView(APIView):
    permission_classes = OPERATOR_PERMS

    def get(self, request):
        active = Employee.objects.filter(status=Employee.Status.ACTIVE)
        unit = employee_unit_from_request(request)
        designation_qs = apply_optional_blank_filter(
            active,
            'sub_department',
            unit,
            blank_flag=truthy_query_flag(request.query_params, 'blank_department'),
        )
        departments = list(
            active.exclude(sub_department='')
            .order_by('sub_department')
            .values_list('sub_department', flat=True)
            .distinct()
        )
        designations = list(
            designation_qs.exclude(designation='')
            .order_by('designation')
            .values_list('designation', flat=True)
            .distinct()
        )
        return ok(
            'Employee filter options.',
            {'departments': departments, 'designations': designations},
        )


class AdminEmployeeDetailView(APIView):
    permission_classes = SYSTEM_ADMIN_PERMS

    def patch(self, request, emp_id):
        employee = get_object_or_404(
            Employee.objects.select_related(
                'account',
                'account__user',
            ).prefetch_related(
                'approver_assignments',
                personal_approver_prefetch(),
            ),
            emp_id__iexact=emp_id,
        )
        serializer = AdminEmployeePatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        for field, value in data.items():
            setattr(employee, field, value)
        employee.save()
        employee = Employee.objects.select_related(
            'account',
            'account__user',
        ).prefetch_related(
            'approver_assignments',
            personal_approver_prefetch(),
        ).get(pk=employee.pk)
        return ok(
            'Employee updated.',
            AdminEmployeeSerializer(
                employee, context={'dept_approvers': staff_dept_approver_map()}
            ).data,
        )

    def delete(self, request, emp_id):
        employee = get_object_or_404(
            Employee.objects.select_related('account', 'account__user'),
            emp_id__iexact=emp_id,
        )
        current = linked_employee(request.user)
        if current is not None and current.pk == employee.pk:
            return fail(
                'Cannot delete your own employee record. Set Inactive instead.',
            )

        try:
            account = employee.account
        except Account.DoesNotExist:
            account = None
        if account and (
            account.is_admin
            or account.user.is_staff
            or account.user.is_superuser
        ):
            other_admins = (
                Account.objects.filter(ADMIN_ACCOUNT_Q).exclude(pk=account.pk).count()
            )
            if other_admins == 0:
                return fail(
                    'Cannot delete the last remaining admin. Set Inactive instead.',
                )

        if employee.leave_applications.exists():
            return fail(UNSAFE_EMPLOYEE_DELETE)
        if (
            employee.as_personal_approver_1.exists()
            or employee.as_personal_approver_2.exists()
            or employee.approval_actions.exists()
        ):
            return fail(UNSAFE_EMPLOYEE_DELETE)

        deleted_emp_id = employee.emp_id
        try:
            with transaction.atomic():
                if account is not None:
                    user = account.user
                    account.delete()
                    user.delete()
                employee.delete()
        except ProtectedError:
            return fail(UNSAFE_EMPLOYEE_DELETE)

        return ok('Employee deleted.', {'emp_id': deleted_emp_id})


class AdminEmployeeResetPasswordView(APIView):
    permission_classes = SYSTEM_ADMIN_PERMS

    def post(self, request, emp_id):
        employee = get_object_or_404(Employee, emp_id__iexact=emp_id)
        account = provision_account(employee)
        serializer = AdminResetPasswordSerializer(
            data=request.data,
            context={'user': account.user},
        )
        serializer.is_valid(raise_exception=True)
        account.user.set_password(serializer.validated_data['new_password'])
        account.user.save(update_fields=['password'])
        account.must_change_password = True
        account.save(update_fields=['must_change_password', 'updated_at'])
        return ok(
            'Password reset. The employee can sign in with the new password and will be asked to change it.',
            {
                'emp_id': employee.emp_id,
                'name': employee.name,
                'must_change_password': True,
            },
        )


class AdminReportView(APIView):
    permission_classes = OPERATOR_PERMS

    def get(self, request):
        year = request.query_params.get('year')
        queryset = LeaveApplication.objects.all()
        if year:
            try:
                year = int(year)
            except (TypeError, ValueError):
                return fail(
                    'Year must be a number.',
                    errors={'year': ['Enter a four-digit year.']},
                )
            queryset = queryset.filter(start_date__year=year)
        by_status = {
            row['status']: row['count']
            for row in queryset.values('status').annotate(count=Count('id'))
        }
        by_type = list(
            queryset.values('leave_type__code', 'leave_type__name')
            .annotate(count=Count('id'), days=Sum('days'))
            .order_by('-count')
        )
        by_department = list(
            queryset.values('employee__sub_department')
            .annotate(count=Count('id'))
            .order_by('-count')[:20]
        )
        by_chain = {
            row['chain_type']: row['count']
            for row in queryset.values('chain_type').annotate(count=Count('id'))
        }
        return ok(
            'Leave report.',
            {
                'total': queryset.count(),
                'year': year,
                'by_status': by_status,
                'by_type': [
                    {
                        'code': row['leave_type__code'],
                        'name': row['leave_type__name'],
                        'count': row['count'],
                        'days': float(row['days'] or 0),
                    }
                    for row in by_type
                ],
                'by_department': [
                    {
                        'department': row['employee__sub_department'] or 'Unspecified',
                        'count': row['count'],
                    }
                    for row in by_department
                ],
                'by_chain': by_chain,
            },
        )


class AdminAuditView(ListAPIView):
    permission_classes = OPERATOR_PERMS
    serializer_class = AuditActionSerializer
    pagination_class = AuditPagination
    queryset = ApprovalAction.objects.select_related(
        'actor', 'application__employee', 'application__leave_type'
    )


DEFAULT_LEAVE_LOCATION = 'Girijananda Chowdhury University-Assam'
ADMIN_LEAVE_EXPORT_FILENAME = 'leave-applications.xlsx'
ADMIN_LEAVE_EXCEL_HEADERS = (
    'Serial No.',
    'Employee ID',
    'Name',
    'Location',
    'Leave Type',
    'Request Date',
    'From Date',
    'To Date',
    'Status',
    'Timeline',
    'Total Days',
)


class AdminLeavePagination(ApprovalPagination):
    def get_paginated_response(self, data):
        return ok(
            'Leave applications.',
            {
                'results': data,
                'count': self.page.paginator.count,
                'page': self.page.number,
                'page_size': self.get_page_size(self.request),
            },
        )


def parse_admin_date(value, field):
    raw = (value or '').strip()
    if not raw:
        return None
    for fmt in ('%Y-%m-%d', '%d-%m-%Y'):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return fail(
        'Enter dates as YYYY-MM-DD.',
        errors={field: ['Enter a valid date.']},
    )


def numeric_days(days):
    if days is None:
        return 0
    value = float(days)
    if value.is_integer():
        return int(value)
    return value


def format_dd_mm_yyyy(value):
    if value is None:
        return ''
    if hasattr(value, 'strftime'):
        if hasattr(value, 'date') and not hasattr(value, 'year'):
            value = value.date()
        elif hasattr(value, 'hour'):
            value = value.date()
        return value.strftime('%d-%m-%Y')
    return str(value)


def title_status(status):
    if not status:
        return ''
    return str(status).replace('_', ' ').title()


def leave_location(employee):
    academy = (getattr(employee, 'academy', None) or '').strip()
    return academy or DEFAULT_LEAVE_LOCATION


def request_date_for(application):
    return application.requested_on or (
        application.created_at.date() if application.created_at else None
    )


def serialize_admin_leave_action(action):
    actor = action.actor
    return {
        'id': action.id,
        'step': action.step,
        'step_label': action.get_step_display(),
        'decision': action.decision,
        'decision_label': title_status(action.decision),
        'actor_name': actor.name if actor else '',
        'actor_emp_id': actor.emp_id if actor else '',
        'remarks': action.remarks,
        'created_at': action.created_at,
    }


def serialize_admin_leave_row(application, serial_no):
    employee = application.employee
    leave_type = application.leave_type
    return {
        'id': application.id,
        'serial_no': serial_no,
        'emp_id': employee.emp_id if employee else '',
        'name': employee.name if employee else '',
        'location': leave_location(employee) if employee else DEFAULT_LEAVE_LOCATION,
        'leave_type': leave_type.name if leave_type else '',
        'request_date': request_date_for(application),
        'from_date': application.start_date,
        'to_date': application.end_date,
        'status': application.status,
        'status_label': title_status(application.status),
        'timeline': 'View',
        'total_days': numeric_days(application.days),
        'actions': [
            serialize_admin_leave_action(action)
            for action in application.approval_actions.all()
        ],
    }


def admin_leave_excel_row(application, serial_no):
    employee = application.employee
    leave_type = application.leave_type
    return [
        serial_no,
        employee.emp_id if employee else '',
        employee.name if employee else '',
        leave_location(employee) if employee else DEFAULT_LEAVE_LOCATION,
        leave_type.name if leave_type else '',
        format_dd_mm_yyyy(request_date_for(application)),
        format_dd_mm_yyyy(application.start_date),
        format_dd_mm_yyyy(application.end_date),
        title_status(application.status),
        'View',
        numeric_days(application.days),
    ]


def admin_leave_queryset(request):
    queryset = LeaveApplication.objects.select_related(
        'employee',
        'leave_type',
    ).prefetch_related(
        Prefetch(
            'approval_actions',
            queryset=ApprovalAction.objects.select_related('actor').order_by('created_at'),
        )
    )
    query = (request.query_params.get('q') or '').strip()
    unit = employee_unit_from_request(request)
    designation = (request.query_params.get('designation') or '').strip()
    start = parse_admin_date(request.query_params.get('start'), 'start')
    if hasattr(start, 'data'):
        return start
    end = parse_admin_date(request.query_params.get('end'), 'end')
    if hasattr(end, 'data'):
        return end

    if query:
        queryset = queryset.filter(
            Q(employee__name__icontains=query) | Q(employee__emp_id__icontains=query)
        )
    if unit:
        queryset = queryset.filter(employee__sub_department__iexact=unit)
    if designation:
        queryset = queryset.filter(employee__designation__iexact=designation)
    if start and end:
        queryset = queryset.filter(start_date__lte=end, end_date__gte=start)
    elif start:
        queryset = queryset.filter(end_date__gte=start)
    elif end:
        queryset = queryset.filter(start_date__lte=end)
    return queryset


class AdminLeaveListView(APIView):
    permission_classes = OPERATOR_PERMS

    def get(self, request):
        queryset = admin_leave_queryset(request)
        if hasattr(queryset, 'data'):
            return queryset
        paginator = AdminLeavePagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        offset = (paginator.page.number - 1) * paginator.get_page_size(request)
        rows = [
            serialize_admin_leave_row(application, offset + index + 1)
            for index, application in enumerate(page)
        ]
        return paginator.get_paginated_response(rows)


class AdminLeaveExportView(APIView):
    permission_classes = OPERATOR_PERMS

    def get(self, request):
        queryset = admin_leave_queryset(request)
        if hasattr(queryset, 'data'):
            return queryset
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = 'Leaves'
        sheet.append(list(ADMIN_LEAVE_EXCEL_HEADERS))
        for index, application in enumerate(queryset, start=1):
            sheet.append(admin_leave_excel_row(application, index))
        buffer = BytesIO()
        workbook.save(buffer)
        payload = buffer.getvalue()
        response = HttpResponse(
            payload,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = f'attachment; filename="{ADMIN_LEAVE_EXPORT_FILENAME}"'
        return response


def serialize_admin_employee(employee):
    employee = Employee.objects.select_related(
        'account',
        'account__user',
    ).prefetch_related(
        'approver_assignments',
        personal_approver_prefetch(),
    ).get(pk=employee.pk)
    return AdminEmployeeSerializer(
        employee, context={'dept_approvers': staff_dept_approver_map()}
    ).data


class AdminAccessPatchSerializer(serializers.Serializer):
    is_admin = serializers.BooleanField(required=False)
    is_operator = serializers.BooleanField(required=False)

    def validate(self, attrs):
        if 'is_admin' not in attrs and 'is_operator' not in attrs:
            raise serializers.ValidationError('Specify is_admin or is_operator.')
        return attrs


class AdminAccessDetailView(APIView):
    permission_classes = SYSTEM_ADMIN_PERMS

    def patch(self, request, emp_id):
        employee = get_object_or_404(Employee, emp_id__iexact=emp_id)
        serializer = AdminAccessPatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        account = provision_account(employee)
        try:
            apply_account_access(
                account,
                is_admin=serializer.validated_data.get('is_admin'),
                is_operator=serializer.validated_data.get('is_operator'),
            )
        except AccessError as exc:
            return fail(exc.message, errors=exc.errors, status=exc.status)
        return ok('Access updated.', serialize_admin_employee(employee))


class AdminAssignLeaveSerializer(serializers.Serializer):
    ACTION_CREDIT = 'CREDIT'
    ACTION_SANCTION = 'SANCTION'
    ACTION_CHOICES = (ACTION_CREDIT, ACTION_SANCTION)

    emp_id = serializers.CharField(max_length=32)
    leave_type_id = serializers.IntegerField()
    days = serializers.DecimalField(max_digits=6, decimal_places=1, min_value=Decimal('0.1'))
    action = serializers.ChoiceField(choices=ACTION_CHOICES)
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    year = serializers.IntegerField(required=False, min_value=2000, max_value=2100)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    session = serializers.ChoiceField(
        choices=LeaveApplication.Session.choices,
        required=False,
        allow_blank=True,
    )

    def validate(self, attrs):
        action = attrs['action']
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')
        if end_date and not start_date:
            raise serializers.ValidationError(
                {'start_date': ['Start date is required when an end date is set.']}
            )
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError(
                {'end_date': ['End date cannot be before start date.']}
            )
        if action == self.ACTION_SANCTION and not start_date:
            raise serializers.ValidationError(
                {'start_date': ['Start date is required to sanction leave.']}
            )
        return attrs


def serialize_leave_credit(credit):
    employee = credit.employee
    granted = credit.granted_by
    leave_type = credit.leave_type
    return {
        'id': credit.id,
        'kind': 'CREDIT',
        'emp_id': employee.emp_id if employee else '',
        'name': employee.name if employee else '',
        'leave_type_id': leave_type.id if leave_type else None,
        'leave_type': leave_type.name if leave_type else '',
        'leave_type_code': leave_type.code if leave_type else '',
        'days': numeric_days(credit.days),
        'year': credit.year,
        'start_date': None,
        'end_date': None,
        'reason': credit.reason,
        'granted_by_emp_id': granted.emp_id if granted else '',
        'granted_by_name': granted.name if granted else '',
        'created_at': credit.created_at,
    }


def serialize_sanctioned_leave(application):
    employee = application.employee
    leave_type = application.leave_type
    return {
        'id': application.id,
        'kind': 'SANCTION',
        'emp_id': employee.emp_id if employee else '',
        'name': employee.name if employee else '',
        'leave_type_id': leave_type.id if leave_type else None,
        'leave_type': leave_type.name if leave_type else '',
        'leave_type_code': leave_type.code if leave_type else '',
        'days': numeric_days(application.days),
        'year': application.start_date.year if application.start_date else None,
        'start_date': application.start_date,
        'end_date': application.end_date,
        'reason': application.reason,
        'granted_by_emp_id': '',
        'granted_by_name': '',
        'created_at': application.created_at,
        'status': application.status,
        'waiting_on': None,
        'source': application.source,
    }


class AdminAssignLeaveView(APIView):
    permission_classes = SYSTEM_ADMIN_PERMS

    def get(self, request):
        credits = list(
            LeaveCredit.objects.select_related(
                'employee', 'leave_type', 'granted_by'
            ).order_by('-created_at')[:40]
        )
        sanctions = list(
            LeaveApplication.objects.filter(
                source=LeaveApplication.Source.ASSIGNED,
            ).select_related('employee', 'leave_type').order_by('-created_at')[:40]
        )
        rows = [serialize_leave_credit(row) for row in credits]
        rows.extend(serialize_sanctioned_leave(row) for row in sanctions)
        rows.sort(key=lambda item: item['created_at'] or timezone.now(), reverse=True)
        return ok('Assigned leave grants.', rows[:40])

    def post(self, request):
        serializer = AdminAssignLeaveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            employee = Employee.objects.get(
                emp_id__iexact=data['emp_id'],
                status=Employee.Status.ACTIVE,
            )
        except Employee.DoesNotExist:
            return fail(
                'No active employee found for that ID.',
                errors={'emp_id': [data['emp_id']]},
                status=404,
            )
        leave_type = get_object_or_404(LeaveType, pk=data['leave_type_id'])
        granted_by = linked_employee(request.user)
        try:
            if data['action'] == AdminAssignLeaveSerializer.ACTION_CREDIT:
                year = data.get('year') or timezone.localdate().year
                credit = credit_leave_days(
                    employee,
                    leave_type,
                    data['days'],
                    year,
                    reason=data.get('reason') or '',
                    granted_by=granted_by,
                )
                payload = serialize_leave_credit(credit)
                payload['balances'] = leave_balances(employee, year)
                return ok('Leave balance credited.', payload, status=201)
            application = sanction_approved_leave(
                employee,
                leave_type,
                data['days'],
                data.get('start_date'),
                end_date=data.get('end_date'),
                reason=data.get('reason') or '',
                granted_by=granted_by,
                session=data.get('session'),
            )
            payload = serialize_sanctioned_leave(application)
            payload['balances'] = leave_balances(employee, application.start_date.year)
            return ok('Leave sanctioned.', payload, status=201)
        except LeaveError as exc:
            return fail(exc.message, errors=exc.errors, status=exc.status)

