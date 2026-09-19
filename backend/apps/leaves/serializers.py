from rest_framework import serializers

from apps.employees.serializers import EmployeeBriefSerializer

from .models import LeaveApplication, LeaveType


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = (
            'id', 'name', 'code', 'description', 'max_days_per_year',
            'applicable_to', 'requires_document',
        )


class LeaveApplicationSerializer(serializers.ModelSerializer):
    leave_type = LeaveTypeSerializer(read_only=True)
    waiting_on = EmployeeBriefSerializer(read_only=True)
    days = serializers.DecimalField(
        max_digits=6, decimal_places=1, coerce_to_string=False, read_only=True
    )

    class Meta:
        model = LeaveApplication
        fields = (
            'id', 'leave_type', 'start_date', 'end_date', 'days', 'session',
            'reason', 'status', 'chain_type', 'current_step', 'waiting_on',
            'requested_on', 'source', 'created_at',
        )


class LeaveApplySerializer(serializers.Serializer):
    leave_type_id = serializers.IntegerField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    session = serializers.ChoiceField(
        choices=LeaveApplication.Session.choices,
        required=False,
        default=LeaveApplication.Session.FULL_DAY,
    )
    reason = serializers.CharField(min_length=8, max_length=2000)

    def validate(self, attrs):
        if attrs['end_date'] < attrs['start_date']:
            raise serializers.ValidationError(
                {'end_date': ['End date cannot be before start date.']}
            )
        session = attrs.get('session') or LeaveApplication.Session.FULL_DAY
        if session in (
            LeaveApplication.Session.FIRST_HALF,
            LeaveApplication.Session.SECOND_HALF,
        ) and attrs['start_date'] != attrs['end_date']:
            raise serializers.ValidationError(
                {'end_date': ['Use the same date for First Half or Second Half.']}
            )
        return attrs
