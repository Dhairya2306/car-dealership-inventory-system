# Verification report

Date: 2026-10-24 (Asia/Kolkata). Current scope: PostgreSQL and authentication foundation.

## Current result

**41 tests passed**, 1 upstream dependency warning, in 2.21 seconds after refactoring.
The complete isolated runner exited 0, including migration checks and database shutdown.
Ruff lint and format checks passed. No vehicle APIs, production data, Docker execution,
frontend execution or deployment were involved.

Runtime: Python 3.12.15, PostgreSQL 17.11, FastAPI 0.162.0, SQLAlchemy 2.0.55,
Pydantic 2.14.1, Alembic 1.20.1, psycopg 3.3.6, PyJWT 2.15.1,
argon2-cffi 25.1.0, pytest 8.4.2. Resolved dependencies are recorded in `backend/uv.lock`.

## Executed commands and results

Commands below ran from the project root. The isolated runner printed its expanded commands;
temporary cluster paths vary for every invocation.

| Exact command | Actual result |
| --- | --- |
| `backend/.venv/bin/python -m pytest backend/tests/test_auth.py -q` | Red: 6 failed, 1 warning in 0.11s; all requested routes returned 404 |
| `backend/.venv/bin/python scripts/test_backend.py --pg-bin .tools/postgres/bin -q` (first implementation run) | Migrations passed; 38 passed, 3 failed, 2 warnings in 2.73s |
| Same isolated runner after assertion/config fixes | Green: 41 passed, 1 warning in 2.22s; runner exit 0 |
| `.tools/uv/bin/uv lock --project backend` | Resolved 47 packages; generated lockfile |
| `.tools/uv/bin/uv sync --project backend --extra dev --locked` | Resolved 47 packages, checked 44 installed packages; exit 0 |
| `backend/.venv/bin/python -m ruff check backend scripts` | All checks passed after fixes |
| `backend/.venv/bin/python -m ruff format --check backend scripts` | 25 files already formatted after refactor |
| Same isolated runner after extracting account services | Refactor: 41 passed, 1 warning in 2.21s; runner exit 0 |

The runner executed these migration commands with `DATABASE_URL` set to its newly created,
private PostgreSQL test database (not the development configuration):

```sh
backend/.venv/bin/python -m alembic -c backend/alembic.ini upgrade head
backend/.venv/bin/python -m alembic -c backend/alembic.ini current
backend/.venv/bin/python -m alembic -c backend/alembic.ini check
backend/.venv/bin/python -m alembic -c backend/alembic.ini downgrade base
backend/.venv/bin/python -m alembic -c backend/alembic.ini upgrade head
backend/.venv/bin/python -m pytest backend/tests -q
```

`current` printed `0001_create_users (head)`. `check` printed
`No new upgrade operations detected.` All migration commands exited 0. The runner also queried
the created users table and confirmed it was empty, then confirmed downgrade removed it before
reapplying the migration. Each run stopped PostgreSQL and removed its temporary directory.

## Test coverage and isolation

- Registration: normalized email, public response fields, database-stored Argon2id hash,
  timezone-aware timestamps, duplicate email, concurrent duplicate registration,
  invalid email/passwords, rejected role/hash fields and no plaintext in validation responses.
- Login: normalized email, signature/issuer/audience verification, 30-minute token lifetime,
  incorrect password and unknown account returning the same generic 401.
- Authorization: missing/malformed credentials, wrong signature/algorithm/issuer/audience,
  expired token, future issue time, missing expiry, invalid subject, deleted/missing user,
  user forbidden from admin access, admin allowed, demotion effective with the same token,
  and an admin JWT claim unable to override the database role.
- Infrastructure: real PostgreSQL readiness, sanitized 503 on connection error,
  allowed/blocked CORS origins, and rejection of insecure configuration.
- Tests create a random schema in the explicitly supplied `_test` database and run Alembic
  there. Per-test transactions use savepoints so endpoint commits remain isolated. The concurrent
  test uses separate real request sessions and removes its own committed test row. The temporary
  cluster runner uses no TCP listener, `.env` credentials or existing database server.

## Corrections made during verification

The first lint pass found formatting/import issues and an enum modernization suggestion;
those were fixed with Ruff and `StrEnum`. The first expanded test run exposed three test
assertion bugs: substring `short` matched the error code `too_short`, and substring `input`
matched the standard phrase "Extra inputs are not permitted". The tests now use a distinct
password sentinel and check error-object keys. No application validation was weakened.

Adding `path_separator = os` resolved Alembic's path-splitting warning, relevant to this
workspace's directory name containing spaces. After the suite passed, account persistence and
password verification moved into `app/services/auth.py`; the unchanged behavior suite passed again.

One warning remains: Starlette 1.9.0 deprecates the installed httpx adapter for TestClient and
recommends httpx2. The pinned adapter works and all tests pass; this warning was not suppressed.

## Runtime bootstrap performed

The original Python 3.9 environment was not modified. These commands succeeded:

