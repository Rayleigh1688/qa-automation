#!/usr/bin/env python3
"""Run controlled write-flow API probes in FAT.

This runner is intentionally separate from the read-only P0 smoke runner.
Use it only for test environments and explicit controlled write probes.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import importlib.util
import json
import os
import struct
import time
from pathlib import Path
from types import ModuleType
from urllib.parse import parse_qs, urlencode, urlparse


def load_smoke_runner() -> ModuleType:
    path = Path(__file__).with_name("api-smoke-runner.py")
    spec = importlib.util.spec_from_file_location("api_smoke_runner", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


smoke = load_smoke_runner()


def row(method: str, clean_url: str, base_var: str = "{{api_url}}") -> dict[str, str]:
    return {
        "priority": "CONTROLLED",
        "method": method,
        "clean_url": clean_url,
        "suggested_base_var": base_var,
    }


def business_ok(result: dict[str, object]) -> bool:
    body = result.get("decoded_body")
    return isinstance(body, dict) and body.get("status") is True


def current_totp(secret: str, timestamp: int | None = None, step: int = 30, digits: int = 6) -> str:
    normalized = secret.strip().replace(" ", "").upper()
    padded = normalized + "=" * (-len(normalized) % 8)
    key = base64.b32decode(padded, casefold=True)
    counter = int((timestamp or time.time()) // step)
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(code % (10**digits)).zfill(digits)


def approval_code(args: argparse.Namespace) -> str:
    explicit = args.approval_code or os.environ.get("ADMIN_APPROVAL_CODE", "")
    if explicit:
        return explicit
    secret = os.environ.get("ADMIN_APPROVAL_TOTP_SECRET", "")
    return current_totp(secret) if secret else ""


def add_approval_code(body: dict[str, object], args: argparse.Namespace) -> dict[str, object]:
    code = approval_code(args)
    if code:
        value = int(code) if str(code).isdigit() else code
        body["google_code"] = value
    return body


def now_window(days: int = 2) -> tuple[int, int]:
    end_time = int(time.time())
    return end_time - days * 86400, end_time + 300


def data_of(result: dict[str, object]) -> object:
    body = result.get("decoded_body")
    if isinstance(body, dict):
        return body.get("data")
    return None


def list_rows(data: object) -> list[dict[str, object]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        rows = data.get("d") or data.get("data") or data.get("list")
        if isinstance(rows, list):
            return [item for item in rows if isinstance(item, dict)]
    return []


def result_record(name: str, result: dict[str, object]) -> dict[str, object]:
    data = data_of(result)
    if isinstance(data, dict) and "pay_url" in data:
        data = {key: ("<redacted pay_url>" if key == "pay_url" else value) for key, value in data.items()}
    return {
        "name": name,
        "url": result.get("url"),
        "http_status": result.get("status"),
        "business_status": (result.get("decoded_body") or {}).get("status")
        if isinstance(result.get("decoded_body"), dict)
        else None,
        "data": data,
        "elapsed_ms": result.get("elapsed_ms"),
        "body_sample": result.get("body_sample"),
    }


def extract_deposit_external_order_id(data: object) -> str:
    if not isinstance(data, dict):
        return ""
    explicit = data.get("external_order_id")
    if explicit:
        return str(explicit)
    pay_url = str(data.get("pay_url") or "")
    if not pay_url:
        return ""
    query = parse_qs(urlparse(pay_url).query)
    return (query.get("checkoutId") or query.get("external_order_id") or [""])[0]


def admin_login(args: argparse.Namespace) -> list[dict[str, object]]:
    login_results, token = smoke.admin_login(args)
    if not token:
        raise SystemExit("admin login failed; cannot run admin approval probes")
    os.environ["ADMIN_TOKEN"] = token
    return [result_record("admin_auth", item) for item in login_results[:1]] + [
        result_record("admin_login", item) for item in login_results[1:]
    ]


def client_login(args: argparse.Namespace) -> list[dict[str, object]]:
    login_results, token = smoke.client_login(args)
    if not token:
        raise SystemExit("client login failed; cannot run controlled write probes")
    os.environ["API_TOKEN"] = token
    return [result_record("client_sms", item) for item in login_results[:1]] + [
        result_record("client_login", item) for item in login_results[1:]
    ]


def query_wallet(args: argparse.Namespace, name: str) -> dict[str, object]:
    result = smoke.request_once(
        row("GET", "{{api_url}}/finance/wallet"),
        args.timeout,
        args.insecure,
    )
    return result_record(name, result)


def register_new_user(args: argparse.Namespace) -> list[dict[str, object]]:
    phone = args.register_phone or os.environ.get("REGISTER_PHONE") or f"99{int(time.time()) % 100000000:08d}"
    password = os.environ.get("REGISTER_PASSWORD", "Qa123456")
    code = os.environ.get("REGISTER_OTP") or os.environ.get("CLIENT_OTP")
    if not code:
        raise SystemExit("REGISTER_OTP or CLIENT_OTP is required for registration")

    sms_body = {
        "country_code": os.environ.get("REGISTER_COUNTRY_CODE", os.environ.get("CLIENT_COUNTRY_CODE", "63")),
        "phone": phone,
        "reason": os.environ.get("REGISTER_SMS_REASON", ""),
    }
    sms_result = smoke.request_once(
        row("POST", "{{api_url}}/member/sms"),
        args.timeout,
        args.insecure,
        sms_body,
        args.body_format,
    )
    otp_id = ""
    data = data_of(sms_result)
    if isinstance(data, dict):
        otp_id = str(data.get("id") or data.get("otp_id") or "")

    records = [result_record("register_sms", sms_result)]
    if not otp_id:
        records.append({"name": "register", "skipped": True, "reason": "missing otp_id", "phone": phone})
        return records

    register_body = {
        "otp_id": otp_id,
        "code": code,
        "password": password,
        "invite_code": os.environ.get("REGISTER_INVITE_CODE", ""),
        "i": os.environ.get("REGISTER_I", ""),
    }
    register_result = smoke.request_once(
        row("POST", "{{api_url}}/member/register"),
        args.timeout,
        args.insecure,
        register_body,
        args.body_format,
    )
    register_record = result_record("register", register_result)
    register_record["phone"] = phone
    records.append(register_record)
    return records


def choose_deposit_channel(args: argparse.Namespace) -> tuple[str, str]:
    channels_result = smoke.request_once(
        row("GET", "{{api_url}}/finance/channel/list?mode=1&source=huawei"),
        args.timeout,
        args.insecure,
    )
    channels = data_of(channels_result)
    if not isinstance(channels, list) or not channels:
        raise SystemExit("no deposit channels available")

    if args.deposit_pid:
        for channel in channels:
            if isinstance(channel, dict) and str(channel.get("id")) == args.deposit_pid:
                amount = args.deposit_amount or str(channel.get("min_amount") or "1")
                return args.deposit_pid, amount
        return args.deposit_pid, args.deposit_amount or "1"

    sorted_channels = sorted(
        [item for item in channels if isinstance(item, dict) and item.get("id")],
        key=lambda item: float(item.get("min_amount") or 999999),
    )
    channel = sorted_channels[0]
    amount_limits = channel.get("amount_limit")
    amount = ""
    if isinstance(amount_limits, list) and amount_limits:
        amount = str(amount_limits[0])
    return str(channel["id"]), args.deposit_amount or amount or str(channel.get("min_amount") or "1")


def run_deposit(args: argparse.Namespace) -> list[dict[str, object]]:
    pid, amount = choose_deposit_channel(args)
    query = f"pid={pid}&amount={amount}&device=web&source=huawei&cashback_flag=0&rotation_flag=0"
    if args.deposit_product_id:
        query += f"&product_id={args.deposit_product_id}"
    deposit_result = smoke.request_once(
        row("GET", "{{api_url}}/finance/payment/deposit?" + query),
        args.timeout,
        args.insecure,
    )
    record = result_record("deposit_create", deposit_result)
    deposit_data = data_of(deposit_result)
    record["pid"] = pid
    record["amount"] = amount
    external_order_id = args.deposit_external_order_id or extract_deposit_external_order_id(deposit_data)
    if external_order_id:
        record["external_order_id"] = external_order_id
    return [record]


def find_deposit_order(args: argparse.Namespace, deposit_id: str = "") -> tuple[dict[str, object], dict[str, object] | None]:
    start_time, end_time = now_window()
    params = {
        "status": args.deposit_status or "PENDING",
        "start_time": start_time,
        "end_time": end_time,
        "page": 1,
        "page_size": 10,
    }
    if deposit_id:
        params["id"] = deposit_id
    result = smoke.request_once(
        row("POST", "{{admin_url}}/admin/finance/deposit/risk/list", "{{admin_url}}"),
        args.timeout,
        args.insecure,
        params,
        args.body_format,
    )
    result["url"] = result.get("url", "") + "?" + urlencode(params)
    rows = list_rows(data_of(result))
    target = None
    if deposit_id:
        target = next((item for item in rows if str(item.get("id")) == str(deposit_id)), None)
    if target is None and rows:
        target = rows[0]
    record = result_record("admin_deposit_risk_list", result)
    record["matched_order"] = target
    return record, target


def approve_deposit(
    args: argparse.Namespace,
    deposit_order: dict[str, object] | None,
    fallback_id: str = "",
    fallback_external_order_id: str = "",
) -> list[dict[str, object]]:
    if not deposit_order and not fallback_id:
        return [{"name": "admin_deposit_manual_success", "skipped": True, "reason": "no pending deposit order found"}]
    deposit_id = str((deposit_order or {}).get("id") or fallback_id)
    if not deposit_id:
        return [{"name": "admin_deposit_manual_success", "skipped": True, "reason": "matched deposit has no id"}]
    external_order_id = str((deposit_order or {}).get("external_order_id") or args.deposit_external_order_id or fallback_external_order_id)
    body: dict[str, object] = {"id": deposit_id, "desc": args.approval_desc}
    if external_order_id:
        body["external_order_id"] = external_order_id
    body = add_approval_code(body, args)
    result = smoke.request_once(
        row("POST", "{{admin_url}}/admin/finance/deposit/manual/success", "{{admin_url}}"),
        args.timeout,
        args.insecure,
        body,
        args.body_format,
    )
    record = result_record("admin_deposit_manual_success", result)
    record["deposit_id"] = deposit_id
    if external_order_id:
        record["external_order_id"] = external_order_id
    return [record]


def choose_withdraw_account(args: argparse.Namespace) -> tuple[str, str, dict[str, object] | None]:
    if args.withdraw_account_id:
        return args.withdraw_account_id, args.withdraw_amount or "1", None
    accounts_result = smoke.request_once(
        row("GET", "{{api_url}}/finance/account/list"),
        args.timeout,
        args.insecure,
    )
    accounts = data_of(accounts_result)
    if not isinstance(accounts, list) or not accounts:
        raise SystemExit("no withdraw accounts available")
    usable = [item for item in accounts if isinstance(item, dict) and item.get("id") and item.get("status") == 1]
    if not usable:
        raise SystemExit("no usable withdraw accounts available")
    account = sorted(usable, key=lambda item: float(item.get("min_amount") or 999999))[0]
    amount_limits = account.get("amount_limit")
    amount = ""
    if isinstance(amount_limits, list) and amount_limits:
        amount = str(amount_limits[0])
    return str(account["id"]), args.withdraw_amount or amount or str(account.get("min_amount") or "1"), account


def run_withdraw(args: argparse.Namespace) -> list[dict[str, object]]:
    account_id, amount, account = choose_withdraw_account(args)
    withdraw_result = smoke.request_once(
        row("GET", f"{{{{api_url}}}}/finance/payment/withdraw?amount={amount}&account_id={account_id}"),
        args.timeout,
        args.insecure,
    )
    record = result_record("withdraw_create", withdraw_result)
    record["account_id"] = account_id
    record["amount"] = amount
    if account:
        record["selected_account"] = account
    return [record]


def find_withdraw_order(args: argparse.Namespace, withdraw_id: str = "") -> tuple[dict[str, object], dict[str, object] | None]:
    start_time, end_time = now_window()
    params = {
        "status": args.withdraw_status or "under_review",
        "start_time": start_time,
        "end_time": end_time,
        "page": 1,
        "page_size": 10,
    }
    if withdraw_id:
        params["id"] = withdraw_id
    result = smoke.request_once(
        row("POST", "{{admin_url}}/admin/finance/withdraw/risk/audit/list", "{{admin_url}}"),
        args.timeout,
        args.insecure,
        params,
        args.body_format,
    )
    result["url"] = result.get("url", "") + "?" + urlencode(params)
    rows = list_rows(data_of(result))
    target = None
    if withdraw_id:
        target = next((item for item in rows if str(item.get("id")) == str(withdraw_id)), None)
    if target is None and rows:
        target = rows[0]
    record = result_record("admin_withdraw_risk_audit_list", result)
    record["matched_order"] = target
    return record, target


def approve_withdraw(args: argparse.Namespace, withdraw_order: dict[str, object] | None) -> list[dict[str, object]]:
    if not withdraw_order:
        return [{"name": "admin_withdraw_agree", "skipped": True, "reason": "no under_review withdraw order found"}]
    withdraw_id = str(withdraw_order.get("id") or "")
    if not withdraw_id:
        return [{"name": "admin_withdraw_agree", "skipped": True, "reason": "matched withdraw has no id"}]
    body = add_approval_code({"id": withdraw_id, "desc": args.approval_desc}, args)
    agree_result = smoke.request_once(
        row("POST", "{{admin_url}}/admin/finance/withdraw/agree", "{{admin_url}}"),
        args.timeout,
        args.insecure,
        body,
        args.body_format,
    )
    records = [result_record("admin_withdraw_agree", agree_result)]
    records[0]["withdraw_id"] = withdraw_id
    if args.withdraw_mark_success:
        success_result = smoke.request_once(
            row("POST", "{{admin_url}}/admin/finance/withdraw/success", "{{admin_url}}"),
            args.timeout,
            args.insecure,
            {
                **body,
                "external_order_id": args.withdraw_external_order_id,
            },
            args.body_format,
        )
        success_record = result_record("admin_withdraw_success", success_result)
        success_record["withdraw_id"] = withdraw_id
        records.append(success_record)
    return records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", default=".env")
    parser.add_argument("--timeout", type=float, default=10)
    parser.add_argument("--insecure", action="store_true")
    parser.add_argument("--body-format", choices=["json", "cbor"], default="cbor")
    parser.add_argument("--out", default="api/results/controlled-write-result.json")
    parser.add_argument("--register", action="store_true")
    parser.add_argument("--deposit", action="store_true")
    parser.add_argument("--approve-deposit", action="store_true")
    parser.add_argument("--withdraw", action="store_true")
    parser.add_argument("--approve-withdraw", action="store_true")
    parser.add_argument("--main-positive-flow", action="store_true")
    parser.add_argument("--register-phone", default="")
    parser.add_argument("--deposit-pid", default="")
    parser.add_argument("--deposit-amount", default="")
    parser.add_argument("--deposit-product-id", default="")
    parser.add_argument("--deposit-external-order-id", default="")
    parser.add_argument("--deposit-status", default="")
    parser.add_argument("--withdraw-account-id", default="")
    parser.add_argument("--withdraw-amount", default="")
    parser.add_argument("--withdraw-status", default="")
    parser.add_argument("--withdraw-mark-success", action="store_true")
    parser.add_argument("--withdraw-external-order-id", default="")
    parser.add_argument("--approval-desc", default="p0 automation")
    parser.add_argument("--approval-code", default="")
    args = parser.parse_args()

    smoke.load_env_file(Path(args.env))
    records: list[dict[str, object]] = []

    if args.main_positive_flow:
        args.deposit = True
        args.approve_deposit = True
        args.withdraw = True
        args.approve_withdraw = True

    if args.register:
        records.extend(register_new_user(args))

    if args.deposit or args.withdraw:
        records.extend(client_login(args))
        records.append(query_wallet(args, "wallet_before"))
    if args.approve_deposit or args.approve_withdraw:
        records.extend(admin_login(args))
    if args.deposit:
        deposit_records = run_deposit(args)
        records.extend(deposit_records)
        deposit_data = deposit_records[-1].get("data")
        deposit_id = str(deposit_data.get("id") or deposit_data.get("order_id") or "") if isinstance(deposit_data, dict) else ""
        deposit_external_order_id = str(deposit_records[-1].get("external_order_id") or "")
        if args.approve_deposit:
            list_record, order = find_deposit_order(args, deposit_id)
            records.append(list_record)
            records.extend(approve_deposit(args, order, deposit_id, deposit_external_order_id))
    if args.withdraw:
        withdraw_records = run_withdraw(args)
        records.extend(withdraw_records)
        withdraw_data = withdraw_records[-1].get("data")
        withdraw_id = str(withdraw_data.get("id") or "") if isinstance(withdraw_data, dict) else ""
        if args.approve_withdraw:
            list_record, order = find_withdraw_order(args, withdraw_id)
            records.append(list_record)
            records.extend(approve_withdraw(args, order))
    if args.deposit or args.withdraw:
        records.append(query_wallet(args, "wallet_after"))

    output = Path(args.out)
    output.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {output.resolve()}")
    for item in records:
        status = item.get("business_status")
        print(f"{item.get('name')} http={item.get('http_status')} business={status} url={item.get('url', '')}")


if __name__ == "__main__":
    main()
