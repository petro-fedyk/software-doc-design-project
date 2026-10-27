# 02 — Entity Catalogue

Notation: `*` required, `?` optional; logical types are indicative (not SQL definitions). IDs are opaque; timestamps use UTC. `Money` = amount + ISO currency; never floating-point currency calculations.

## Identity and organization
| Entity / value object | Essential attributes | Responsibility / invariants |
|---|---|---|
| **User** | id*, email*, passwordHash*, status*, createdAt* | Identity; normalized unique email, status active/disabled |
| **RoleAssignment** | id*, userId*, role*, branchId? | Platform/branch permissions; avoid interpreting admin as pharmacist credential |
| **CustomerProfile** | userId*, displayName*, contactPhone?, preferences? | Customer-specific public/contact profile, customer-owned |
| **EmployeeProfile** | userId*, employeeStatus*, professionalAuthorization? | Employment/personnel attributes; authorization verified separately |
| **PharmacyBranch** | id*, name*, address*, contact*, active*, pickupEnabled* | Branch-level operations, location, fulfilment capabilities |
| **EmployeeAssignment** | id*, employeeId*, branchId*, activeFrom*, activeTo? | Assignment to one or more branches; permission checked for every operation |

## Catalogue and inventory
| Entity / value object | Essential attributes | Responsibility / invariants |
|---|---|---|
| **Product** | id*, name*, categoryId*, manufacturerId*, prescriptionRequired*, storagePolicyId*, status* | Shared product identity and regulated flags; no local price/quantity |
| **Category** | id*, name*, active* | Classification |
| **Manufacturer** | id*, name* | Producer metadata |
| **StoragePolicy** | id*, transportConditions*, shippingRestrictions*, specialHandling? | Machine-readable eligibility criteria; no automatic legal inference |
| **BranchAssortment** | id*, branchId*, productId*, unitPrice*, active* | Branch-product offering; unique active pair (branch, product) |
| **StockBalance** | assortmentId*, onHand*, reserved*, version* | `0 <= reserved <= onHand`; available derived, not freely editable |
| **StockMovement** | id*, assortmentId*, kind*, delta*, actorId*, occurredAt*, reason? | Auditable stock adjustments; never silently overwrite stock history |

## Ordering and fulfilment
| Entity / value object | Essential attributes | Responsibility / invariants |
|---|---|---|
| **Cart** | id*, ownerUserId?, sessionKey?, updatedAt* | Draft selection; customer/session-specific |
| **CartItem** | id*, cartId*, productId*, quantity* | quantity > 0; provisional prices are not guaranteed |
| **Order** | id*, customerId*, branchId*, status*, currency*, totalSnapshot*, createdAt* | One fulfilment branch; contains immutable accepted terms |
| **OrderItem** | id*, orderId*, productId*, quantity*, unitPriceSnapshot*, discountSnapshot* | Historical snapshots; do not depend on mutable branch price |
| **Reservation** | id*, orderId*, assortmentId*, quantity*, status*, expiresAt? | Hold quantity until consumed/released; reserve and release atomically |
| **DeliverySelection** | orderId*, method*, destinationSnapshot?, eligibilitySnapshot* | Pickup / courier / postal; destination required by method |
| **Shipment** | id*, orderId*, carrier?, trackingNumber?, status*, shippedAt? | Exists for shipment-mode orders; tracking may be simulated |

## Financial and pharmacy-specific
| Entity / value object | Essential attributes | Responsibility / invariants |
|---|---|---|
| **Payment** | id*, orderId*, providerReference?, method*, amount*, status*, idempotencyKey* | Payment attempts separate from order; retries do not duplicate capture |
| **Refund** | id*, paymentId*, amount*, status*, requestedAt* | Linked to successful captured payment; cannot exceed refundable amount |
| **PrescriptionReference** | id*, customerId*, maskedReference?, encryptedPayload?, createdAt* | Minimal synthetic or consented data; protected access |
| **PrescriptionVerification** | id*, orderId*, authorizedEmployeeId*, outcome*, checkedAt*, note? | Simulated in-person professional verification; audit decision |

## Loyalty and messaging
| Entity / value object | Essential attributes | Responsibility / invariants |
|---|---|---|
| **LoyaltyTier** | id*, code*, description*, active* | Standard / social / premium eligibility configuration |
| **LoyaltyAccount** | id*, customerId*, tierId*, pointsBalance* | One active account per customer; points must agree with ledger |
| **LoyaltyEntry** | id*, accountId*, orderId?, deltaPoints*, type*, occurredAt*, uniqueEventKey* | Append-only accrual/reversal ledger; deduplication by event |
| **LoyaltyPolicy** | id*, tierId*, earnRate*, eligibleCategories?, activeFrom* | Rate and exclusions configurable |
| **Promotion** | id*, conditions*, discountRule*, validity*, enabled* | Discount eligibility, not a medical suitability rule |
| **Notification** | id*, customerId*, type*, payloadRef*, status*, createdAt* | Notification delivery record; avoid medical data in message payload |
| **NotificationPreference** | customerId*, channel*, category*, optedIn* | Per-customer consent/preference settings |
| **AvailabilityWatch** | id*, customerId*, productId*, branchId?, active* | Trigger when eligible stock becomes available |
| **Reminder** | id*, customerId*, schedule*, productId?, enabled* | User-configured scheduling, not inferred treatment advice |
| **AuditEvent** | id*, actorId*, action*, resourceType*, resourceId*, occurredAt* | Non-sensitive administrative audit trail |

## Value objects / enumerations (not necessarily database tables)
`Money`, `Address`, `Quantity`, `Email`, `Phone`, `OrderStatus`, `ReservationStatus`, `PaymentStatus`, `ShipmentStatus`, `DeliveryMethod`, `VerificationOutcome`, `ShippingEligibility`.

## Entity boundaries
- `StockBalance` should be modified through guarded inventory/reservation operations, never by unconstrained direct writes.
- `OrderItem` snapshots persist even if a product is later deactivated.
- `PrescriptionVerification` records are not proof of real e-health validation.
- A `Product` can exist with zero branch offerings.
- Technical deletion of referenced products/orders is normally prohibited; deactivate/archive instead.
