from datetime import date, timedelta

from django.conf import settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.approvals.models import ApprovalAction, ApproverAssignment, EmployeeApprover
from apps.approvals.services import (
    HOD_DESIGNATION_RE,
    applicant_is_hod,
    find_approver1,
    find_approver2,
    looks_like_hod,
    route_pending_applications,
)
from apps.employees.models import Employee
from apps.leaves.models import LeaveApplication, LeaveType


def make_employee(**overrides):
    defaults = {
        'emp_id': 'GCU020041',
        'name': 'Bhabajit Baruah',
        'dob': '1988-05-06',
        'designation': 'Assistant Professor',
        'designation_type': Employee.DesignationType.FACULTY,
        'group_name': 'Faculty',
        'department': 'School Of Engineering and Technology',
        'sub_department': 'Department of Mechanical Engineering',
        'email': 'bhabajit_me@gcuniversity.ac.in',
        'mobile': '7002128161',
        'joining_date': '2012-08-01',
        'status': Employee.Status.ACTIVE,
    }
    defaults.update(overrides)
    return Employee.objects.create(**defaults)


def login_as(client, emp_id, password=None):
    password = password or settings.DEFAULT_EMPLOYEE_PASSWORD
    login = client.post(
        '/api/v1/auth/login/',
        {'emp_id': emp_id, 'password': password},
        format='json',
    )
    if login.status_code != 200 and password == settings.DEFAULT_EMPLOYEE_PASSWORD:
        return login_as(client, emp_id, 'NewPass#2026')
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["data"]["access"]}')
    if login.data['data']['user']['must_change_password']:
        client.post(
            '/api/v1/auth/change-password/',
            {
                'current_password': password,
                'new_password': 'NewPass#2026',
                'confirm_password': 'NewPass#2026',
            },
            format='json',
        )
        password = 'NewPass#2026'
        login = client.post(
            '/api/v1/auth/login/',
            {'emp_id': emp_id, 'password': password},
            format='json',
        )
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["data"]["access"]}')
    return password


