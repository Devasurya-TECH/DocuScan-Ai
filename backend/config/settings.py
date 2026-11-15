"""
Django settings for DocuScan AI backend.
"""

import os
from datetime import timedelta
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIST_DIR = BASE_DIR.parent / 'dist'

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'unsafe-development-key-change-me')
DEBUG = os.environ.get('DJANGO_DEBUG', 'true').lower() == 'true'

allowed_hosts_raw = os.environ.get('DJANGO_ALLOWED_HOSTS', '*')
if allowed_hosts_raw.strip() == '*':
    ALLOWED_HOSTS = ['*']
else:
    ALLOWED_HOSTS = [h.strip() for h in allowed_hosts_raw.split(',') if h.strip()]

# Render internal health checks probe localhost/127.0.0.1. Ensure local probes never fail with 400 DisallowedHost.
for default_host in ['localhost', '127.0.0.1', '0.0.0.0', 'testserver', '.onrender.com']:
    if default_host not in ALLOWED_HOSTS and '*' not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(default_host)

render_host = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if render_host and render_host not in ALLOWED_HOSTS and '*' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(render_host)

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'rest_framework',
    'rest_framework_simplejwt',
    'documents',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',   # Serves React assets via Gunicorn
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
        'DIRS': [FRONTEND_DIST_DIR],
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
# Supports SQLite locally, and PostgreSQL (e.g. Neon Serverless Postgres) via DATABASE_URL in production
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

database_url = os.environ.get('DATABASE_URL')
if database_url:
    import urllib.parse
    # Normalize postgres:// to postgresql:// for psycopg
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    db_url = urllib.parse.urlparse(database_url)
    query_params = urllib.parse.parse_qs(db_url.query)

    db_options = {}
    if 'sslmode' in query_params:
        db_options['sslmode'] = query_params['sslmode'][0]
    elif not DEBUG or 'neon.tech' in (db_url.hostname or ''):
        db_options['sslmode'] = 'require'

    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': urllib.parse.unquote(db_url.path.lstrip('/')),
        'USER': urllib.parse.unquote(db_url.username or ''),
        'PASSWORD': urllib.parse.unquote(db_url.password or ''),
        'HOST': db_url.hostname,
        'PORT': db_url.port or 5432,
        'CONN_MAX_AGE': int(os.environ.get('DB_CONN_MAX_AGE', '0')),
    }
    if db_options:
        DATABASES['default']['OPTIONS'] = db_options

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PARSER_CLASSES': (
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 25,
}

# SimpleJWT configuration
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=14),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': False,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'SIGNING_KEY': SECRET_KEY,
}

# Celery Configuration
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://127.0.0.1:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://127.0.0.1:6379/0')
# Read both CELERY_TASK_ALWAYS_EAGER and legacy CELERY_ALWAYS_EAGER
CELERY_TASK_ALWAYS_EAGER = os.environ.get('CELERY_TASK_ALWAYS_EAGER', os.environ.get('CELERY_ALWAYS_EAGER', 'true')).lower() == 'true'
CELERY_ALWAYS_EAGER = CELERY_TASK_ALWAYS_EAGER
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_TASK_TIME_LIMIT = 300

# CORS settings — restricted for production security
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_CREDENTIALS = False

# Default development origins — production URL also listed as a fallback
# (the env var CORS_ALLOWED_ORIGINS on Render is the authoritative production value)
CORS_ALLOWED_ORIGINS = [
    'https://docu-scan-ai-sigma.vercel.app',
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]

# Allow any custom origins specified in the environment (e.g. production Vercel frontend URL)
custom_cors_origins = os.environ.get('CORS_ALLOWED_ORIGINS', '')
if custom_cors_origins:
    for origin in custom_cors_origins.split(','):
        origin = origin.strip()
        if origin and origin not in CORS_ALLOWED_ORIGINS:
            CORS_ALLOWED_ORIGINS.append(origin)

# Allow Vercel production and preview deployment URLs for this project only.
# Rejects all other *.vercel.app domains.
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://docu-scan-ai-sigma(-[a-zA-Z0-9_-]+)?\.vercel\.app$",
]

# CSRF trusted origins for web forms / admin / cross-origin requests
CSRF_TRUSTED_ORIGINS = [
    'https://docu-scan-ai-sigma.vercel.app',
    'https://*.onrender.com',
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'http://localhost:3000',
    'http://127.0.0.1:3000',
]
if custom_cors_origins:
    for origin in custom_cors_origins.split(','):
        origin = origin.strip()
        if origin and origin not in CSRF_TRUSTED_ORIGINS:
            CSRF_TRUSTED_ORIGINS.append(origin)

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static & Media files
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [FRONTEND_DIST_DIR / 'assets'] if (FRONTEND_DIST_DIR / 'assets').exists() else []

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Persistent Object Storage (Cloudflare R2 / AWS S3)
# When configured, uploaded documents and generated files persist across Render restarts for $0
USE_S3_STORAGE = (
    os.environ.get('USE_S3_STORAGE', 'false').lower() == 'true'
    or bool(os.environ.get('AWS_ACCESS_KEY_ID'))
    or bool(os.environ.get('R2_ACCESS_KEY_ID'))
)

if USE_S3_STORAGE:
    if 'storages' not in INSTALLED_APPS:
        INSTALLED_APPS.append('storages')
    AWS_ACCESS_KEY_ID = os.environ.get('R2_ACCESS_KEY_ID', os.environ.get('AWS_ACCESS_KEY_ID'))
    AWS_SECRET_ACCESS_KEY = os.environ.get('R2_SECRET_ACCESS_KEY', os.environ.get('AWS_SECRET_ACCESS_KEY'))
    AWS_STORAGE_BUCKET_NAME = os.environ.get('R2_BUCKET_NAME', os.environ.get('AWS_STORAGE_BUCKET_NAME', 'docuscan-media'))
    AWS_S3_ENDPOINT_URL = os.environ.get('R2_ENDPOINT_URL', os.environ.get('AWS_S3_ENDPOINT_URL'))
    AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME', 'auto')
    AWS_S3_SIGNATURE_VERSION = 's3v4'
    AWS_DEFAULT_ACL = None
    AWS_S3_FILE_OVERWRITE = False
    AWS_QUERYSTRING_AUTH = True
    AWS_QUERYSTRING_EXPIRE = 3600
    STORAGES = {
        'default': {
            'BACKEND': 'storages.backends.s3.S3Storage',
        },
        'staticfiles': {
            'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
        },
    }
else:
    STORAGES = {
        'default': {
            'BACKEND': 'django.core.files.storage.FileSystemStorage',
        },
        'staticfiles': {
            'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
        },
    }

# Ensure local directories exist (fallback when not using S3)
os.makedirs(MEDIA_ROOT / 'documents', exist_ok=True)
os.makedirs(MEDIA_ROOT / 'processed_documents', exist_ok=True)
os.makedirs(MEDIA_ROOT / 'exports', exist_ok=True)

# Production security and upload constraints
DATA_UPLOAD_MAX_MEMORY_SIZE = 52428800  # 50 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 52428800  # 50 MB
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'

