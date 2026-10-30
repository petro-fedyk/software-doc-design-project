> Current frontend architecture (2026-10-29): two independent portals, one Django API and one MySQL database. See [portal requirements, sessions and roles](../portals/ARCHITECTURE.md) and [page/API responsibility matrix](../portals/PAGE_API_MATRIX.md). Historical framework/database deployment assumptions below are superseded by that implementation.

# 04 — Business Operations

This catalogue describes domain *commands and outcomes*, not API endpoints. IDs are stable for later traceability.

| ID | Operation (actor) | Preconditions / rules | Affected concepts | Success / failure |
|---|---|---|---|---|
| OP-01 | Search products (visitor) | Only active publicly visible products | Product, Category, BranchAssortment | Results filtered / empty results |
| OP-02 | Manage cart (customer/guest session) | Positive quantity, visible product | Cart, CartItem | Updated cart / validation error |
| OP-03 | Quote checkout (customer) | Choose single branch; validate lines and fulfilment options | Cart, BranchAssortment, DeliverySelection, Promotion | Quoted amount/options / conflict or ineligible delivery |
| OP-04 | Place order (customer) | Authorized, valid quote, available quantities, valid delivery selection | Order, OrderItem, Reservation, StockBalance | Order and atomic holds / insufficient inventory, stale price, forbidden item |
| OP-05 | Select payment method (customer) | Allowed for chosen delivery/order | Payment method choice | Payment initiated or offline condition recorded / unavailable method |
| OP-06 | Run educational card-payment scenario (customer) | Fictional credentials validated in browser; selected scenario and idempotency key | Payment, Order, outbox | Adapter returns APPROVED/DECLINED/TIMEOUT; duplicate safely ignored; no card credentials reach API |
| OP-07 | Cancel order (customer/employee) | Policy allows state transition | Order, Reservation, Payment, Refund | Cancel/release/refund workflow / cancellation forbidden |
| OP-08 | Fulfil pickup order (assigned employee) | Order ready; if Rx, valid pharmacist verification | Order, Reservation, StockBalance | Completed and stock deducted / verification missing |
| OP-09 | Prepare shipment (assigned employee) | Shipping eligible, address valid, stock reserved | Shipment, Order | Label/tracking placeholder / carrier mismatch |
| OP-10 | Book Rx pickup (customer) | Rx product, active branch, stock, pickup only | Order, Reservation | Booking held / unavailable or ineligible |
| OP-11 | Verify Rx (authorized pharmacist) | Current professional authority and same branch; **mock validation only** | PrescriptionVerification, Order | Pass/fail audit outcome / unauthorized or invalid simulation |
| OP-12 | Receive inventory (assigned employee) | Stock movement has positive delta and reason | StockMovement, StockBalance | Increased onHand / invalid adjustment |
| OP-13 | Adjust branch price (assigned employee) | Assigned branch, nonnegative valid amount | BranchAssortment, AuditEvent | Updated local price / forbidden |
| OP-14 | Change branch assortment (assigned employee) | Global product exists and active | BranchAssortment | Offered or deactivated / duplicate pair |
| OP-15 | Create branch (admin) | Unique branch identity, valid location | PharmacyBranch, AuditEvent | Branch created / invalid data |
| OP-16 | Assign employee (admin) | Active employee and branch | EmployeeAssignment, RoleAssignment | Assignment created / invalid/duplicate |
| OP-17 | Maintain global catalogue (admin) | Product fields and regulatory flags validated | Product, Category, StoragePolicy | Catalogue updated / invalid change |
| OP-18 | Configure loyalty and promotions (admin) | Valid periods, nonnegative rates, exclusions | LoyaltyPolicy, Promotion | Rules published / invalid overlap |
| OP-19 | Accrue loyalty once (system) | Completed eligible order, unique event key | LoyaltyAccount, LoyaltyEntry | Points ledger updated / duplicate no-op |
| OP-20 | Watch availability (customer) | Valid active product, optional branch | AvailabilityWatch | Watch created / already subscribed |
| OP-21 | Notify customer (system/provider) | Allowed type, preference/consent, minimal payload | Notification, NotificationPreference | Sent/queued or skipped / provider failed |
| OP-22 | Schedule personal reminder (customer) | Customer opts in and chooses schedule | Reminder | Created/changed/disabled / invalid schedule |
| OP-23 | Refund successful payment (authorized staff/system) | Settlement exists, amount <= refundable balance | Refund, Payment, Order | Refund recorded / over-refund denied |

## Detailed operation contracts

### OP-04 — Place order
1. Validate customer authorization, cart contents, current active branch, prices and product restrictions.
2. Resolve delivery eligibility for **every** line and selected carrier/method.
3. Atomically re-check and reserve available units per branch-product; concurrent orders must not over-reserve.
4. Snapshot line description, quantities, unit prices, discount, fulfilment method and total.
5. Create order and reservations in a single consistent transaction; commit or roll back all.
6. Initiate payment separately if selected; unpaid does not mean paid.

**Errors:** `OUT_OF_STOCK`, `PRICE_CHANGED`, `BRANCH_UNAVAILABLE`, `DELIVERY_NOT_ALLOWED`, `INVALID_CART`, `AUTH_REQUIRED`.

### OP-07 — Cancel order
Only permitted states transition to cancelled. Release each active reservation exactly once, prevent shipment dispatch after cancellation and create a refund request when payment was captured. Record audit and notify customer; do not assume a refund is instantaneous.

### OP-08 / OP-11 — Prescription handover
Only an authorized pharmacist can record the simulated verification outcome. A negative or missing outcome blocks physical handover. Do not store real prescription access codes in screenshots, source code, fixtures or logs.

### OP-19 — Loyalty accrual
Compute points from the eligible final order amount and applicable policy. Write a unique ledger event tied to completion; retrying the event must not double-credit. Partial refunds require compensating adjustments as configured.

## Exception policy
Operations reject invalid input explicitly. Never silently clamp negative quantities, convert restricted delivery to postal shipping, mark a failed payment paid, or finalize prescription handover based only on a customer-supplied reference.
