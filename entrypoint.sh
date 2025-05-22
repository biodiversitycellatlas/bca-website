#!/bin/bash
set -e

# Collect all static files
python manage.py collectstatic --noinput

if [ "${ENVIRONMENT:-}" = "prod" ]; then
    # Serve Django apps using gunicorn
    gunicorn -w 4 config.wsgi --bind 0.0.0.0:8000
else
    # Update data models
    python manage.py makemigrations
    python manage.py migrate

    # Run server directly in Django (insecure)
    python manage.py runserver 0.0.0.0:8000
fi
