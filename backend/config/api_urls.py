"""
/api/v1/ route aggregator.

Each app owns its own urls.py; this file only wires them together under
their URL prefixes. Add one `path(...)` line per app as each phase
introduces it — nothing else in this file should need to change.
"""
from django.urls import include, path

from apps.leaves.urls import leave_type_urlpatterns

urlpatterns = [
    path('', include('apps.core.urls')),
    path('auth/', include('apps.accounts.urls')),
    path('employees/', include('apps.employees.urls')),
    path('leave-types/', include((leave_type_urlpatterns, 'leave-types'))),
    path('leaves/', include('apps.leaves.urls')),
    path('approvals/', include('apps.approvals.urls')),
    path('notifications/', include('apps.notifications.urls')),
    path('dashboard/', include('apps.core.dashboard_urls')),
    path('admin/', include('apps.core.admin_urls')),
]
