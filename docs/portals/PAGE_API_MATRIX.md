# Page → Portal → Role → REST operations

Audit of the existing Vanilla JS app and API, 2026-10-29. Existing customer and management renderers were moved rather than rebuilt. Paths below are relative to `/api`; `{id}` denotes the selected record. Shared authentication does not imply shared browser sessions.

| Page / operation | Portal / role | Existing endpoints |
|---|---|---|
| Home, catalog, search, category, manufacturer, branch selection | Customer / guest, CUSTOMER | GET products/, categories/, manufacturers/, pharmacies/; supported filters and page query |
| Product details and branch availability | Customer / guest, CUSTOMER | GET products/{id}/, products/{id}/availability/, pharmacies/{id}/inventory/ |
| Pharmacy directory/detail | Customer / guest, CUSTOMER | GET pharmacies/, pharmacies/{id}/, pharmacies/{id}/inventory/ |
| Register | Customer / guest | POST auth/register/ |
| Login and session restoration | Both / respective allowed roles | POST auth/token/, GET me/ |
| Guest cart, update/remove, transfer on customer sign-in | Customer / guest | GET/PUT guest-cart/; customer GET/PUT cart/ after login |
| Customer cart / update / remove | Customer / CUSTOMER | GET/PUT cart/ |
| Quote review / explicit order creation / recipient | Customer / CUSTOMER | GET payment-methods/; POST checkout/quote/, orders/ |
| Order history, detail, cancellation | Customer / owner | GET orders/, orders/{id}/; POST orders/{id}/transition/ |
| Simulated payment, fulfillment, reorder | Customer / owner | POST orders/{id}/pay/, orders/{id}/reorder/; GET orders/{id}/fulfillment/ |
| Profile and preferences | Customer / CUSTOMER | GET/PATCH profile/; GET/POST preferences/ |
| Loyalty / select tier / notifications / mark read | Customer / CUSTOMER | GET loyalty/; POST loyalty/ (`STANDARD`, `SOCIAL` with six digit document number, or simulated `PREMIUM` subscription for 30 UAH per 30 days); GET notifications/; POST notifications/{id}/read/ |
| Saved prescription labels | Customer / CUSTOMER | GET/POST prescriptions/; DELETE prescriptions/{id}/ |
| Availability watches / toggle | Customer / CUSTOMER | GET/POST availability-watches/ |
| Reminders | Customer / CUSTOMER | GET/POST reminders/ |
| Branch workspace / inventory / local price / listing / add product to assortment | Management / assigned STAFF or ADMIN | GET pharmacies/, pharmacies/{id}/inventory/, products/; PATCH pharmacies/{id}/inventory/{product_id}/ (send unit_price and quantity to add a new product) |
| Branch orders / transitions / shipment / refund | Management / assigned STAFF or ADMIN | GET orders/; POST orders/{id}/transition/, orders/{id}/ship/, orders/{id}/refund/ |
| Prescription approve/reject | Management / assigned STAFF with pharmacist qualification | POST orders/{id}/verify-prescription/ |
| Branch statistics and audit | Management / assigned STAFF or ADMIN | GET pharmacies/{id}/statistics/, pharmacies/{id}/audit/ |
| Network statistics and audit | Management / ADMIN | GET admin/statistics/, admin/audit/ |
| Users / create staff / edit role and activation | Management / ADMIN | GET/POST admin/users/; GET/PATCH admin/users/{id}/ |
| Staff assignments | Management / ADMIN | GET/POST admin/assignments/; GET/PATCH admin/assignments/{id}/ |
| Pharmacy and catalog maintenance | Management / ADMIN writes | GET/POST pharmacies/, products/, categories/, manufacturers/; GET/PATCH corresponding {id}/ |
| Promotions / promotion products / loyalty tiers / delivery rules | Management / ADMIN | GET/POST admin/promotions/, admin/promotion-products/, admin/loyalty-tiers/, admin/delivery-rules/; GET/PATCH corresponding {id}/ |
| Logout, mobile menu, 404, loading, API errors | Each portal | Local session deletion/navigation; API errors remain authoritative |

Customer routes: `#home`, `#catalog`, `#product:{id}`, `#pharmacies`, `#pharmacy:{id}`, `#login`, `#register`, `#cart`, `#account`, `#orders`. `#staff` and `#admin` are 404.

Management routes: `#login`, `#staff?pharmacy={id}`, `#admin`. No registration, catalog or checkout pages. Staff receive a denial page for direct `#admin` navigation. Admin may open the branch workspace; pharmacist actions remain restricted independently.
