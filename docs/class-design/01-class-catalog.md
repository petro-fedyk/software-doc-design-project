# 01 — Class catalogue and ownership

These are proposed Python-level classes. Attributes below are selective; Stage 03 `02-entities.md` remains the full logical attribute inventory. Keep domain entities independent of Django ORM.

| Module | Class / interface | Kind | Responsibility |
|---|---|---|---|
| Identity | `Customer`, `EmployeeAssignment`, `RoleAssignment` | domain | Identity references and branch access facts; framework auth stays infrastructure |
| Network | `PharmacyBranch` | entity | Operating branch identity and fulfilment settings |
| Catalog | `Product`, `StoragePolicy`, `Category`, `Manufacturer` | entity/value | Shared product data and shipping restrictions |
| Inventory | `BranchAssortment`, `StockBalance`, `StockMovement`, `Reservation` | entity/value | Branch price, on-hand vs reserved stock, auditable movements and holds |
| Cart | `Cart`, `CartItem` | entity | Provisional contents before checkout |
| Ordering | `Order`, `OrderItem`, `OrderDraft` | entity/value | Accepted order snapshot and immutable draft |
| Ordering | `OrderApplicationService`, `OrderDraftBuilder` | application/domain helper | Checkout orchestration and draft construction |
| Ordering | `OrderState`, `CreatedState`, `ProcessingState`, `CompletedState`, `CancelledState` | strategy-like state objects | Permitted order transitions, distinct behavior |
| Ordering | `OrderRepository`, `UnitOfWork` | ports | Persistence and transaction boundaries |
| Inventory | `InventoryPort` | port | Atomically reserve/release stock in a transaction |
| Pricing | `PricingService`, `DiscountPolicy`, `StandardDiscount`, `SocialDiscount`, `PremiumDiscount` | service + strategy | Eligible discount calculations, Money semantics |
| Payments | `Payment`, `PaymentService`, `PaymentGateway`, `MockPaymentGateway` | entity/service/port/infra | Idempotent payment initiation and state recording |
| Delivery | `DeliverySelection`, `Shipment`, `DeliveryService`, `DeliveryHandler` | entities + service/port | Eligibility and simulated fulfilment |
| Delivery | `DeliveryHandlerCreator`, `PickupCreator`, `CourierCreator`, `PostalCreator` | GoF factory creators | Create selected delivery handler |
| Prescriptions | `PrescriptionReference`, `PrescriptionVerification`, `PrescriptionService` | entities + service | Simulated onsite verification, authorization checks |
| Loyalty | `LoyaltyAccount`, `LoyaltyEntry`, `LoyaltyService` | entities + service | One-time posting of bonus accrual/reversal |
| Notifications | `DomainEvent`, `EventPublisher`, `EventSubscriber`, `NotificationSubscriber`, `LoyaltySubscriber` | event/ports/observers | Decoupled reactions to committed domain events |
| Notifications | `OutboxEvent`, `OutboxRepository`, `EventDispatcher`, `NotificationSender` | infrastructure/ports | Durable queued events and background delivery |
| Data | `DjangoOrderRepository`, `DjangoUnitOfWork`, `DjangoInventoryAdapter` | infrastructure implementations | Django ORM mapping and atomic persistence (adapter here means port implementation, **not a mandated GoF Adapter pattern**) |
| Data | `OrderORM`, `OrderItemORM` | Django models | Database representation only |
| Presentation | `OrderView`, `CatalogView`, `AdminView` | Django views | Input, auth boundary, DTOs, output; no domain decisions |
| Bootstrap | `ServiceContainer` | composition root | Construct dependencies in application startup, not domain Singleton |

## Disciplined naming
- `Order` denotes pure domain model; `OrderORM` denotes infrastructure model.
- `OrderRepository` denotes a Protocol / ABC; `DjangoOrderRepository` implements it.
- `UnitOfWork` is a transactional port with a Django implementation. DB transition semantics must be tested.
- Do not create repository interfaces for every catalog lookup; ordinary admin CRUD can call ORM in presentation/infrastructure.
- Observer delivery is async relative to HTTP; outbox commits atomically with business changes.
