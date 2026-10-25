# Verification report

Date: 2026-10-25 (Asia/Kolkata). Current scope: local setup, admin provisioning and submission verification.

## Final local setup milestone — 2026-10-25

**135 backend tests, 25 frontend tests and three Chromium workflows passed.** Persistent local
initialization, operator CLI promotion and API/database restart verification also passed. No real
user was promoted. The existing screenshots were preserved; new browser captures are ignored.

### Commands actually executed

From the project root (Node/browser PATH variables are needed in this workspace):

```sh
UV_PYTHON_INSTALL_DIR="$PWD/.tools/python" .tools/uv/bin/uv sync --project backend --extra dev --locked
.tools/uv/bin/uv pip check --python backend/.venv/bin/python
export PATH="$PWD/.tools/node/bin:$PATH"
npm --prefix frontend ci
backend/.venv/bin/python scripts/test_backend.py --pg-bin .tools/postgres/bin -q --tb=short
npm --prefix frontend run test
npm --prefix frontend run lint
frontend/node_modules/.bin/prettier --check 'frontend/src/**/*.{ts,tsx,css}' 'frontend/*.{ts,js,json}' 'frontend/e2e/*.ts'
npm --prefix frontend run build
npm --prefix frontend audit --audit-level=moderate
backend/.venv/bin/python -m ruff check backend scripts
backend/.venv/bin/python -m ruff format --check backend scripts
export PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/browsers"
backend/.venv/bin/python scripts/test_frontend_integration.py --pg-bin .tools/postgres/bin
backend/.venv/bin/python scripts/verify_local_setup.py --pg-bin .tools/postgres/bin
git diff --check
```

| Check | Actual result |
| --- | --- |
| Locked backend install / package compatibility | 47 packages resolved; 44 installed packages compatible |
| npm clean install | 269 packages installed; 270 audited; zero vulnerabilities |
| Full PostgreSQL pytest runner | 135 passed, one existing warning, 16.33s; exit 0 |
| Migrations in isolated backend runner | Upgrade/downgrade, existing-user preservation and metadata drift checks passed |
| Frontend component tests | 25 passed in three files, 2.05s |
| ESLint / Prettier | Passed |
| TypeScript / Vite production build | Passed; JS 292.62 kB, CSS 25.86 kB before gzip |
| npm audit | Zero known vulnerabilities |
| Ruff lint / formatting | Passed; 39 files formatted |
| Chromium | Three passed, 6.2s; live health/CORS checks passed |
| Fresh setup/persistence verification | All four checks passed; temporary services stopped |

### New coverage and actual corrections

Nine CLI cases cover exact-account promotion, preservation of identity/password/other users,
idempotency and unchanged timestamp on rerun, CLI output/exit codes, missing/invalid email,
missing user, sanitized database failure and rejected public role assignment/promotion route.
Three local setup tests verify refusal to overwrite `.env`/data and exclusive mode-0600 secret
files. One API regression test verifies a sanitized retryable 503 when login cannot reach PostgreSQL.
All previous 122 backend cases are retained, including stock concurrency and role enforcement.

The initial targeted command was:

```sh
backend/.venv/bin/python scripts/test_backend.py --pg-bin .tools/postgres/bin -q -k 'test_admin_cli or test_login_database_failure' --tb=short
```

Before implementation, pytest stopped with one collection error because `app.cli` did not exist
(122 deselected, exit 2 from pytest; runner failed). After implementation, the same command passed
10 cases, with 122 deselected, in 0.31s. The full suite subsequently passed 135 cases. No test was
removed or weakened. Ruff found three long strings and a missing explicit subprocess `check`
argument; these and a formatting mismatch were corrected before successful checks.

The third Chromium journey deliberately aborts the login network request, verifies the clear UI
error, then removes the interception and successfully signs in against FastAPI. This is a simulated
browser network failure, not a claim that Playwright stopped the API. The separate persistence
runner actually stops the API and PostgreSQL and verifies recovery.

### Persistence, promotion and outages

`scripts/verify_local_setup.py` creates a new private temporary directory, copies only the safe
`.env.example`, and invokes the same initializer used for development. It uses SCRAM-authenticated
TCP PostgreSQL on 55441 and a separate API on 8002. It verifies:

1. Private `.env` permissions, a database application role without superuser/create-role/create-db
   privileges, migration to head and no schema drift.
