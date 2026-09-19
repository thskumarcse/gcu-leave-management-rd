from rest_framework.generics import ListAPIView
from rest_framework.views import APIView

from apps.core.responses import fail, ok
from apps.employees.views import linked_employee

from .models import Notification
from .pagination import NotificationPagination
from .serializers import NotificationSerializer
from .services import mark_read, unread_count


def require_employee(user):
    employee = linked_employee(user)
    if employee is None:
        return None, fail('No employee record is linked to this account.', status=404)
    return employee, None


class NotificationListView(ListAPIView):
    serializer_class = NotificationSerializer
    pagination_class = NotificationPagination

    def get_queryset(self):
        employee = linked_employee(self.request.user)
        if employee is None:
            return Notification.objects.none()
        return Notification.objects.filter(employee=employee)

    def list(self, request, *args, **kwargs):
        employee, error = require_employee(request.user)
        if error:
            return error
        response = super().list(request, *args, **kwargs)
        if hasattr(response, 'data') and isinstance(response.data, dict):
            payload = response.data.get('data') or {}
            if isinstance(payload, dict):
                payload['unread'] = unread_count(employee)
        return response


class NotificationReadView(APIView):
    def post(self, request, pk=None):
        employee, error = require_employee(request.user)
        if error:
            return error
        updated = mark_read(employee, pk)
        return ok('Notifications marked read.', {'updated': updated, 'unread': unread_count(employee)})
