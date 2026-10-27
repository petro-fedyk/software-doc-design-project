# 02 — Key class contracts (design, not executable code)

`Money` should use Decimal or integer minor units, explicit currency. All IDs are opaque. Signatures are descriptive, not framework-specific.

| Class | Essential attributes | Representative operations | Invariant |
|---|---|---|---|
| `Product` | `id`, `prescription_required`, `storage_policy` | `requires_prescription()` | Global record has no branch-level price |
| `BranchAssortment` | `branch_id`, `product_id`, `unit_price`, `active` | `change_price(new_price)` | Unique active branch-product offering; price >= 0 |
| `StockBalance` | `on_hand`, `reserved`, `version` | `available()`, `reserve(quantity)`, `release(quantity)` | `0 <= reserved <= on_hand`; concurrent persistence guarded |
| `Cart` | `owner_id`, `items` | `add_item()`, `change_quantity()`, `remove_item()` | Quantity > 0 |
| `Order` | `id`, `customer_id`, `branch_id`, `status`, `items`, `total` | `confirm()`, `mark_processing()`, `complete()`, `cancel()` | Status transition valid; accepted price snapshot immutable |
| `OrderItem` | `product_id`, `quantity`, `unit_price_snapshot`, `discount_snapshot` | `line_total()` | Values refer to accepted sale, not current catalog |
| `Reservation` | `order_id`, `assortment_id`, `quantity`, `status` | `fulfill()`, `release()`, `expire()` | Must not double-release stock |
| `Payment` | `order_id`, `amount`, `status`, `idempotency_key` | `mark_succeeded()`, `mark_failed()` | No duplicate capture |
| `OrderApplicationService` | `orders: OrderRepository`, `inventory: InventoryPort`, `uow: UnitOfWork`, `pricing: PricingService`, `builder: OrderDraftBuilder` | `place_order(command)`, `cancel_order(order_id)` | Reserve and save atomically; durable event in same transaction |
| `OrderRepository` | — | `get(order_id) -> Order?`, `save(order)` | Pure domain return values, never Django QuerySets |
| `InventoryPort` | — | `reserve(branch_id, product_id, qty)`, `release(reservation_id)` | Concurrent reserve atomic |
| `UnitOfWork` | — | `begin()`, `commit()`, `rollback()` | Covers order, inventory, outbox as a single DB transaction |
| `PaymentGateway` | — | `authorize(reference, amount, idempotency_key)` | Deterministic mock, no network payment or real credentials |
| `DiscountPolicy` | — | `calculate_discount(lines, eligibility) -> Money` | Policy must honor product restrictions |
| `OrderDraftBuilder` | `draft_fields` | `with_customer()`, `with_branch()`, `add_line()`, `with_delivery()`, `with_total()`, `build()` | `build()` rejects missing fields; has zero I/O |
| `OrderState` | — | `confirm(order)`, `start_processing(order)`, `complete(order)`, `cancel(order)` | Meaningful per-state behavior; persisted enum is source of truth |
| `EventPublisher` | `subscribers` | `subscribe(type, handler)`, `unsubscribe(type, handler)`, `publish(event)` | Listener registration and deterministic dispatch |
| `EventDispatcher` | `outbox: OutboxRepository`, `publisher: EventPublisher` | `process_next_batch()` | Retries and deduplicates durable events |
| `DeliveryHandlerCreator` | — | `create_handler() -> DeliveryHandler` | Factory Method overridden by three concrete creators |

## Cross-cutting design constraints
- The browser never receives ORM models; Django view transforms commands and DTOs.
- Business invariants are checked in pure domain and application services; SQL transaction implementation enforces atomicity.
- Payment, shipment, and reservation lifecycles are independent from `Order.status`.
- Pharmacist authority is checked from authorized staff records, not inferred from network admin rights.
- Recipe identifiers in this educational project are synthetic; no external Ukrainian eHealth verification is claimed.
- `DjangoOrderRepository` maps `Order` to/from `OrderORM`. Mapping must preserve snapshots, IDs, and states.
