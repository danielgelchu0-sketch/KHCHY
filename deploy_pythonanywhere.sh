#!/usr/bin/env bash
# ==============================================================================
# HKHC Community Discussion Platform - PythonAnywhere Deployment Script
# Run this script in the PythonAnywhere Bash console after pulling new code.
# ==============================================================================

set -e

echo "=== [1/5] Activating Virtual Environment ==="
# Adjust path if your virtualenv is located elsewhere, e.g., ~/.virtualenvs/hkhc-env
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "$HOME/.virtualenvs/hkhc-env" ]; then
    source "$HOME/.virtualenvs/hkhc-env/bin/activate"
else
    echo "Warning: Virtual environment not found automatically. Ensure active venv before running."
fi

echo "=== [2/5] Installing/Updating Production Dependencies ==="
pip install --upgrade pip
pip install -r requirements/prod.txt

echo "=== [3/5] Applying Database Migrations ==="
python manage.py migrate --settings=config.settings.production

echo "=== [4/5] Collecting Static Files ==="
python manage.py collectstatic --noinput --settings=config.settings.production

echo "=== [5/5] Running Deployment Checks ==="
python manage.py check --deploy --settings=config.settings.production

echo ""
echo "=============================================================================="
echo "Deployment tasks completed successfully!"
echo "Remember to reload your Web App in the PythonAnywhere Web tab dashboard."
echo "=============================================================================="
