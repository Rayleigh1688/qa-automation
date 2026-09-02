#!/usr/bin/env python3
"""Run P0 API negative and guardrail cases.

These cases are separated from the read-only positive smoke set because their
expected result is usually business failure, auth rejection, or safe fallback.
They should not create valid payments, approvals, KYC records, or config changes.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import os
import time
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from datetime import datetime
from pathlib import Path

from p0_session import load_session
from types import ModuleType


def load_smoke_runner() -> ModuleType:
    path = Path(__file__).with_name("api-smoke-runner.py")
    spec = importlib.util.spec_from_file_location("api_smoke_runner", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


smoke = load_smoke_runner()


@dataclass(frozen=True)
class Case:
    case_id: str
    scenario_id: str
    domain: str
    flow: str
    name: str
    assertion: str


def load_cases(path: Path = Path("api/p0/test-cases.csv")) -> list[Case]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row.get("execution_policy") == "negative_smoke"]
    return [
        Case(
            row["case_id"], row["scenario_id"], row["domain"], row["flow_stage"],
            row["case_name"], row["assertions"],
        )
        for row in rows
    ]


CASES = load_cases()


def row(method: str, clean_url: str, base_var: str = "{{api_url}}") -> dict[str, str]:
    return {
        "priority": "P0_NEGATIVE",
        "method": method,
        "clean_url": clean_url,
        "suggested_base_var": base_var,
    }


def body_status(result: dict[str, object]) -> object:
    body = result.get("decoded_body")
    if isinstance(body, dict):
        return body.get("status")
    return None


def data_of(result: dict[str, object]) -> object:
    body = result.get("decoded_body")
    if isinstance(body, dict):
        return body.get("data")
    return None


def has_nested(value: object, path: str) -> bool:
    current = value
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return False
    return True


def assertion_result(result: dict[str, object], assertion: str) -> tuple[bool, list[str]]:
    failures: list[str] = []
    body = result.get("decoded_body")
    rules = [item for item in assertion.split(",") if item]

    for rule in rules:
        if rule == "http_200":
            if result.get("status") != 200:
                failures.append("http status is not 200")
        elif rule == "decoded":
            if body is None:
                failures.append("body is not decoded")
        elif rule == "no_5xx":
            status = result.get("status")
            if status == "ERROR" or not isinstance(status, int) or status >= 500:
                failures.append("response is 5xx or request error")
        elif rule == "business_not_true":
            if isinstance(body, dict) and body.get("status") is True:
                failures.append("business status is unexpectedly true")
        elif rule == "protected_rejected":
            if isinstance(body, dict) and body.get("status") is True:
                failures.append("protected endpoint returned business success")
            status = result.get("status")
            if status == "ERROR" or (isinstance(status, int) and status >= 500):
                failures.append("protected endpoint returned server error")
        elif rule == "no_token":
            if smoke.extract_token(result):
                failures.append("response unexpectedly contains token")
        elif rule.startswith("no_key:"):
            key = rule.removeprefix("no_key:")
            if has_nested(body, key):
                failures.append(f"response unexpectedly contains {key}")
        else:
            failures.append(f"unknown assertion {rule}")

    return not failures, failures


def record(case: Case, result: dict[str, object], extra: dict[str, object] | None = None) -> dict[str, object]:
    passed, failures = assertion_result(result, case.assertion)
    return {
        "case_id": case.case_id,
        "scenario_id": case.scenario_id,
        "domain": case.domain,
        "flow": case.flow,
        "name": case.name,
        "assertion": case.assertion,
        "assertion_passed": passed,
        "assertion_failures": failures,
        "method": result.get("method"),
        "url": result.get("url"),
        "http_status": result.get("status"),
        "business_status": body_status(result),
        "elapsed_ms": result.get("elapsed_ms"),
        "body_sample": result.get("body_sample", ""),
        **(extra or {}),
    }


def request_with_token(
    request_row: dict[str, str],
    args: argparse.Namespace,
    token_var: str,
    token_value: str,
    body: dict[str, object] | None = None,
) -> dict[str, object]:
    previous = os.environ.get(token_var)
    try:
        if token_value:
            os.environ[token_var] = token_value
        else:
            os.environ.pop(token_var, None)
        return smoke.request_once(request_row, args.timeout, args.insecure, body, args.body_format)
    finally:
        if previous is None:
            os.environ.pop(token_var, None)
        else:
            os.environ[token_var] = previous


def client_sms(args: argparse.Namespace, phone: str, reason: str = "login") -> dict[str, object]:
    return smoke.request_once(
        row("POST", "{{api_url}}/member/sms"),
        args.timeout,
        args.insecure,
        {
            "country_code": os.environ.get("CLIENT_COUNTRY_CODE", "63"),
            "phone": phone,
            "reason": reason,
        },
        args.body_format,
    )


def otp_id_from(result: dict[str, object]) -> str:
    data = data_of(result)
    if isinstance(data, dict):
        return str(data.get("id") or data.get("otp_id") or "")
    return ""


def token_from_latest_positive_result(path: str = "api/results/p0-smoke-result.json") -> str:
    result_path = Path(path)
    if not result_path.exists():
        return ""
    try:
        items = json.loads(result_path.read_text(encoding="utf-8"))
    except Exception:
        return ""
    if not isinstance(items, list):
        return ""
    for item in items:
        if isinstance(item, dict) and item.get("priority") == "LOGIN":
            token = smoke.extract_token(item)
            if token:
                return token
    return ""


def login_with_code(args: argparse.Namespace, phone: str, otp_id: str, code: str) -> dict[str, object]:
    return smoke.request_once(
        row("POST", "{{api_url}}/member/otp/login/v2"),
        args.timeout,
        args.insecure,
        {
            "country_code": os.environ.get("CLIENT_COUNTRY_CODE", "63"),
            "phone": phone,
            "otp_id": otp_id,
            "code": code,
            "i": os.environ.get("CLIENT_I", ""),
        },
        args.body_format,
    )


def choose_withdraw_account(args: argparse.Namespace) -> str:
    result = smoke.request_once(row("GET", "{{api_url}}/finance/account/list"), args.timeout, args.insecure)
    accounts = data_of(result)
    if not isinstance(accounts, list):
        return ""
    for account in accounts:
        if isinstance(account, dict) and account.get("id"):
            return str(account["id"])
    return ""


def choose_deposit_channel(args: argparse.Namespace) -> tuple[str, str, str]:
    result = smoke.request_once(
        row("GET", "{{api_url}}/finance/channel/list?mode=1&source=huawei"),
        args.timeout,
        args.insecure,
        None,
        args.body_format,
    )
    channels = data_of(result)
    if not isinstance(channels, list):
        return "", "", ""
    for channel in channels:
        if not isinstance(channel, dict):
            continue
        channel_id = channel.get("id")
        minimum = channel.get("min_amount")
        maximum = channel.get("max_amount")
        if channel_id is not None and minimum is not None and maximum is not None:
            return str(channel_id), str(minimum), str(maximum)
    return "", "", ""


def outside_limit_amount(limit: str, direction: str) -> str:
    try:
        value = Decimal(limit)
    except InvalidOperation:
        return ""
    amount = value - 1 if direction == "below" else value + 1
    return format(max(amount, Decimal("0")), "f")


def run_cases(args: argparse.Namespace) -> list[dict[str, object]]:
    phone = os.environ.get("CLIENT_PHONE", "")
    if not phone:
        raise SystemExit("CLIENT_PHONE is required")

    records: list[dict[str, object]] = []
    sms_result = client_sms(args, phone)
    otp_id = otp_id_from(sms_result) or os.environ.get("P0_NEGATIVE_OTP_ID", "invalid-otp-id")

    admin_token = os.environ.get("ADMIN_TOKEN", "")
    if admin_token:
        probe = smoke.request_once(
            row("GET", "{{admin_url}}/admin/me/detail", "{{admin_url}}"),
            args.timeout,
            args.insecure,
        )
        body = probe.get("decoded_body")
        if not (isinstance(body, dict) and body.get("status") is True):
            admin_token = ""
            os.environ.pop("ADMIN_TOKEN", None)
    if not admin_token and os.environ.get("ADMIN_EMAIL") and os.environ.get("ADMIN_PASSWORD") and os.environ.get("ADMIN_GOOGLE_CODE"):
        admin_login_results, admin_token = smoke.admin_login(args)
        if admin_token:
            os.environ["ADMIN_TOKEN"] = admin_token
        else:
            records.append(
                {
                    "case_id": "ADMIN-LOGIN",
                    "name": "后台登录前置失败",
                    "assertion_passed": False,
                    "assertion_failures": ["admin login failed"],
                    "body_sample": json.dumps([item.get("body_sample", "") for item in admin_login_results], ensure_ascii=False),
                }
            )

    case_by_id = {case.case_id: case for case in CASES}
    invalid_code = os.environ.get("P0_NEGATIVE_OTP", "000000")

    records.append(record(case_by_id["NTC-001"], login_with_code(args, phone, otp_id, invalid_code)))
    records.append(record(case_by_id["NTC-002"], login_with_code(args, phone, otp_id, "")))
    records.append(
        record(
            case_by_id["NTC-003"],
            request_with_token(row("GET", "{{api_url}}/member/detail"), args, "API_TOKEN", ""),
        )
    )

    # Never perform a second successful login here: it would invalidate the
    # shared P0 token. Reuse the session created by the single auth stage.
    client_token = os.environ.get("API_TOKEN", "") or token_from_latest_positive_result()
    if not client_token:
        raise SystemExit("client token is required; run python3 scripts/run-api-tests.py p0 first or provide API_TOKEN")
    os.environ["API_TOKEN"] = client_token

    records.append(
        record(
            case_by_id["NTC-004"],
            request_with_token(row("GET", "{{api_url}}/member/kyc/detail"), args, "API_TOKEN", ""),
        )
    )
    records.append(
        record(
            case_by_id["NTC-005"],
            request_with_token(row("GET", "{{api_url}}/finance/wallet"), args, "API_TOKEN", "invalid-token"),
        )
    )
    records.append(
        record(
            case_by_id["NTC-006"],
            smoke.request_once(
                row("GET", "{{api_url}}/member/game/listRw?page=-1&page_size=-1&venues=not-exist&sort=bad"),
                args.timeout,
                args.insecure,
            ),
        )
    )
    records.append(
        record(
            case_by_id["NTC-008"],
            smoke.request_once(
                row("GET", "{{api_url}}/finance/payment/deposit?pid=99999999&amount=10&device=web&source=huawei&cashback_flag=0&rotation_flag=0"),
                args.timeout,
                args.insecure,
            ),
        )
    )
    low_amount = os.environ.get("P0_NEGATIVE_WITHDRAW_AMOUNT", "1")
    withdraw_account_id = choose_withdraw_account(args)
    if not withdraw_account_id:
        raise SystemExit("NTC-009 requires a valid bound withdraw account on CLIENT_PHONE")
    records.append(
        record(
            case_by_id["NTC-009"],
            smoke.request_once(
                row("GET", f"{{{{api_url}}}}/finance/payment/withdraw?amount={low_amount}&account_id={withdraw_account_id}"),
                args.timeout,
                args.insecure,
            ),
            {"account_id": withdraw_account_id, "amount": low_amount},
        )
    )
    records.append(
        record(
            case_by_id["NTC-010"],
            smoke.request_once(row("GET", "{{api_url}}/finance/withdraw/list?time_flag=-999&page=-1&page_size=-1"), args.timeout, args.insecure),
        )
    )

    records.append(
        record(
            case_by_id["NTC-013"],
            smoke.request_once(
                row("POST", "{{api_url}}/member/kyc/insert"),
                args.timeout,
                args.insecure,
                {},
                args.body_format,
            ),
        )
    )
    if args.include_deposit_limit_contract:
        deposit_channel_id, min_amount, max_amount = choose_deposit_channel(args)
        if not deposit_channel_id:
            raise SystemExit("unable to find a deposit channel with min_amount and max_amount")
        for case_id, amount, bound in [
            ("NTC-014", outside_limit_amount(min_amount, "below"), "min_amount"),
            ("NTC-015", outside_limit_amount(max_amount, "above"), "max_amount"),
        ]:
            records.append(
                record(
                    case_by_id[case_id],
                    smoke.request_once(
                        row(
                            "GET",
                            "{{api_url}}/finance/payment/deposit?"
                            f"pid={deposit_channel_id}&amount={amount}&device=web&source=huawei&cashback_flag=0&rotation_flag=0",
                        ),
                        args.timeout,
                        args.insecure,
                        None,
                        args.body_format,
                    ),
                    {"channel_id": deposit_channel_id, "amount": amount, "limit": bound},
                )
            )
    records.append(
        record(
            case_by_id["NTC-016"],
            smoke.request_once(
                row("GET", "{{api_url}}/finance/deposit/list?status=INVALID&time_flag=-999&page=-1&page_size=999999"),
                args.timeout,
                args.insecure,
            ),
        )
    )

    if admin_token:
        records.append(
            record(
                case_by_id["NTC-011"],
                request_with_token(row("GET", "{{admin_url}}/admin/me/detail", "{{admin_url}}"), args, "ADMIN_TOKEN", "invalid-admin-token"),
            )
        )
        now = int(time.time())
        records.append(
            record(
                case_by_id["NTC-012"],
                smoke.request_once(
                    row("POST", "{{admin_url}}/admin/finance/deposit/risk/list", "{{admin_url}}"),
                    args.timeout,
                    args.insecure,
                    {"status": "PENDING", "start_time": now, "end_time": now - 86400, "page": 1, "page_size": 10},
                    args.body_format,
                ),
            )
        )
    else:
        for case_id in ["NTC-011", "NTC-012"]:
            case = case_by_id[case_id]
            records.append(
                {
                    "case_id": case.case_id,
                    "scenario_id": case.scenario_id,
                    "domain": case.domain,
                    "flow": case.flow,
                    "name": case.name,
                    "assertion_passed": False,
                    "assertion_failures": ["admin login prerequisite failed"],
                }
            )

    return records


def table(rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(rows[0]) + " |",
        "| " + " | ".join("---" for _ in rows[0]) + " |",
    ]
    for row in rows[1:]:
        lines.append("| " + " | ".join(item.replace("|", "\\|") for item in row) + " |")
    return "\n".join(lines)


def body_hint(item: dict[str, object]) -> str:
    return str(item.get("body_sample", ""))[:120].replace("\n", " ")


def write_report(records: list[dict[str, object]], args: argparse.Namespace) -> None:
    passed = [item for item in records if item.get("assertion_passed") is True]
    failed = [item for item in records if item.get("assertion_passed") is False]
    summary = [
        ["指标", "数量"],
        ["P0 反例用例", str(len(records))],
        ["断言通过", str(len(passed))],
        ["断言失败", str(len(failed))],
    ]
    detail = [["用例ID", "场景ID", "流程", "领域", "用例", "HTTP", "业务状态", "断言", "耗时", "摘要"]]
    for item in records:
        failures = item.get("assertion_failures") or []
        detail.append(
            [
                str(item.get("case_id", "")),
                str(item.get("scenario_id", "")),
                str(item.get("flow", "")),
                str(item.get("domain", "")),
                str(item.get("name", "")),
                str(item.get("http_status", "")),
                str(item.get("business_status", "")),
                "PASS" if item.get("assertion_passed") else "; ".join(str(failure) for failure in failures),
                f"{item.get('elapsed_ms', '')}ms" if item.get("elapsed_ms") is not None else "",
                body_hint(item),
            ]
        )

    report = f"""# P0 API Negative Report

