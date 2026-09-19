from decimal import Decimal
from datetime import timedelta

from django.db.models import Min, Q, Sum
from django.utils import timezone

from .models import LeaveApplication, LeaveCredit, LeaveType

HALF_DAY = Decimal('0.5')


class LeaveError(Exception):
    def __init__(self, message, status=400, errors=None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.errors = errors or {}


def normalize_session(leave_type, session):
    if leave_type.code != 'CL':
        return LeaveApplication.Session.FULL_DAY
    session = (session or LeaveApplication.Session.FULL_DAY).strip().upper()
    if session not in LeaveApplication.Session.values:
        raise LeaveError(
            'Casual leave must be First Half, Second Half, or Full day.',
            errors={'session': ['Choose First Half, Second Half, or Full day.']},
        )
    return session


def count_leave_days(start_date, end_date, session=None):
    if end_date < start_date:
        raise LeaveError(
            'End date cannot be before start date.',
            errors={'end_date': ['End date cannot be before start date.']},
        )
    session = session or LeaveApplication.Session.FULL_DAY
    if session in (LeaveApplication.Session.FIRST_HALF, LeaveApplication.Session.SECOND_HALF):
        if start_date != end_date:
            raise LeaveError(
                'Half-day casual leave must be for a single date.',
                errors={'end_date': ['Use the same date for First Half or Second Half.']},
            )
        return HALF_DAY
    return Decimal((end_date - start_date).days + 1)


def _blocking_queryset(employee, exclude_id=None):
    queryset = LeaveApplication.objects.filter(
        employee=employee,
        status__in=[LeaveApplication.Status.PENDING, LeaveApplication.Status.APPROVED],
    )
    if exclude_id:
        queryset = queryset.exclude(pk=exclude_id)
    return queryset


def assert_no_overlap(employee, start_date, end_date, session=None, exclude_id=None):
    session = session or LeaveApplication.Session.FULL_DAY
    overlapping = _blocking_queryset(employee, exclude_id).filter(
        start_date__lte=end_date,
        end_date__gte=start_date,
    )
    if session == LeaveApplication.Session.FIRST_HALF:
        overlapping = overlapping.exclude(session=LeaveApplication.Session.SECOND_HALF)
    elif session == LeaveApplication.Session.SECOND_HALF:
        overlapping = overlapping.exclude(session=LeaveApplication.Session.FIRST_HALF)
    if overlapping.exists():
        raise LeaveError(
            'This period overlaps an existing pending or approved leave.',
            errors={'start_date': ['Overlaps another leave application.']},
        )


def used_days_for(employee, leave_type, year, exclude_id=None):
    return _blocking_queryset(employee, exclude_id).filter(
        leave_type=leave_type,
        start_date__year=year,
    ).aggregate(total=Sum('days'))['total'] or Decimal('0')


def extra_credit_days(employee, leave_type, year):
    total = LeaveCredit.objects.filter(
        employee=employee,
        leave_type=leave_type,
        year=year,
    ).aggregate(total=Sum('days'))['total']
    return total or Decimal('0')


def credit_baseline_used(employee, leave_type, year):
    values = list(
        LeaveCredit.objects.filter(
            employee=employee,
            leave_type=leave_type,
            year=year,
        ).values_list('baseline_used', flat=True)
    )
    if not values:
        return None
    return min(values)


def _remaining_for_type(leave_type, used, credited, baseline):
    credited = credited or Decimal('0')
    used = used or Decimal('0')
    base = leave_type.max_days_per_year
    if base is None:
        if credited <= 0:
            return None, None
        usage_against_credit = max(used - (baseline or Decimal('0')), Decimal('0'))
        remaining = max(credited - usage_against_credit, Decimal('0'))
        return remaining, credited
    maximum = Decimal(base) + credited
    remaining = max(maximum - used, Decimal('0'))
    return remaining, maximum


def yearly_entitlement(employee, leave_type, year):
    extra = extra_credit_days(employee, leave_type, year)
    base = leave_type.max_days_per_year
    if base is None:
        return extra if extra > 0 else None
    return Decimal(base) + extra


def remaining_days_for(employee, leave_type, year, exclude_id=None):
    used = used_days_for(employee, leave_type, year, exclude_id=exclude_id)
    credited = extra_credit_days(employee, leave_type, year)
    baseline = credit_baseline_used(employee, leave_type, year)
    remaining, _maximum = _remaining_for_type(leave_type, used, credited, baseline)
    return remaining


def assert_balance_available(employee, leave_type, start_date, days, exclude_id=None):
    remaining = remaining_days_for(
        employee, leave_type, start_date.year, exclude_id=exclude_id
    )
    if remaining is None:
        return
    if days > remaining:
        raise LeaveError(
            (
                f'{leave_type.name} has {_as_number(remaining)} day(s) remaining '
                f'in {start_date.year}.'
            ),
            errors={'leave_type_id': ['Not enough balance for this leave type.']},
        )


def leave_types_for(employee):
    return LeaveType.objects.filter(is_active=True).filter(
        Q(applicable_to=LeaveType.ApplicableTo.ALL)
        | Q(applicable_to=employee.designation_type)
    )


def submit_leave(employee, leave_type, start_date, end_date, reason, session=None):
    if not leave_type.is_active:
        raise LeaveError('This leave type is not available.')
    if leave_type.applicable_to != LeaveType.ApplicableTo.ALL:
        if leave_type.applicable_to != employee.designation_type:
            raise LeaveError('This leave type is not available for your role.')

    session = normalize_session(leave_type, session)
    days = count_leave_days(start_date, end_date, session)
    assert_no_overlap(employee, start_date, end_date, session)
    assert_balance_available(employee, leave_type, start_date, days)

    application = LeaveApplication.objects.create(
        employee=employee,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        days=days,
        session=session,
        reason=reason.strip(),
        requested_on=timezone.localdate(),
        status=LeaveApplication.Status.PENDING,
        source=LeaveApplication.Source.INTERNAL,
    )
    from apps.approvals.services import route_new_application
    return route_new_application(application)


def cancel_leave(application, employee):
    if application.employee_id != employee.id:
        raise LeaveError('Leave application not found.', status=404)
    if application.status != LeaveApplication.Status.PENDING:
        raise LeaveError('Only pending applications can be cancelled.')
    application.status = LeaveApplication.Status.CANCELLED
    application.current_step = ''
    application.waiting_on = None
    application.save(update_fields=['status', 'current_step', 'waiting_on', 'updated_at'])
    return application


def _as_number(value):
    if value is None:
        return None
    number = float(value)
    if number.is_integer():
        return int(number)
    return number


def leave_balances(employee, year=None):
    year = year or timezone.localdate().year
    types = list(leave_types_for(employee))
    used_rows = _blocking_queryset(employee).filter(start_date__year=year).values(
        'leave_type_id'
    ).annotate(total=Sum('days'))
    used_map = {row['leave_type_id']: row['total'] or Decimal('0') for row in used_rows}
    credit_rows = LeaveCredit.objects.filter(employee=employee, year=year).values(
        'leave_type_id'
    ).annotate(total=Sum('days'), baseline=Min('baseline_used'))
    credit_map = {row['leave_type_id']: row['total'] or Decimal('0') for row in credit_rows}
    baseline_map = {row['leave_type_id']: row['baseline'] for row in credit_rows}
    balances = []
    for leave_type in types:
        used = used_map.get(leave_type.id, Decimal('0'))
        credited = credit_map.get(leave_type.id, Decimal('0'))
        remaining, maximum = _remaining_for_type(
            leave_type,
            used,
            credited,
            baseline_map.get(leave_type.id),
        )
        balances.append(
            {
                'id': leave_type.id,
                'code': leave_type.code,
                'name': leave_type.name,
                'max_days_per_year': _as_number(maximum),
                'credited': _as_number(credited),
                'used': _as_number(used),
                'remaining': _as_number(remaining),
            }
        )
    return balances


def leave_summary(employee):
    queryset = LeaveApplication.objects.filter(employee=employee)
    counts = {
        'pending': queryset.filter(status=LeaveApplication.Status.PENDING).count(),
        'approved': queryset.filter(status=LeaveApplication.Status.APPROVED).count(),
        'rejected': queryset.filter(status=LeaveApplication.Status.REJECTED).count(),
        'cancelled': queryset.filter(status=LeaveApplication.Status.CANCELLED).count(),
    }
    recent = list(queryset.select_related('leave_type', 'waiting_on')[:5])
    return counts, recent, leave_balances(employee)


def _notify_assigned(employee, title, message):
    from apps.notifications.services import notify_employee

    notify_employee(employee, title, message, link='/leaves')


def credit_leave_days(employee, leave_type, days, year, reason='', granted_by=None):
    days = Decimal(str(days))
    if days <= 0:
        raise LeaveError(
            'Days must be greater than zero.',
            errors={'days': ['Enter a positive number of days.']},
        )
    if not leave_type.is_active:
        raise LeaveError('This leave type is not available.')
    used = used_days_for(employee, leave_type, year)
    credit = LeaveCredit.objects.create(
        employee=employee,
        leave_type=leave_type,
        year=year,
        days=days,
        baseline_used=used,
        reason=(reason or '').strip(),
        granted_by=granted_by,
    )
    _notify_assigned(
        employee,
        'Leave balance credited',
        (
            f'{_as_number(days)} extra day(s) of {leave_type.name} '
            f'were added to your {year} balance.'
        ),
    )
    return credit


def _sanction_dates(leave_type, start_date, end_date, days, session):
    if start_date is None:
        raise LeaveError(
            'Start date is required to sanction leave.',
            errors={'start_date': ['Enter a start date.']},
        )
    if end_date is not None:
        session = normalize_session(leave_type, session)
        counted = count_leave_days(start_date, end_date, session)
        return start_date, end_date, counted, session

    days = Decimal(str(days))
    if days <= 0:
        raise LeaveError(
            'Days must be greater than zero.',
            errors={'days': ['Enter a positive number of days.']},
        )
    if days == HALF_DAY:
        session = normalize_session(
            leave_type,
            session or LeaveApplication.Session.FIRST_HALF,
        )
        if session == LeaveApplication.Session.FULL_DAY:
            session = LeaveApplication.Session.FIRST_HALF
            if leave_type.code != 'CL':
                raise LeaveError(
                    'Half-day leave is only available for casual leave.',
                    errors={'days': ['Use a whole number of days for this leave type.']},
                )
        return start_date, start_date, HALF_DAY, session

    if days != days.to_integral_value():
        raise LeaveError(
            'Use a whole number of days, or 0.5 for half-day casual leave.',
            errors={'days': ['Enter a whole number of days.']},
        )
    session = LeaveApplication.Session.FULL_DAY
    end_date = start_date + timedelta(days=int(days) - 1)
    counted = count_leave_days(start_date, end_date, session)
    return start_date, end_date, counted, session


def sanction_approved_leave(
    employee,
    leave_type,
    days,
    start_date,
    end_date=None,
    reason='',
    granted_by=None,
    session=None,
):
    if not leave_type.is_active:
        raise LeaveError('This leave type is not available.')
    start_date, end_date, counted, session = _sanction_dates(
        leave_type, start_date, end_date, days, session
    )
    assert_no_overlap(employee, start_date, end_date, session)
    note = (reason or '').strip() or 'Sanctioned by administration.'
    application = LeaveApplication.objects.create(
        employee=employee,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        days=counted,
        session=session,
        reason=note,
        requested_on=timezone.localdate(),
        status=LeaveApplication.Status.APPROVED,
        chain_type=LeaveApplication.ChainType.NONE,
        current_step='',
        waiting_on=None,
        source=LeaveApplication.Source.ASSIGNED,
    )
    _notify_assigned(
        employee,
        'Leave sanctioned',
        (
            f'{_as_number(counted)} day(s) of {leave_type.name} '
            f'were sanctioned from {start_date.isoformat()} to {end_date.isoformat()}.'
        ),
    )
    return application
