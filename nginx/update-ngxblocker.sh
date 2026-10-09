#!/bin/sh
# Fetch the latest nginx-ultimate-bad-bot-blocker config from GitHub,
# validate it with `nginx -t`, promote in place and reload nginx.
#
# Runs forever in the background, started by entrypoint.sh.
# Logs go to stderr → `podman logs bca-nginx-1`.
set -eu

BASE_URL="https://raw.githubusercontent.com/mitchellkrogza/nginx-ultimate-bad-bot-blocker/master"
INITIAL_WAIT="${NGXBLOCKER_INITIAL_WAIT:-604800}"      # 7 days
UPDATE_INTERVAL="${NGXBLOCKER_UPDATE_INTERVAL:-86400}" # 24 hours

CONF_D_FILES="botblocker-nginx-settings.conf globalblacklist.conf"
BOTS_D_FILES="blockbots.conf ddos.conf \
whitelist-ips.conf whitelist-domains.conf \
blacklist-ips.conf blacklist-user-agents.conf \
bad-referrer-words.conf custom-bad-referrers.conf"

log() { printf '[ngxblocker-update] %s %s\n' "$(date -u +%FT%TZ)" "$*" >&2; }

fetch_all() {
    tmp="$1"
    mkdir -p "$tmp/conf.d" "$tmp/bots.d"
    for f in $CONF_D_FILES; do
        curl -fsSL --retry 3 --connect-timeout 10 --max-time 60 \
            "$BASE_URL/conf.d/$f" -o "$tmp/conf.d/$f" || return 1
    done
    for f in $BOTS_D_FILES; do
        curl -fsSL --retry 3 --connect-timeout 10 --max-time 60 \
            "$BASE_URL/bots.d/$f" -o "$tmp/bots.d/$f" || return 1
    done
}

promote_or_rollback() {
    tmp="$1"
    backup="$(mktemp -d)"
    mkdir -p "$backup/conf.d" "$backup/bots.d"

    # Snapshot current ngxblocker files so we can revert if validation fails
    for f in $CONF_D_FILES; do
        [ -f "/etc/nginx/conf.d/$f" ] && cp "/etc/nginx/conf.d/$f" "$backup/conf.d/$f"
    done
    for f in $BOTS_D_FILES; do
        [ -f "/etc/nginx/bots.d/$f" ] && cp "/etc/nginx/bots.d/$f" "$backup/bots.d/$f"
    done

    cp "$tmp/conf.d/"*.conf /etc/nginx/conf.d/
    cp "$tmp/bots.d/"*.conf /etc/nginx/bots.d/

    if nginx -t 2>/dev/null; then
        if nginx -s reload 2>/dev/null; then
            log "updated and reloaded"
            rm -rf "$backup"
            return 0
        fi
        log "reload failed — rolling back"
    else
        log "nginx -t failed on new config — rolling back"
    fi

    # Revert
    for f in $CONF_D_FILES; do
        [ -f "$backup/conf.d/$f" ] && cp "$backup/conf.d/$f" "/etc/nginx/conf.d/$f"
    done
    for f in $BOTS_D_FILES; do
        [ -f "$backup/bots.d/$f" ] && cp "$backup/bots.d/$f" "/etc/nginx/bots.d/$f"
    done
    rm -rf "$backup"
    return 1
}

log "update loop started; initial wait ${INITIAL_WAIT}s, then every ${UPDATE_INTERVAL}s"
sleep "$INITIAL_WAIT"

while true; do
    tmp="$(mktemp -d)"
    if fetch_all "$tmp"; then
        promote_or_rollback "$tmp" || true
    else
        log "fetch failed — skipping this cycle"
    fi
    rm -rf "$tmp"
    sleep "$UPDATE_INTERVAL"
done
