from django.shortcuts import get_object_or_404
from rest_framework.generics import ListAPIView
from rest_framework.views import APIView

from apps.core.responses import fail, ok
from apps.employees.views import linked_employee

from .models import LeaveApplication, LeaveType
from .pagination import LeavePagination
from .serializers import (
    LeaveApplicationSerializer,
    LeaveApplySerializer,
    LeaveTypeSerializer,
)
from .services import (
    LeaveError,
    cancel_leave,
    leave_balances,
    leave_summary,
    leave_types_for,
    submit_leave,
)


def require_employee(user):
    employee = linked_employee(user)
    if employee is None:
        return None, fail('No employee record is linked to this account.', status=404)
    return employee, None


class LeaveTypeListView(APIView):
    def get(self, request):
        employee, error = require_employee(request.user)
        if error:
            return error
        types = leave_types_for(employee)
        balances = {item['id']: item for item in leave_balances(employee)}
        payload = []
        for leave_type in types:
            data = LeaveTypeSerializer(leave_type).data
            usage = balances.get(leave_type.id, {})
            data['used'] = usage.get('used', 0)
            data['remaining'] = usage.get('remaining')
            data['credited'] = usage.get('credited', 0)
            if 'max_days_per_year' in usage:
                data['max_days_per_year'] = usage.get('max_days_per_year')
            payload.append(data)
        return ok('Leave types.', payload)


class LeaveListCreateView(ListAPIView):
    serializer_class = LeaveApplicationSerializer
    pagination_class = LeavePagination

    def get_queryset(self):
        employee = linked_employee(self.request.user)
        if employee is None:
            return LeaveApplication.objects.none()
        queryset = LeaveApplication.objects.filter(employee=employee).select_related(
            'leave_type', 'waiting_on'
        )
        status_filter = (self.request.query_params.get('status') or '').strip().upper()
        if status_filter in LeaveApplication.Status.values:
            queryset = queryset.filter(status=status_filter)
        return queryset

    def list(self, request, *args, **kwargs):
        employee, error = require_employee(request.user)
        if error:
            return error
        return super().list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        employee, error = require_employee(request.user)
        if error:
            return error

        serializer = LeaveApplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        leave_type = get_object_or_404(
            LeaveType, pk=serializer.validated_data['leave_type_id']
        )
        try:
            application = submit_leave(
                employee,
                leave_type,
                serializer.validated_data['start_date'],
                serializer.validated_data['end_date'],
                serializer.validated_data['reason'],
                serializer.validated_data.get('session'),
            )
        except LeaveError as exc:
            return fail(exc.message, errors=exc.errors, status=exc.status)

        return ok(
            'Leave application submitted.',
            LeaveApplicationSerializer(application).data,
            status=201,
        )


class LeaveSummaryView(APIView):
    def get(self, request):
        employee, error = require_employee(request.user)
        if error:
            return error
        counts, recent, balances = leave_summary(employee)
        return ok(
            'Leave summary.',
            {
                **counts,
                'balances': balances,
                'recent': LeaveApplicationSerializer(recent, many=True).data,
            },
        )


class LeaveDetailView(APIView):
    def get(self, request, pk):
        employee, error = require_employee(request.user)
        if error:
            return error
        application = get_object_or_404(
            LeaveApplication.objects.select_related('leave_type', 'waiting_on'),
            pk=pk,
            employee=employee,
        )
        return ok('Leave application.', LeaveApplicationSerializer(application).data)


class LeaveCancelView(APIView):
    def post(self, request, pk):
        employee, error = require_employee(request.user)
        if error:
            return error
        application = get_object_or_404(LeaveApplication, pk=pk, employee=employee)
        try:
            application = cancel_leave(application, employee)
        except LeaveError as exc:
            return fail(exc.message, errors=exc.errors, status=exc.status)
        return ok('Leave application cancelled.', LeaveApplicationSerializer(application).data)
