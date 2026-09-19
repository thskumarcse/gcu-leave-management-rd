from django.core.management.base import BaseCommand, CommandError

from apps.approvals.services import grant_admin
from apps.employees.models import Employee


class Command(BaseCommand):
    help = (
        'Grant in-app admin access (Account.is_admin and Django is_staff) '
        'to an employee by emp_id. Creates the login account if needed.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            'emp_id',
            help='Employee ID, e.g. GCU020057',
        )

    def handle(self, *args, **options):
        emp_id = (options['emp_id'] or '').strip()
        if not emp_id:
            raise CommandError('emp_id is required.')
        try:
            employee = Employee.objects.get(emp_id__iexact=emp_id)
        except Employee.DoesNotExist as exc:
            raise CommandError(
                f'No employee found for emp_id={emp_id}. '
                'Import backend/data/employee.csv first.'
            ) from exc

        account = grant_admin(employee)
        self.stdout.write(self.style.SUCCESS(
            f'Admin access granted to {employee.emp_id} — {employee.name} '
            f'(is_admin={account.is_admin}, is_staff={account.user.is_staff}).'
        ))
