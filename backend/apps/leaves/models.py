from django.db import models


class LeaveType(models.Model):
    class ApplicableTo(models.TextChoices):
        ALL = 'ALL', 'All employees'
        FACULTY = 'FACULTY', 'Faculty'
        STAFF = 'STAFF', 'Staff'

    name = models.CharField(max_length=80)
    code = models.CharField(max_length=20, unique=True)
    description = models.CharField(max_length=255, blank=True)
    max_days_per_year = models.PositiveIntegerField(null=True, blank=True)
    applicable_to = models.CharField(
        max_length=10, choices=ApplicableTo.choices, default=ApplicableTo.ALL
    )
    requires_document = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'name']

    def __str__(self):
        return f'{self.code} — {self.name}'


class LeaveApplication(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        CANCELLED = 'CANCELLED', 'Cancelled'

    class ChainType(models.TextChoices):
        FACULTY = 'FACULTY', 'Faculty (HOD → VC)'
        STAFF = 'STAFF', 'Staff (Approver 1 → Approver 2 → VC)'
        NONE = 'NONE', 'Unrouted'

    class Step(models.TextChoices):
        HOD = 'HOD', 'Head of Department'
        APPROVER_1 = 'APPROVER_1', 'Approver 1'
        APPROVER_2 = 'APPROVER_2', 'Approver 2'
        VC = 'VC', 'Vice-Chancellor'

    class Source(models.TextChoices):
        INTERNAL = 'INTERNAL', 'Applied in this system'
        IMPORTED = 'IMPORTED', 'Imported from university report'
        ASSIGNED = 'ASSIGNED', 'Sanctioned by administration'

    class Session(models.TextChoices):
        FULL_DAY = 'FULL_DAY', 'Full day'
        FIRST_HALF = 'FIRST_HALF', 'First Half'
        SECOND_HALF = 'SECOND_HALF', 'Second Half'

    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='leave_applications',
    )
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.PROTECT,
        related_name='applications',
    )
    start_date = models.DateField()
    end_date = models.DateField()
    days = models.DecimalField(max_digits=6, decimal_places=1)
    session = models.CharField(
        max_length=12,
        choices=Session.choices,
        default=Session.FULL_DAY,
    )
    reason = models.TextField()
    requested_on = models.DateField(null=True, blank=True, db_index=True)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    chain_type = models.CharField(
        max_length=10, choices=ChainType.choices, default=ChainType.NONE, blank=True
    )
    current_step = models.CharField(max_length=20, blank=True, db_index=True)
    waiting_on = models.ForeignKey(
        'employees.Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='leave_approvals_waiting',
    )
    source = models.CharField(
        max_length=12,
        choices=Source.choices,
        default=Source.INTERNAL,
        db_index=True,
    )
    external_key = models.CharField(max_length=191, unique=True, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-requested_on', '-created_at']
        indexes = [
            models.Index(fields=['employee', 'status']),
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['status', 'waiting_on']),
            models.Index(fields=['source']),
        ]

    def __str__(self):
        return f'{self.employee.emp_id} {self.leave_type.code} {self.start_date}'


class LeaveCredit(models.Model):
    """Extra yearly entitlement granted by an operator or admin."""

    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='leave_credits',
    )
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.PROTECT,
        related_name='credits',
    )
    year = models.PositiveSmallIntegerField()
    days = models.DecimalField(max_digits=6, decimal_places=1)
    baseline_used = models.DecimalField(max_digits=6, decimal_places=1, default=0)
    reason = models.CharField(max_length=255, blank=True)
    granted_by = models.ForeignKey(
        'employees.Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='granted_leave_credits',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['employee', 'leave_type', 'year']),
        ]

    def __str__(self):
        return f'{self.employee.emp_id} {self.leave_type.code} +{self.days} ({self.year})'
