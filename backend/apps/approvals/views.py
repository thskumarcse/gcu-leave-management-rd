from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.generics import ListAPIView
from rest_framework.views import APIView

from apps.core.responses import fail, ok
from apps.employees.views import linked_employee
from apps.leaves.models import LeaveApplication
from apps.leaves.serializers import LeaveApplicationSerializer
from apps.leaves.services import leave_balances

from .pagination import ApplicantLeavePagination, ApprovalPagination
from .serializers import (
    ApprovalApplicationSerializer,
    ApproverAssignmentSerializer,
    DecideSerializer,
)
from .services import ApprovalError, decide_application, inbox_queryset, roles_for_employee
from .models import ApproverAssignment


def require_employee(user):
    employee = linked_employee(user)
    if employee is None:
        return None, fail('No employee record is linked to this account.', status=404)
    return employee, None


class ApprovalInboxView(ListAPIView):
    serializer_class = ApprovalApplicationSerializer
    pagination_class = ApprovalPagination

    def get_queryset(self):
        employee = linked_employee(self.request.user)
        if employee is None:
            return LeaveApplication.objects.none()
        return inbox_queryset(employee)

    def list(self, request, *args, **kwargs):
        employee, error = require_employee(request.user)
        if error:
            return error
        return super().list(request, *args, **kwargs)


class ApprovalDetailView(APIView):
    def get(self, request, pk):
        employee, error = require_employee(request.user)
        if error:
            return error
        application = get_object_or_404(inbox_queryset(employee), pk=pk)
        return ok(
            'Leave application awaiting your decision.',
            ApprovalApplicationSerializer(application).data,
        )


class ApprovalEmployeeLeavesView(APIView):
    """Applicant leave usage for an inbox item the viewer is waiting on."""

    def get(self, request, pk):
        employee, error = require_employee(request.user)
        if error:
            return error
        application = get_object_or_404(inbox_queryset(employee), pk=pk)
        applicant = application.employee
        year = timezone.localdate().year
        queryset = LeaveApplication.objects.filter(employee=applicant).select_related(
            'leave_type', 'waiting_on'
        )
        paginator = ApplicantLeavePagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return ok(
            'Applicant leave usage.',
            {
                'year': year,
                'balances': leave_balances(applicant, year=year),
                'leaves': paginator.nested_payload(
                    LeaveApplicationSerializer(page, many=True).data
                ),
            },
        )


class ApprovalDecideView(APIView):
    def post(self, request, pk):
        employee, error = require_employee(request.user)
        if error:
            return error

        serializer = DecideSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        application = get_object_or_404(
            LeaveApplication.objects.select_related('employee', 'leave_type', 'waiting_on'),
            pk=pk,
        )
        try:
            application = decide_application(
                application,
                employee,
                serializer.validated_data['decision'],
                serializer.validated_data.get('remarks', ''),
            )
        except ApprovalError as exc:
            return fail(exc.message, errors=exc.errors, status=exc.status)

        application = (
            LeaveApplication.objects.select_related('employee', 'leave_type', 'waiting_on')
            .prefetch_related('approval_actions__actor')
            .get(pk=application.pk)
        )
        message = (
            'Leave application rejected.'
            if application.status == LeaveApplication.Status.REJECTED
            else (
                'Leave application approved.'
                if application.status == LeaveApplication.Status.APPROVED
                else 'Forwarded to the next approver.'
            )
        )
        return ok(message, ApprovalApplicationSerializer(application).data)


class MyApprovalRolesView(APIView):
    def get(self, request):
        employee, error = require_employee(request.user)
        if error:
            return error
        assignments = ApproverAssignment.objects.filter(
            employee=employee
        ).select_related('employee')
        return ok(
            'Approval roles.',
            {
                **roles_for_employee(employee),
                'assignments': ApproverAssignmentSerializer(assignments, many=True).data,
            },
        )
