from django.urls import path

from .views import ChangePasswordView, LoginView, LogoutView, MeView, RefreshView

urlpatterns = [
    path('login/', LoginView.as_view(), name='auth-login'),
    path('change-password/', ChangePasswordView.as_view(), name='auth-change-password'),
    path('me/', MeView.as_view(), name='auth-me'),
    path('refresh/', RefreshView.as_view(), name='auth-refresh'),
    path('logout/', LogoutView.as_view(), name='auth-logout'),
]
