from rest_framework_simplejwt.tokens import RefreshToken

from apps.approvals.services import roles_for_employee
from apps.notifications.services import unread_count


def issue_tokens(user):
    refresh = RefreshToken.for_user(user)
    account = getattr(user, 'account', None)
    employee = getattr(account, 'employee', None)

    claims = {
        'emp_id': employee.emp_id if employee else user.username,
        'name': employee.name if employee else user.get_full_name(),
        'must_change_password': bool(account and account.must_change_password),
    }
    for key, value in claims.items():
        refresh[key] = value
        refresh.access_token[key] = value

    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    }


def serialize_account(account):
    employee = account.employee
    payload = {
        'emp_id': employee.emp_id,
        'name': employee.name,
        'email': employee.email,
        'department': employee.department,
        'designation': employee.designation,
        'designation_type': employee.designation_type,
        'group_name': employee.group_name,
        'sub_department': employee.sub_department,
        'must_change_password': account.must_change_password,
        'is_admin': bool(
            account.is_admin
            or account.user.is_staff
            or account.user.is_superuser
        ),
        'is_operator': bool(account.is_operator),
        'unread_notifications': unread_count(employee),
    }
    payload.update(roles_for_employee(employee))
    return payload
