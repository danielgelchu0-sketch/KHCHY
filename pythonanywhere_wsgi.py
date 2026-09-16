"""
PythonAnywhere WSGI Configuration File.
Copy this content into your PythonAnywhere WSGI configuration file
(/var/www/<your_username>_pythonanywhere_com_wsgi.py) or reference it directly.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Path configuration
import getpass
current_user = getpass.getuser()
potential_dirs = [
    Path(f"/home/{current_user}/HKHC-Chat-SYSTEM"),
    Path(__file__).resolve().parent,
    Path.cwd(),
]
PROJECT_DIR = next((p for p in potential_dirs if (p / "manage.py").exists()), Path(__file__).resolve().parent)

if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

# Ensure apps directory is on path
APPS_DIR = PROJECT_DIR / "apps"
if str(APPS_DIR) not in sys.path:
    sys.path.insert(0, str(APPS_DIR))

# Load production environment variables
env_path = PROJECT_DIR / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Set production settings
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.production"

# Initialize Django WSGI application
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
