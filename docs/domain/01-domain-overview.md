# 01 — Domain Overview

## Objective
Model the rules, entities and responsibilities for an educational web application simulating a network of pharmacies. This stage describes **what the domain does**, independent of backend framework, REST endpoints, SQL schema and GoF implementation.

## In scope
- Shared product catalogue; branch-specific assortment, price, on-hand stock and availability.
- Customers, employee-to-branch assignments and network administration.
- Cart, one-fulfilment-branch-per-order checkout, reservations and fulfilment.
- Pickup, courier, and postal delivery **only when product restrictions and carrier capabilities permit**.
- Prescription medicine reservation for in-person handover and **simulated** authorized verification.
- Test-mode card/digital-wallet payment, offline/pay-at-pickup where configured, refunds.
- Loyalty tiers, promotions, points ledger, notifications and customer-configured reminders.

## Out of scope for the educational MVP
Real state e-health verification/dispensing, live medical records, real-money processing, automatic legal eligibility decisions, clinical advice, live carrier shipping APIs and production-grade pharmacy dispensing. Integration interfaces may be planned, not claimed to exist.

## Actors / authority
| Actor | Authorized scope |
|---|---|
| Visitor (guest/customer shared public capabilities) | Browse catalogue, search and check branch availability |
| Customer | Own cart, orders, saved prescription references, loyalty and notification settings |
| Pharmacy employee | Stock, local prices, assortment and orders **of assigned branches only** |
| Authorized pharmacist | Employee with additional professional authorization to verify/dispense prescriptions in simulation |
| Network administrator | Branches, employee accounts, assignments, global catalogue, platform policy and reporting; not automatically pharmacist authority |
| Payment provider / carrier / notification provider | Optional *external systems*, sandbox or adapters, not internal employees |

## Key vocabulary
- **Product**: shared catalogue description, not branch-specific inventory.
- **BranchAssortment**: a product offered by a branch, with branch-specific price, sale status and stock tracking.
- **StockBalance**: on-hand and reserved units for an assortment item; available = onHand - reserved.
- **Reservation**: time-bounded commitment of units to an order; not a purchase or prescription approval.
- **Order**: immutable purchased-item snapshots and chosen fulfilment branch, plus lifecycle state.
- **Payment**: separate external/simulated monetary transaction with its own lifecycle.
- **Shipment**: delivery fulfilment tracking, only when delivery is selected.
- **PrescriptionVerification**: educational record of an authorized in-person verification outcome, not actual e-health validation.

## Design decisions (proposed; validate with supervisor)
| ID | Decision |
|---|---|
| D-01 | Every order uses exactly one fulfilment branch. Mixed-branch carts must be split or corrected before submission. |
| D-02 | Global product metadata belongs to administrators; assigned employees manage branch assortment, price and stock only. |
| D-03 | Prescription-required products are reserve-for-pickup only in the course project; final handover is conditioned on authorized verification. This is a **project constraint**, not a universal legal claim. |
| D-04 | Eligibility for shipping is the intersection of product rules, branch capabilities, carrier capabilities and applicable restrictions. Storage temperature alone is insufficient. |
| D-05 | Payments occur via test/sandbox integration; no card PAN/CVV is stored. |
| D-06 | Loyalty points accrue once upon completed eligible purchase; returns/reversals create compensating ledger entries. |
| D-07 | Money amounts and purchase prices are snapshotted when the order is accepted; later catalogue price changes do not rewrite historical orders. |
| D-08 | Patient/prescription data is minimized and access-restricted; use synthetic examples only. |

## Traceability examples
| Existing use-case family | Domain coverage |
|---|---|
| UC-01 catalog, checkout, payment, delivery | Product, BranchAssortment, Cart, Order, Reservation, Payment, DeliverySelection, Shipment |
| UC-02 account, loyalty, reminders | User, CustomerProfile, LoyaltyAccount, LoyaltyEntry, NotificationPreference, AvailabilityWatch, Reminder |
| UC-03 branch operations | PharmacyBranch, EmployeeAssignment, BranchAssortment, StockBalance, StockMovement, Order |
| UC-04 network administration | PharmacyBranch, User, RoleAssignment, EmployeeAssignment, Product, LoyaltyPolicy, Promotion |
| UC-05 prescription reservation | Product, Reservation, PrescriptionReference, PrescriptionVerification, Order |

## Open decisions to record before detailed design
1. Whether a guest can maintain a temporary cart (recommended) but must sign in before checkout.
2. Whether pickup orders allow pay-at-pickup (recommended configurable).
3. Whether each physical batch/expiry needs tracking (recommended as future extension; MVP tracks units per branch-product).
4. Whether multiple concurrent payment attempts are permitted (recommended: yes, but at most one captured payment per obligation).
5. Loyalty points conversion rate and product exclusions: configuration, not hardcoded medical rules.

## Acceptance of this stage
Requirements can be traced to concepts, operations and invariants. Open decisions are explicitly marked; no unverified e-prescription or courier integrations are presented as implemented.
