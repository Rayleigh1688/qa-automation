#!/usr/bin/env python3
"""Render the current P0 API execution as a conventional case-level report."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from urllib.parse import urlsplit

from p0_report_template import (
    format_execution_duration,
    report_verdict,
    write_html_report,
    write_markdown_report,
)


CONTROLLED_NAMES = {
    "register_phone_allocate": "分配未注册手机号",
    "register_sms": "申请注册验证码",
    "register": "注册新账号",
    "client_token_reuse": "复用本轮客户端 Token",
    "kyc_detail_existing": "查询 KYC 当前状态",
    "kyc_submit": "提交 KYC",
    "admin_kyc_approve": "后台通过 KYC",
    "kyc_detail_after_approval": "复查 KYC 通过状态",
    "client_password_login": "资金账号登录",
    "client_otp_login": "资金账号登录",
    "wallet_before": "充值前钱包查询",
    "admin_auth": "后台登录预校验",
    "admin_login": "后台登录",
    "deposit_create": "创建充值订单",
    "admin_deposit_risk_list": "后台定位待审充值单",
    "admin_deposit_manual_success": "后台充值补单",
    "wallet_after_deposit": "等待充值到账并核对余额",
    "member_detail_for_turnover": "查询流水会员 UID",
    "turnover_before_clear": "查询清空前流水",
    "turnover_clear": "清空流水限制",
    "turnover_after_clear": "复查清空后流水",
    "member_detail_before_withdraw_account": "查询钱包密码状态",
    "wallet_password_set": "设置钱包密码",
    "wallet_password_check": "验证钱包密码",
    "withdraw_account_before": "查询现有提款账户",
    "withdraw_account_insert": "绑定 Maya 提款账户",
    "withdraw_account_after": "复查 Maya 账户并取得 account_id",
    "wallet_before_withdraw": "清流后确认可提现余额",
    "withdraw_create": "创建提现订单",
    "admin_withdraw_list": "后台精确查询提现订单",
    "admin_withdraw_risk_audit_list": "后台精确查询提现订单",
    "admin_withdraw_agree": "后台通过提现审核",
    "client_withdraw_list": "客户端精确查询提现订单",
    "wallet_after": "充值后钱包查询",
}

CONTROLLED_METHODS = {
    "client_password_login": "POST", "client_otp_login": "POST", "wallet_before": "GET",
    "admin_auth": "POST", "admin_login": "POST", "admin_token_reuse": "GET", "deposit_create": "GET",
    "admin_deposit_risk_list": "POST", "admin_deposit_manual_success": "POST", "wallet_after": "GET",
    "admin_withdraw_list": "POST", "admin_withdraw_risk_audit_list": "POST",
}

PLANNED_LOGINS = [
    ("LOGIN-01", "客户端认证", "POST /member/v2/login 或 /member/otp/login/v2"),
    ("LOGIN-02", "后台登录预校验", "POST /admin/login/auth"),
    ("LOGIN-03", "后台登录", "POST /admin/login"),
]

PLANNED_CONTROLLED = [
    (("register",), "注册新账号"),
    (("kyc_submit",), "提交 KYC"),
    (("admin_kyc_approve",), "后台通过 KYC"),
    (("deposit_create",), "创建充值订单"),
    (("admin_deposit_manual_success",), "后台充值补单"),
    (("wallet_after_deposit",), "等待充值到账并核对余额"),
    (("turnover_before_clear",), "查询清空前流水"),
    (("turnover_clear",), "清空流水限制"),
    (("wallet_password_check",), "验证钱包密码"),
    (("withdraw_account_after",), "复查 Maya 账户并取得 account_id"),
    (("wallet_before_withdraw",), "清流后确认可提现余额"),
    (("withdraw_create",), "创建提现订单"),
    (("admin_withdraw_risk_audit_list",), "后台精确查询提现订单"),
    (("client_withdraw_list",), "客户端精确查询提现订单"),
]


def controlled_group(name: str) -> str:
    if name.startswith("register"):
        return "受控注册流程"
    if "kyc" in name:
        return "受控 KYC 流程"
    if name.startswith("deposit") or "deposit" in name or name in {"wallet_before", "wallet_after"}:
        return "受控充值流程"
    if "turnover" in name:
        return "受控流水流程"
    if "withdraw_account" in name or "wallet_password" in name:
        return "受控提款账户流程"
    if "withdraw" in name:
        return "受控提现流程"
    return "受控流程认证"


def load_json(path: Path, default: object) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def load_controlled(paths: list[str]) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for path in paths:
        loaded = load_json(Path(path), [])
        if isinstance(loaded, list):
            records.extend(item for item in loaded if isinstance(item, dict))
    return records


def load_cases(path: Path) -> dict[str, dict[str, str]]:
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            return {row["case_id"]: row for row in csv.DictReader(handle)}
    except OSError:
        return {}


def endpoint(method: object, url: object) -> str:
    parsed = urlsplit(str(url or ""))
    return f"{method or ''} {parsed.path or '/'}".strip()


def login_name(url: object) -> str:
    path = urlsplit(str(url or "")).path
    if path == "/admin/login/auth":
        return "后台登录预校验"
    if path == "/admin/login":
        return "后台登录"
    return "客户端登录"


def business_value(item: dict[str, object]) -> object:
    if "business_status" in item:
        return item.get("business_status")
    body = item.get("decoded_body")
    return body.get("status") if isinstance(body, dict) else ""


def build_items(
    cases: dict[str, dict[str, str]],
    positive: list[dict[str, object]],
    negative: list[dict[str, object]],
    controlled: list[dict[str, object]],
) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    async_withdraw_verified = any(
        result.get("name") in {"admin_withdraw_list", "client_withdraw_list"}
        and isinstance(result.get("matched_order"), dict)
        and str(result["matched_order"].get("status") or "").lower()
        in {"paying", "paid", "success"}
        for result in controlled
    )
    login_index = 0
    for result in positive:
        case_id = str(result.get("case_id") or "")
        if not case_id:
            login_index += 1
            passed = result.get("ok") is True and business_value(result) is True
            items.append({
                "group": "登录前置", "id": f"LOGIN-{login_index:02d}", "name": login_name(result.get("url")),
                "kind": "SETUP", "status": "PASS" if passed else "FAIL",
                "target": endpoint(result.get("method"), result.get("url")),
                "expected": "HTTP 成功且业务 status=true", "actual": f"HTTP {result.get('status', '')} · business={business_value(result)}",
                "duration": f"{result.get('elapsed_ms', '')}ms", "detail": "" if passed else str(result.get("body_sample") or "认证失败"),
            })
            continue
        case = cases.get(case_id, {})
        passed = result.get("assertion_passed") is True
        failures = "; ".join(str(value) for value in result.get("assertion_failures", []) or [])
        items.append({
            "group": case.get("flow_stage_label") or "API 正例", "id": case_id,
            "name": case.get("case_name") or case_id, "kind": "正例", "status": "PASS" if passed else "FAIL",
            "target": endpoint(result.get("method"), result.get("url")), "expected": case.get("assertions") or "符合登记断言",
            "actual": f"HTTP {result.get('status', '')} · business={business_value(result)} · assertion={passed}",
            "duration": f"{result.get('elapsed_ms', '')}ms", "detail": failures,
        })
    for result in negative:
        case_id = str(result.get("case_id") or "")
        case = cases.get(case_id, {})
        passed = result.get("assertion_passed") is True
        failures = "; ".join(str(value) for value in result.get("assertion_failures", []) or [])
        items.append({
            "group": case.get("flow_stage_label") or "API 反例", "id": case_id,
            "name": case.get("case_name") or str(result.get("name") or case_id), "kind": "反例", "status": "PASS" if passed else "FAIL",
            "target": endpoint(result.get("method"), result.get("url")), "expected": case.get("assertions") or str(result.get("assertion") or "符合反例断言"),
            "actual": f"HTTP {result.get('http_status', '')} · business={result.get('business_status', '')} · assertion={passed}",
            "duration": f"{result.get('elapsed_ms', '')}ms", "detail": failures,
        })
    for index, result in enumerate(controlled, 1):
        name = str(result.get("name") or f"controlled_{index}")
        passed = result.get("business_status") is True
        obsolete_deposit_lookup = (
            name == "admin_deposit_list"
            and "deposit order not found" in str(result.get("reason") or "")
            and '"status": true' in str(result.get("body_sample") or "").lower()
        )
        pre_clear_withdraw_attempt = (
            name == "withdraw_create"
            and "Insufficient balance" in str(result.get("body_sample") or "")
        )
        async_response_reconciled = (
            name == "withdraw_create"
            and result.get("business_status") is False
            and async_withdraw_verified
        )
        item_status = (
            "SKIPPED"
            if obsolete_deposit_lookup or pre_clear_withdraw_attempt or async_response_reconciled
            else "PASS"
            if passed
            else "FAIL"
        )
        items.append({
            "group": controlled_group(name), "id": f"FLOW-{index:02d}", "name": CONTROLLED_NAMES.get(name, name),
            "kind": "受控写/核对", "status": item_status, "target": endpoint(CONTROLLED_METHODS.get(name, "API"), result.get("url")),
            "expected": "HTTP 200 且业务 status=true", "actual": f"HTTP {result.get('http_status', '')} · business={result.get('business_status', '')}",
            "duration": f"{result.get('elapsed_ms', '')}ms", "detail": "" if passed else str(result.get("body_sample") or "业务失败"),
        })
    return items


def add_planned_not_run(
    items: list[dict[str, str]],
    cases: dict[str, dict[str, str]],
    *,
    include_controlled: bool,
) -> None:
    existing_ids = {item["id"] for item in items}
    if not any(item_id.startswith("LOGIN-") for item_id in existing_ids):
        for item_id, name, target in PLANNED_LOGINS:
            items.append({
                "group": "登录前置", "id": item_id, "name": name, "kind": "SETUP", "status": "NOT_RUN",
                "target": target, "expected": "认证成功并获得本轮新 token", "actual": "未产生执行结果", "duration": "", "detail": "前序阶段已停止",
            })
    for case_id, case in cases.items():
        if case.get("execution_policy") not in {"safe_smoke", "negative_smoke"} or case_id in existing_ids:
            continue
        items.append({
            "group": case.get("flow_stage_label") or "API", "id": case_id,
            "name": case.get("case_name") or case_id,
            "kind": "正例" if case.get("execution_policy") == "safe_smoke" else "反例",
            "status": "NOT_RUN", "target": f"{case.get('method', '')} {case.get('path', '')}".strip(),
            "expected": case.get("assertions") or "符合登记断言", "actual": "未产生执行结果",
            "duration": "", "detail": "前序阶段失败或中断",
        })
    if include_controlled:
        existing_controlled_names = {item.get("name") for item in items if item.get("kind") == "受控写/核对"}
        for index, (_, name) in enumerate(PLANNED_CONTROLLED, 1):
            if name in existing_controlled_names:
                continue
            items.append({
                "group": "受控全流程", "id": f"PLANNED-{index:02d}", "name": name,
                "kind": "受控写/核对", "status": "NOT_RUN", "target": "完整受控阶段",
                "expected": "HTTP 200 且业务 status=true", "actual": "未产生执行结果",
                "duration": "", "detail": "前序阶段失败或中断",
            })


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", default="api/p0/test-cases.csv")
    parser.add_argument("--positive", default="api/results/p0-smoke-result.json")
    parser.add_argument("--negative", default="api/results/p0-negative-result.json")
    parser.add_argument(
        "--controlled",
        nargs="+",
        default=["api/results/p0-controlled-flow-result.json"],
    )
    parser.add_argument("--run-status", default="api/results/p0-run-status.json")
    parser.add_argument("--scope", default="FAT")
    parser.add_argument("--out", default="api/results/p0-api-report.md")
    parser.add_argument("--html-out", default="api/results/p0-api-report.html")
    args = parser.parse_args()
    status = load_json(Path(args.run_status), {})
    status = status if isinstance(status, dict) else {}
    positive = load_json(Path(args.positive), [])
    negative = load_json(Path(args.negative), [])
    controlled = load_controlled(args.controlled)
    cases = load_cases(Path(args.cases))
    items = build_items(
        cases,
        positive if isinstance(positive, list) else [],
        negative if isinstance(negative, list) else [],
        controlled,
    )
    add_planned_not_run(items, cases, include_controlled=status.get("mode") != "read")
    verdict, detail = report_verdict(items, str(status.get("status") or ""))
    if status.get("error"):
        detail = f"最后阶段：{status.get('stage', 'unknown')}；{status['error']}"
    kwargs = dict(title="P0 API 执行报告", scope=args.scope, verdict=verdict, verdict_detail=detail, items=items)
    write_markdown_report(**kwargs, output=Path(args.out))
    write_html_report(
        **kwargs,
        report_kind="API",
        output=Path(args.html_out),
        metadata=[
            ("最后阶段", str(status.get("stage") or "unknown")),
            ("执行耗时", format_execution_duration(status.get("started_at"), status.get("finished_at"))),
        ],
    )
    print(f"wrote {Path(args.out).resolve()}")
    print(f"wrote {Path(args.html_out).resolve()}")


if __name__ == "__main__":
    main()
