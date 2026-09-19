from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.accounts.permissions import (
    IsOperatorOrAdmin,
    PasswordChangeNotRequired,
    user_is_operator_or_admin,
)
from apps.core.responses import fail, ok

from .models import Employee
from .pagination import EmployeePagination
from .serializers import EmployeeDirectorySerializer, EmployeeSelfSerializer

BLANK_FILTER = '__blank__'


def employee_unit_from_request(request):
    """Department in the UI is Sub Department. Accept both query names."""
    params = request.query_params
    return (
        (params.get('sub_department') or '').strip()
        or (params.get('department') or '').strip()
    )


def is_blank_filter_value(value):
    return (value or '').strip().lower() == BLANK_FILTER


def truthy_query_flag(params, name):
    return (params.get(name) or '').strip().lower() in ('1', 'true', 'yes')


def blank_or_empty_q(field):
    return Q(**{field: ''}) | Q(**{f'{field}__isnull': True})


def apply_optional_blank_filter(queryset, field, raw_value, blank_flag=False):
    """Match a normal iexact value, or empty/null when the blank sentinel is used."""
    value = (raw_value or '').strip()
    if blank_flag or is_blank_filter_value(value):
        return queryset.filter(blank_or_empty_q(field))
    if value:
        return queryset.filter(**{f'{field}__iexact': value})
    return queryset


def linked_employee(user):
    account = getattr(user, 'account', None)
    return getattr(account, 'employee', None)


class MyEmployeeView(APIView):
    def get(self, request):
        employee = linked_employee(request.user)
        if employee is None:
            return fail('No employee record is linked to this account.', status=404)
        return ok('Employee profile.', EmployeeSelfSerializer(employee).data)


class EmployeeListView(ListAPIView):
    serializer_class = EmployeeDirectorySerializer
    pagination_class = EmployeePagination
    permission_classes = [IsAuthenticated, PasswordChangeNotRequired, IsOperatorOrAdmin]

    def get_queryset(self):
        queryset = Employee.objects.filter(status=Employee.Status.ACTIVE)
        query = (self.request.query_params.get('q') or '').strip()
        designation_type = (self.request.query_params.get('designation_type') or '').strip().upper()
        group_name = (self.request.query_params.get('group_name') or '').strip()
        unit = employee_unit_from_request(self.request)

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
        if unit:
            queryset = queryset.filter(sub_department__iexact=unit)
        return queryset


class EmployeeDetailView(APIView):
    def get(self, request, emp_id):
        employee = get_object_or_404(Employee, emp_id__iexact=emp_id)
        viewer = linked_employee(request.user)
        is_self = viewer is not None and viewer.id == employee.id

        if employee.status != Employee.Status.ACTIVE and not is_self:
            return fail('Employee not found.', status=404)

        serializer_class = EmployeeSelfSerializer if is_self else EmployeeDirectorySerializer
        if not is_self and not user_is_operator_or_admin(request.user):
            return fail('Employee not found.', status=404)
        return ok('Employee record.', serializer_class(employee).data)
