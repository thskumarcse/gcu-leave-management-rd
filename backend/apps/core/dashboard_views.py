from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.accounts.permissions import PasswordChangeNotRequired
from apps.approvals.serializers import ApprovalApplicationSerializer
from apps.approvals.services import approver_dashboard, inbox_queryset, roles_for_employee
from apps.core.responses import fail, ok
from apps.employees.views import linked_employee


class ApproverDashboardView(APIView):
    permission_classes = [IsAuthenticated, PasswordChangeNotRequired]

    def get(self, request):
        employee = linked_employee(request.user)
        if employee is None:
            return fail('No employee record is linked to this account.', status=404)
        roles = roles_for_employee(employee)
        if not (roles['is_hod'] or roles['is_vc'] or roles['is_approver']):
            return fail('You do not have an approval role.', status=403)
        data = approver_dashboard(employee)
        recent = inbox_queryset(employee)[:8]
        data['recent'] = ApprovalApplicationSerializer(recent, many=True).data
        data.update(roles)
        return ok('Approver dashboard.', data)
