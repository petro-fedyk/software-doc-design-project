# Internet Pharmacy — Goodwell

An Internet Pharmacy coursework project with a customer website, a separate staff/administrator portal, a Django REST API, and a persistent MySQL database.

**GitHub repository:** https://github.com/petro-fedyk/software-doc-design-project

This README explains how to deploy the project from a fresh checkout, start an existing installation, and inspect it during a demonstration. Commands below target Linux/Ubuntu and run from the repository root unless stated otherwise.

## 1. Components

| Component | Implementation | Local address |
| --- | --- | --- |
| Customer website | HTML, CSS, JavaScript; Node.js server | http://localhost:4173/#home |
| Staff and administrator portal | HTML, CSS, JavaScript; Node.js server | http://localhost:4174/#login |
| Backend | Django REST Framework, JWT authentication | http://localhost:8000/api/ |
| Swagger UI | Interactive API documentation | http://localhost:8000/api/docs/ |
| OpenAPI schema | Generated API contract | http://localhost:8000/api/schema/ |
| Database | MySQL 8.0.42, InnoDB | `127.0.0.1:3308` |
| Background worker | Transactional outbox processing | No web port |

The customer interface provides a catalog, pharmacy availability, a cart grouped by pharmacy, checkout, order history, and loyalty information. Staff work with assigned pharmacies; administrators manage the network. Payments and shipment providers are simulated. The management portal is a custom interface, not Django Admin.

SQL files in `db/migrations/` are the schema authority. Django maps the existing tables; do not run Django `migrate`, `makemigrations`, or `flush`.

## 2. Prerequisites

Install:

- Git.
- Docker Engine or Docker Desktop with Docker Compose v2.
- Python 3.12 with `venv` and pip for the SQL migration tools.
- Node.js 22 only if running the portals outside Docker.
- Optional: MySQL Workbench or the MySQL command-line client.

Check the installed tools:

```bash
git --version
docker --version
docker compose version
python3 --version
```

Docker must be running and accessible to your user. If it requires administrator permissions, prefix the Docker commands below with `sudo`. Use the same Docker context throughout: different contexts can point to different databases and volumes.

```bash
docker context show
docker ps
```

## 3. Clone and configure

```bash
git clone https://github.com/petro-fedyk/software-doc-design-project.git
cd software-doc-design-project
# Preserve an existing local configuration:
[ -f .env ] || cp .env.example .env
```

Edit `.env` before starting the database:

| Variable | Configuration |
| --- | --- |
| `MYSQL_ROOT_PASSWORD` | Set a private local MySQL root password |
| `MYSQL_DATABASE` | Keep `internet_pharmacy` |
| `MYSQL_USER` | Keep `internet_pharmacy` |
| `MYSQL_PASSWORD` | Set a private application database password |
| `MYSQL_HOST` | Keep `127.0.0.1` for host-side migration commands |
| `MYSQL_PORT` | Default `3308`; choose an unused host port if needed |
| `DJANGO_SECRET_KEY` | Replace the placeholder with a random secret of at least 32 characters |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` for local use |
| `DJANGO_DEBUG` | Keep `0` |
| `PHARMACIST_IDS` | Comma-separated IDs of staff authorized for simulated prescription verification; empty denies verification |
| `ENABLED_PAYMENT_METHODS` | Keep the supplied supported payment methods unless intentionally restricting checkout |

Generate the Django secret locally and paste the result into `.env`:

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
```

Do not commit `.env` or credentials. Compose overrides the database host/port inside backend containers to `db:3306`; the host tools and Workbench use port `3308`.

## 4. First deployment: database and schema

Start MySQL first:

```bash
docker compose up -d db
docker compose ps
docker compose logs --tail=50 db
```

