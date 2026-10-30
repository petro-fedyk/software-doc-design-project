# Phase 2 — Django backend

Phase 1 was explicitly accepted before implementation. Django 5.2 maps the existing MySQL schema through 31 unmanaged models. SQL files in `db/migrations` remain the only schema source of truth. Neither the API nor the worker applies migrations at startup. Django `migrate`, `makemigrations`, and `flush` are disabled in the project management entry point.

## Run the API and worker

The existing Phase 1 database must be running and migrated. Add a locally generated `DJANGO_SECRET_KEY` to the untracked `.env` (at least 32 random characters). The current workspace already has one. For a fresh checkout, generate a value with `python3 -c 'import secrets; print(secrets.token_urlsafe(48))'`; replace the placeholder in `.env.example` when copying it.

From the repository root:

```bash
docker compose -f compose.yaml -f compose.backend.yaml up --build -d
docker compose -f compose.yaml -f compose.backend.yaml ps
curl --fail http://127.0.0.1:8000/api/health/
```

- API: <http://127.0.0.1:8000/api/>
- Interactive Swagger documentation: <http://127.0.0.1:8000/api/docs/>
- OpenAPI: <http://127.0.0.1:8000/api/schema/>
- Database for Workbench: `127.0.0.1:3308`; database/user/password come from `.env`.

The Compose overlay adds `backend` and `worker` and preserves the existing database service and persistent volume. Stop only the new processes with:

```bash
docker compose -f compose.yaml -f compose.backend.yaml stop backend worker
```

Two Vanilla JS portals now use these REST endpoints: customer on 4173 and management on 4174. Django Admin is not installed. No Django auth, session, content-type or admin-log tables are introduced. See [portal architecture](../portals/ARCHITECTURE.md).

## Accounts and authorization

The historical Phase 1 seed accounts have unusable passwords. The local coursework startup now runs `bootstrap_admin`: it creates `admin` with password `admin` only when no ADMIN exists and never resets existing credentials. For the already created local coursework admin, run `python manage.py set_coursework_admin_password` to set that password explicitly. Register a customer through `POST /api/auth/register/`, or create an operator account with a private password prompt:

```bash
docker compose -f compose.yaml -f compose.backend.yaml exec backend \
  python manage.py create_account administrator admin@example.test --role ADMIN
```

Sign in with `POST /api/auth/token/` and supply `Authorization: Bearer <access>` on protected requests. Access tokens expire after 15 minutes; sign in again to obtain another token. There is no refresh-token or server logout table. Password changes and account deactivation invalidate previously issued tokens. Roles and active pharmacy assignments are read from the database on every request. `AA` and `SS` have no authorization meaning.

Administrators create staff through `/api/admin/users/` and assign them through `/api/admin/assignments/`. Staff may manage only assigned active pharmacies. Customers may read only their own orders and private records.

Prescription verification is simulated. The schema has no professional-qualification field, so verification requires all three conditions: `STAFF` role, an active matching assignment, and explicit membership in `PHARMACIST_IDS` in `.env`. Empty configuration denies verification to everyone, including administrators. Set the comma-separated IDs of authorized course staff, then recreate the backend/worker to load the configuration. See the schema proposals before implementing persisted qualifications.

`ENABLED_PAYMENT_METHODS` controls available checkout methods; the default is `CARD,BANK_TRANSFER,CASH_ON_DELIVERY,ONLINE_GATEWAY`. Actual payment processing is simulated. No endpoint accepts card numbers, CVV/CVC, cryptocurrency private keys, or seed phrases.

## Demonstration workflow

