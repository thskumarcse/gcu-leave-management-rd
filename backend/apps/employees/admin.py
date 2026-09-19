from django.contrib import admin

from .models import Employee


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = (
        'emp_id', 'name', 'department', 'sub_department', 'designation',
        'group_name', 'designation_type', 'status', 'joining_date',
    )
    list_filter = ('designation_type', 'group_name', 'user_type', 'status', 'department')
    search_fields = ('emp_id', 'name', 'email', 'department', 'sub_department')
    ordering = ('emp_id',)
    readonly_fields = ('created_at', 'updated_at')
