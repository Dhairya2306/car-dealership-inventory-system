# Implementation plan and requirements checklist

Scope: a two-day local MVP. Scaffolding, authentication, inventory backend and React workflows are complete.
The suites pass 144 backend tests, 26 frontend tests and three Chromium journeys;
see TEST_REPORT.md for actual results and limitations. Final local verification: 2026-10-25.

## Day 1: backend (approximately 8 hours)

1. Foundation (1 hour): inspect workspace, scaffold, install prerequisites and dependencies,
   validate PostgreSQL persistence, generate dependency locks.
2. Accounts (2 hours): user migration, Argon2 hashing, registration, JWT login and auth dependency.
   Public registration cannot assign roles. Add a local admin provisioning command with a password
   prompt; never publish default admin credentials.
3. Inventory (2 hours): vehicle migration, validation, protected CRUD and combined search filters.
4. Stock (2 hours): atomic purchase/restock operations, database constraints, concurrent requests
   against PostgreSQL, rollback and authorization tests.
5. Review (1 hour): full backend test run, error contracts, migration verification, meaningful commits.

## Day 2: frontend and delivery (approximately 8 hours)

1. Account screens and authenticated API client (1.5 hours).
2. Inventory dashboard, combined filters, purchase feedback and zero-stock states (2 hours).
3. Admin forms, responsive layout, keyboard accessibility, loading/error/empty states (2 hours).
4. Component tests and end-to-end manual smoke checks against PostgreSQL (1.5 hours).
5. Capture actual screenshots, finish README/AI records and test report (1 hour).

## Requirements

- [x] Inspect existing workspace; preserve existing `.venv`.
- [x] Create backend/frontend structure and dependency manifests.
- [x] Add secret-free `.env.example` and `.gitignore`.
- [x] Prepare optional PostgreSQL Compose template with a named volume and health check.
- [x] Install backend runtime/dependencies, lock versions and verify PostgreSQL migrations.
- [x] Install frontend prerequisites and lock dependencies; verify tests, lint and build.
- [x] Initialize and verify persistent loopback PostgreSQL, restart behavior and private configuration.
- [ ] Optional Docker: install and validate Compose/container storage (not available on this Mac).
- [x] User registration and login; unique normalized email; Argon2 hashes only.
- [x] JWT validation, expiry, issuer/audience checks and reusable current-user/admin dependencies.
- [x] Public registration cannot grant admin; backend role enforcement tested with test-only routes.
- [x] Apply authentication/admin dependencies to inventory routes.
- [x] Add operator CLI promotion of an existing account; idempotent and tested without real-user promotion.
- [x] Vehicle: generated unique ID, make, model, category, decimal price, integer stock quantity.
- [x] `POST /api/vehicles`: authenticated user adds a vehicle (updated user specification).
- [x] `GET /api/vehicles`: list vehicles with pagination (authenticated).
- [x] `GET /api/vehicles/search`: combine make/model/category/minimum/maximum price filters.
- [x] `PUT /api/vehicles/{id}`: authenticated user updates descriptive fields and price.
- [x] `DELETE /api/vehicles/{id}`: delete vehicle (admin-only).
- [x] `POST /api/vehicles/{id}/purchase`: authenticated purchase with safe stock decrement.
- [x] `POST /api/vehicles/{id}/restock`: admin-only positive stock increment.
- [x] Input validation, missing resources, forbidden/unauthenticated requests, conflict responses.
- [x] React registration/login and authenticated inventory dashboard.
- [x] Search/filter controls and purchase buttons disabled at zero stock.
- [x] Authenticated add/edit and admin delete/restock controls; responsive polished UI.
- [x] pytest + FastAPI TestClient, including PostgreSQL concurrent purchase integration tests.
- [x] Vitest + React Testing Library for forms, permissions, zero stock and error feedback.
- [x] Record Red-Green-Refactor evidence for the authentication/authorization foundation.
- [x] Record vehicle/stock behavior failures before implementation and passing integration results.
- [x] Meaningful local scaffold, failing-test and implementation commits with Codex co-author trailers.
- [x] Initial README, detailed My AI Usage section, real prompt excerpt in root PROMPTS.md.
- [x] Actual screenshots and verified browser/test instructions; persistent setup documented separately.
- [x] Final test report with real test counts, commands, results and known limitations.
- [x] Prepare Render/Vercel settings, hosted URL handling and locally verified production commands.
- [ ] Publish/deploy and verify actual hosted origins/TLS only after explicit user authorization.

## Implemented design decisions

- Use synchronous SQLAlchemy 2 sessions with psycopg and ordinary FastAPI `def` routes;
  PostgreSQL in development and integration tests, with a separate disposable test database.
- Use database `NUMERIC(12,2)` / Python Decimal for price; reject negative price/stock and
  invalid price ranges; trim and constrain text fields. Do not use floating point for money.
- The later user specification explicitly allows authenticated users to add/update vehicle details;
  delete and restock remain admin-only. Registration rejects role fields and creates regular users.
- Purchase initially buys one unit per request. Restock accepts a positive integer quantity.
  Use `UPDATE ... SET quantity = quantity - 1 WHERE id = :id AND quantity > 0 RETURNING ...`
  inside a transaction. Check affected rows; return 404 for missing vehicles and 409 for no stock.
  Add a database CHECK constraint to enforce nonnegative stock. Restock also uses an atomic update.
- Quantity is excluded from PUT. Atomic purchase/restock operations are separate from descriptive
  edits, and concurrent tests verify that edits cannot restore purchased stock.
- Register `/search` before `/{id}`. Use case-insensitive partial make/model search, category
  filtering and inclusive price bounds. Define pagination and deterministic ordering.
- Return 201 on create, 200 on successful reads/updates/stock operations, 204 on delete,
  401 for missing/invalid credentials, 403 for insufficient role, 404 for missing records,
  409 for duplicate accounts/out-of-stock conflicts, 422 for invalid inputs.
- Keep bearer tokens in memory and tab-scoped sessionStorage for refresh persistence. Validate
  the session and role with `/auth/me`; expire sessions and clear them on authenticated 401.
  Do not place secrets in Vite
  environment variables. Development uses Vite's `/api` proxy; configure exact allowed origins
  if separate origins are later required.

## Red-Green-Refactor and Git

For each important rule, first write and run the failing behavior test, recording its actual
failure. Implement the smallest fix, rerun to green, then refactor and rerun. Keep test and
implementation commits small and descriptive. Test simultaneous buyers for the final unit
using separate PostgreSQL connections: exactly one succeeds and final stock is zero.

No repository-specific trailer instruction existed at inspection. AI-assisted commits use
the actual tool identity: `Co-authored-by: Codex <noreply@openai.com>`.