生成时间：`{datetime.now().astimezone().isoformat()}`

## 执行范围

- 环境：{args.scope}
- 执行器：`scripts/api-p0-negative-runner.py`
- 结果文件：`{args.out}`
- 请求编码：{args.body_format.upper()}
- TLS：测试环境临时使用 `--insecure`

这组用例验证 P0 主流程的反例和保护性规则，预期结果通常是业务失败、鉴权失败或稳定降级，不应创建有效充值、提现、审批或 KYC 记录。

## 结果概览

{table(summary)}

## 用例明细

{table(detail)}
"""
    Path(args.report).write_text(report, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", default=os.environ.get("ENV_FILE", ".env.fat"))
    parser.add_argument("--timeout", type=float, default=10)
    parser.add_argument("--insecure", action="store_true")
    parser.add_argument("--body-format", choices=["json", "cbor"], default="cbor")
    parser.add_argument("--out", default="api/results/p0-negative-result.json")
    parser.add_argument("--report", default="api/results/p0-negative-report.md")
    parser.add_argument("--scope", default="FAT")
    parser.add_argument("--include-deposit-limit-contract", action="store_true")
    parser.add_argument("--session-in", default="", help="Reuse ignored P0 client/admin tokens")
    args = parser.parse_args()

    smoke.load_env_file(Path(args.env))
    if args.session_in:
        load_session(args.session_in, os.environ.get("CLIENT_PHONE", ""))
    records = run_cases(args)
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(records, args)
    print(f"wrote {output.resolve()}")
    print(f"wrote {Path(args.report).resolve()}")

    failed = [item for item in records if item.get("assertion_passed") is not True]
    print(f"ok {len(records) - len(failed)}/{len(records)}")
    for item in records:
        print(f"{item.get('case_id')} pass={item.get('assertion_passed')} http={item.get('http_status')} business={item.get('business_status')} {item.get('name')}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
