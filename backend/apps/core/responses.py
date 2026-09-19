from rest_framework.response import Response


def ok(message, data=None, status=200):
    body = {'success': True, 'message': message}
    if data is not None:
        body['data'] = data
    return Response(body, status=status)


def fail(message, errors=None, status=400, code=None):
    body = {'success': False, 'message': message}
    if errors is not None:
        body['errors'] = errors
    if code is not None:
        body['code'] = code
    return Response(body, status=status)
