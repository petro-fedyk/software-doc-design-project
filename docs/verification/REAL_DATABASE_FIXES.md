# Backend Fixes Before Stage 08 Frontend

This report records the backend corrections and the checks performed against the existing `internet_pharmacy` database. No migration was applied, no business rows were changed, and no automated test connected to the live database.

## Fix 1 — Invalid JSON roots

**Root cause.** `StrictSerializer.to_internal_value()` called `set(data)` before confirming that the JSON root was a mapping. JSON arrays containing objects could raise `TypeError`, which was returned as HTTP 500.

**Files changed.** `apps/backend/pharmacy/api/serializers.py`; `apps/backend/tests/test_safe_regressions.py`.

**Correction.** The serializer now checks `collections.abc.Mapping` first and raises a DRF validation error for arrays, `null`, strings, numbers, and other non-object roots. Object validation and unsupported-field checks then proceed as before.

**Test command and actual output.** The focused test file is DB-free and does not use the project `db` fixture:

```text
$ .venv/bin/pytest -q apps/backend/tests/test_safe_regressions.py
............                                                             [100%]
12 passed in 0.52s
```

**Manual HTTP reproduction.** With the backend running and `$TOKEN` set to a valid access token:

```bash
curl -i -X PUT http://127.0.0.1:8000/api/cart/ \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  --data '[{"product_id":1,"quantity":1}]'
```

**Expected response.** HTTP `400 Bad Request`, with a JSON error similar to:

```json
{"non_field_errors":["Expected a JSON object."]}
```

**Schema migration required.** No.

## Fix 2 — Outbox notification replay idempotency

**Root cause.** The worker dispatched event type and payload without the durable outbox event ID. Notification handlers used unconditional inserts, so replaying an already completed event could create another order, availability, or promotion notification.

**Files changed.** `apps/backend/pharmacy/application/services.py`; `apps/backend/pharmacy/application/subscribers.py`; `apps/backend/pharmacy/infrastructure/worker.py`; `apps/backend/pharmacy/infrastructure/repositories.py`; `apps/backend/pharmacy/models.py`; `apps/backend/pharmacy/api/views.py`; `apps/backend/tests/test_safe_regressions.py`; `db/migrations/0003_notification_outbox_idempotency.sql`; `db/scripts/generate_erd.py`; `docs/diagrams/database/Internet_Pharmacy_MySQL_ERD.drawio`.

**Correction.** The worker now passes `event_id` into event dispatch. Notification creation uses a stable `(source_event_id, user_id, type)` lookup. Migration 0003 adds a nullable source-event column and a matching unique index. Existing notifications remain untouched: the new column is `NULL` for historical rows, and MySQL permits multiple `NULL` values in the unique index. The notifications API explicitly selects its prior fields, so it does not expose the internal idempotency key. The editable ERD generator and diagram now include the migration-added column.

**Test command and actual output.** The focused DB-free tests verify event-ID propagation, one simulated record for replayed stable identity, and unchanged migration-era behavior. The SQL unique index itself was not exercised against the live database because that requires applying the migration, which this task explicitly forbids.

```text
$ .venv/bin/pytest -q apps/backend/tests/test_safe_regressions.py
............                                                             [100%]
12 passed in 0.52s
```

The editable diagram was regenerated and parsed successfully:

```text
$ .venv/bin/python db/scripts/generate_erd.py
Wrote docs/diagrams/database/Internet_Pharmacy_MySQL_ERD.drawio with 32 schema tables including migration ledger across 5 pages

$ python3 -c "import xml.etree.ElementTree as ET; ET.parse('docs/diagrams/database/Internet_Pharmacy_MySQL_ERD.drawio'); print('draw.io XML: PASS')"
draw.io XML: PASS
```

**Manual HTTP observation.** There is no HTTP endpoint for replaying a completed internal outbox event. After a normal event has been processed, the visible notifications can be inspected without changing data:

