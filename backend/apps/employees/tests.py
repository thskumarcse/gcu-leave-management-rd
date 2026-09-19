import tempfile

from django.conf import settings
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from openpyxl import Workbook

from apps.accounts.models import Account
from apps.employees.models import Employee
from apps.employees.services import import_employees_from_csv, import_employees_from_file


HEADER = (
    'Serial No,emp_id,Name,Department,Group Name,User Type,Designation,'
    'Joining Date,Email ID,Mobile No.,Date of Birth,Sub Department,Academy'
)

ROW_ONE = (
    '1,GCU020041,Bhabajit  Baruah,School Of Engineering and Technology,Faculty,'
    'Regular,Assistant Professor,01-08-2012,bhabajit_me@gcuniversity.ac.in,'
    '-7002128161,06-05-1988,Department of Mechanical Engineering,'
    'Girijananda Chowdhury University'
)
ROW_TWO = (
    '2,GCU010042,ANJAN  DEKA,Administration,Admin,Regular,Administration,'
    '01-02-2023,anjan_adm@gcuniversity.ac.in,-7002098566,03-10-1994,-,'
    'Girijananda Chowdhury University'
)

VALID_CSV = f'{HEADER}\n{ROW_ONE}\n{ROW_TWO}\n'


def write_csv(content):
    tmp = tempfile.NamedTemporaryFile(
        mode='w', suffix='.csv', delete=False, newline='', encoding='utf-8'
    )
    tmp.write(content)
    tmp.close()
    return tmp.name


