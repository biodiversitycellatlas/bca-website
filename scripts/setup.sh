# Copy the *.template files to avoid the .template suffix
cp .env.template .env
cp nginx/nginx.conf.template nginx/nginx.conf
cp .pg_service.conf.template .pg_service.conf
cp .pgpass.template .pgpass

# Fix the permissions for .pgpass
chmod 600 .pgpass
