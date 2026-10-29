#!/usr/bin/env python3
"""Load local .env and run real-MySQL integration tests."""
from __future__ import annotations
import sys
import unittest
from pathlib import Path
from migrate import ROOT, load_env_file

load_env_file(ROOT / '.env')
if __import__('os').environ.get('MYSQL_DATABASE', 'internet_pharmacy') == 'internet_pharmacy':
    print(
        'Refusing to run destructive integration tests against the coursework database. '
        'Set MYSQL_DATABASE to a dedicated test schema first; no rows were changed.',
        file=sys.stderr,
    )
    sys.exit(2)
suite = unittest.defaultTestLoader.discover(str(ROOT / 'db' / 'tests'), pattern='test_*.py')
result = unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(0 if result.wasSuccessful() else 1)
