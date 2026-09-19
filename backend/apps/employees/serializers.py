from rest_framework import serializers

from .models import Employee


class EmployeeBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = (
            'emp_id', 'name', 'designation', 'department', 'sub_department',
            'designation_type',
        )


DIRECTORY_FIELDS = (
    'emp_id',
    'name',
    'designation',
    'designation_type',
    'group_name',
    'user_type',
    'department',
    'sub_department',
    'academy',
    'email',
    'joining_date',
    'status',
)


class EmployeeDirectorySerializer(serializers.ModelSerializer):
    """Public employee fields. Date of birth and mobile stay off the directory."""

    class Meta:
        model = Employee
        fields = DIRECTORY_FIELDS


class EmployeeSelfSerializer(serializers.ModelSerializer):
    """Full master record, returned only to the employee themselves."""

    class Meta:
        model = Employee
        fields = DIRECTORY_FIELDS + ('dob', 'mobile')
