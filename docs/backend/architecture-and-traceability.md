# Architecture and use-case traceability

## Layers

| Layer | Location | Responsibility |
|---|---|---|
| Domain | `apps/backend/pharmacy/domain/core.py` | Decimal money, quantity/stock invariants, state transitions, delivery eligibility, discount and loyalty calculations, draft construction, event publisher |
| Application | `pharmacy/application/` | Constructor-injected order/payment/inventory/customer services and independent notification/loyalty subscribers; no Django imports |
| Ports | `pharmacy/application/ports.py` | Aggregate-specific repository, payment/shipment, and Unit of Work protocols using plain Python values |
| ORM infrastructure | `pharmacy/models.py`, `pharmacy/infrastructure/repositories.py` | 31 unmanaged SQL mappings, domain mappers, locking, persistence and rollback |
| Alternative implementation | `pharmacy/infrastructure/memory.py` | In-memory checkout repositories/UoW tested by the same ordering contracts as MySQL |
| Providers | `pharmacy/infrastructure/providers.py` | Deterministic simulated payments/refunds and shipment references |
| Presentation | `pharmacy/api/` | Strict input serializers, JWT authentication, REST routes, ownership filtering, read queries and administrative CRUD |
| Composition | `pharmacy/composition.py` | Per-request constructor wiring; no mutable global service locator |
| Worker | `pharmacy/infrastructure/worker.py` | Durable outbox claim/dispatch/retry; scheduled maintenance |

Simple identity/catalogue/network administrative CRUD uses the ORM at the presentation boundary, as permitted by the Stage 04 architecture. Checkout, reservations, payment/refund processing, inventory mutations, prescription verification, customer scheduling, and loyalty operations use explicit services/ports. All domain and application modules remain importable without Django.

## UML pattern realization

| Pattern | Implementation | Observable use |
|---|---|---|
| Strategy | `DiscountPolicy`, `StandardDiscount`, `SocialDiscount`, `PremiumDiscount`, `PromotionDiscount`, `ProductEligibility` | Pricing selects the greatest eligible discount per line; rates come from persisted policy records; Rx lines are excluded |
| State | `OrderState` subclasses and persisted-state mapping | Different permitted transitions for pending, confirmed, processing, ready, shipping and terminal states |
| Observer | `EventPublisher`, `NotificationSubscriber`, `LoyaltySubscriber` | Independent subscribers handle committed order events; completion additionally awards points |
| Factory Method | `PickupCreator`, `CourierCreator`, `PostalCreator` | Concrete creators construct delivery handlers for eligibility/fees and simulated fulfillment |
| Builder | `OrderDraftBuilder` | Builds and validates an immutable draft without I/O; transaction and reservations belong to the application service |

The six existing UML class pages and six use-case pages were reviewed. Their source files were not modified. Names differ only where the SQL vocabulary is authoritative (`pharmacy_id`, for example, maps the conceptual branch identifier). The complete order lifecycle from the domain documentation supplements the representative State diagram.

## Operation coverage

| Domain operation | Implementation / REST entry point |
|---|---|
| OP-01 Search | `GET /products/` with `search`, `category`, `manufacturer`, `prescription_required`; product detail and `/availability/` |
| OP-02 Cart | `GET/PUT /cart/`; signed-cookie `GET/PUT /guest-cart/` |
| OP-03 Quote | `POST /checkout/quote/` |
| OP-04 Place | `POST /orders/`; current prices, single branch, atomic stock reservation |
| OP-05 Select payment | `payment_method` in checkout, enabled-method environment setting, `GET /payment-methods/` |
| OP-06 Confirm simulation | `/orders/{id}/pay/` creates pending payment; trusted worker invokes injected simulator |
| OP-07 Cancel | `/orders/{id}/transition/` with `CANCELLED`; idempotent release and queued refund |
| OP-08 Pickup | Staff state transitions; stock consumed exactly once at completion |
| OP-09 Shipment | `/orders/{id}/ship/`; asynchronous simulated tracking and current eligibility check |
| OP-10 Rx booking | Standard checkout with Rx product, enforced pickup-only |
| OP-11 Rx verification | `/orders/{id}/verify-prescription/`; same-branch authorized staff only |
| OP-12 Inventory receipt | `PATCH /pharmacies/{id}/inventory/{product_id}/` with `quantity`; signed `adjustment` supports recorded corrections |
| OP-13 Branch price | Same endpoint with `unit_price` |
| OP-14 Assortment | Same endpoint creates the branch/product pair or toggles `is_listed` |
| OP-15 Branch network | Administrative `POST/PATCH /pharmacies/` |
| OP-16 Assignment | `/admin/users/` and `/admin/assignments/` |
| OP-17 Global catalogue | Administrative product/category/manufacturer writes |
| OP-18 Loyalty/promotions | `/admin/loyalty-tiers/`, `/admin/promotions/`, `/admin/promotion-products/` |
| OP-19 Loyalty once | Completion subscriber and unique ledger event key; points snapshotted at completion |
| OP-20 Availability watch | `/availability-watches/`; stock-receipt subscriber |
| OP-21 Notifications | `/notifications/`, `/notifications/{id}/read/`, preferences and opted-in promotion dispatch |
| OP-22 Reminders | `/reminders/`; current opt-in required, worker schedules future occurrences |
| OP-23 Refund | `/orders/{id}/refund/`; staff assignment, amount limit and deterministic retry key |

All paths above have the `/api` prefix. Additional UML account and monitoring cases are covered by `/auth/register/`, `/auth/token/`, `/me/`, `/profile/`, `/prescriptions/`, `/orders/{id}/reorder/`, `/loyalty/`, branch statistics/audit, and network-wide statistics/audit. `DELETE /prescriptions/{id}/` is owner-scoped; all stored references are generated simulations.

Payment configuration is deployment configuration, not a database-backed administration screen, because the approved schema contains no payment-method configuration table. Professional pharmacist authorization is similarly deployment-managed pending the explicit schema proposal. These are documented limitations, not silently added tables.

## Policy decisions

- Money is Decimal in the domain and SQL; API monetary values serialize as decimal strings.
- Discounts use the largest eligible rate per line and do not stack. Prescription products receive no promotional/loyalty discount in this course implementation.
- Shipping charges are 55 UAH courier / 75 UAH postal / zero pickup in the replaceable delivery handlers.
- Reservations expire after 24 hours. Unshipped expired orders are cancelled through the normal application workflow, preserving refund/release semantics.
- Completion points apply to eligible goods net of the order discount, excluding shipping and Rx goods. Refund reversal is proportional to the refunded share of the order grand total.
- Product prescription/temperature flags cannot change while that product occurs in an open order. Price changes remain allowed and do not alter accepted snapshots.
- The database's one-delivery-per-order uniqueness is authoritative; reshipment is not implemented.