Wait until `db` is **healthy**. Then install the host-side migration dependency:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install mysql-connector-python
```

Review the versioned SQL files in `db/migrations/`, then explicitly apply them:

```bash
.venv/bin/python db/scripts/migrate.py
.venv/bin/python db/scripts/verify_schema.py
```

The runner records migration checksums in `schema_migrations`, skips previously applied unchanged files, and rejects changes to applied migrations. Backend startup does not apply SQL migrations. On an existing installation, review pending migrations before running the command; do not recreate the database.

### Database contents on a fresh checkout

GitHub contains source code and schema migrations, **not the contents of the author's local Docker volume**. A new installation does not automatically contain the existing products, customers, or purchase history shown in screenshots.

After signing in as administrator, create the catalog and pharmacy records, then inventory and staff assignments through the management portal. Existing installations retain their records in the persistent volume. The historical `seed_learning_data.py` and `seed_coursework_data.py` entry points are disabled; do not use them as startup commands. `seed_storefront_branches.py` is a maintenance tool for an existing dataset, not a general empty-database bootstrap.

## 5. Start the complete application

After applying the schema, run all five services:

```bash
docker compose -f compose.yaml -f compose.backend.yaml -f compose.portals.yaml up --build -d
docker compose -f compose.yaml -f compose.backend.yaml -f compose.portals.yaml ps
```

Expected services: `db`, `backend`, `worker`, `customer-web`, and `management-web`. MySQL and backend have health checks; the worker and portals should be running.

Open:

- [Customer website](http://localhost:4173/#home)
- [Staff/administrator login](http://localhost:4174/#login)
- [Swagger UI](http://localhost:8000/api/docs/)

Use `localhost` consistently in the browser; switching to `127.0.0.1` uses a different browser origin and separate login/cart storage.

### Alternative: run portals directly with Node.js

Start only the database, backend, and worker in Docker:

```bash
docker compose -f compose.yaml -f compose.backend.yaml up --build -d
node apps/start-portals.mjs
```

Keep the Node terminal open. `Ctrl+C` stops both portals. No npm installation or frontend build is required. The default API origin is `http://127.0.0.1:8000`.

Do not run Docker portals and host Node portals simultaneously on the same ports. To switch from Docker portals:

```bash
docker compose -f compose.yaml -f compose.backend.yaml -f compose.portals.yaml stop customer-web management-web
node apps/start-portals.mjs
```

## 6. Accounts and first use

On a fresh database, backend startup creates **username `admin`, password `admin`** only if no ADMIN account exists. These are local coursework credentials. Existing administrator accounts and passwords are not reset. This deployment binds ports to loopback and is intended for a local demonstration, not public production hosting.

1. Sign in at port **4174** as administrator.
2. Create the required categories, manufacturers, pharmacies, and products; configure inventory and delivery rules through the available management sections.
3. Create a user with role **STAFF** and add an active pharmacy assignment. A staff role alone does not grant access to every pharmacy.
4. Register a customer through the website at port **4173**.
5. Add an available product to the cart, choose a pharmacy and fulfillment/payment method, and confirm the order.
6. Process the order using the assigned staff account. For pickup, follow `PROCESSING → READY_FOR_PICKUP → COMPLETED`.
7. Refresh the customer's order history to see the result.

Prescription verification additionally requires the staff ID in `PHARMACIST_IDS`. Recreate backend and worker after changing this configuration. JWT sessions expire; sign in again when requested. Username prefixes do not grant permissions.

The worker must remain running for queued payment, notification, and loyalty processing. Loyalty awards integer points according to the customer's tier and eligible products; small purchases can round down to zero.

## 7. Verify the running installation

These commands inspect the running services without creating orders or changing business records:

```bash
docker compose -f compose.yaml -f compose.backend.yaml -f compose.portals.yaml ps
curl --fail http://localhost:8000/api/health/
curl --fail http://localhost:8000/api/products/
curl --fail -I http://localhost:4173/
curl --fail -I http://localhost:4174/
.venv/bin/python db/scripts/verify_schema.py
docker compose -f compose.yaml -f compose.backend.yaml logs --tail=100 backend worker
```

In Swagger, inspect public endpoints first. Protected endpoints require a JWT obtained through `/api/auth/token/` and entered using **Authorize**. Executing write endpoints changes the real database. Do not run database-mutating automated tests against the demonstration database.

### Inspect MySQL using commands

Open the MySQL client inside the existing container; enter `MYSQL_PASSWORD` from `.env` at the password prompt:

```bash
docker compose exec db mysql -u internet_pharmacy -p internet_pharmacy
```

Run read-only SQL:

```sql
SHOW DATABASES;
USE internet_pharmacy;
SHOW TABLES;
SELECT version, applied_at FROM schema_migrations ORDER BY version;
SELECT id, sku, name, prescription_required FROM products LIMIT 20;
SELECT id, name, address, city FROM pharmacies LIMIT 20;
SELECT p.name AS product, ph.name AS pharmacy, i.unit_price,
       i.on_hand, i.reserved, i.on_hand - i.reserved AS available
FROM pharmacy_inventory i
JOIN products p ON p.id = i.product_id
JOIN pharmacies ph ON ph.id = i.pharmacy_id
LIMIT 20;
SELECT status, COUNT(*) AS events FROM outbox_events GROUP BY status;
```

