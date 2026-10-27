# 10 — Persistence Abstractions and Database Independence

## Objective
Allow business services to be tested without a database and allow the persistence implementation to change without editing domain rules. Django ORM supplies portability between supported SQL backends; repositories isolate domain logic from the **ORM itself**.

## Separation
1. Pure Python domain entities/value objects implement invariants, transitions, calculations.
2. Application use cases coordinate operations via injected port interfaces.
3. Infrastructure ORM models represent persisted schema and relationships.
4. Mapper functions transform ORM models to/from domain entities.
5. Repository implementations implement domain/application ports.
6. UnitOfWork abstracts a transaction for multi-entity writes.

## Minimal ports (examples)
- `OrderRepository.get(id)`, `.save(order)`
- `InventoryPort.reserve(pharmacy_id, product_id, quantity)` with atomic semantics
- `UnitOfWork` for shared transactional boundary and outbox write
- `PaymentGateway.authorize(order_ref, amount, idempotency_key)` returns a plain result
- `NotificationSender.send(message)`; `EventPublisher.enqueue(event)`

## Scope
Do **not** create a repository class for every Django model. Simple Django Admin CRUD and read-only queries can use ORM directly **only in presentation/infrastructure**. Order, stock reservation, payments, prescription verification, and loyalty state changes go through explicit application contracts.

## Database migration acceptance
The same domain unit tests pass unmodified. Infrastructure mapping and transactions pass integration tests on the target backend. Check locking and isolation, field compatibility, migrations and data transfer. Configuration change alone is not proof of portability.

## Testing matrix
| Level | Storage | Purpose |
|---|---|---|
| Domain unit | None | Domain invariants and GoF policies |
| Application unit | Fake repositories/UoW | Business scenarios with no ORM |
| Adapter contract | SQLite test DB | Port behavior, mapper fidelity |
| API integration | Django test DB | Permissions, forms, HTTP behavior |
| Portability smoke | PostgreSQL optional | Same contract/transaction semantics |
| Container | SQLite volume | Startup, worker, restart persistence |
