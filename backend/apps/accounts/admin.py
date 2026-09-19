from django.conf import settings
from django.contrib import admin, messages

from .models import Account


@admin.action(description='Reset selected accounts to the default password')
def reset_to_default_password(modeladmin, request, queryset):
    count = 0
    for account in queryset.select_related('user'):
        account.user.set_password(settings.DEFAULT_EMPLOYEE_PASSWORD)
        account.user.save(update_fields=['password'])
        account.must_change_password = True
        account.save(update_fields=['must_change_password', 'updated_at'])
        count += 1
    messages.success(
        request,
        f'Reset {count} account(s) to the default password. They must change it at next login.',
    )


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = (
        'emp_id', 'employee_name', 'must_change_password', 'is_admin', 'is_operator', 'updated_at',
    )
    list_filter = ('must_change_password', 'is_admin', 'is_operator')
    search_fields = ('employee__emp_id', 'employee__name', 'user__username')
    autocomplete_fields = ('user', 'employee')
    readonly_fields = ('created_at', 'updated_at')
    actions = [reset_to_default_password]

    @admin.display(ordering='employee__emp_id', description='Employee ID')
    def emp_id(self, obj):
        return obj.employee.emp_id

    @admin.display(ordering='employee__name', description='Name')
    def employee_name(self, obj):
        return obj.employee.name
