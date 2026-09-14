"""
One-step automated production environment setup for PythonAnywhere (HKHC).
Run: python setup_env.py
"""
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

secret_key = secrets.token_urlsafe(50)

env_content = f"""# Production environment configuration for HKHC Community
SECRET_KEY={secret_key}
DEBUG=False
ALLOWED_HOSTS=hkhc.pythonanywhere.com,HKHC.pythonanywhere.com,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://hkhc.pythonanywhere.com,https://HKHC.pythonanywhere.com

# Database: default SQLite for PythonAnywhere free tier
DB_ENGINE=

# Email: console backend for PythonAnywhere free tier
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# Security & Cookies
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=False
"""

ENV_FILE.write_text(env_content, encoding="utf-8")
print(f"Successfully created {ENV_FILE}")
print("Your SECRET_KEY and production settings have been configured.")
