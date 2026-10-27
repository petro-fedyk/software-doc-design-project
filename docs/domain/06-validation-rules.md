# 06 — Validation Rules and Invariants

These are business checks and security controls. UI validation provides convenience; server/domain validation remains authoritative.

| ID | Rule | Enforce when | Expected outcome |
|---|---|---|---|
| VAL-01 | Quantity is a positive integer | Cart, order, reservation | Reject zero/negative/fractional |
| VAL-02 | Monetary amounts are nonnegative fixed precision, currency explicit | Prices, orders, payments | Reject invalid amount/currency |
| VAL-03 | `available = onHand - reserved`, and `0 <= reserved <= onHand` | Every stock/reservation mutation | Reject conflicting update |
| VAL-04 | Global product identified independently from branch offering | Catalogue/stock | Prevent local fields in Product |
| VAL-05 | No duplicate active (branch, product) offering | Assortment changes | Reject duplicate |
| VAL-06 | Employee branch assignment required for scoped action | Every branch write/read of protected details | Forbidden if unassigned |
| VAL-07 | Admin role alone does not grant pharmacist verification authority | Rx verification | Forbidden without qualification |
| VAL-08 | Prescription-required items: pickup only, verified before handover (course scope) | Checkout/handover | Reject forbidden delivery/dispense |
| VAL-09 | Shipping requires product + branch + carrier eligibility | Delivery quote/order | Remove unavailable option with reason |
| VAL-10 | One fulfilment branch per order | Checkout | Require split/reselection |
| VAL-11 | Product active; branch active; enough stock at acceptance | Place order | Reject outdated quote |
| VAL-12 | Historical order items retain accepted price snapshot | Price edits/order read | Historical value unchanged |
| VAL-13 | Payment success requires trusted callback or sandbox confirmation | Payment transition | Ignore browser-only assertions |
| VAL-14 | Idempotency key deduplicates payment capture/refunds | Payment callbacks and retries | No duplicate charge/refund |
| VAL-15 | Captured refunds cannot exceed captured payments net of previous refunds | Refund request | Reject over-refund |
| VAL-16 | Loyalty completion event credits at most once | Loyalty accrual | Duplicate event no-op |
| VAL-17 | A customer accesses only own private records | Profiles/orders/Rx/loyalty | Forbidden otherwise |
| VAL-18 | Never log raw passwords, card numbers, prescription codes | Logs/telemetry/fixtures | Redact or omit |
| VAL-19 | Marketing notifications respect opt-in and channel preferences | Notifications | Suppress if not allowed |
| VAL-20 | Cancellation/expiration releases stock reservations exactly once | Order/reservation transitions | No negative or double release |
| VAL-21 | Deactivated branches/products cannot accept new orders | Checkout | Reject new ordering; preserve history |
| VAL-22 | Reminder schedule is set by the user, not inferred from medical need | Reminder configuration | Reject unwanted auto-scheduling |
| VAL-23 | State transition guard follows configured workflow | Every transition | Reject illegal transition |
| VAL-24 | Inventory updates must be atomic across concurrent requests | Reserve/consume/release | Prevent overselling |

## Worked stock example
Before: `onHand=10`, `reserved=3`, `available=7`. A request for 8 must fail. Two concurrent requests for 5 must not both succeed. A successful reservation for 5 produces `reserved=8`, `available=2`; cancellation releases 5 once (`reserved=3`). Completed handover consumes 5 once (`onHand=5`, `reserved=3` if that reservation was active immediately before completion).

## Error classification
- **Validation**: missing/invalid fields, quantities, price, delivery address.
- **Authorization**: customer attempts admin action, employee acts on another branch, unqualified Rx verification.
- **Conflict**: insufficient stock, duplicate assignment, stale price, illegal state transition.
- **Integration**: sandbox payment failure, carrier or notification provider unavailable.

## Quality criteria / suggested tests
- Property checks for inventory invariants under concurrent reservation attempts.
- Authorization matrix test per role and branch.
- State-transition table tests including forbidden transitions.
- Payment event replay/idempotency tests.
- Prescription handover denial when verification absent/failed.
- Shipping tests with cold-chain restriction and unsupported carrier.
- Loyalty award once and reversal on refund.

No real patient records, real e-prescription redemption codes or live card credentials should be used in tests.
