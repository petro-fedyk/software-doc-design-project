# 05 — Traceability to requirements and business scenarios

| Business scenario (Stage 01/02) | Domain / application participants | Supporting interface or GoF |
|---|---|---|
| Catalog search / product detail | Product, Category, BranchAssortment, CatalogView | Django read-query infrastructure, storage policy |
| Branch availability / price | PharmacyBranch, BranchAssortment, StockBalance | InventoryPort for mutations |
| Basket and checkout | Cart, CartItem, Order, OrderItem, OrderApplicationService | OrderDraftBuilder, PricingService, OrderRepository, UnitOfWork |
| Discounts / loyalty tiers | LoyaltyAccount, LoyaltyEntry, PricingService | DiscountPolicy Strategy, LoyaltySubscriber |
| Reservation | Reservation, StockBalance | InventoryPort, UnitOfWork |
| Payment options | Payment, PaymentService | PaymentGateway, mock implementation |
| Pickup/courier/postal selection | DeliverySelection, Shipment, DeliveryService | DeliveryHandlerCreator Factory Method, delivery eligibility rules |
| Prescription reservation and in-person verification | PrescriptionReference, PrescriptionVerification, PrescriptionService | Authorized employee check, no real eHealth API |
| Order transitions / cancellation | Order, Reservation, Payment | OrderState State, compensating business steps |
| Notifications / availability and reminders | Notification, AvailabilityWatch, Reminder | EventPublisher Observer, outbox/worker, NotificationSender |
| Admin branches and staff | PharmacyBranch, EmployeeAssignment, RoleAssignment, AdminView | Django Admin + scoped permission checks |

Use-case IDs differ between diagrams (G/C/P/W/M/R). Map by scenario description rather than assuming identical IDs represent the same function. Verify with current Use Case catalog before final report.
