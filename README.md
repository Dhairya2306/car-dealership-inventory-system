# Car Dealership Inventory System

A two-day MVP project for authenticated vehicle inventory, customer purchases and admin stock
management. Stack: FastAPI, SQLAlchemy 2, Pydantic, Alembic, PostgreSQL, JWT/Argon2, React,
TypeScript, Vite and Tailwind CSS.

**Current status: authentication and vehicle inventory backend implemented and tested.** Registration,
login, JWT/role checks, database readiness, vehicle CRUD/search, pagination and atomic stock changes
are available. Frontend workflows remain unimplemented; the UI still has a setup screen.
See [the plan and requirements checklist](docs/IMPLEMENTATION_PLAN.md) and
[actual verification results](docs/TEST_REPORT.md).

The [workspace and Git audit](docs/WORKSPACE_AUDIT.md) lists the existing files, verified features,
remaining work and steps for creating a GitHub repository before an explicitly approved push.

## Workspace layout

```text
backend/
  app/                  Routes, settings/security, User/Vehicle models, schemas and services
  migrations/           Alembic environment, users migration and additive vehicles migration
  tests/                pytest/TestClient tests against isolated PostgreSQL
  pyproject.toml        Backend runtime and development dependencies
  uv.lock               Resolved backend dependency versions and package hashes
frontend/
  src/                  React entry point, starter screen, styles and test setup
  package.json          Frontend dependencies and scripts
docs/                   Implementation checklist, test report and future screenshots
scripts/test_backend.py Temporary PostgreSQL cluster, migration checks and test runner
compose.yaml            Optional PostgreSQL service with persistent named storage
.env.example            Configuration names and intentionally empty secrets
PROMPTS.md              Actual user prompt excerpt from this conversation
```

## Prerequisites

Use Python 3.12 and PostgreSQL 17 for the backend. Docker Desktop with Compose v2 can run the
included persistent development database; a local PostgreSQL server also works. Use uv to install
the locked backend dependencies. The frontend will need Node.js 22 (at least 22.12) with npm.
Its Vite 7/Vitest 3 dependencies are still unverified and have no lockfile yet.

On 2026-10-24, uv and Python 3.12.15 were installed under ignored `.tools/`, and backend dependencies
were installed in `backend/.venv`. PostgreSQL 17.11 was built from its checksum-verified official
source into `.tools/postgres/` for isolated tests. The original Python 3.9 root `.venv` is preserved.
Docker and Node/npm are still unavailable. The test runner shuts down and removes its temporary
cluster; it does not leave a development database running.

## Local setup

The isolated tests and migrations have run successfully. The following persistent development
setup still requires your local database credentials; no `.env` or development accounts were created.

From the project root, copy the example without overwriting an existing configuration:

```sh
cp -n .env.example .env
backend/.venv/bin/python -c 'import secrets; print(secrets.token_hex(32))'
```

Use independently generated values for `POSTGRES_PASSWORD` and `JWT_SECRET_KEY` in `.env`.
Put the same database password into `DATABASE_URL`; hexadecimal values need no URL encoding.
If you change the database/user/port, update the URL accordingly. Never commit `.env`.
The API requires a JWT secret of at least 32 characters, fixes the signing algorithm to HS256,
and issues tokens with a configurable expiry (30 minutes by default), issuer and audience.
`CORS_ORIGINS` is a JSON list of exact allowed origins; the default is `http://localhost:5173`.

With Docker installed and running:

```sh
docker compose config --quiet
docker compose up -d db
docker compose ps
```

The database port binds to localhost. The `postgres_data` named volume persists data across
container recreation and ordinary `docker compose down`. Do not remove the volume if you need
the data. Initialization variables apply to a fresh database volume; changing `.env` does not
change existing database passwords. Without Docker, create a local database and user and set
`DATABASE_URL` to that instance.

Backend, from this workspace's project root (the installed uv executable is shown):

```sh
.tools/uv/bin/uv sync --project backend --extra dev --locked
source backend/.venv/bin/activate
python -m alembic -c backend/alembic.ini upgrade head
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

On another machine with uv installed, replace `.tools/uv/bin/uv` with `uv`; it can obtain Python 3.12.
Both the API and Alembic load the root `.env`, with exported environment variables taking precedence.
The migrations create `users` and `vehicles` with their validation constraints. Upgrading an
existing `0001_create_users` database to `0002_create_vehicles` preserves its user records.
Alembic needs only `DATABASE_URL`; starting the API also requires `JWT_SECRET_KEY`.

The readiness endpoint is `http://127.0.0.1:8000/api/health`; interactive API docs are at `/docs`.
Readiness executes `SELECT 1` and returns 200 with `{"status":"ok","database":"ok"}`, or 503
without connection details when PostgreSQL is unavailable. It does not check schema revisions.

