FROM dhi.io/nginx:1.31.6-debian13-dev

# curl + ca-certs so the in-container update loop can fetch ngxblocker
# updates from GitHub. kept to a single layer to minimise image bloat.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

# Vendored ngxblocker seed. entrypoint.sh copies these into
# /etc/nginx/{conf.d,bots.d}/ on container start.
COPY bot-blocker/ /etc/nginx/bot-blocker-seed/

# globalblacklist.conf is .gitignored because upstream updates it several times
# a day — vendoring would be constant PR noise. Fetch a fresh copy at build
# time so the baked seed always matches recent upstream; the in-container
# update loop keeps it current afterwards.
RUN curl -fsSL --retry 3 \
    "https://raw.githubusercontent.com/mitchellkrogza/nginx-ultimate-bad-bot-blocker/master/conf.d/globalblacklist.conf" \
    -o /etc/nginx/bot-blocker-seed/conf.d/globalblacklist.conf

# Background update loop started by entrypoint.sh.
COPY update-ngxblocker.sh /usr/local/bin/update-ngxblocker.sh
RUN chmod +x /usr/local/bin/update-ngxblocker.sh

# Any <400 response (including the HTTP → HTTPS 301) means the nginx master
# is up and accepting connections. curl -f treats 4xx/5xx as failures.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://localhost/ -o /dev/null || exit 1
