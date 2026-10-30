# Frontend Manual Testing and Demonstration

## Start and open the existing application

Run these from the existing repository. Do not run Django migrations or reset the database as part of the frontend check.

```bash
cd /home/petro/Documents/ChatGPT/online-pharmacy

# Inspect current Compose services; this does not modify them.
docker compose -f compose.yaml -f compose.backend.yaml ps

# The frontend proxy expects the already-running Django API on port 8000.
curl -i http://127.0.0.1:8000/api/health/

# Start the no-build static frontend (Node.js 18.16+; verified with Node 22.22.1).
node apps/frontend/server.mjs
```

Open <http://127.0.0.1:4173/>. If port 4173 is already in use, leave that server alone and start another instance with `FRONTEND_PORT=4174 node apps/frontend/server.mjs`, then open <http://127.0.0.1:4174/>. The proxy target can be changed with `API_ORIGIN=http://127.0.0.1:8000` if the Django API uses another local address.

If the API is stopped and the existing database service is the Compose `db` service, start the already-defined API/worker using:

```bash
docker compose -f compose.yaml -f compose.backend.yaml up -d backend worker
docker compose -f compose.yaml -f compose.backend.yaml ps
curl -i http://127.0.0.1:8000/api/health/
```

This may also start the Compose database dependency. If MySQL is managed outside this Compose project, do not run the command until its current database connection configuration is understood. The frontend itself never starts or changes MySQL.

## Checks executed for this implementation

### Automated API-client checks

Command:

```bash
node --test apps/frontend/tests/api.test.mjs
```

Observed result: `6` tests passed, `0` failed. They cover JSON/auth header handling, 401 expiration signaling, 403 distinction, network failure messaging, in-memory token clearing, and JWT expiration signaling. These tests stub Fetch and do not connect to MySQL or Django.

Syntax checks:

```bash
node --check apps/frontend/server.mjs
node --input-type=module --check < apps/frontend/src/app.js
node --input-type=module --check < apps/frontend/src/auth.js
node --input-type=module --check < apps/frontend/src/ui.js
```

Observed result: all commands exited successfully after the implementation fixes.

### Read-only live API and browser checks

The checks below were recorded before the storefront data refresh on 2026-10-29. Their catalog counts and limitations are historical and do not describe the current seeded catalog. The refresh used the existing database and is documented in `FRONTEND_COMPLETION_REPORT.md`; no post-refresh browser acceptance run is recorded here.

Observed against the currently running local API on 2026-10-29:

| Check | Result |
|---|---|
| `GET /api/health/` | PASS, HTTP 200, `{"status":"ok","database":"mysql"}` |
| `GET /api/products/?page=1` | PASS, HTTP 200, paginated result count 3 |
| `GET /api/categories/` | PASS, HTTP 200, two category rows |
| `GET /api/manufacturers/` | PASS, HTTP 200, one manufacturer row |
| `GET /api/pharmacies/` | PASS, HTTP 200, one pharmacy row |
| `GET /api/payment-methods/` | PASS, HTTP 200, four simulated payment methods |
| Browser `/#home` | PASS, real API catalog rendered; no browser console error observed |
| Browser catalog stock and price | PASS, selected branch dropdown, exact API `unit_price`, and `available` quantity rendered from that branch's inventory endpoint |
| Browser `/#catalog` | PASS, opens the catalog directly without the landing hero; route change returns to the top of the page |
| Browser `/#product:1` | PASS, product detail rendered with API-provided branch availability, `125.00 UAH`, and `25` available |
| Browser `/#pharmacies` | PASS, branch card rendered from API data |
| Browser `/#login` and `/#register` | PASS, Ukrainian forms rendered; no credentials submitted |

At the time of this earlier audit, the live API returned three `DEMO-*` rows and the single branch `Demo Central Pharmacy`. No catalog or database rows were inserted, updated, or deleted during those checks. The later storefront refresh is documented separately above and in `FRONTEND_COMPLETION_REPORT.md`.

The previous version of this paragraph described the earlier three-product database and is superseded by the storefront refresh recorded above. The current UI reads each selected branch's inventory endpoint and displays its branch-specific price and availability. Customer, staff, and administrator workflows were not tested after the refresh; use only authorized accounts and avoid destructive actions during a demonstration.

### Existing schema status

The read-only command `.venv/bin/python db/scripts/verify_schema.py` returned `SCHEMA VERIFICATION: FAIL` during the earlier audit, when migrations `0002_neutral_payment_providers.sql` and `0003_notification_outbox_idempotency.sql` were pending. The later storefront refresh did not apply migrations. Re-run the schema verifier before making a current claim about outbox-backed workflows.

## Guided manual workflows

Use only existing, explicitly designated coursework accounts and records. Do not use automated tests against the live database. The screens call the actual API and mutations persist to `internet_pharmacy`.

### Guest

1. Open the catalog and search for a SKU or name; apply category/manufacturer filters.
2. Open a product to see the API-provided details, prescription/storage flags, branch price, and available quantity.
3. Open **Аптеки** and request a branch's listed inventory.
4. Add to the guest cart only if you intend to change the browser's guest-cart cookie. The guest cart does not create an order; sign in with a Customer account for checkout.