```sh
python3 -m pip install --target .tools/uv uv
UV_PYTHON_INSTALL_DIR="$PWD/.tools/python" .tools/uv/bin/uv venv --python 3.12 backend/.venv
.tools/uv/bin/uv pip install --python backend/.venv/bin/python -e './backend[dev]'
curl --fail --location --output .tools/downloads/postgresql.tar.bz2 https://ftp.postgresql.org/pub/source/v17.11/postgresql-17.11.tar.bz2
curl --fail --location --output .tools/downloads/postgresql.sha256 https://ftp.postgresql.org/pub/source/v17.11/postgresql-17.11.tar.bz2.sha256
tar -xjf .tools/downloads/postgresql.tar.bz2 -C .tools
```

A Python hashlib check compared the archive's SHA256 with the downloaded checksum and passed.
From `.tools/postgresql-17.11`, the following commands succeeded (logs under ignored `.tools/`):

```sh
./configure --prefix="$PWD/../postgres" --without-icu --without-readline --without-zlib > ../postgres-configure.log 2>&1
make -j4 > ../postgres-build.log 2>&1
make install > ../postgres-install.log 2>&1
```

These local PostgreSQL binaries are for isolated tests. They were not installed system-wide and
do not provide TLS. Use the normal PostgreSQL distribution/Compose image for development services.

## Remaining work and limits

There is no backend test blocker for this milestone. A persistent development instance still
needs user-selected credentials and a running database; no `.env`, admin account or development
database was created. Docker remains unavailable, so Compose and container persistence were not
verified. No browser/frontend build or tests were run. No live HTTP server smoke test was run;
the endpoints were exercised with FastAPI TestClient against real PostgreSQL. Admin provisioning,
vehicle functionality and stock safety remain future milestones.

## Archived scaffold verification

The following records the earlier scaffold-only state, before runtimes and authentication were
implemented. Its missing-tool and pending-test statements are historical, not current results.

## Actual environment inspection

| Check | Observed result |
| --- | --- |
| Workspace files before changes | Only an existing `.venv`; no application files or AGENTS.md |
| `python3 --version` / `.venv/bin/python --version` | Python 3.9.6 |
| `.venv/bin/python -m pip list` | pip 21.2.4; setuptools 58.0.4 |
| `git --version` | Git 2.50.1 (Apple Git-155) |
| `git status --short --branch` before setup | Not a Git repository |
| `node --version`, `npm --version`, `docker --version` | Command not found |
| `command -v python3.12` and `command -v psql` | Not found on PATH |
| `git init -b main` | Initial sandbox attempt denied; approved retry succeeded |

## Static checks executed

A Python script was run through `.venv/bin/python` using standard-library `ast`, `json`,
`configparser`, `pathlib` and the existing pip-vendored TOML parser. It did not import application
dependencies or change the virtual environment. It parsed all `backend/**/*.py`, both frontend
JSON manifests, `backend/pyproject.toml`, and `backend/alembic.ini`, then checked that `.env` had
not been created and the original environment still declared Python 3.9.6. Exit status: 0.

Actual output:

```text
PASS: Python syntax parsed for 9 files (no imports/runtime execution)
PASS: 2 JSON manifests parsed
PASS: pyproject.toml parsed; Python requirement >=3.12
PASS: Alembic INI parsed
PASS: no .env created; original virtual environment remains Python 3.9.6
```

`git check-ignore` matched `.env`, `backend/.env`, `backend/.venv/example`, `.venv/bin/python`,
`frontend/node_modules/example` and `frontend/dist/example`. `.env.example` was supplied in the
same check and was not ignored; `git status --short` also showed it as an untracked file.

`git diff --check` exited 0 before staging, but untracked files are outside that check's scope;
this is not evidence that application behavior or even the new files were tested.

After staging all 32 scaffold files, `git diff --cached --check` exited 0 with no output.
This verifies whitespace hygiene for the staged files only.

## Not run

| Validation | Status / reason |
| --- | --- |
| Dependency installation/resolution and lock generation | Not run; target Python and Node/npm missing |
| FastAPI startup, API requests | Not run; runtime dependencies not installed |
| pytest/TestClient | Not run; no feature tests written and dependencies unavailable |
| TypeScript check, Vite build, Vitest/RTL | Not run; Node/npm unavailable |
| Compose config validation / database startup | Not run; Docker unavailable |
| Alembic migration / PostgreSQL persistence | Not run; no PostgreSQL, dependencies or model revisions |
| Concurrent purchase / permission tests | Pending implementation |
| Browser review / screenshots | Not run; application not launched |

Automated feature tests executed: **0**. No feature-test pass rate or coverage is claimed.
Static syntax checks cannot establish dependency compatibility, runtime correctness, database
connectivity, authorization or stock safety. This is not the final delivery test report.

## Next verification milestone

Install prerequisites; resolve dependencies and commit lockfiles; run Compose validation and
PostgreSQL health/persistence checks. Then record real Red-Green-Refactor results for registration,
JWT/roles and stock safety, including two concurrent buyers for one unit against PostgreSQL.
Run component tests, a production frontend build and manual browser checks; replace pending
entries with actual commands, counts, outcomes and screenshots.
