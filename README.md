# Car Dealership Inventory System

A two-day MVP project for authenticated vehicle inventory, customer purchases and admin stock
management. Stack: FastAPI, SQLAlchemy 2, Pydantic, Alembic, PostgreSQL, JWT/Argon2, React,
TypeScript, Vite and Tailwind CSS.

**Current status: full-stack local MVP implemented and verified.** The React app includes
registration/login, protected sessions, a responsive inventory dashboard, combined search, pagination,
create/edit forms, one-unit purchases, and admin restock/delete dialogs. FastAPI enforces permissions
and atomic stock changes. Final verification on 2026-10-25: **135 backend tests, 25 frontend tests
and three Chromium workflows passed**. Persistent local setup, restart checks and operator-only admin
provisioning are implemented. This workspace has an empty migrated development database; no real
application user was created or promoted.
See [the plan and requirements checklist](docs/IMPLEMENTATION_PLAN.md) and
[actual verification results](docs/TEST_REPORT.md).

The [historical workspace and Git audit](docs/WORKSPACE_AUDIT.md) records an earlier milestone.
Use this README and the latest test-report section for current setup and results.

## Workspace layout

```text
backend/
  app/                  Routes, settings/security, User/Vehicle models, schemas and services
  app/cli.py            Operator-only promotion of an existing account to admin
  app/local_database.py  Safe persistent local database initialization/start/stop/status
  migrations/           Users, vehicles and backward-compatible optional user-name migrations
  tests/                pytest/TestClient tests against isolated PostgreSQL
  pyproject.toml        Backend runtime and development dependencies
  uv.lock               Resolved backend dependency versions and package hashes
frontend/
  src/                  Auth context, API client, pages, dialog components and component tests
  e2e/                  Playwright journeys against the live API
  package-lock.json     Reproducible npm dependencies
  .env.example          Public API path, development proxy and display currency
docs/                   Implementation checklist, test report and actual screenshots
scripts/test_backend.py Temporary PostgreSQL cluster, migration checks and test runner
scripts/test_frontend_integration.py Disposable PostgreSQL/API/Vite browser-test runner
scripts/verify_local_setup.py Fresh setup, CLI and API/database restart/outage verification
compose.yaml            Optional PostgreSQL service with persistent named storage
.env.example            Configuration names and intentionally empty secrets
PROMPTS.md              Actual user prompt excerpt from this conversation
```

## Prerequisites

Use Python 3.12 and PostgreSQL 17 for the backend. Docker Desktop with Compose v2 can run the
included persistent development database; a local PostgreSQL server also works. Use uv to install
the locked backend dependencies. The frontend needs Node.js 22 (at least 22.12) with npm.
Vite 7, Vitest 5, React 19 and Tailwind 4 are installed and locked in `frontend/package-lock.json`.

On 2026-10-24, uv and Python 3.12.15 were installed under ignored `.tools/`, and backend dependencies
were installed in `backend/.venv`. PostgreSQL 17.11 was built from its checksum-verified official
source into `.tools/postgres/` for isolated tests. The original Python 3.9 root `.venv` is preserved.
Node 22.23.4/npm 10.9.9 were subsequently installed under `.tools/node`, and Playwright Chromium
under `.tools/browsers`. Docker remains unavailable. Test runners shut down and remove their
temporary clusters. On 2026-10-25 a separate persistent development cluster was initialized
under ignored `.tools/dev-postgres` on port 55432. It remains running, with no application users
or vehicles. Its generated `.env` and operator-password file are private and ignored. Do not delete
`.tools` as cache: it now contains your persistent database as well as the earlier downloaded tools.

## Fresh macOS setup

Use a terminal in the project root. Do not edit files inside `.venv`, `node_modules` or caches.
The application source is in `backend/app` and `frontend/src`.

### Install prerequisites and locked dependencies

