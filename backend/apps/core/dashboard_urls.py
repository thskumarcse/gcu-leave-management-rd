from django.urls import path

from .dashboard_views import ApproverDashboardView

urlpatterns = [
    path('', ApproverDashboardView.as_view(), name='approver-dashboard'),
]
