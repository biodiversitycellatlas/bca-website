#!/bin/sh

# Copy the *.template files to avoid the .template suffix
cp .env.template .env
cp nginx/nginx.conf.template nginx/nginx.conf
cp .pg_service.conf.template .pg_service.conf
cp .pgpass.template .pgpass

# Modify COMPOSE_FILE based on environment
if [ "$1" = "test" ]; then
    echo "COMPOSE_FILE=compose.yml:compose.test.yml" >>.env
elif [ "$1" = "e2e" ]; then
    echo "COMPOSE_FILE=compose.yml:compose.e2e.yml" >>.env
elif [ "$1" = "prod" ]; then
    echo "COMPOSE_FILE=compose.yml:compose.prod.yml" >>.env

fi

# Fix the permissions for .pgpass
chmod 600 .pgpass
