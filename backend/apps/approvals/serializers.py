from rest_framework import serializers

from apps.employees.serializers import EmployeeBriefSerializer
from apps.leaves.models import LeaveApplication
from apps.leaves.serializers import LeaveTypeSerializer

from .models import ApprovalAction, ApproverAssignment, EmployeeApprover


class ApprovalActionSerializer(serializers.ModelSerializer):
    actor = EmployeeBriefSerializer(read_only=True)

    class Meta:
        model = ApprovalAction
        fields = ('id', 'step', 'decision', 'remarks', 'actor', 'created_at')


class ApprovalApplicationSerializer(serializers.ModelSerializer):
    leave_type = LeaveTypeSerializer(read_only=True)
    employee = EmployeeBriefSerializer(read_only=True)
    waiting_on = EmployeeBriefSerializer(read_only=True)
    actions = ApprovalActionSerializer(source='approval_actions', many=True, read_only=True)
    days = serializers.DecimalField(
        max_digits=6, decimal_places=1, coerce_to_string=False, read_only=True
    )

    class Meta:
        model = LeaveApplication
        fields = (
            'id', 'employee', 'leave_type', 'start_date', 'end_date', 'days',
            'session', 'reason', 'status', 'chain_type', 'current_step', 'waiting_on',
            'actions', 'requested_on', 'source', 'created_at',
        )


class DecideSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=['APPROVED', 'REJECTED'])
    remarks = serializers.CharField(required=False, allow_blank=True, max_length=2000)

    def validate(self, attrs):
        if attrs['decision'] == 'REJECTED' and not (attrs.get('remarks') or '').strip():
            raise serializers.ValidationError(
                {'remarks': ['Please give a reason for rejection.']}
            )
        return attrs


class ApproverAssignmentSerializer(serializers.ModelSerializer):
    employee = EmployeeBriefSerializer(read_only=True)

    class Meta:
        model = ApproverAssignment
        fields = (
            'id', 'role', 'department', 'sub_department', 'employee',
        )


class EmployeeApproverSerializer(serializers.ModelSerializer):
    employee = EmployeeBriefSerializer(read_only=True)
    approver_1 = EmployeeBriefSerializer(read_only=True, allow_null=True)
    approver_2 = EmployeeBriefSerializer(read_only=True, allow_null=True)

    class Meta:
        model = EmployeeApprover
        fields = ('id', 'employee', 'approver_1', 'approver_2')