class ImportEmployeesTests(TestCase):
    def test_imports_new_employees(self):
        report = import_employees_from_csv(write_csv(VALID_CSV))
        self.assertEqual(report.imported, 2)
        self.assertEqual(report.updated, 0)
        self.assertEqual(report.skipped_count, 0)
        self.assertEqual(Employee.objects.count(), 2)
        faculty = Employee.objects.get(emp_id='GCU020041')
        self.assertEqual(faculty.name, 'Bhabajit Baruah')
        self.assertEqual(faculty.designation_type, Employee.DesignationType.FACULTY)
        self.assertEqual(faculty.group_name, 'Faculty')
        self.assertEqual(faculty.mobile, '7002128161')
        self.assertEqual(faculty.dob.isoformat(), '1988-05-06')
        self.assertEqual(faculty.joining_date.isoformat(), '2012-08-01')
        self.assertEqual(faculty.sub_department, 'Department of Mechanical Engineering')
        staff = Employee.objects.get(emp_id='GCU010042')
        self.assertEqual(staff.designation_type, Employee.DesignationType.STAFF)
        self.assertEqual(staff.sub_department, '')

    def test_reimport_updates_designation(self):
        path = write_csv(VALID_CSV)
        import_employees_from_csv(path)
        self.assertEqual(Employee.objects.get(emp_id='GCU020041').designation, 'Assistant Professor')
        updated = VALID_CSV.replace('Assistant Professor', 'VC', 1)
        report = import_employees_from_csv(write_csv(updated))
        self.assertEqual(report.imported, 0)
        self.assertEqual(report.updated, 2)
        self.assertEqual(Employee.objects.get(emp_id='GCU020041').designation, 'VC')
        self.assertEqual(Employee.objects.get(emp_id='GCU010042').designation, 'Administration')

    def test_reimport_updates_not_duplicates(self):
        path = write_csv(VALID_CSV)
        import_employees_from_csv(path)
        report = import_employees_from_csv(path)
        self.assertEqual(report.imported, 0)
        self.assertEqual(report.updated, 2)
        self.assertEqual(Employee.objects.count(), 2)

    def test_optional_dash_fields_are_imported(self):
        csv_text = (
            f'{HEADER}\n'
            '1,GCU099999,Someone Else,Administration,Other Employee,Other Employee,'
            '-, -, -, -, -, Girijananda Chowdhury University\n'
        )
        report = import_employees_from_csv(write_csv(csv_text))
        self.assertEqual(report.imported, 1)
        employee = Employee.objects.get(emp_id='GCU099999')
        self.assertEqual(employee.designation, '')
        self.assertEqual(employee.email, '')
        self.assertEqual(employee.mobile, '')
        self.assertIsNone(employee.dob)
        self.assertIsNone(employee.joining_date)
        self.assertEqual(employee.designation_type, Employee.DesignationType.STAFF)

    def test_system_accounts_are_skipped(self):
        csv_text = (
            f'{VALID_CSV}'
            '3,SYSADMIN,System  Administrator,Administration,Admin,-,-,-,'
            'sambit.kundu@serosoft.in,9.82366E+11,16-08-1990,-,'
            'Girijananda Chowdhury University\n'
        )
        report = import_employees_from_csv(write_csv(csv_text))
        self.assertEqual(report.imported, 2)
        self.assertEqual(report.skipped_count, 1)
        self.assertFalse(Employee.objects.filter(emp_id='SYSADMIN').exists())

    def test_invalid_date_is_skipped(self):
        csv_text = VALID_CSV.replace('06-05-1988', 'not-a-date')
        report = import_employees_from_csv(write_csv(csv_text))
        self.assertEqual(report.skipped_count, 1)
        self.assertFalse(Employee.objects.filter(emp_id='GCU020041').exists())
        self.assertTrue(Employee.objects.filter(emp_id='GCU010042').exists())

    def test_duplicate_emp_id_within_file_is_skipped_once(self):
        csv_text = VALID_CSV + (
            '3,GCU020041,Bhabajit Dup,School Of Engineering and Technology,Faculty,'
            'Regular,Assistant Professor,01-08-2012,dup@gcuniversity.ac.in,'
            '-7002128161,06-05-1988,Department of Mechanical Engineering,'
            'Girijananda Chowdhury University\n'
        )
        report = import_employees_from_csv(write_csv(csv_text))
        self.assertEqual(report.imported, 2)
        self.assertEqual(report.skipped_count, 1)
        self.assertEqual(Employee.objects.filter(emp_id='GCU020041').count(), 1)

    def test_duplicate_emails_are_allowed(self):
        csv_text = (
            f'{HEADER}\n{ROW_ONE}\n'
            '2,GCU020999,Someone Else,School Of Engineering and Technology,Faculty,'
            'Regular,Assistant Professor,01-08-2012,bhabajit_me@gcuniversity.ac.in,'
            '-7002128999,06-05-1988,Department of Mechanical Engineering,'
            'Girijananda Chowdhury University\n'
        )
        report = import_employees_from_csv(write_csv(csv_text))
        self.assertEqual(report.imported, 2)
        self.assertEqual(report.skipped_count, 0)

    def test_never_creates_duplicate_employees(self):
        path = write_csv(VALID_CSV)
        for _ in range(3):
            import_employees_from_csv(path)
        self.assertEqual(Employee.objects.count(), 2)

    def test_deactivate_missing_marks_old_rows_inactive(self):
        import_employees_from_csv(write_csv(VALID_CSV))
        Employee.objects.create(
            emp_id='GCU001',
            name='Old Sample',
            designation_type=Employee.DesignationType.FACULTY,
            status=Employee.Status.ACTIVE,
        )
        report = import_employees_from_csv(write_csv(VALID_CSV), deactivate_missing=True)
        self.assertEqual(report.deactivated, 1)
        self.assertEqual(
            Employee.objects.get(emp_id='GCU001').status,
            Employee.Status.INACTIVE,
        )


def write_xlsx(rows):
    workbook = Workbook()
    sheet = workbook.active
    for row in rows:
        sheet.append(row)
    tmp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
    tmp.close()
    workbook.save(tmp.name)
    return tmp.name


