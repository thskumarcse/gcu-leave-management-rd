from django.urls import path

from .views import EmployeeDetailView, EmployeeListView, MyEmployeeView

urlpatterns = [
    path('me/', MyEmployeeView.as_view(), name='employee-me'),
    path('', EmployeeListView.as_view(), name='employee-list'),
    path('<str:emp_id>/', EmployeeDetailView.as_view(), name='employee-detail'),
]
