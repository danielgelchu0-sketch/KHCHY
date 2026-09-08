"""
Development settings for HKHC Community Discussion Platform.
"""
from .base import *  # noqa: F403

DEBUG = True

# In local dev, allow localhost hosts
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]

# Development email backend prints to console
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Less restrictive session cookies for localhost development
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