On a fresh Mac with [Homebrew](https://brew.sh/) installed:

```sh
brew install uv node@22 postgresql@17
export PATH="$(brew --prefix node@22)/bin:$PATH"
uv sync --project backend --extra dev --locked
npm --prefix frontend ci
```

The official [uv](https://formulae.brew.sh/formula/uv),
[Node 22](https://formulae.brew.sh/formula/node@22) and
[PostgreSQL 17](https://formulae.brew.sh/formula/postgresql@17) formula pages were checked.
Homebrew itself is not installed here, so those installation commands were not executed on this Mac.
The locked uv/npm dependency installs and the remaining setup were verified with local binaries.
uv supplies Python 3.12 when needed. Use Node 22.12+; the tested version is 22.23.4.

In **this already-prepared workspace**, use the existing binaries instead:

```sh
export PATH="$PWD/.tools/node/bin:$PATH"
UV_PYTHON_INSTALL_DIR="$PWD/.tools/python" .tools/uv/bin/uv sync --project backend --extra dev --locked
npm --prefix frontend ci
```

### Option A: dedicated persistent database (verified)

For a **fresh clone without a root `.env`**, run:

```sh
backend/.venv/bin/python -m app.local_database init --pg-bin "$(brew --prefix postgresql@17)/bin"
backend/.venv/bin/python -m alembic -c backend/alembic.ini upgrade head
backend/.venv/bin/python -m alembic -c backend/alembic.ini current
backend/.venv/bin/python -m alembic -c backend/alembic.ini check
```

On this prepared Mac, replace the `--pg-bin` argument with `.tools/postgres/bin`.
**Initialization has already been run here; do not rerun init to start the database.**

The initializer creates `.tools/dev-postgres/data`, listens only on `127.0.0.1:55432`, uses SCRAM
password authentication, and creates a database owned by an application role without superuser,
create-role or create-database privileges. Random database/JWT secrets are written to a new root
`.env` with mode 0600; none are printed. The cluster operator password is stored privately under
`.tools/dev-postgres/operator-password`. It creates no application account. `--port` can select a
free port during init; later starts reuse the recorded port. TCP only is used for this local cluster.

Init refuses to overwrite **any existing `.env` or managed cluster**, including a partial previous
setup. It never deletes data. If a failure leaves files, inspect them and the local log; do not remove
an existing configuration/database to bypass the guard. Configure an existing server manually using
Option B. Exported `DATABASE_URL`/JWT variables override `.env`; unset stale exports if necessary.

Manage this workspace's database as your normal macOS user:

```sh
backend/.venv/bin/python -m app.local_database status --pg-bin .tools/postgres/bin
backend/.venv/bin/python -m app.local_database stop --pg-bin .tools/postgres/bin
backend/.venv/bin/python -m app.local_database start --pg-bin .tools/postgres/bin
```

Use your Homebrew PostgreSQL bin directory on a fresh machine. Stop/start retain all data; after
reboot, use start. This is not installed as a login service. A second start of an already-running
server returns a nonzero pg_ctl result; use status first. No reset/delete command is provided.
Back up your database before removing the checkout or `.tools`. The bundled PostgreSQL build lacks
TLS and is restricted to local development; use a standard PostgreSQL distribution for remote hosting.

### Option B: existing PostgreSQL or Docker (manual alternative)

Preserve existing configuration. If no `.env` exists, copy the example and generate separate secrets:

```sh
cp -n .env.example .env
chmod 600 .env
backend/.venv/bin/python -c 'import secrets; print(secrets.token_hex(32))'
```

Run the generator separately for each secret and enter them locally; never paste secrets into chat
or commit them. Set `POSTGRES_PASSWORD`, `DATABASE_URL` and `JWT_SECRET_KEY`. The URL must use
`postgresql+psycopg://USER:PASSWORD@HOST:PORT/DATABASE`. Percent-encode reserved password characters;
generated hex values need no encoding. JWT secrets need at least 32 characters.

For a server you administer, PostgreSQL's `createuser` and `createdb` can create a dedicated role
and database without resetting other databases (replace the administrator name and server details):

```sh
createuser -h 127.0.0.1 -p 5432 -U YOUR_DB_ADMIN --pwprompt --no-superuser --no-createdb --no-createrole dealership
createdb -h 127.0.0.1 -p 5432 -U YOUR_DB_ADMIN --owner=dealership dealership
```

These manual commands were not executed against an external server. If either object already
exists, inspect/reuse it instead of dropping it. Configure `.env` to match and run `alembic upgrade
head` as above. Do not run test-only downgrades on your development database.

Alternatively, with Docker Desktop installed, a configured `.env`, and a free configured port:

```sh
docker compose config --quiet
docker compose up -d db
docker compose ps
```

Docker was unavailable during verification. The Compose service binds to localhost and uses the
`postgres_data` named volume. Never use `docker compose down -v` if data must be preserved.
Changing `.env` does not change passwords inside an already initialized volume. Do not run both
local PostgreSQL and Compose on the same port. Compose's POSTGRES_USER is its bootstrap role;
Option A uses a separate, restricted application role.

### Environment and application startup

Both the API and Alembic read the root `.env`; shell environment variables take precedence.
`JWT_ALGORITHM=HS256`, a default 30-minute expiry, issuer and audience are validated.
`CORS_ORIGINS=["http://localhost:5173"]` allows the local frontend; add exact origins only as needed.
Frontend `VITE_*` values are public and must never contain signing/database secrets.

Start the API in one terminal, from the project root:

```sh
backend/.venv/bin/python -m alembic -c backend/alembic.ini upgrade head
backend/.venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In another terminal, with Node on PATH:

```sh
cp -n frontend/.env.example frontend/.env
npm --prefix frontend run dev
```

Open `http://localhost:5173`. API docs: `http://127.0.0.1:8000/docs`.
`http://127.0.0.1:8000/api/health` returns 200 when PostgreSQL is reachable, or sanitized 503 when
unavailable. Authentication/inventory requests also return a clear 503 on connection failures.
The UI offers retry for API/network errors. Health checks connectivity, not schema revision;
run migrations before starting. Current migration head is `0003_user_name`. Additive upgrades
preserve users, and migration round trips are tested only in isolated test databases.

## Provision the first admin

1. Register the intended account through the UI. It initially has role `user`.
2. In a trusted local terminal, verify that `.env`/exported `DATABASE_URL` points to the intended
   database. Run the following with that account's real email:

```sh
backend/.venv/bin/python -m app.cli promote-admin --email 'YOUR_REGISTERED_EMAIL'
```

The command validates and normalizes the email exactly as login does. It locks the matching user,
changes only the role and update timestamp, and commits the transaction. Rerunning reports
`already an admin` without changing the account. Missing users fail with exit 1 and create nothing;
missing/invalid email fails with exit 2. Database/configuration failures return a sanitized error.
It never asks for or replaces the user's password. Refresh the browser to reload the role.

**Authorization boundary:** this is a database-operator command, not an API endpoint. Anyone who
can run it with the application's database credentials already has database write authority. Keep
those credentials private; ordinary JWT holders cannot invoke the CLI through HTTP, and public
registration continues to reject `role`/`is_admin`. There is no default admin password or public
promotion route. No real account has been promoted in this workspace; only disposable test users
were promoted while verifying the command.

## Authentication API

| Endpoint | JSON input | Result |
| --- | --- | --- |
| `POST /api/auth/register` | `email`, `password`, optional `name` | 201: ID, normalized email, name, role and timestamps |
| `POST /api/auth/login` | `email`, `password` | 200: `access_token`, `token_type`, `expires_in` |
| `GET /api/auth/me` | Bearer token | 200: current user profile and authoritative role |
| `GET /api/health` | None | PostgreSQL readiness, 200 or 503 |

The registration UI requires a name (1–100 characters after trimming); the API keeps it optional
for existing clients. Existing accounts with no name display their email.
Email is trimmed, validated and lowercased for registration and login. Registration passwords must
be 12–128 characters and are stored only as Argon2id hashes. Registration always assigns `user`;
unknown fields including `role` and `is_admin` return 422. Duplicate email returns 409. Incorrect
login credentials return a generic 401 with a Bearer challenge. Validation errors omit raw input.

Protected inventory routes depend on `CurrentUser` or `AdminUser` from
`backend/app/api/dependencies.py`. These validate signature, expiry, issuer, audience and required
claims, then load the user and role from PostgreSQL. Missing/invalid tokens return 401; insufficient
role returns 403. The operator CLI above provisions admins; there are no default admin credentials
or public role-changing endpoints. Authorization tests use test-only routes, absent from the real application.

## Vehicle API

Every vehicle endpoint requires `Authorization: Bearer <access_token>`. Per the updated inventory
requirements, regular authenticated users can create and update vehicles. Delete and restock
require an admin role, enforced by the backend.

| Endpoint | Access | Success |
| --- | --- | --- |
| `POST /api/vehicles` | Authenticated | 201, created vehicle |
| `GET /api/vehicles` | Authenticated | 200, paginated vehicles |
| `GET /api/vehicles/search` | Authenticated | 200, filtered paginated vehicles |
| `PUT /api/vehicles/{id}` | Authenticated | 200, updated vehicle details |
| `DELETE /api/vehicles/{id}` | Admin | 204, empty response |
| `POST /api/vehicles/{id}/purchase` | Authenticated | 200, vehicle after buying one unit |
| `POST /api/vehicles/{id}/restock` | Admin | 200, vehicle after stock increment |

Create body example (sample inventory data, not a seeded record):

```json
{
  "make": "Toyota",
  "model": "Corolla",
  "category": "Sedan",
  "price": "24500.25",
  "quantity": 2
}
```

Responses include a generated UUID, these fields, and `created_at` / `updated_at` timestamps.
Prices use PostgreSQL `NUMERIC(12,2)` and Python Decimal; JSON responses encode them as strings.
Prices must be positive, finite, at most `9999999999.99`, with no more than two fractional digits.
Stock must be a JSON integer from 0 to 2147483647; booleans, numeric strings and fractional stock
are rejected. Make/model/category are trimmed, nonempty strings limited to 100/100/50 characters.
Unknown fields are rejected.

`PUT` requires all four descriptive fields (`make`, `model`, `category`, `price`). It rejects
`quantity`: after creation, stock changes only through purchase/restock. This prevents a stale
edit form from restoring purchased stock and prevents users bypassing admin restock authorization.
Purchase takes no body and buys exactly one unit. Restock takes `{"quantity": 3}` and requires a
positive integer increment. Both operations use atomic SQL updates; purchases condition the
decrement on positive stock, and restocks check for integer overflow. A database check also
forbids negative stock. Successful details and stock updates refresh `updated_at`.

List and search accept `limit` (default 20, range 1–100) and `offset` (default 0, range
0–2147483647). Responses have `items`, `total`, `limit`, and `offset`; results sort by creation
timestamp then UUID. An empty or beyond-end page has an empty `items` list. Counts/pages reflect
current reads and can change as other users modify inventory.

Search accepts any combination of `make`, `model`, `category`, `min_price`, and `max_price`.
Make/model match case-insensitive substrings, with `%` and `_` treated literally. Category is an
exact case-insensitive match. Price bounds are inclusive and nonnegative; minimum above maximum
is rejected. For example: `/api/vehicles/search?make=toy&category=sedan&max_price=30000&limit=20`.
The static `/search` route is declared before dynamic vehicle-ID routes.

Missing vehicles return 404; out-of-stock purchases and stock overflow return 409. Missing or
invalid tokens return 401, insufficient role 403, and invalid bodies/queries/UUIDs 422. Error
responses use a `detail` field; validation errors use a list of field errors within that field.

Each request owns a SQLAlchemy session. Account services commit successful writes and roll back
failed writes; the dependency closes the session and rolls back outstanding work. The initial
migration uses timezone-aware timestamps; ORM updates refresh `updated_at`. Direct SQL updates
must update that timestamp explicitly. Password rehashing occurs after successful login when needed.

## Frontend setup and architecture

In a second terminal, from the project root on this Mac:

```sh
export PATH="$PWD/.tools/node/bin:$PATH"
npm --prefix frontend ci
npm --prefix frontend run dev
```

On another machine, install Node 22.12+ and omit the PATH line. Open `http://localhost:5173`.
The API from the backend instructions must be running on port 8000 with its database migrated.
Register your own account; there are no demo credentials or automatically granted admin roles.
Admin controls require an account provisioned by the database operator with role `admin`.
Use `python -m app.cli promote-admin --email ...` through the backend environment as documented above.

Frontend configuration belongs in ignored `frontend/.env`, copied from its example:

| Variable | Default | Purpose |
| --- | --- | --- |
| `VITE_API_BASE_URL` | `/api` | Public API prefix included in the browser bundle |
| `API_PROXY_TARGET` | `http://127.0.0.1:8000` | Vite development proxy destination |
| `VITE_CURRENCY` | `INR` | ISO currency for display; prices do not include a stored currency |

Restart Vite after changing configuration. Never put passwords or JWT signing secrets in `VITE_*`.
The development proxy avoids cross-origin browser requests. For a direct API URL, set the backend's
`CORS_ORIGINS` to the exact frontend origin. A production host must serve the SPA fallback and route
`/api` to FastAPI, or configure a public API URL and CORS before building. Vite's proxy is development
only; this project has not been deployed.

- `auth/AuthProvider.tsx` owns login/logout, profile loading and expiry. `sessionStorage` retains the
  bearer token across refreshes within a tab; closing the tab normally ends that session. It is
  JavaScript-accessible, so preventing XSS remains important. No password is stored. Storage-disabled
  browsers retain an in-memory session only. No refresh tokens are implemented.
- The client decodes expiry only for UX; `/auth/me` and every backend endpoint validate signatures.
  Roles come from the database profile. Authenticated 401 responses clear the matching session;
  transient network errors offer retry. A 403 does not incorrectly log the user out.
- `lib/api.ts` attaches bearer headers and translates API/network errors. `pages/InventoryPage.tsx`
  owns filters, pagination and refreshes; requests are aborted when filters or pages change.
- `components/VehicleDialog.tsx` handles create/edit/restock/delete with a native modal, labelled
  inputs, keyboard dismissal and destructive confirmation. PUT excludes stock; purchases always
  buy one unit. A stock conflict refreshes the inventory and displays the API error.
- Prices are submitted as decimal strings. Numeric conversion is only for display and input-range
  comparisons; persistence and arithmetic remain Decimal/NUMERIC in the backend.

Dashboard stock summaries describe the current page, while the vehicle count comes from the API's
filtered total. Purchases are disabled at zero stock or while another purchase is pending.

## Backend verification

From the project root, using the binaries already prepared in this workspace:

```sh
backend/.venv/bin/python scripts/test_backend.py --pg-bin .tools/postgres/bin -q
backend/.venv/bin/python -m ruff check backend scripts
backend/.venv/bin/python -m ruff format --check backend scripts
```

The runner creates a new PostgreSQL cluster under a private temporary directory and listens only
on its Unix socket. It migrates to users, inserts a temporary account, then verifies that the full
user row survives vehicle upgrade and downgrade. It also checks schema drift and the complete
migration round trip, runs pytest, and stops the server. It never connects to the development
database or consumes `.env` credentials. Trust
authentication is limited to this private temporary test cluster. The locally compiled PostgreSQL
build does not include TLS; it is used only for isolated tests and loopback development. Use a
standard PostgreSQL distribution/managed server for remote deployment.

Alternatively, explicitly export `TEST_DATABASE_URL` for a dedicated PostgreSQL database ending
in `_test` and run `backend/.venv/bin/python -m pytest backend/tests -q`. Tests never fall back to
`DATABASE_URL`; they reject equality with it. Each suite creates its own random schema, migrates
it, rolls back individual tests and drops only that schema. The test database user must be allowed
to create schemas. Do not supply a production database.

Current result: **135 passed**, including all 122 previous cases plus admin CLI, safe setup guards
and sanitized database-outage tests.
Concurrent tests use real independent PostgreSQL transactions: eight buyers
compete for one or three units; parallel restocks preserve every increment; edits during purchase
do not restore stock; mixed purchases/restocks preserve totals. Migration checks and Ruff passed.
One upstream Starlette warning about the httpx TestClient adapter remains. See [the test report](docs/TEST_REPORT.md)
for exact commands and results.

## Frontend verification

From the project root:

```sh
export PATH="$PWD/.tools/node/bin:$PATH"
npm --prefix frontend run test
npm --prefix frontend run lint
npm --prefix frontend run build
npm --prefix frontend audit --audit-level=moderate
```

Actual results: **25 tests passed**, ESLint and TypeScript/Vite build passed. npm reported zero
known vulnerabilities after upgrading the scaffold's Vitest dependency. The build writes ignored
`frontend/dist/`. This does not start a production deployment.

For reproducible browser integration and screenshot capture:

```sh
export PATH="$PWD/.tools/node/bin:$PATH"
export PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/browsers"
(cd frontend && npx playwright install chromium)
backend/.venv/bin/python scripts/test_frontend_integration.py --pg-bin .tools/postgres/bin
```

The browser runner starts a private temporary PostgreSQL database, applies all migrations, creates
an admin with a random disposable password, and runs FastAPI on 8001 and Vite on 5175. Keep those
ports free. It verifies health and CORS, runs **three passing Chromium workflows**, then stops
all services and removes the database. It never points at your persistent database. Browser tests
use genuine API requests, while unit tests mock fetch. On another machine, provide the installed
PostgreSQL binary directory with `--pg-bin`. Local service logs are ignored in `.tools/`.

The browser journeys cover registration, login, CRUD, search, pagination, purchases to zero,
refresh persistence, logout, invalid sessions, admin restock/delete confirmation and Escape dismissal.
The third journey simulates a refused API network request, checks the error message and retries
successfully against the real API. The mobile viewport check detects horizontal overflow.
Firefox/Safari and production hosting have not been verified.

Verify fresh persistent setup and restarts independently:

```sh
backend/.venv/bin/python scripts/verify_local_setup.py --pg-bin .tools/postgres/bin
```

This creates a disposable SCRAM-authenticated cluster on 55441 and an API on 8002. It tests the
same initializer, migrations, real CLI promotion/rerun, API shutdown/restart, database shutdown/503
responses/restart, and exact preservation of user and vehicle records. It never targets your existing
`.env` or persistent database and removes only its own temporary directory after stopping services.
Keep these ports free. All persistence/outage checks passed on 2026-10-25.

## Screenshots

These are actual Chromium captures from the live integration run using disposable sample inventory.
The desktop and mobile captures occur at different points in the purchase workflow, so stock differs.
The browser runner now writes new captures to ignored `.tools/browser-screenshots/` to preserve
these existing evidence files. Review new captures before explicitly copying them into
`docs/screenshots/`. No real account credentials are shown.

![Inventory dashboard](docs/screenshots/inventory-desktop.png)

<details>
<summary>Mobile inventory</summary>

<img src="docs/screenshots/inventory-mobile.png" alt="Inventory on a 390-pixel mobile viewport" width="300" />

</details>

[Login screenshot](docs/screenshots/login.png) · [Registration screenshot](docs/screenshots/registration.png)

## My AI Usage

- **Tool:** OpenAI Codex, acting as an engineering assistant in the local workspace.
- **Input:** the user's complete specification and scoped first task. A verbatim user-message
  excerpt is preserved in [PROMPTS.md](PROMPTS.md); it is not an invented public chat link.
- **Work contributed:** the initial scaffold and plan, followed by PostgreSQL session management,
  the users migration/model, authentication schemas and routes, Argon2/JWT utilities, reusable
  authorization dependencies, CORS, isolated integration tests and their temporary database runner.
  The vehicle milestone adds its model/migration, schemas, seven endpoints, stock services,
  PostgreSQL concurrency tests, migration preservation checks and frontend API documentation.
  The frontend milestone adds the React workflows, API/session handling, component/browser tests,
  actual screenshots and setup documentation, plus optional names and `/auth/me` in the existing API.
  The final setup milestone adds safe persistent local PostgreSQL initialization, operator-only
  account promotion, outage responses, tests and restart-persistence verification.
- **Engineering choices:** preserve the original virtual environment, use a separate Python 3.12
  environment, keep secrets out of Git, plan backend role enforcement and atomic stock changes.
  The user's later specification explicitly allows authenticated users to add/update vehicle
  details; it supersedes the original admin-only assumption. Stock edits use dedicated endpoints.
- **Verification and limits:** six authentication tests first failed with 404. Implementation and
  expanded tests initially produced 38 passes and three overly broad test assertions; those assertions
  were corrected. The next run passed all 41 tests. Account logic was then extracted from route
  handlers into a service module and the full suite rerun. Vehicle development first recorded four
  expected failures, then 45 passes for create/list; five further behavior checks failed before
  implementing the remaining endpoints. The backend at that milestone passed 122 cases. Frontend tests initially
  had one ambiguous price matcher
  (24 passed, one failed); scoping it to the intended vehicle fixed the assertion, yielding 25 passes.
  ESLint/build and two live Chromium workflows passed. A dependency audit prompted a Vitest upgrade;
  the resolved dependency tree reports zero known vulnerabilities. All database verification used
  temporary data. Migration preservation and drift checks ran. Docker remains unverified, and these
  checks do not claim production load testing.
- **Final verification (2026-10-25):** the initial admin test collection failed because the CLI
  did not exist. After implementation, ten targeted tests passed. The complete suite now passes
  135 backend and 25 frontend tests plus three Chromium journeys. Persistent setup, real promotion,
  downtime recovery and complete-row preservation across restarts passed on disposable data.
  An empty local development database was then initialized and migrated without creating users.
- **Human review:** review authorization assumptions, install prerequisites, then inspect real test
  results and the UI at each milestone. No human review or acceptance is claimed yet.
- **Ongoing record:** append actual future prompt/response excerpts or genuine public links;
  record important failing tests, passing results and corrections as development proceeds.
- **Attribution:** AI-assisted commits use `Co-authored-by: Codex <noreply@openai.com>`.
  No pre-existing project-specific trailer rule was found. Local commits are allowed by the task;
  remote pushes and deployment require explicit approval.

## References consulted

- [Vite setup and Node requirements](https://vite.dev/guide/)
- [Tailwind's Vite integration](https://tailwindcss.com/docs/installation/using-vite)
- [FastAPI JWT and password hashing](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)
- [SQLAlchemy 2.0 documentation](https://docs.sqlalchemy.org/en/20/intro.html)
- [Vitest setup](https://vitest.dev/guide/)
- [Official PostgreSQL image and storage configuration](https://hub.docker.com/_/postgres)
