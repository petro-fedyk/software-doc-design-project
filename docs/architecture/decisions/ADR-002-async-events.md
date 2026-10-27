# ADR-002 — Durable Asynchronous Internal Observer Events

**Status:** Accepted for design.

**Context:** Event handling should not block HTTP, and events should not silently disappear during restart.

**Decision:** Commit domain mutations and SQLite outbox jobs in one transaction. One local background dispatcher (dedicated Django management-command worker process) executes registered observer callbacks after commit with idempotency keys and retries.

**Consequences:** More robust than fire-and-forget threads without adopting Celery/Redis/RabbitMQ. Not a distributed queue; with future multi-instance deployment, reassess claims/leasing or adopt dedicated worker architecture.
