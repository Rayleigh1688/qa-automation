#!/usr/bin/env python3
"""Run all offline unit tests with repository paths on Windows, macOS and Linux."""
from pathlib import Path
import os
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


def main():
    os.chdir(ROOT)
    suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests/unit'), pattern='test_*.py')
    return 0 if unittest.TextTestRunner(verbosity=1).run(suite).wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())
