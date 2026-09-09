#!/usr/bin/env python3
"""Render Playwright JSON into the shared P0 report layout."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

from ui_report_evidence import build_evidence, append_markdown

from filbet.reporting import (
    format_execution_duration,
    report_verdict,
    write_html_report,
    write_markdown_report,
)


def load_json(path: Path, default: object) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def sanitize_detail(value: object) -> str:
    message = re.sub(r"\x1b\[[0-9;]*m", "", str(value or ""))
    for name, secret in os.environ.items():
        if len(secret) >= 4 and any(marker in name.upper() for marker in (
            "PASSWORD", "SECRET", "TOKEN", "OTP", "CODE", "PHONE", "EMAIL", "DEVICE",
        )):
            message = message.replace(secret, "<redacted>")
    return re.sub(
        r"([?&](?:token|code|otp|phone|email|uid|device_id|x-device-id)=)[^&\s]+",
        r"\1<redacted>",
        message,
        flags=re.IGNORECASE,
    )[:2000]


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
                    "detail": sanitize_detail(error.get("message") or last.get("error") or ""),
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


def apply_expected_tests(items: list[dict[str, str]], expected: object) -> list[dict[str, str]]:
    if not isinstance(expected, list):
        return items
    remaining = list(items)
    ordered: list[dict[str, str]] = []
    for entry in expected:
        if not isinstance(entry, dict):
            continue
        file_name = Path(str(entry.get("file") or "")).name
        title = str(entry.get("title") or "")
        display_name = str(entry.get("displayName") or title)
        group_name = str(entry.get("group") or Path(file_name).stem or "UI 用例")
        matched_index = next((
            index for index, item in enumerate(remaining)
            if (Path(item["target"]).name, item["name"]) == (file_name, title)
        ), None)
        if matched_index is not None:
            item = remaining.pop(matched_index)
            item["id"] = str(entry.get("id") or item["id"])
            item["group"] = group_name
            item["name"] = display_name
            ordered.append(item)
            continue
        ordered.append({
            "group": group_name,
            "id": str(entry.get("id") or f"UI-{len(ordered) + 1:03d}"),
            "name": display_name or "未收集的 UI 用例",
            "kind": "UI",
            "status": "NOT_RUN",
            "target": file_name,
            "expected": "Playwright 默认套件必须收集并执行该用例",
            "actual": "not collected",
            "duration": "",
            "detail": "默认 UI P0 固定清单中的用例未被 Playwright 收集。",
        })
    for index, item in enumerate(remaining, 1):
        item["id"] = f"UI-UNPLANNED-{index:03d}"
        item["status"] = "FAIL"
        item["detail"] = (
            "该用例不在 ui/data/client-p0-default-suite.json 固定清单中；"
            "请先完成 P0 范围评审并同步清单。"
        )
    return [*ordered, *remaining]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="ui/results/ui-playwright-result.json")
    parser.add_argument("--scope", default="FAT")
    parser.add_argument("--run-status", choices=["PASS", "FAILED", "INTERRUPTED", "BLOCKED"], default="")
    parser.add_argument("--run-status-file", default="ui/results/p0-ui-run-status.json")
    parser.add_argument("--expected", default="ui/data/client-p0-default-suite.json")
    parser.add_argument("--out", default="ui/reports/p0-ui-report.md")
    parser.add_argument("--html-out", default="ui/reports/p0-ui-report.html")
    args = parser.parse_args()
    source = load_json(Path(args.input), {})
    status_source = load_json(Path(args.run_status_file), {})
    items = apply_expected_tests(collect_tests(source), load_json(Path(args.expected), []))
    run_status = args.run_status or (
        str(status_source.get("status") or "") if isinstance(status_source, dict) else ""
    ) or (str(source.get("status") or "") if isinstance(source, dict) else "")
    verdict, detail = report_verdict(items, run_status)
    kwargs = dict(title="P0 UI 执行报告", scope=args.scope, verdict=verdict, verdict_detail=detail, items=items)
    evidence = build_evidence(source, status_source, items, Path(args.input), Path(args.html_out))
    write_markdown_report(**kwargs, output=Path(args.out))
    append_markdown(Path(args.out), evidence)
    metadata = []
    if isinstance(status_source, dict):
        metadata = [
            ("执行状态", str(status_source.get("status") or "")),
            ("最后阶段", str(status_source.get("stage") or "")),
            ("执行总耗时", format_execution_duration(
                status_source.get("started_at"), status_source.get("finished_at"),
            )),
        ]
    write_html_report(**kwargs, report_kind="UI", metadata=metadata, evidence=evidence, output=Path(args.html_out))
    print(f"wrote {Path(args.out).resolve()}")
    print(f"wrote {Path(args.html_out).resolve()}")


if __name__ == "__main__":
    main()
