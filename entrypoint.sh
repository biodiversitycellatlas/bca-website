#!/bin/bash
set -e # Exit if any command returns a non-zero status

# Create and apply Django migrations
run_django_migrations() {
    python manage.py makemigrations
    python manage.py migrate
}

# Check if table exists in database
has_table() {
    table="%_$1"

    psql -h "${POSTGRES_HOST}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -tAc \
        "SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name LIKE '${table}'
        );" | grep -q t
}

run_django_migrations

# Deploy Django app
if [ "${ENVIRONMENT:-}" = "prod" ]; then
    # Serve Django apps using gunicorn
    gunicorn -w 4 config.wsgi --bind 0.0.0.0:8000
else
    # Prepare JavaScript and CSS static files
    bun install
    bun run build
    python manage.py collectstatic --noinput

    # Run server directly in Django (insecure, dev only)
    python manage.py runserver 0.0.0.0:8000
fi
