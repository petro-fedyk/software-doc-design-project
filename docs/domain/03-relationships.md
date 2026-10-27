# 03 — Relationships and Multiplicities

This is a **conceptual** object model, not a database diagram. Multiplicities express intended business rules and may be refined before persistence design.

| Source | Target | Multiplicity and meaning | Ownership / notes |
|---|---|---|---|
| User | CustomerProfile | 1 ↔ 0..1 | Only customer identities |
| User | EmployeeProfile | 1 ↔ 0..1 | Only employed identities |
| User | RoleAssignment | 1 → 0..* | Authorization managed centrally |
| EmployeeProfile | EmployeeAssignment | 1 → 0..* | Historical assignments retained |
| PharmacyBranch | EmployeeAssignment | 1 → 0..* | Branch may have multiple employees |
| Product | Category | many → 1 | Category is shared |
| Product | Manufacturer | many → 1 | Producer is shared |
| Product | StoragePolicy | many → 1 | Reused policy permitted |
| PharmacyBranch | BranchAssortment | 1 → 0..* | Branch-specific offering |
| Product | BranchAssortment | 1 → 0..* | Each offering points to global product |
| BranchAssortment | StockBalance | 1 ↔ 1 | Stock quantity per branch-product in MVP |
| BranchAssortment | StockMovement | 1 → 0..* | Stock ledger records |
| CustomerProfile | Cart | 1 → 0..* historical; at most 1 active | Guest carts may instead use session key |
| Cart | CartItem | 1 → 0..* | Draft items |
| CustomerProfile | Order | 1 → 0..* | Own orders only |
| PharmacyBranch | Order | 1 → 0..* | Exactly one fulfilment branch per order |
| Order | OrderItem | 1 → 1..* | Composition: order controls items |
| Product | OrderItem | 1 → 0..* | Order item snapshots survive catalogue edits |
| Order | Reservation | 1 → 0..* | Typically one reservation per order line/assortment |
| BranchAssortment | Reservation | 1 → 0..* | Only reservations for same branch |
| Order | DeliverySelection | 1 ↔ 1 | Pickup or shipping choice |
| Order | Shipment | 1 → 0..* | Zero for pickup; allows re-shipment as future extension |
| Order | Payment | 1 → 0..* | Multiple attempts possible, settlement guarded |
| Payment | Refund | 1 → 0..* | Cumulative refund <= captured amount |
| CustomerProfile | PrescriptionReference | 1 → 0..* | Private data, optional |
| Order | PrescriptionVerification | 1 → 0..* | May require re-check; latest valid result controls dispensing |
| EmployeeProfile | PrescriptionVerification | 1 → 0..* | Must have current professional authority |
| CustomerProfile | LoyaltyAccount | 1 ↔ 0..1 | Optional enrolment |
| LoyaltyTier | LoyaltyAccount | 1 → 0..* | One current tier per account |
| LoyaltyAccount | LoyaltyEntry | 1 → 0..* | Append-only points ledger |
| CustomerProfile | Notification | 1 → 0..* | Delivery status per notification |
| CustomerProfile | AvailabilityWatch | 1 → 0..* | Scoped to product and optional branch |
| CustomerProfile | Reminder | 1 → 0..* | User-controlled schedule |

## Cross-entity integrity rules
1. Every `OrderItem` product must have been available through the order's fulfilment branch when accepted.
2. Every `Reservation.assortmentId` must belong to the same branch as its `Order.branchId`.
3. Sum of active holds must reconcile to `StockBalance.reserved`.
4. A branch-scoped employee mutation requires an active `EmployeeAssignment` matching the target branch.
5. A postal/courier order must have a supported destination and eligible lines; pickup must have an active branch.
6. A prescription-required line can be handed over only after authorized in-person verification in the course simulation.
7. `Payment` captures and `LoyaltyEntry` accruals require deduplication, even on retried events.
8. A deactivated product/branch cannot be newly ordered, but historical snapshots remain intact.

## Diagram instructions
See `../diagrams/domain/source/domain-model.mmd`; validate cardinalities before translating to full UML class diagram in Stage 05. Do not confuse this conceptual diagram with the relational schema.
