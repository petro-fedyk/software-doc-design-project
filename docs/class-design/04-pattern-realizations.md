# 04 — Five GoF realizations

## 1 Strategy / discount selection
`PricingService` holds/receives a `DiscountPolicy` abstraction. `StandardDiscount`, `SocialDiscount`, `PremiumDiscount` implement it. Choose one according to eligible customer tier; every policy still respects product restrictions and Money types. Changing a tier strategy should not change checkout code.

## 2 State / order state-dependent behavior
`Order` holds persisted `OrderStatus` and delegates allowed transitions to `OrderState` objects. `CreatedState`, `ProcessingState`, `CompletedState`, and `CancelledState` express distinct transition behavior; confirmed/ready intermediate rules may remain explicit if diagram/class count would explode. Invalid transitions raise domain exceptions. Do not persist state object identities.

## 3 Observer / deferred domain-event handling
`EventPublisher` (Subject) registers `EventSubscriber` observers. `NotificationSubscriber` and `LoyaltySubscriber` receive events; separate handler identifiers track idempotency. Domain changes + `OutboxEvent` are written in one UoW. Django background worker later loads event and invokes registered observers. The Observer is the subscription/notification relationship; outbox is a durability mechanism, not GoF itself.

## 4 Factory Method / delivery workflow object creation
`DeliveryHandlerCreator.create_handler()` is the factory method. `PickupCreator`, `CourierCreator`, `PostalCreator` override it and produce handlers implementing `DeliveryHandler`. Mock handlers simulate fulfilment. Do not replace it with a single `if`/`switch` helper and still label it GoF Factory Method. Keep creation small and localized.

## 5 Builder / validated immutable draft
`OrderDraftBuilder` constructs an `OrderDraft` via staged methods: customer, branch, lines, delivery, totals, `build()`. It validates required fields and returns a consistent immutable draft. Business I/O and inventory reserve happen only in `OrderApplicationService`; do not put persistence and payments in builder. A Director class is not required.

## Why no Adapter pattern?
External interfaces are ports with simple mock infrastructure implementations. That does not require a separately mandated GoF Adapter pattern. Repository, DI and Unit of Work are not counted as GoF patterns.

## Interactions
Pricing Strategy -> Builder -> inventory and order repository under Unit of Work -> State transitions -> outbox -> asynchronous Observer handlers. Factory Method supplies the selected mock delivery handler for fulfilment. Failures must leave consistent stock, order, payment and outbox state.
