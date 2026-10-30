# Two portals, one modular monolith

The customer portal (`apps/customer-web`, port 4173) and management portal (`apps/management-web`, port 4174) have separate HTML entry points, application modules, routes, CSS and processes. The existing Django REST API on port 8000 and persistent MySQL database `internet_pharmacy` remain shared. The outbox worker runs the same backend code. Domain services, repositories, Unit of Work and the five GoF patterns remain unchanged.

Small browser utilities and the development static/proxy server live in `apps/web-shared`. Sharing HTTP, authentication, localization and HTML formatting code does not mount one portal's pages in the other. `apps/frontend/server.mjs` is a compatibility launcher for the customer portal; its former documents are historical.

Each browser sends same-origin `/api/*` requests to its portal. The portal proxy forwards them to the same `API_ORIGIN`, default `http://127.0.0.1:8000`. No browser cross-origin API requests are used, so broad Django CORS settings are unnecessary. Both `localhost` and `127.0.0.1` work, but they are separate browser origins; use one hostname consistently. The servers bind loopback unless explicitly configured for a Compose container.

## Sessions and server authorization

JWTs are held in memory and tab-scoped sessionStorage with separate `pharmacy.customer.session` and `pharmacy.management.session` keys. Reload restores the token then validates `/api/me/`; expiry/401 and logout clear that portal's stored session. Cookies are not isolated by port; the existing guest-cart cookie belongs only to the customer workflow. Neither portal stores passwords.

Both portals reuse Django's `/api/auth/token/`. Before returning a successful login response to the browser, the portal server obtains the authenticated identity from Django `/api/me/` and requires CUSTOMER for the customer portal or STAFF/ADMIN for management. Wrong-role login receives HTTP 403 without a token. Management proxy registration is also refused. Client role checks are additional navigation behavior. Calling the API directly does not bypass Django's role, ownership, pharmacy-assignment and pharmacist checks on each protected operation.

## Initial administrator

`python manage.py bootstrap_admin` creates username `admin`, password `admin`, role ADMIN, only if **no ADMIN row exists**, including inactive rows. It hashes the password using Django; no plaintext is stored in MySQL. New coursework accounts require a password of at least 4 characters. Compose runs bootstrap before Gunicorn. Existing administrator passwords and roles are never reset by bootstrap. Run `python manage.py set_coursework_admin_password` to explicitly set the password on the existing `admin` ADMIN account. A non-admin username/email collision fails clearly without replacing the record. MySQL's named advisory lock serializes concurrent startup attempts without schema changes. This local educational default should be replaced by private provisioning for a production deployment.

## Requirements and boundaries

- FR-PORTAL-01: guests/customers can browse and complete all supported customer operations in the customer portal.
- FR-PORTAL-02: staff and admins have a distinct login and management navigation, with no public registration or buyer checkout.
- FR-PORTAL-03: inventory and order changes in management are visible in customer reads from the same database.
- FR-PORTAL-04: network administrators can create staff and active pharmacy assignments using existing admin APIs.
- FR-BOOTSTRAP-01: first local administrator is available without manually inventing credentials; repeated startup preserves existing accounts.
- NFR-PORTAL-01: either frontend can stop independently; Django/MySQL are their only shared runtime data dependencies.
- NFR-PORTAL-02: direct routes, refresh, logout, expiry, mobile layouts and failed API requests have defined states.
- NFR-PORTAL-03: authorization is enforced by Django; different ports and hidden links are not authorization.
- NFR-PORTAL-04: one persistent database; no clones, resets, schema changes, new authentication server or frontend framework.

Production VPN/private-network access, TLS and origin restrictions are future deployment options. They are not implemented in this coursework.

See [page/API matrix](PAGE_API_MATRIX.md), [demonstration guide](DEMONSTRATION.md), and [verification](../verification/portal-split/REPORT.md).
