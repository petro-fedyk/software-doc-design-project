# 07 — Domain Boundaries and Responsibilities

These are **logical domains**, not mandated deployable microservices or directories. A modular monolith is a good default for this course project.

| Domain module | Owns | May request from | Must not own |
|---|---|---|---|
| Identity & Access | User, roles, profiles, employee authorization | Pharmacy Network assignments | Order fulfilment logic |
| Pharmacy Network | PharmacyBranch, EmployeeAssignment | Identity identities | Customer carts or payments |
| Catalogue | Product, Category, Manufacturer, StoragePolicy | None | Branch stock or local price |
| Inventory | BranchAssortment, StockBalance, StockMovement, Reservation | Catalogue and Network | Card payments, loyalty balance |
| Ordering | Cart, CartItem, Order, OrderItem | Inventory, Delivery eligibility, Payments status | Direct database changes to foreign modules |
| Delivery | DeliverySelection, Shipment, eligibility policies | Catalogue policy, Network and carrier capabilities | Prescriptions or card credentials |
| Payments | Payment, Refund, provider references | Ordering obligation | Order item mutation or stock ownership |
| Prescription Workflow | PrescriptionReference, PrescriptionVerification | Identity/authority, Orders and Catalogue flags | Claiming real e-health verification |
| Loyalty | LoyaltyTier/Account/Policy/Entry, Promotion | Confirmed order event | Editing past OrderItems |
| Notifications | Notification, Preferences, Watch, Reminder | Domain events and customer preferences | Defining order state |
| Audit | AuditEvent | Authorized domain changes | Sensitive health secrets |

## Proposed interaction flow: checkout
1. Ordering validates cart and chosen fulfilment branch.
2. Delivery evaluates permitted methods based on all lines, carrier and branch capability.
3. Inventory atomically holds each order item.
4. Ordering persists order and accepted price/discount snapshots.
5. Payments runs an independent sandbox attempt if selected.
6. Order transitions are determined by payment policy and fulfilment state.
7. Notifications may consume status events without blocking the core order.

## Proposed domain events (illustrative)
`StockChanged`, `ReservationPlaced`, `ReservationReleased`, `OrderPlaced`, `OrderConfirmed`, `OrderCompleted`, `OrderCancelled`, `PaymentSucceeded`, `RefundCompleted`, `ProductBecameAvailable`, `LoyaltyPointsAccrued`, `PrescriptionVerificationRecorded`.

**Delivery semantics:** Events are logical contracts only. Do not claim an actual message broker exists at this stage. Consumers need idempotent handlers when at-least-once delivery is used.

## Boundaries to keep strict
- UI controllers validate transport shape but do **not** decide stock rules or prescription eligibility.
- Domain services enforce policies regardless of HTTP, CLI, background worker or tests.
- Persistence repositories load and store domain state; they do not invent business policy.
- Payment gateway adapters translate provider protocol; only verified results update domain payment state.
- Permission policy applies per branch and, for prescriptions, per professional qualification.
- Reporting may read across domains but must not mutate operational state.

## Stage 04/05 follow-up
Determine architecture layers, GoF patterns only where motivated (`Strategy` delivery/loyalty policies, `State` complex transitions, `Adapter` external gateways, event handlers for notifications), final UML class responsibilities, and ERD. Pattern selection is **not a deliverable of Stage 03**.
