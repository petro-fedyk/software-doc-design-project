# MySQL database

This directory contains the schema migrations and database utilities. The storefront catalog uses commercial medicine names and public product-image references. The pharmacy branches are sourced from public АНЦ branch listings. Prices and stock are simulated educational values; the site does not represent live offers, real reservations, customer data, or valid prescriptions.

## Start and populate

From the repository root, configure `.env` from `.env.example`, then run:

```bash
docker compose up -d db
python3 -m venv .venv
.venv/bin/pip install mysql-connector-python
.venv/bin/python db/scripts/migrate.py
```

The storefront dataset is already installed in the existing `internet_pharmacy` database. To review the safe, repeatable update plan without changing data, run:

```bash
.venv/bin/python db/scripts/seed_storefront_branches.py
```

The script maps the existing 50 pharmacy IDs to source-attributed АНЦ branches and maintains 30 stocked products plus five unavailable products in the catalog. It preserves order/customer/payment/prescription rows and does not delete or truncate data. To intentionally refresh these storefront records after reviewing the dry-run output, use `.venv/bin/python db/scripts/seed_storefront_branches.py --apply`. The database connection uses the values in `.env`.

## Verify

```bash
.venv/bin/python db/scripts/verify_schema.py
.venv/bin/python db/scripts/test_mysql.py
```

The integration-test runner refuses to target the `internet_pharmacy` coursework database because these tests create fixture rows. Use a dedicated test schema. Test scripts do not delete fixture rows.

To inspect the catalogue and order counts in MySQL:

```sql
SELECT p.sku AS registration_number, p.name, m.name AS manufacturer
FROM products AS p
JOIN manufacturers AS m ON m.id = p.manufacturer_id
ORDER BY p.name;

SELECT 'products' AS table_name, COUNT(*) AS row_count FROM products
UNION ALL SELECT 'orders', COUNT(*) FROM orders
UNION ALL SELECT 'payments', COUNT(*) FROM payments;
```

Static reference tables remain limited by their approved domain rules (for example, `loyalty_tiers` permits exactly three tier codes). `schema_migrations` is a technical ledger, not business data. Product and branch images link to their public sources. Branch names and addresses identify real public ANC locations; branch-specific stock and price values are simulated and must not be represented as live pharmacy offers.
