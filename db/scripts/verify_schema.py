#!/usr/bin/env python3
"""Compare the live MySQL catalog to canonical migration tables/columns/keys."""
from __future__ import annotations

import re
from pathlib import Path

from generate_erd import parse_schema
from migrate import connect, load_env_file, ROOT

EXPECTED_DOMAIN_TABLES = {
    'users','employee_assignments','customer_profiles','pharmacies','categories','manufacturers','products',
    'pharmacy_inventory','inventory_movements','carts','cart_items','orders','order_items','reservations',
    'payments','refunds','deliveries','delivery_rules','prescription_records','prescription_verifications',
    'loyalty_tiers','loyalty_accounts','loyalty_transactions','promotions','promotion_products','notifications',
    'availability_subscriptions','reminders','notification_preferences','outbox_events','audit_entries',
}


def main() -> int:
    load_env_file(ROOT / '.env')
    migration_text = '\n'.join(p.read_text() for p in sorted((ROOT/'db/migrations').glob('[0-9][0-9][0-9][0-9]_*.sql')))
    expected_tables = parse_schema()
    expected_fk = set(re.findall(r'CONSTRAINT (\w+) FOREIGN KEY', migration_text))
    expected_checks = set(re.findall(r'CONSTRAINT (\w+) CHECK', migration_text))
    expected_indexes = {'PRIMARY'} | set(re.findall(r'(?:UNIQUE )?KEY (\w+) \(', migration_text))
    conn = connect()
    try:
        cur = conn.cursor()
        cur.execute('SELECT VERSION(), @@default_storage_engine, @@character_set_server, @@collation_server, @@global.time_zone, @@session.time_zone, @@system_time_zone')
        version, engine, charset, collation, global_zone, session_zone, system_zone = cur.fetchone()
        cur.execute("SELECT table_name, engine, table_collation FROM information_schema.tables WHERE table_schema=DATABASE() AND table_type='BASE TABLE'")
        actual_tables = {name: (eng, coll) for name, eng, coll in cur.fetchall()}
        domain_actual = set(actual_tables) - {'schema_migrations'}
        missing, unexpected = EXPECTED_DOMAIN_TABLES-domain_actual, domain_actual-EXPECTED_DOMAIN_TABLES
        bad_tables = {name: vals for name, vals in actual_tables.items() if vals[0] != 'InnoDB' or not vals[1].startswith('utf8mb4')}
        cur.execute("SELECT table_name, column_name FROM information_schema.columns WHERE table_schema=DATABASE()")
        actual_columns: dict[str,set[str]] = {}
        for table,column in cur.fetchall(): actual_columns.setdefault(table,set()).add(column)
        expected_columns={name:{c[0] for c in data['columns']} for name,data in expected_tables.items()}
        column_diffs={name:{'missing':sorted(cols-actual_columns.get(name,set())), 'extra':sorted(actual_columns.get(name,set())-cols)} for name,cols in expected_columns.items() if cols!=actual_columns.get(name,set())}
        cur.execute("SELECT constraint_name FROM information_schema.table_constraints WHERE table_schema=DATABASE() AND constraint_type='FOREIGN KEY'")
        actual_fk={row[0] for row in cur.fetchall()}
        cur.execute("SELECT constraint_name FROM information_schema.table_constraints WHERE table_schema=DATABASE() AND constraint_type='CHECK'")
        actual_checks={row[0] for row in cur.fetchall()}
        cur.execute("SELECT DISTINCT index_name FROM information_schema.statistics WHERE table_schema=DATABASE()")
        actual_indexes={row[0] for row in cur.fetchall()}
        cur.execute('SELECT version, checksum FROM schema_migrations ORDER BY version')
        migrations=cur.fetchall()
        print(f'MySQL: {version}; engine: {engine}; charset/collation: {charset}/{collation}; time_zone(global/session)={global_zone}/{session_zone} (system {system_zone})')
        print(f'Domain tables: {len(domain_actual)}/{len(EXPECTED_DOMAIN_TABLES)}; migration ledger: {"present" if "schema_migrations" in actual_tables else "missing"}')
        print(f'Columns: {sum(map(len,actual_columns.values()))}; FKs: {len(actual_fk)} (expected {len(expected_fk)}); CHECKs: {len(actual_checks)} (expected {len(expected_checks)}); indexes: {len(actual_indexes)}; migrations: {len(migrations)}')
        if missing: print('Missing tables:', ', '.join(sorted(missing)))
        if unexpected: print('Unexpected domain tables:', ', '.join(sorted(unexpected)))
        if bad_tables: print('Non-InnoDB/non-utf8mb4 tables:', bad_tables)
        if column_diffs: print('Column differences:', column_diffs)
        if expected_fk-actual_fk: print('Missing foreign keys:', sorted(expected_fk-actual_fk))
        if expected_checks-actual_checks: print('Missing CHECK constraints:', sorted(expected_checks-actual_checks))
        if expected_indexes-actual_indexes: print('Missing indexes:', sorted(expected_indexes-actual_indexes))
        passed=(version.startswith('8.') and global_zone in ('+00:00','UTC') and session_zone in ('+00:00','UTC') and not missing and not unexpected and not bad_tables and not column_diffs and expected_fk<=actual_fk and expected_checks<=actual_checks and expected_indexes<=actual_indexes and 'schema_migrations' in actual_tables and bool(migrations))
        print('SCHEMA VERIFICATION: '+('PASS' if passed else 'FAIL'))
        return 0 if passed else 1
    finally:
        conn.close()

if __name__ == '__main__':
    raise SystemExit(main())
