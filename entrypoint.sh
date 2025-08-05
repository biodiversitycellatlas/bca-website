#!/bin/bash
set -e

# Collect all static files
python manage.py collectstatic --noinput

run_django_migrations() {
    python manage.py makemigrations
    python manage.py migrate
}

check_table_exists() {
    table="%_$1"

    result=$(python -c "
import psycopg2, os, sys
conn = psycopg2.connect(
    host=os.getenv('POSTGRES_HOST'),
    user=os.getenv('POSTGRES_USER'),
    password=os.getenv('POSTGRES_PASSWORD'),
    dbname=os.getenv('POSTGRES_DB')
)
cur = conn.cursor()
cur.execute('''
    SELECT EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_name LIKE %s
    );
''', (sys.argv[1], ))
print(1 if cur.fetchone()[0] else 0)
" "$table")
    [ "$result" -eq 1 ] && return 0 || return 1
}

if [ "${ENVIRONMENT:-}" = "prod" ]; then
    # Create tables with data models if they do not exist
    if ! check_table_exists 'species'; then
        run_django_migrations
    fi

    # Serve Django apps using gunicorn
    gunicorn -w 4 config.wsgi --bind 0.0.0.0:8000
else
    # Update data models
    run_django_migrations

    # Run server directly in Django (insecure)
    python manage.py runserver 0.0.0.0:8000
fi