2. Normal registration, rejected client-supplied role, initial 403 on admin actions, then the actual
   `python -m app.cli promote-admin --email persistence-test@example.com` subprocess and its rerun.
   The email belongs only to that disposable database. A CLI attempt with an incorrect database
   password fails without changing the role or exposing credentials. Existing JWTs resolve the
   new database role after authorized promotion.
3. API stop/restart and database stop/restart retain complete user and vehicle rows, including
   password hash, UUID, timestamps, role, decimal price and stock. Login still works afterward.
4. Stopped API refuses connections; stopped database produces health 503 and sanitized inventory
   503; restarting the same data directory restores successful requests.

No migrations to base, reset, deletion or recreation are used during the persistence comparison.
Only after checks does the runner stop services and remove its own temporary data.

### This workspace's permanent development setup

The following commands were separately executed successfully against the newly initialized,
previously absent local development cluster:

```sh
backend/.venv/bin/python -m app.local_database init --pg-bin .tools/postgres/bin
backend/.venv/bin/python -m alembic -c backend/alembic.ini upgrade head
backend/.venv/bin/python -m alembic -c backend/alembic.ini current
backend/.venv/bin/python -m alembic -c backend/alembic.ini check
backend/.venv/bin/python -m app.local_database status --pg-bin .tools/postgres/bin
```

Result: PostgreSQL running at `127.0.0.1:55432`, head `0003_user_name`, no upgrade operations.
A read-only database inspection verified zero users, zero vehicles and a restricted application
role. Root `.env` is mode 0600. `git check-ignore` confirmed `.env`, the data directory and operator
password are ignored; secrets were not printed or staged. No real application accounts were
created or promoted. Unlike test clusters, this persistent cluster remains running for the user.

### Submission limits

Homebrew installation instructions were checked against official formula pages but not executed:
Homebrew and Docker are absent here. Docker/Compose, Safari, Firefox, external hosting and production
load were not verified. The local PostgreSQL build has no TLS and binds to loopback only. Permanent
admin creation requires the operator to register and explicitly choose an account; there is no
default password. Existing Starlette/httpx, ESLint 9 support, whatwg-encoding and browser color-env
warnings remain; tests/build passed and npm audit found zero vulnerabilities. Earlier milestone
records below are historical. No push was performed during this task.

## Historical frontend milestone — 2026-10-24


**122 backend tests, 25 frontend tests and two live Chromium journeys passed.** No persistent
or production database was used. Browser tests started real FastAPI and Vite services, exercised
the actual API and captured the committed screenshots. Services and the temporary database were
stopped after verification. No push or deployment was performed.

### Commands actually run and results

Commands ran from the project root; Node commands used the installed local Node on PATH:

```sh
export PATH="$PWD/.tools/node/bin:$PATH"
backend/.venv/bin/python scripts/test_backend.py --pg-bin .tools/postgres/bin -q --tb=short
npm --prefix frontend run test
npm --prefix frontend run lint
npm --prefix frontend run build
npm --prefix frontend audit --audit-level=moderate
backend/.venv/bin/python -m ruff check backend scripts
backend/.venv/bin/python -m ruff format --check backend scripts
git diff --check
export PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/browsers"
backend/.venv/bin/python scripts/test_frontend_integration.py --pg-bin .tools/postgres/bin
```

| Check | Actual result |
| --- | --- |
| Full backend runner | 122 passed, one existing warning, 10.53s; exit 0 |
| Alembic checks inside backend runner | Head `0003_user_name`; no schema drift; upgrade/downgrade round trip passed |
| Existing-account preservation | Original ID/email/hash/role/timestamps preserved; new optional name is NULL |
| Vitest/React Testing Library | 25 passed across three files, 1.58s; exit 0 |
| ESLint | Passed; final rerun after browser-test formatting also passed |
| TypeScript/Vite production build | Passed; CSS 25.86 kB and JS 292.62 kB before gzip |
| npm audit | `found 0 vulnerabilities` |
| Ruff lint/format | `All checks passed!`; 34 files already formatted |
| Git whitespace check | Passed, no output |
| Live API/Vite/CORS | Health 200, Vite ready, allowed-origin OPTIONS response verified |
| Playwright Chromium | Two passed; initial run 6.8s, final rerun 3.2s after runner/format cleanup |

The live browser command runs migrations before startup and uses its own random test admin password.
The two browser journeys intentionally run serially against shared disposable inventory. There are
no hardcoded usable credentials. Logs, browser binaries, node_modules, dist and browser failure
artifacts are ignored. The runtime was Node 22.23.4/npm 10.9.9, Vite 7.3.7 and Vitest 5.0.5.

