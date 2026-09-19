from django.core.management.base import BaseCommand, CommandError

from apps.approvals.services import (
    ApprovalError,
    assign_vc,
    grant_admin,
    resolve_vc_employee,
    route_pending_applications,
    sync_approver1_assignments,
    sync_hod_assignments,
)


class Command(BaseCommand):
    help = (
        'Assign HODs, staff Approver 1s, and the Vice-Chancellor used in the '
        'leave approval chains. Approver 2 is not auto-created; assign it in Settings.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--vc',
            dest='vc_emp_id',
            default='',
            help='Employee ID to assign as Vice-Chancellor (overrides VC_EMP_ID).',
        )
        parser.add_argument(
            '--route-pending',
            action='store_true',
            help='Place existing unrouted pending applications onto the approval chain.',
        )

    def handle(self, *args, **options):
        hod_report = sync_hod_assignments()
        self.stdout.write(self.style.SUCCESS(
            f"HOD assignments: {hod_report['hod_count']} "
            f"(new {hod_report['created']}, updated {hod_report['updated']}, "
            f"removed {hod_report['removed']})"
        ))
        for note in hod_report['skipped']:
            self.stdout.write(self.style.WARNING(f'  {note}'))

        staff_report = sync_approver1_assignments()
        self.stdout.write(self.style.SUCCESS(
            f"Approver 1 assignments: {staff_report['approver_count']} "
            f"(new {staff_report['created']}, updated {staff_report['updated']}, "
            f"removed {staff_report['removed']})"
        ))

        try:
            vc_employee = resolve_vc_employee(options['vc_emp_id'] or None)
        except ApprovalError as exc:
            raise CommandError(str(exc))

        if vc_employee:
            assign_vc(vc_employee)
            grant_admin(vc_employee)
            self.stdout.write(self.style.SUCCESS(
                f'VC: {vc_employee.emp_id} - {vc_employee.name}'
            ))
            self.stdout.write(self.style.SUCCESS(
                f'Admin access granted to {vc_employee.emp_id}.'
            ))
        else:
            self.stdout.write(self.style.WARNING(
                'VC: not set. Pass --vc EMP_ID or set VC_EMP_ID.'
            ))

        if options['route_pending']:
            routed = route_pending_applications(notify=False)
            self.stdout.write(self.style.SUCCESS(
                f'Routed {routed} pending application(s).'
            ))