## Authentication API

| Endpoint | JSON input | Result |
| --- | --- | --- |
| `POST /api/auth/register` | `email`, `password` | 201: ID, normalized email, role and timestamps |
| `POST /api/auth/login` | `email`, `password` | 200: `access_token`, `token_type`, `expires_in` |
| `GET /api/health` | None | PostgreSQL readiness, 200 or 503 |

Email is trimmed, validated and lowercased for registration and login. Registration passwords must
be 12–128 characters and are stored only as Argon2id hashes. Registration always assigns `user`;
unknown fields including `role` and `is_admin` return 422. Duplicate email returns 409. Incorrect
login credentials return a generic 401 with a Bearer challenge. Validation errors omit raw input.

Protected inventory routes depend on `CurrentUser` or `AdminUser` from
`backend/app/api/dependencies.py`. These validate signature, expiry, issuer, audience and required
claims, then load the user and role from PostgreSQL. Missing/invalid tokens return 401; insufficient
role returns 403. Admin provisioning is deferred; there are no default admin credentials or public
role-changing endpoints. Authorization tests use test-only routes, absent from the real application.

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

Frontend, in a second terminal:

```sh
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` to port 8000. The frontend requires no secret
environment variables. After the first verified install, use `npm ci` with the generated lockfile.

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
build is for testing and does not include TLS; use the Compose image or your managed server for
normal development/deployment.

Alternatively, explicitly export `TEST_DATABASE_URL` for a dedicated PostgreSQL database ending
in `_test` and run `backend/.venv/bin/python -m pytest backend/tests -q`. Tests never fall back to
`DATABASE_URL`; they reject equality with it. Each suite creates its own random schema, migrates
it, rolls back individual tests and drops only that schema. The test database user must be allowed
to create schemas. Do not supply a production database.

Current result: **118 passed**, including all 41 existing authentication/foundation tests and
77 inventory cases. Concurrent tests use real independent PostgreSQL transactions: eight buyers
compete for one or three units; parallel restocks preserve every increment; edits during purchase
do not restore stock; mixed purchases/restocks preserve totals. Migration checks and Ruff passed.
One upstream Starlette warning about the httpx TestClient adapter remains. See [the test report](docs/TEST_REPORT.md)
for exact commands and results. Frontend tests/build and browser review remain pending.

## Screenshots

Pending a running application. Actual captures will be saved under `docs/screenshots/` and
embedded here after the UI is implemented and reviewed. No screenshots or deployment URLs
are claimed by this scaffold.

## My AI Usage

- **Tool:** OpenAI Codex, acting as an engineering assistant in the local workspace.
- **Input:** the user's complete specification and scoped first task. A verbatim user-message
  excerpt is preserved in [PROMPTS.md](PROMPTS.md); it is not an invented public chat link.
- **Work contributed:** the initial scaffold and plan, followed by PostgreSQL session management,
  the users migration/model, authentication schemas and routes, Argon2/JWT utilities, reusable
  authorization dependencies, CORS, isolated integration tests and their temporary database runner.
  The vehicle milestone adds its model/migration, schemas, seven endpoints, stock services,
  PostgreSQL concurrency tests, migration preservation checks and frontend API documentation.
- **Engineering choices:** preserve the original virtual environment, use a separate Python 3.12
  environment, keep secrets out of Git, plan backend role enforcement and atomic stock changes.
  The user's later specification explicitly allows authenticated users to add/update vehicle
  details; it supersedes the original admin-only assumption. Stock edits use dedicated endpoints.
- **Verification and limits:** six authentication tests first failed with 404. Implementation and
  expanded tests initially produced 38 passes and three overly broad test assertions; those assertions
  were corrected. The next run passed all 41 tests. Account logic was then extracted from route
  handlers into a service module and the full suite rerun. Vehicle development first recorded four
  expected failures, then 45 passes for create/list; five further behavior checks failed before
  implementing the remaining endpoints. The expanded backend now passes 118 cases. All database
  work used temporary test data. Migration preservation and metadata drift checks ran; Docker and
  frontend checks remain pending. These runs do not claim production load testing.
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
