# 09 — Stage 04 Definition of Done

Architecture review passes only if:

- [ ] Existing Stage 01–03 requirements and diagrams remain unchanged or differences are explicitly flagged.
- [ ] Every required functional group maps to a named module and primary owner.
- [ ] Data ownership between catalog, branch inventory, reservation, order, payment, and shipment is clear.
- [ ] Layer and module dependency rules are documented.
- [ ] Constructor injection and composition root are specified without claiming native Django DI; pure domain services have no ORM imports.
- [ ] Five named GoF patterns each have a real problem, participants, key method contracts, and at least one verifiable behavior.
- [ ] Background events are asynchronous to HTTP, durable, retryable, and idempotent.
- [ ] One-process SQLite concurrency and worker limits are documented.
- [ ] Docker persistence and cross-machine deployment expectations are described.
- [ ] Access-control, checkout atomicity, simulated prescriptions/payment and shipment boundaries are explicit.
- [ ] Architecture and sequence diagrams render.
- [ ] No application code, schema migration or production infrastructure is silently claimed to exist.

## Future implementation smoke tests
1. Admin creates branch and assigns worker; worker cannot edit other branches.
2. Product master appears in multiple branches with different prices and available stock.
3. Concurrent reservation attempts cannot oversell.
4. Cart validation respects simulated prescription pickup and shipment eligibility.
5. Checkout uses mock payment and mock shipping only.
6. Observer jobs survive simulated process restart and do not duplicate bonuses.
7. `docker compose up --build` serves UI and API; data survives restart.

## Traceability
Maintain a small mapping `FR -> module -> use case -> test` during Stage 05+; do not create a heavyweight requirements management system.

- [ ] Domain and application business rules do not import Django ORM or SQL backends.
- [ ] Application unit tests use in-memory fake ports without a database.
- [ ] All critical writes use an injected UnitOfWork and contract-tested repositories.
- [ ] Docker uses web + single worker from one image, with shared local SQLite volume.
