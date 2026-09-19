from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.leaves.import_services import LeaveImportError, import_emp_leaves


class Command(BaseCommand):
    help = (
        'Imports historical leave applications from the university Employee '
        'Leave Report (default: data/emp_leaves.xls). Matches employees by '
        'emp_id and does not duplicate rows already imported.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            dest='file_path',
            default=str(Path(settings.BASE_DIR) / 'data' / 'emp_leaves.xls'),
            help='Path to the leave report (default: data/emp_leaves.xls).',
        )
        parser.add_argument(
            '--skip-routing',
            action='store_true',
            help='Do not place imported pending rows onto the HOD / VC chain.',
        )

    def handle(self, *args, **options):
        file_path = options['file_path']
        self.stdout.write(f'Importing leave report from {file_path} ...')
        try:
            report = import_emp_leaves(
                file_path,
                route_pending=not options['skip_routing'],
            )
        except LeaveImportError as exc:
            raise CommandError(str(exc))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Rows read:         {report.total_rows}'))
        self.stdout.write(self.style.SUCCESS(f'Imported (new):    {report.imported}'))
        self.stdout.write(self.style.SUCCESS(f'Updated:           {report.updated}'))
        self.stdout.write(self.style.SUCCESS(f'Pending routed:    {report.routed_pending}'))

        if report.skipped:
            self.stdout.write(self.style.WARNING(f'Skipped:           {report.skipped_count}'))
            self.stdout.write('')
            preview = report.skipped[:30]
            for issue in preview:
                self.stdout.write(
                    f'  Row {issue.row_number} (emp_id={issue.emp_id}): {issue.reason}'
                )
            remaining = report.skipped_count - len(preview)
            if remaining > 0:
                self.stdout.write(self.style.WARNING(f'  ... and {remaining} more skipped row(s).'))
        else:
            self.stdout.write(self.style.SUCCESS('Skipped:           0'))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Leave import complete.'))
