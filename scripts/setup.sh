#!/bin/sh

# Copy the *.template files to avoid the .template suffix
cp .env.template .env
cp nginx/nginx.conf.template nginx/nginx.conf
cp .pg_service.conf.template .pg_service.conf
cp .pgpass.template .pgpass

# If "prod" argument is passed, modify COMPOSE_FILE to include compose.prod.yml
if [ "$1" = "prod" ]; then
    echo "COMPOSE_FILE=compose.yml:compose.prod.yml" >> .env
fi

# Fix the permissions for .pgpass
chmod 600 .pgpass
