# Car Dealership Inventory System

A two-day MVP project for authenticated vehicle inventory, customer purchases and admin stock
management. Stack: FastAPI, SQLAlchemy 2, Pydantic, Alembic, PostgreSQL, JWT/Argon2, React,
TypeScript, Vite and Tailwind CSS.

**Current status: initial scaffold only.** Authentication, inventory operations and feature tests
are not implemented yet. The API has a process-liveness route and the UI has a setup screen.
See [the plan and requirements checklist](docs/IMPLEMENTATION_PLAN.md) and
[actual verification results](docs/TEST_REPORT.md).

## Workspace layout

```text
backend/
  app/                  API entry point, metadata, future routes/models/schemas/services
  migrations/           Alembic environment and future revisions
  tests/                Future pytest/TestClient and PostgreSQL integration tests
  pyproject.toml        Backend runtime and development dependencies
frontend/
  src/                  React entry point, starter screen, styles and test setup
  package.json          Frontend dependencies and scripts
docs/                   Implementation checklist, test report and future screenshots
compose.yaml            Optional PostgreSQL service with persistent named storage
.env.example            Configuration names and intentionally empty secrets
PROMPTS.md              Actual user prompt excerpt from this conversation
```

## Prerequisites

Install Python 3.12 and Node.js 22 (at least 22.12) with npm. For the included database service,
install and start Docker Desktop with Compose v2; alternatively use a local PostgreSQL 17 server.
Git is also required. This scaffold targets the Vite 7/Vitest 3 dependency families; dependency
ranges are provisional until installation, build and tests are verified. No lockfiles have been
generated yet. Commit the npm lockfile and a resolved backend dependency lock in the next step.

Inspection on 2026-10-24 found Python 3.9.6 and Git 2.50.1, but no Node/npm, Docker, `psql`,
or Python 3.12 on PATH. The pre-existing root `.venv` contains only pip and setuptools and was
preserved. Use a new backend virtual environment as shown below.

## Local setup

These commands are instructions for after installing prerequisites; they have **not** been
executed successfully in this environment.

From the project root, copy the example without overwriting an existing configuration:

```sh
cp -n .env.example .env
python3.12 -c 'import secrets; print(secrets.token_hex(32))'
```

Use independently generated values for `POSTGRES_PASSWORD` and `JWT_SECRET_KEY` in `.env`.
Put the same database password into `DATABASE_URL`; hexadecimal values need no URL encoding.
If you change the database/user/port, update the URL accordingly. Never commit `.env`.
JWT/CORS settings are reserved for the next implementation increment; no authentication exists yet.

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

Backend, from the project root:

```sh
python3.12 -m venv backend/.venv
source backend/.venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e './backend[dev]'
python -m alembic -c backend/alembic.ini upgrade head
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Alembic loads the root `.env` without overriding existing environment variables. There are no
model revisions yet, so the migration command does not create user or vehicle tables.
The future feature increment will supply and test those migrations. The liveness endpoint is
`http://127.0.0.1:8000/api/health`; interactive API docs are at `/docs`. Liveness does not prove
database connectivity.

Frontend, in a second terminal:

```sh
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` to port 8000. The frontend requires no secret
environment variables. After the first verified install, use `npm ci` with the generated lockfile.

## Checks during implementation

After dependencies and behavior tests have been added:

```sh
python -m pytest backend/tests
python -m ruff check backend
cd frontend
npm test
npm run build
```

The test directories currently contain no test cases; pytest/Vitest will report no tests, not a
passing suite. Integration tests must use a dedicated PostgreSQL test database. The future
suite will cover invalid tokens, role escalation, CRUD/search, stock boundaries and concurrent
purchases. Record commands and real results in [the test report](docs/TEST_REPORT.md).

## Screenshots

Pending a running application. Actual captures will be saved under `docs/screenshots/` and
embedded here after the UI is implemented and reviewed. No screenshots or deployment URLs
are claimed by this scaffold.

## My AI Usage

- **Tool:** OpenAI Codex, acting as an engineering assistant in the local workspace.
- **Input:** the user's complete specification and scoped first task. A verbatim user-message
  excerpt is preserved in [PROMPTS.md](PROMPTS.md); it is not an invented public chat link.
- **Work contributed in this increment:** workspace/tool inspection, a staged implementation plan,
  requirements checklist, dependency manifests, FastAPI/React entry points, Alembic scaffolding,
  Tailwind/Vitest configuration, an optional Compose template, environment example and documentation.
- **Engineering choices:** preserve the original virtual environment, use a separate Python 3.12
  environment, keep secrets out of Git, plan backend role enforcement and atomic stock changes.
  Add/update admin authorization is explicitly recorded as an assumption in the plan.
- **Verification and limits:** static parsing and Git hygiene checks are recorded in the test report.
  Missing runtimes prevent dependency resolution, API execution, frontend build/test, database
  migrations and container validation. Generated configuration is not evidence of a working system.
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
