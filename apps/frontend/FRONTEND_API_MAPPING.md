# Frontend API Mapping

All paths below are relative to `/api`. The running Django URL configuration is the source used to verify these paths. JSON fields are sent only for the listed operations; list reads may return arrays or DRF `{count,next,previous,results}` pages. API validation and authorization errors are displayed instead of treating them as success.

| Page / role | User action | Method and endpoint | Request data | Expected response / access |
|---|---|---|---|---|
| Public catalog / Guest, Customer, Staff, Admin | List and filter products | `GET /products/?search=&category=&manufacturer=&page=` | Optional query parameters | Paginated product page; public active items, Admin can see inactive items |
| Public catalog / any | Categories | `GET /categories/` | — | Category page/array |
| Public catalog / any | Manufacturers | `GET /manufacturers/` | — | Manufacturer page/array |
| Product detail / any | Read product | `GET /products/{id}/` | — | Product object including prescription/storage flags |
| Product detail / any | Branch availability and price | `GET /products/{id}/availability/` | — | Array of active listed branch, price, available quantity |
| Pharmacy list / any | Browse active branches | `GET /pharmacies/` | — | Pharmacy page/array |
| Pharmacy list / any | Listed branch inventory | `GET /pharmacies/{pharmacy_id}/inventory/` | — | Public inventory array; Staff/Admin receives full projection only for an authorized branch |
| Authentication / Guest | Register | `POST /auth/register/` | `username,email,full_name,password` (password 4+ chars) | `access,expires_in`; creates a Customer through the existing API |
| Authentication / Guest | Sign in | `POST /auth/token/` | `username,password` | `access,expires_in`; invalid credentials return 401 |
| Any signed-in role | Resolve identity/role | `GET /me/` | Bearer token | `id,username,email,role,pharmacy_ids,pharmacist` |
| Guest cart / Guest | Read/update cart | `GET /guest-cart/`; `PUT /guest-cart/` | `product_id,quantity` | API-backed guest cart; quantity zero removes the line |
| Customer cart / Customer | Read/update cart | `GET /cart/`; `PUT /cart/` | `product_id,quantity` | API-backed customer cart; quantity zero removes the line |
| Checkout / Customer | Get current quote | `POST /checkout/quote/` | `pharmacy_id,fulfillment_method,items[{product_id,quantity}]` | Server-calculated lines, subtotal, discount, shipping, total; availability conflicts can be 409 |
| Checkout / Customer | Place confirmed order | `POST /orders/` | Quote fields plus `payment_method,expected_total,items[{product_id,quantity,expected_unit_price}]`; recipient for delivery | Created order; price/stock and prescription checks are repeated by backend |
| Customer account | Read/edit profile | `GET /profile/`; `PATCH /profile/` | `full_name,phone,preferred_pharmacy_id` | Profile object; Customer only |
| Customer account | Preferences | `GET /preferences/`; `POST /preferences/` | `promotions_enabled,reminders_enabled` | Preference rows; Customer only |
| Customer account | Loyalty | `GET /loyalty/` | — | Loyalty account and transaction rows; Customer only |
| Customer account | Read notifications | `GET /notifications/` | — | Notification array; Customer only |
| Customer account | Mark notification read | `POST /notifications/{id}/read/` | Empty object | Updated row; Customer only |
| Customer account | Read/create availability watch | `GET /availability-watches/`; `POST /availability-watches/` | `product_id,pharmacy_id,is_active` | Watch rows; Customer only |
| Customer account | Read/create reminders | `GET /reminders/`; `POST /reminders/` | `product_id,interval_days,next_run_at,is_active` | Reminder rows; next run must be in the future; no delete endpoint exposed |
| Customer account | Saved prescription labels | `GET /prescriptions/`; `POST /prescriptions/`; `DELETE /prescriptions/{id}/` | Create: `display_label` | Masked/demo label rows; never uploads a medical document |
| Customer orders | Read own orders | `GET /orders/` | — | Order objects and line snapshots; Customer queryset is owner-filtered |
| Customer orders | Simulated payment request | `POST /orders/{id}/pay/` | `idempotency_key` | Queued payment request (202); inspect status through fulfillment endpoint |
| Staff / assigned pharmacy | Request simulated refund | `POST /orders/{id}/refund/` | `amount,reason,idempotency_key` | Queued refund request; pharmacy assignment and refundable balance checked by backend |
| Customer orders | Cancel | `POST /orders/{id}/transition/` | `{status:"CANCELLED"}` | Updated order or API state/permission error |
| Customer orders | Reorder | `POST /orders/{id}/reorder/` | Empty object | Copies order items to the API cart; availability is rechecked at checkout |
| Customer orders | Payment/delivery/refund details | `GET /orders/{id}/fulfillment/` | — | Payments, delivery and refunds; only accessible orders |
| Staff portal / assigned Staff | Full inventory and stock update | `GET /pharmacies/{id}/inventory/`; `PATCH /pharmacies/{id}/inventory/{product_id}/` | One of `adjustment`, `quantity`, `unit_price`, `is_listed` (backend validation applies) | Inventory projection / updated inventory; branch assignment enforced by backend |
| Staff portal / assigned Staff | Branch orders | `GET /orders/` | — | Orders only for assigned pharmacies |
| Staff portal / assigned Staff | Allowed order status change | `POST /orders/{id}/transition/` | `status` from supported state choices | Updated order; backend checks transition, branch, payment, and prescription rules |
| Staff portal / pharmacist-qualified Staff | Verify prescription | `POST /orders/{id}/verify-prescription/` | `approved:boolean` | Simulated approval/rejection; requires pharmacy assignment and pharmacist qualification |
| Staff portal / assigned Staff | Request shipment | `POST /orders/{id}/ship/` | No body | Queued simulated shipment (202) |
| Staff portal | Branch statistics/audit | `GET /pharmacies/{id}/statistics/`; `GET /pharmacies/{id}/audit/` | — | Branch-limited statistics/audit rows |
| Admin portal / Admin | Network statistics/audit | `GET /admin/statistics/`; `GET /admin/audit/` | — | Aggregate totals/statuses and audit rows |
| Admin portal / Admin | CRUD operations (create/read/update) | `GET,POST,PATCH /pharmacies/`, `/products/`, `/categories/`, `/manufacturers/` | Resource serializer fields; no delete method exists | API response; Admin required for writes |
| Admin portal / Admin | User management | `GET,POST,PATCH /admin/users/` | `username,email,role,is_active`; create also requires password (4+ chars) | User rows; backend hashes passwords; no user delete operation |
| Admin portal / Admin | Staff assignments | `GET,POST,PATCH /admin/assignments/` | `user,pharmacy,is_active` | Assignment rows; assigned user must be active Staff |
| Admin portal / Admin | Promotions/products | `GET,POST,PATCH /admin/promotions/`; `GET,POST,PATCH /admin/promotion-products/` | Promotion serializer fields; link uses `promotion,product` | Promotion/link rows; write is Admin-only |
| Admin portal / Admin | Loyalty tiers | `GET,POST,PATCH /admin/loyalty-tiers/` | `code,bonus_rate,discount_rate` | Standard/Social/Premium tier rows; backend validates rates and tier codes |
| Admin portal / Admin | Delivery rules | `GET,POST,PATCH /admin/delivery-rules/` | `method,requires_cold_chain,cold_chain_supported,enabled,max_storage_min_c,min_storage_max_c` | Rule rows; backend validates method/ranges |
| API/verification | Payment options | `GET /payment-methods/` | — | Enabled method names and `simulated` flag |
| API health | Check DB connectivity | `GET /health/` | — | `status,database`; read-only health response |

## Deliberately unavailable capabilities

- General-purpose DELETE does not exist for the admin viewsets; the UI does not offer delete buttons.
- The API does not expose public promotions, customer cart merge, or employee qualification in assignment rows.
- API order objects omit a prescription-needed flag; a qualified pharmacist may see verification controls, while the backend decides whether a given order is verifiable.
- `/api/payment-methods/` lists only simulated method keys; it does not accept card credentials.
