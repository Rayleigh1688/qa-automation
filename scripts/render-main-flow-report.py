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
<title>P0 主流程报告</title><style>
:root{{--ink:#17232d;--muted:#64727d;--line:#d9e1e5;--panel:#fff;--bg:#f3f6f5;--pass:#16754b;--fail:#bd3434;--pending:#a76508}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:14px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
main{{max-width:1180px;margin:auto;padding:28px 20px 56px}}header{{display:flex;justify-content:space-between;gap:24px;align-items:start;border-bottom:1px solid var(--line);padding-bottom:22px}}h1{{font-size:26px;margin:0 0 5px}}h2{{font-size:18px;margin:30px 0 10px}}h2 small,.meta{{font-size:13px;font-weight:400;color:var(--muted)}}.verdict{{min-width:220px;border:1px solid var(--line);background:var(--panel);padding:14px 16px;border-left:5px solid var(--pending)}}.verdict.fail{{border-left-color:var(--fail)}}.verdict.pass{{border-left-color:var(--pass)}}.verdict strong{{display:block;font-size:22px;letter-spacing:0;margin-bottom:3px}}.metrics{{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin:20px 0}}.metric{{background:var(--panel);border:1px solid var(--line);padding:12px}}.metric span{{color:var(--muted);display:block}}.metric strong{{font-size:24px}}.flow-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:8px}}.flow{{color:var(--ink);text-decoration:none;background:var(--panel);border:1px solid var(--line);padding:10px 12px;border-left:4px solid var(--pending)}}.flow.pass{{border-left-color:var(--pass)}}.flow.fail{{border-left-color:var(--fail)}}.flow small{{float:right;color:var(--muted)}}.case{{background:var(--panel);border:1px solid var(--line);margin:6px 0}}summary{{display:grid;grid-template-columns:74px 84px 1fr 70px;gap:10px;align-items:center;padding:11px 12px;cursor:pointer;list-style:none}}summary::-webkit-details-marker{{display:none}}.badge{{font-size:12px;font-weight:600}}.badge.pass{{color:var(--pass)}}.badge.fail{{color:var(--fail)}}.badge.pending{{color:var(--pending)}}summary em{{color:var(--muted);font-style:normal;text-align:right}}.case-body{{border-top:1px solid var(--line);padding:12px 16px;background:#fbfcfc}}dl{{display:grid;grid-template-columns:105px 1fr;gap:7px 14px;margin:0}}dt{{color:var(--muted)}}dd{{margin:0;word-break:break-word}}@media(max-width:640px){{header{{display:block}}.verdict{{margin-top:16px}}summary{{grid-template-columns:68px 1fr}}summary em{{display:none}}dl{{grid-template-columns:1fr}}dt{{margin-top:8px}}}}
</style></head><body><main><header><div><h1>P0 主流程报告</h1><div class="meta">环境：{html.escape(scope)} · 生成时间：{html.escape(generated_at)} · 场景：{html.escape(scenarios_path)}</div></div><div class="verdict {status_class('失败' if verdict == 'BLOCKED' else '通过' if verdict == 'PASS' else '未执行')}"><strong>{verdict}</strong><span>{html.escape(verdict_detail)}</span></div></header><div class="metrics">{cards}</div><nav class="flow-grid">{''.join(flow_items)}</nav>{''.join(sections)}</main></body></html>"""


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
    elif scenario_id == "MF-064":
        required = [names.get("deposit_create"), names.get("admin_deposit_risk_list"), names.get("admin_deposit_manual_success")]
        if any(item is None for item in required):
            return "未执行", "缺少充值创建、后台待审定位或补单结果"
        if all(item.get("business_status") is True for item in required if item):
            return "通过", "本次充值单已创建、在后台定位并完成补单"
        return "未通过", "充值创建、后台待审定位或补单存在业务失败"
    elif scenario_id == "MF-065":
        required = [
            names.get("withdraw_create"),
            names.get("admin_withdraw_risk_audit_list"),
            names.get("admin_withdraw_agree"),
            names.get("admin_withdraw_success"),
        ]
        if any(item is None for item in required):
            return "未执行", "缺少提现创建、后台待审定位、审核或成功标记结果"
        if all(item.get("business_status") is True for item in required if item):
            return "通过", "本次提现单已创建、在后台定位、审核同意并标记成功"
        return "未通过", "提现创建、后台待审定位、审核或成功标记存在业务失败"
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


def aggregate_flow_status(
    scenario_id: str,
    flow_cases: list[dict[str, str]],
    positive_by_case: dict[str, dict[str, object]],
    negative_by_case: dict[str, dict[str, object]],
    controlled_results: list[dict[str, object]],
) -> tuple[str, str]:
    failures: list[str] = []
    missing: list[str] = []
    pending: list[str] = []
    controlled_by_name = {str(item.get("name", "")): item for item in controlled_results}
    controlled_map = {
        "CTC-001": ["register"],
        "CTC-003": ["kyc_submit"],
        "CTC-004": ["admin_kyc_approve", "kyc_detail_after_approval"],
        "CTC-005": ["deposit_create"],
        "CTC-006": ["admin_deposit_manual_success"],
        "CTC-007": ["p0_reconciliation"],
        "CTC-008": ["p0_reconciliation"],
        "CTC-009": ["withdraw_create"],
        "CTC-010": ["admin_withdraw_risk_audit_list"],
        "DTC-002": ["pre_kyc_withdraw_blocked"],
    }
    for case in flow_cases:
        case_id = case["case_id"]
        policy = case["execution_policy"]
        if policy == "safe_smoke":
            result = positive_by_case.get(case_id)
            if result is None:
                missing.append(case_id)
            elif result.get("assertion_passed") is not True:
                failures.append(case_id)
        elif policy == "negative_smoke":
            result = negative_by_case.get(case_id)
            if result is None:
                missing.append(case_id)
            elif result.get("assertion_passed") is not True:
                failures.append(case_id)
        elif case_id in controlled_map:
            names = controlled_map[case_id]
            results = [controlled_by_name.get(name) for name in names]
            if any(result is None for result in results):
                missing.append(case_id)
            elif any(result.get("business_status") is not True for result in results if result):
                failures.append(case_id)
        elif policy == "setup":
            continue
        elif policy == "known_defect_probe":
            continue
        else:
            pending.append(case_id)
    if scenario_id in {"MF-006", "MF-008"}:
        reconciliation = controlled_by_name.get("p0_reconciliation")
        if reconciliation is None:
            missing.append("p0_reconciliation")
        elif reconciliation.get("business_status") is not True:
            failures.append("p0_reconciliation")
    if failures:
        return "失败", "失败用例：" + ", ".join(failures)
    if missing:
        detail = "缺少执行结果：" + ", ".join(missing)
        if pending:
            detail += "；待实现/待数据：" + ", ".join(pending)
        return "未执行", detail
    if pending:
        return "部分通过", "已执行项通过；待实现/待数据：" + ", ".join(pending)
    return "通过", "该主流程所有已登记用例均通过"


def render_flow_html(scope: str, rows: list[dict[str, str]], verdict: str) -> str:
    cards = "".join(
        f'<section><b>{html.escape(row["scenario_id"])} · {html.escape(row["flow_stage_label"])}</b>'
        f'<span class="{status_class(row["runtime_status"])}">{html.escape(row["runtime_status"])}</span>'
        f'<p>{html.escape(row["runtime_detail"])}</p></section>'
        for row in rows
    )
    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>P0 主流程报告</title><style>body{{max-width:980px;margin:auto;padding:28px;font:14px/1.6 sans-serif;background:#f4f6f5;color:#17232d}}header,section{{background:#fff;border:1px solid #d9e1e5;padding:16px;margin:10px 0}}b{{font-size:17px}}span{{float:right}}.pass{{color:#16754b}}.fail{{color:#bd3434}}.pending{{color:#a76508}}p{{margin:8px 0 0;color:#64727d}}</style></head>
<body><header><h1>P0 主流程报告</h1><p>环境：{html.escape(scope)} · 结论：{html.escape(verdict)}</p></header>{cards}</body></html>"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenarios", default="api/p0/main-flow-scenarios.csv")
    parser.add_argument("--cases", default="api/p0/test-cases.csv")
    parser.add_argument("--positive-result", default="api/results/p0-smoke-result.json")
    parser.add_argument("--negative-result", default="api/results/p0-negative-result.json")
    parser.add_argument("--controlled-result", default="api/results/fund-flow-seed-result.json")
    parser.add_argument("--withdraw-result", default="api/results/withdraw-result.json")
    parser.add_argument("--pre-kyc-withdraw-result", default="ui/results/client-unverified-withdraw.json")
    parser.add_argument("--kyc-result", default="api/results/kyc-result.json")
    parser.add_argument("--reconciliation-result", default="api/results/p0-reconciliation-result.json")
    parser.add_argument("--out", default="api/results/p0-main-flow-report.md")
    parser.add_argument("--html-out", default="")
    parser.add_argument("--scope", default="FAT")
    args = parser.parse_args()

    scenarios = load_csv(Path(args.scenarios))
    cases = load_csv(Path(args.cases))
    positive_items = load_json(Path(args.positive_result))
    negative_items = load_json(Path(args.negative_result))
    controlled_items = load_json(Path(args.controlled_result))
    withdraw_items = load_json(Path(args.withdraw_result))
    pre_kyc_withdraw = load_json(Path(args.pre_kyc_withdraw_result))
    kyc_items = load_json(Path(args.kyc_result))
    reconciliation = load_json(Path(args.reconciliation_result))
    positive_by_case = {
        str(item.get("case_id")): item
        for item in positive_items
        if isinstance(item, dict) and item.get("case_id")
    }
    negative_by_case = {
        str(item.get("case_id")): item
        for item in negative_items
        if isinstance(item, dict) and item.get("case_id")
    }
    cases_by_scenario: dict[str, list[dict[str, str]]] = {}
    for case in cases:
        scenario_id = case.get("scenario_id", "")
        if scenario_id:
            cases_by_scenario.setdefault(scenario_id, []).append(case)
    controlled_results = [item for item in controlled_items if isinstance(item, dict)] if isinstance(controlled_items, list) else []
    if isinstance(withdraw_items, list):
        controlled_results.extend(item for item in withdraw_items if isinstance(item, dict))
    if isinstance(pre_kyc_withdraw, dict):
        controlled_results.append({
            "name": "pre_kyc_withdraw_blocked",
            "business_status": bool(
                pre_kyc_withdraw.get("securityRequirementsVisible") is True
                and pre_kyc_withdraw.get("walletPasswordRequired") is True
                and pre_kyc_withdraw.get("kycRequired") is True
                and pre_kyc_withdraw.get("withdrawRequestCount") == 0
            ),
            "data": pre_kyc_withdraw,
        })
    if isinstance(kyc_items, list):
        controlled_results.extend(item for item in kyc_items if isinstance(item, dict))
    if isinstance(reconciliation, dict):
        controlled_results.append({
            "name": "p0_reconciliation",
            "business_status": reconciliation.get("status") == "PASS",
            "data": reconciliation,
        })

    detail_rows = [["顺序", "场景ID", "主流程", "用例数", "正例", "反例", "运行结论", "说明"]]
    details: list[dict[str, str]] = []
    runtime_counter: Counter[str] = Counter()
    stage_counter: Counter[str] = Counter()
    for scenario in scenarios:
        flow_cases = cases_by_scenario.get(scenario["scenario_id"], [])
        runtime_status, detail = aggregate_flow_status(
            scenario["scenario_id"], flow_cases, positive_by_case, negative_by_case, controlled_results
        )
        runtime_counter[runtime_status] += 1
        stage_counter[scenario["flow_stage_label"]] += 1
        detail_rows.append(
            [
                scenario["flow_order"],
                scenario["scenario_id"],
                scenario["flow_stage_label"],
                str(len(flow_cases)),
                str(sum(case.get("polarity") == "positive" for case in flow_cases)),
                str(sum(case.get("polarity") == "negative" for case in flow_cases)),
                runtime_status,
                detail[:160],
            ]
        )
        details.append({**scenario, "runtime_status": runtime_status, "runtime_detail": detail})

    summary_rows = [["指标", "数量"]] + [[key, str(value)] for key, value in runtime_counter.most_common()]
    stage_rows = [["流程", "主流程数"]] + [[key, str(value)] for key, value in stage_counter.items()]

    report = f"""# P0 Main Flow Report

生成时间：`{datetime.now().astimezone().isoformat()}`

## 执行范围

- 环境：{args.scope}
- 场景来源：`{args.scenarios}`
- 可执行用例：`{args.cases}`
- 正例结果：`{args.positive_result}`
- 反例结果：`{args.negative_result}`
- 受控写结果：`{args.controlled_result}`
- 新号 KYC 前提现 UI 结果：`{args.pre_kyc_withdraw_result}`
- KYC 结果：`{args.kyc_result}`
- 资金链核对：`{args.reconciliation_result}`

这份报告按真实业务依赖顺序汇总 8 条 P0 主流程。`test-cases.csv` 是完整正反例索引；接口候选池不决定这里的范围或顺序。

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
        verdict = "BLOCKED" if runtime_counter["失败"] else "PARTIAL" if runtime_counter["未执行"] or runtime_counter["部分通过"] else "PASS"
        Path(args.html_out).write_text(
            render_flow_html(args.scope, details, verdict),
            encoding="utf-8",
        )
        print(f"wrote {Path(args.html_out).resolve()}")


if __name__ == "__main__":
    main()
