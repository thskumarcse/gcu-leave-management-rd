"""
Import the university Employee Leave Report (SpreadsheetML .xls) from data/.
"""
import datetime
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

from apps.employees.models import Employee

from .models import LeaveApplication, LeaveType
from .services import count_leave_days

SS = '{urn:schemas-microsoft-com:office:spreadsheet}'

REQUIRED_HEADERS = [
    'Serial No.',
    'Employee ID',
    'Name',
    'Location',
    'Leave Type',
    'Request Date',
    'From Date',
    'To Date',
    'Status',
]

DATE_FORMATS = ('%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d')

LEAVE_TYPE_CATALOG = {
    'casual leave': {
        'code': 'CL',
        'name': 'Casual Leave',
        'max_days_per_year': 12,
        'sort_order': 1,
        'description': 'Short personal leave for unforeseen needs.',
    },
    'earned leave': {
        'code': 'EL',
        'name': 'Earned Leave',
        'max_days_per_year': 30,
        'sort_order': 2,
        'description': 'Privilege leave earned through service.',
    },
    'sick leave': {
        'code': 'ML',
        'name': 'Sick Leave',
        'max_days_per_year': 15,
        'sort_order': 3,
        'requires_document': True,
        'description': 'Leave on medical grounds.',
    },
    'medical leave': {
        'code': 'ML',
        'name': 'Sick Leave',
        'max_days_per_year': 15,
        'sort_order': 3,
        'requires_document': True,
        'description': 'Leave on medical grounds.',
    },
    'duty leave': {
        'code': 'DL',
        'name': 'Duty Leave',
        'max_days_per_year': None,
        'sort_order': 4,
        'description': 'Official duty assigned by the university.',
    },
    'duty leave assigned by the university': {
        'code': 'DL',
        'name': 'Duty Leave',
        'max_days_per_year': None,
        'sort_order': 4,
        'description': 'Official duty assigned by the university.',
    },
    'vacation leave': {
        'code': 'VL',
        'name': 'Vacation Leave',
        'max_days_per_year': None,
        'sort_order': 6,
        'description': 'Vacation leave as notified by the university.',
    },
    'leave without pay': {
        'code': 'LWP',
        'name': 'Leave Without Pay',
        'max_days_per_year': None,
        'sort_order': 7,
        'description': 'Unpaid leave.',
    },
    'paternity leave': {
        'code': 'PL',
        'name': 'Paternity Leave',
        'max_days_per_year': None,
        'sort_order': 8,
        'requires_document': True,
        'description': 'Paternity leave.',
    },
    'maternity leave': {
        'code': 'MAT',
        'name': 'Maternity Leave',
        'max_days_per_year': None,
        'sort_order': 9,
        'requires_document': True,
        'description': 'Maternity leave.',
    },
    'extraordinary leave': {
        'code': 'EOL',
        'name': 'Extraordinary Leave',
        'max_days_per_year': None,
        'sort_order': 10,
        'description': 'Extraordinary leave.',
    },
    'special leave': {
        'code': 'SPL',
        'name': 'Special Leave',
        'max_days_per_year': None,
        'sort_order': 11,
        'description': 'Special leave.',
    },
}

STATUS_MAP = {
    'approved': LeaveApplication.Status.APPROVED,
    'rejected': LeaveApplication.Status.REJECTED,
    'pending': LeaveApplication.Status.PENDING,
    'withdrawn': LeaveApplication.Status.CANCELLED,
    'cancelled': LeaveApplication.Status.CANCELLED,
    'partially cancelled': LeaveApplication.Status.APPROVED,
}


class LeaveImportError(Exception):
    """Raised when the leave report itself is unusable."""


@dataclass
class RowIssue:
    row_number: int
    emp_id: str
    reason: str


@dataclass
class LeaveImportReport:
    total_rows: int = 0
    imported: int = 0
    updated: int = 0
    skipped: list = field(default_factory=list)
    routed_pending: int = 0

    @property
    def skipped_count(self):
        return len(self.skipped)


def _cell_text(cell):
    data = cell.find(f'{SS}Data')
    if data is None or data.text is None:
        return ''
    return data.text.strip()


def _row_values(row, width=10):
    values = [''] * width
    col = 1
    for cell in row.findall(f'{SS}Cell'):
        index = cell.get(f'{SS}Index')
        if index:
            col = int(index)
        if 1 <= col <= width:
            values[col - 1] = _cell_text(cell)
        col += 1
    return values


def _parse_date(value, field_name):
    value = (value or '').strip()
    if not value or value in {'-', '--'}:
        raise ValueError(f'{field_name} is missing.')
    for fmt in DATE_FORMATS:
        try:
            return datetime.datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError(f'{field_name} "{value}" is not a valid date.')


def _iter_data_rows(file_path):
    tree = ET.parse(file_path)
    table = tree.find(f'.//{SS}Worksheet/{SS}Table')
    if table is None:
        raise LeaveImportError('The leave report has no worksheet table.')
    rows = table.findall(f'{SS}Row')
    if not rows:
        raise LeaveImportError('The leave report is empty.')
    header = _row_values(rows[0])
    for index, expected in enumerate(REQUIRED_HEADERS):
        actual = header[index] if index < len(header) else ''
        if actual.strip().lower() != expected.lower():
            raise LeaveImportError(
                f'Expected column {index + 1} to be "{expected}", found "{actual}".'
            )
    for offset, row in enumerate(rows[1:], start=2):
        yield offset, _row_values(row)


