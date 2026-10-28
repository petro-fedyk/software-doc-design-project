#!/usr/bin/env python3
"""Provision an isolated MySQL test database through the local Compose service."""

import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "db/scripts"))
from migrate import load_env_file

load_env_file(ROOT / ".env")
name = os.environ.get("MYSQL_DATABASE", "internet_pharmacy") + "_test"
user = os.environ.get("MYSQL_USER", "internet_pharmacy")
if not all(re.fullmatch(r"[a-zA-Z0-9_]+", x) for x in (name, user)):
    raise SystemExit(
        "Database and user names must contain letters, digits and underscores."
    )
query = f"CREATE DATABASE IF NOT EXISTS `{name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci; GRANT ALL PRIVILEGES ON `{name}`.* TO '{user}'@'%';"
subprocess.run(
    [
        "docker",
        "compose",
        "exec",
        "-T",
        "db",
        "sh",
        "-c",
        'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot',
    ],
    input=query,
    text=True,
    cwd=ROOT,
    check=True,
)
subprocess.run(
    [sys.executable, str(ROOT / "db/scripts/migrate.py")],
    env={**os.environ, "MYSQL_DATABASE": name},
    check=True,
)
print(f"Test database ready: {name}")
