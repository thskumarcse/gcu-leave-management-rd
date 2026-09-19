"""
Root URL configuration.

Everything under /api/v1/ is versioned and defined in config/api_urls.py so
that a future v2 can be added alongside it without touching this file.
"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('config.api_urls')),
]
