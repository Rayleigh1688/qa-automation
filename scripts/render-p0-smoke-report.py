#!/usr/bin/env python3
"""Render P0 smoke JSON results into a concise Markdown report."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path


def load_cases(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return {row["case_id"]: row for row in csv.DictReader(handle)}


def table(rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(rows[0]) + " |",
        "| " + " | ".join("---" for _ in rows[0]) + " |",
    ]
    for row in rows[1:]:
        lines.append("| " + " | ".join(item.replace("|", "\\|") for item in row) + " |")
    return "\n".join(lines)


def body_status(item: dict[str, object]) -> str:
    body = item.get("decoded_body")
    if isinstance(body, dict) and "status" in body:
        return str(body["status"])
    return ""


def body_hint(item: dict[str, object]) -> str:
    body = item.get("decoded_body")
    if not isinstance(body, dict):
        return item.get("body_sample", "")[:120]
    data = body.get("data")
    if isinstance(data, dict):
        return "keys: " + ", ".join(str(key) for key in list(data.keys())[:8])
    if isinstance(data, list):
        return f"list[{len(data)}]"
    return str(data)[:120]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", default="api/results/p0-smoke-result.json")
    parser.add_argument("--cases", default="api/p0/test-cases.csv")
    parser.add_argument("--out", default="api/results/p0-smoke-report.md")
    parser.add_argument("--title", default="P0 API Smoke Report")
    parser.add_argument("--scope", default="FAT")
    parser.add_argument("--include-known-replacements", action="store_true")
    args = parser.parse_args()

    results = json.loads(Path(args.result).read_text(encoding="utf-8"))
    cases = load_cases(Path(args.cases))
    case_results = [item for item in results if item.get("case_id")]
    login_results = [item for item in results if item.get("priority") == "LOGIN"]
    passed = [item for item in case_results if item.get("assertion_passed") is True]
    failed = [item for item in case_results if item.get("assertion_passed") is False]
    domains = Counter(cases[item["case_id"]]["domain"] for item in case_results if item["case_id"] in cases)

    summary = [
        ["指标", "数量"],
        ["登录请求", str(len(login_results))],
        ["P0 用例", str(len(case_results))],
        ["断言通过", str(len(passed))],
        ["断言失败", str(len(failed))],
    ]
    domain_rows = [["领域", "用例数"]] + [[key, str(value)] for key, value in domains.most_common()]

    detail_rows = [["用例ID", "流程阶段", "领域", "用例", "HTTP", "业务状态", "断言", "耗时", "摘要"]]
    for item in case_results:
        case = cases.get(item["case_id"], {})
        failures = item.get("assertion_failures") or []
        detail_rows.append(
            [
                str(item["case_id"]),
                case.get("flow_stage_label", ""),
                case.get("domain", ""),
                case.get("case_name", ""),
                str(item.get("status", "")),
                body_status(item),
                "PASS" if item.get("assertion_passed") else "; ".join(str(failure) for failure in failures),
                f"{item.get('elapsed_ms', '')}ms",
                body_hint(item),
            ]
        )

    failed_rows = [["用例ID", "URL", "失败原因"]]
    for item in failed:
        failed_rows.append(
            [
                str(item["case_id"]),
                str(item.get("url", "")),
                "; ".join(str(failure) for failure in item.get("assertion_failures", [])),
            ]
        )

    known_replacements = """

## 已知替代关系

| 老接口 | 状态 | 替代接口 |
| --- | --- | --- |
| `GET /member/game/list` | HTTP 200 但业务 `status=false` | `GET /member/v2/index`、`GET /member/game/listRw`、`GET /member/game/list/recommend` |
| `GET /member/vip` | HTTP 200 但业务失败 | `GET /promo/vip/config`、`GET /promo/vip/sign/in/config` |
""" if args.include_known_replacements else ""

    report = f"""# {args.title}

生成时间：`{datetime.now().astimezone().isoformat()}`

## 执行范围

- 环境：{args.scope}
- 用例来源：`{args.cases}`
- 请求编码：CBOR
- 响应解码：CBOR/JSON
- TLS：测试环境临时使用 `--insecure`

## 结果概览

{table(summary)}

## 领域分布

{table(domain_rows)}

## 失败用例

{table(failed_rows) if failed else "无。"}

## 用例明细

{table(detail_rows)}
{known_replacements}
"""
    Path(args.out).write_text(report, encoding="utf-8")
    print(f"wrote {Path(args.out).resolve()}")


if __name__ == "__main__":
    main()
