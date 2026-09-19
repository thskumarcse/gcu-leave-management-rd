from datetime import date, timedelta

from django.conf import settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.employees.models import Employee
from apps.leaves.models import LeaveApplication, LeaveType
from apps.approvals.models import ApproverAssignment


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


class LeaveApiTests(APITestCase):
    def setUp(self):
        self.employee = make_employee()
        self.casual, _ = LeaveType.objects.get_or_create(
            code='CL',
            defaults={
                'name': 'Casual Leave',
                'max_days_per_year': 12,
                'applicable_to': LeaveType.ApplicableTo.ALL,
                'sort_order': 1,
            },
        )
        self.faculty_only = LeaveType.objects.create(
            name='Faculty Special Leave',
            code='FSL',
            applicable_to=LeaveType.ApplicableTo.FACULTY,
            sort_order=2,
        )
        self.staff_only = LeaveType.objects.create(
            name='Staff Special Leave',
            code='SSL',
            applicable_to=LeaveType.ApplicableTo.STAFF,
            sort_order=3,
        )
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
        ApproverAssignment.objects.create(
            role=ApproverAssignment.Role.HOD,
            department=self.employee.department,
            sub_department=self.employee.sub_department,
            employee=self.hod,
        )
        ApproverAssignment.objects.create(
            role=ApproverAssignment.Role.VC,
            employee=self.vc,
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
        self.start = date.today() + timedelta(days=14)
        self.end = self.start + timedelta(days=2)

    def _apply(self, **overrides):
        payload = {
            'leave_type_id': self.casual.id,
            'start_date': self.start.isoformat(),
            'end_date': self.end.isoformat(),
            'reason': 'Family function at home in Guwahati.',
        }
        payload.update(overrides)
        return self.client.post('/api/v1/leaves/', payload, format='json')

    def test_leave_types_exclude_other_role(self):
        response = self.client.get('/api/v1/leave-types/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        codes = {item['code'] for item in response.data['data']}
        self.assertIn('CL', codes)
        self.assertIn('FSL', codes)
        self.assertNotIn('SSL', codes)

    def test_apply_leave_creates_pending_application(self):
        response = self._apply()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['data']['status'], 'PENDING')
        self.assertEqual(response.data['data']['days'], 3)
        self.assertEqual(response.data['data']['session'], 'FULL_DAY')
        self.assertEqual(response.data['data']['requested_on'], date.today().isoformat())
        self.assertEqual(response.data['data']['current_step'], 'HOD')
        self.assertEqual(response.data['data']['waiting_on']['emp_id'], 'GCU020014')
        self.assertEqual(LeaveApplication.objects.count(), 1)

    def test_overlap_is_rejected(self):
        self._apply()
        response = self._apply(
            start_date=(self.start + timedelta(days=1)).isoformat(),
            end_date=(self.end + timedelta(days=1)).isoformat(),
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(LeaveApplication.objects.count(), 1)

    def test_end_before_start_is_rejected(self):
        response = self._apply(
            start_date=self.end.isoformat(),
            end_date=self.start.isoformat(),
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_balance_is_enforced(self):
        response = self._apply(
            end_date=(self.start + timedelta(days=20)).isoformat(),
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_is_limited_to_own_applications(self):
        other = make_employee(
            emp_id='GCU010042',
            name='Anjan Deka',
            email='anjan_adm@gcuniversity.ac.in',
            designation_type=Employee.DesignationType.STAFF,
        )
        self._apply()
        LeaveApplication.objects.create(
            employee=other,
            leave_type=self.casual,
            start_date=self.start,
            end_date=self.end,
            days=3,
            reason='Other employee leave',
            status=LeaveApplication.Status.PENDING,
        )
        response = self.client.get('/api/v1/leaves/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['count'], 1)

    def test_cancel_pending_leave(self):
        created = self._apply()
        leave_id = created.data['data']['id']
        response = self.client.post(f'/api/v1/leaves/{leave_id}/cancel/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['status'], 'CANCELLED')

    def test_cannot_cancel_approved_leave(self):
        created = self._apply()
        leave_id = created.data['data']['id']
        LeaveApplication.objects.filter(pk=leave_id).update(
            status=LeaveApplication.Status.APPROVED
        )
        response = self.client.post(f'/api/v1/leaves/{leave_id}/cancel/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_summary_counts_recent_applications(self):
        self._apply()
        response = self.client.get('/api/v1/leaves/summary/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['pending'], 1)
        self.assertEqual(len(response.data['data']['recent']), 1)
        codes = {item['code'] for item in response.data['data']['balances']}
        self.assertIn('CL', codes)

    def test_casual_first_half_is_half_day(self):
        response = self._apply(
            start_date=self.start.isoformat(),
            end_date=self.start.isoformat(),
            session='FIRST_HALF',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['data']['days'], 0.5)
        self.assertEqual(response.data['data']['session'], 'FIRST_HALF')
        self.assertEqual(response.data['data']['requested_on'], date.today().isoformat())

    def test_casual_second_half_can_share_day_with_first_half(self):
        first = self._apply(
            start_date=self.start.isoformat(),
            end_date=self.start.isoformat(),
            session='FIRST_HALF',
        )
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        second = self._apply(
            start_date=self.start.isoformat(),
            end_date=self.start.isoformat(),
            session='SECOND_HALF',
            reason='Need the afternoon off as well for the same event.',
        )
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        self.assertEqual(LeaveApplication.objects.count(), 2)

    def test_two_first_halves_on_same_day_are_rejected(self):
        self._apply(
            start_date=self.start.isoformat(),
            end_date=self.start.isoformat(),
            session='FIRST_HALF',
        )
        response = self._apply(
            start_date=self.start.isoformat(),
            end_date=self.start.isoformat(),
            session='FIRST_HALF',
            reason='Trying to book the same morning twice.',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
