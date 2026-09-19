from django.db import models
from django.db.models import Q


class ApproverAssignment(models.Model):
    """
    Who signs off leave for a unit.

    Faculty: HOD (matched on department / sub-department) then VC.
    Staff: personal EmployeeApprover first, then this department-level
    Approver 1 / Approver 2, then VC.
    HOD applicants (faculty or staff) skip to VC only.
    HOD stays one per department / sub-department.
    """

    class Role(models.TextChoices):
        HOD = 'HOD', 'Head of Department'
        APPROVER_1 = 'APPROVER_1', 'Approver 1'
        APPROVER_2 = 'APPROVER_2', 'Approver 2'
        VC = 'VC', 'Vice-Chancellor'

    STAFF_ROLES = (Role.APPROVER_1, Role.APPROVER_2)

    role = models.CharField(max_length=20, choices=Role.choices)
    department = models.CharField(max_length=150, blank=True)
    sub_department = models.CharField(max_length=150, blank=True)
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='approver_assignments',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['role', 'department', 'sub_department']
        constraints = [
            models.UniqueConstraint(
                fields=['role', 'department', 'sub_department'],
                condition=Q(role='HOD'),
                name='uniq_hod_role_unit',
            ),
            models.UniqueConstraint(
                fields=['role'],
                condition=Q(role='VC'),
                name='uniq_vc_role',
            ),
            models.UniqueConstraint(
                fields=['role', 'employee', 'department'],
                condition=Q(role__in=['APPROVER_1', 'APPROVER_2']),
                name='uniq_staff_approver_role_employee_dept',
            ),
        ]
        indexes = [
            models.Index(fields=['role']),
            models.Index(fields=['employee']),
            models.Index(fields=['department', 'sub_department']),
        ]

    def __str__(self):
        unit = self.sub_department or self.department or 'University'
        return f'{self.role} · {unit} · {self.employee.emp_id}'


class EmployeeApprover(models.Model):
    """
    Per-employee staff approval chain. One row per subject employee.
    Staff routing uses this before falling back to department ApproverAssignment.
    """

    employee = models.OneToOneField(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='personal_approver_map',
    )
    approver_1 = models.ForeignKey(
        'employees.Employee',
        on_delete=models.PROTECT,
        related_name='as_personal_approver_1',
        null=True,
        blank=True,
    )
    approver_2 = models.ForeignKey(
        'employees.Employee',
        on_delete=models.PROTECT,
        related_name='as_personal_approver_2',
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['employee__emp_id']
        indexes = [
            models.Index(fields=['approver_1']),
            models.Index(fields=['approver_2']),
        ]

    def __str__(self):
        a1 = self.approver_1.emp_id if self.approver_1_id else '—'
        a2 = self.approver_2.emp_id if self.approver_2_id else '—'
        return f'{self.employee.emp_id} · A1 {a1} · A2 {a2}'


class ApprovalAction(models.Model):
    class Decision(models.TextChoices):
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'

    class Step(models.TextChoices):
        HOD = 'HOD', 'Head of Department'
        APPROVER_1 = 'APPROVER_1', 'Approver 1'
        APPROVER_2 = 'APPROVER_2', 'Approver 2'
        VC = 'VC', 'Vice-Chancellor'

    application = models.ForeignKey(
        'leaves.LeaveApplication',
        on_delete=models.CASCADE,
        related_name='approval_actions',
    )
    step = models.CharField(max_length=20, choices=Step.choices)
    actor = models.ForeignKey(
        'employees.Employee',
        on_delete=models.PROTECT,
        related_name='approval_actions',
    )
    decision = models.CharField(max_length=10, choices=Decision.choices)
    remarks = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['application', 'created_at']),
        ]

    def __str__(self):
        return f'{self.application_id} {self.step} {self.decision}'
