from django.db import models


class Notification(models.Model):
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    title = models.CharField(max_length=160)
    message = models.CharField(max_length=400)
    link = models.CharField(max_length=200, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['employee', 'is_read']),
        ]

    def __str__(self):
        return f'{self.employee.emp_id}: {self.title}'