### Customer

1. Sign in with an existing designated Customer account. A reload or expired token requires signing in again because the access token remains in memory only.
2. Add an existing catalog item, set quantity, and update the API cart.
3. Choose a pharmacy, fulfilment mode, and simulated payment method. For delivery, supply a recipient and destination.
4. Request a quote. Review the API-calculated line prices and total; confirm only if you intend to create a persistent order and reserve stock.
5. In order history, review status, payment, delivery, refund, cancel, and reorder actions. Payment and shipment are simulated.
6. For a CARD order, choose **Оплатити** and use only `DEMO USER`, `0000 0000 0000 0000`, `12/30`, `000`. Run APPROVED, DECLINED, and TIMEOUT on separate designated orders. Confirm the API request contains only `idempotency_key` and `demo_scenario`; never submit real credentials. In MySQL, inspect `payments.status`, `provider = EDUCATIONAL_SIMULATOR`, and the outbox scenario. Verify no card-number/CVV columns or values are present in payment/outbox rows or backend logs.
6. Review and update profile, preferences, loyalty transactions, notification read state, saved prescription labels, watches, and reminders.

### Staff

1. Sign in with an existing Staff account assigned to a pharmacy.
2. Confirm the branch selector only contains assigned pharmacies.
3. Review on-hand, reserved, available, price, and listed status. Save only an intended inventory adjustment; the backend checks the branch assignment and prevents reserved stock from being overwritten.
4. Use only valid API-approved order transitions. Prescription controls appear only when `/api/me/` reports pharmacist qualification; the API still decides whether that order is verifiable.
5. Try another branch only as an intentional permission demonstration with the instructor's designated test account; expected result is HTTP 403. Do not use another customer's account or data.

### Admin

1. Sign in with the existing designated Admin account.
2. Inspect network totals and the Users, Pharmacies, Products, Categories, Manufacturers, Assignments, Promotions, Promotion Products, Loyalty Tiers, and Delivery Rules sections.
3. Use supported create/update forms only with approved educational values. Admin endpoints do not expose general delete operations.
4. Use audit views to review recorded changes.

## Inspecting persisted records in MySQL Workbench or CLI

These are read-only inspection queries. Use the same existing `internet_pharmacy` connection; no query below creates, updates, or deletes rows.

```sql
USE internet_pharmacy;

SELECT id, sku, name, category_id, manufacturer_id, prescription_required,
       storage_min_c, storage_max_c, is_active
FROM products
ORDER BY id;

SELECT p.sku, p.name, ph.code, ph.name AS pharmacy,
       i.unit_price, i.on_hand, i.reserved,
       i.on_hand - i.reserved AS available, i.is_listed
FROM pharmacy_inventory AS i
JOIN products AS p ON p.id = i.product_id
JOIN pharmacies AS ph ON ph.id = i.pharmacy_id
ORDER BY ph.id, p.id;

SELECT o.id, o.order_number, o.status, o.payment_method, o.grand_total, o.created_at
FROM orders AS o
ORDER BY o.id DESC
LIMIT 20;

SELECT id, order_id, status, provider, amount
FROM payments
ORDER BY id DESC
LIMIT 20;

SELECT id, actor_id, action, target_type, target_id, occurred_at
FROM audit_entries
ORDER BY id DESC
LIMIT 30;
```

The last four queries will show changes only after an authorized user performs those actions through the frontend/API. No such write scenario was executed for this report.

## Actual scenario status

| Scenario | Status | Evidence / limitation |
|---|---|---|
| API client JSON, auth header, 401, 403, network failure | PASS | Four isolated Node tests |
| Syntax checks | PASS | Node parser commands above |
| Guest public navigation/catalog/detail/pharmacy page | PASS | Exercised in browser with live API GETs |
| Actual non-demo pharmaceutical catalog | BLOCKED at audit time | API then returned only three synthetic `DEMO-*` seed records; see the later storefront refresh report |
| Register/login/logout and token expiration | NOT TESTED | The form views render, but no designated account was created or submitted in this read-only verification; token expiration behavior is covered only by an isolated frontend unit test |
| Guest/customer cart writes | NOT TESTED | Would modify the current browser guest cookie or customer cart |
| Quote and order placement/reservation/cancellation | NOT TESTED | Persistent business-row changes require the instructor's explicit test account/record workflow; DB also has pending migrations |
| Simulated payment/refund/shipment worker outcomes | NOT TESTED | No writes or external-effect simulation was triggered |
| Customer profile, loyalty, notifications, reminders, watches | NOT TESTED | Authentication required; no personal account data was changed |
| Staff inventory/order permissions | NOT TESTED | No designated staff account and target record supplied |
| Admin create/update and audit | NOT TESTED | No designated admin account or approved target records supplied |
| Responsive layout | PASS, visual inspection only | Browser rendered at a narrow ~550 px viewport; no automated device matrix run |
