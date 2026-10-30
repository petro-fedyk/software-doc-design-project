# 01 — Architecture Overview

Current implementation (2026-10-29): a Django modular monolith with two independently served HTML/CSS/Vanilla JavaScript portals. Customer Portal runs on 4173; Management Portal on 4174; both reuse the existing Django REST API on 8000 and persistent MySQL `internet_pharmacy`. The outbox worker runs the same backend code and database.

Browser → portal same-origin proxy → Django JWT/role checks → application services → domain objects / repository ports → Django ORM → MySQL. This supersedes the earlier SQLite, server-rendered frontend and Django Admin proposal.

Domain rules remain plain Python. Infrastructure implements repository and Unit of Work contracts. The composition root uses constructor injection; no new infrastructure framework or backend service is introduced. Factory Method, Builder, Strategy, State and Observer are unchanged.

Each order belongs to one pharmacy. Stock and price are branch-local. Django enforces customer ownership, staff assignments and separate pharmacist qualification. JWT identities share one users table; each portal owns its browser session. Payments, delivery and prescription checks remain simulated.

See [portal architecture and requirements](../portals/ARCHITECTURE.md), [endpoint matrix](../portals/PAGE_API_MATRIX.md), and [deployment](08-deployment.md).
