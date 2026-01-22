#!/bin/bash
set -e # Exit if any command returns a non-zero status

# Collect all Django static files
python manage.py collectstatic --noinput

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

# Prepare JS and CSS dependencies
bun install
bun run build:ts

# Check whether the environment is production
if [ "${ENVIRONMENT:-}" = "prod" ]; then
    # Create tables with data models if they do not exist
    if ! has_table 'species'; then
        run_django_migrations
    fi

    # Serve Django apps using gunicorn
    gunicorn -w 4 config.wsgi --bind 0.0.0.0:8000
else
    # Update data models in dev
    run_django_migrations

    # Run server directly in Django (insecure, dev only)
    python manage.py runserver 0.0.0.0:8000
fi
