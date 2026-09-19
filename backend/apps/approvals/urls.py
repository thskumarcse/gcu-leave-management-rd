from django.urls import path

from .views import (
    ApprovalDecideView,
    ApprovalDetailView,
    ApprovalEmployeeLeavesView,
    ApprovalInboxView,
    MyApprovalRolesView,
)

urlpatterns = [
    path('', ApprovalInboxView.as_view(), name='approval-inbox'),
    path('roles/', MyApprovalRolesView.as_view(), name='approval-roles'),
    path('<int:pk>/', ApprovalDetailView.as_view(), name='approval-detail'),
    path(
        '<int:pk>/employee-leaves/',
        ApprovalEmployeeLeavesView.as_view(),
        name='approval-employee-leaves',
    ),
    path('<int:pk>/decide/', ApprovalDecideView.as_view(), name='approval-decide'),
]
