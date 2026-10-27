# 08 — Stage 05 Diagram Repair Review

The existing six-page editable file was repaired in place at `docs/diagrams/Internet_Pharmacy_Class_Diagrams.drawio`. Its original is preserved byte-for-byte at `docs/diagrams/Internet_Pharmacy_Class_Diagrams.before-stage05-repair.drawio`. No application code or earlier-stage documentation was changed.

## Page-by-page changes

1. **System Class Overview:** Reorganized into Presentation, Composition Root, Application, Domain, Ports/Interfaces, and Infrastructure clusters. Routed dependencies to ports, infrastructure implementations to their interfaces, and kept `OrderORM` in Infrastructure. `Order` composes only `OrderItem`; `Product` is a referenced entity. Added branch assortment, stock, reservation, payment, delivery, and draft-line relationships with multiplicities. The representative pattern classes are shown beside their interfaces.
2. **Strategy — Discounts:** Connected each concrete discount policy to `DiscountPolicy` with its own realization. `ProductEligibility` is a separate policy dependency used by `PricingService`; it is not a Strategy implementation.
3. **State — Order:** Connected `Order` to the `OrderState` abstraction and each representative concrete state independently to the interface. Removed state-to-state relationships; the page describes behavior, not lifecycle transitions.
4. **Observer — Domain Events:** Separated the in-process publisher/subscriber API from durable asynchronous dispatch. Added an `OutboxRepository`; subscribers independently realize `EventSubscriber`. `DomainEvent` is a parameter/value object, not an observer. A note documents atomic business/outbox commit, later worker dispatch, retries, and idempotency.
5. **Factory Method — Delivery:** Routed each concrete creator to the abstract creator and each handler to `DeliveryHandler`. Each creator has a `«creates»` dependency to its matching handler.
6. **Builder — Order Draft:** `OrderApplicationService` depends on `OrderDraftBuilder`; the builder produces `OrderDraft`. The draft composes one-or-more lines and references its delivery selection. The note limits Builder to draft construction and validation; placement, reservation, persistence, payment, and event recording remain application-service work.

## Validation performed

- Parsed the native `.drawio` XML and confirmed it contains six diagram pages in the original order. All edge source and target IDs resolve to cells on their own page.
- Exported pages 1–6 individually with diagrams.net Desktop 32.6.1. All six exports completed successfully and were visually inspected for page content, legibility, and connector routing.
- The deliverable remains a native, editable diagrams.net `.drawio` document; the PNG exports were temporary visual checks and are not included in the repository.
- No application source code was changed.

## Known simplifications and decisions to reconcile

- The overview uses `Customer`-related IDs but does not expand Stage 03's `User`, `CustomerProfile`, and `EmployeeProfile`; those identity concepts remain in the domain model and need a later naming/ownership decision.
- Stage 03 allows `Order` to have `0..*` shipments for possible reshipment; the Stage 05 class catalogue says `0..1`. The overview deliberately omits Shipment multiplicity until this is resolved.
- The State page is representative. The complete persisted lifecycle, including confirmed, ready, awaiting-shipment, and shipped statuses, remains in Stage 03. Whether those statuses need separate State classes is an implementation/design decision.
- The Builder page models `DeliverySelection` on the draft during checkout; Stage 03 specifies the final `Order` relationship. The draft value should be snapshotted into the accepted order.
- `DjangoInventoryAdapter` means an infrastructure implementation of `InventoryPort`; it does not introduce the excluded GoF Adapter pattern. `ServiceContainer` is a conceptual composition-root box, not a global service locator.
- The overview omits secondary entities and the full event/outbox workflow by design; the detailed pattern pages carry those relationships.
