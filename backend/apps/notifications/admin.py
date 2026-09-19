from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('employee', 'title', 'is_read', 'created_at')
    list_filter = ('is_read',)
    search_fields = ('employee__emp_id', 'employee__name', 'title', 'message')
    autocomplete_fields = ('employee',)
    readonly_fields = ('created_at',)
