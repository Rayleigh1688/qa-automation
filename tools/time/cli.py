#!/usr/bin/env python3
"""Print today's calendar ranges as millisecond timestamps; entirely offline."""

import argparse
from datetime import date, datetime
import json
import re

from ranges import GMT8, calculate_ranges


def parse_date(value: str) -> date:
    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError
        return date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError("日期须为有效的 YYYY-MM-DD，例如 2026-10-09") from None


def main() -> None:
    parser = argparse.ArgumentParser(prog="Time", description="今天、昨天、本周、本月、上月的毫秒时间戳（GMT+8）")
    parser.add_argument("--date", type=parse_date, help="指定基准日期 YYYY-MM-DD；默认 GMT+8 今天")
    parser.add_argument("--json", action="store_true", help="输出 JSON，便于复制或供脚本读取")
    args = parser.parse_args()
    reference = args.date if args.date is not None else datetime.now(GMT8).date()
    try:
        ranges = calculate_ranges(reference)
    except (ValueError, OverflowError):
        parser.error("日期超出可计算范围，无法取得完整的上月或下一周期")
    if args.json:
        print(json.dumps({
            "date": reference.isoformat(),
            "timezone": "GMT+8",
            "week_start": "Monday",
            "end_inclusive": True,
            "ranges": ranges,
        }, ensure_ascii=False, indent=2))
        return
    print(f"Time · {reference.isoformat()} · GMT+8 · 周一开周")
    print("范围    开始时间戳 (ms)   结束时间戳 (ms)")
    for item in ranges:
        print(f"{item['label']}    {item['start_ms']:>13}   {item['end_ms']:>13}")
    print("结束包含最后一毫秒（23:59:59.999）；本周、本月为完整日历范围。")


if __name__ == "__main__":
    main()
