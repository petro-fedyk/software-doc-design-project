# MySQL learning database

This directory contains the MySQL schema migrations, repeatable seed script, and integration checks. The product catalogue uses registered Ukrainian medicine names and registration numbers from the [State Register of Medicinal Products](https://drlz.moz.gov.ua/register/products/). Product packaging details, stock, prices, pharmacies, people, and transactions are synthetic learning data; no real customer data or valid prescriptions are included.

## Start and populate

From the repository root, configure `.env` from `.env.example`, then run:

```bash
docker compose up -d db
python3 -m venv .venv
.venv/bin/pip install mysql-connector-python
.venv/bin/python db/scripts/migrate.py
.venv/bin/python db/scripts/seed_learning_data.py
```

The seed script deletes and replaces business-table records in the configured database. Run it only against the learning database. The database connection uses the values in `.env`.

## Verify

```bash
.venv/bin/python db/scripts/verify_schema.py
.venv/bin/python db/scripts/test_mysql.py
```

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

Most business tables contain 25 rows. Exceptions follow the schema and data meaning: `loyalty_tiers` has its three allowed tiers; `users` has 25 customer and 25 staff accounts; `prescription_verifications` has one record because the seed marks only one catalogue item as prescription-required. Prescription references are synthetic and explicitly marked as such.
