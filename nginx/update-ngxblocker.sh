#!/bin/sh
# Fetch the latest globalblacklist.conf from nginx-ultimate-bad-bot-blocker,
# validate it with `nginx -t`, promote in place and reload nginx.
#
# Only globalblacklist.conf is refreshed at runtime — the other ngxblocker
# files (bots.d/*, botblocker-nginx-settings.conf) change at most a couple
# of times per year and are vendored, so re-fetching them would be waste.
#
# Runs forever in the background, started by entrypoint.sh.
# Logs go to stderr → `podman logs bca-nginx-1`.
set -eu

URL="https://raw.githubusercontent.com/mitchellkrogza/nginx-ultimate-bad-bot-blocker/master/conf.d/globalblacklist.conf"
TARGET="/etc/nginx/conf.d/globalblacklist.conf"
INITIAL_WAIT="${NGXBLOCKER_INITIAL_WAIT:-604800}"      # 7 days
UPDATE_INTERVAL="${NGXBLOCKER_UPDATE_INTERVAL:-86400}" # 24 hours

log() { printf '[ngxblocker-update] %s %s\n' "$(date -u +%FT%TZ)" "$*" >&2; }

update_once() {
    tmp="$(mktemp)"
    if ! curl -fsSL --retry 3 --connect-timeout 10 --max-time 60 "$URL" -o "$tmp"; then
        log "fetch failed — skipping this cycle"
        rm -f "$tmp"
        return 1
    fi

    if cmp -s "$tmp" "$TARGET"; then
        log "no change upstream"
        rm -f "$tmp"
        return 0
    fi

    backup="$(mktemp)"
    cp "$TARGET" "$backup"
    cp "$tmp" "$TARGET"

    if nginx -t 2>/dev/null && nginx -s reload 2>/dev/null; then
        log "updated and reloaded"
        rm -f "$tmp" "$backup"
        return 0
    fi

    log "validation or reload failed — rolling back"
    cp "$backup" "$TARGET"
    rm -f "$tmp" "$backup"
    return 1
}

log "update loop started; initial wait ${INITIAL_WAIT}s, then every ${UPDATE_INTERVAL}s"
sleep "$INITIAL_WAIT"

while true; do
    update_once || true
    sleep "$UPDATE_INTERVAL"
done
