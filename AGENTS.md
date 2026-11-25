## Project: BCA website and data portal

- Django + DRF data portal with a Ghost CMS site, served by Nginx via Podman Compose
- PostgreSQL on a remote server (local Podman DB for testing); point local dev at it via `POSTGRES_SERVICE` in `.env`
- All Python work happens inside the `web` container (`podman compose exec web bash`)
- Lint using Super-Linter: ruff (Python), djlint (Django), Prettier + ESLint (JS/CSS)
- 4-space indentation
- Avoid nested functions
- Keep comments succinct and human-readable; avoid multi-line `#` comment blocks

## Commands

- Start services: `podman compose up -d --build` (needs `podman login dhi.io`; first time only: run `./scripts/setup.sh` to create configs from `*.template`)
- Run tests: `podman compose exec web python manage.py test app.tests.test_models` (omit the module to run all; CI runs `podman compose exec web coverage run -m pytest`)
- TypeScript tests: `podman compose exec web bun test`
- Lint: `./scripts/superlinter.py check` (fix: `./scripts/superlinter.py fix`)
- Rebuild JS/CSS assets: `podman compose exec web bun run build`
- Migrate: `podman compose exec web python manage.py migrate` (CI check: `makemigrations --check`)
- Integrity checks: `podman compose exec web python manage.py check --deploy` / `check_data` / `check_metadata` / `dump_bioschemas`
- End-to-end tests: `podman compose run --rm e2e pytest e2e/ -v` (separate DB volume; create it once with `manage.py createtestdb`)

## Rules

- Follow the repo's existing code conventions; reuse existing abstractions (mixins, utils, helper functions) instead of duplicating logic
- Always generate and commit migrations with model changes, then restart `web` (CI fails `makemigrations --check`)
- Never hand-edit the gitignored `dist/` output; rebuild with `bun run build` + `collectstatic`
- A fresh local DB has no data; never write tests that depend on real data
- Before committing: run the migration check, tests, deployment check, and lint
- Never commit local config or secrets (`.env`, `.pgpass`, `.pg_service.conf`) — only their `*.template` counterparts
- NEVER AUTOMATICALLY COMMIT WITHOUT ASKING! DO NOT CREATE PR AND DO NOT PUSH TO REMOTE REPOSITORY WITHOUT CONFIRMATION!
- PR: title based on titles from previous PRs, descriptions with one-line summary + bulleted "## Changes" section
- Include rollback steps in PR descriptions for risky changes

## Structure

- `app/` — Django app: models, views, templates, management commands, tests
- `rest/` — DRF API: viewsets, serializers, drf-spectacular schema, enrichment services
- `config/` — project settings (`config/settings.py`) and URLs
- `scripts/data/` — one-off data-loading scripts (need `pip install .[dataload]`, run against a real DB)
- `e2e/` — Playwright tests
- `ghost/` — website config
- `nginx/` — reverse-proxy config
- `data/` — gitignored local reference data (annotations, GO OBO, tree of life)
