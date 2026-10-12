#!/usr/bin/env python3
"""Thin CLI for authorised FAT client detail/recommendation observation."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from filbet.loss_rebate_client import analyse_recorded, run_client_readonly

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", default=".env.fat")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--insecure", action="store_true")
    parser.add_argument("--admin-snapshot", type=Path, required=True)
    parser.add_argument("--recorded", type=Path, help="analyse an existing two-GET batch offline")
    parser.add_argument("--selection-context", type=Path, help="optional saved public first-group DB summary; offline only")
    parser.add_argument("--out", type=Path, default=ROOT / "reports/qa/ISOP-2090/20261012-full")
    args = parser.parse_args()
    if args.recorded:
        if args.execute:
            parser.error("recorded analysis cannot execute network")
        return analyse_recorded(args)
    if args.selection_context:
        parser.error("selection context is only accepted with --recorded")
    return run_client_readonly(args)

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print("本地编排失败：" + type(error).__name__ + "；未自动重试。")
        raise SystemExit(1)
