# Internet Pharmacy — Stage 03 Domain Analysis

This package documents the **proposed domain model**, not implemented software. All files are in English. It builds on the previously agreed pharmacy network: guest/customer, branch-scoped pharmacy employee, network administrator, and authorized pharmacist; branch-specific prices/stock; pickup, courier and conditionally postal delivery; simulated prescription verification; sandbox payment methods; loyalty and notifications.

## Deliverables

| File | Purpose |
|---|---|
| `docs/domain/01-domain-overview.md` | Scope, assumptions, terminology, decisions and traceability |
| `docs/domain/02-entities.md` | Entity catalogue with core attributes and invariants |
| `docs/domain/03-relationships.md` | Multiplicities, ownership and consistency |
| `docs/domain/04-business-operations.md` | Commands, authorization, pre/postconditions, failures |
| `docs/domain/05-state-lifecycles.md` | Order, reservation, payment, shipment state machines |
| `docs/domain/06-validation-rules.md` | Data rules, authorization, invariants, concurrency and security |
| `docs/domain/07-domain-boundaries.md` | Business modules, ownership and interaction rules |
| `docs/diagrams/domain/source/*.mmd` | Mermaid conceptual diagrams, reviewable source |
| `docs/diagrams/state/source/*.mmd` | Mermaid state machine source |
| `AGENT_INTEGRATION_GUIDE.md` | Safe, idempotent monorepo integration instructions |

**Stage-03 exit criteria:** Every major use case has an identifiable owner, participating entities, operation preconditions/outcomes; critical invariants and state transitions are consistent; no framework, database engine, API route or GoF design pattern is prematurely mandated.

Mermaid sources are **not** native `.drawio` files. Render/export to SVG or redraw in diagrams.net only after review. No fake diagram exports are included.