### Inspect MySQL in Workbench

Create a connection with connection method **Standard TCP/IP**:

- Hostname: `127.0.0.1`
- Port: `3308` (or your `MYSQL_PORT`)
- Username: `internet_pharmacy`
- Password: the `MYSQL_PASSWORD` value in `.env`
- Default schema: `internet_pharmacy`

Click **Test Connection**, open the connection, refresh **Schemas**, expand `internet_pharmacy → Tables`, and use **Select Rows – Limit 1000** on a table. The SQL above can also be run in a query tab.

## 8. Everyday startup, updates, and shutdown

### Start an already configured installation

```bash
docker compose -f compose.yaml -f compose.backend.yaml -f compose.portals.yaml up -d
```

### Apply source updates

Review changes and any new SQL migrations first. Apply approved migrations explicitly using the command in section 4. Then rebuild backend and worker and start the portals:

```bash
docker compose -f compose.yaml -f compose.backend.yaml -f compose.portals.yaml up --build -d
```

Portal files are mounted from the checkout. Reload the browser with **Ctrl+Shift+R** after frontend changes. After changing a portal server module, restart the portal processes:

```bash
docker compose -f compose.yaml -f compose.backend.yaml -f compose.portals.yaml restart customer-web management-web
```

### Stop without losing data

```bash
docker compose -f compose.yaml -f compose.backend.yaml -f compose.portals.yaml stop
```

MySQL data remains in the named volume `internet_pharmacy_mysql_data`. Do not use `down -v`, remove that volume, or run cleanup/reset scripts on the demonstration database.

## 9. Troubleshooting

| Symptom | What to inspect or do |
| --- | --- |
| Docker socket `permission denied` | Use an account allowed to access Docker or run the same command with `sudo`. |
| `sudo docker compose` is unknown | Check that Compose v2 is installed for the Docker CLI used by sudo; a user-only plugin may not be visible to root. |
| Port already in use | Check `docker ps` and `ss -ltnp`; stop the duplicate project process. Change `MYSQL_PORT` for a database port conflict and use that port in Workbench. |
| Database access denied | Check `.env` against the credentials used when the volume was initialized. Editing `.env` does not change passwords in an existing MySQL volume. |
| Missing tables / backend startup fails | Wait for healthy MySQL and run the reviewed SQL migrations before starting backend. |
| Empty catalog after cloning | A Git clone does not copy database records. Populate the catalog and inventory through the administrator portal. |
| Portal reports API unavailable | Check backend health and logs; keep backend on port 8000 or configure the portal's `API_ORIGIN`. |
| Login returns 403 | Customers use port 4173; STAFF and ADMIN use port 4174. Check account role and active status. |
| Staff sees no pharmacies | Add an active assignment to an active pharmacy. |
| Payment/notifications remain pending | Check `worker` status and logs; inspect outbox event statuses. |
| Old interface or loading error | Reload with Ctrl+Shift+R; inspect browser console and restart the portal after server changes. |

## 10. Repository guide and design documentation

| Path | Purpose |
| --- | --- |
| `apps/backend/` | Domain, application services, ORM adapters, REST API, outbox worker |
| `apps/customer-web/` | Customer portal |
| `apps/management-web/` | Staff and administrator portal |
| `apps/web-shared/` | Shared frontend utilities and HTTP server |
| `db/migrations/` | Versioned SQL schema |
| `db/scripts/` | Migration and database inspection tools |
| `docs/diagrams/` | Editable diagrams |
| `docs/verification/` | Recorded verification reports |

- [Domain analysis — Stage 03](docs/domain/README-stage-03.md)
- [Architecture — Stage 04](docs/architecture/01-overview.md)
- [Class design — Stage 05](docs/class-design/README.md)
- [Editable UML class diagrams](docs/diagrams/Internet_Pharmacy_Class_Diagrams.drawio)
- [Database documentation](db/README.md)
- [Backend architecture and API guide](docs/backend/README.md)
- [Portal architecture](docs/portals/ARCHITECTURE.md)
- [Page → portal → role → API mapping](docs/portals/PAGE_API_MATRIX.md)
- [Detailed demonstration scenario](docs/portals/DEMONSTRATION.md)

Open `.drawio` files in diagrams.net to inspect and edit their pages. Historical verification reports describe their recorded runs; they are not evidence that every later revision has been retested.
