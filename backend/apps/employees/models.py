from django.db import models


class Employee(models.Model):
    """
    The employee master record, sourced from data/employee.csv via the
    import_employees management command. Separate from the login Account —
    an employee can exist here with no login, and system/ERP rows in the
    CSV are skipped on import.
    """

    class DesignationType(models.TextChoices):
        FACULTY = 'FACULTY', 'Faculty'
        STAFF = 'STAFF', 'Staff'

    class Status(models.TextChoices):
        ACTIVE = 'Active', 'Active'
        INACTIVE = 'Inactive', 'Inactive'

    emp_id = models.CharField(max_length=32, unique=True, db_index=True)
    name = models.CharField(max_length=150)
    dob = models.DateField(null=True, blank=True)
    designation = models.CharField(max_length=150, blank=True)
    designation_type = models.CharField(max_length=10, choices=DesignationType.choices)
    group_name = models.CharField(max_length=50, blank=True)
    user_type = models.CharField(max_length=50, blank=True)
    department = models.CharField(max_length=150, blank=True)
    sub_department = models.CharField(max_length=150, blank=True)
    academy = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True)
    mobile = models.CharField(max_length=20, blank=True)
    joining_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.ACTIVE
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['emp_id']
        indexes = [
            models.Index(fields=['department']),
            models.Index(fields=['designation_type']),
            models.Index(fields=['group_name']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f'{self.emp_id} — {self.name}'

    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE
