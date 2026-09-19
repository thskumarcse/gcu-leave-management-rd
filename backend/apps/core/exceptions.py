from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    """
    Wrap DRF's default error payloads in the project's {success, message, errors}
    envelope so the frontend can handle auth and validation the same way.
    """
    response = exception_handler(exc, context)
    if response is None:
        return None

    data = response.data
    code = getattr(getattr(exc, 'detail', None), 'code', None)

    if isinstance(data, dict) and 'detail' in data and len(data) <= 2:
        message = str(data['detail'])
        payload = {'success': False, 'message': message}
        if code:
            payload['code'] = code
        response.data = payload
    elif isinstance(data, dict):
        response.data = {
            'success': False,
            'message': 'Request failed.',
            'errors': data,
        }
    elif isinstance(data, list):
        response.data = {
            'success': False,
            'message': str(data[0]) if data else 'Request failed.',
            'errors': data,
        }
    else:
        response.data = {'success': False, 'message': str(data)}

    return response
