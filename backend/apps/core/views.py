from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    GET /api/v1/health/

    Unauthenticated liveness check used by the frontend to confirm it can
    reach the API, and by deployment tooling to confirm the service is up.
    Deliberately returns no sensitive information.
    """
    return Response(
        {
            'success': True,
            'message': 'GCU Leave Management API is running.',
            'data': {
                'status': 'ok',
                'service': 'gcu-leave-management-backend',
                'debug': settings.DEBUG,
            },
        }
    )
