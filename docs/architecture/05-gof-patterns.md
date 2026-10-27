# 05 — GoF Patterns (Five Scoped Uses)

Exactly five are selected to match the coursework decision. Keep each focused; avoid an elaborate class tree.

## 1. Strategy — Pricing/discount policy
**Problem:** standard/social/premium buyers and product-specific eligibility affect discounts.
**Participants:** `DiscountPolicy` interface, `StandardDiscount`, `SocialDiscount`, `PremiumDiscount`, `PricingService` context.
**Contract:** `calculate_discount(order_lines, customer_tier, eligible_products) -> Money` (use Decimal/integer cents, not binary float).
**DI:** Inject policy resolver/factory at `PricingService` boundary; domain must validate limits. Existing tier policy must not overwrite item eligibility checks.
**Evidence:** Switching policy changes discount calculation but not checkout orchestration.

## 2. State — Order lifecycle
**Problem:** allowed actions differ between CREATED/CONFIRMED/PROCESSING/READY/COMPLETED/CANCELLED.
**Participants:** `OrderState` protocol, narrowly scoped concrete states, `Order` context.
**Contract:** `confirm`, `start_processing`, `mark_ready`, `complete`, `cancel` validate transitions.
**Constraint:** Keep a persisted status enum as source of truth and map it to appropriate behavior. Do not create dozens of classes. If the course explicitly expects GoF State, implement a meaningful, small state family (at least CREATED/PROCESSING/COMPLETED/CANCELLED semantics) rather than renaming `if` statements without behavior.
**Evidence:** Invalid transitions rejected and valid transitions tested.

## 3. Observer — Domain event notifications
**Problem:** one committed domain event can trigger independent loyalty, notification and audit reactions.
**Participants:** `EventPublisher/Subject`, `EventHandler/Observer`, `OrderCompletedHandler`, `NotificationHandler`, optional `AuditHandler`.
**Mechanism:** durable outbox records enqueue events; a background dispatcher selects subscribers by event type and invokes handlers asynchronously relative to HTTP request.
**Evidence:** Register/remove observers in tests; multiple handlers receive one event, and duplicate event delivery is idempotent.

## 4. Factory Method — Creating mock delivery workflow handlers
**Problem:** pickup/courier/postal delivery needs distinct handler creation.
**Participants:** abstract `DeliveryHandlerCreator` with `create_handler()`, and `PickupCreator`, `CourierCreator`, `PostalCreator` overriding that method; a small interface `DeliveryHandler`.
**IMPORTANT:** A single if/switch function is a simple factory, not GoF Factory Method. Avoid confusing these. Only create three creator types if the distinction actually justifies the coursework requirement; share common orchestration.
**Evidence:** Each creator builds the correct handler; checkout depends only on delivery contract.

## 5. Builder — Order draft snapshot construction
**Problem:** create a validated immutable order draft with lines, chosen pharmacy, delivery method, discounts, and payable total before storage.
**Participants:** `OrderDraftBuilder`, `OrderDraft` product, optional director `OrderDraftAssembler` ONLY if reuse warrants it.
**Contract:** `with_customer`, `with_pharmacy`, `add_line`, `with_delivery`, `with_price`, `build()`.
**Constraint:** Builder only assembles/validates the draft. It MUST NOT reserve inventory, charge, send events or commit transactions. Checkout service coordinates those.
**Evidence:** Tests demonstrate an incomplete draft is rejected and a complete one is immutable/valid.

## Excluded patterns
No Adapter, Singleton, Command, Repository-as-GoF claim, or extra framework abstraction. Repository and DI are architectural techniques, **not** among the five GoF patterns.

## Pattern interaction
Checkout -> discount Strategy -> order draft Builder -> stock reservation and order persistence -> order State transitions -> committed outbox -> asynchronous Observer handlers. Factory Method constructs selected mock delivery handler used during fulfillment.