def ensure_leave_types():
    by_code = {}
    for spec in LEAVE_TYPE_CATALOG.values():
        leave_type, _ = LeaveType.objects.update_or_create(
            code=spec['code'],
            defaults={
                'name': spec['name'],
                'description': spec.get('description', ''),
                'max_days_per_year': spec.get('max_days_per_year'),
                'requires_document': spec.get('requires_document', False),
                'sort_order': spec['sort_order'],
                'is_active': True,
                'applicable_to': LeaveType.ApplicableTo.ALL,
            },
        )
        by_code[spec['code']] = leave_type
    return by_code


def resolve_leave_type(name, by_code):
    spec = LEAVE_TYPE_CATALOG.get((name or '').strip().lower())
    if not spec:
        return None
    return by_code[spec['code']]


def map_status(raw_status):
    return STATUS_MAP.get((raw_status or '').strip().lower())


def external_key(emp_id, leave_type_name, requested_on, start_date, end_date, raw_status):
    return '|'.join([
        emp_id.strip().upper(),
        (leave_type_name or '').strip().lower(),
        requested_on.isoformat(),
        start_date.isoformat(),
        end_date.isoformat(),
        (raw_status or '').strip().lower(),
    ])


def _chain_type(employee):
    if employee.designation_type == Employee.DesignationType.FACULTY:
        return LeaveApplication.ChainType.FACULTY
    if employee.designation_type == Employee.DesignationType.STAFF:
        return LeaveApplication.ChainType.STAFF
    return LeaveApplication.ChainType.NONE


def _reason(raw_status):
    label = (raw_status or '').strip() or 'unknown'
    return f'Imported from the university leave report (original status: {label}).'


def import_emp_leaves(file_path, route_pending=True):
    path = Path(file_path)
    if not path.exists():
        raise LeaveImportError(f'Leave report not found: {path}')

    report = LeaveImportReport()
    type_by_code = ensure_leave_types()
    employees = {emp.emp_id.upper(): emp for emp in Employee.objects.all()}
    existing = {
        app.external_key: app
        for app in LeaveApplication.objects.filter(
            source=LeaveApplication.Source.IMPORTED
        ).prefetch_related('approval_actions')
        if app.external_key
    }
    pending_ids = []

    for row_number, values in _iter_data_rows(path):
        report.total_rows += 1
        emp_id = (values[1] or '').strip()
        leave_type_name = (values[4] or '').strip()
        raw_status = (values[8] or '').strip()

        if not any(values):
            report.skipped.append(RowIssue(row_number, emp_id, 'Empty row.'))
            continue
        if not emp_id:
            report.skipped.append(RowIssue(row_number, emp_id, 'Employee ID is blank.'))
            continue
        employee = employees.get(emp_id.upper())
        if employee is None:
            report.skipped.append(
                RowIssue(row_number, emp_id, 'No matching employee master record.')
            )
            continue
        leave_type = resolve_leave_type(leave_type_name, type_by_code)
        if leave_type is None:
            report.skipped.append(
                RowIssue(row_number, emp_id, f'Unknown leave type "{leave_type_name}".')
            )
            continue
        status = map_status(raw_status)
        if status is None:
            report.skipped.append(
                RowIssue(row_number, emp_id, f'Unknown status "{raw_status}".')
            )
            continue
        try:
            requested_on = _parse_date(values[5], 'Request Date')
            start_date = _parse_date(values[6], 'From Date')
            end_date = _parse_date(values[7], 'To Date')
            days = count_leave_days(start_date, end_date)
        except Exception as exc:
            report.skipped.append(RowIssue(row_number, emp_id, str(exc)))
            continue

        key = external_key(
            emp_id, leave_type_name, requested_on, start_date, end_date, raw_status
        )
        fields = {
            'employee': employee,
            'leave_type': leave_type,
            'start_date': start_date,
            'end_date': end_date,
            'days': days,
            'reason': _reason(raw_status),
            'requested_on': requested_on,
            'status': status,
            'session': LeaveApplication.Session.FULL_DAY,
            'source': LeaveApplication.Source.IMPORTED,
            'external_key': key,
            'chain_type': _chain_type(employee),
        }

        current = existing.get(key)
        if current is None:
            application = LeaveApplication.objects.create(**fields)
            existing[key] = application
            report.imported += 1
            if status == LeaveApplication.Status.PENDING:
                pending_ids.append(application.id)
            continue

        if current.approval_actions.exists():
            report.skipped.append(
                RowIssue(row_number, emp_id, 'Already processed in this system; left unchanged.')
            )
            continue

        for name, value in fields.items():
            setattr(current, name, value)
        if status != LeaveApplication.Status.PENDING:
            current.current_step = ''
            current.waiting_on = None
        current.save()
        report.updated += 1
        if status == LeaveApplication.Status.PENDING:
            pending_ids.append(current.id)

    if route_pending and pending_ids:
        from apps.approvals.services import route_new_application

        for application in LeaveApplication.objects.filter(pk__in=pending_ids):
            route_new_application(application, notify=False)
            report.routed_pending += 1

    return report
