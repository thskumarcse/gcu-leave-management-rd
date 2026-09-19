from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.responses import fail, ok

from .serializers import ChangePasswordSerializer, LoginSerializer, LogoutSerializer
from .services import AuthError, login_with_emp_id
from .tokens import issue_tokens, serialize_account


class LoginView(APIView):
    # Do not JWT-authenticate login: a leftover expired access token in
    # Authorization would 401 before the password is checked.
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            account = login_with_emp_id(
                serializer.validated_data['emp_id'],
                serializer.validated_data['password'],
            )
        except AuthError as exc:
            return fail(exc.message, status=exc.status, code=exc.code)

        data = {
            **issue_tokens(account.user),
            'user': serialize_account(account),
        }
        message = (
            'Signed in. Please set a new password before continuing.'
            if account.must_change_password
            else 'Signed in.'
        )
        return ok(message, data)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        account = getattr(request.user, 'account', None)
        if account is None:
            return fail('This account cannot change password here.', status=403)

        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        if not request.user.check_password(serializer.validated_data['current_password']):
            return fail(
                'Current password is incorrect.',
                errors={'current_password': ['Current password is incorrect.']},
                status=400,
            )

        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save(update_fields=['password'])
        account.must_change_password = False
        account.save(update_fields=['must_change_password', 'updated_at'])

        data = {
            **issue_tokens(request.user),
            'user': serialize_account(account),
        }
        return ok('Password updated. You can now use the system.', data)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        account = getattr(request.user, 'account', None)
        if account is None:
            return fail('No employee account is linked to this user.', status=404)
        return ok('Current user.', serialize_account(account))


class RefreshView(APIView):
    # Refresh is public and authenticated only by the refresh token in the
    # body. Default JWTAuthentication would 401 on an expired access Bearer
    # before this view ran — which is exactly when the client needs refresh.
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = TokenRefreshSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as exc:
            # Return 401 ourselves: DRF coerces AuthenticationFailed to 403
            # when authentication_classes is empty (no WWW-Authenticate).
            return fail(str(exc), status=401)
        return ok('Token refreshed.', serializer.validated_data)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        raw = serializer.validated_data.get('refresh')
        if raw:
            try:
                RefreshToken(raw).blacklist()
            except TokenError:
                pass
        return ok('Signed out.')
