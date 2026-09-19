from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.employees.services import CsvFormatError, import_employees_from_file


class Command(BaseCommand):
    help = (
        'Imports/updates Employee records from a CSV or Excel file (default: '
        'data/employee.csv). Never creates duplicate employees — matches '
        'on emp_id and updates in place if it already exists. Fields that '
        'are not in the file are left unchanged on existing employees.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            dest='file_path',
            default=str(Path(settings.BASE_DIR) / 'data' / 'employee.csv'),
            help='Path to the employee CSV or Excel file (default: data/employee.csv).',
        )

        parser.add_argument(
            '--keep-missing',
            action='store_true',
            help='Do not mark employees missing from this file as Inactive.',
        )

    def handle(self, *args, **options):
        file_path = options['file_path']
        self.stdout.write(f'Importing employees from {file_path} ...')

        try:
            report = import_employees_from_file(
                file_path,
                deactivate_missing=not options['keep_missing'],
            )
        except CsvFormatError as exc:
            raise CommandError(str(exc))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Rows read:      {report.total_rows}'))
        self.stdout.write(self.style.SUCCESS(f'Imported (new): {report.imported}'))
        self.stdout.write(self.style.SUCCESS(f'Updated:        {report.updated}'))
        self.stdout.write(self.style.SUCCESS(f'Deactivated:    {report.deactivated}'))

        if report.skipped:
            self.stdout.write(self.style.WARNING(f'Skipped:        {report.skipped_count}'))
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('Skipped row details:'))
            for issue in report.skipped:
                self.stdout.write(
                    f'  Row {issue.row_number} (emp_id={issue.emp_id}): {issue.reason}'
                )
        else:
            self.stdout.write(self.style.SUCCESS('Skipped:        0'))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Import complete.'))