class FacultyApprovalFlowTests(APITestCase):
    def setUp(self):
        self.faculty = make_employee()
        self.hod = make_employee(
            emp_id='GCU020014',
            name='Debarshi Mallick',
            designation='Associate Professor & HOD',
            email='debarshi_me@gcuniversity.ac.in',
            mobile='7002474854',
        )
        self.vc = make_employee(
            emp_id='GCU090001',
            name='Vice Chancellor',
            designation='Vice-Chancellor',
            designation_type=Employee.DesignationType.STAFF,
            group_name='Admin',
            department='Administration',
            sub_department='',
            email='vc@gcuniversity.ac.in',
            mobile='9000000001',
        )
        self.outsider = make_employee(
            emp_id='GCU020043',
            name='Abhinandan Kalita',
            designation='Assistant Professor',
            sub_department='Department of Electronics & Communication Engineering',
            email='abhinandan_ece@gcuniversity.ac.in',
            mobile='8638552352',
        )
        self.staff = make_employee(
            emp_id='GCU010042',
            name='Anjan Deka',
            designation='Administration',
            designation_type=Employee.DesignationType.STAFF,
            group_name='Admin',
            department='Administration',
            sub_department='',
            email='anjan_adm@gcuniversity.ac.in',
            mobile='7002098566',
        )
        ApproverAssignment.objects.create(
            role=ApproverAssignment.Role.HOD,
            department=self.faculty.department,
            sub_department=self.faculty.sub_department,
            employee=self.hod,
        )
        ApproverAssignment.objects.create(
            role=ApproverAssignment.Role.VC,
            department='',
            sub_department='',
            employee=self.vc,
        )
        self.casual, _ = LeaveType.objects.get_or_create(
            code='CL',
            defaults={
                'name': 'Casual Leave',
                'max_days_per_year': 12,
                'applicable_to': LeaveType.ApplicableTo.ALL,
                'sort_order': 1,
            },
        )
        self.start = date.today() + timedelta(days=14)
        self.end = self.start + timedelta(days=2)

    def _apply_as(self, emp_id):
        login_as(self.client, emp_id)
        return self.client.post(
            '/api/v1/leaves/',
            {
                'leave_type_id': self.casual.id,
                'start_date': self.start.isoformat(),
                'end_date': self.end.isoformat(),
                'reason': 'Family function at home in Guwahati.',
            },
            format='json',
        )

    def test_faculty_apply_waits_on_hod(self):
        response = self._apply_as('GCU020041')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.data['data']
        self.assertEqual(data['status'], 'PENDING')
        self.assertEqual(data['current_step'], 'HOD')
        self.assertEqual(data['waiting_on']['emp_id'], 'GCU020014')
        self.assertTrue(response.data['data']['waiting_on']['name'])

    def test_hod_approve_forwards_to_vc(self):
        created = self._apply_as('GCU020041')
        leave_id = created.data['data']['id']

        login_as(self.client, 'GCU020014')
        inbox = self.client.get('/api/v1/approvals/')
        self.assertEqual(inbox.data['data']['count'], 1)

        decide = self.client.post(
            f'/api/v1/approvals/{leave_id}/decide/',
            {'decision': 'APPROVED'},
            format='json',
        )
        self.assertEqual(decide.status_code, status.HTTP_200_OK)
        self.assertEqual(decide.data['data']['status'], 'PENDING')
        self.assertEqual(decide.data['data']['current_step'], 'VC')
        self.assertEqual(decide.data['data']['waiting_on']['emp_id'], 'GCU090001')

        login_as(self.client, 'GCU020014')
        inbox_after = self.client.get('/api/v1/approvals/')
        self.assertEqual(inbox_after.data['data']['count'], 0)

    def test_vc_approve_completes_application(self):
        created = self._apply_as('GCU020041')
        leave_id = created.data['data']['id']
        login_as(self.client, 'GCU020014')
        self.client.post(
            f'/api/v1/approvals/{leave_id}/decide/',
            {'decision': 'APPROVED'},
            format='json',
        )
        login_as(self.client, 'GCU090001')
        decide = self.client.post(
            f'/api/v1/approvals/{leave_id}/decide/',
            {'decision': 'APPROVED'},
            format='json',
        )
        self.assertEqual(decide.status_code, status.HTTP_200_OK)
        self.assertEqual(decide.data['data']['status'], 'APPROVED')
        self.assertEqual(decide.data['data']['current_step'], '')
        self.assertIsNone(decide.data['data']['waiting_on'])
        self.assertEqual(
            ApprovalAction.objects.filter(application_id=leave_id).count(), 2
        )

    def test_hod_reject_requires_remarks_and_stops_chain(self):
        created = self._apply_as('GCU020041')
        leave_id = created.data['data']['id']
        login_as(self.client, 'GCU020014')
        missing = self.client.post(
            f'/api/v1/approvals/{leave_id}/decide/',
            {'decision': 'REJECTED'},
            format='json',
        )
        self.assertEqual(missing.status_code, status.HTTP_400_BAD_REQUEST)

        rejected = self.client.post(
            f'/api/v1/approvals/{leave_id}/decide/',
            {'decision': 'REJECTED', 'remarks': 'Department coverage is too thin that week.'},
            format='json',
        )
        self.assertEqual(rejected.status_code, status.HTTP_200_OK)
        self.assertEqual(rejected.data['data']['status'], 'REJECTED')
        login_as(self.client, 'GCU090001')
        inbox = self.client.get('/api/v1/approvals/')
        self.assertEqual(inbox.data['data']['count'], 0)

    def test_outsider_cannot_decide(self):
        created = self._apply_as('GCU020041')
        leave_id = created.data['data']['id']
        login_as(self.client, 'GCU020043')
        response = self.client.post(
            f'/api/v1/approvals/{leave_id}/decide/',
            {'decision': 'APPROVED'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            LeaveApplication.objects.get(pk=leave_id).current_step, 'HOD'
        )

    def test_hod_applying_skips_self_and_goes_to_vc(self):
        response = self._apply_as('GCU020014')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['data']['status'], 'PENDING')
        self.assertEqual(response.data['data']['current_step'], 'VC')
        self.assertNotEqual(response.data['data']['current_step'], 'APPROVER_1')
        self.assertEqual(response.data['data']['waiting_on']['emp_id'], 'GCU090001')
        self.assertTrue(applicant_is_hod(self.hod))

        leave_id = response.data['data']['id']
        login_as(self.client, 'GCU090001')
        decide = self.client.post(
            f'/api/v1/approvals/{leave_id}/decide/',
            {'decision': 'APPROVED'},
            format='json',
        )
        self.assertEqual(decide.status_code, status.HTTP_200_OK)
        self.assertEqual(decide.data['data']['status'], 'APPROVED')
        self.assertEqual(
            ApprovalAction.objects.filter(application_id=leave_id).count(), 1
        )

    def test_hod_in_designation_goes_to_vc_only(self):
        titles = (
            'Associate Professor & HOD',
            'Professor & HOD',
            'HOD',
        )
        for index, title in enumerate(titles, start=1):
            with self.subTest(designation=title):
                self.assertIsNotNone(HOD_DESIGNATION_RE.search(title))
                emp = make_employee(
                    emp_id=f'GCU02005{index}',
                    name=f'Titled Head {index}',
                    designation=title,
                    email=f'titled_head_{index}@gcuniversity.ac.in',
                    mobile=f'700200005{index}',
                )
                self.assertTrue(looks_like_hod(emp))
                self.assertTrue(applicant_is_hod(emp))
                self.assertFalse(
                    ApproverAssignment.objects.filter(
                        employee=emp,
                        role=ApproverAssignment.Role.HOD,
                    ).exists()
                )
                response = self._apply_as(emp.emp_id)
                self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                data = response.data['data']
                self.assertEqual(data['status'], 'PENDING')
                self.assertEqual(data['current_step'], 'VC')
                self.assertEqual(data['waiting_on']['emp_id'], 'GCU090001')
                self.assertNotEqual(data['current_step'], 'HOD')
                self.assertNotEqual(data['current_step'], 'APPROVER_1')
                self.assertNotEqual(data['waiting_on']['emp_id'], 'GCU020014')

    def test_route_pending_reroutes_hod_title_waiting_on_hod_to_vc(self):
        titled_hod = make_employee(
            emp_id='GCU020054',
            name='Misrouted Head',
            designation='Associate Professor & HOD',
            email='misrouted_head@gcuniversity.ac.in',
            mobile='7002000054',
        )
        misrouted = LeaveApplication.objects.create(
            employee=titled_hod,
            leave_type=self.casual,
            start_date=self.start,
            end_date=self.end,
            days=3,
            reason='Imported pending leave still waiting on department HOD.',
            status=LeaveApplication.Status.PENDING,
            chain_type=LeaveApplication.ChainType.FACULTY,
            current_step=LeaveApplication.Step.HOD,
            waiting_on=self.hod,
        )
        regular = LeaveApplication.objects.create(
            employee=self.faculty,
            leave_type=self.casual,
            start_date=self.start + timedelta(days=10),
            end_date=self.end + timedelta(days=10),
            days=3,
            reason='Regular faculty leave correctly waiting on HOD.',
            status=LeaveApplication.Status.PENDING,
            chain_type=LeaveApplication.ChainType.FACULTY,
            current_step=LeaveApplication.Step.HOD,
            waiting_on=self.hod,
        )

        routed = route_pending_applications(notify=False)
        self.assertGreaterEqual(routed, 1)

        misrouted.refresh_from_db()
        regular.refresh_from_db()
        self.assertEqual(misrouted.current_step, LeaveApplication.Step.VC)
        self.assertEqual(misrouted.waiting_on_id, self.vc.id)
        self.assertEqual(regular.current_step, LeaveApplication.Step.HOD)
        self.assertEqual(regular.waiting_on_id, self.hod.id)

    def test_staff_without_approver1_goes_to_vc(self):
        response = self._apply_as('GCU010042')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['data']['status'], 'PENDING')
        self.assertEqual(response.data['data']['chain_type'], 'STAFF')
        self.assertEqual(response.data['data']['current_step'], 'VC')
        self.assertEqual(response.data['data']['waiting_on']['emp_id'], 'GCU090001')

    def test_staff_apply_waits_on_approver1(self):
        approver = make_employee(
            emp_id='GCU010010',
            name='Staff Approver',
            designation='Office Superintendent',
            designation_type=Employee.DesignationType.STAFF,
            group_name='Admin',
            department='Administration',
            sub_department='',
            email='staff_approver@gcuniversity.ac.in',
            mobile='7002000010',
        )
        ApproverAssignment.objects.create(
            role=ApproverAssignment.Role.APPROVER_1,
            department=self.staff.department,
            sub_department='',
            employee=approver,
        )
        response = self._apply_as('GCU010042')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.data['data']
        self.assertEqual(data['chain_type'], 'STAFF')
        self.assertEqual(data['current_step'], 'APPROVER_1')
        self.assertEqual(data['waiting_on']['emp_id'], 'GCU010010')

        login_as(self.client, 'GCU010010')
        decide = self.client.post(
            f'/api/v1/approvals/{data["id"]}/decide/',
            {'decision': 'APPROVED'},
            format='json',
        )
        self.assertEqual(decide.status_code, status.HTTP_200_OK)
        self.assertEqual(decide.data['data']['current_step'], 'VC')
        self.assertEqual(decide.data['data']['waiting_on']['emp_id'], 'GCU090001')

    def test_login_payload_includes_hod_role(self):
        login_as(self.client, 'GCU020014')
        me = self.client.get('/api/v1/auth/me/')
        self.assertTrue(me.data['data']['is_hod'])
        self.assertFalse(me.data['data']['is_vc'])
        self.assertGreaterEqual(me.data['data']['inbox_count'], 0)

    def test_hod_sees_applicant_leave_usage_not_own(self):
        year = date.today().year
        earned, _ = LeaveType.objects.get_or_create(
            code='EL',
            defaults={
                'name': 'Earned Leave',
                'max_days_per_year': 30,
                'applicable_to': LeaveType.ApplicableTo.ALL,
                'sort_order': 2,
            },
        )
        LeaveType.objects.get_or_create(
            code='ML',
            defaults={
                'name': 'Medical Leave',
                'max_days_per_year': 15,
                'applicable_to': LeaveType.ApplicableTo.ALL,
                'sort_order': 3,
            },
        )
        LeaveApplication.objects.create(
            employee=self.faculty,
            leave_type=self.casual,
            start_date=date(year, 1, 6),
            end_date=date(year, 1, 7),
            days=2,
            reason='Earlier approved casual leave.',
            status=LeaveApplication.Status.APPROVED,
            requested_on=date(year, 1, 2),
        )
        LeaveApplication.objects.create(
            employee=self.faculty,
            leave_type=earned,
            start_date=date(year, 3, 10),
            end_date=date(year, 3, 14),
            days=5,
            reason='Earned leave taken in March.',
            status=LeaveApplication.Status.APPROVED,
            requested_on=date(year, 3, 1),
        )
        created = self._apply_as('GCU020041')
        leave_id = created.data['data']['id']

        login_as(self.client, 'GCU020014')
        response = self.client.get(f'/api/v1/approvals/{leave_id}/employee-leaves/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data['data']
        self.assertTrue(response.data['success'])
        self.assertEqual(data['year'], year)
        balances = {item['code']: item for item in data['balances']}
        self.assertIn('CL', balances)
        self.assertIn('EL', balances)
        self.assertIn('ML', balances)
        self.assertEqual(balances['CL']['used'], 5)
        self.assertEqual(balances['CL']['remaining'], 7)
        self.assertEqual(balances['CL']['max_days_per_year'], 12)
        self.assertEqual(balances['EL']['used'], 5)
        ids = {item['id'] for item in data['leaves']['results']}
        self.assertIn(leave_id, ids)
        self.assertGreaterEqual(data['leaves']['count'], 3)
        self.assertNotIn(
            'GCU020014',
            {item.get('employee', {}).get('emp_id') for item in data['leaves']['results']},
        )

        paged = self.client.get(
            f'/api/v1/approvals/{leave_id}/employee-leaves/',
            {'page_size': 1, 'page': 1},
        )
        self.assertEqual(len(paged.data['data']['leaves']['results']), 1)
        self.assertGreaterEqual(paged.data['data']['leaves']['count'], 3)

    def test_outsider_and_applicant_cannot_read_employee_leaves(self):
        created = self._apply_as('GCU020041')
        leave_id = created.data['data']['id']

        login_as(self.client, 'GCU020043')
        outsider = self.client.get(f'/api/v1/approvals/{leave_id}/employee-leaves/')
        self.assertEqual(outsider.status_code, status.HTTP_404_NOT_FOUND)

        login_as(self.client, 'GCU020041')
        applicant = self.client.get(f'/api/v1/approvals/{leave_id}/employee-leaves/')
        self.assertEqual(applicant.status_code, status.HTTP_404_NOT_FOUND)

        self.client.credentials()
        anonymous = self.client.get(f'/api/v1/approvals/{leave_id}/employee-leaves/')
        self.assertEqual(anonymous.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_vc_sees_applicant_leaves_after_hod_forwards(self):
        created = self._apply_as('GCU020041')
        leave_id = created.data['data']['id']
        login_as(self.client, 'GCU020014')
        self.client.post(
            f'/api/v1/approvals/{leave_id}/decide/',
            {'decision': 'APPROVED'},
            format='json',
        )
        hod_after = self.client.get(f'/api/v1/approvals/{leave_id}/employee-leaves/')
        self.assertEqual(hod_after.status_code, status.HTTP_404_NOT_FOUND)

        login_as(self.client, 'GCU090001')
        vc = self.client.get(f'/api/v1/approvals/{leave_id}/employee-leaves/')
        self.assertEqual(vc.status_code, status.HTTP_200_OK)
        codes = {item['code'] for item in vc.data['data']['balances']}
        self.assertIn('CL', codes)
        self.assertEqual(vc.data['data']['leaves']['results'][0]['id'], leave_id)


class StaffApprover2FlowTests(APITestCase):
    def setUp(self):
        self.staff = make_employee(
            emp_id='GCU010042',
            name='Anjan Deka',
            designation='Administration',
            designation_type=Employee.DesignationType.STAFF,
            group_name='Admin',
            department='Administration',
            sub_department='',
            email='anjan_adm@gcuniversity.ac.in',
            mobile='7002098566',
        )
        self.approver1 = make_employee(
            emp_id='GCU010010',
            name='Staff Approver One',
            designation='Office Superintendent',
            designation_type=Employee.DesignationType.STAFF,
            group_name='Admin',
            department='Administration',
            sub_department='',
            email='staff_approver1@gcuniversity.ac.in',
            mobile='7002000010',
        )
        self.approver2 = make_employee(
            emp_id='GCU010020',
            name='Staff Approver Two',
            designation='Deputy Registrar',
            designation_type=Employee.DesignationType.STAFF,
            group_name='Admin',
            department='Administration',
            sub_department='',
            email='staff_approver2@gcuniversity.ac.in',
            mobile='7002000020',
        )
        self.other_a1 = make_employee(
            emp_id='GCU010005',
            name='Earlier Approver One',
            designation='Section Officer',
            designation_type=Employee.DesignationType.STAFF,
            group_name='Admin',
            department='Administration',
            sub_department='',
            email='staff_approver1b@gcuniversity.ac.in',
            mobile='7002000005',
        )
        self.vc = make_employee(
            emp_id='GCU090001',
            name='Vice Chancellor',
            designation='Vice-Chancellor',
            designation_type=Employee.DesignationType.STAFF,
            group_name='Admin',
            department='Administration',
            sub_department='',
            email='vc@gcuniversity.ac.in',
            mobile='9000000001',
        )
        ApproverAssignment.objects.create(
            role=ApproverAssignment.Role.VC,
            department='',
            sub_department='',
            employee=self.vc,
        )
        self.casual, _ = LeaveType.objects.get_or_create(
            code='CL',
            defaults={
                'name': 'Casual Leave',
                'max_days_per_year': 12,
                'applicable_to': LeaveType.ApplicableTo.ALL,
                'sort_order': 1,
            },
        )
        self.start = date.today() + timedelta(days=14)
        self.end = self.start + timedelta(days=2)

    def _apply_as(self, emp_id):
        login_as(self.client, emp_id)
        return self.client.post(
            '/api/v1/leaves/',
            {
                'leave_type_id': self.casual.id,
                'start_date': self.start.isoformat(),
                'end_date': self.end.isoformat(),
                'reason': 'Family function at home in Guwahati.',
            },
            format='json',
        )

    def test_staff_with_approver2_goes_a1_then_a2_then_vc(self):
        ApproverAssignment.objects.create(
            role=ApproverAssignment.Role.APPROVER_1,
            department=self.staff.department,
            sub_department='',
            employee=self.approver1,
        )
        ApproverAssignment.objects.create(
            role=ApproverAssignment.Role.APPROVER_2,
            department=self.staff.department,
            sub_department='',
            employee=self.approver2,
        )
        created = self._apply_as('GCU010042')
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        data = created.data['data']
        self.assertEqual(data['current_step'], 'APPROVER_1')
        self.assertEqual(data['waiting_on']['emp_id'], 'GCU010010')

        login_as(self.client, 'GCU010010')
        decide_a1 = self.client.post(
            f'/api/v1/approvals/{data["id"]}/decide/',
            {'decision': 'APPROVED'},
            format='json',
        )
        self.assertEqual(decide_a1.status_code, status.HTTP_200_OK)
        self.assertEqual(decide_a1.data['data']['current_step'], 'APPROVER_2')
        self.assertEqual(decide_a1.data['data']['waiting_on']['emp_id'], 'GCU010020')

        login_as(self.client, 'GCU010020')
        decide_a2 = self.client.post(
            f'/api/v1/approvals/{data["id"]}/decide/',
            {'decision': 'APPROVED'},
            format='json',
        )
        self.assertEqual(decide_a2.status_code, status.HTTP_200_OK)
        self.assertEqual(decide_a2.data['data']['current_step'], 'VC')
        self.assertEqual(decide_a2.data['data']['waiting_on']['emp_id'], 'GCU090001')

    def test_approver1_and_approver2_see_applicant_leave_usage(self):
        ApproverAssignment.objects.create(
            role=ApproverAssignment.Role.APPROVER_1,
            department=self.staff.department,
            sub_department='',
            employee=self.approver1,
        )
        ApproverAssignment.objects.create(
            role=ApproverAssignment.Role.APPROVER_2,
            department=self.staff.department,
            sub_department='',
            employee=self.approver2,
        )
        created = self._apply_as('GCU010042')
        leave_id = created.data['data']['id']

        login_as(self.client, 'GCU010010')
        a1 = self.client.get(f'/api/v1/approvals/{leave_id}/employee-leaves/')
        self.assertEqual(a1.status_code, status.HTTP_200_OK)
        self.assertIn('CL', {item['code'] for item in a1.data['data']['balances']})
        self.assertEqual(a1.data['data']['leaves']['count'], 1)

        self.client.post(
            f'/api/v1/approvals/{leave_id}/decide/',
            {'decision': 'APPROVED'},
            format='json',
        )
        a1_after = self.client.get(f'/api/v1/approvals/{leave_id}/employee-leaves/')
        self.assertEqual(a1_after.status_code, status.HTTP_404_NOT_FOUND)

        login_as(self.client, 'GCU010020')
        a2 = self.client.get(f'/api/v1/approvals/{leave_id}/employee-leaves/')
        self.assertEqual(a2.status_code, status.HTTP_200_OK)
        self.assertEqual(a2.data['data']['leaves']['results'][0]['id'], leave_id)

    def test_staff_without_approver2_still_goes_to_vc(self):
        ApproverAssignment.objects.create(
            role=ApproverAssignment.Role.APPROVER_1,
            department=self.staff.department,
            sub_department='',
            employee=self.approver1,
        )
        created = self._apply_as('GCU010042')
        login_as(self.client, 'GCU010010')
        decide = self.client.post(
            f'/api/v1/approvals/{created.data["data"]["id"]}/decide/',
            {'decision': 'APPROVED'},
            format='json',
        )
        self.assertEqual(decide.data['data']['current_step'], 'VC')

    def test_multiple_approver1_picks_lowest_emp_id_not_applicant(self):
        ApproverAssignment.objects.create(
            role=ApproverAssignment.Role.APPROVER_1,
            department=self.staff.department,
            sub_department='',
            employee=self.approver1,
        )
        ApproverAssignment.objects.create(
            role=ApproverAssignment.Role.APPROVER_1,
            department=self.staff.department,
            sub_department='',
            employee=self.other_a1,
        )
        created = self._apply_as('GCU010042')
        self.assertEqual(created.data['data']['waiting_on']['emp_id'], 'GCU010005')

        as_self = self._apply_as('GCU010005')
        self.assertEqual(as_self.data['data']['waiting_on']['emp_id'], 'GCU010010')

    def test_login_payload_includes_approver2_role(self):
        ApproverAssignment.objects.create(
            role=ApproverAssignment.Role.APPROVER_2,
            department=self.approver2.department,
            sub_department='',
            employee=self.approver2,
        )
        login_as(self.client, 'GCU010020')
        me = self.client.get('/api/v1/auth/me/')
        self.assertTrue(me.data['data']['is_approver'])
        self.assertIn('APPROVER_2', me.data['data']['roles'])


class PersonalStaffApproverTests(APITestCase):
    def setUp(self):
        self.staff = make_employee(
            emp_id='GCU010042',
            name='Anjan Deka',
            designation='Administration',
            designation_type=Employee.DesignationType.STAFF,
            group_name='Admin',
            department='Administration',
            sub_department='',
            email='anjan_adm@gcuniversity.ac.in',
            mobile='7002098566',
        )
        self.colleague = make_employee(
            emp_id='GCU010043',
            name='Colleague Staff',
            designation='Administration',
            designation_type=Employee.DesignationType.STAFF,
            group_name='Admin',
            department='Administration',
            sub_department='',
            email='colleague_adm@gcuniversity.ac.in',
            mobile='7002098567',
        )
        self.personal_a1 = make_employee(
            emp_id='GCU010010',
            name='Personal Approver One',
            designation='Office Superintendent',
            designation_type=Employee.DesignationType.STAFF,
            group_name='Admin',
            department='Administration',
            sub_department='',
            email='personal_a1@gcuniversity.ac.in',
            mobile='7002000010',
        )
        self.personal_a2 = make_employee(
            emp_id='GCU010020',
            name='Personal Approver Two',
            designation='Deputy Registrar',
            designation_type=Employee.DesignationType.STAFF,
            group_name='Admin',
            department='Administration',
            sub_department='',
            email='personal_a2@gcuniversity.ac.in',
            mobile='7002000020',
        )
        self.dept_a1 = make_employee(
            emp_id='GCU010005',
            name='Department Approver One',
            designation='Section Officer',
            designation_type=Employee.DesignationType.STAFF,
            group_name='Admin',
            department='Administration',
            sub_department='',
            email='dept_a1@gcuniversity.ac.in',
            mobile='7002000005',
        )
        self.dept_a2 = make_employee(
            emp_id='GCU010006',
            name='Department Approver Two',
            designation='Section Officer',
            designation_type=Employee.DesignationType.STAFF,
            group_name='Admin',
            department='Administration',
            sub_department='',
            email='dept_a2@gcuniversity.ac.in',
            mobile='7002000006',
        )
        self.vc = make_employee(
            emp_id='GCU090001',
            name='Vice Chancellor',
            designation='Vice-Chancellor',
            designation_type=Employee.DesignationType.STAFF,
            group_name='Admin',
            department='Administration',
            sub_department='',
            email='vc@gcuniversity.ac.in',
            mobile='9000000001',
        )
        ApproverAssignment.objects.create(
            role=ApproverAssignment.Role.VC,
            department='',
            sub_department='',
            employee=self.vc,
        )
        ApproverAssignment.objects.create(
            role=ApproverAssignment.Role.APPROVER_1,
            department='Administration',
            sub_department='',
            employee=self.dept_a1,
        )
        ApproverAssignment.objects.create(
            role=ApproverAssignment.Role.APPROVER_2,
            department='Administration',
            sub_department='',
            employee=self.dept_a2,
        )
        self.casual, _ = LeaveType.objects.get_or_create(
            code='CL',
            defaults={
                'name': 'Casual Leave',
                'max_days_per_year': 12,
                'applicable_to': LeaveType.ApplicableTo.ALL,
                'sort_order': 1,
            },
        )
        self.start = date.today() + timedelta(days=14)
        self.end = self.start + timedelta(days=2)

    def _apply_as(self, emp_id):
        login_as(self.client, emp_id)
        return self.client.post(
            '/api/v1/leaves/',
            {
                'leave_type_id': self.casual.id,
                'start_date': self.start.isoformat(),
                'end_date': self.end.isoformat(),
                'reason': 'Family function at home in Guwahati.',
            },
            format='json',
        )

    def test_personal_mapping_beats_department_and_does_not_change_colleague(self):
        EmployeeApprover.objects.create(
            employee=self.staff,
            approver_1=self.personal_a1,
            approver_2=self.personal_a2,
        )
        self.assertEqual(find_approver1(self.staff).emp_id, self.personal_a1.emp_id)
        self.assertEqual(find_approver2(self.staff).emp_id, self.personal_a2.emp_id)
        self.assertEqual(find_approver1(self.colleague).emp_id, self.dept_a1.emp_id)
        self.assertEqual(find_approver2(self.colleague).emp_id, self.dept_a2.emp_id)

        created = self._apply_as('GCU010042')
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        data = created.data['data']
        self.assertEqual(data['current_step'], 'APPROVER_1')
        self.assertEqual(data['waiting_on']['emp_id'], self.personal_a1.emp_id)

        login_as(self.client, self.personal_a1.emp_id)
        decide_a1 = self.client.post(
            f'/api/v1/approvals/{data["id"]}/decide/',
            {'decision': 'APPROVED'},
            format='json',
        )
        self.assertEqual(decide_a1.status_code, status.HTTP_200_OK)
        self.assertEqual(decide_a1.data['data']['current_step'], 'APPROVER_2')
        self.assertEqual(decide_a1.data['data']['waiting_on']['emp_id'], self.personal_a2.emp_id)

        login_as(self.client, self.personal_a2.emp_id)
        decide_a2 = self.client.post(
            f'/api/v1/approvals/{data["id"]}/decide/',
            {'decision': 'APPROVED'},
            format='json',
        )
        self.assertEqual(decide_a2.data['data']['current_step'], 'VC')

        other = self._apply_as(self.colleague.emp_id)
        self.assertEqual(other.data['data']['waiting_on']['emp_id'], self.dept_a1.emp_id)

    def test_personal_row_without_a2_does_not_fall_back_to_department(self):
        EmployeeApprover.objects.create(
            employee=self.staff,
            approver_1=self.personal_a1,
            approver_2=None,
        )
        self.assertEqual(find_approver1(self.staff).emp_id, self.personal_a1.emp_id)
        self.assertIsNone(find_approver2(self.staff))

        created = self._apply_as('GCU010042')
        login_as(self.client, self.personal_a1.emp_id)
        decide = self.client.post(
            f'/api/v1/approvals/{created.data["data"]["id"]}/decide/',
            {'decision': 'APPROVED'},
            format='json',
        )
        self.assertEqual(decide.data['data']['current_step'], 'VC')

    def test_personal_approver_gets_role_on_login(self):
        EmployeeApprover.objects.create(
            employee=self.staff,
            approver_1=self.personal_a1,
            approver_2=self.personal_a2,
        )
        login_as(self.client, self.personal_a1.emp_id)
        me = self.client.get('/api/v1/auth/me/')
        self.assertTrue(me.data['data']['is_approver'])
        self.assertIn('APPROVER_1', me.data['data']['roles'])

    def test_staff_hod_by_designation_goes_to_vc_not_personal_a1(self):
        staff_hod = make_employee(
            emp_id='GCU010099',
            name='Staff Head',
            designation='HOD Administration',
            designation_type=Employee.DesignationType.STAFF,
            group_name='Admin',
            department='Administration',
            sub_department='',
            email='staff_hod@gcuniversity.ac.in',
            mobile='7002000099',
        )
        EmployeeApprover.objects.create(
            employee=staff_hod,
            approver_1=self.personal_a1,
            approver_2=self.personal_a2,
        )
        self.assertTrue(applicant_is_hod(staff_hod))
        self.assertEqual(find_approver1(staff_hod).emp_id, self.personal_a1.emp_id)

        created = self._apply_as(staff_hod.emp_id)
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        data = created.data['data']
        self.assertEqual(data['chain_type'], 'STAFF')
        self.assertEqual(data['current_step'], 'VC')
        self.assertEqual(data['waiting_on']['emp_id'], self.vc.emp_id)
        self.assertNotEqual(data['current_step'], 'APPROVER_1')

        colleague = self._apply_as(self.staff.emp_id)
        self.assertEqual(colleague.data['data']['current_step'], 'APPROVER_1')

    def test_professor_and_hod_with_personal_a1_a2_goes_to_vc_not_approver_2(self):
        self.assertIsNotNone(HOD_DESIGNATION_RE.search('Professor & HOD'))
        titled_hod = make_employee(
            emp_id='GCU020112',
            name='Minakshi Gogoi Test',
            designation='Professor & HOD',
            designation_type=Employee.DesignationType.STAFF,
            group_name='Admin',
            department='School Of Engineering and Technology',
            sub_department='Department of Computer Science and Engineering',
            email='minakshi_hod_test@gcuniversity.ac.in',
            mobile='7002000112',
        )
        EmployeeApprover.objects.create(
            employee=titled_hod,
            approver_1=self.personal_a1,
            approver_2=self.personal_a2,
        )
        self.assertTrue(looks_like_hod(titled_hod))
        self.assertTrue(applicant_is_hod(titled_hod))
        self.assertEqual(find_approver1(titled_hod).emp_id, self.personal_a1.emp_id)
        self.assertEqual(find_approver2(titled_hod).emp_id, self.personal_a2.emp_id)

        created = self._apply_as(titled_hod.emp_id)
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        data = created.data['data']
        self.assertEqual(data['status'], 'PENDING')
        self.assertEqual(data['current_step'], 'VC')
        self.assertEqual(data['waiting_on']['emp_id'], self.vc.emp_id)
        self.assertNotEqual(data['current_step'], 'APPROVER_1')
        self.assertNotEqual(data['current_step'], 'APPROVER_2')
        self.assertNotEqual(data['waiting_on']['emp_id'], self.personal_a2.emp_id)

    def test_staff_hod_assignment_goes_to_vc_without_hod_in_title(self):
        assigned_hod = make_employee(
            emp_id='GCU010088',
            name='Assigned Head',
            designation='Administration',
            designation_type=Employee.DesignationType.STAFF,
            group_name='Admin',
            department='Administration',
            sub_department='',
            email='assigned_hod@gcuniversity.ac.in',
            mobile='7002000088',
        )
        ApproverAssignment.objects.create(
            role=ApproverAssignment.Role.HOD,
            department=assigned_hod.department,
            sub_department='',
            employee=assigned_hod,
        )
        EmployeeApprover.objects.create(
            employee=assigned_hod,
            approver_1=self.personal_a1,
            approver_2=self.personal_a2,
        )
        self.assertTrue(applicant_is_hod(assigned_hod))
        created = self._apply_as(assigned_hod.emp_id)
        self.assertEqual(created.data['data']['current_step'], 'VC')
        self.assertEqual(created.data['data']['waiting_on']['emp_id'], self.vc.emp_id)

    def test_hod_as_personal_a1_still_approves_others(self):
        hod_approver = make_employee(
            emp_id='GCU010077',
            name='HOD Who Approves Staff',
            designation='Associate Professor & HOD',
            designation_type=Employee.DesignationType.STAFF,
            group_name='Admin',
            department='Administration',
            sub_department='',
            email='hod_as_a1@gcuniversity.ac.in',
            mobile='7002000077',
        )
        EmployeeApprover.objects.create(
            employee=self.staff,
            approver_1=hod_approver,
            approver_2=self.personal_a2,
        )
        created = self._apply_as(self.staff.emp_id)
        self.assertEqual(created.data['data']['current_step'], 'APPROVER_1')
        self.assertEqual(created.data['data']['waiting_on']['emp_id'], hod_approver.emp_id)

    def test_route_pending_reroutes_hod_waiting_on_a1_to_vc(self):
        staff_hod = make_employee(
            emp_id='GCU010066',
            name='Pending Staff HOD',
            designation='HOD Administration',
            designation_type=Employee.DesignationType.STAFF,
            group_name='Admin',
            department='Administration',
            sub_department='',
            email='pending_hod@gcuniversity.ac.in',
            mobile='7002000066',
        )
        misrouted = LeaveApplication.objects.create(
            employee=staff_hod,
            leave_type=self.casual,
            start_date=self.start,
            end_date=self.end,
            days=3,
            reason='Imported pending leave still waiting on Approver 1.',
            status=LeaveApplication.Status.PENDING,
            chain_type=LeaveApplication.ChainType.STAFF,
            current_step=LeaveApplication.Step.APPROVER_1,
            waiting_on=self.personal_a1,
        )
        unrouted = LeaveApplication.objects.create(
            employee=staff_hod,
            leave_type=self.casual,
            start_date=self.start + timedelta(days=10),
            end_date=self.end + timedelta(days=10),
            days=3,
            reason='Imported pending leave with no approver yet.',
            status=LeaveApplication.Status.PENDING,
            chain_type=LeaveApplication.ChainType.NONE,
            current_step='',
            waiting_on=None,
        )
        regular = LeaveApplication.objects.create(
            employee=self.staff,
            leave_type=self.casual,
            start_date=self.start + timedelta(days=20),
            end_date=self.end + timedelta(days=20),
            days=3,
            reason='Regular staff leave correctly waiting on Approver 1.',
            status=LeaveApplication.Status.PENDING,
            chain_type=LeaveApplication.ChainType.STAFF,
            current_step=LeaveApplication.Step.APPROVER_1,
            waiting_on=self.personal_a1,
        )

        routed = route_pending_applications(notify=False)
        self.assertGreaterEqual(routed, 2)

        misrouted.refresh_from_db()
        unrouted.refresh_from_db()
        regular.refresh_from_db()
        self.assertEqual(misrouted.status, LeaveApplication.Status.PENDING)
        self.assertEqual(misrouted.current_step, LeaveApplication.Step.VC)
        self.assertEqual(misrouted.waiting_on_id, self.vc.id)
        self.assertEqual(unrouted.current_step, LeaveApplication.Step.VC)
        self.assertEqual(unrouted.waiting_on_id, self.vc.id)
        self.assertEqual(regular.current_step, LeaveApplication.Step.APPROVER_1)
        self.assertEqual(regular.waiting_on_id, self.personal_a1.id)
