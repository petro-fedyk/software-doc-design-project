# 07 — Stage 05 acceptance checklist

- [ ] All important Stage 03 entities appear in the class catalogue (not necessarily on crowded overview page).
- [ ] Every essential class has clear ownership, invariants and meaningful operations.
- [ ] Relationship direction/cardinality and composition are correct.
- [ ] `Order` pure domain and `OrderORM` Django representation are clearly distinct.
- [ ] `OrderApplicationService` depends on `OrderRepository`, `InventoryPort`, `UnitOfWork`, not ORM.
- [ ] DI is constructor-based and wired at composition root, without a global service locator.
- [ ] Strategy, State, Observer, Factory Method, Builder each have a real participant structure and scenario.
- [ ] Observer is delivered asynchronously via outbox worker; business state/outbox recorded atomically.
- [ ] Factory Method is not merely a generic `switch` function; Builder performs no I/O.
- [ ] Core tests can use fake repositories, ports, UoW without DB.
- [ ] Django app/admin still enforce authenticated branch-scoped permissions.
- [ ] Diagrams open in diagrams.net; labels/links readable; DOT previews present.
- [ ] `docs/class-design/05-traceability.md` checked against current Use Case files.
- [ ] All outputs remain design documentation; no false claim of implemented classes or API.

**Stage completion means design is reviewable and consistent. Implementation remains a later stage.**
