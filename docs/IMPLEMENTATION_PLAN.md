# Implementation plan and requirements checklist

Scope: a two-day local MVP. Scaffolding and the PostgreSQL/authentication foundation are complete.
The latest foundation run passed 41 tests; see TEST_REPORT.md for actual results and limitations.

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
- [ ] Install frontend/Docker prerequisites; validate Compose and persistent development storage.
- [x] User registration and login; unique normalized email; Argon2 hashes only.
- [x] JWT validation, expiry, issuer/audience checks and reusable current-user/admin dependencies.
- [x] Public registration cannot grant admin; backend role enforcement tested with test-only routes.
- [ ] Apply dependencies to inventory routes; add local admin provisioning.
- [ ] Vehicle: generated unique ID, make, model, category, decimal price, integer stock quantity.
- [ ] `POST /api/vehicles`: add vehicle (planned admin-only).
- [ ] `GET /api/vehicles`: list vehicles (authenticated).
- [ ] `GET /api/vehicles/search`: combine make/model/category/minimum/maximum price filters.
- [ ] `PUT /api/vehicles/{id}`: update vehicle (planned admin-only).
- [ ] `DELETE /api/vehicles/{id}`: delete vehicle (admin-only).
- [ ] `POST /api/vehicles/{id}/purchase`: authenticated purchase with safe stock decrement.
- [ ] `POST /api/vehicles/{id}/restock`: admin-only positive stock increment.
- [ ] Input validation, missing resources, forbidden/unauthenticated requests, conflict responses.
- [ ] React registration/login and authenticated inventory dashboard.
- [ ] Search/filter controls and purchase buttons disabled at zero stock.
- [ ] Admin add/update/delete/restock controls; responsive polished UI.
- [ ] pytest + FastAPI TestClient, including PostgreSQL concurrent purchase integration tests.
- [ ] Vitest + React Testing Library for forms, permissions, zero stock and error feedback.
- [x] Record Red-Green-Refactor evidence for the authentication/authorization foundation.
- [ ] Record stock-operation Red-Green-Refactor evidence when implemented.
- [x] Meaningful local scaffold, failing-test and implementation commits with Codex co-author trailers.
- [x] Initial README, detailed My AI Usage section, real prompt excerpt in root PROMPTS.md.
- [ ] Actual screenshots and final tested setup instructions.
- [ ] Final test report with real test counts, commands, results and known limitations.
- [ ] Deployment/push only after explicit user authorization (outside this increment).

## Design decisions for the next increments

- Use synchronous SQLAlchemy 2 sessions with psycopg and ordinary FastAPI `def` routes;
  PostgreSQL in development and integration tests, with a separate disposable test database.
- Use database `NUMERIC(12,2)` / Python Decimal for price; reject negative price/stock and
  invalid price ranges; trim and constrain text fields. Do not use floating point for money.
- Admin-only add/update is an assumption based on the requested admin UI. All inventory access
  requires login. Registration rejects role fields and always creates a regular user.
- Purchase initially buys one unit per request. Restock accepts a positive integer quantity.
  Use `UPDATE ... SET quantity = quantity - 1 WHERE id = :id AND quantity > 0 RETURNING ...`
  inside a transaction. Check affected rows; return 404 for missing vehicles and 409 for no stock.
  Add a database CHECK constraint to enforce nonnegative stock. Restock also uses an atomic update.
- Ensure admin quantity edits cannot silently overwrite concurrent purchase results: use an
  explicit locking/version strategy or separate quantity changes from descriptive edits.
- Register `/search` before `/{id}`. Use case-insensitive partial make/model search, category
  filtering and inclusive price bounds. Define pagination and deterministic ordering.
- Return 201 on create, 200 on successful reads/updates/stock operations, 204 on delete,
  401 for missing/invalid credentials, 403 for insufficient role, 404 for missing records,
  409 for duplicate accounts/out-of-stock conflicts, 422 for invalid inputs.
- Keep bearer tokens in memory initially; reload requires login. Do not place secrets in Vite
  environment variables. Development uses Vite's `/api` proxy; configure exact allowed origins
  if separate origins are later required.

## Red-Green-Refactor and Git

For each important rule, first write and run the failing behavior test, recording its actual
failure. Implement the smallest fix, rerun to green, then refactor and rerun. Keep test and
implementation commits small and descriptive. Test simultaneous buyers for the final unit
using separate PostgreSQL connections: exactly one succeeds and final stock is zero.

No repository-specific trailer instruction existed at inspection. AI-assisted commits use
the actual tool identity: `Co-authored-by: Codex <noreply@openai.com>`.
