#!/bin/bash
set -e

# Collect all static files
python manage.py collectstatic --noinput

if [ "${ENVIRONMENT:-}" = "prod" ]; then
    # Create tables with data models if they do not exist
    if ! psql -h ${POSTGRES_HOST} -d ${POSTGRES_DB} -tAc "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name LIKE '%_species');" | grep -q t; then
        python manage.py makemigrations
        python manage.py migrate
    fi

    # Serve Django apps using gunicorn
    gunicorn -w 4 config.wsgi --bind 0.0.0.0:8000
else
    # Update data models
    python manage.py makemigrations
    python manage.py migrate

    # Run server directly in Django (insecure)
    python manage.py runserver 0.0.0.0:8000
fi
