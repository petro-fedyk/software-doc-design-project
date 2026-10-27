# 04 — Dependency Injection and Persistence Ports

## Approach
Django is not a general-purpose dependency injection container. Use **constructor injection** in application services and a small `composition.py` module / factory for assembling implementations. Instantiate dependencies per command or request where transaction state exists; do not make mutable UoWs global singletons.

## Minimal shape (illustrative Python)
```python
from typing import Protocol

class OrderRepository(Protocol):
    def get(self, order_id: int) -> "Order | None": ...
    def save(self, order: "Order") -> None: ...

class UnitOfWork(Protocol):
    orders: OrderRepository
    def __enter__(self) -> "UnitOfWork": ...
    def __exit__(self, exc_type, exc_value, traceback) -> None: ...
    def commit(self) -> None: ...

class CancelOrder:
    def __init__(self, uow_factory):
        self.uow_factory = uow_factory

    def execute(self, order_id: int):
        with self.uow_factory() as uow:
            order = uow.orders.get(order_id)
            if order is None:
                raise OrderNotFound()
            order.cancel()   # pure domain operation
            uow.orders.save(order)
            uow.commit()
```
The example omits authorization and DTO mapping for brevity. `Order` is a **pure domain entity**, not a `models.Model`. A `DjangoOrderRepository` maps ORM rows to the domain object and back. A `FakeUnitOfWork` can support tests without DB access.

## Composition
`composition.py`: choose Django-backed repository factory, mock payment gateway, event publisher and delivery policy; inject these into each use case. Django views call these use cases; no `Order.objects` in domain/application code.

## Contracts and data access
Repository implementations must respect the same error, return-type and transaction semantics. Do not expose ORM QuerySets or Django exceptions across the boundary. Use plain DTOs/value objects where helpful. Avoid abstracting every read query into a universal repository; create narrow query services for UI read models if needed.

## Test obligations
- Unit tests use fake repositories/UoW and fake external gateways with no Django setup or database.
- Contract tests run the same suite on fake and Django-backed implementations.
- Django integration tests verify ORM mappings and transactional behavior.
- SQLite and PostgreSQL compatibility tests run where both DBs are available; at minimum document unverified PostgreSQL assumptions.
