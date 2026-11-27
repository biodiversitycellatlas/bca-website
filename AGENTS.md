## Project: BCA website and data portal

- Django + DRF data portal with a Ghost CMS site, served by Nginx via Podman Compose
- All Python work happens inside the `web` container (`podman compose exec web bash`)
- Local dev uses the local podman Postgres database by default; point dev at a remote server via `POSTGRES_SERVICE` in `.env` (tests always use the local container based on `config/settings.py`)
- Lint with Super-Linter: ruff (Python), djlint (Django), Prettier + ESLint (JS/CSS); all validators enabled in `.github/linters` can be run with `./scripts/superlinter.py check` and `./scripts/superlinter.py fix`
- Code style follows `.editorconfig` (4-space indentation, LF line endings, final newline, no trailing whitespace; `test_fixtures/` is exempt)
- Avoid nested functions
- Keep comments succinct and human-readable; avoid multi-line `#` comment blocks

## Commands

- Start services: `podman compose up -d --build` (needs `podman login dhi.io`; first time only: run `./scripts/setup.sh` to create configs from `*.template`)
- Run tests: `podman compose exec web python -m pytest` (full suite; CI runs `coverage run -m pytest`). `manage.py test <module>` only runs Django test cases, so it silently skips plain test classes (e.g. the Bioschemas tests in `app/tests/test_utils.py` and `app/tests/test_templatetags.py`)
- TypeScript tests: `podman compose exec web bun test`
- Rebuild JS/CSS assets: `podman compose exec web bun run build`
- Migrate: `podman compose exec web python manage.py migrate` (CI check: `makemigrations --check`)
- Integrity checks: `podman compose exec web python manage.py check --deploy` / `check_data` / `check_metadata` / `dump_bioschemas`
- End-to-end tests (read preparation in `README.md`): `podman compose run --rm e2e pytest e2e/ -v`
- Other workflows (initial setup, unit tests, static files) are covered in `README.md`

## Rules

- Follow the repo's existing code conventions; reuse existing abstractions (mixins, utils, helper functions) instead of duplicating logic
- Include migrations with model changes (CI fails `makemigrations --check`); restart `web` after model changes
- Never hand-edit the gitignored `dist/` output; edit the frontend sources in `app/static/app/src/` or `rest/static/rest/src/`, then rebuild with `bun run build` + `collectstatic`
- Never write tests that depend on real data — use `app/management/commands/factories.py`, `createtestdb`, or the `test_fixtures/` folders instead
- Before committing: run the migration check, tests, deployment check, and lint
- Never commit local config or secrets (`.env`, `.pgpass`, `.pg_service.conf`) — only their `*.template` counterparts
- Ask before committing, pushing, or opening a PR
- PR: title in the style of previous PR titles (e.g. `REST: add models and endpoint for cell type hierarchies`); description with a one-line summary + bulleted "## Changes" section
- Branch names: `<user>/<topic>` (e.g. `nuno/citation`)
- Include rollback steps in PR descriptions for risky changes

## Structure

- `app/` — Django app: models, views, templates, management commands; tests in `app/tests/` (with `app/tests/test_fixtures/`)
- `app/systemchecks/` — data/metadata checks behind `check_data` and `check_metadata`
- `app/static/app/src/` — frontend TypeScript/CSS sources for the portal
- `rest/` — DRF API: viewsets, serializers, drf-spectacular schema, enrichment services; tests in `rest/tests/` (with `rest/tests/test_fixtures/`)
- `config/` — project settings (`config/settings.py`) and URLs
- `scripts/` — repository tooling (`setup.sh`, `superlinter.py`, health checks); `scripts/data/` holds the one-off data-loading scripts, to be replaced in time with Django management commands
- `e2e/` — Playwright tests
- `ghost/` — website config
- `nginx/` — reverse-proxy config
- `data/` — gitignored local reference data (annotations, GO OBO, tree of life)
