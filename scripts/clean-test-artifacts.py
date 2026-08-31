#!/usr/bin/env python3
"""Clean generated test artifacts while keeping result directories present."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


TARGETS = {
    "api": [Path("api/results")],
    "ui": [Path("ui/results"), Path("ui/reports"), Path("playwright-report"), Path("test-results")],
}

PRESERVE = {
    Path("api/results"): {"p0-api-session.json"},
    Path("ui/results"): {"client-p0-storage-state.json"},
}


def clean_dir(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for child in root.iterdir():
        if child.name == ".gitkeep" or child.name in PRESERVE.get(root, set()):
            continue
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink()
    (root / ".gitkeep").touch()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("scope", choices=["api", "ui", "all"], help="artifact group to clean")
    args = parser.parse_args()

    scopes = ["api", "ui"] if args.scope == "all" else [args.scope]
    for scope in scopes:
        for root in TARGETS[scope]:
            clean_dir(root)
            print(f"cleaned {root}")


if __name__ == "__main__":
    main()
