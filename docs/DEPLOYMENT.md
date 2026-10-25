# Render API/PostgreSQL + Vercel frontend

Prepared on 2026-10-25. This guide reflects the inspected repository and local verification.
No Render/Vercel service was created, no production database was accessed, and no push or deployment
was performed. Replace placeholders with values from your dashboards; no live URLs are assumed.

## Architecture and directory settings

Vercel serves the built React SPA. Browser requests go directly to the Render FastAPI service over
HTTPS with a bearer token. FastAPI connects to Render Postgres. Vite's development proxy is not
used in production. Only the backend receives database credentials and the JWT signing key.

- Render **Root Directory: `backend`**. This exposes `pyproject.toml`, `uv.lock`, `app`, and
  `alembic.ini` in the service root. All Render commands below are relative to that directory.
- Vercel **Root Directory: `frontend`**. Its `vercel.json` configures Vite, locked npm installation,
  build/output and SPA deep-link rewrites.

Render detects uv from a lockfile in the service root. Root-directory settings also change command
paths and exclude files outside that root. See [Render uv](https://render.com/docs/uv-version) and
[monorepo support](https://render.com/docs/monorepo-support).

No Render Blueprint is added: the existing monorepo works with dashboard settings, while database
region, service plan and names remain your choices. No duplicate dependency manifest is needed.

## Render database

In the dashboard, select/create Render Postgres with PostgreSQL **17**, the major version tested
locally. Choose the same account and region for the database and web service. For persistent
production use, choose a plan with appropriate retention/backups; review the plan before creating
billable resources. Copy the database's **Internal Database URL** into the web service's
`DATABASE_URL` environment variable. Never put it in source code, Vercel, or chat.

Both `postgres://` and `postgresql://` are normalized to `postgresql+psycopg://` by the shared
settings class, used by the API, Alembic and admin CLI. Existing psycopg-specific URLs still work.
Credentials, percent encoding and query options are preserved. Use `sslmode=require` for encrypted
Render connections: append `?sslmode=require` when there is no query, or `&sslmode=require` when
there are other query parameters; replace any conflicting existing sslmode instead of duplicating it.
Render internal certificates do not support `verify-ca`/`verify-full`.
[Render connection and TLS documentation](https://render.com/docs/postgresql-creating-connecting).

Do not run `app.local_database init`, Docker Compose, `initdb`, test runners, or database-reset
commands on Render. Managed PostgreSQL already provides persistent storage; the web service's
filesystem is not the database.

## Render web service: exact settings

Create/configure a **Python 3 Web Service**, select the intended repository/branch, and use:

| Setting | Value |
| --- | --- |
| Root Directory | `backend` |
| Build Command | `uv sync --locked --no-dev` |
| Start Command | `.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT"` |
| Health Check Path | `/api/health` |
| Pre-Deploy Command, where supported | `.venv/bin/python -m alembic -c alembic.ini upgrade head` |
| Auto-Deploy | Off while reviewing initial configuration; enable later only if desired |

The start command has no reload mode, dependency installation, schema creation or migrations.
Render supplies `PORT`; do not hardcode 8000 or replace the binding with localhost.
[Render's FastAPI start-command guidance](https://render.com/docs/deploy-fastapi).

Configure environment variables in the **Render dashboard**:

| Variable | Required production value / existing default |
| --- | --- |
| `PYTHON_VERSION` | `3.12.15`, the locally tested interpreter |
| `UV_VERSION` | `0.13.5`, the locally tested uv version |
| `UV_PROJECT_ENVIRONMENT` | `.venv`, so install/start/migration paths agree |
| `DATABASE_URL` | Actual Render database URL, including the chosen TLS query option |
| `JWT_SECRET_KEY` | Independently generated production signing secret, at least 32 characters |
| `CORS_ORIGINS` | JSON array containing the actual Vercel production origin, e.g. `["https://YOUR-FRONTEND-HOST"]` after replacing the placeholder |
| `PORT` | Provided by Render; no manual value needed |
| `JWT_ALGORITHM` | Optional; existing default and only allowed value: `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Optional; existing default: `30` |
| `JWT_ISSUER` | Optional; existing default: `dealership-api` |
| `JWT_AUDIENCE` | Optional; existing default: `dealership-web` |

Keep issuer/audience stable across deployments unless intentionally invalidating old tokens. Generate
the signing secret locally with `python -c 'import secrets; print(secrets.token_hex(32))'`, enter it
only into Render's secret settings, and do not reuse the development `.env` key. Changing the key
invalidates existing tokens. No new production secret was generated for this preparation task.

`POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` and `POSTGRES_PORT` are **local/Compose** inputs,
not required FastAPI settings. The API reads the complete `DATABASE_URL`. Do not upload a `.env`;
hosted environment variables take precedence. `PYTHON_VERSION` is explicit because the repository's
root `.python-version` sits outside Render's `backend` service root.
[Render Python/runtime version configuration](https://render.com/docs/python-version).

`uv sync --locked --no-dev` uses the existing lock and fails if it is stale; it does not regenerate
it. The optional `dev` extra is not selected. Do not install with unpinned `pip install fastapi ...`
or regenerate the lock during deployment. The production installation and app imports were tested
in a fresh local copy without changing `backend/.venv`.
[uv lock and sync behavior](https://docs.astral.sh/uv/concepts/projects/sync/).

## Production migrations: separate, forward-only release step

Review pending migration code and confirm the target database/backup before applying migrations.
Run exactly this from Render's `backend` root:

```sh
.venv/bin/python -m alembic -c alembic.ini upgrade head
```

For a service with pre-deploy support, set that command in Render's **Pre-Deploy Command** field.
It runs after the build and before releasing the new service. Render currently provides this
feature for paid web services; do not assume it exists on a free service.
[Render deployment steps](https://render.com/docs/deploys#pre-deploy-command).

If your plan has no pre-deploy command, apply the same migration once from a trusted operator
machine or an appropriately configured one-off environment **before** releasing the API. Use the
external database URL for a machine outside Render, with TLS and the permitted network access.
The following optional procedure, from the repository root, prompts privately and does not put
the URL in shell history or overwrite your development `.env` (instructions only; not executed
against a hosted database):

```sh
backend/.venv/bin/python - <<'PY'
import getpass
import os
import subprocess
import sys

env = os.environ.copy()
env["DATABASE_URL"] = getpass.getpass("Render external database URL with sslmode=require: ")
if not env["DATABASE_URL"]:
    raise SystemExit("No database URL supplied; stopped")
subprocess.run(
    [sys.executable, "-m", "alembic", "-c", "backend/alembic.ini", "upgrade", "head"],
    env=env,
    check=True,
)
PY
```

Use one migration runner per release; do not run it concurrently from every API worker. If it
fails, investigate before releasing the app. Never run `downgrade base`, drop tables, reset the
cluster, or replace `upgrade head` with `create_all()` in startup. A code rollback does not reverse
a database migration; plan compatible forward migrations and backups instead.

After migration, from the Render service root:

```sh
.venv/bin/python -m alembic -c alembic.ini current
.venv/bin/python -m alembic -c alembic.ini check
```

Current repository head is `0003_user_name`. The health endpoint checks database connectivity,
not migration revision. Existing migrations add users, vehicles and an optional name; they preserve
existing records on upgrade. Destructive downgrade functions are only exercised in isolated tests.

## Vercel: exact settings

Import the intended repository and configure:

| Setting | Value |
| --- | --- |
| Root Directory | `frontend` |
| Framework Preset | Vite |
| Node.js Version | 22.x (project requires at least 22.12) |
| Install Command | `npm ci` |
| Build Command | `npm run build` |
| Output Directory | `dist` |

`frontend/vercel.json` supplies the install/build/output settings and rewrites non-file routes to
`/index.html`. This supports opening or refreshing `/login`, `/register` and `/inventory`; assets
are served from the filesystem before rewrites. Root Directory and Node version are dashboard
settings. `package.json` restricts Node to `>=22.12.0 <23` so Vercel cannot select a newer major
from an open-ended engine range.
[Vercel Node version precedence](https://vercel.com/docs/functions/runtimes/node-js/node-js-versions).
No Vercel API functions or backend proxy are added.
[Vercel Vite SPA guidance](https://vercel.com/docs/frameworks/frontend/vite#using-vite-to-make-spas).

Set **`VITE_API_BASE_URL`** in Vercel's **Production** environment to:

```text
https://YOUR-ACTUAL-RENDER-HOST/api
```

Use the actual service URL displayed by Render; the text above is a placeholder, not a deployed
address. The `/api` suffix is required because the client appends `/auth/login`, `/vehicles`, etc.
An optional trailing slash is removed by the client. Do not use `/api` alone, localhost, an internal
database host, or `API_PROXY_TARGET` for the Vercel deployment. `API_PROXY_TARGET` controls only
Vite's local development server. `VITE_CURRENCY` is optional and defaults to `INR`; it is display
metadata, not currency conversion.

Vite embeds `VITE_API_BASE_URL` during the build. Redeploy the frontend after changing it. Never set
`DATABASE_URL`, passwords or `JWT_SECRET_KEY` on Vercel: all `VITE_*` values are public browser data.
Use a separate staging API/database for previews, or leave preview API access unconfigured. Do
not point every preview at production by default.

## Match origins and verify after your approved deployment

Once the actual Vercel production domain is known, set Render's `CORS_ORIGINS` to a JSON array of
that exact HTTPS origin, without a path or trailing slash. Include a custom domain only if you
serve the frontend there. Update/redeploy the Render service after changing its environment.
Do not use `*` or a wildcard for all Vercel previews. Bearer authentication uses the Authorization
header; browser cookies and `allow_credentials=True` are not required.

After you choose to publish/deploy, manually verify the actual sites:

1. `/api/health` returns 200 and migrations report head; database connection failures return 503.
2. Refresh `/inventory` directly on Vercel; the SPA loads and unauthenticated users reach login.
3. Register/login from Vercel; confirm the browser calls the Render HTTPS `/api` URL and CORS
   permits that origin. Inspect errors locally without copying JWTs or credentials into logs/chat.
4. Exercise create/search/pagination/edit/purchase, zero-stock behavior and logout.
5. Register the intended administrator yourself; in a trusted Render shell at the backend root,
   explicitly run `.venv/bin/python -m app.cli promote-admin --email 'YOUR_REGISTERED_EMAIL'`.
   If shell access is unavailable, use a trusted operator environment with the hosted database URL,
   following the private-input pattern above. No user is promoted automatically.
6. Refresh the profile and verify admin restock/delete; normal users must still receive 403.

## Local preparation checks and limits

Run the existing suites and this local production-command rehearsal:

```sh
backend/.venv/bin/python scripts/test_backend.py --pg-bin .tools/postgres/bin -q --tb=short
export PATH="$PWD/.tools/node/bin:$PATH"
npm --prefix frontend run test
npm --prefix frontend run lint
VITE_API_BASE_URL=https://api.example/api npm --prefix frontend run build
backend/.venv/bin/python scripts/verify_render.py --uv-bin .tools/uv/bin/uv --pg-bin .tools/postgres/bin
```

`api.example` is a reserved test domain used only to verify the build-time URL; it is not a live
API and must not be copied to your dashboard. The rehearsal copies backend sources into a private
temporary directory, installs production dependencies, creates a separate local database, runs
exact migration/start commands, checks PORT binding, readiness and an HTTPS-origin preflight, then
stops/removes its own resources. It never uses your existing database or calls Render/Vercel.

See [TEST_REPORT.md](TEST_REPORT.md) for actual results. Render Linux execution, hosted TLS,
Vercel routing/CDN behavior, actual domain CORS and production performance still require verification
on the chosen services. Deployment files and instructions alone are not evidence of a successful
hosted deployment. Review changes, then authorize publication/deployment separately.
