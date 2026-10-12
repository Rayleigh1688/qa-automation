#!/usr/bin/env python3
"""Explicit FAT activity41 write lane; default dryrun makes no requests."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from filbet.loss_rebate_config import run_config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", default=".env.fat")
    parser.add_argument("--out", type=Path, default=ROOT / "reports/qa/ISOP-2090/20261012-full")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--fat-guard", default="")
    parser.add_argument("--marker", action="store_true", help="append a unique summary marker, read client sync, restore immediately")
    parser.add_argument("--marker-only", action="store_true", help="independent new baseline and summary marker only; no negative writes")
    parser.add_argument("--restore-from", type=Path, help="one cleanup-only attempt for a recorded failed/accepted negative; never replays tests")
    parser.add_argument("--insecure", action="store_true", help="use only for the known FAT certificate trust boundary")
    args = parser.parse_args()
    if sum(bool(value) for value in (args.marker, args.marker_only, args.restore_from)) > 1:
        parser.error("--marker, --marker-only and --restore-from are mutually exclusive")
    return run_config(args)


if __name__ == "__main__":
    raise SystemExit(main())
