from django.urls import path

from .views import (
    LeaveCancelView,
    LeaveDetailView,
    LeaveListCreateView,
    LeaveSummaryView,
    LeaveTypeListView,
)

leave_type_urlpatterns = [
    path('', LeaveTypeListView.as_view(), name='leave-type-list'),
]

urlpatterns = [
    path('', LeaveListCreateView.as_view(), name='leave-list'),
    path('summary/', LeaveSummaryView.as_view(), name='leave-summary'),
    path('<int:pk>/', LeaveDetailView.as_view(), name='leave-detail'),
    path('<int:pk>/cancel/', LeaveCancelView.as_view(), name='leave-cancel'),
]
