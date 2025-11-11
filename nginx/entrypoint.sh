#!/bin/sh
set -e

echo "[NGINX] Preparing config..."

# Ensure directory exists
mkdir -p /etc/nginx/conf.d

# Substitute variables into config
envsubst '$DJANGO_HOSTNAME $GHOST_HOSTNAME' \
  < /etc/nginx/nginx.conf.template \
  > /etc/nginx/conf.d/default.conf

echo "[NGINX] Final NGINX config:"
cat /etc/nginx/conf.d/default.conf

# Ensure nginx cert folder exists
mkdir -p /etc/nginx/certs

# Link the cert and key dynamically from env vars
ln -sf "/certs/$CERT_FILE" /etc/nginx/certs/server.crt
ln -sf "/certs/$CERT_KEY_FILE" /etc/nginx/certs/server.key

echo "[NGINX] Starting server..."
exec nginx -g 'daemon off;'
