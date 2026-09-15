#!/usr/bin/env python3
"""Compatibility-friendly unified requirement workflow CLI."""
from qa_workflow.cli import entrypoint

if __name__ == '__main__':
    raise SystemExit(entrypoint())
