#!/usr/bin/env python3
"""Compatibility CLI for the manual Telegram QA workflow."""
from qa_delivery.cli import main, entrypoint

if __name__ == "__main__":
    raise SystemExit(entrypoint())
