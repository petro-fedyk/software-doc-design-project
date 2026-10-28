#!/usr/bin/env python3
"""Apply immutable numbered MySQL SQL migrations."""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from pathlib import Path

import mysql.connector
from mysql.connector import Error

ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / 'db' / 'migrations'


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key.strip(), value)


def connect(*, database: bool = True):
    cfg = {
        'host': os.environ.get('MYSQL_HOST', '127.0.0.1'),
        'port': int(os.environ.get('MYSQL_PORT', '3306')),
        'user': os.environ.get('MYSQL_USER', 'internet_pharmacy'),
        'password': os.environ.get('MYSQL_PASSWORD', ''),
        'connection_timeout': 10,
        'autocommit': True,
    }
    if database:
        cfg['database'] = os.environ.get('MYSQL_DATABASE', 'internet_pharmacy')
    conn = mysql.connector.connect(**cfg)
    cursor = conn.cursor()
    cursor.execute("SET time_zone = '+00:00'")
    cursor.close()
    return conn


def statements(sql: str) -> list[str]:
    # These project migrations intentionally use plain DDL/DML statements, no stored routines.
    cleaned = re.sub(r'^\s*--.*$', '', sql, flags=re.MULTILINE)
    return [part.strip() for part in cleaned.split(';') if part.strip()]


def apply_migrations(conn) -> None:
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS schema_migrations (
      version VARCHAR(120) NOT NULL PRIMARY KEY,
      checksum CHAR(64) NOT NULL,
      applied_at DATETIME(6) NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci""")
    cursor.execute("SELECT GET_LOCK('internet_pharmacy_schema_migrations', 30)")
    if cursor.fetchone()[0] != 1:
        raise RuntimeError('Could not acquire schema migration advisory lock')
    try:
        for path in sorted(MIGRATIONS.glob('[0-9][0-9][0-9][0-9]_*.sql')):
            content = path.read_bytes()
            digest = hashlib.sha256(content).hexdigest()
            cursor.execute('SELECT checksum FROM schema_migrations WHERE version=%s', (path.name,))
            row = cursor.fetchone()
            if row:
                if row[0] != digest:
                    raise RuntimeError(f'Applied migration {path.name} was modified; add a new migration instead')
                print(f'SKIP {path.name} (already applied)')
                continue
            print(f'APPLY {path.name}')
            for sql in statements(content.decode('utf-8')):
                cursor.execute(sql)
            cursor.execute('INSERT INTO schema_migrations(version, checksum, applied_at) VALUES (%s,%s,UTC_TIMESTAMP(6))', (path.name, digest))
    finally:
        cursor.execute("SELECT RELEASE_LOCK('internet_pharmacy_schema_migrations')")
        cursor.fetchone()
        cursor.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', type=Path, default=ROOT / '.env')
    args = parser.parse_args()
    load_env_file(args.env_file)
    try:
        conn = connect()
        try:
            apply_migrations(conn)
            print('Migration check complete.')
        finally:
            conn.close()
    except (Error, RuntimeError, OSError) as exc:
        print(f'Database migration failed: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
