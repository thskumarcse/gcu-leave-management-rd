from rest_framework.pagination import PageNumberPagination

from apps.core.responses import ok


class ApprovalPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return ok(
            'Approval inbox.',
            {
                'results': data,
                'count': self.page.paginator.count,
                'page': self.page.number,
                'page_size': self.get_page_size(self.request),
            },
        )


class ApplicantLeavePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

    def nested_payload(self, data):
        return {
            'results': data,
            'count': self.page.paginator.count,
            'page': self.page.number,
            'page_size': self.get_page_size(self.request),
        }
