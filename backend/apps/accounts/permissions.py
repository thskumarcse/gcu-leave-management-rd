from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission


class PasswordChangeRequired(PermissionDenied):
    default_detail = 'You must change your default password before continuing.'
    default_code = 'password_change_required'


class PasswordChangeNotRequired(BasePermission):
    """
    Blocks every authenticated endpoint until the employee replaces the
    default password. Views that must stay reachable during that (login,
    change-password, me, logout, refresh) override permission_classes.
    """

    def has_permission(self, request, view):
        user = request.user
        if not getattr(user, 'is_authenticated', False):
            return True
        account = getattr(user, 'account', None)
        if account and account.must_change_password:
            raise PasswordChangeRequired()
        return True


def account_for(user):
    return getattr(user, 'account', None)


def user_is_system_admin(user):
    if not getattr(user, 'is_authenticated', False):
        return False
    if user.is_staff or user.is_superuser:
        return True
    account = account_for(user)
    return bool(account and account.is_admin)


def user_is_operator_or_admin(user):
    if user_is_system_admin(user):
        return True
    account = account_for(user)
    return bool(account and account.is_operator)


class IsSystemAdmin(BasePermission):
    """Developer admin: grant/revoke Access (is_admin / is_operator)."""

    def has_permission(self, request, view):
        return user_is_system_admin(request.user)


class IsOperatorOrAdmin(BasePermission):
    """Analytics (and directory). Settings stay admin-only."""

    def has_permission(self, request, view):
        return user_is_operator_or_admin(request.user)