### Coverage

- Auth forms: required name, email/password validation, registration payload, login failures,
  protected navigation, session restoration, malformed/expired/revoked tokens and retry after a
  network failure. Optional backend names preserve old registration clients.
- API client: bearer header, JSON payloads, FastAPI 422 details, 204 responses, network/non-JSON
  errors, authenticated 401 session clearing and 403 behavior.
- Dashboard: rendering, combined filters, invalid price ranges, pagination, loading/empty/error
  states, retry, create validation, edit payload excluding stock and admin-only controls.
- Purchase: zero-stock disabling, exactly one unit per API request, success refresh and a 409
  stock-conflict refresh with error feedback. Existing PostgreSQL concurrency tests still pass.
- Browser: register/login, create/edit, search/pagination, buy to zero, reload session, logout,
  invalid-session redirect, admin restock, delete cancellation/confirmation, Escape dismissal.
- Screenshots: actual login, registration, desktop inventory and 390px mobile inventory images
  under `docs/screenshots/`. Desktop/mobile images were visually reviewed; a browser assertion
  also confirms no horizontal overflow at the mobile viewport. Sample inventory is test-only.

### Actual failures and corrections

The first frontend test run had 24 passes and one failure: a price matcher selected two vehicles
with the same price. The corrected assertion scopes the price to the intended vehicle row; the
application behavior and test intent were preserved. The next run passed all 25 tests.

The scaffold's initial Vitest 3 dependency tree produced three npm audit findings (two moderate,
one critical). Updating Vitest to 5.0.5 removed those findings; tests/build passed with the updated
lockfile. npm also printed an ESLint 9 support/deprecation notice during installation; lint still
passes. The existing Starlette httpx TestClient deprecation warning remains. Playwright printed a
harmless NO_COLOR/FORCE_COLOR conflict warning; neither warning was hidden.

### Remaining limitations

Docker is unavailable, so Compose and persistent container storage were not verified. No root
`.env`, persistent development database or permanent admin account was created. Those setup steps
are documented in README; admin provisioning still needs an operator-managed process. Session
storage is scoped to a tab and JavaScript-accessible; there is no refresh-token flow. Currency is
configurable display metadata, not a per-record database field. Browser checks used Chromium;
Safari/Firefox, production hosting and load testing were not performed.

## Historical vehicle milestone

The following results describe the preceding backend milestone before frontend integration.

### Verified result at that time

**118 passed, 1 warning in 9.24s** in the final rerun requested by the user. The full temporary
PostgreSQL runner exited 0 and shut down its cluster. This includes all 41 existing authentication
and foundation tests, 72 vehicle API/validation cases, and 5 concurrent-stock cases. The previous
complete run also passed 118 cases in 9.56s. No existing tests were removed or weakened.

### Commands actually run

```sh
backend/.venv/bin/python scripts/test_backend.py --pg-bin .tools/postgres/bin -q --tb=short
backend/.venv/bin/python -m ruff check backend scripts
backend/.venv/bin/python -m ruff format --check backend scripts
.tools/uv/bin/uv pip check --python backend/.venv/bin/python
git diff --check
```

Results: 118 tests passed; Ruff reported `All checks passed!`; 32 Python files were already
formatted; all 44 installed packages were compatible; Git's whitespace check returned no errors.
The sole warning is the unchanged upstream Starlette httpx TestClient deprecation, not a test failure.

### Incremental implementation and actual failing tests

| Command | Result |
| --- | --- |
| `backend/.venv/bin/python scripts/test_backend.py --pg-bin .tools/postgres/bin -q -k test_vehicle` before vehicle routes existed | 4 failed, 41 deselected, 1 warning in 0.26s; create/list returned 404 |
| `backend/.venv/bin/python scripts/test_backend.py --pg-bin .tools/postgres/bin -q` after create/list slice | 45 passed, 1 warning in 2.43s; migration checks passed |
| `backend/.venv/bin/python scripts/test_backend.py --pg-bin .tools/postgres/bin -q -k 'test_vehicle_purchase_one or test_vehicle_admin_restock or test_vehicle_search_combines or test_vehicle_admin_can_delete or test_vehicle_update_details' --tb=short` before remaining endpoints | 5 failed, 107 deselected, 1 warning in 0.55s; missing routes produced 404 or missing response fields |
| `backend/.venv/bin/python scripts/test_backend.py --pg-bin .tools/postgres/bin -q --tb=short` after all endpoints | 112 passed, 1 warning in 8.57s |
| Same command after adding concurrent requests, offset bound and user-preservation checks | 118 passed, 1 warning in 9.56s |
| Same command after the user's final review/verification request | 118 passed, 1 warning in 9.24s |