```bash
curl -i http://127.0.0.1:8000/api/notifications/ \
  -H "Authorization: Bearer $TOKEN"
```

**Expected response.** HTTP `200 OK` with a JSON array. Reprocessing the same event must leave one notification for that event, user, and notification type. Deterministic replay needs the worker or a DB-level test; this HTTP read alone does not force replay.

**Schema migration required.** Yes. Apply `0003_notification_outbox_idempotency.sql` manually before deploying the new backend/worker code. Migration `0002` is also currently pending, as recorded under Fix 5.

## Fix 3 — OpenAPI response contracts

**Root cause.** Several endpoints returned JSON arrays while documenting a single object. Product availability also inherited a page wrapper in the schema despite returning a raw array. Product filters and common error responses were not adequately described.

**Files changed.** `apps/backend/pharmacy/api/serializers.py`; `apps/backend/pharmacy/api/views.py`.

**Correction.** Added response serializers for availability, inventory, preferences, availability watches, reminders, notifications, saved prescriptions, and audit rows. These list responses are documented as arrays. Product listing is documented as a paginated `count/next/previous/results` object, while availability is a raw array. Product query parameters `category`, `manufacturer`, `prescription_required`, `search`, and pagination `page` are listed. Relevant error response shapes/statuses are included for the corrected operations. Runtime API behavior was not changed except excluding the newly added internal `source_event_id` from notification output.

**Test command and actual output.**

```text
$ cd apps/backend
$ ../../.venv/bin/python manage.py spectacular --validate --file /tmp/internet-pharmacy-openapi.yaml
[exit code 0; no warnings or errors]
```

The generated schema was also inspected. Product listing references `PaginatedProductPageList`; product availability, inventory, preferences, watches, reminders, notifications, prescriptions, and audit responses are arrays. Product query parameters are `category,manufacturer,page,prescription_required,search`.

**Manual HTTP reproduction.**

```bash
curl -i http://127.0.0.1:8000/api/schema/
```

**Expected response.** HTTP `200 OK` with the OpenAPI document; the paths above distinguish arrays from the paginated product response. Swagger UI remains available at `/api/docs/`.

**Schema migration required.** No for OpenAPI corrections. The notification field exclusion is required to preserve the existing notification response contract after migration 0003.

## Fix 4 — Deadlock handling

**Root cause.** Database transaction operations had no bounded retry when MySQL selected them as a deadlock victim. Retrying one statement would not restore the transaction's earlier reads and writes.

**Files changed.** `apps/backend/pharmacy/application/services.py`; `apps/backend/tests/test_safe_regressions.py`.

**Correction.** Added a bounded retry wrapper for MySQL error 1213. It invokes the entire application operation again, so each attempt creates a fresh Unit of Work and transaction. It retries order placement/transitions, payment/refund requests, inventory/cart/personal updates, and other DB-only commands. Event consumers that call payment or shipment providers are not decorated and are never retried by this mechanism. Personal update input is copied before execution so repositories that consume fields cannot change a later retry's command.

**Test command and actual output.** The no-DB tests verify whole-operation retry, a four-attempt maximum (initial attempt plus three retries), no retry for a lock-timeout error, preservation of consumed input, and no retry of external gateway work:

```text
$ .venv/bin/pytest -q apps/backend/tests/test_safe_regressions.py
............                                                             [100%]
12 passed in 0.52s
```

**Manual HTTP reproduction.** A single HTTP request cannot deterministically induce a MySQL deadlock, and the API has no endpoint for controlling transaction locks. A normal cart update can be issued with:

```bash
curl -i -X PUT http://127.0.0.1:8000/api/cart/ \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  --data '{"product_id":1,"quantity":1}'
```

**Expected response.** HTTP `200 OK` during normal operation; if the transaction receives MySQL 1213, the whole transaction is retried up to three times. The command itself does not force contention and changes the authenticated user's cart if run.

