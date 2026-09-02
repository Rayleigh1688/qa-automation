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
import time
import uuid
from pathlib import Path
from types import ModuleType
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

from p0_session import load_session, write_session
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
    explicit = args.approval_code or os.environ.get("ADMIN_APPROVAL_CODE", "")
    if explicit:
        return explicit
    secret = os.environ.get("ADMIN_APPROVAL_TOTP_SECRET", "")
    algorithm = os.environ.get("ADMIN_APPROVAL_TOTP_ALGORITHM", "SHA1")
    return current_totp(secret, algorithm=algorithm) if secret else ""


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


def query_wallet(args: argparse.Namespace, name: str) -> dict[str, object]:
    result = smoke.request_once(
        row("GET", "{{api_url}}/finance/wallet"),
        args.timeout,
        args.insecure,
    )
    return result_record(name, result)


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
        records.append({"name": "register", "skipped": True, "reason": "missing otp_id", "phone": phone})
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
    register_record = result_record("register", register_result)
    register_record["phone"] = phone
    records.append(register_record)
    return records


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
    body = add_approval_code({"uid": target_uid, "desc": args.approval_desc}, args)
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

    detail = smoke.request_once(
        row("GET", "{{api_url}}/member/kyc/detail"), args.timeout, args.insecure
    )
    detail_record = result_record("kyc_detail_after_approval", detail)
    profile = data_of(detail)
    approved = isinstance(profile, dict) and int(profile.get("kyc_status") or 0) == 5
    detail_record["business_status"] = approved
    detail_record["expected_kyc_status"] = 5
    detail_record["actual_kyc_status"] = profile.get("kyc_status") if isinstance(profile, dict) else None
    records.append(detail_record)
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


