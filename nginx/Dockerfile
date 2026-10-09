FROM dhi.io/nginx:1.31.6-debian13-dev

# curl + ca-certs so the in-container update loop can fetch ngxblocker
# updates from GitHub. kept to a single layer to minimise image bloat.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

# Vendored ngxblocker seed. entrypoint.sh copies these into
# /etc/nginx/{conf.d,bots.d}/ on container start.
COPY bot-blocker/ /etc/nginx/bot-blocker-seed/

# Background update loop started by entrypoint.sh.
COPY update-ngxblocker.sh /usr/local/bin/update-ngxblocker.sh
RUN chmod +x /usr/local/bin/update-ngxblocker.sh
