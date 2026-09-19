from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Account
from apps.accounts.permissions import PasswordChangeNotRequired
from apps.employees.models import Employee

User = get_user_model()

DEFAULT_PASSWORD = settings.DEFAULT_EMPLOYEE_PASSWORD


def make_employee(**overrides):
    defaults = {
        'emp_id': 'GCU001',
        'name': 'Employee One',
        'dob': '1985-04-12',
        'designation': 'Associate Professor',
        'designation_type': Employee.DesignationType.FACULTY,
        'department': 'CSE',
        'email': 'employee1@gcu.edu',
        'mobile': '9876543210',
        'joining_date': '2016-05-25',
        'status': Employee.Status.ACTIVE,
    }
    defaults.update(overrides)
    return Employee.objects.create(**defaults)


class LoginTests(APITestCase):
    def setUp(self):
        self.employee = make_employee()

    def test_first_login_with_default_password_creates_account(self):
        response = self.client.post(
            '/api/v1/auth/login/',
            {'emp_id': 'GCU001', 'password': DEFAULT_PASSWORD},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertTrue(response.data['data']['user']['must_change_password'])
        self.assertFalse(response.data['data']['user']['is_operator'])
        self.assertFalse(response.data['data']['user']['is_admin'])
        self.assertIn('access', response.data['data'])
        self.assertTrue(Account.objects.filter(employee=self.employee).exists())
        self.assertEqual(User.objects.filter(username='GCU001').count(), 1)

    def test_login_is_case_insensitive_for_emp_id(self):
        response = self.client.post(
            '/api/v1/auth/login/',
            {'emp_id': 'gcu001', 'password': DEFAULT_PASSWORD},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['user']['emp_id'], 'GCU001')

    def test_unknown_emp_id_is_rejected(self):
        response = self.client.post(
            '/api/v1/auth/login/',
            {'emp_id': 'NOPE', 'password': DEFAULT_PASSWORD},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(response.data['success'])

    def test_wrong_password_is_rejected(self):
        self.client.post(
            '/api/v1/auth/login/',
            {'emp_id': 'GCU001', 'password': DEFAULT_PASSWORD},
            format='json',
        )
        response = self.client.post(
            '/api/v1/auth/login/',
            {'emp_id': 'GCU001', 'password': 'not-the-password'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_inactive_employee_cannot_login(self):
        self.employee.status = Employee.Status.INACTIVE
        self.employee.save()
        response = self.client.post(
            '/api/v1/auth/login/',
            {'emp_id': 'GCU001', 'password': DEFAULT_PASSWORD},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data.get('code'), 'employee_inactive')
        self.assertFalse(Account.objects.exists())

    def test_login_does_not_duplicate_accounts(self):
        for _ in range(3):
            self.client.post(
                '/api/v1/auth/login/',
                {'emp_id': 'GCU001', 'password': DEFAULT_PASSWORD},
                format='json',
            )
        self.assertEqual(Account.objects.count(), 1)
        self.assertEqual(User.objects.filter(username='GCU001').count(), 1)


class RefreshTests(APITestCase):
    def setUp(self):
        self.employee = make_employee()
        login = self.client.post(
            '/api/v1/auth/login/',
            {'emp_id': 'GCU001', 'password': DEFAULT_PASSWORD},
            format='json',
        )
        self.access = login.data['data']['access']
        self.refresh = login.data['data']['refresh']

    def test_refresh_works_without_access_token(self):
        response = self.client.post(
            '/api/v1/auth/refresh/',
            {'refresh': self.refresh},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('access', response.data['data'])
        self.assertIn('refresh', response.data['data'])

    def test_refresh_ignores_expired_or_invalid_access_header(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer not-a-valid-access-token')
        response = self.client.post(
            '/api/v1/auth/refresh/',
            {'refresh': self.refresh},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data['data'])
        self.assertIn('refresh', response.data['data'])

    def test_invalid_refresh_is_rejected(self):
        response = self.client.post(
            '/api/v1/auth/refresh/',
            {'refresh': 'not-a-refresh-token'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ChangePasswordTests(APITestCase):
    def setUp(self):
        self.employee = make_employee()
        login = self.client.post(
            '/api/v1/auth/login/',
            {'emp_id': 'GCU001', 'password': DEFAULT_PASSWORD},
            format='json',
        )
        self.access = login.data['data']['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access}')

    def test_me_is_allowed_before_password_change(self):
        response = self.client.get('/api/v1/auth/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['data']['must_change_password'])

    def test_other_endpoints_are_blocked_until_password_changes(self):
        from rest_framework.test import APIRequestFactory, force_authenticate

        factory = APIRequestFactory()
        request = factory.get('/api/v1/auth/me/')
        user = User.objects.get(username='GCU001')
        force_authenticate(request, user=user)
        request.user = user
        with self.assertRaises(Exception) as raised:
            PasswordChangeNotRequired().has_permission(request, None)
        self.assertEqual(raised.exception.default_code, 'password_change_required')

    def test_change_password_then_old_password_fails(self):
        response = self.client.post(
            '/api/v1/auth/change-password/',
            {
                'current_password': DEFAULT_PASSWORD,
                'new_password': 'NewPass#2026',
                'confirm_password': 'NewPass#2026',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['data']['user']['must_change_password'])

        self.client.credentials()
        old = self.client.post(
            '/api/v1/auth/login/',
            {'emp_id': 'GCU001', 'password': DEFAULT_PASSWORD},
            format='json',
        )
        self.assertEqual(old.status_code, status.HTTP_401_UNAUTHORIZED)

        new = self.client.post(
            '/api/v1/auth/login/',
            {'emp_id': 'GCU001', 'password': 'NewPass#2026'},
            format='json',
        )
        self.assertEqual(new.status_code, status.HTTP_200_OK)
        self.assertFalse(new.data['data']['user']['must_change_password'])

    def test_cannot_reuse_default_password(self):
        response = self.client.post(
            '/api/v1/auth/change-password/',
            {
                'current_password': DEFAULT_PASSWORD,
                'new_password': DEFAULT_PASSWORD,
                'confirm_password': DEFAULT_PASSWORD,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_mismatched_confirmation_is_rejected(self):
        response = self.client.post(
            '/api/v1/auth/change-password/',
            {
                'current_password': DEFAULT_PASSWORD,
                'new_password': 'NewPass#2026',
                'confirm_password': 'OtherPass#2026',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_wrong_current_password_is_rejected(self):
        response = self.client.post(
            '/api/v1/auth/change-password/',
            {
                'current_password': 'wrong-password',
                'new_password': 'NewPass#2026',
                'confirm_password': 'NewPass#2026',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
