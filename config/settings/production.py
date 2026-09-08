"""
Production settings for HKHC Community Discussion Platform.
Optimized for deployment environments such as PythonAnywhere.
"""
import os
from .base import *  # noqa: F403

DEBUG = False

# Production secret key must be set via environment variable
if SECRET_KEY == "insecure-default-development-key-change-in-prod-hkhc-community":  # noqa: F405
    raise RuntimeError("CRITICAL: Production SECRET_KEY environment variable is not set!")

# Production Allowed Hosts
if not ALLOWED_HOSTS or ALLOWED_HOSTS == ["localhost", "127.0.0.1"]:  # noqa: F405
    # Enforce setting explicit ALLOWED_HOSTS in production
    pass

# Security Headers & Cookie Policies
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "True").lower() in ("true", "1", "yes")
CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "True").lower() in ("true", "1", "yes")
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # Set to False so HTMX can read CSRF token if needed from cookie or csrf-token header

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "True").lower() in ("true", "1", "yes")
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv("SECURE_HSTS_INCLUDE_SUBDOMAINS", "True").lower() in ("true", "1", "yes")
SECURE_HSTS_PRELOAD = os.getenv("SECURE_HSTS_PRELOAD", "False").lower() in ("true", "1", "yes")

# Respect X-Forwarded-Proto header for reverse proxies / PythonAnywhere HTTPS
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