class ImportEmployeesExcelTests(TestCase):
    def test_excel_remaps_and_preserves_missing_designation(self):
        Employee.objects.create(
            emp_id='GCU020004',
            name='Dipankar Saha',
            designation='Registrar',
            designation_type=Employee.DesignationType.STAFF,
            group_name='Admin',
            department='Administration',
            sub_department='',
            email='registrar@gcuniversity.ac.in',
            status=Employee.Status.ACTIVE,
        )
        Employee.objects.create(
            emp_id='GCU010002',
            name='Kandarpa Kumar Das',
            designation='VC',
            designation_type=Employee.DesignationType.STAFF,
            group_name='Admin',
            department='Administration',
            sub_department='',
            email='vc@gcuniversity.ac.in',
            status=Employee.Status.ACTIVE,
        )
        path = write_xlsx([
            ['Sl', 'Employee ID', 'Name', 'Email', 'Type', 'Status', 'Campus', 'School', 'Department'],
            [1, 'GCU020004', 'Dipankar Saha', 'hod_pharmacology@gcuniversity.ac.in',
             'teaching', 'Active', 'GCU', 'School of Pharmaceutical Science',
             'Department of Pharmacology - G'],
            [2, 'GCU099888', 'New Person', 'new_person@gcuniversity.ac.in',
             'administrative', 'Active', 'GCU', '—', '—'],
        ])
        report = import_employees_from_file(path)
        self.assertEqual(report.imported, 1)
        self.assertEqual(report.updated, 1)
        self.assertEqual(report.skipped_count, 0)

        registrar = Employee.objects.get(emp_id='GCU020004')
        self.assertEqual(registrar.designation, 'Registrar')
        self.assertEqual(registrar.email, 'hod_pharmacology@gcuniversity.ac.in')
        self.assertEqual(registrar.department, 'School of Pharmaceutical Science')
        self.assertEqual(registrar.sub_department, 'Department of Pharmacology - G')
        self.assertEqual(registrar.designation_type, Employee.DesignationType.FACULTY)
        self.assertEqual(registrar.group_name, 'Faculty')

        created = Employee.objects.get(emp_id='GCU099888')
        self.assertEqual(created.name, 'New Person')
        self.assertEqual(created.designation, '')
        self.assertEqual(created.designation_type, Employee.DesignationType.STAFF)
        self.assertEqual(created.group_name, 'Admin')
        self.assertEqual(created.department, '')
        self.assertEqual(created.sub_department, '')

        vc = Employee.objects.get(emp_id='GCU010002')
        self.assertEqual(vc.designation, 'VC')
        self.assertEqual(vc.email, 'vc@gcuniversity.ac.in')
        self.assertEqual(Employee.objects.count(), 3)


def make_employee(**overrides):
    defaults = {
        'emp_id': 'GCU020041',
        'name': 'Bhabajit Baruah',
        'dob': '1988-05-06',
        'designation': 'Assistant Professor',
        'designation_type': Employee.DesignationType.FACULTY,
        'group_name': 'Faculty',
        'user_type': 'Regular',
        'department': 'School Of Engineering and Technology',
        'sub_department': 'Department of Mechanical Engineering',
        'academy': 'Girijananda Chowdhury University',
        'email': 'bhabajit_me@gcuniversity.ac.in',
        'mobile': '7002128161',
        'joining_date': '2012-08-01',
        'status': Employee.Status.ACTIVE,
    }
    defaults.update(overrides)
    return Employee.objects.create(**defaults)


