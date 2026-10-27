# 03 — UML relationships and direction

## Domain cardinality
| From | To | Meaning |
|---|---|---|
| `Customer` 1 | `Order` 0..* | Customer places orders |
| `PharmacyBranch` 1 | `BranchAssortment` 0..* | Branch owns its offerings |
| `Product` 1 | `BranchAssortment` 0..* | Product may be offered in many branches |
| `BranchAssortment` 1 | `StockBalance` 1 | One guarded current stock balance per offering |
| `Order` 1 | `OrderItem` 1..* | Composition, accepted line snapshots |
| `OrderItem` * | `Product` 1 | Referenced product, never composition |
| `Order` 1 | `Payment` 0..* | Payment attempts |
| `Order` 1 | `Reservation` 0..* | Stock holds |
| `Order` 1 | `DeliverySelection` 1 | Chosen fulfilment mode |
| `Order` 1 | `Shipment` 0..1 | Present for courier/postal fulfilment when shipped |
| `EmployeeAssignment` * | `PharmacyBranch` 1 | Staff scope by assignment |

## UML notation
- **Solid line** = association, attach cardinality near ends.
- **Filled diamond** at `Order` for composition with `OrderItem` (owned lifecycle).
- **Dashed open arrow** = use/dependency from client toward referenced type (`OrderApplicationService` -> `OrderRepository`).
- **Dashed line, hollow triangle at interface** = realization from `DjangoOrderRepository` to `OrderRepository`.
- **Solid line, hollow triangle at parent** = inheritance (`CreatedState` -> `OrderState` if ABC base used).
- Avoid generic unlabelled solid lines between unrelated service classes; prefer explicit port dependencies.

## Dependency constraints
Presentation -> Application -> Domain and Ports; Infrastructure -> Ports and Domain mapping. Domain MUST NOT import Django, HTTP, ORM, SQLite, background worker, `ServiceContainer`, or infrastructure modules. Composition root imports concrete implementations for assembly.

`OrderApplicationService` delegates inventory atomic operation and delegates transaction scope to `UnitOfWork`. The factory creates delivery handlers; their actual fulfilment occurs after checkout, not inside `OrderDraftBuilder`.
