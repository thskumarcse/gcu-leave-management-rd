from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


# Known in-app admins in addition to the VC granted by sync_approvers.
EXTRA_ADMIN_EMP_IDS = ('GCU020057',)


class Command(BaseCommand):
    help = (
        'Configure approval chains (HOD, Approver 1, VC), grant the VC admin '
        'access, and route any unrouted pending leave applications.'
    )

    def handle(self, *args, **options):
        call_command('sync_approvers', route_pending=True)
        for emp_id in EXTRA_ADMIN_EMP_IDS:
            try:
                call_command('grant_admin', emp_id)
            except CommandError as exc:
                self.stdout.write(self.style.WARNING(str(exc)))
