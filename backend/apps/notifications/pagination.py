from rest_framework.pagination import PageNumberPagination

from apps.core.responses import ok


class NotificationPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 50

    def get_paginated_response(self, data):
        return ok(
            'Notifications.',
            {
                'results': data,
                'count': self.page.paginator.count,
                'page': self.page.number,
                'page_size': self.get_page_size(self.request),
            },
        )
