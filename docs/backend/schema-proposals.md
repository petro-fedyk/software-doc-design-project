# Schema review and explicit proposals

No Phase 2 migration was applied to the learning database. Existing migrations `0001_initial.sql` and `0002_neutral_payment_providers.sql` remain unchanged. The isolated test database uses those same migrations.

| Finding | Current behavior | Proposal requiring separate approval |
|---|---|---|
| `users.role` allows ADMIN/STAFF/CUSTOMER but stores no pharmacist qualification | Verification requires STAFF, active branch assignment and an explicit deployment allowlist; defaults deny all | Add a staff-qualification table with user FK, qualification type, validity dates, revocation status and approving actor |
| UML `OrderItem.discount_snapshot` and regulatory/storage snapshots are absent | The order stores the complete discount; line name/unit-price/quantity remain immutable; active-order product restriction changes are rejected | Add line discount, Rx-required and storage-policy snapshot columns; define a backfill before enabling per-line refunds or historical regulatory reconstruction |
| No persisted payment-method configuration | Enabled methods are constructor-injected from deployment configuration; GET exposes only enabled methods | Add a payment-method settings table if runtime administrative configuration must persist |
| Refunds have no idempotency key column | A deterministic unique outbox event ID deduplicates requests; retain those events | Optionally add a unique refund request key for independent retention and reconciliation |
| Stage 03 permits multiple shipments; SQL has `UNIQUE(deliveries.order_id)` | One delivery record per order | Remove uniqueness and define shipment-item allocation only if reshipment becomes approved scope |
| Stage 04 references Django Auth/Admin and SQLite | MySQL is used; Django password hashers plus JWT operate on the existing users table; administration is REST | Standard Django Admin/permissions/sessions would require explicit additional tables and an approved identity mapping |
| Domain reservation/payment lifecycle names differ from SQL enums | Released reservations persist as CANCELLED; an expired hold persists as EXPIRED; payment attempts use existing PENDING/SUCCEEDED/FAILED/UNKNOWN/REFUNDED values | No change required for current course workflows; keep independent lifecycles |

The obsolete SQLite/container guidance and Flask-shaped module example in earlier documents are treated as historical. The user's Phase 2 requirement and accepted MySQL schema take precedence; Stage 01–05 files were preserved.

Outbox processing is atomic for local simulated providers. External providers need stable idempotency and reconciliation for an outcome that succeeds remotely but fails before local commit. A real integration must not infer success from a browser request. None is implemented in this phase.
