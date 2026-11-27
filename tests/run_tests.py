#!/usr/bin/env python3
"""Run every test in tests/. Standard library and PyYAML only.

    python3 tests/run_tests.py          from the repository root, or anywhere

The tests that run Ansible need it on PATH or importable (the controller's
Ansible virtual environment) and are skipped without it. The tests that use
uc-controller's checkers need UC_CONTROLLER to name a uc-controller checkout,
and are skipped without it. Each test makes its own secrets root and client
inventory in a temporary directory, with values from the safe values
register, never reading the operator's ~/.secrets/ or ~/.private/.
Exit status 0 when every test passes.
"""
import sys
import unittest
from pathlib import Path

if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    suite = unittest.defaultTestLoader.discover(str(here), top_level_dir=str(here))
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
