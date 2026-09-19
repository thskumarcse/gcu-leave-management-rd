from rest_framework.pagination import PageNumberPagination

from apps.core.responses import ok


class EmployeePagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 500

    def get_paginated_response(self, data):
        return ok(
            'Employees.',
            {
                'results': data,
                'count': self.page.paginator.count,
                'page': self.page.number,
                'page_size': self.get_page_size(self.request),
            },
        )
