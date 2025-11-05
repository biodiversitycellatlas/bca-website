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

echo "[NGINX] Starting server..."
exec nginx -g 'daemon off;'
