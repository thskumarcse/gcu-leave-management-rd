"""
Django settings for the GCU Leave Management backend.

Phase 1 scope: Django + DRF + CORS + SQLite + a health-check endpoint.
Settings that later phases need (JWT lifetimes, etc.) are included now so
this file doesn't need restructuring later, but the apps that use them
(accounts, employees, leaves, approvals, notifications) are added to
INSTALLED_APPS only when their phase introduces them.
"""

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Loads backend/.env if present. In production, real environment variables
# (set by the host/process manager) take precedence over anything here.
load_dotenv(BASE_DIR / '.env')


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ('1', 'true', 'yes', 'on')


def env_list(name, default=''):
    value = os.environ.get(name, default)
    return [item.strip() for item in value.split(',') if item.strip()]


# SECURITY WARNING: keep the secret key used in production secret!
# Falls back to a clearly-fake dev-only key so `runserver` works out of the
# box after `git clone`, but production must set SECRET_KEY explicitly.
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-dev-only-change-me')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env_bool('DEBUG', default=True)

ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', 'localhost,127.0.0.1')


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    # Local apps — added phase by phase.
    'apps.core',
    'apps.employees',
    'apps.accounts',
    'apps.leaves',
    'apps.approvals',
    'apps.notifications',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/stable/ref/settings/#databases
#
# SQLite for local development. DATABASE_URL is read here so switching to
# PostgreSQL later is a config change, not a code change — wire up
# dj-database-url (or django-environ) when that migration happens.

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/stable/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# Internationalization
# https://docs.djangoproject.com/en/stable/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/stable/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Django REST Framework
# Global defaults; individual views/viewsets override permission_classes
# where a stricter or looser rule is needed (e.g. AllowAny on /health/).

REST_FRAMEWORK = {
    'EXCEPTION_HANDLER': 'apps.core.exceptions.api_exception_handler',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
        'apps.accounts.permissions.PasswordChangeNotRequired',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ) if not DEBUG else (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ),
}

# Wired up fully in Phase 3 when accounts/auth is built.
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}


# CORS
# https://github.com/adamchainz/django-cors-headers
#
# Origins are environment-driven so local dev (Vite on :5173) and any future
# deployed frontend can both be configured without touching code.

CORS_ALLOWED_ORIGINS = env_list(
    'CORS_ALLOWED_ORIGINS',
    'http://localhost:5173,http://127.0.0.1:5173',
)
CORS_ALLOW_CREDENTIALS = True

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = 'same-origin'

CSRF_TRUSTED_ORIGINS = env_list(
    'CSRF_TRUSTED_ORIGINS',
    ''
)

# First-login password for every employee ID. Accounts are not registered —
# they are created on first successful login, and must_change_password stays
# true until the employee sets their own password.
DEFAULT_EMPLOYEE_PASSWORD = os.environ.get('DEFAULT_EMPLOYEE_PASSWORD', 'gcu@123')

# Employee ID used as Vice-Chancellor (final approver). Empty falls back to
# the registrar@gcuniversity.ac.in row during `sync_approvers` if that email
# exists. GCU010002 is VC; GCU020004 is Registrar.
VC_EMP_ID = os.environ.get('VC_EMP_ID', '').strip()
