#!/usr/bin/env python3
"""Thin CLI for the directed ISOP-2090 FAT report suite."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "scripts"))
from filbet.loss_rebate import reassess_recorded, run_readonly
from qa_core.output_paths import repository_output_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", default=".env.fat")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--insecure", action="store_true")
    parser.add_argument("--out", type=lambda value: repository_output_path(value, ROOT),
                        default=str(ROOT / "reports/qa/ISOP-2090/20261012-full"))
    parser.add_argument("--start-date", help="inclusive GMT+8 statistics date, YYYY-MM-DD; requires --end-date")
    parser.add_argument("--end-date", help="inclusive GMT+8 statistics date; maximum window 31 days")
    parser.add_argument("--reassess", type=Path, help="offline reclassification of an existing result.json")
    args = parser.parse_args()
    if args.reassess:
        if args.execute or args.start_date or args.end_date:
            parser.error("offline reassessment cannot combine with --execute or a new date window")
        return reassess_recorded(args.reassess)
    return run_readonly(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print("本地编排失败：" + type(error).__name__ + "；检查参数与本轮输出，未自动重试。")
        raise SystemExit(1)