class EmployeeApiTests(APITestCase):
    def setUp(self):
        self.faculty = make_employee()
        self.staff = make_employee(
            emp_id='GCU010042',
            name='Anjan Deka',
            email='anjan_adm@gcuniversity.ac.in',
            mobile='7002098566',
            designation='Administration',
            designation_type=Employee.DesignationType.STAFF,
            group_name='Admin',
            department='Administration',
            sub_department='',
            dob='1994-10-03',
            joining_date='2023-02-01',
        )
        self.inactive = make_employee(
            emp_id='GCU099999',
            name='Inactive Person',
            email='inactive@gcu.edu',
            mobile='9000000000',
            status=Employee.Status.INACTIVE,
        )
        login = self.client.post(
            '/api/v1/auth/login/',
            {'emp_id': 'GCU020041', 'password': settings.DEFAULT_EMPLOYEE_PASSWORD},
            format='json',
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["data"]["access"]}')
        self.client.post(
            '/api/v1/auth/change-password/',
            {
                'current_password': settings.DEFAULT_EMPLOYEE_PASSWORD,
                'new_password': 'NewPass#2026',
                'confirm_password': 'NewPass#2026',
            },
            format='json',
        )
        relogin = self.client.post(
            '/api/v1/auth/login/',
            {'emp_id': 'GCU020041', 'password': 'NewPass#2026'},
            format='json',
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {relogin.data["data"]["access"]}')

    def _grant_operator(self):
        account = Account.objects.get(employee=self.faculty)
        account.is_operator = True
        account.save(update_fields=['is_operator', 'updated_at'])

    def test_me_returns_full_master_record(self):
        response = self.client.get('/api/v1/employees/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data['data']
        self.assertEqual(data['emp_id'], 'GCU020041')
        self.assertEqual(data['dob'], '1988-05-06')
        self.assertEqual(data['mobile'], '7002128161')
        self.assertEqual(data['sub_department'], 'Department of Mechanical Engineering')

    def test_faculty_cannot_list_directory(self):
        response = self.client.get('/api/v1/employees/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_directory_omits_dob_and_inactive_rows(self):
        self._grant_operator()
        response = self.client.get('/api/v1/employees/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['data']['results']
        emp_ids = {row['emp_id'] for row in results}
        self.assertEqual(emp_ids, {'GCU020041', 'GCU010042'})
        self.assertNotIn('dob', results[0])
        self.assertNotIn('mobile', results[0])

    def test_directory_search_filters_by_name(self):
        self._grant_operator()
        response = self.client.get('/api/v1/employees/', {'q': 'Anjan'})
        results = response.data['data']['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['emp_id'], 'GCU010042')

    def test_directory_filters_by_sub_department(self):
        self._grant_operator()
        by_unit = self.client.get(
            '/api/v1/employees/',
            {'department': 'Department of Mechanical Engineering', 'page_size': 500},
        )
        self.assertEqual(by_unit.status_code, status.HTTP_200_OK)
        emp_ids = [row['emp_id'] for row in by_unit.data['data']['results']]
        self.assertIn('GCU020041', emp_ids)
        self.assertNotIn('GCU010042', emp_ids)

        by_school = self.client.get(
            '/api/v1/employees/',
            {'department': 'School Of Engineering and Technology', 'page_size': 500},
        )
        self.assertNotIn('GCU020041', [row['emp_id'] for row in by_school.data['data']['results']])

    def test_directory_filters_by_group_name(self):
        self._grant_operator()
        response = self.client.get('/api/v1/employees/', {'group_name': 'Faculty'})
        results = response.data['data']['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['emp_id'], 'GCU020041')

    def test_other_employee_detail_is_hidden_from_faculty(self):
        response = self.client.get('/api/v1/employees/GCU010042/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_other_employee_detail_hides_sensitive_fields(self):
        self._grant_operator()
        response = self.client.get('/api/v1/employees/GCU010042/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('dob', response.data['data'])
        self.assertEqual(response.data['data']['name'], 'Anjan Deka')

    def test_own_detail_includes_sensitive_fields(self):
        response = self.client.get('/api/v1/employees/GCU020041/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['dob'], '1988-05-06')

    def test_inactive_employee_is_hidden_from_others(self):
        response = self.client.get('/api/v1/employees/GCU099999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_directory_is_rejected(self):
        self.client.credentials()
        response = self.client.get('/api/v1/employees/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