The first working slice was committed as `31f56a3`. The remaining implementation and verification
work was reviewed in place, including the untracked concurrency test file, and preserved for the
completed milestone commit. One Ruff import-order error in the expanded runner was fixed before
the final successful checks. There were no unexpected application test failures in the green runs.

### Migration verification and existing users

The runner executed the following sequence using only its newly created PostgreSQL database:

```sh
backend/.venv/bin/python -m alembic -c backend/alembic.ini upgrade 0001_create_users
# Runner inserts a temporary user with a randomly generated, Argon2-hashed password.
backend/.venv/bin/python -m alembic -c backend/alembic.ini upgrade head
backend/.venv/bin/python -m alembic -c backend/alembic.ini current
backend/.venv/bin/python -m alembic -c backend/alembic.ini check
backend/.venv/bin/python -m alembic -c backend/alembic.ini downgrade 0001_create_users
backend/.venv/bin/python -m alembic -c backend/alembic.ini upgrade head
backend/.venv/bin/python -m alembic -c backend/alembic.ini downgrade base
backend/.venv/bin/python -m alembic -c backend/alembic.ini upgrade head
backend/.venv/bin/python -m pytest backend/tests -q --tb=short
```

Every command exited 0. `current` printed `0002_create_vehicles (head)` and `check` printed
`No new upgrade operations detected.` The runner compared the entire pre-existing user row,
including UUID, email, hash, role and timestamps, before/after the vehicle upgrade and downgrade:
`PASS: existing user preserved across vehicle upgrade and downgrade`. It also confirmed that
the vehicle table was created empty, removed by vehicle downgrade, and both tables were removed
by the full test-only downgrade before being recreated. No persistent or production data was touched.

### Coverage and code review

- All seven inventory endpoints require JWT authentication. Create/update/purchase are available
  to regular users; delete/restock require admin. Existing expired/invalid JWT and role tests pass.
- Search combines case-insensitive make/model substrings, exact case-insensitive category and
  inclusive Decimal price bounds. Wildcards are escaped, pagination is bounded and static search
  is registered before dynamic IDs. Empty pages and invalid ranges are covered.
- Positive finite `NUMERIC(12,2)` prices, trimmed required fields, strict integer stock, overflow,
  missing vehicles, invalid updates and database CHECK constraints are exercised.
- Eight simultaneous buyers compete for one unit and then three units: exactly 1 or 3 purchases
  succeed, the remaining requests return 409, and final stock is zero.
- Four simultaneous restocks add 1, 2, 3 and 4 to initial stock 1; final stock is 11.
- Concurrent purchase and details edit both succeed; final stock remains zero and the edited make
  is preserved. PUT never accepts or writes quantity.
- Four simultaneous purchases and four increments of 2 from stock 10 all succeed; final stock is 14.
- Concurrent tests use real request sessions and independent PostgreSQL transactions, with a thread
  barrier to launch competing requests. They do not override the authentication/session dependencies.
- Writes use parameterized SQLAlchemy statements. Purchases use a conditional decrement and restocks
  use bounded atomic addition; both return the updated row. Not-found/conflict paths roll back,
  successful writes commit, and request sessions close through the existing dependency.

### Remaining work and limits

The requested inventory backend is ready for frontend integration. Admin account provisioning,
persistent local development setup, Docker verification and frontend work remain separate tasks.
No frontend files were changed or frontend tests run. The isolated database tests verify this
milestone, not production performance. The upstream TestClient warning remains. Nothing from this
milestone was pushed to GitHub; local commits await user review.

## Historical authentication foundation report

The following results describe the earlier authentication milestone, before vehicle development.

### Authentication result at that time

**41 tests passed**, 1 upstream dependency warning, in 2.15 seconds in the latest workspace audit.
The preceding post-refactor run passed in 2.21 seconds. See WORKSPACE_AUDIT.md for the new audit.
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
| Same isolated runner during the subsequent workspace/Git audit | 41 passed, 1 warning in 2.15s; migration checks and cluster shutdown passed; exit 0 |
| `.tools/uv/bin/uv pip check --python backend/.venv/bin/python` during the audit | 44 installed packages checked; all compatible |

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
