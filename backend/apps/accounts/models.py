from django.conf import settings
from django.db import models


class Account(models.Model):
    """
    Login record for an Employee. There is no self-serve registration —
    an Account is created on first successful login with the default
    password, tied 1:1 to an existing Employee master row.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='account',
    )
    employee = models.OneToOneField(
        'employees.Employee',
        on_delete=models.PROTECT,
        related_name='account',
    )
    must_change_password = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    is_operator = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['employee__emp_id']
        indexes = [
            models.Index(fields=['must_change_password']),
            models.Index(fields=['is_admin']),
            models.Index(fields=['is_operator']),
        ]

    @property
    def is_developer_admin(self):
        user = getattr(self, 'user', None)
        return bool(
            self.is_admin
            or (user and (user.is_staff or user.is_superuser))
        )

    def __str__(self):
        return f'{self.employee.emp_id} account'
