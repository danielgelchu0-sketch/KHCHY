"""
Django base settings for HKHC Community Discussion Platform.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from django.utils.translation import gettext_lazy as _

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Ensure the apps directory is importable
APPS_DIR = BASE_DIR / "apps"
if str(APPS_DIR) not in sys.path:
    sys.path.insert(0, str(APPS_DIR))

# Load environment variables from .env if present
env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Security Settings
SECRET_KEY = os.getenv("SECRET_KEY", "insecure-default-development-key-change-in-prod-hkhc-community")
DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "t", "yes")

# Allowed Hosts & CSRF
raw_allowed_hosts = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,.pythonanywhere.com")
ALLOWED_HOSTS = [host.strip() for host in raw_allowed_hosts.split(",") if host.strip()]
if ".pythonanywhere.com" not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(".pythonanywhere.com")

raw_csrf_trusted = os.getenv("CSRF_TRUSTED_ORIGINS", "")
if raw_csrf_trusted:
    CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in raw_csrf_trusted.split(",") if origin.strip()]
else:
    CSRF_TRUSTED_ORIGINS = []
for origin in ["https://*.pythonanywhere.com", "http://*.pythonanywhere.com"]:
    if origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(origin)

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Local HKHC Apps
    "apps.core.apps.CoreConfig",
    "apps.accounts.apps.AccountsConfig",
    "apps.discussions.apps.DiscussionsConfig",
    "apps.moderation.apps.ModerationConfig",
    "apps.notifications.apps.NotificationsConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "apps.accounts.middleware.AccountStatusMiddleware",  # Intercept suspended/banned users immediately
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
                "apps.core.context_processors.community_context",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Custom User Model & Backends
AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = [
    "apps.accounts.backends.EmailOrDisplayNameBackend",
]

# Database Configuration
# Default to SQLite for local development; switches to PostgreSQL when configured
DB_ENGINE = os.getenv("DB_ENGINE", "")
DB_NAME = os.getenv("DB_NAME", "")
DB_USER = os.getenv("DB_USER", "")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "")
DB_PORT = os.getenv("DB_PORT", "")

database_url = os.getenv("DATABASE_URL", "")

if database_url:
    # Minimal URL parser to avoid external dependencies
    from urllib.parse import urlparse
    parsed = urlparse(database_url)
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": parsed.path.lstrip("/"),
            "USER": parsed.username or "",
            "PASSWORD": parsed.password or "",
            "HOST": parsed.hostname or "localhost",
            "PORT": parsed.port or "5432",
        }
    }
elif DB_ENGINE == "django.db.backends.postgresql" and DB_NAME:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": DB_NAME,
            "USER": DB_USER,
            "PASSWORD": DB_PASSWORD,
            "HOST": DB_HOST or "localhost",
            "PORT": DB_PORT or "5432",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

if "test" in sys.argv:
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Internationalization
LANGUAGE_CODE = "en"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ("en", _("English")),
    ("am", _("Amharic")),
]

LOCALE_PATHS = [
    BASE_DIR / "locale",
]

LANGUAGE_COOKIE_NAME = "django_language"
LANGUAGE_COOKIE_AGE = 365 * 24 * 60 * 60  # 1 year
LANGUAGE_COOKIE_PATH = "/"
LANGUAGE_COOKIE_SAMESITE = "Lax"

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

# Media files (User uploads such as profile photos)
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
MAX_UPLOAD_SIZE = 2 * 1024 * 1024  # 2MB maximum upload limit

# Authentication URLs
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "discussions:topic_list"
LOGOUT_REDIRECT_URL = "core:home"

# Email Configuration
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "25"))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "False").lower() in ("true", "1", "yes")
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "HKHC Community <noreply@community.hkhc.org>")

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Community Platform Settings
COMMUNITY_NAME = "HKHC Community"
COMMUNITY_DESCRIPTION = "A safe, moderated church community space for honest questions, biblical fellowship, and thoughtful discussion."
PAGINATION_PAGE_SIZE = 20

# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] [{levelname}] [{name}:{lineno}] {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
        "django.security": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "apps.moderation": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "apps.accounts": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
