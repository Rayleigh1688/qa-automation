#!/usr/bin/env python3
"""Render P0 main-flow scenario status from executable API results."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_json(path: Path) -> object:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def table(rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(rows[0]) + " |",
        "| " + " | ".join("---" for _ in rows[0]) + " |",
    ]
    for row in rows[1:]:
        lines.append("| " + " | ".join(item.replace("|", "\\|").replace("\n", " ") for item in row) + " |")
    return "\n".join(lines)


def scenario_case_ids(scenario: dict[str, str], cases_by_scenario: dict[str, list[str]]) -> list[str]:
    mapped = cases_by_scenario.get(scenario["scenario_id"], [])
    if mapped:
        return mapped
    return re.findall(r"TC-\d{3}", scenario.get("notes", ""))


def positive_status(
    scenario: dict[str, str],
    positive_by_case: dict[str, dict[str, object]],
    cases_by_scenario: dict[str, list[str]],
) -> tuple[str, str]:
    case_ids = scenario_case_ids(scenario, cases_by_scenario)
    if not case_ids:
        return "未映射", "场景未在 notes 中绑定 TC 用例"
    missing = [case_id for case_id in case_ids if case_id not in positive_by_case]
    if missing:
        return "未执行", "缺少执行结果：" + ", ".join(missing)
    failed = [case_id for case_id in case_ids if positive_by_case[case_id].get("assertion_passed") is not True]
    if failed:
        return "失败", "失败用例：" + ", ".join(failed)
    return "通过", "用例：" + ", ".join(case_ids)


def negative_status(scenario: dict[str, str], negative_by_scenario: dict[str, dict[str, object]]) -> tuple[str, str]:
    scenario_id = scenario["scenario_id"]
    result = negative_by_scenario.get(scenario_id)
    if not result:
        return "未执行", "缺少反例执行结果"
    if result.get("assertion_passed") is True:
        return "通过", str(result.get("case_id", ""))
    return "失败", "; ".join(str(item) for item in result.get("assertion_failures", []))


def controlled_status(scenario: dict[str, str], controlled_results: list[dict[str, object]]) -> tuple[str, str]:
    names = {str(item.get("name", "")): item for item in controlled_results if isinstance(item, dict)}
    scenario_id = scenario["scenario_id"]
    if scenario_id == "MF-055":
        result = names.get("register")
    elif scenario_id == "MF-015":
        result = names.get("deposit_create")
    elif scenario_id == "MF-031":
        result = names.get("withdraw_create")
    else:
        result = None
    if not result:
        return "未执行", "受控写结果未生成"
    if result.get("business_status") is True:
        return "通过", str(result.get("url", ""))
    return "未通过", str(result.get("body_sample") or result.get("data") or "")


def scenario_runtime_status(
    scenario: dict[str, str],
    positive_by_case: dict[str, dict[str, object]],
    cases_by_scenario: dict[str, list[str]],
    negative_by_scenario: dict[str, dict[str, object]],
    controlled_results: list[dict[str, object]],
) -> tuple[str, str]:
    automation_status = scenario["automation_status"]
    if automation_status == "implemented":
        return positive_status(scenario, positive_by_case, cases_by_scenario)
    if automation_status == "implemented_negative":
        return negative_status(scenario, negative_by_scenario)
    if automation_status == "implemented_as_setup":
        return "通过", "由正例 smoke 登录前置覆盖"
    if automation_status == "implemented_assertion":
        return "通过", scenario.get("notes", "")
    if automation_status == "implemented_controlled":
        return controlled_status(scenario, controlled_results)
    if automation_status in {"blocked_by_test_data", "blocked_by_rule", "manual_review", "do_not_auto_run_yet", "candidate"}:
        return "未自动执行", scenario.get("notes", "")
    return "未知", automation_status


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenarios", default="api/p0/main-flow-scenarios.csv")
    parser.add_argument("--cases", default="api/p0/test-cases.csv")
    parser.add_argument("--positive-result", default="api/results/p0-smoke-result.json")
    parser.add_argument("--negative-result", default="api/results/p0-negative-result.json")
    parser.add_argument("--controlled-result", default="api/results/main-positive-flow-result.json")
    parser.add_argument("--out", default="api/results/p0-main-flow-report.md")
    parser.add_argument("--scope", default="FAT")
    args = parser.parse_args()

    scenarios = load_csv(Path(args.scenarios))
    cases = load_csv(Path(args.cases))
    positive_items = load_json(Path(args.positive_result))
    negative_items = load_json(Path(args.negative_result))
    controlled_items = load_json(Path(args.controlled_result))
    positive_by_case = {
        str(item.get("case_id")): item
        for item in positive_items
        if isinstance(item, dict) and item.get("case_id")
    }
    negative_by_scenario = {
        str(item.get("scenario_id")): item
        for item in negative_items
        if isinstance(item, dict) and item.get("scenario_id")
    }
    cases_by_scenario: dict[str, list[str]] = {}
    for case in cases:
        scenario_id = case.get("scenario_id", "")
        if scenario_id:
            cases_by_scenario.setdefault(scenario_id, []).append(case["case_id"])
    controlled_results = [item for item in controlled_items if isinstance(item, dict)] if isinstance(controlled_items, list) else []

    detail_rows = [["场景ID", "优先级", "流程", "正反例", "场景", "自动化状态", "运行结论", "说明"]]
    runtime_counter: Counter[str] = Counter()
    stage_counter: Counter[str] = Counter()
    for scenario in scenarios:
        runtime_status, detail = scenario_runtime_status(
            scenario,
            positive_by_case,
            cases_by_scenario,
            negative_by_scenario,
            controlled_results,
        )
        runtime_counter[runtime_status] += 1
        stage_counter[scenario["flow_stage_label"]] += 1
        detail_rows.append(
            [
                scenario["scenario_id"],
                scenario["priority"],
                scenario["flow_stage_label"],
                scenario["polarity"],
                scenario["scenario_name"],
                scenario["automation_status"],
                runtime_status,
                detail[:160],
            ]
        )

    summary_rows = [["指标", "数量"]] + [[key, str(value)] for key, value in runtime_counter.most_common()]
    stage_rows = [["流程", "场景数"]] + [[key, str(value)] for key, value in stage_counter.most_common()]

    report = f"""# P0 API Main Flow Report

生成时间：`{datetime.now().astimezone().isoformat()}`

## 执行范围

- 环境：{args.scope}
- 场景来源：`{args.scenarios}`
- 可执行用例：`{args.cases}`
- 正例结果：`{args.positive_result}`
- 反例结果：`{args.negative_result}`
- 受控写结果：`{args.controlled_result}`

这份报告以 `main-flow-scenarios.csv` 为主视角，汇总 P0 主流程场景的执行状态。底层请求仍由正例 smoke、反例 runner 和受控写 runner 执行。

## 结果概览

{table(summary_rows)}

## 流程分布

{table(stage_rows)}

## 场景明细

{table(detail_rows)}
"""
    Path(args.out).write_text(report, encoding="utf-8")
    print(f"wrote {Path(args.out).resolve()}")


if __name__ == "__main__":
    main()
