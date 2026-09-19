from django.contrib import admin

from .models import ApprovalAction, ApproverAssignment, EmployeeApprover


@admin.register(ApproverAssignment)
class ApproverAssignmentAdmin(admin.ModelAdmin):
    list_display = ('role', 'department', 'sub_department', 'employee', 'updated_at')
    list_filter = ('role', 'department')
    search_fields = (
        'employee__emp_id', 'employee__name', 'department', 'sub_department',
    )
    autocomplete_fields = ('employee',)


@admin.register(EmployeeApprover)
class EmployeeApproverAdmin(admin.ModelAdmin):
    list_display = ('employee', 'approver_1', 'approver_2', 'updated_at')
    search_fields = (
        'employee__emp_id',
        'employee__name',
        'approver_1__emp_id',
        'approver_1__name',
        'approver_2__emp_id',
        'approver_2__name',
    )
    autocomplete_fields = ('employee', 'approver_1', 'approver_2')


@admin.register(ApprovalAction)
class ApprovalActionAdmin(admin.ModelAdmin):
    list_display = ('application', 'step', 'decision', 'actor', 'created_at')
    list_filter = ('step', 'decision')
    search_fields = (
        'application__employee__emp_id',
        'actor__emp_id',
        'actor__name',
        'remarks',
    )
    autocomplete_fields = ('application', 'actor')
    readonly_fields = ('created_at',)
