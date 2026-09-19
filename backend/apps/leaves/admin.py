from django.contrib import admin

from .models import LeaveApplication, LeaveCredit, LeaveType


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = (
        'code', 'name', 'max_days_per_year', 'applicable_to',
        'requires_document', 'is_active', 'sort_order',
    )
    list_filter = ('applicable_to', 'is_active', 'requires_document')
    search_fields = ('code', 'name')
    ordering = ('sort_order', 'name')


@admin.register(LeaveApplication)
class LeaveApplicationAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'employee', 'leave_type', 'start_date', 'end_date',
        'days', 'session', 'status', 'current_step', 'waiting_on', 'source',
        'requested_on', 'created_at',
    )
    list_filter = ('status', 'leave_type', 'session', 'chain_type', 'current_step', 'source')
    search_fields = ('employee__emp_id', 'employee__name', 'reason', 'external_key')
    autocomplete_fields = ('employee', 'leave_type', 'waiting_on')
    readonly_fields = ('days', 'external_key', 'created_at', 'updated_at')


@admin.register(LeaveCredit)
class LeaveCreditAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'employee', 'leave_type', 'year', 'days', 'baseline_used', 'granted_by', 'created_at',
    )
    list_filter = ('year', 'leave_type')
    search_fields = ('employee__emp_id', 'employee__name', 'reason')
    autocomplete_fields = ('employee', 'leave_type', 'granted_by')
    readonly_fields = ('created_at', 'updated_at')
