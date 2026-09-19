from .models import Notification


def notify_employee(employee, title, message, link=''):
    if employee is None:
        return None
    return Notification.objects.create(
        employee=employee,
        title=title,
        message=message,
        link=link or '',
    )


def unread_count(employee):
    if employee is None:
        return 0
    return Notification.objects.filter(employee=employee, is_read=False).count()


def mark_read(employee, pk=None):
    queryset = Notification.objects.filter(employee=employee, is_read=False)
    if pk is not None:
        queryset = queryset.filter(pk=pk)
    return queryset.update(is_read=True)
