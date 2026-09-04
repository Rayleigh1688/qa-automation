#!/usr/bin/env python3
"""Run controlled write-flow API probes in test environments.

This runner is intentionally separate from the read-only P0 smoke runner.
Use it only for test environments and explicit controlled write probes.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import mimetypes
import os
import ssl
import sys
import time
import uuid
from decimal import Decimal, InvalidOperation
from pathlib import Path
from types import ModuleType
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
PHONE_CURSOR_DIR = ROOT_DIR / "api/local-state"
DEFAULT_REGISTER_PHONE_START = "9000000001"
DEFAULT_WITHDRAW_AMOUNT = "100"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from p0_report_template import report_verdict, write_html_report
from totp import current_totp


def load_smoke_runner() -> ModuleType:
    path = Path(__file__).with_name("api-smoke-runner.py")
    spec = importlib.util.spec_from_file_location("api_smoke_runner", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


smoke = load_smoke_runner()


OPERATION_FLAGS = {
    "register": "register",
    "kyc-submit": "submit_kyc",
    "kyc-approve": "approve_kyc",
    "deposit-create": "deposit",
    "deposit-check-client": "check_client_deposit_list",
    "deposit-check-admin": "check_admin_deposit_list",
    "deposit-approve": "approve_deposit",
    "withdraw-create": "withdraw",
    "withdraw-account-prepare": "prepare_withdraw_account",
    "withdraw-check-client": "check_client_withdraw_list",
    "withdraw-check-admin": "check_admin_withdraw_list",
    "withdraw-approve": "approve_withdraw",
    "turnover-clear": "clear_turnover",
}

CLIENT_OPERATION_LANES = {
    "kyc-submit": "KYC_CLIENT",
    "kyc-approve": "KYC_CLIENT",
    "deposit-create": "WRITE_CLIENT",
    "deposit-check-client": "WRITE_CLIENT",
    "withdraw-create": "WITHDRAW_CLIENT",
    "withdraw-check-client": "WITHDRAW_CLIENT",
}

ACTIVE_ARGS: argparse.Namespace | None = None
ACTIVE_RECORDS: list[dict[str, object]] | None = None
OPERATION_REPORT_WRITTEN = False
LAST_APPROVAL_CODE = ""


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


def approval_code(args: argparse.Namespace) -> str:
    global LAST_APPROVAL_CODE
    explicit = args.approval_code
    if explicit:
        if explicit == LAST_APPROVAL_CODE:
            raise SystemExit("the explicit approval code cannot be reused for another approval action")
        LAST_APPROVAL_CODE = explicit
        return explicit
    secret = os.environ.get("ADMIN_APPROVAL_TOTP_SECRET", "")
    algorithm = os.environ.get("ADMIN_APPROVAL_TOTP_ALGORITHM", "SHA1")
    if secret:
        seconds_remaining = 30 - (int(time.time()) % 30)
        if seconds_remaining <= 3:
            time.sleep(seconds_remaining + 1)
        code = current_totp(secret, algorithm=algorithm)
        if code == LAST_APPROVAL_CODE:
            seconds_remaining = 30 - (int(time.time()) % 30)
            time.sleep(seconds_remaining + 1)
            code = current_totp(secret, algorithm=algorithm)
        LAST_APPROVAL_CODE = code
        return code
    fallback = os.environ.get("ADMIN_APPROVAL_CODE", "")
    if fallback:
        if fallback == LAST_APPROVAL_CODE:
            raise SystemExit(
                "ADMIN_APPROVAL_CODE is a single-use fallback and cannot be reused; configure ADMIN_APPROVAL_TOTP_SECRET"
            )
        LAST_APPROVAL_CODE = fallback
    return fallback


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
    data = redact_payload(data_of(result))
    decoded = redact_payload(result.get("decoded_body"))
    return {
        "name": name,
        "url": result.get("url"),
        "http_status": result.get("status"),
        "business_status": (result.get("decoded_body") or {}).get("status")
        if isinstance(result.get("decoded_body"), dict)
        else None,
        "data": data,
        "elapsed_ms": result.get("elapsed_ms"),
        "body_sample": json.dumps(decoded, ensure_ascii=False)[:2000] if decoded is not None else "",
    }


def redact_payload(value: object, key: str = "") -> object:
    sensitive_keys = {"token", "password", "code", "google_code", "otp", "pay_url"}
    if key.lower() in sensitive_keys:
        return "<redacted>"
    if isinstance(value, dict):
        return {str(item_key): redact_payload(item_value, str(item_key)) for item_key, item_value in value.items()}
    if isinstance(value, list):
        return [redact_payload(item) for item in value]
    return value


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
    if os.environ.get("ADMIN_TOKEN"):
        probe = smoke.request_once(
            row("GET", "{{admin_url}}/admin/me/detail", "{{admin_url}}"),
            args.timeout,
            args.insecure,
        )
        if business_ok(probe):
            return [result_record("admin_token_reuse", probe)]
        os.environ.pop("ADMIN_TOKEN", None)
    login_results, token = smoke.admin_login(args)
    if not token:
        raise SystemExit("admin login failed; cannot run admin approval probes")
    os.environ["ADMIN_TOKEN"] = token
    return [result_record("admin_auth", item) for item in login_results[:1]] + [
        result_record("admin_login", item) for item in login_results[1:]
    ]


def client_login(args: argparse.Namespace) -> list[dict[str, object]]:
    # Controlled phases may run back-to-back on the same FAT account. Reuse a
    # freshly obtained token when supplied, but validate it before any write so
    # repeated SMS requests do not trigger the test-environment phone limiter.
    if os.environ.get("API_TOKEN"):
        probe = smoke.request_once(
            row("GET", "{{api_url}}/member/detail"),
            args.timeout,
            args.insecure,
        )
        if business_ok(probe):
            return [result_record("client_token_reuse", probe)]
        os.environ.pop("API_TOKEN", None)

    login_results, token = smoke.client_login(args)
    if not token:
        raise SystemExit("client login failed; cannot run controlled write probes")
    os.environ["API_TOKEN"] = token
    records = []
    for item in login_results:
        url = str(item.get("url") or "")
        if url.endswith("/member/sms"):
            name = "client_sms"
        elif "/member/otp/login" in url:
            name = "client_otp_login"
        else:
            name = "client_password_login"
        records.append(result_record(name, item))
    return records


def relabel(records: list[dict[str, object]], prefix: str) -> list[dict[str, object]]:
    renamed = []
    for record in records:
        item = dict(record)
        item["name"] = f"{prefix}_{item.get('name', '')}"
        renamed.append(item)
    return renamed


def use_withdraw_client(
    args: argparse.Namespace,
) -> tuple[str | None, str | None, str | None, str | None]:
    phone = args.withdraw_client_phone or os.environ.get("WITHDRAW_CLIENT_PHONE", "")
    if not phone:
        return None, None, None, None
    previous_phone = os.environ.get("CLIENT_PHONE")
    previous_password = os.environ.get("CLIENT_PASSWORD")
    previous_otp = os.environ.get("CLIENT_OTP")
    previous_token = os.environ.get("API_TOKEN")
    os.environ["CLIENT_PHONE"] = phone
    password = os.environ.get("WITHDRAW_CLIENT_PASSWORD") or os.environ.get("WRITE_CLIENT_PASSWORD", "")
    if password:
        os.environ["CLIENT_PASSWORD"] = password
    otp = args.withdraw_client_otp or os.environ.get("WITHDRAW_CLIENT_OTP", "")
    if otp:
        os.environ["CLIENT_OTP"] = otp
    os.environ.pop("API_TOKEN", None)
    return previous_phone, previous_password, previous_otp, previous_token


def restore_client(
    previous_phone: str | None,
    previous_password: str | None,
    previous_otp: str | None,
    previous_token: str | None,
) -> None:
    if previous_phone is None:
        os.environ.pop("CLIENT_PHONE", None)
    else:
        os.environ["CLIENT_PHONE"] = previous_phone
    if previous_password is None:
        os.environ.pop("CLIENT_PASSWORD", None)
    else:
        os.environ["CLIENT_PASSWORD"] = previous_password
    if previous_otp is None:
        os.environ.pop("CLIENT_OTP", None)
    else:
        os.environ["CLIENT_OTP"] = previous_otp
    if previous_token is None:
        os.environ.pop("API_TOKEN", None)
    else:
        os.environ["API_TOKEN"] = previous_token


def apply_primary_client_override(args: argparse.Namespace) -> None:
    if args.use_register_phone:
        phone = load_phone_cursor(phone_cursor_path(args.env))
        password = os.environ.get("REGISTER_PASSWORD", "")
        if not phone or not password:
            raise SystemExit("register phone cursor and REGISTER_PASSWORD are required")
        args.client_phone = phone
        os.environ["CLIENT_PHONE"] = phone
        os.environ["CLIENT_PASSWORD"] = password
        otp = os.environ.get("REGISTER_OTP", "")
        if otp:
            os.environ["CLIENT_OTP"] = otp
        return
    phone = args.client_phone or os.environ.get("WRITE_CLIENT_PHONE", "")
    write_phone = os.environ.get("WRITE_CLIENT_PHONE", "")
    normalized_phone = "".join(character for character in phone if character.isdigit())
    normalized_write_phone = "".join(character for character in write_phone if character.isdigit())
    use_write_lane = bool(
        not args.client_phone
        or (normalized_phone and normalized_phone == normalized_write_phone)
    )
    password = os.environ.get("WRITE_CLIENT_PASSWORD", "") if use_write_lane else ""
    otp = args.client_otp or os.environ.get("WRITE_CLIENT_OTP", "")
    if phone:
        os.environ["CLIENT_PHONE"] = phone
    if password:
        os.environ["CLIENT_PASSWORD"] = password
    if otp:
        os.environ["CLIENT_OTP"] = otp


def apply_operation_client_lane(args: argparse.Namespace) -> None:
    prefix = CLIENT_OPERATION_LANES.get(args.operation, "")
    if not prefix:
        return
    phone = os.environ.get(f"{prefix}_PHONE", "")
    password = os.environ.get(f"{prefix}_PASSWORD", "")
    otp = os.environ.get(f"{prefix}_OTP", "")
    if not phone:
        raise SystemExit(f"{prefix}_PHONE is required for operation {args.operation}")
    args.client_phone = phone
    if otp:
        args.client_otp = otp
    os.environ["CLIENT_PHONE"] = phone
    if password:
        os.environ["CLIENT_PASSWORD"] = password
    if otp:
        os.environ["CLIENT_OTP"] = otp


def configure_operation(args: argparse.Namespace) -> None:
    if not args.operation:
        return
    selected = [flag for flag in OPERATION_FLAGS.values() if getattr(args, flag)]
    if selected or args.complete_kyc or args.main_positive_flow:
        raise SystemExit("--operation cannot be combined with legacy flow flags")
    setattr(args, OPERATION_FLAGS[args.operation], True)
    if args.operation == "deposit-create":
        args.deposit_amount = args.deposit_amount or os.environ.get("P0_DEPOSIT_AMOUNT", "")
        args.deposit_pid = args.deposit_pid or os.environ.get("P0_DEPOSIT_PID", "")
    if args.operation == "kyc-submit":
        args.kyc_image = os.environ.get("KYC_IMAGE", "") or args.kyc_image
    if args.operation == "withdraw-create":
        args.withdraw_amount = args.withdraw_amount or os.environ.get("P0_WITHDRAW_AMOUNT", "")
        args.withdraw_account_id = (
            args.withdraw_account_id or os.environ.get("P0_WITHDRAW_ACCOUNT_ID", "")
        )
    if args.operation == "withdraw-account-prepare":
        args.maya_pid = args.maya_pid or os.environ.get("PROVISION_MAYA_PID", "")
    if args.operation == "kyc-approve" and not args.kyc_uid:
        args.kyc_uid = os.environ.get("KYC_CLIENT_UID", "")
        if not args.kyc_uid:
            raise SystemExit("kyc-approve requires --kyc-uid or KYC_CLIENT_UID")
    if args.operation in {
        "deposit-check-client",
        "deposit-check-admin",
        "deposit-approve",
    } and not args.deposit_id:
        args.deposit_id = os.environ.get("P0_DEPOSIT_ID", "")
        if not args.deposit_id:
            raise SystemExit(f"{args.operation} requires --deposit-id or P0_DEPOSIT_ID")
    if args.operation in {
        "withdraw-check-client",
        "withdraw-check-admin",
        "withdraw-approve",
    } and not args.withdraw_id:
        args.withdraw_id = os.environ.get("P0_WITHDRAW_ID", "")
        if not args.withdraw_id:
            raise SystemExit(f"{args.operation} requires --withdraw-id or P0_WITHDRAW_ID")
    if args.operation == "turnover-clear" and not args.member_uid:
        args.member_uid = os.environ.get("P0_MEMBER_UID", "")
        if not args.member_uid:
            raise SystemExit("turnover-clear requires --member-uid or P0_MEMBER_UID")
    apply_operation_client_lane(args)


def query_wallet(args: argparse.Namespace, name: str) -> dict[str, object]:
    result = smoke.request_once(
        row("GET", "{{api_url}}/finance/wallet"),
        args.timeout,
        args.insecure,
    )
    return result_record(name, result)


def wait_for_deposit_credit(
    args: argparse.Namespace,
    wallet_before: dict[str, object],
    expected_amount: str,
) -> dict[str, object]:
    before_data = wallet_before.get("data")
    before_balance = (
        decimal_value(before_data.get("balance"))
        if isinstance(before_data, dict)
        else None
    )
    amount = decimal_value(expected_amount)
    if before_balance is None or amount is None:
        return {
            "name": "wallet_after_deposit",
            "business_status": False,
            "reason": "deposit wallet checkpoint is not numeric",
        }
    attempts = max(1, int(args.wallet_settlement_attempts))
    interval = max(0.0, float(args.wallet_settlement_interval))
    record: dict[str, object] = {}
    for attempt in range(1, attempts + 1):
        record = query_wallet(args, "wallet_after_deposit")
        after_data = record.get("data")
        after_balance = (
            decimal_value(after_data.get("balance"))
            if isinstance(after_data, dict)
            else None
        )
        record["expected_balance_delta"] = str(amount)
        record["actual_balance_delta"] = (
            str(after_balance - before_balance) if after_balance is not None else ""
        )
        record["poll_attempts"] = attempt
        if (
            record.get("business_status") is True
            and after_balance is not None
            and after_balance - before_balance >= amount
        ):
            return record
        if attempt < attempts:
            time.sleep(interval)
    record["business_status"] = False
    record["reason"] = (
        f"deposit was approved but wallet balance did not increase by {amount} "
        f"within {attempts} attempts"
    )
    return record


def wait_for_withdrawable_funds(args: argparse.Namespace) -> dict[str, object]:
    required = decimal_value(args.withdraw_amount or DEFAULT_WITHDRAW_AMOUNT)
    if required is None or required <= 0:
        return {
            "name": "wallet_before_withdraw",
            "business_status": False,
            "reason": "withdraw amount is not numeric",
        }
    attempts = max(1, int(args.wallet_settlement_attempts))
    interval = max(0.0, float(args.wallet_settlement_interval))
    record: dict[str, object] = {}
    for attempt in range(1, attempts + 1):
        record = query_wallet(args, "wallet_before_withdraw")
        data = record.get("data")
        balance = decimal_value(data.get("balance")) if isinstance(data, dict) else None
        withdrawable = decimal_value(data.get("withdrawable")) if isinstance(data, dict) else None
        record["required_amount"] = str(required)
        record["poll_attempts"] = attempt
        if (
            record.get("business_status") is True
            and balance is not None
            and withdrawable is not None
            and balance >= required
            and withdrawable >= required
        ):
            return record
        if attempt < attempts:
            time.sleep(interval)
    record["business_status"] = False
    record["reason"] = (
        f"wallet does not have withdrawable funds >= {required} after turnover clear"
    )
    return record


def wallet_password_body(password: str) -> dict[str, str]:
    return {"pwd": password}


def prepare_withdraw_account(args: argparse.Namespace) -> list[dict[str, object]]:
    password = args.wallet_password or os.environ.get("CLIENT_WALLET_PASSWORD", "")
    phone = "".join(character for character in os.environ.get("CLIENT_PHONE", "") if character.isdigit())
    maya_account = args.maya_account or os.environ.get("PROVISION_MAYA_ACCOUNT", "") or phone
    maya_pid = args.maya_pid or os.environ.get("PROVISION_MAYA_PID", "")
    if not (password.isdigit() and len(password) == 6):
        raise SystemExit("CLIENT_WALLET_PASSWORD or --wallet-password must be a 6-digit value")
    if not maya_account.isdigit():
        raise SystemExit("Maya account must be numeric")
    if not maya_pid.isdigit():
        raise SystemExit("PROVISION_MAYA_PID or --maya-pid must be numeric")

    records: list[dict[str, object]] = []
    profile = smoke.request_once(
        row("GET", "{{api_url}}/member/detail"), args.timeout, args.insecure
    )
    profile_record = result_record("member_detail_before_withdraw_account", profile)
    records.append(profile_record)
    profile_data = data_of(profile)
    if not business_ok(profile) or not isinstance(profile_data, dict):
        return records

    has_wallet_password = profile_data.get("has_wallet_password") is True
    profile_record["has_wallet_password"] = has_wallet_password
    if not has_wallet_password:
        password_result = smoke.request_once(
            row("POST", "{{api_url}}/finance/wallet/pwd/set"),
            args.timeout,
            args.insecure,
            wallet_password_body(password),
            args.body_format,
            content_type="application/json",
        )
        records.append(result_record("wallet_password_set", password_result))
        if not business_ok(password_result):
            return records

    password_check = smoke.request_once(
        row("POST", "{{api_url}}/finance/wallet/pwd/check"),
        args.timeout,
        args.insecure,
        wallet_password_body(password),
        args.body_format,
        content_type="application/json",
    )
    records.append(result_record("wallet_password_check", password_check))
    if not business_ok(password_check):
        return records

    before = smoke.request_once(
        row("GET", "{{api_url}}/finance/account/list"), args.timeout, args.insecure
    )
    before_record = result_record("withdraw_account_before", before)
    before_rows = list_rows(data_of(before))
    existing = next(
        (
            item
            for item in before_rows
            if str(item.get("account") or "") == maya_account
            and str(item.get("payment_platform_id") or "") == maya_pid
        ),
        None,
    )
    before_record["matched_account"] = existing is not None
    records.append(before_record)
    if not business_ok(before):
        return records

    if existing is None:
        insert = smoke.request_once(
            row("POST", "{{api_url}}/finance/account/insert"),
            args.timeout,
            args.insecure,
            {
                "account": maya_account,
                "first_name": args.maya_first_name,
                "last_name": args.maya_last_name,
                "middle_name": args.maya_middle_name,
                "pid": maya_pid,
                "cat": 2,
                "bank_name": None,
                "bank_code": None,
            },
            args.body_format,
            content_type="application/json",
        )
        records.append(result_record("withdraw_account_insert", insert))
        if not business_ok(insert):
            return records
    else:
        records.append({
            "name": "withdraw_account_insert",
            "business_status": True,
            "skipped": True,
            "reason": "matching Maya account already exists",
        })

    after = smoke.request_once(
        row("GET", "{{api_url}}/finance/account/list"), args.timeout, args.insecure
    )
    after_record = result_record("withdraw_account_after", after)
    matched = next(
        (
            item
            for item in list_rows(data_of(after))
            if str(item.get("account") or "") == maya_account
            and str(item.get("payment_platform_id") or "") == maya_pid
        ),
        None,
    )
    account_id = str(matched.get("id") or "") if isinstance(matched, dict) else ""
    after_record.update({
        "matched_account": matched is not None,
        "account_masked": "*" * max(len(maya_account) - 4, 0) + maya_account[-4:],
        "payment_platform_id": maya_pid,
        "account_id": account_id,
    })
    if business_ok(after) and not account_id:
        after_record["business_status"] = False
        after_record["reason"] = "Maya account was not returned after binding"
    records.append(after_record)
    return records


def register_new_user(args: argparse.Namespace) -> list[dict[str, object]]:
    phone = args.register_phone or os.environ.get("REGISTER_PHONE", "")
    if not phone:
        raise SystemExit("REGISTER_PHONE or --register-phone is required; use an allocated 090XXXXXXXX KYC test account")
    password = os.environ.get("REGISTER_PASSWORD", "")
    if not password:
        raise SystemExit("REGISTER_PASSWORD is required for registration")
    code = os.environ.get("REGISTER_OTP") or os.environ.get("CLIENT_OTP")
    otp_source = os.environ.get(
        "REGISTER_OTP_SOURCE",
        os.environ.get("CLIENT_OTP_SOURCE", "fixed"),
    ).strip().lower()
    if not code and otp_source != "admin_sms":
        raise SystemExit(
            "REGISTER_OTP/CLIENT_OTP or REGISTER_OTP_SOURCE=admin_sms is required for registration"
        )

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
        records.append({
            "name": "register",
            "business_status": False,
            "skipped": True,
            "reason": "missing otp_id",
            "phone_masked": masked_phone(phone),
        })
        return records

    if not code and otp_source == "admin_sms":
        code = smoke.admin_sms_otp(args, otp_id)
    if not code:
        records.append({
            "name": "register",
            "business_status": False,
            "skipped": True,
            "reason": "registration OTP lookup failed",
            "phone": phone,
        })
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
    register_data = data_of(register_result)
    register_token = str(register_data.get("token") or "") if isinstance(register_data, dict) else ""
    if register_token:
        os.environ["API_TOKEN"] = register_token
        os.environ["CLIENT_PHONE"] = phone
        os.environ["CLIENT_PASSWORD"] = password
        args.client_phone = phone
    register_record = result_record("register", register_result)
    register_record["phone_masked"] = masked_phone(phone)
    records.append(register_record)
    return records


def masked_phone(phone: str) -> str:
    return "*" * max(len(phone) - 4, 0) + phone[-4:]


def phone_cursor_path(env_path: str) -> Path:
    name = Path(env_path).name.lower()
    if name.startswith(".env."):
        name = name[5:]
    elif name.startswith("env."):
        name = name[4:]
    safe_name = "".join(character if character.isalnum() else "-" for character in name).strip("-")
    return PHONE_CURSOR_DIR / f"register-phone-{safe_name or 'test'}.json"


def load_phone_cursor(path: Path) -> str:
    if not path.is_file():
        return ""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"registration phone cursor is invalid: {path}") from error
    value = payload.get("next_start") if isinstance(payload, dict) else ""
    if not isinstance(value, str) or not value.isdigit():
        raise SystemExit(f"registration phone cursor has no numeric next_start: {path}")
    return value


def save_phone_cursor(path: Path, phone: str, env_path: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {"environment_file": Path(env_path).name, "next_start": phone},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    path.chmod(0o600)


def admin_member_exists(args: argparse.Namespace, phone: str) -> bool:
    result = smoke.request_once(
        row("POST", "{{admin_url}}/admin/member/list", "{{admin_url}}"),
        args.timeout,
        args.insecure,
        {"page": 1, "page_size": 10, "phone": phone},
        args.body_format,
    )
    if not business_ok(result):
        raise SystemExit("admin member lookup returned a business failure")
    data = data_of(result)
    rows = data.get("d") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        raise SystemExit("admin member lookup data.d is not a list")
    return any(
        isinstance(item, dict) and str(item.get("phone") or "") == phone
        for item in rows
    )


def allocate_registration_phone(args: argparse.Namespace) -> tuple[str, dict[str, object]]:
    known_phone = os.environ.get("CLIENT_PHONE") or os.environ.get("WRITE_CLIENT_PHONE", "")
    if not known_phone:
        raise SystemExit("CLIENT_PHONE or WRITE_CLIENT_PHONE is required to verify admin phone filtering")
    if not admin_member_exists(args, known_phone):
        raise SystemExit("admin phone filter could not locate the configured known member")

    cursor_path = phone_cursor_path(args.env)
    start = (
        args.register_phone
        or os.environ.get("REGISTER_PHONE", "")
        or os.environ.get("PROVISION_PHONE_START", "")
        or load_phone_cursor(cursor_path)
        or DEFAULT_REGISTER_PHONE_START
    )
    if not start.isdigit():
        raise SystemExit("registration phone start must be numeric")
    width = len(start)
    for offset in range(args.register_scan_limit):
        candidate = str(int(start) + offset).zfill(width)
        if not admin_member_exists(args, candidate):
            save_phone_cursor(cursor_path, candidate, args.env)
            try:
                cursor_display = str(cursor_path.relative_to(ROOT_DIR))
            except ValueError:
                cursor_display = str(cursor_path)
            return candidate, {
                "name": "register_phone_allocate",
                "business_status": True,
                "phone_masked": masked_phone(candidate),
                "checked_candidates": offset + 1,
                "cursor_file": cursor_display,
            }
    raise SystemExit(f"no unregistered phone found within {args.register_scan_limit} candidates")


def upload_kyc_attachment(args: argparse.Namespace, image_path: Path, field_name: str) -> dict[str, object]:
    boundary = f"----qa-kyc-{uuid.uuid4().hex}"
    content_type = mimetypes.guess_type(image_path.name)[0] or "application/octet-stream"
    filename = f"{field_name}_{int(time.time() * 1000)}{image_path.suffix.lower()}"
    prefix = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode("utf-8")
    payload = prefix + image_path.read_bytes() + f"\r\n--{boundary}--\r\n".encode("utf-8")
    upload_row = row("POST", "{{api_url}}/member/oss/upload")
    url = smoke.resolve_url(upload_row["clean_url"])
    headers = smoke.headers_for(upload_row)
    headers["content-type"] = f"multipart/form-data; boundary={boundary}"
    request = Request(url, data=payload, method="POST", headers=headers)
    context = ssl._create_unverified_context() if args.insecure else None
    started = time.monotonic()
    try:
        with urlopen(request, timeout=args.timeout, context=context) as response:
            body_bytes = response.read()
            decoded, sample = smoke.decode_body_sample(body_bytes)
            result = {
                "priority": "CONTROLLED",
                "method": "POST",
                "url": url,
                "status": response.status,
                "elapsed_ms": int((time.monotonic() - started) * 1000),
                "decoded_body": decoded,
                "body_sample": sample,
            }
    except Exception as error:
        raise SystemExit(f"KYC attachment upload failed for {field_name}: {error}") from error
    data = data_of(result)
    object_key = str(data.get("object_key") or "") if isinstance(data, dict) else ""
    if not business_ok(result) or not object_key:
        raise SystemExit(f"KYC attachment upload rejected for {field_name}: {result.get('body_sample')}")
    return {
        "name": f"kyc_upload_{field_name}",
        "url": result.get("url"),
        "http_status": result.get("status"),
        "business_status": True,
        "object_key": object_key,
        "elapsed_ms": result.get("elapsed_ms"),
    }


def submit_kyc(args: argparse.Namespace) -> list[dict[str, object]]:
    image_path = Path(args.kyc_image)
    if not image_path.is_file():
        raise SystemExit(f"KYC image does not exist: {image_path}")

    detail_before = smoke.request_once(
        row("GET", "{{api_url}}/member/kyc/detail"), args.timeout, args.insecure
    )
    profile = data_of(detail_before)
    if not isinstance(profile, dict):
        raise SystemExit("cannot read KYC profile before submission")
    if int(profile.get("kyc_status") or 0) != 0:
        raise SystemExit(f"KYC account is not submit-ready: kyc_status={profile.get('kyc_status')}")

    shops_result = smoke.request_once(
        row("POST", "{{api_url}}/member/kyc/shops"), args.timeout, args.insecure
    )
    shops_data = data_of(shops_result)
    shops = list_rows(shops_data)
    if not shops and isinstance(shops_data, list):
        shops = [item for item in shops_data if isinstance(item, dict)]
    def branch_label(item: dict[str, object]) -> str:
        return str(item.get("label") or item.get("name") or item.get("address") or "")

    branch = next(
        (
            item
            for item in shops
            if branch_label(item) == args.kyc_nearest_branch
            or str(item.get("value") or "") == args.kyc_nearest_branch
        ),
        None,
    )
    if branch is None and "Taft Ave" in args.kyc_nearest_branch:
        branch = next((item for item in shops if "Taft Ave, Pasay" in branch_label(item)), None)
    if branch is None:
        preview = [str(item.get("label") or item.get("name") or item.get("address") or "") for item in shops[:5]]
        raise SystemExit(f"KYC branch is not available: {args.kyc_nearest_branch}; available={preview}")

    uploads = [
        upload_kyc_attachment(args, image_path, "front_side_of_id"),
        upload_kyc_attachment(args, image_path, "back_side_of_id"),
        upload_kyc_attachment(args, image_path, "selfie_with_id_card"),
    ]
    attachment_keys = [str(item["object_key"]) for item in uploads]
    uid = str(profile.get("uid") or "")
    body = {
        "attachments": {
            "face": attachment_keys[0],
            "idPhoto": attachment_keys[1],
            "selfieWithIDPhotoPath": attachment_keys[2],
        },
        "birthday": args.kyc_birthday,
        "country_code": str(profile.get("country_code") or "63"),
        "current_address": args.kyc_current_address,
        "first_name": args.kyc_first_name,
        "middle_name": args.kyc_middle_name,
        "last_name": args.kyc_last_name,
        "nationality": args.kyc_nationality,
        "gender": args.kyc_gender,
        "id_number": args.kyc_id_number or uid,
        "id_type": args.kyc_id_type,
        "nature_of_work": args.kyc_nature_of_work,
        "nearest_branch": branch_label(branch),
        "shop_id": int(branch.get("value") or branch.get("id") or branch.get("shop_id") or 0),
        "occupation": args.kyc_nature_of_work,
        "permanent_address": args.kyc_permanent_address,
        "phone": str(profile.get("phone") or ""),
        "place_of_birth": args.kyc_place_of_birth,
        "source_of_income": args.kyc_source_of_income,
    }
    submit_result = smoke.request_once(
        row("POST", "{{api_url}}/member/kyc/insert"),
        args.timeout,
        args.insecure,
        body,
        args.body_format,
    )
    detail_after = smoke.request_once(
        row("GET", "{{api_url}}/member/kyc/detail"), args.timeout, args.insecure
    )
    return [
        result_record("kyc_detail_before", detail_before),
        result_record("kyc_shops", shops_result),
        *uploads,
        result_record("kyc_submit", submit_result),
        result_record("kyc_detail_after", detail_after),
    ]


def find_kyc_record(args: argparse.Namespace, uid: str) -> tuple[dict[str, object], dict[str, object] | None]:
    def request_list(body: dict[str, object]) -> dict[str, object]:
        return smoke.request_once(
            row("POST", "{{admin_url}}/admin/kyc/list", "{{admin_url}}"),
            args.timeout,
            args.insecure,
            body,
            args.body_format,
        )

    query: dict[str, object] = {"page": 1, "page_size": 50, "source": "default"}
    if uid:
        query["uid"] = uid
    result = request_list(query)
    rows = list_rows(data_of(result))
    target = next((item for item in rows if str(item.get("uid") or item.get("id") or "") == uid), None)
    if uid and target is None:
        result = request_list({"page": 1, "page_size": 100, "source": "default"})
        rows = list_rows(data_of(result))
        target = next((item for item in rows if str(item.get("uid") or item.get("id") or "") == uid), None)
    record = result_record("admin_kyc_list", result)
    record["matched_record"] = target
    return record, target


def approve_kyc(args: argparse.Namespace, uid: str) -> list[dict[str, object]]:
    list_record, target = find_kyc_record(args, uid)
    records = [list_record]
    if not target:
        records.append({
            "name": "admin_kyc_approve",
            "business_status": False,
            "reason": f"KYC record not found for uid={uid or '<missing>'}",
        })
        return records
    target_uid = str(target.get("uid") or uid)
    body = add_approval_code({"uid": target_uid, "comment": args.approval_desc}, args)
    result = smoke.request_once(
        row("POST", "{{admin_url}}/admin/kyc/approve", "{{admin_url}}"),
        args.timeout,
        args.insecure,
        body,
        args.body_format,
    )
    approve_record = result_record("admin_kyc_approve", result)
    approve_record["uid"] = target_uid
    records.append(approve_record)
    if not business_ok(result):
        return records

    detail, profile, attempts = wait_for_kyc_status(args, 5)
    detail_record = result_record("kyc_detail_after_approval", detail)
    approved = isinstance(profile, dict) and int(profile.get("kyc_status") or 0) == 5
    detail_record["business_status"] = approved
    detail_record["expected_kyc_status"] = 5
    detail_record["actual_kyc_status"] = profile.get("kyc_status") if isinstance(profile, dict) else None
    detail_record["poll_attempts"] = attempts
    records.append(detail_record)
    return records


def resolve_kyc_uid(args: argparse.Namespace, profile: object = None) -> str:
    if args.kyc_uid:
        return args.kyc_uid
    profile_uid = str(profile.get("uid") or "") if isinstance(profile, dict) else ""
    if args.use_register_phone:
        return profile_uid
    return os.environ.get("KYC_CLIENT_UID", "") or profile_uid


def wait_for_kyc_status(
    args: argparse.Namespace,
    expected_status: int,
) -> tuple[dict[str, object], object, int]:
    attempts = max(1, int(getattr(args, "kyc_status_attempts", 1)))
    interval = max(0.0, float(getattr(args, "kyc_status_interval", 0)))
    result: dict[str, object] = {}
    profile: object = None
    for attempt in range(1, attempts + 1):
        result = smoke.request_once(
            row("GET", "{{api_url}}/member/kyc/detail"), args.timeout, args.insecure
        )
        profile = data_of(result)
        actual = int(profile.get("kyc_status") or 0) if isinstance(profile, dict) else -1
        if actual == expected_status or attempt == attempts:
            return result, profile, attempt
        time.sleep(interval)
    return result, profile, attempts


def remaining_turnover(rows: list[dict[str, object]]) -> Decimal:
    total = Decimal("0")
    for item in rows:
        if int(item.get("state") or 0) != 1:
            continue
        turnover = decimal_value(item.get("turnover")) or Decimal("0")
        finished = decimal_value(item.get("finished")) or Decimal("0")
        total += max(turnover - finished, Decimal("0"))
    return total


def query_admin_turnover(
    args: argparse.Namespace,
    uid: str,
    name: str,
) -> tuple[dict[str, object], Decimal]:
    result = smoke.request_once(
        row(
            "GET",
            f"{{{{admin_url}}}}/admin/finance/turnover/list?uid={uid}&page=1&page_size=100",
            "{{admin_url}}",
        ),
        args.timeout,
        args.insecure,
    )
    record = result_record(name, result)
    rows = list_rows(data_of(result))
    remaining = remaining_turnover(rows)
    record["row_count"] = len(rows)
    record["remaining_turnover"] = str(remaining)
    return record, remaining


def run_turnover_clear(
    args: argparse.Namespace,
    uid: str,
    expected_locked: Decimal | None = None,
) -> list[dict[str, object]]:
    before_record, before = query_admin_turnover(args, uid, "turnover_before_clear")
    records = [before_record]
    if before_record.get("business_status") is not True:
        return records
    discovery_attempts = max(1, int(getattr(args, "turnover_discovery_attempts", 30)))
    discovery_interval = max(0.0, float(getattr(args, "turnover_discovery_interval", 1)))
    if expected_locked is not None and expected_locked > 0:
        for attempt in range(1, discovery_attempts + 1):
            before_record["discovery_attempts"] = attempt
            if before > 0 or int(before_record.get("row_count") or 0) > 0:
                break
            if attempt < discovery_attempts:
                time.sleep(discovery_interval)
                before_record, before = query_admin_turnover(args, uid, "turnover_before_clear")
                records[0] = before_record
        if before == 0 and int(before_record.get("row_count") or 0) == 0:
            before_record["business_status"] = False
            before_record["reason"] = (
                f"wallet remains locked={expected_locked} but no turnover record appeared "
                f"within {discovery_attempts} attempts"
            )
            return records
    if before == 0:
        records.append({
            "name": "turnover_clear",
            "business_status": True,
            "skipped": True,
            "reason": "remaining turnover is already zero",
        })
        return records
    body = add_approval_code(
        {"uid": uid, "remark": args.turnover_clear_remark},
        args,
    )
    result = smoke.request_once(
        row("POST", "{{admin_url}}/admin/finance/turnover/clear", "{{admin_url}}"),
        args.timeout,
        args.insecure,
        body,
        "cbor",
        content_type="application/x-www-form-urlencoded",
    )
    records.append(result_record("turnover_clear", result))
    if not business_ok(result):
        return records
    attempts = max(1, int(getattr(args, "turnover_clear_attempts", 10)))
    interval = max(0.0, float(getattr(args, "turnover_clear_interval", 1)))
    after_record: dict[str, object] = {}
    after = before
    for attempt in range(1, attempts + 1):
        after_record, after = query_admin_turnover(args, uid, "turnover_after_clear")
        after_record["poll_attempts"] = attempt
        if after == 0 or attempt == attempts:
            break
        time.sleep(interval)
    after_record["business_status"] = after_record.get("business_status") is True and after == 0
    if after != 0:
        after_record["reason"] = f"remaining turnover is not zero after clear: {after}"
    records.append(after_record)
    return records


def decimal_value(value: object) -> Decimal | None:
    try:
        parsed = Decimal(str(value))
        return parsed if parsed.is_finite() else None
    except (InvalidOperation, TypeError, ValueError):
        return None


def channel_amount_options(channel: dict[str, object]) -> list[Decimal]:
    raw_options = channel.get("amount_limit")
    if not isinstance(raw_options, list):
        return []
    options: list[Decimal] = []
    for raw in raw_options:
        if isinstance(raw, dict):
            raw = raw.get("amount", raw.get("value"))
        parsed = decimal_value(raw)
        if parsed is not None:
            options.append(parsed)
    return options


def channel_accepts_amount(channel: dict[str, object], amount: str) -> bool:
    requested = decimal_value(amount)
    if requested is None or requested <= 0:
        return False
    minimum = decimal_value(channel.get("min_amount"))
    maximum = decimal_value(channel.get("max_amount"))
    if minimum is not None and requested < minimum:
        return False
    if maximum is not None and requested > maximum:
        return False
    return True


def default_channel_amount(channel: dict[str, object]) -> str:
    options = channel_amount_options(channel)
    for option in options:
        if channel_accepts_amount(channel, str(option)):
            return str(option)
    return str(channel.get("min_amount") or "1")


def choose_deposit_channel(args: argparse.Namespace) -> tuple[str, str]:
    channels_result = smoke.request_once(
        row("GET", "{{api_url}}/finance/channel/list?mode=1"),
        args.timeout,
        args.insecure,
    )
    channels = data_of(channels_result)
    if not isinstance(channels, list) or not channels:
        raise SystemExit("no deposit channels available")

    usable_channels = [item for item in channels if isinstance(item, dict) and item.get("id")]
    if args.deposit_pid:
        usable_channels = [item for item in usable_channels if str(item.get("id")) == args.deposit_pid]
        if not usable_channels:
            raise SystemExit(f"configured deposit channel is unavailable: pid={args.deposit_pid}")

    requested_amount = args.deposit_amount
    if requested_amount:
        usable_channels = [
            item for item in usable_channels if channel_accepts_amount(item, requested_amount)
        ]
        if not usable_channels:
            pid_context = f" for pid={args.deposit_pid}" if args.deposit_pid else ""
            raise SystemExit(
                f"no deposit channel accepts amount={requested_amount}{pid_context}; "
                "check min_amount and max_amount"
            )

    if not usable_channels:
        raise SystemExit("no usable deposit channels available")
    requested = decimal_value(requested_amount) if requested_amount else None
    channel = next(
        (
            item for item in usable_channels
            if requested is not None and requested in channel_amount_options(item)
        ),
        usable_channels[0],
    )
    amount = requested_amount or default_channel_amount(channel)
    if not channel_accepts_amount(channel, amount):
        raise SystemExit(f"deposit channel pid={channel['id']} has no valid amount tier")
    return str(channel["id"]), amount


def run_deposit(args: argparse.Namespace) -> list[dict[str, object]]:
    pid, amount = choose_deposit_channel(args)
    query = (
        f"pid={pid}&amount={amount}&device=web&source=huawei"
        f"&cashback_flag={args.deposit_cashback_flag}&rotation_flag={args.deposit_rotation_flag}"
    )
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
    record["cashback_flag"] = args.deposit_cashback_flag
    record["rotation_flag"] = args.deposit_rotation_flag
    external_order_id = args.deposit_external_order_id or extract_deposit_external_order_id(deposit_data)
    if external_order_id:
        record["external_order_id"] = external_order_id
    return [record]


def run_deposit_stage(args: argparse.Namespace, records: list[dict[str, object]]) -> bool:
    deposit_records = run_deposit(args)
    records.extend(deposit_records)
    if any(item.get("business_status") is not True for item in deposit_records):
        for item in deposit_records:
            if item.get("business_status") is not True:
                item["business_status"] = False
        return False

    deposit_data = deposit_records[-1].get("data")
    deposit_id = str(deposit_data.get("id") or deposit_data.get("order_id") or "") if isinstance(deposit_data, dict) else ""
    deposit_external_order_id = str(deposit_records[-1].get("external_order_id") or "")
    if args.approve_deposit:
        client_records = check_client_deposit_list(args, deposit_id)
        records.extend(client_records)
        if any(item.get("business_status") is not True for item in client_records):
            return False
        matched_order = client_records[-1].get("matched_order")
        if isinstance(matched_order, dict):
            deposit_external_order_id = str(
                matched_order.get("external_order_id")
                or matched_order.get("merchant_order_id")
                or deposit_external_order_id
            )
        if not deposit_id or not deposit_external_order_id:
            records.append({
                "name": "deposit_identifiers",
                "business_status": False,
                "reason": "client deposit record is missing id or external_order_id",
            })
            return False
        approval_records = approve_deposit(
            args,
            None,
            deposit_id,
            deposit_external_order_id,
        )
        records.extend(approval_records)
        if any(item.get("business_status") is not True for item in approval_records):
            for item in approval_records:
                if item.get("business_status") is not True:
                    item["business_status"] = False
            return False
    return True


def check_client_deposit_list(args: argparse.Namespace, deposit_id: str) -> list[dict[str, object]]:
    identifiers = (
        "id",
        "order_id",
        "external_order_id",
        "merchant_order_id",
        "transaction_id",
    )
    attempts = max(1, int(getattr(args, "deposit_lookup_attempts", 1)))
    interval = max(0.0, float(getattr(args, "deposit_lookup_interval", 0)))
    result: dict[str, object] = {}
    matched = None
    for attempt in range(attempts):
        result = smoke.request_once(
            row("GET", "{{api_url}}/finance/deposit/list?page=1&page_size=50&time_flag=0"),
            args.timeout,
            args.insecure,
        )
        rows = list_rows(data_of(result))
        matched = next(
            (
                item
                for item in rows
                if any(str(item.get(key) or "") == str(deposit_id) for key in identifiers)
            ),
            None,
        )
        if matched is not None or attempt + 1 >= attempts:
            break
        time.sleep(interval)
    record = result_record("client_deposit_list", result)
    record["matched_order"] = matched
    if matched is None:
        record["business_status"] = False
        record["reason"] = f"deposit order not found: id={deposit_id}"
    return [record]


def find_deposit_order(args: argparse.Namespace, deposit_id: str = "") -> tuple[dict[str, object], dict[str, object] | None]:
    start_time, end_time = now_window()
    base_params: dict[str, object] = {
        "status": args.deposit_status or "PENDING",
        "start_time": start_time,
        "end_time": end_time,
        "page": 1,
        "page_size": 50,
    }
    attempts = max(1, int(getattr(args, "deposit_lookup_attempts", 1)))
    interval = max(0.0, float(getattr(args, "deposit_lookup_interval", 0)))
    result: dict[str, object] = {}
    target = None
    for attempt in range(attempts):
        params = dict(base_params)
        # Some FAT admin deployments accept only their internal id here,
        # while deposit-create returns the client order_id. Try the narrow
        # server filter first, then poll the recent pending page and match the
        # same identifier locally. Never fall back to an unrelated first row.
        if deposit_id and attempt == 0:
            params["id"] = deposit_id
        result = smoke.request_once(
            row("POST", "{{admin_url}}/admin/finance/deposit/risk/list", "{{admin_url}}"),
            args.timeout,
            args.insecure,
            params,
            args.body_format,
        )
        result["url"] = str(result.get("url") or "") + "?" + urlencode(params)
        rows = list_rows(data_of(result))
        if deposit_id:
            identifiers = (
                "id",
                "order_id",
                "external_order_id",
                "merchant_order_id",
                "transaction_id",
            )
            target = next(
                (
                    item
                    for item in rows
                    if any(str(item.get(key) or "") == str(deposit_id) for key in identifiers)
                ),
                None,
            )
        elif rows:
            target = rows[0]
        if target is not None or attempt + 1 >= attempts:
            break
        time.sleep(interval)
    record_name = "admin_deposit_risk_list"
    if deposit_id and target is None:
        # Online-channel orders may be visible in the general deposit ledger
        # before (or without) entering the risk-review queue.
        params = {
            "start_time": start_time,
            "end_time": end_time,
            "page": 1,
            "page_size": 100,
        }
        result = smoke.request_once(
            row("POST", "{{admin_url}}/admin/finance/deposit/list", "{{admin_url}}"),
            args.timeout,
            args.insecure,
            params,
            args.body_format,
        )
        result["url"] = str(result.get("url") or "") + "?" + urlencode(params)
        rows = list_rows(data_of(result))
        identifiers = (
            "id",
            "order_id",
            "external_order_id",
            "merchant_order_id",
            "transaction_id",
        )
        target = next(
            (
                item
                for item in rows
                if any(str(item.get(key) or "") == str(deposit_id) for key in identifiers)
            ),
            None,
        )
        record_name = "admin_deposit_list"
    record = result_record(record_name, result)
    record["matched_order"] = target
    if deposit_id and target is None:
        record["business_status"] = False
        record["reason"] = f"deposit order not found: id={deposit_id}"
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
        return args.withdraw_account_id, args.withdraw_amount or DEFAULT_WITHDRAW_AMOUNT, None
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
    amount = args.withdraw_amount or DEFAULT_WITHDRAW_AMOUNT
    requested = decimal_value(amount)
    maximum = decimal_value(account.get("max_amount"))
    if requested is None or requested < Decimal(DEFAULT_WITHDRAW_AMOUNT):
        raise SystemExit(f"withdraw amount must be at least {DEFAULT_WITHDRAW_AMOUNT}")
    if maximum is not None and requested > maximum:
        raise SystemExit(f"withdraw amount exceeds selected account maximum={maximum}")
    return str(account["id"]), amount, account


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


def run_withdraw_stage(
    args: argparse.Namespace,
    records: list[dict[str, object]],
) -> tuple[bool, str]:
    before_result, before_rows = fetch_client_withdraw_list(args)
    before_record = result_record("withdraw_list_before_create", before_result)
    records.append(before_record)
    if before_record.get("business_status") is not True:
        return False, ""
    existing_ids = {
        str(item.get("id") or item.get("order_no") or "")
        for item in before_rows
        if item.get("id") or item.get("order_no")
    }
    started_at_ms = int(time.time() * 1000)
    withdraw_records = run_withdraw(args)
    records.extend(withdraw_records)
    withdraw_data = withdraw_records[-1].get("data") if withdraw_records else None
    withdraw_id = (
        str(withdraw_data.get("id") or withdraw_data.get("order_no") or "")
        if isinstance(withdraw_data, dict)
        else ""
    )
    if withdraw_id and all(item.get("business_status") is True for item in withdraw_records):
        return True, withdraw_id

    create_record = withdraw_records[-1] if withdraw_records else {}
    amount = str(create_record.get("amount") or args.withdraw_amount or DEFAULT_WITHDRAW_AMOUNT)
    selected = create_record.get("selected_account")
    platform_id = (
        str(selected.get("payment_platform_id") or "")
        if isinstance(selected, dict)
        else ""
    )
    attempts = max(1, int(args.withdraw_lookup_attempts))
    interval = max(0.0, float(args.withdraw_lookup_interval))
    reconcile_record: dict[str, object] = {}
    matched = None
    for attempt in range(1, attempts + 1):
        lookup_result, lookup_rows = fetch_client_withdraw_list(args)
        candidates = []
        for item in lookup_rows:
            item_id = str(item.get("id") or item.get("order_no") or "")
            item_amount = decimal_value(item.get("amount"))
            created_at = int(item.get("created_at") or 0)
            same_platform = not platform_id or str(item.get("payment_platform_id") or "") == platform_id
            if (
                item_id
                and item_id not in existing_ids
                and item_amount == decimal_value(amount)
                and same_platform
                and created_at >= started_at_ms - 2000
            ):
                candidates.append(item)
        if candidates:
            matched = max(candidates, key=lambda item: int(item.get("created_at") or 0))
        reconcile_record = result_record("client_withdraw_async_reconcile", lookup_result)
        reconcile_record["matched_order"] = matched
        reconcile_record["poll_attempts"] = attempt
        if matched is not None or attempt == attempts:
            break
        time.sleep(interval)
    if matched is None:
        reconcile_record["business_status"] = False
        reconcile_record["reason"] = "withdraw response had no usable id and no new matching order appeared"
        records.append(reconcile_record)
        return False, ""

    withdraw_id = str(matched.get("id") or matched.get("order_no") or "")
    create_record["response_business_status"] = create_record.get("business_status")
    create_record["business_status"] = True
    create_record["async_reconciled"] = True
    create_record["reason"] = "synchronous response was inconclusive; a new matching order appeared asynchronously"
    reconcile_record["business_status"] = True
    reconcile_record["withdraw_id"] = withdraw_id
    records.append(reconcile_record)
    return True, withdraw_id


def fetch_client_withdraw_list(
    args: argparse.Namespace,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    result = smoke.request_once(
        row("GET", "{{api_url}}/finance/withdraw/list?time_flag=0&page=1&page_size=50"),
        args.timeout,
        args.insecure,
    )
    return result, list_rows(data_of(result))


def check_client_withdraw_list(args: argparse.Namespace, withdraw_id: str = "") -> list[dict[str, object]]:
    result, rows = fetch_client_withdraw_list(args)
    record = result_record("client_withdraw_list", result)
    matched = next((item for item in rows if str(item.get("id") or item.get("order_no") or "") == withdraw_id), None) if withdraw_id else (rows[0] if rows else None)
    record["matched_order"] = matched
    if withdraw_id and matched is None:
        record["business_status"] = False
        record["reason"] = f"withdraw order not found: id={withdraw_id}"
    return [record]


def find_withdraw_order(args: argparse.Namespace, withdraw_id: str = "") -> tuple[dict[str, object], dict[str, object] | None]:
    start_time, end_time = now_window()
    params = {
        "status": args.withdraw_status or "under_review",
        "start_time": start_time * 1000,
        "end_time": end_time * 1000,
        "page": 1,
        "page_size": 10,
    }
    if withdraw_id:
        params["id"] = withdraw_id
    def request_list(body: dict[str, object]) -> dict[str, object]:
        response = smoke.request_once(
            row("POST", "{{admin_url}}/admin/finance/withdraw/risk/audit/list", "{{admin_url}}"),
            args.timeout,
            args.insecure,
            body,
            args.body_format,
        )
        response["url"] = response.get("url", "") + "?" + urlencode(body)
        return response

    result = request_list(params)
    rows = list_rows(data_of(result))
    if withdraw_id and not rows:
        # The FAT endpoint currently returns an empty page when id and time
        # filters are combined. Retry the same status page without those
        # filters, then match the controlled order id locally.
        result = request_list({
            "status": args.withdraw_status or "under_review",
            "page": 1,
            "page_size": 10,
        })
        rows = list_rows(data_of(result))
    target = None
    if withdraw_id:
        target = next((item for item in rows if str(item.get("id")) == str(withdraw_id)), None)
    elif rows:
        target = rows[0]
    record_name = "admin_withdraw_risk_audit_list"
    if withdraw_id and target is None:
        general_params = {
            "start_time": start_time * 1000,
            "end_time": end_time * 1000,
            "page": 1,
            "page_size": 100,
        }
        result = smoke.request_once(
            row("POST", "{{admin_url}}/admin/finance/withdraw/list", "{{admin_url}}"),
            args.timeout,
            args.insecure,
            general_params,
            args.body_format,
        )
        result["url"] = result.get("url", "") + "?" + urlencode(general_params)
        rows = list_rows(data_of(result))
        target = next((item for item in rows if str(item.get("id")) == str(withdraw_id)), None)
        record_name = "admin_withdraw_list"
    record = result_record(record_name, result)
    record["matched_order"] = target
    if withdraw_id and target is None:
        record["business_status"] = False
        record["reason"] = f"withdraw order not found: id={withdraw_id}"
    return record, target


def check_admin_withdraw_list(args: argparse.Namespace, withdraw_id: str = "") -> list[dict[str, object]]:
    list_record, _ = find_withdraw_order(args, withdraw_id)
    return [list_record]


def approve_withdraw(args: argparse.Namespace, withdraw_order: dict[str, object] | None) -> list[dict[str, object]]:
    if not withdraw_order:
        return [{"name": "admin_withdraw_agree", "skipped": True, "reason": "no under_review withdraw order found"}]
    withdraw_id = str(withdraw_order.get("id") or "")
    if not withdraw_id:
        return [{"name": "admin_withdraw_agree", "skipped": True, "reason": "matched withdraw has no id"}]
    status = str(withdraw_order.get("status") or "").strip().lower()
    if status and status != "under_review":
        return [{
            "name": "admin_withdraw_agree",
            "business_status": True,
            "skipped": True,
            "withdraw_id": withdraw_id,
            "reason": f"withdraw order already progressed to status={status}",
        }]
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
        if not business_ok(agree_result):
            records.append({
                "name": "admin_withdraw_success",
                "skipped": True,
                "reason": "withdraw agree failed; success transition is not allowed",
                "withdraw_id": withdraw_id,
            })
            return records
        external_order_id = args.withdraw_external_order_id or f"p0-automation-{withdraw_id}"
        success_result = smoke.request_once(
            row("POST", "{{admin_url}}/admin/finance/withdraw/success", "{{admin_url}}"),
            args.timeout,
            args.insecure,
            {
                **body,
                "external_order_id": external_order_id,
            },
            args.body_format,
        )
        success_record = result_record("admin_withdraw_success", success_result)
        success_record["withdraw_id"] = withdraw_id
        records.append(success_record)
    return records


def finish(args: argparse.Namespace, records: list[dict[str, object]]) -> None:
    global OPERATION_REPORT_WRITTEN
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    report_name = args.operation or getattr(args, "flow_name", "")
    if report_name:
        for item in records:
            item["operation"] = report_name
    output.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {output.resolve()}")
    if report_name:
        report_items: list[dict[str, str]] = []
        for index, item in enumerate(records, 1):
            business_status = item.get("business_status")
            if business_status is True:
                status = "PASS"
            elif item.get("skipped"):
                status = "SKIPPED"
            else:
                status = "FAIL"
            raw_url = str(item.get("url") or "")
            parsed_url = urlparse(raw_url)
            safe_url = (
                f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
                if parsed_url.scheme and parsed_url.netloc
                else parsed_url.path
            )
            report_items.append({
                "group": report_name,
                "id": f"{report_name}-{index:02d}",
                "name": str(item.get("name") or "unnamed"),
                "kind": "API",
                "status": status,
                "target": safe_url,
                "expected": "HTTP 请求完成且业务状态为 true",
                "actual": (
                    f"HTTP={item.get('http_status', '—')}, "
                    f"business={business_status if business_status is not None else '—'}"
                ),
                "duration": f"{item.get('elapsed_ms')} ms" if item.get("elapsed_ms") is not None else "",
                "detail": str(item.get("reason") or ""),
            })
        verdict, detail = report_verdict(report_items)
        html_output = output.with_suffix(".html")
        write_html_report(
            title=f"P0 API 操作报告 · {report_name}",
            scope="UAT" if ".uat" in Path(args.env).name.lower() else "FAT",
            report_kind="API 独立操作",
            verdict=verdict,
            verdict_detail=detail,
            items=report_items,
            output=html_output,
            metadata=[("原始结果", str(output))],
        )
        OPERATION_REPORT_WRITTEN = True
        print(f"HTML report: {html_output.resolve()}")
    for item in records:
        status = item.get("business_status")
        raw_url = str(item.get("url") or "")
        parsed_url = urlparse(raw_url)
        safe_url = (
            f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
            if parsed_url.scheme and parsed_url.netloc
            else parsed_url.path
        )
        print(f"{item.get('name')} http={item.get('http_status')} business={status} url={safe_url}")
    failed_names = [
        str(item.get("name") or "unnamed")
        for item in records
        if item.get("business_status") is False
    ]
    if failed_names:
        raise SystemExit("controlled flow business failure: " + ", ".join(failed_names))


def main() -> None:
    global ACTIVE_ARGS, ACTIVE_RECORDS
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", default=os.environ.get("ENV_FILE", ".env.fat"))
    parser.add_argument("--timeout", type=float, default=10)
    parser.add_argument("--insecure", action="store_true")
    parser.add_argument("--body-format", choices=["json", "cbor"], default="cbor")
    parser.add_argument("--out", default="")
    parser.add_argument("--flow-name", default="")
    parser.add_argument(
        "--operation",
        choices=sorted(OPERATION_FLAGS),
        default="",
        help="Run one independent P0 API operation with fresh authentication",
    )
    parser.add_argument("--register", action="store_true")
    parser.add_argument("--submit-kyc", action="store_true")
    parser.add_argument("--approve-kyc", action="store_true")
    parser.add_argument("--complete-kyc", action="store_true", help="Submit when ready, approve pending record, then verify client status")
    parser.add_argument("--deposit", action="store_true")
    parser.add_argument("--check-client-deposit-list", action="store_true")
    parser.add_argument("--check-admin-deposit-list", action="store_true")
    parser.add_argument("--approve-deposit", action="store_true")
    parser.add_argument("--withdraw", action="store_true")
    parser.add_argument("--prepare-withdraw-account", action="store_true")
    parser.add_argument("--approve-withdraw", action="store_true")
    parser.add_argument("--check-client-withdraw-list", action="store_true")
    parser.add_argument("--check-admin-withdraw-list", action="store_true")
    parser.add_argument("--clear-turnover", action="store_true")
    parser.add_argument("--main-positive-flow", action="store_true")
    parser.add_argument("--client-phone", default="")
    parser.add_argument("--client-otp", default="")
    parser.add_argument("--use-register-phone", action="store_true")
    parser.add_argument("--register-phone", default="")
    parser.add_argument("--register-scan-limit", type=int, default=200)
    parser.add_argument("--kyc-image", default="21000000008072.webp")
    parser.add_argument("--kyc-first-name", default="Codex")
    parser.add_argument("--kyc-middle-name", default="")
    parser.add_argument("--kyc-last-name", default="001")
    parser.add_argument("--kyc-birthday", default="1993-08-31")
    parser.add_argument("--kyc-gender", choices=["male", "female"], default="male")
    parser.add_argument("--kyc-nationality", default="Philippines")
    parser.add_argument("--kyc-place-of-birth", default="Manila")
    parser.add_argument("--kyc-current-address", default="Manila")
    parser.add_argument("--kyc-permanent-address", default="Manila")
    parser.add_argument("--kyc-nearest-branch", default="2040 Taft Ave, Pasay, Metro Mani")
    parser.add_argument("--kyc-nature-of-work", default="Employed – Permanent/Contractual")
    parser.add_argument("--kyc-source-of-income", default="Employment Income")
    parser.add_argument("--kyc-id-type", default="COUNTRY_ID")
    parser.add_argument("--kyc-id-number", default="")
    parser.add_argument("--kyc-uid", default="")
    parser.add_argument("--kyc-status-attempts", type=int, default=10)
    parser.add_argument("--kyc-status-interval", type=float, default=1)
    parser.add_argument("--member-uid", default="")
    parser.add_argument("--deposit-pid", default="")
    parser.add_argument("--deposit-amount", default="")
    parser.add_argument("--deposit-product-id", default="")
    parser.add_argument("--deposit-id", default="")
    parser.add_argument("--deposit-cashback-flag", choices=["0", "1"], default="0")
    parser.add_argument("--deposit-rotation-flag", choices=["0", "1"], default="0")
    parser.add_argument("--deposit-external-order-id", default="")
    parser.add_argument("--deposit-status", default="")
    parser.add_argument("--deposit-lookup-attempts", type=int, default=6)
    parser.add_argument("--deposit-lookup-interval", type=float, default=1)
    parser.add_argument("--wallet-settlement-attempts", type=int, default=20)
    parser.add_argument("--wallet-settlement-interval", type=float, default=1)
    parser.add_argument("--withdraw-account-id", default="")
    parser.add_argument("--wallet-password", default="")
    parser.add_argument("--maya-account", default="")
    parser.add_argument("--maya-pid", default="")
    parser.add_argument("--maya-first-name", default="Codex")
    parser.add_argument("--maya-middle-name", default="")
    parser.add_argument("--maya-last-name", default="001")
    parser.add_argument("--withdraw-id", default="")
    parser.add_argument("--withdraw-amount", default="")
    parser.add_argument("--withdraw-client-phone", default="")
    parser.add_argument("--withdraw-client-otp", default="")
    parser.add_argument("--withdraw-status", default="")
    parser.add_argument("--withdraw-lookup-attempts", type=int, default=15)
    parser.add_argument("--withdraw-lookup-interval", type=float, default=1)
    parser.add_argument("--withdraw-mark-success", action="store_true")
    parser.add_argument("--withdraw-external-order-id", default="")
    parser.add_argument("--approval-desc", default="p0 automation")
    parser.add_argument("--approval-code", default="")
    parser.add_argument("--turnover-clear-remark", default="p0 api no-bet flow")
    parser.add_argument("--turnover-clear-attempts", type=int, default=10)
    parser.add_argument("--turnover-clear-interval", type=float, default=1)
    parser.add_argument("--turnover-discovery-attempts", type=int, default=30)
    parser.add_argument("--turnover-discovery-interval", type=float, default=1)
    args = parser.parse_args()
    if not args.out:
        args.out = (
            f"api/results/operations/{args.operation}.json"
            if args.operation
            else "api/results/controlled-write-result.json"
        )
    ACTIVE_ARGS = args

    smoke.load_env_file(Path(args.env))
    configure_operation(args)
    if args.use_register_phone or not args.operation:
        apply_primary_client_override(args)
    os.environ.pop("API_TOKEN", None)
    os.environ.pop("ADMIN_TOKEN", None)
    records: list[dict[str, object]] = []
    ACTIVE_RECORDS = records

    if args.main_positive_flow:
        args.register = True
        args.deposit = True
        args.approve_deposit = True
        # Stop at the deposit checkpoint. A real game bet and asynchronous
        # turnover reconciliation must happen before any withdrawal attempt.

    if args.register:
        if not (args.register_phone or os.environ.get("REGISTER_PHONE", "")):
            records.extend(admin_login(args))
            allocated_phone, allocation_record = allocate_registration_phone(args)
            args.register_phone = allocated_phone
            records.append(allocation_record)
        register_records = register_new_user(args)
        records.extend(register_records)
        if any(item.get("business_status") is not True for item in register_records):
            finish(args, records)
            return

    if args.complete_kyc:
        kyc_start = len(records)
        records.extend(client_login(args))
        records.append({
            "name": "register",
            "business_status": True,
            "skipped": True,
            "reason": "allocated KYC pool account already exists and authenticated",
        })
        current_detail = smoke.request_once(
            row("GET", "{{api_url}}/member/kyc/detail"), args.timeout, args.insecure
        )
        current_profile = data_of(current_detail)
        current_status = int(current_profile.get("kyc_status") or 0) if isinstance(current_profile, dict) else -1
        if current_status == 0:
            records.extend(submit_kyc(args))
            submitted = records[-1].get("data") if records else None
            current_status = int(submitted.get("kyc_status") or 0) if isinstance(submitted, dict) else 0
        else:
            records.append(result_record("kyc_detail_existing", current_detail))
            if current_status != 5:
                records.append({
                    "name": "kyc_submit",
                    "business_status": True,
                    "skipped": True,
                    "reason": f"existing submitted KYC status={current_status}",
                    "data": current_profile,
                })
        kyc_uid = resolve_kyc_uid(args, current_profile)
        if not kyc_uid:
            raise SystemExit("KYC uid is required for controlled approval")
        args.member_uid = kyc_uid
        if current_status == 5:
            existing = result_record("kyc_detail_after_approval", current_detail)
            existing["business_status"] = True
            existing["expected_kyc_status"] = 5
            existing["actual_kyc_status"] = 5
            records.extend([
                {"name": "kyc_submit", "business_status": True, "skipped": True, "reason": "KYC pool account is already approved"},
                {"name": "admin_kyc_approve", "business_status": True, "skipped": True, "reason": "KYC already approved"},
                existing,
            ])
        else:
            records.extend(admin_login(args))
            records.extend(approve_kyc(args, kyc_uid))
        if any(item.get("business_status") is False for item in records[kyc_start:]):
            finish(args, records)
            return

    if args.submit_kyc and not args.complete_kyc:
        records.extend(client_login(args))
        records.extend(submit_kyc(args))

    if args.approve_kyc and not args.complete_kyc:
        if not args.submit_kyc:
            records.extend(client_login(args))
        kyc_uid = resolve_kyc_uid(args)
        if not kyc_uid:
            detail = smoke.request_once(
                row("GET", "{{api_url}}/member/kyc/detail"), args.timeout, args.insecure
            )
            profile = data_of(detail)
            kyc_uid = resolve_kyc_uid(args, profile)
        if not kyc_uid:
            raise SystemExit("KYC uid is required for controlled approval")
        args.member_uid = kyc_uid
        records.extend(admin_login(args))
        records.extend(approve_kyc(args, kyc_uid))

    current_phone = os.environ.get("CLIENT_PHONE", "")
    withdraw_phone = (
        current_phone
        if args.use_register_phone
        else args.withdraw_client_phone or os.environ.get("WITHDRAW_CLIENT_PHONE", "")
    )
    separate_withdraw_client = bool(
        args.withdraw
        and withdraw_phone
        and "".join(filter(str.isdigit, withdraw_phone)) != "".join(filter(str.isdigit, current_phone))
    )

    if (
        args.deposit
        or args.clear_turnover
        or args.prepare_withdraw_account
        or (args.withdraw and not separate_withdraw_client)
    ):
        records.extend(client_login(args))
        if args.deposit or args.clear_turnover or args.withdraw:
            records.append(query_wallet(args, "wallet_before"))
    elif args.check_client_deposit_list or args.check_client_withdraw_list:
        records.extend(client_login(args))
    if (
        args.approve_deposit
        or args.check_admin_deposit_list
        or args.clear_turnover
        or args.approve_withdraw
        or args.check_admin_withdraw_list
    ):
        records.extend(admin_login(args))
    if args.deposit:
        if not run_deposit_stage(args, records):
            finish(args, records)
            return
        if args.approve_deposit:
            wallet_before = next(
                (item for item in records if item.get("name") == "wallet_before"),
                {},
            )
            wallet_after_deposit = wait_for_deposit_credit(
                args,
                wallet_before,
                args.deposit_amount,
            )
            records.append(wallet_after_deposit)
            if wallet_after_deposit.get("business_status") is not True:
                finish(args, records)
                return
    elif args.approve_deposit and args.deposit_id:
        if args.deposit_external_order_id:
            records.extend(
                approve_deposit(
                    args,
                    None,
                    args.deposit_id,
                    args.deposit_external_order_id,
                )
            )
        else:
            list_record, order = find_deposit_order(args, args.deposit_id)
            records.append(list_record)
            if list_record.get("business_status") is True:
                records.extend(approve_deposit(args, order, args.deposit_id, ""))
    elif args.check_admin_deposit_list:
        list_record, _ = find_deposit_order(args, args.deposit_id)
        records.append(list_record)
    if args.clear_turnover:
        uid = args.member_uid
        if not uid and os.environ.get("API_TOKEN"):
            detail = smoke.request_once(
                row("GET", "{{api_url}}/member/detail"), args.timeout, args.insecure
            )
            records.append(result_record("member_detail_for_turnover", detail))
            profile = data_of(detail)
            uid = str(profile.get("uid") or "") if isinstance(profile, dict) else ""
        if not uid:
            raise SystemExit("member uid is required before clearing turnover")
        args.member_uid = uid
        wallet_checkpoint = next(
            (
                item
                for item in reversed(records)
                if item.get("name") in {"wallet_after_deposit", "wallet_before"}
            ),
            {},
        )
        wallet_data = wallet_checkpoint.get("data")
        expected_locked = (
            decimal_value(wallet_data.get("locked"))
            if isinstance(wallet_data, dict)
            else None
        )
        turnover_records = run_turnover_clear(args, uid, expected_locked)
        records.extend(turnover_records)
        if any(item.get("business_status") is not True for item in turnover_records):
            finish(args, records)
            return
    if args.prepare_withdraw_account:
        prepare_records = prepare_withdraw_account(args)
        records.extend(prepare_records)
        if any(item.get("business_status") is not True for item in prepare_records):
            finish(args, records)
            return
    created_withdraw_id = ""
    if args.withdraw and separate_withdraw_client:
        previous_phone, previous_password, previous_otp, previous_token = use_withdraw_client(args)
        try:
            records.extend(relabel(client_login(args), "withdraw"))
            records.append(query_wallet(args, "withdraw_wallet_before"))
            withdrawable_record = wait_for_withdrawable_funds(args)
            records.append(withdrawable_record)
            if withdrawable_record.get("business_status") is not True:
                finish(args, records)
                return
            withdraw_ok, withdraw_id = run_withdraw_stage(args, records)
            if not withdraw_ok:
                finish(args, records)
                return
            created_withdraw_id = withdraw_id
            if args.check_admin_withdraw_list:
                records.extend(check_admin_withdraw_list(args, withdraw_id))
            if args.approve_withdraw:
                list_record, order = find_withdraw_order(args, withdraw_id)
                records.append(list_record)
                records.extend(approve_withdraw(args, order))
            records.append(query_wallet(args, "withdraw_wallet_after"))
        finally:
            restore_client(previous_phone, previous_password, previous_otp, previous_token)
    elif args.withdraw:
        withdrawable_record = wait_for_withdrawable_funds(args)
        records.append(withdrawable_record)
        if withdrawable_record.get("business_status") is not True:
            finish(args, records)
            return
        withdraw_ok, withdraw_id = run_withdraw_stage(args, records)
        if not withdraw_ok:
            finish(args, records)
            return
        created_withdraw_id = withdraw_id
        if args.check_admin_withdraw_list:
            records.extend(check_admin_withdraw_list(args, withdraw_id))
        if args.approve_withdraw:
            list_record, order = find_withdraw_order(args, withdraw_id)
            records.append(list_record)
            records.extend(approve_withdraw(args, order))
    elif args.approve_withdraw and args.withdraw_id:
        list_record, order = find_withdraw_order(args, args.withdraw_id)
        records.append(list_record)
        if list_record.get("business_status") is True:
            records.extend(approve_withdraw(args, order))
    elif args.check_admin_withdraw_list:
        records.extend(check_admin_withdraw_list(args, args.withdraw_id))
    if args.check_client_withdraw_list:
        records.extend(check_client_withdraw_list(args, args.withdraw_id or created_withdraw_id))
    if args.check_client_deposit_list:
        records.extend(check_client_deposit_list(args, args.deposit_id))
    if args.deposit or (args.withdraw and not separate_withdraw_client):
        records.append(query_wallet(args, "wallet_after"))

    finish(args, records)


if __name__ == "__main__":
    try:
        main()
    except BaseException as error:
        if (
            ACTIVE_ARGS
            and (ACTIVE_ARGS.operation or ACTIVE_ARGS.flow_name)
            and not OPERATION_REPORT_WRITTEN
        ):
            message = str(error) or type(error).__name__
            sensitive_markers = ("PASSWORD", "SECRET", "TOKEN", "OTP", "CODE", "PHONE", "EMAIL")
            for name, value in os.environ.items():
                if value and any(marker in name.upper() for marker in sensitive_markers):
                    message = message.replace(value, "<redacted>")
            message = message[:1000]
            failure_records = list(ACTIVE_RECORDS or [])
            failure_records.append({
                "name": "operation_error",
                "business_status": False,
                "reason": message,
            })
            try:
                finish(ACTIVE_ARGS, failure_records)
            except BaseException:
                pass
            raise SystemExit(message) from None
        raise
