# 03 — Dependency Rules

## Allowed imports
- `presentation` (Django views/forms/admin) -> application use cases, input/output DTOs.
- `application` -> pure domain entities, domain policies, narrow abstract ports (Python `Protocol` or ABC).
- `domain` -> Python standard library and pure domain types ONLY. **No Django models**, ORM queries, framework imports, settings, HTTP, filesystem or external gateways.
- `infrastructure` -> application/domain ports; Django ORM models, DB transactions and integrations.
- `composition` -> all layers as the single allowed place for constructing concrete dependencies.

## Boundaries
Application services own authorization and orchestration, transaction orchestration through injected `UnitOfWork`, not Django views. Django ORM models are persistence DTOs, not business-rule owners in critical flows. Repository mappers explicitly convert to/from plain domain entities; avoid leaking QuerySets, lazy ORM relations or database sessions across ports.

## Ports
Define focused ports for `OrderRepository`, `InventoryRepository`, `UnitOfWork`, `PaymentGateway`, `EventPublisher`, `NotificationSender`, `DeliveryPolicy` only when consumers need them. Keep read-only catalog/admin Django ORM operations pragmatic; critical domain flows must remain testable without ORM.

## Transactions
A checkout must atomically reserve inventory, create an order and enqueue an outbox record. Revalidate stock and price inside the transaction. For SQLite, use safe conditional updates and handle `database is locked` errors / contention with bounded retry; do not claim `select_for_update()` provides row-level locking on SQLite. PostgreSQL tests must verify semantics independently.

## Dependency graph tests
Static checks (or import inspection) should fail if `domain` imports `django`, `sqlite3`, `psycopg`, `infrastructure`, or `presentation`, or if application services import concrete repositories.
