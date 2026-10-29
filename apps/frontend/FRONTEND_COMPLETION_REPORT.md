# Stage 08 Frontend Implementation Report

## Implemented

### Storefront refresh (2026-10-29)

- The active storefront catalog uses 35 commercial medicine entries with sourced product images: 30 are stocked at each of the 50 existing pharmacy branches and five remain visible as unavailable.
- The 50 existing branch records now identify real АНЦ locations in Kyiv, Lviv, Odesa, and Dnipro, with addresses and official branch images. Branch IDs were retained.
- Product cards open from the full card surface and show a stronger add-to-cart action, selected-branch price, and available quantity. Product details let the customer compare available branches, prices, and stock.
- A branch page shows its address, official image, and available products. The cart stays tied to one selected branch and offers pickup, courier, and postal fulfillment plus the API-supported payment choices.
- Price and stock are simulated coursework values, not live commercial offers. Existing order history was preserved; retired placeholder products were archived rather than deleted.

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
- **Storefront correction (2026-10-29):** Catalog cards now display the selected pharmacy's API-backed price and available quantity, disable add-to-cart when there is no listed stock, and allow branch selection. Route changes reset scroll, the catalog route skips the landing hero, and stale API renders cannot replace a newer route. Read-only browser checks confirmed the selected branch, price, and quantity.
- **Live API:** `GET /api/health/`, products, categories, manufacturers, pharmacies, and payment methods returned HTTP 200 on 2026-10-29.
- **Database (previous audit, before the 2026-10-29 storefront refresh):** Read-only inspection confirmed 3 products, 3 inventory rows, 1 pharmacy, and 0 users or orders. The schema verifier returned `SCHEMA VERIFICATION: FAIL`; 0002 and 0003 remained pending at that time.
- **Database (storefront refresh, 2026-10-29):** The reviewed `seed_storefront_branches.py --apply` command updated the existing database in place. It retained 50 branch rows and 53 orders, activated 35 products, and confirmed in its run output that all 50 branches have 30 stocked commercial products and five visible unavailable products. No migration was required. No automated tests or post-refresh live browser checks were run as part of that refresh.

## Known blockers and not-tested scenarios

1. **Catalog data limits:** Active product trade names and branch identities are real, but branch prices and quantities are simulated. They must not be presented as live pharmacy offers. Existing order-line snapshots can retain old names as historical records.
2. **Database/API acceptance:** No schema verifier or post-refresh authenticated workflow was run in this refresh. Re-run the schema verifier and use instructor-designated credentials before claiming full order/outbox acceptance.
3. **Customer/staff/admin authenticated flows:** Not tested after this refresh. Use instructor-designated credentials for the demonstration. The refresh preserved existing order and account history.
4. **Prescription verification eligibility:** The order-list endpoint does not expose whether an order contains a prescription item. Qualified staff can see the verification action, but the server remains authoritative and may reject orders where verification is not required.
5. **Unavailable backend features:** No public promotions listing, no guest-to-customer cart merge, no staff qualification in assignment serialization, and no general resource delete API are exposed. These are documented and not fabricated in the frontend.
6. **Formal responsive matrix:** The UI was visually inspected at the available narrow browser viewport; a full desktop/tablet/device automated matrix was not run.

## Git history

- `a6340a2` — Add vanilla frontend API and auth foundation
- `5d8f20a` — Build API-backed pharmacy storefront and role portals
- `a427da3` — Verify frontend API integration and guard mutations
- `99baa4d` — Show live branch stock in pharmacy catalog

The final report and development log are included in a separate documentation-only commit; it does not add another implementation milestone.

## Live demonstration

1. Start or confirm the existing backend and worker, using the commands in [FRONTEND_MANUAL_TESTING.md](FRONTEND_MANUAL_TESTING.md). Confirm `curl -i http://127.0.0.1:8000/api/health/` returns HTTP 200.
2. Run `node apps/frontend/server.mjs`; open <http://127.0.0.1:4173/>. If that port is occupied, use `FRONTEND_PORT=4174 node apps/frontend/server.mjs` and open <http://127.0.0.1:4174/>.
3. Demonstrate the 35 active commercial medicine entries and branch-specific price and stock from the current database. Explain that prices and stock are simulated coursework data, not live offers.
4. For Customer, Staff, and Admin demonstrations, use the instructor-designated accounts and records. Show persistence with the read-only SQL queries in the manual guide. Do not claim any unexecuted write flow passed.
5. The API-token design, endpoint traceability, and test results are summarized in the architecture/mapping documents and the commits above.

## Overall status

The frontend and read-only API integration are in place, and catalog cards show database-backed branch stock and price. Stage 08 live end-to-end acceptance is **not complete**: the live catalog is synthetic, migrations are pending, and there are no accounts or orders for role-workflow verification. Frontend changes cannot turn missing database records into real pharmacy data.
