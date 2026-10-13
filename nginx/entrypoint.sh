#!/bin/sh
set -e

echo "[NGINX] Preparing production config..."

# Enforce secure TLS in production
if [ "$ENVIRONMENT" = "prod" ] && [ "$NODE_TLS_REJECT_UNAUTHORIZED" != "1" ]; then
    export NODE_TLS_REJECT_UNAUTHORIZED=1
fi

# Ensure directory exists
mkdir -p /etc/nginx/conf.d /etc/nginx/bots.d

# Seed ngxblocker files from the image into the active locations.
# Running on every start keeps the active files in sync with whatever was
# vendored into the image; the background update loop then overlays the
# latest upstream version a week after boot and daily thereafter.
if [ -d /etc/nginx/bot-blocker-seed ]; then
    cp /etc/nginx/bot-blocker-seed/conf.d/*.conf /etc/nginx/conf.d/
    cp /etc/nginx/bot-blocker-seed/bots.d/*.conf /etc/nginx/bots.d/
fi

# Substitute variables into config
envsubst '$DJANGO_HOSTNAME $GHOST_HOSTNAME $GHOST_INTERNAL_URL $PLAUSIBLE_HOSTNAME' \
    </etc/nginx/nginx.prod.conf.template \
    >/etc/nginx/conf.d/default.conf

echo "[NGINX] Final NGINX config:"
cat /etc/nginx/conf.d/default.conf

# Ensure nginx cert folder exists
mkdir -p /etc/nginx/certs

# Link the cert and key dynamically from env vars
ln -sf "/certs/$CERT_FILE" /etc/nginx/certs/server.crt
ln -sf "/certs/$CERT_KEY_FILE" /etc/nginx/certs/server.key

# Background update loop for ngxblocker. Only started if the script was
# baked into the image (production build); harmless if missing.
if [ -x /usr/local/bin/update-ngxblocker.sh ]; then
    /usr/local/bin/update-ngxblocker.sh &
fi

echo "[NGINX] Starting server..."
exec nginx -g 'daemon off;'
