#!/usr/bin/env python3
"""Render UI P0 positive/negative results from Playwright JSON attachments."""

from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
from urllib.parse import urlsplit


def attachments(value: object):
    if isinstance(value, dict):
        for item in value.get("attachments", []):
            if isinstance(item, dict):
                yield item
        for item in value.values():
            yield from attachments(item)
    elif isinstance(value, list):
        for item in value:
            yield from attachments(item)


def compact_url(value: str) -> str:
    parsed = urlsplit(value)
    return parsed.path or "/"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="ui/results/ui-playwright-result.json")
    parser.add_argument("--json-out", default="ui/results/client-p0-positive-negative.json")
    parser.add_argument("--report-out", default="ui/reports/client-p0-positive-negative-report.md")
    args = parser.parse_args()

    source = json.loads(Path(args.input).read_text(encoding="utf-8"))
    results: dict[str, dict[str, object]] = {}
    for item in attachments(source):
        if item.get("contentType") != "application/json" or not item.get("body"):
            continue
        try:
            result = json.loads(base64.b64decode(item["body"]))
        except (ValueError, TypeError, json.JSONDecodeError):
            continue
        name = result.get("name") if isinstance(result, dict) else None
        if (
            isinstance(name, str)
            and result.get("status") in {"passed", "failed", "blocked"}
            and (name.startswith("negative_") or name == "positive_logged_in_my_wallet")
        ):
            results[name] = result

    ordered = list(results.values())
    json_out = Path(args.json_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps({"results": ordered}, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# 客户端 P0 UI 正反例执行报告",
        "",
        f"- 用例数: {len(ordered)}",
        "",
        "| 用例 | 结果 | URL | 关键说明 |",
        "|---|---|---|---|",
    ]
    for result in ordered:
        state = result.get("state") if isinstance(result.get("state"), dict) else {}
        lines.append(
            f"| {result.get('name', '')} | {result.get('status', '')} | "
            f"`{compact_url(str(state.get('url', '')))}` | {result.get('note', '')} |"
        )
    report_out = Path(args.report_out)
    report_out.parent.mkdir(parents=True, exist_ok=True)
    report_out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {json_out} and {report_out}")


if __name__ == "__main__":
    main()
