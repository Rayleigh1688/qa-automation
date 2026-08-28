#!/usr/bin/env python3
"""Render P0 main-flow scenario status from executable API results."""

from __future__ import annotations

import argparse
import csv
import html
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


def release_verdict(counter: Counter[str]) -> tuple[str, str]:
    if counter["失败"] or counter["未通过"]:
        return "BLOCKED", "存在产品缺陷或自动化失败，不能作为 P0 放行结论。"
    if counter["未自动执行"] or counter["未执行"] or counter["未映射"]:
        return "PARTIAL", "已执行场景通过，但仍有未自动化或未执行的 P0 场景。"
    return "PASS", "所有已纳入 P0 的场景均通过。"


def status_class(status: str) -> str:
    if status == "通过":
        return "pass"
    if status in {"失败", "未通过"}:
        return "fail"
    return "pending"


def render_html_report(
    scope: str,
    scenarios_path: str,
    verdict: str,
    verdict_detail: str,
    counter: Counter[str],
    details: list[dict[str, str]],
) -> str:
    stages: dict[str, list[dict[str, str]]] = {}
    for item in details:
        stages.setdefault(item["flow_stage_label"], []).append(item)
    cards = "".join(
        f'<div class="metric {status_class(name)}"><span>{html.escape(name)}</span><strong>{count}</strong></div>'
        for name, count in counter.most_common()
    )
    flow_items = []
    for stage, items in stages.items():
        stage_status = next((item["runtime_status"] for item in items if item["runtime_status"] in {"失败", "未通过"}), "")
        stage_status = stage_status or next((item["runtime_status"] for item in items if item["runtime_status"] != "通过"), "通过")
        flow_items.append(
            f'<a href="#{html.escape(stage)}" class="flow {status_class(stage_status)}">'
            f'{html.escape(stage)}<small>{len(items)}</small></a>'
        )
    sections = []
    for stage, items in stages.items():
        rows = []
        for item in items:
            rows.append(
                "<details class=\"case\">"
                f"<summary><span class=\"badge {status_class(item['runtime_status'])}\">{html.escape(item['runtime_status'])}</span>"
                f"<b>{html.escape(item['scenario_id'])}</b><span>{html.escape(item['scenario_name'])}</span>"
                f"<em>{html.escape(item['polarity'])}</em></summary>"
                "<div class=\"case-body\">"
                f"<dl><dt>自动化状态</dt><dd>{html.escape(item['automation_status'])}</dd>"
                f"<dt>运行结论</dt><dd>{html.escape(item['runtime_detail'])}</dd>"
                f"<dt>接口/资产</dt><dd>{html.escape(item['endpoints_or_assets'])}</dd>"
                f"<dt>预置条件</dt><dd>{html.escape(item['precondition'])}</dd>"
                f"<dt>预期断言</dt><dd>{html.escape(item['expected_assertions'])}</dd></dl>"
                "</div></details>"
            )
        sections.append(f'<section id="{html.escape(stage)}"><h2>{html.escape(stage)} <small>{len(items)} 个场景</small></h2>{"".join(rows)}</section>')
    generated_at = datetime.now().astimezone().isoformat()
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>P0 API 主流程报告</title><style>
:root{{--ink:#17232d;--muted:#64727d;--line:#d9e1e5;--panel:#fff;--bg:#f3f6f5;--pass:#16754b;--fail:#bd3434;--pending:#a76508}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:14px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
main{{max-width:1180px;margin:auto;padding:28px 20px 56px}}header{{display:flex;justify-content:space-between;gap:24px;align-items:start;border-bottom:1px solid var(--line);padding-bottom:22px}}h1{{font-size:26px;margin:0 0 5px}}h2{{font-size:18px;margin:30px 0 10px}}h2 small,.meta{{font-size:13px;font-weight:400;color:var(--muted)}}.verdict{{min-width:220px;border:1px solid var(--line);background:var(--panel);padding:14px 16px;border-left:5px solid var(--pending)}}.verdict.fail{{border-left-color:var(--fail)}}.verdict.pass{{border-left-color:var(--pass)}}.verdict strong{{display:block;font-size:22px;letter-spacing:0;margin-bottom:3px}}.metrics{{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin:20px 0}}.metric{{background:var(--panel);border:1px solid var(--line);padding:12px}}.metric span{{color:var(--muted);display:block}}.metric strong{{font-size:24px}}.flow-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:8px}}.flow{{color:var(--ink);text-decoration:none;background:var(--panel);border:1px solid var(--line);padding:10px 12px;border-left:4px solid var(--pending)}}.flow.pass{{border-left-color:var(--pass)}}.flow.fail{{border-left-color:var(--fail)}}.flow small{{float:right;color:var(--muted)}}.case{{background:var(--panel);border:1px solid var(--line);margin:6px 0}}summary{{display:grid;grid-template-columns:74px 84px 1fr 70px;gap:10px;align-items:center;padding:11px 12px;cursor:pointer;list-style:none}}summary::-webkit-details-marker{{display:none}}.badge{{font-size:12px;font-weight:600}}.badge.pass{{color:var(--pass)}}.badge.fail{{color:var(--fail)}}.badge.pending{{color:var(--pending)}}summary em{{color:var(--muted);font-style:normal;text-align:right}}.case-body{{border-top:1px solid var(--line);padding:12px 16px;background:#fbfcfc}}dl{{display:grid;grid-template-columns:105px 1fr;gap:7px 14px;margin:0}}dt{{color:var(--muted)}}dd{{margin:0;word-break:break-word}}@media(max-width:640px){{header{{display:block}}.verdict{{margin-top:16px}}summary{{grid-template-columns:68px 1fr}}summary em{{display:none}}dl{{grid-template-columns:1fr}}dt{{margin-top:8px}}}}
</style></head><body><main><header><div><h1>P0 API 主流程报告</h1><div class="meta">环境：{html.escape(scope)} · 生成时间：{html.escape(generated_at)} · 场景：{html.escape(scenarios_path)}</div></div><div class="verdict {status_class('失败' if verdict == 'BLOCKED' else '通过' if verdict == 'PASS' else '未执行')}"><strong>{verdict}</strong><span>{html.escape(verdict_detail)}</span></div></header><div class="metrics">{cards}</div><nav class="flow-grid">{''.join(flow_items)}</nav>{''.join(sections)}</main></body></html>"""


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
    elif scenario_id == "MF-046":
        agree = names.get("admin_withdraw_agree")
        success = names.get("admin_withdraw_success")
        if agree and success and agree.get("business_status") is True and success.get("business_status") is True:
            return "通过", "后台审核同意并标记成功；不校验第三方到账"
        if not agree or not success:
            return "未执行", "缺少后台提现审核或成功状态结果"
        return "未通过", str(success.get("body_sample") or success.get("data") or agree.get("body_sample") or agree.get("data") or "")
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
    if automation_status == "known_defect":
        return "失败", scenario.get("notes", "")
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
    parser.add_argument("--html-out", default="")
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
    details: list[dict[str, str]] = []
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
        details.append({**scenario, "runtime_status": runtime_status, "runtime_detail": detail})

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
    if args.html_out:
        verdict, verdict_detail = release_verdict(runtime_counter)
        Path(args.html_out).write_text(
            render_html_report(args.scope, args.scenarios, verdict, verdict_detail, runtime_counter, details),
            encoding="utf-8",
        )
        print(f"wrote {Path(args.html_out).resolve()}")


if __name__ == "__main__":
    main()
