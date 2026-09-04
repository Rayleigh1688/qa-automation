#!/usr/bin/env python3
"""Render Playwright JSON into the shared P0 report layout."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from p0_report_template import report_verdict, write_html_report, write_markdown_report


def collect_tests(value: object, inherited_file: str = "") -> list[dict[str, str]]:
    collected: list[dict[str, str]] = []
    if isinstance(value, dict):
        current_file = str(value.get("file") or inherited_file)
        tests = value.get("tests")
        if isinstance(tests, list) and ("title" in value or current_file):
            for test in tests:
                if not isinstance(test, dict):
                    continue
                results = test.get("results") if isinstance(test.get("results"), list) else []
                last = results[-1] if results and isinstance(results[-1], dict) else {}
                raw_status = str(last.get("status") or ("passed" if test.get("ok") is True else "failed"))
                status = "PASS" if raw_status == "passed" else "SKIPPED" if raw_status == "skipped" else "FAIL"
                error = last.get("error") if isinstance(last.get("error"), dict) else {}
                collected.append({
                    "group": Path(current_file).stem or "UI 用例", "id": f"UI-{len(collected) + 1:03d}",
                    "name": str(test.get("title") or value.get("title") or "UI test"), "kind": "UI",
                    "status": status, "target": current_file, "expected": "Playwright 用例断言全部满足",
                    "actual": raw_status, "duration": f"{last.get('duration', '')}ms" if last else "",
                    "detail": str(error.get("message") or last.get("error") or ""),
                })
        for key, child in value.items():
            if key not in {"tests", "results"}:
                child_items = collect_tests(child, current_file)
                for item in child_items:
                    item["id"] = f"UI-{len(collected) + 1:03d}"
                    collected.append(item)
    elif isinstance(value, list):
        for child in value:
            child_items = collect_tests(child, inherited_file)
            for item in child_items:
                item["id"] = f"UI-{len(collected) + 1:03d}"
                collected.append(item)
    return collected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="ui/results/ui-playwright-result.json")
    parser.add_argument("--scope", default="FAT")
    parser.add_argument("--out", default="ui/reports/p0-ui-report.md")
    parser.add_argument("--html-out", default="ui/reports/p0-ui-report.html")
    args = parser.parse_args()
    try:
        source = json.loads(Path(args.input).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        source = {}
    items = collect_tests(source)
    run_status = str(source.get("status") or "") if isinstance(source, dict) else ""
    verdict, detail = report_verdict(items, "FAILED" if run_status == "failed" else "")
    kwargs = dict(title="P0 UI 执行报告", scope=args.scope, verdict=verdict, verdict_detail=detail, items=items)
    write_markdown_report(**kwargs, output=Path(args.out))
    write_html_report(**kwargs, report_kind="UI", output=Path(args.html_out))
    print(f"wrote {Path(args.out).resolve()}")
    print(f"wrote {Path(args.html_out).resolve()}")


if __name__ == "__main__":
    main()
