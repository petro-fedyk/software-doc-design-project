# Phase 2 verification

Verification date: 2026-10-28.

| Check | Result | Evidence |
|---|---|---|
| Django configuration | PASS | `apps/backend/manage.py check`: no issues |
| Python lint | PASS | `ruff check apps/backend --select F`: all checks passed |
| OpenAPI | PASS | Generated and validated with `manage.py spectacular --validate --fail-on-warn` |
| Pure domain unit tests | PASS | `pytest -q apps/backend/tests/test_domain.py`: 17 passed |
| Backend automated suite | PASS | `MYSQL_DATABASE=internet_pharmacy_test .venv/bin/pytest -q`: 43 passed |
| MySQL schema validation | PASS | MySQL 8.0.42, InnoDB, 31/31 domain tables, 205 columns, 39 FKs, 36 CHECK constraints, 58 indexes |
| Phase 1 MySQL transaction suite | PASS | `db/scripts/test_mysql.py`: 6 passed, including rollback, FK/unique constraints, outbox and concurrent reservations |
| Live API and worker | PASS | Django server and outbox worker running locally against the manually started MySQL instance |
| HTTP health, schema and Swagger | PASS | `/api/health/`, `/api/schema/`, `/api/docs/` returned HTTP 200; health reported MySQL connected |

The database schema was not modified during Phase 2 verification. To unblock the test suite, access was granted only to the isolated `internet_pharmacy_test` database and the two existing SQL migrations were applied there. Django `migrate`, `makemigrations`, and `flush` remain disabled through the project management entry point. Docker Compose status could not be inspected because this shell user lacks access to the Docker socket; the API and worker were started locally instead. Do not point tests at the learning database.

## Reproduce checks

```bash
.venv/bin/python apps/backend/manage.py check
.venv/bin/ruff check apps/backend --select F
.venv/bin/python apps/backend/manage.py spectacular \
  --file docs/backend/openapi.yaml --validate --fail-on-warn
MYSQL_DATABASE=internet_pharmacy_test .venv/bin/pytest -q
.venv/bin/python db/scripts/verify_schema.py
.venv/bin/python db/scripts/test_mysql.py
```
