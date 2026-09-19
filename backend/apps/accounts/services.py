from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.db import transaction
from django.db.models import Q

from apps.employees.models import Employee

from .models import Account

User = get_user_model()

INVALID_CREDENTIALS = 'Invalid employee ID or password.'
INACTIVE_EMPLOYEE = 'This employee ID is not active. Contact the administrator.'


def default_password():
    return getattr(settings, 'DEFAULT_EMPLOYEE_PASSWORD', 'gcu@123')


class AuthError(Exception):
    def __init__(self, message, status=401, code=None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code


def _split_name(full_name):
    parts = (full_name or '').strip().split(None, 1)
    if not parts:
        return '', ''
    if len(parts) == 1:
        return parts[0], ''
    return parts[0], parts[1]


def provision_account(employee):
    """
    Ensure a Django user + Account exist for this employee. First-time
    accounts get the default password and must_change_password=True.
    """
    first_name, last_name = _split_name(employee.name)
    with transaction.atomic():
        user, created = User.objects.get_or_create(
            username=employee.emp_id,
            defaults={
                'email': employee.email,
                'first_name': first_name,
                'last_name': last_name,
            },
        )
        if created or not user.has_usable_password():
            user.set_password(default_password())
            user.save(update_fields=['password'])

        account, _ = Account.objects.get_or_create(
            employee=employee,
            defaults={'user': user, 'must_change_password': True},
        )
        if account.user_id != user.id:
            account.user = user
            account.save(update_fields=['user', 'updated_at'])
    return account


def login_with_emp_id(emp_id, password):
    emp_id = (emp_id or '').strip()
    password = password or ''

    if not emp_id or not password:
        raise AuthError(INVALID_CREDENTIALS)

    try:
        employee = Employee.objects.get(emp_id__iexact=emp_id)
    except Employee.DoesNotExist:
        raise AuthError(INVALID_CREDENTIALS)

    if not employee.is_active:
        raise AuthError(INACTIVE_EMPLOYEE, status=403, code='employee_inactive')

    account = provision_account(employee)
    user = authenticate(username=account.user.username, password=password)
    if user is None:
        raise AuthError(INVALID_CREDENTIALS)

    return account


class AccessError(Exception):
    def __init__(self, message, status=400, errors=None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.errors = errors or {}


ADMIN_ACCOUNT_Q = Q(is_admin=True) | Q(user__is_staff=True) | Q(user__is_superuser=True)


def account_is_admin(account):
    if account is None:
        return False
    user = getattr(account, 'user', None)
    return bool(
        account.is_admin
        or (user and (user.is_staff or user.is_superuser))
    )


def apply_account_access(account, *, is_admin=None, is_operator=None):
    """
    Grant or revoke developer-admin / operator flags. Last remaining admin
    cannot be removed. Operators never receive Django is_staff.
    """
    if is_admin is None and is_operator is None:
        raise AccessError('Specify is_admin or is_operator.')

    currently_admin = account_is_admin(account)
    if is_admin is not None and currently_admin and not is_admin:
        other_admins = Account.objects.filter(ADMIN_ACCOUNT_Q).exclude(pk=account.pk).count()
        if other_admins == 0:
            raise AccessError(
                'Cannot remove the last remaining admin.',
                errors={'is_admin': ['At least one admin must remain.']},
            )

    update_fields = ['updated_at']
    if is_operator is not None:
        account.is_operator = bool(is_operator)
        update_fields.append('is_operator')
    if is_admin is not None:
        account.is_admin = bool(is_admin)
        update_fields.append('is_admin')
    account.save(update_fields=update_fields)

    if is_admin is not None:
        user = account.user
        if is_admin and not user.is_staff:
            user.is_staff = True
            user.save(update_fields=['is_staff'])
        if not is_admin and user.is_staff and not user.is_superuser:
            user.is_staff = False
            user.save(update_fields=['is_staff'])
    return account
