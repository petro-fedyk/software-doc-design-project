# Stage 08 Frontend Implementation Report

## Implemented

- A no-build, Vanilla JS application with Ukrainian end-user labels, responsive layout, accessible native forms, shared header/footer, loading/error/empty states, and browser hash navigation.
- Central API client with configurable `/api` base, JSON serialization, bearer authentication, request timeout, network-error handling, and separate unauthorized (401) / forbidden (403) behavior.
- In-memory access token with automatic expiry and reauthentication. No JWT is placed in localStorage or sessionStorage; a page reload starts a fresh unauthenticated session.
- Public, API-backed product catalog with search/category/manufacturer filters and server pagination; product detail includes category/manufacturer, prescription and storage data, branch-specific price and available stock; pharmacy listing and public branch inventory.
- Guest API cookie cart and authenticated Customer cart; quantity updates/removal; server quote review followed by a separate explicit order confirmation request; simulated payment choices do not collect credentials.
- Customer pages for own orders, payment/delivery/refund visibility, cancellation/reorder, profile, preferred pharmacy, preferences, loyalty balance/transactions, notifications, masked prescription labels, availability subscriptions, and reminders.
- Staff workspace constrained by `/api/me/` pharmacy assignments, with full inventory projection, safe stock/price/listed edits, allowed order transition/shipment actions, pharmacist-qualified prescription controls, refund request, statistics, and branch audit.
- Admin workspace for users, pharmacies, products, categories, manufacturers, staff assignments, promotions and product associations, loyalty tiers, delivery rules, pagination, create/edit, network statistics, and audit. It does not offer unsupported general DELETE operations.
- Development-only static server and same-origin API proxy; no npm dependencies or frontend framework.
- English engineering documentation and a six-case Node test suite that does not connect to Django/MySQL.

## Routes and workflows

The exact route mapping, methods, payloads, access rules, and known API gaps are listed in [FRONTEND_API_MAPPING.md](FRONTEND_API_MAPPING.md). Architecture and boundaries are in [FRONTEND_ARCHITECTURE.md](FRONTEND_ARCHITECTURE.md). Startup, safe live checks, database inspection queries, manual role demonstrations, and observed scenario statuses are in [FRONTEND_MANUAL_TESTING.md](FRONTEND_MANUAL_TESTING.md).

Important write workflows are implemented in the UI but were not invoked in this verification. This preserves the user's current business rows and guest cart. Frontend mutations call Django APIs; they never connect directly to MySQL.

## Verification performed

- **Automated:** `node --test apps/frontend/tests/api.test.mjs` — 6 passed, 0 failed. The tests stub Fetch. They cover bearer/JSON request handling, 401, 403, network failures, in-memory tokens, and expiration.
- **Syntax:** `node --check apps/frontend/server.mjs`; module syntax checks for `app.js`, `auth.js`, and `ui.js` — passed.
- **Browser:** GET-only home/catalog, product details (including storage range, branch price/stock), and pharmacy pages were opened against the running local API. No browser console error was observed.
- **Live API:** `GET /api/health/`, products, categories, manufacturers, pharmacies, and payment methods returned HTTP 200 on 2026-10-29.
- **Database:** The read-only schema verifier returned `SCHEMA VERIFICATION: FAIL`; 0002 and 0003 remain pending. This task applied no migration, changed no database rows, and created no database copy.

## Known blockers and not-tested scenarios

1. **Catalog content:** The connected database currently returns only three synthetic `DEMO-*` development-seed products and a demo branch. The UI faithfully displays those API rows; it cannot demonstrate the real named medicines requested earlier until the existing database/catalog is populated by its owner with approved real product records. This implementation did not invent or insert catalog records.
2. **Pending migrations:** `0002_neutral_payment_providers.sql` and `0003_notification_outbox_idempotency.sql` are pending in the live schema. Follow the existing database report and have the database owner review/apply them manually; the frontend does not do so. Outbox-backed write scenarios remain unverified until the verifier passes.
3. **Customer/staff/admin authenticated flows:** Not tested. No designated account credentials and authorized target records were provided, and this run deliberately made no persistent business-row changes.
4. **Prescription verification eligibility:** The order-list endpoint does not expose whether an order contains a prescription item. Qualified staff can see the verification action, but the server remains authoritative and may reject orders where verification is not required.
5. **Unavailable backend features:** No public promotions listing, no guest-to-customer cart merge, no staff qualification in assignment serialization, and no general resource delete API are exposed. These are documented and not fabricated in the frontend.
6. **Formal responsive matrix:** The UI was visually inspected at the available narrow browser viewport; a full desktop/tablet/device automated matrix was not run.

## Git history

- `a6340a2` — Add vanilla frontend API and auth foundation
- `5d8f20a` — Build API-backed pharmacy storefront and role portals
- `a427da3` — Verify frontend API integration and guard mutations

The final report and development log are included in a separate documentation-only commit; it does not add another implementation milestone.

## Live demonstration

1. Start or confirm the existing backend and worker, using the commands in [FRONTEND_MANUAL_TESTING.md](FRONTEND_MANUAL_TESTING.md). Confirm `curl -i http://127.0.0.1:8000/api/health/` returns HTTP 200.
2. Run `node apps/frontend/server.mjs`; open <http://127.0.0.1:4173/>. If that port is occupied, use `FRONTEND_PORT=4174 node apps/frontend/server.mjs` and open <http://127.0.0.1:4174/>.
3. Demonstrate guest browsing with the actual rows currently served by the connected API. Explain that the current catalog is synthetic demo seed content.
4. For Customer, Staff, and Admin demonstrations, use the instructor-designated accounts and records. Show persistence with the read-only SQL queries in the manual guide. Do not claim any unexecuted write flow passed.
5. The API-token design, endpoint traceability, and test results are summarized in the architecture/mapping documents and the commits above.

## Overall status

The frontend implementation and its read-only API integration are in place. The Stage 08 live end-to-end acceptance criteria are **not fully satisfied** because the live catalog is synthetic, migrations are pending, and authenticated mutation workflows were not exercised. No frontend-side change can truthfully resolve those environment/data/account blockers.
