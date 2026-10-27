# 02 — Modules and Ownership

| Module | Owns | Primary operations | Outbound collaboration |
|---|---|---|---|
| identity | User, Role, customer profile | authenticate, authorize | staff assignments |
| network | Pharmacy, EmployeeAssignment | create branches, assign staff | identity |
| catalog | Product, Category, Manufacturer | search, maintain master product metadata | none |
| inventory | PharmacyInventory, movement, reservation | stock, price, reserve/release | catalog, network |
| ordering | Cart, Order, OrderItem | checkout, status transitions, cancellation | inventory, pricing, delivery, payment |
| prescriptions | mock prescription reference/verification | reservation policy, simulated verification | ordering, identity |
| delivery | method/rule, shipment | eligibility, quote, mock tracking | catalog, ordering |
| payments | Payment, Refund | start/confirm simulated payment | ordering |
| loyalty | tier, account, bonus transaction, promotions | compute discounts, credit bonus once | ordering |
| notifications | subscriptions, reminders, messages | enqueue and send mock notice | event processing |
| shared | event contracts, exceptions, transaction boundaries | common primitives only | none |

## Boundary rules
Modules do not import another module's infrastructure or models for ad-hoc mutations. Collaborate through application-facing ports and service methods. Explicitly allow a few direct read-only queries via interfaces, not a generalized event bus for every action.

Cross-module application orchestration (checkout) lives in `ordering`; stock invariant is enforced in `inventory`; payment result belongs to `payments`. Record module ownership for new entities before adding new tables.

## Suggested directory layout
```text
apps/backend/
  app/
    __init__.py                # create_app and composition root call
    config.py
    composition.py             # constructors and injected service wiring
    web/
      templates/
      static/css/
      static/js/
    modules/
      identity/{routes.py,service.py,domain.py,repository.py}
      network/{routes.py,service.py,domain.py,repository.py}
      catalog/{routes.py,service.py,domain.py,repository.py}
      inventory/{routes.py,service.py,domain.py,repository.py}
      ordering/{routes.py,service.py,domain.py,repository.py}
      prescriptions/{routes.py,service.py,domain.py,repository.py}
      delivery/{routes.py,service.py,domain.py,repository.py}
      payments/{routes.py,service.py,domain.py,repository.py}
      loyalty/{routes.py,service.py,domain.py,repository.py}
      notifications/{routes.py,service.py,domain.py,repository.py}
    shared/{events.py,worker.py,errors.py,unit_of_work.py}
    infrastructure/{database.py,mock_gateways.py}
  tests/{unit,integration}
  requirements.txt
  Dockerfile
```
Create module files as needed rather than adding empty boilerplate everywhere. An ORM model file may be split from `domain.py` if that separation clarifies business logic.
