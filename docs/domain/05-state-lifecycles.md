# 05 — State Lifecycles

Lifecycle names are conceptual. Implemented status names may differ, but meanings and transition guards must remain consistent. See Mermaid source files in `docs/diagrams/state/source/`.

## Order
`DRAFT` (cart, not persisted order) → `PENDING_CONFIRMATION` → `CONFIRMED` → `PROCESSING` → `READY_FOR_PICKUP` or `AWAITING_SHIPMENT` → `SHIPPED` (shipping) → `COMPLETED`.

Allowed cancellation from pending, confirmed, processing and ready (subject to policy); do not let `CANCELLED` or `COMPLETED` transition back to active. Payment status is separate. Shipping and pickup do **not** follow identical steps.

| From | Event / guard | To | Side effect |
|---|---|---|---|
| PENDING_CONFIRMATION | Stock reserved and checkout valid | CONFIRMED | Confirm order |
| CONFIRMED | Assigned employee starts work | PROCESSING | Record actor/time |
| PROCESSING | Pickup packed and available | READY_FOR_PICKUP | Notify customer |
| PROCESSING | Shipping packed, route approved | AWAITING_SHIPMENT | Create shipment |
| AWAITING_SHIPMENT | Carrier handoff confirmed | SHIPPED | Record tracking |
| READY_FOR_PICKUP | Pickup confirmed; Rx verified if applicable | COMPLETED | Consume reservations; loyalty event |
| SHIPPED | Delivery confirmed | COMPLETED | Finalize and loyalty event |
| Eligible nonterminal state | Cancellation allowed | CANCELLED | Release reservations, initiate refund if necessary |

Newly placed customer orders remain in `PENDING_CONFIRMATION` until pharmacy staff or an administrator confirms them. Staff cancellation requires one reason code: `OUT_OF_STOCK`, `PRICE_CHANGED`, `PRESCRIPTION_ISSUE`, `DELIVERY_UNAVAILABLE`, or `OTHER`. The code is retained on the order and returned in customer order history. Customer-initiated cancellation is recorded as `CUSTOMER_REQUEST`.

**Payment condition:** For prepaid orders, fulfilment requires successful payment; configurable pay-at-pickup permits later settlement. In either case completion must respect the selected payment policy.

## Reservation
`CREATED → ACTIVE → FULFILLED`; `ACTIVE → RELEASED` on cancellation; `ACTIVE → EXPIRED` if time runs out. All terminal paths decrement the reserved counter exactly once. Reservation expiry handling must not independently cancel already shipped orders.

## Payment
`PENDING → SUCCEEDED` (APPROVED), `FAILED` (DECLINED), or `UNKNOWN` (TIMEOUT) through the educational adapter. These are simulated outcomes, not bank authorizations. Refunds have their own lifecycle and do not retroactively change the captured payment into an unpaid one. Payment does not independently advance the order's fulfilment state; existing staff transitions remain subject to the payment gate.

## Shipment
`CREATED → PREPARING → SHIPPED → DELIVERED`; exceptions may lead to `EXCEPTION` and subsequently resolution. No `Shipment` for pickup orders by default.

## Prescription verification
`NOT_CHECKED → APPROVED / REJECTED` recorded as a verification event in simulated in-person flow. A later re-check produces another event, not silent overwriting. This is **not** integration with a real medical authority.

## Transition guarantees
1. Each change has an authorized actor, guard, timestamp and auditable reason when needed.
2. Replayed messages cannot duplicate stock consumption, loyalty credit, refund or payment capture.
3. No shipping transition may bypass product/branch/carrier eligibility.
4. No prescription handover without authorized verification.
5. Order, reservation, payment and shipment must **not** be compressed into one shared status field.
