#!/usr/bin/env python3
"""Thin CLI for the directed ISOP-2090 FAT report suite."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from filbet.loss_rebate import reassess_recorded, run_readonly


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", default=".env.fat")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--insecure", action="store_true")
    parser.add_argument("--out", type=Path, default=ROOT / "reports/qa/ISOP-2090/20261012-full")
    parser.add_argument("--reassess", type=Path, help="offline reclassification of an existing result.json")
    args = parser.parse_args()
    if args.reassess:
        if args.execute:
            parser.error("offline reassessment cannot combine with --execute")
        return reassess_recorded(args.reassess)
    return run_readonly(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print("本地编排失败：" + type(error).__name__ + "；检查参数与本轮输出，未自动重试。")
        raise SystemExit(1)
