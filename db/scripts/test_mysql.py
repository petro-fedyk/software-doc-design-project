#!/usr/bin/env python3
"""Load local .env and run real-MySQL integration tests."""
from __future__ import annotations
import sys
import unittest
from pathlib import Path
from migrate import ROOT, load_env_file

load_env_file(ROOT / '.env')
suite = unittest.defaultTestLoader.discover(str(ROOT / 'db' / 'tests'), pattern='test_*.py')
result = unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(0 if result.wasSuccessful() else 1)