def check_client_withdraw_list(args: argparse.Namespace) -> list[dict[str, object]]:
    result = smoke.request_once(
        row("GET", "{{api_url}}/finance/withdraw/list?time_flag=0&page=1&page_size=10"),
        args.timeout,
        args.insecure,
    )
    rows = list_rows(data_of(result))
    record = result_record("client_withdraw_list", result)
    record["matched_order"] = rows[0] if rows else None
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
    record = result_record("admin_withdraw_risk_audit_list", result)
    record["matched_order"] = target
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", default=os.environ.get("ENV_FILE", ".env.fat"))
    parser.add_argument("--timeout", type=float, default=10)
    parser.add_argument("--insecure", action="store_true")
    parser.add_argument("--body-format", choices=["json", "cbor"], default="cbor")
    parser.add_argument("--out", default="api/results/controlled-write-result.json")
    parser.add_argument("--session-in", default="", help="Reuse an ignored P0 client/admin token session when account hashes match")
    parser.add_argument("--session-out", default="", help="Persist the current P0 client/admin token session to an ignored file")
    parser.add_argument("--register", action="store_true")
    parser.add_argument("--submit-kyc", action="store_true")
    parser.add_argument("--approve-kyc", action="store_true")
    parser.add_argument("--complete-kyc", action="store_true", help="Submit when ready, approve pending record, then verify client status")
    parser.add_argument("--deposit", action="store_true")
    parser.add_argument("--approve-deposit", action="store_true")
    parser.add_argument("--withdraw", action="store_true")
    parser.add_argument("--approve-withdraw", action="store_true")
    parser.add_argument("--check-client-withdraw-list", action="store_true")
    parser.add_argument("--check-admin-withdraw-list", action="store_true")
    parser.add_argument("--main-positive-flow", action="store_true")
    parser.add_argument("--client-phone", default="")
    parser.add_argument("--client-otp", default="")
    parser.add_argument("--register-phone", default="")
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
    parser.add_argument("--deposit-pid", default="")
    parser.add_argument("--deposit-amount", default="")
    parser.add_argument("--deposit-product-id", default="")
    parser.add_argument("--deposit-id", default="")
    parser.add_argument("--deposit-cashback-flag", choices=["0", "1"], default="0")
    parser.add_argument("--deposit-rotation-flag", choices=["0", "1"], default="0")
    parser.add_argument("--deposit-external-order-id", default="")
    parser.add_argument("--deposit-status", default="")
    parser.add_argument("--withdraw-account-id", default="")
    parser.add_argument("--withdraw-id", default="")
    parser.add_argument("--withdraw-amount", default="")
    parser.add_argument("--withdraw-client-phone", default="")
    parser.add_argument("--withdraw-client-otp", default="")
    parser.add_argument("--withdraw-status", default="")
    parser.add_argument("--withdraw-mark-success", action="store_true")
    parser.add_argument("--withdraw-external-order-id", default="")
    parser.add_argument("--approval-desc", default="p0 automation")
    parser.add_argument("--approval-code", default="")
    args = parser.parse_args()

    smoke.load_env_file(Path(args.env))
    apply_primary_client_override(args)
    if args.session_in:
        load_session(args.session_in, os.environ.get("CLIENT_PHONE", ""))
    records: list[dict[str, object]] = []

    if args.main_positive_flow:
        args.register = True
        args.deposit = True
        args.approve_deposit = True
        # Stop at the deposit checkpoint. A real game bet and asynchronous
        # turnover reconciliation must happen before any withdrawal attempt.

    if args.register:
        records.extend(register_new_user(args))

    if args.complete_kyc:
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
        kyc_uid = args.kyc_uid or os.environ.get("KYC_CLIENT_UID", "")
        if not kyc_uid and isinstance(current_profile, dict):
            kyc_uid = str(current_profile.get("uid") or "")
        if not kyc_uid:
            raise SystemExit("KYC uid is required for controlled approval")
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

    if args.submit_kyc and not args.complete_kyc:
        records.extend(client_login(args))
        records.extend(submit_kyc(args))

    if args.approve_kyc and not args.complete_kyc:
        if not args.submit_kyc:
            records.extend(client_login(args))
        kyc_uid = args.kyc_uid or os.environ.get("KYC_CLIENT_UID", "")
        if not kyc_uid:
            detail = smoke.request_once(
                row("GET", "{{api_url}}/member/kyc/detail"), args.timeout, args.insecure
            )
            profile = data_of(detail)
            kyc_uid = str(profile.get("uid") or "") if isinstance(profile, dict) else ""
        if not kyc_uid:
            raise SystemExit("KYC uid is required for controlled approval")
        records.extend(admin_login(args))
        records.extend(approve_kyc(args, kyc_uid))

    withdraw_phone = args.withdraw_client_phone or os.environ.get("WITHDRAW_CLIENT_PHONE", "")
    current_phone = os.environ.get("CLIENT_PHONE", "")
    separate_withdraw_client = bool(
        args.withdraw
        and withdraw_phone
        and "".join(filter(str.isdigit, withdraw_phone)) != "".join(filter(str.isdigit, current_phone))
    )

    if args.deposit or (args.withdraw and not separate_withdraw_client):
        records.extend(client_login(args))
        records.append(query_wallet(args, "wallet_before"))
    elif args.check_client_withdraw_list:
        records.extend(client_login(args))
    if args.approve_deposit or args.approve_withdraw or args.check_admin_withdraw_list:
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
    elif args.approve_deposit and args.deposit_id:
        list_record, order = find_deposit_order(args, args.deposit_id)
        records.append(list_record)
        records.extend(approve_deposit(args, order, args.deposit_id, args.deposit_external_order_id))
    if args.withdraw and separate_withdraw_client:
        previous_phone, previous_password, previous_otp, previous_token = use_withdraw_client(args)
        try:
            records.extend(relabel(client_login(args), "withdraw"))
            records.append(query_wallet(args, "withdraw_wallet_before"))
            withdraw_records = run_withdraw(args)
            records.extend(withdraw_records)
            withdraw_data = withdraw_records[-1].get("data")
            withdraw_id = str(withdraw_data.get("id") or withdraw_data.get("order_no") or "") if isinstance(withdraw_data, dict) else ""
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
        withdraw_records = run_withdraw(args)
        records.extend(withdraw_records)
        withdraw_data = withdraw_records[-1].get("data")
        withdraw_id = str(withdraw_data.get("id") or withdraw_data.get("order_no") or "") if isinstance(withdraw_data, dict) else ""
        if args.check_admin_withdraw_list:
            records.extend(check_admin_withdraw_list(args, withdraw_id))
        if args.approve_withdraw:
            list_record, order = find_withdraw_order(args, withdraw_id)
            records.append(list_record)
            records.extend(approve_withdraw(args, order))
    elif args.approve_withdraw and args.withdraw_id:
        list_record, order = find_withdraw_order(args, args.withdraw_id)
        records.append(list_record)
        records.extend(approve_withdraw(args, order))
    elif args.check_admin_withdraw_list:
        records.extend(check_admin_withdraw_list(args, args.withdraw_id))
    if args.check_client_withdraw_list:
        records.extend(check_client_withdraw_list(args))
    if args.deposit or (args.withdraw and not separate_withdraw_client):
        records.append(query_wallet(args, "wallet_after"))

    output = Path(args.out)
    output.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.session_out:
        write_session(
            args.session_out,
            client_token=os.environ.get("API_TOKEN", ""),
            admin_token=os.environ.get("ADMIN_TOKEN", ""),
            client_phone=os.environ.get("CLIENT_PHONE", ""),
        )
    print(f"wrote {output.resolve()}")
    for item in records:
        status = item.get("business_status")
        print(f"{item.get('name')} http={item.get('http_status')} business={status} url={item.get('url', '')}")
    failed_names = [
        str(item.get("name") or "unnamed")
        for item in records
        if item.get("business_status") is False
    ]
    if failed_names:
        raise SystemExit("controlled flow business failure: " + ", ".join(failed_names))


if __name__ == "__main__":
    main()