1. Open Swagger and register/sign in as a customer. Use **Authorize** with the access token.
2. Browse `/api/products/` and `/api/products/{id}/availability/`; select one pharmacy.
3. Send a quote request to `/api/checkout/quote/`. Use the returned prices and `grand_total` when placing the order. See [examples](examples.http).
4. `POST /api/orders/` creates a confirmed order and reservations atomically. The client must provide `expected_unit_price` for every line and `expected_total`; changed prices return HTTP 409.
5. `POST /api/orders/{id}/pay/` with a unique `idempotency_key` queues a simulated payment. The worker settles it asynchronously. Inspect `/api/orders/{id}/fulfillment/`.
6. Sign in as assigned staff. For pickup, transition through `PROCESSING`, `READY_FOR_PICKUP`, `COMPLETED`. A prescription item additionally requires authorized simulated verification. Cash payment is recorded by staff at completion.
7. For courier/postal orders, transition through `PROCESSING`, `AWAITING_SHIPMENT`; call `/ship/`; the worker validates current eligibility, creates simulated tracking, consumes reserved stock, and marks the order shipped. Staff then confirms completion.
8. Inspect inventory, notifications, and loyalty. Order history retains original name and price snapshots.

Guest carts use a signed, HTTP-only, same-site cookie at `/api/guest-cart/`. They do not add a session table. Authenticated carts use the existing cart tables. Reordering copies quantities into the current cart and requires a new quote.

## Transactions and asynchronous work

Application services receive a Unit of Work factory through constructor injection. The ORM Unit of Work uses `transaction.atomic`; absence of explicit commit rolls back. Checkout locks inventory in product order. Order/reservation/stock changes and outbox rows commit together.

Workers use InnoDB `SELECT ... FOR UPDATE SKIP LOCKED`. Each local simulated effect and its outbox `DONE` marker commit in the same transaction. A crash rolls back both; the row lock is released. Failed handlers roll back their effects, then receive exponential retry delay capped at one hour. Ten failures produce `FAILED`. Error fields contain an error code/class, not credentials or request bodies.

The worker also cancels expired unshipped reservations and sends opted-in scheduled reminders. Marketing notifications require the current `promotions_enabled` preference. Stock receipt events notify and deactivate matching availability subscriptions.

Payment requests serialize on their order and use the existing unique `payments.idempotency_key`. Refund requests use a deterministic unique outbox event ID; retain those outbox rows for the entire supported refund retry period. Provider keys are stable across retries. Loyalty uses unique ledger event keys, and completion events snapshot the awarded point count before asynchronous processing. Refunds proportionally reverse previously awarded points.

The supplied providers perform no network I/O. Replacement providers must preserve idempotency and set network timeouts; database rollback cannot undo an external financial effect. Remote notification adapters additionally need provider deduplication. The current implementation makes no claim of exactly-once external delivery.

Run one batch manually:

```bash
docker compose -f compose.yaml -f compose.backend.yaml exec worker \
  python manage.py outbox_worker --once --batch-size 100
```

## Local development and tests

The Docker build installs its own native MySQL client dependencies. For a host installation on Ubuntu, use `build-essential`, `pkg-config`, `python3-dev`, and `default-libmysqlclient-dev`, then:

```bash
python3 -m venv .venv
.venv/bin/pip install -r apps/backend/requirements-dev.txt
.venv/bin/python apps/backend/manage.py check
.venv/bin/python apps/backend/manage.py runserver 127.0.0.1:8000
```

Use a separate test database, never the demonstration database:

```bash
.venv/bin/python apps/backend/scripts/prepare_test_db.py
MYSQL_DATABASE=internet_pharmacy_test .venv/bin/pytest -q
.venv/bin/python db/scripts/verify_schema.py
.venv/bin/python db/scripts/test_mysql.py
.venv/bin/python apps/backend/manage.py spectacular \
  --file docs/backend/openapi.yaml --validate --fail-on-warn
```

If the base database name differs, substitute `<base_name>_test`. The test provisioner only creates/grants the test database and applies existing SQL migrations there. Tests reject database names without the `_test` suffix. Most fixtures use rollback; concurrency tests use committed rows on separate connections and explicitly remove their own records afterward.

## Design and known decisions

- [Architecture and use-case traceability](architecture-and-traceability.md)
- [Schema proposals and deviations](schema-proposals.md)
- [Verification results](verification.md)
- [Generated OpenAPI](openapi.yaml)

This is a local educational deployment on loopback HTTP. TLS termination, shared distributed rate limiting, provider production credentials, and refresh-token revocation are outside this phase. The login limiter is process-local; it is not presented as a distributed abuse-prevention system.
