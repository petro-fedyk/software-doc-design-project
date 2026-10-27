# 01 — Architecture Overview (Revised)

## Decision
Use a Django modular monolith with server-rendered Django templates, HTML/CSS/vanilla JavaScript, Django views plus JSON REST endpoints, Django ORM, SQLite initially, and Docker Compose. Keep one deployable application and a dedicated **management-command worker process** in the same image for asynchronous outbox processing. No React, DRF by default, Celery, Redis, or microservices.

## Core dependency principle
**Domain rules are plain Python.** They must not import Django, ORM models, SQL, HTTP, settings, templates, or concrete payment/notification implementations. Application use cases depend on small `Protocol` contracts. Infrastructure implements those ports with Django ORM and mock gateways. The composition root wires concrete objects using constructor injection. This is dependency inversion, not a claim that Django provides a general-purpose DI container.

## Request flow
Browser -> Django URL/view -> application use-case service -> pure Python domain objects / ports -> ORM-backed repository adapter -> configured database.

## Django responsibilities
Django Auth and Groups provide baseline authentication and permissions. Object-level pharmacy assignment checks are explicit application authorization rules. Django Admin provides staff/network CRUD administration; it must be scoped and hardened, not considered a replacement for customer workflows. Django models belong to persistence infrastructure and map to/from domain entities for nontrivial workflows.

## Portability
Django ORM abstracts the SQLite/PostgreSQL backends, but migrations, transaction behavior, locking, concurrency, and data migration must be tested on both. Swapping the database should not change domain/business services. Do not promise zero-effort DB migration.

## Critical invariants
- One order is fulfilled by one pharmacy.
- Product master data is network-wide; price and stock are branch-specific.
- Checkout persists order, reservations and relevant outbox entries in a single DB transaction.
- Never charge real cards; use simulated payment gateways.
- Prescription fulfillment is pickup-only with mock verification for the coursework.
- Only appropriate delivery options are selectable.

## Non-goals
Microservices, event bus infrastructure, generic repository framework, reflection-based DI containers, additional database server by default, real pharmacy/prescription integrations or real monetary transactions.