**Schema migration required.** No.

## Fix 5 — Production migration readiness

**Root cause.** The live migration ledger contains only `0001_initial.sql`; `0002_neutral_payment_providers.sql` has not been applied. The existing schema verifier did not compare the ledger with all migration files, so it could miss a pending migration when a constraint name already existed.

**Files changed.** `db/scripts/verify_schema.py`; `db/migrations/0003_notification_outbox_idempotency.sql`; `db/scripts/generate_erd.py`; `docs/diagrams/database/Internet_Pharmacy_MySQL_ERD.drawio`. Existing migrations `0001_initial.sql` and `0002_neutral_payment_providers.sql` were not edited.

**Correction.** The verifier now reports pending migration files and applied checksum mismatches, and includes columns introduced by `ALTER TABLE` when comparing the catalog. A read-only inspection confirmed that `0001_initial.sql` has a matching checksum, migration 0002 is pending, the payments table still has `chk_payments_provider`, and there are currently no payment rows that conflict with the new provider values. The database is MySQL `8.0.42`, InnoDB, and `utf8mb4`.

**Test/verification command and actual output.** This command was run against the existing `internet_pharmacy` database and only read metadata/catalog data:

```text
$ .venv/bin/python db/scripts/verify_schema.py
MySQL: 8.0.42; engine: InnoDB; charset/collation: utf8mb4/utf8mb4_0900_ai_ci; time_zone(global/session)=+00:00/+00:00 (system UTC)
Domain tables: 31/31; migration ledger: present
Columns: 205; FKs: 39 (expected 39); CHECKs: 36 (expected 36); indexes: 58; migrations: 1
Pending migrations: 0002_neutral_payment_providers.sql, 0003_notification_outbox_idempotency.sql
Column differences: {'notifications': {'missing': ['source_event_id'], 'extra': []}}
Missing indexes: ['uq_notifications_event_user_type']
SCHEMA VERIFICATION: FAIL
```

The failure is expected until the developer applies the two pending migrations. A separate read-only preflight returned `DATABASE: internet_pharmacy`, `0001_initial.sql: checksum_match=True`, `PAYMENT PROVIDERS: (no rows)`, and `ROWS INCOMPATIBLE WITH 0002: 0`. No migration was run.

**Manual HTTP observation.** Schema migration state is not exposed through HTTP. A read-only database health check is:

```bash
curl -i http://127.0.0.1:8000/api/health/
```

**Expected response.** HTTP `200 OK` with `{"status":"ok","database":"mysql"}` when the backend can connect. This does not replace `verify_schema.py` for migration validation.

**Schema migration required.** Yes. Migrations 0002 and 0003 must be applied manually, in order. Do not deploy the updated backend/worker before 0003 is applied: notification writes now require `notifications.source_event_id`.

## Deployment and verification commands

These commands are provided for the developer to run. They were **not** executed here; the live database was not changed.

```bash
cd /home/petro/Documents/ChatGPT/online-pharmacy

# Manually apply pending numbered migrations to the configured internet_pharmacy DB.
.venv/bin/python db/scripts/migrate.py

# Rebuild/restart only the backend and worker; the existing DB volume remains in place.
docker compose -f compose.yaml -f compose.backend.yaml up -d --build backend worker

# Verify live schema and immutable migration checksums.
.venv/bin/python db/scripts/verify_schema.py

# Run focused tests that do not use the database fixture or touch business rows.
.venv/bin/pytest -q apps/backend/tests/test_safe_regressions.py

# Validate the generated API contract.
cd apps/backend
../../.venv/bin/python manage.py spectacular --validate --file /tmp/internet-pharmacy-openapi.yaml

# Check the running API and inspect Swagger UI.
curl -i http://127.0.0.1:8000/api/health/
```

After migration, `verify_schema.py` should report `SCHEMA VERIFICATION: PASS` and include all three numbered migrations with matching checksums. That result has not yet been observed.
