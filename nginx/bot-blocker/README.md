# nginx-ultimate-bad-bot-blocker

Vendored snapshot of [mitchellkrogza/nginx-ultimate-bad-bot-blocker](https://github.com/mitchellkrogza/nginx-ultimate-bad-bot-blocker) — a maintained blacklist of bad bots, scrapers, referrer spam, and known-malicious IP ranges, delivered as nginx config includes.

## How it fits into the stack

- Files here are the **seed**. `nginx/Dockerfile` copies them into `/etc/nginx/bot-blocker-seed/` inside the image.
- `globalblacklist.conf` is `.gitignore`d because upstream updates it several times a day — vendoring would be constant PR noise. `nginx/Dockerfile` fetches a fresh copy at build time so the baked seed always matches recent upstream.
- On every container start, `nginx/entrypoint.sh` copies the seed into `/etc/nginx/conf.d/` and `/etc/nginx/bots.d/`.
- `nginx/update-ngxblocker.sh` runs in the background: sleeps 7 days after boot, then every 24 h fetches the latest `globalblacklist.conf`, validates with `nginx -t`, promotes on success and rolls back on failure. The other files are stable enough that re-fetching them would be waste. All transitions log to stderr.
- `nginx/nginx.prod.conf.template` enables the blocker by including `blockbots.conf` + `ddos.conf` inside each HTTPS `server {}` block.

## File roles

| File                                    | Scope              | Purpose                                                                                    |
| --------------------------------------- | ------------------ | ------------------------------------------------------------------------------------------ |
| `conf.d/globalblacklist.conf`           | `http`             | All the maps/geos: `$bad_bot`, `$bad_words`, `$bad_referer`, `$validate_client`, bot zones |
| `conf.d/botblocker-nginx-settings.conf` | `http`             | Hash-size tunables, `flood` + `addr` DDoS limit zones                                      |
| `bots.d/blockbots.conf`                 | `server`           | Enforces the `$bad_bot` / `$bad_words` / `$bad_referer` checks                             |
| `bots.d/ddos.conf`                      | `server`           | Applies `flood` + `addr` zones                                                             |
| `bots.d/whitelist-ips.conf`             | included from maps | Add IPs you never want blocked                                                             |
| `bots.d/whitelist-domains.conf`         | included from maps | Add referrer domains to never flag                                                         |
| `bots.d/blacklist-ips.conf`             | included from maps | Add IPs you always want blocked                                                            |
| `bots.d/blacklist-user-agents.conf`     | included from maps | Add extra UAs to always block                                                              |
| `bots.d/bad-referrer-words.conf`        | included from maps | Add referrer substrings to flag                                                            |
| `bots.d/custom-bad-referrers.conf`      | included from maps | Add specific referrer URLs to flag                                                         |

Local customisations go into the `whitelist-*` / `blacklist-*` / `custom-*` files — those are the ones the upstream project explicitly reserves for site-level additions. Editing `globalblacklist.conf` is pointless: it's `.gitignore`d, rebuilt from upstream on each image build, and overwritten by the update loop.

## Useful commands

### Confirm the blocker is active

```sh
# Known-bad UA → nginx returns 444 (connection dropped), curl shows status 000
curl -sk --max-time 3 -o /dev/null -w "%{http_code}\n" \
    -H "User-Agent: AhrefsBot/7.0" https://portal.biodiversitycellatlas.org/

# Normal browser → 200
curl -sk -o /dev/null -w "%{http_code}\n" \
    -H "User-Agent: Mozilla/5.0" https://portal.biodiversitycellatlas.org/
```

Watch nginx log the 444 live:

```sh
podman logs -f bca-nginx-1 2>&1 | grep ' 444 '
```

### Check what's loaded in the running container

```sh
podman exec bca-nginx-1 ls /etc/nginx/conf.d/ /etc/nginx/bots.d/
podman exec bca-nginx-1 wc -l /etc/nginx/conf.d/globalblacklist.conf
```

### See the update-loop status

```sh
# Start-up line + every tick's result go to stderr
podman logs bca-nginx-1 2>&1 | grep ngxblocker
```

Expected after a fresh deploy:

```text
[ngxblocker-update] 2026-10-09T10:04:36Z update loop started; initial wait 604800s, then every 86400s
```

After the first successful tick (seven days later):

```text
[ngxblocker-update] 2026-10-16T10:04:36Z updated and reloaded
```

### Refresh the vendored seed from upstream

Only the slow-moving files are vendored — `botblocker-nginx-settings.conf` (upstream last touched years ago) and the `bots.d/*` files (also years-old). You rarely need to refresh them, but when you do:

```sh
cd nginx/bot-blocker
BASE=https://raw.githubusercontent.com/mitchellkrogza/nginx-ultimate-bad-bot-blocker/master
for f in conf.d/botblocker-nginx-settings.conf \
         bots.d/blockbots.conf bots.d/ddos.conf \
         bots.d/whitelist-ips.conf bots.d/whitelist-domains.conf \
         bots.d/blacklist-ips.conf bots.d/blacklist-user-agents.conf \
         bots.d/bad-referrer-words.conf bots.d/custom-bad-referrers.conf; do
  curl -fsSL "$BASE/$f" -o "$f"
done
```

`globalblacklist.conf` is intentionally not in this list — it comes from the build-time fetch and the daily in-container update.

Then review the diff and commit.

### Tweak the update cadence without rebuilding

Both intervals are env-overridable. Add to the `nginx:` service in `compose.prod.yml`:

```yaml
environment:
    - NGXBLOCKER_INITIAL_WAIT=86400 # 1 day instead of 7
    - NGXBLOCKER_UPDATE_INTERVAL=43200 # 12 hours instead of 24
```

Then `podman compose up -d --no-deps --force-recreate nginx`.
