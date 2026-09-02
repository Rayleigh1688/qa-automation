#!/usr/bin/env python3
"""Provision one test member through registration, KYC approval, and deposit credit."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
DEFAULT_OUTPUT_DIR = ROOT / "api/results/provisioning"
DEFAULT_PHONE_START = "9000000001"


class ProvisioningError(RuntimeError):
    pass


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ProvisioningError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sys.path.insert(0, str(SCRIPTS))
smoke = load_module("api_smoke_runner", SCRIPTS / "api-smoke-runner.py")
p0_session = load_module("p0_session_for_provisioning", SCRIPTS / "p0_session.py")


def controlled_row(method: str, clean_url: str, base_var: str) -> dict[str, str]:
    return {
        "priority": "PROVISION",
        "method": method,
        "clean_url": clean_url,
        "suggested_base_var": base_var,
    }


def business_data(result: dict[str, object]) -> object:
    body = result.get("decoded_body")
    if not isinstance(body, dict) or body.get("status") is not True:
        raise ProvisioningError("admin member lookup returned a business failure")
    return body.get("data")


def member_rows(args: argparse.Namespace, phone: str) -> list[dict[str, object]]:
    result = smoke.request_once(
        controlled_row("POST", "{{admin_url}}/admin/member/list", "{{admin_url}}"),
        args.timeout,
        args.insecure,
        {"page": 1, "page_size": 10, "phone": phone},
        "cbor",
    )
    data = business_data(result)
    rows = data.get("d") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        raise ProvisioningError("admin member list data.d is not a list")
    return [item for item in rows if isinstance(item, dict)]


def exact_member_exists(args: argparse.Namespace, phone: str) -> bool:
    return any(str(item.get("phone") or "") == phone for item in member_rows(args, phone))


def validate_test_environment(env_path: Path) -> None:
    urls = [os.environ.get("API_URL", ""), os.environ.get("ADMIN_URL", "")]
    if not all(urls):
        raise ProvisioningError("API_URL and ADMIN_URL are required")
    env_name = env_path.name.lower()
    if not any(marker in env_name for marker in ("fat", "uat", "test", "staging")):
        raise ProvisioningError("environment filename must explicitly identify FAT, UAT, test, or staging")
    forbidden_markers = ("prod", "production")
    for url in urls:
        lowered = url.lower()
        if any(marker in lowered for marker in forbidden_markers):
            raise ProvisioningError(f"refusing provisioning against a production-like URL: {url}")


def find_unused_phone(args: argparse.Namespace) -> str:
    known_phone = os.environ.get("CLIENT_PHONE") or os.environ.get("WRITE_CLIENT_PHONE", "")
    if not known_phone:
        raise ProvisioningError("CLIENT_PHONE or WRITE_CLIENT_PHONE is required to validate exact admin filtering")
    if not exact_member_exists(args, known_phone):
        raise ProvisioningError("admin phone filter could not locate the configured known member")

    start = (
        args.start_phone
        or os.environ.get("REGISTER_PHONE")
        or os.environ.get("PROVISION_PHONE_START")
        or DEFAULT_PHONE_START
    )
    if not start or not start.isdigit():
        raise ProvisioningError(
            "--start-phone, REGISTER_PHONE, or PROVISION_PHONE_START must be numeric"
        )
    width = len(start)
    start_number = int(start)
    for offset in range(args.scan_limit):
        candidate = str(start_number + offset).zfill(width)
        if not exact_member_exists(args, candidate):
            return candidate
    raise ProvisioningError(f"no unused phone found within {args.scan_limit} candidates")


def secure_write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    path.chmod(0o600)


def ensure_ignored_output_dir(path: Path) -> Path:
    resolved = path.resolve()
    allowed = (ROOT / "api/results").resolve()
    try:
        resolved.relative_to(allowed)
    except ValueError as error:
        raise ProvisioningError("--out-dir must stay under the ignored api/results directory") from error
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def stage_records(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        raise ProvisioningError(f"stage result is missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ProvisioningError(f"stage result is not a list: {path}")
    path.chmod(0o600)
    return [item for item in payload if isinstance(item, dict)]


def named_record(records: list[dict[str, object]], name: str) -> dict[str, object]:
    record = next((item for item in records if item.get("name") == name), None)
    if not record:
        raise ProvisioningError(f"required stage record is missing: {name}")
    return record


def require_business_true(records: list[dict[str, object]], name: str) -> dict[str, object]:
    record = named_record(records, name)
    if record.get("business_status") is not True:
        raise ProvisioningError(f"stage record did not pass: {name}")
    return record


def validate_deposit_checkpoint(
    records: list[dict[str, object]], expected_amount: str
) -> dict[str, object]:
    created = require_business_true(records, "deposit_create")
    pending_list = require_business_true(records, "admin_deposit_risk_list")
    manual = require_business_true(records, "admin_deposit_manual_success")
    wallet_before = require_business_true(records, "wallet_before")
    wallet_after = require_business_true(records, "wallet_after")

    created_data = created.get("data")
    created_order_id = created_data.get("order_id") if isinstance(created_data, dict) else None
    manual_order_id = manual.get("deposit_id")
    if created_order_id is None or manual_order_id is None:
        raise ProvisioningError("deposit order correlation fields are missing")
    if str(created_order_id) != str(manual_order_id):
        raise ProvisioningError("manual success did not process the newly created deposit")

    before_data = wallet_before.get("data")
    after_data = wallet_after.get("data")
    if not isinstance(before_data, dict) or not isinstance(after_data, dict):
        raise ProvisioningError("wallet checkpoint data is missing")
    try:
        balance_delta = Decimal(str(after_data["balance"])) - Decimal(str(before_data["balance"]))
        amount = Decimal(str(expected_amount))
    except (KeyError, InvalidOperation, TypeError, ValueError) as error:
        raise ProvisioningError("wallet balance checkpoint is not numeric") from error
    if balance_delta != amount:
        raise ProvisioningError(
            f"wallet balance delta {balance_delta} did not equal deposit amount {amount}"
        )

    return {
        "same_created_order": True,
        "wallet_balance_delta": str(balance_delta),
        "pending_list_matched": isinstance(pending_list.get("matched_order"), dict),
    }


def run_stage(
    name: str,
    arguments: list[str],
    env: dict[str, str],
    result_path: Path,
    output_dir: Path,
) -> list[dict[str, object]]:
    completed = subprocess.run(
        [sys.executable, str(SCRIPTS / "api-controlled-flow-runner.py"), *arguments],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    log_path = output_dir / f"{name}.log"
    log_path.write_text(completed.stdout + completed.stderr, encoding="utf-8")
    log_path.chmod(0o600)
    if completed.returncode != 0:
        raise ProvisioningError(f"{name} process failed; inspect {log_path}")
    return stage_records(result_path)


def masked_phone(phone: str) -> str:
    return "*" * max(len(phone) - 4, 0) + phone[-4:]


def require_result_status(result: dict[str, object], name: str) -> object:
    body = result.get("decoded_body")
    if not isinstance(body, dict) or body.get("status") is not True:
        raise ProvisioningError(f"{name} returned a business failure")
    return body.get("data")


def account_rows(data: object) -> list[dict[str, object]]:
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def safe_result_record(name: str, result: dict[str, object]) -> dict[str, object]:
    body = result.get("decoded_body")
    record: dict[str, object] = {
        "name": name,
        "http_status": result.get("status"),
        "business_status": body.get("status") if isinstance(body, dict) else None,
    }
    if isinstance(body, dict):
        for key in ("code", "msg", "message"):
            if key in body:
                record[key] = body[key]
    return record


def valid_login_password(value: str) -> bool:
    return (
        8 <= len(value) <= 20
        and any(character.isalpha() for character in value)
        and any(character.isdigit() for character in value)
    )


def wallet_password_body(password: str) -> dict[str, str]:
    return {"pwd": password}


def login_password_auth_body(
    phone: str, country_code: str, otp_id: str, code: str
) -> dict[str, object]:
    return {
        "code": code,
        "phone": phone,
        "country_code": country_code,
        "otp_id": otp_id,
    }


def login_password_update_body(
    otp_id: str, code: str, new_password: str
) -> dict[str, object]:
    return {
        "code": code,
        "new_password": new_password,
        "otp_id": otp_id,
    }


def core_stages_pass(summary: dict[str, object]) -> bool:
    stages = summary.get("stages")
    return isinstance(stages, dict) and all(
        stages.get(name) == "PASS" for name in ("register", "kyc", "deposit")
    )


def mark_extension(
    summary: dict[str, object],
    name: str,
    status: str,
    **details: object,
) -> None:
    extensions = summary.get("extensions")
    if not isinstance(extensions, dict):
        extensions = {}
        summary["extensions"] = extensions
    extensions[name] = {"status": status, **details}


def ensure_client_session(
    args: argparse.Namespace,
    phone: str,
    session_path: Path,
) -> dict[str, object]:
    loaded = p0_session.load_session(str(session_path), phone)
    if loaded.get("client"):
        profile = smoke.request_once(
            controlled_row("GET", "{{api_url}}/member/detail", "{{api_url}}"),
            args.timeout,
            args.insecure,
        )
        body = profile.get("decoded_body")
        if isinstance(body, dict) and body.get("status") is True:
            return profile
    raise ProvisioningError(
        "saved client session is stale; refresh or export the current session before this step"
    )


def prepare_withdrawal_account(
    args: argparse.Namespace,
    output_dir: Path,
    summary: dict[str, object],
) -> dict[str, object]:
    phone = str(summary.get("phone") or "")
    if not phone:
        raise ProvisioningError("existing provisioning summary has no member phone")
    password = args.wallet_password or os.environ.get("CLIENT_WALLET_PASSWORD", "")
    maya_account = args.maya_account or os.environ.get("PROVISION_MAYA_ACCOUNT", "")
    maya_pid = args.maya_pid or os.environ.get("PROVISION_MAYA_PID", "")
    if not (password.isdigit() and len(password) == 6):
        raise ProvisioningError("wallet password must be a 6-digit value")
    if not maya_account.isdigit() or not maya_pid.isdigit():
        raise ProvisioningError("Maya account and channel pid must be numeric")

    session_path = output_dir / "member-bootstrap-session.json"
    result_path = output_dir / "member-withdraw-account.json"
    if result_path.exists():
        previous = stage_records(result_path)
        if any(
            item.get("name") == "withdraw_account_after"
            and item.get("business_status") is True
            and item.get("matched_account") is True
            for item in previous
        ):
            return {"account_masked": masked_phone(maya_account), "insert_performed": False}

    records: list[dict[str, object]] = []
    profile = ensure_client_session(args, phone, session_path)
    profile_record = safe_result_record("member_detail", profile)
    records.append(profile_record)
    secure_write(result_path, records)
    profile_data = require_result_status(profile, "member_detail")
    has_wallet_password = (
        profile_data.get("has_wallet_password") if isinstance(profile_data, dict) else None
    )
    profile_record["has_wallet_password"] = has_wallet_password
    secure_write(result_path, records)
    if has_wallet_password is not True:
        set_password = smoke.request_once(
            controlled_row("POST", "{{api_url}}/finance/wallet/pwd/set", "{{api_url}}"),
            args.timeout,
            args.insecure,
            wallet_password_body(password),
            "cbor",
            content_type="application/json",
        )
        records.append(safe_result_record("wallet_password_set", set_password))
        secure_write(result_path, records)
        require_result_status(set_password, "wallet_password_set")

        profile_after = smoke.request_once(
            controlled_row("GET", "{{api_url}}/member/detail", "{{api_url}}"),
            args.timeout,
            args.insecure,
        )
        profile_after_data = require_result_status(
            profile_after, "member_detail_after_wallet_password"
        )
        confirmed = (
            profile_after_data.get("has_wallet_password")
            if isinstance(profile_after_data, dict)
            else None
        )
        records.append({
            **safe_result_record("member_detail_after_wallet_password", profile_after),
            "has_wallet_password": confirmed,
        })
        secure_write(result_path, records)
        if confirmed is not True:
            raise ProvisioningError(
                "wallet password set succeeded but member detail did not confirm it"
            )

    check = smoke.request_once(
        controlled_row("POST", "{{api_url}}/finance/wallet/pwd/check", "{{api_url}}"),
        args.timeout,
        args.insecure,
        wallet_password_body(password),
        "cbor",
        content_type="application/json",
    )
    records.append(safe_result_record("wallet_password_check", check))
    secure_write(result_path, records)
    require_result_status(check, "wallet_password_check")

    before = smoke.request_once(
        controlled_row("GET", "{{api_url}}/finance/account/list", "{{api_url}}"),
        args.timeout,
        args.insecure,
    )
    before_data = require_result_status(before, "withdraw_account_before")
    existing = next(
        (item for item in account_rows(before_data) if str(item.get("account") or "") == maya_account),
        None,
    )
    records.append({
        "name": "withdraw_account_before",
        "http_status": before.get("status"),
        "business_status": True,
        "matched_account": existing is not None,
    })
    secure_write(result_path, records)

    if existing is None:
        insert = smoke.request_once(
            controlled_row("POST", "{{api_url}}/finance/account/insert", "{{api_url}}"),
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
            "cbor",
            content_type="application/json",
        )
        records.append(safe_result_record("withdraw_account_insert", insert))
        secure_write(result_path, records)
        insert_data = require_result_status(insert, "withdraw_account_insert")
        records[-1]["data"] = insert_data
    else:
        records.append({
            "name": "withdraw_account_insert",
            "business_status": True,
            "skipped": True,
            "reason": "matching Maya account already exists",
        })

    after = smoke.request_once(
        controlled_row("GET", "{{api_url}}/finance/account/list", "{{api_url}}"),
        args.timeout,
        args.insecure,
    )
    after_data = require_result_status(after, "withdraw_account_after")
    matched = next(
        (item for item in account_rows(after_data) if str(item.get("account") or "") == maya_account),
        None,
    )
    records.append({
        "name": "withdraw_account_after",
        "http_status": after.get("status"),
        "business_status": True,
        "matched_account": matched is not None,
        "data": matched,
    })
    secure_write(result_path, records)
    if matched is None:
        raise ProvisioningError("Maya account insert succeeded but account list did not return it")
    return {"account_masked": masked_phone(maya_account), "insert_performed": existing is None}


def prepare_login_password(
    args: argparse.Namespace,
    output_dir: Path,
    summary: dict[str, object],
) -> dict[str, object]:
    phone = str(summary.get("phone") or "")
    if not phone:
        raise ProvisioningError("existing provisioning summary has no member phone")
    session_path = output_dir / "member-bootstrap-session.json"
    result_path = output_dir / "member-login-password.json"
    profile = ensure_client_session(args, phone, session_path)
    profile_data = require_result_status(profile, "member_detail_before_login_password")
    has_login_password = (
        profile_data.get("has_login_password") if isinstance(profile_data, dict) else None
    )
    records = [
        {
            **safe_result_record("member_detail_before_login_password", profile),
            "has_login_password": has_login_password,
        }
    ]
    secure_write(result_path, records)
    if has_login_password is True:
        return {"already_set": True, "update_performed": False}

    otp_id = args.login_password_otp_id or os.environ.get("PROVISION_LOGIN_PASSWORD_OTP_ID", "")
    code = args.login_password_code or os.environ.get("PROVISION_LOGIN_PASSWORD_CODE", "")
    new_password = args.login_password or os.environ.get("PROVISION_LOGIN_PASSWORD", "")
    country_code = os.environ.get("REGISTER_COUNTRY_CODE", "63")
    if not (otp_id.isdigit() and code.isdigit() and len(code) == 6):
        raise ProvisioningError("login password setup requires a numeric otp id and 6-digit code")
    if not valid_login_password(new_password):
        raise ProvisioningError("login password must be 8-20 characters with at least one letter and one number")

    auth = smoke.request_once(
        controlled_row("POST", "{{api_url}}/member/auth/sms", "{{api_url}}"),
        args.timeout,
        args.insecure,
        login_password_auth_body(phone, country_code, otp_id, code),
        "cbor",
        content_type="application/json",
    )
    records.append(safe_result_record("login_password_sms_auth", auth))
    secure_write(result_path, records)
    require_result_status(auth, "login_password_sms_auth")

    update = smoke.request_once(
        controlled_row("POST", "{{api_url}}/member/retrieve/password", "{{api_url}}"),
        args.timeout,
        args.insecure,
        login_password_update_body(otp_id, code, new_password),
        "cbor",
        content_type="application/json",
    )
    records.append(safe_result_record("login_password_update", update))
    secure_write(result_path, records)
    require_result_status(update, "login_password_update")

    after = smoke.request_once(
        controlled_row("GET", "{{api_url}}/member/detail", "{{api_url}}"),
        args.timeout,
        args.insecure,
    )
    after_data = require_result_status(after, "member_detail_after_login_password")
    updated = after_data.get("has_login_password") if isinstance(after_data, dict) else None
    records.append({
        **safe_result_record("member_detail_after_login_password", after),
        "has_login_password": updated,
    })
    secure_write(result_path, records)
    if updated is not True:
        raise ProvisioningError("password update succeeded but member detail did not confirm it")
    return {"already_set": False, "update_performed": True}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create one test member, approve KYC, and credit one controlled deposit."
    )
    parser.add_argument("--env", default=os.environ.get("ENV_FILE", ".env.fat"))
    parser.add_argument("--start-phone", default="")
    parser.add_argument("--scan-limit", type=int, default=200)
    parser.add_argument("--execute", action="store_true", help="Perform registration, KYC approval, and deposit credit")
    parser.add_argument(
        "--prepare-withdrawal",
        action="store_true",
        help="For the existing provisioned member, verify wallet password and idempotently bind Maya",
    )
    parser.add_argument(
        "--set-login-password",
        action="store_true",
        help="For the existing provisioned member, verify SMS OTP and set a login password",
    )
    parser.add_argument(
        "--validate-existing",
        action="store_true",
        help="Validate existing local stage artifacts without replaying any request",
    )
    parser.add_argument("--deposit-amount", default="")
    parser.add_argument("--deposit-pid", default="")
    parser.add_argument("--kyc-image", default="")
    parser.add_argument("--approval-desc", default="test data provisioning")
    parser.add_argument("--wallet-password", default="")
    parser.add_argument("--maya-account", default="")
    parser.add_argument("--maya-pid", default="")
    parser.add_argument("--maya-first-name", default="Codex")
    parser.add_argument("--maya-middle-name", default="")
    parser.add_argument("--maya-last-name", default="001")
    parser.add_argument("--login-password", default="")
    parser.add_argument("--login-password-otp-id", default="")
    parser.add_argument("--login-password-code", default="")
    parser.add_argument("--timeout", type=float, default=20)
    parser.add_argument("--insecure", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--out-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    args.body_format = "cbor"
    selected_modes = sum(
        bool(value)
        for value in (args.prepare_withdrawal, args.set_login_password, args.validate_existing)
    )
    if selected_modes > 1:
        parser.error("--prepare-withdrawal, --set-login-password, and --validate-existing are mutually exclusive")

    env_path = Path(args.env)
    smoke.load_env_file(env_path)
    validate_test_environment(env_path)
    output_dir = ensure_ignored_output_dir(Path(args.out_dir))
    summary_path = output_dir / "member-bootstrap-summary.json"
    summary: dict[str, object] = {
        "environment_file": str(Path(args.env)),
        "executed": args.execute,
        "status": "DISCOVERY",
        "stages": {},
    }

    active_extension = ""
    try:
        if args.prepare_withdrawal:
            active_extension = "withdraw_account"
            if not args.execute:
                raise ProvisioningError("--prepare-withdrawal is a write operation and requires --execute")
            if not summary_path.exists():
                raise ProvisioningError(f"summary is missing: {summary_path}")
            existing_summary = json.loads(summary_path.read_text(encoding="utf-8"))
            if not isinstance(existing_summary, dict):
                raise ProvisioningError("existing summary is not an object")
            summary = existing_summary
            evidence = prepare_withdrawal_account(args, output_dir, summary)
            mark_extension(summary, active_extension, "PASS", **evidence)
            if core_stages_pass(summary):
                summary["status"] = "PASS"
            summary.pop("error", None)
            secure_write(summary_path, summary)
            print(f"stage_withdraw_account=PASS summary={summary_path}")
            return

        if args.set_login_password:
            active_extension = "login_password"
            if not args.execute:
                raise ProvisioningError("--set-login-password is a write operation and requires --execute")
            if not summary_path.exists():
                raise ProvisioningError(f"summary is missing: {summary_path}")
            existing_summary = json.loads(summary_path.read_text(encoding="utf-8"))
            if not isinstance(existing_summary, dict):
                raise ProvisioningError("existing summary is not an object")
            summary = existing_summary
            evidence = prepare_login_password(args, output_dir, summary)
            mark_extension(summary, active_extension, "PASS", **evidence)
            if core_stages_pass(summary):
                summary["status"] = "PASS"
            summary.pop("error", None)
            secure_write(summary_path, summary)
            print(f"stage_login_password=PASS summary={summary_path}")
            return

        if args.validate_existing:
            if not summary_path.exists():
                raise ProvisioningError(f"summary is missing: {summary_path}")
            existing_summary = json.loads(summary_path.read_text(encoding="utf-8"))
            if not isinstance(existing_summary, dict):
                raise ProvisioningError("existing summary is not an object")
            summary = existing_summary
            register_records = stage_records(output_dir / "member-register.json")
            kyc_records = stage_records(output_dir / "member-kyc.json")
            deposit_records = stage_records(output_dir / "member-deposit.json")
            require_business_true(register_records, "register")
            require_business_true(kyc_records, "kyc_submit")
            require_business_true(kyc_records, "admin_kyc_approve")
            approved = require_business_true(kyc_records, "kyc_detail_after_approval")
            if approved.get("actual_kyc_status") != 5:
                raise ProvisioningError("client KYC status did not refresh to 5")
            deposit_amount = (
                args.deposit_amount
                or str(summary.get("deposit_amount") or "")
                or os.environ.get("P0_DEPOSIT_AMOUNT", "1200")
            )
            deposit_evidence = validate_deposit_checkpoint(deposit_records, deposit_amount)
            summary["stages"] = {"register": "PASS", "kyc": "PASS", "deposit": "PASS"}
            summary["status"] = "PASS"
            summary["deposit_amount"] = deposit_amount
            summary["validation"] = {**deposit_evidence, "requests_replayed": False}
            summary.pop("error", None)
            secure_write(summary_path, summary)
            print(f"validation=PASS requests_replayed=false summary={summary_path}")
            return

        _, admin_token = smoke.admin_login(args)
        if not admin_token:
            raise ProvisioningError("admin login failed")
        os.environ["ADMIN_TOKEN"] = admin_token
        phone = find_unused_phone(args)
        summary["phone"] = phone
        summary["phone_masked"] = masked_phone(phone)
        summary["status"] = "PLANNED"
        secure_write(summary_path, summary)
        print(f"unused_phone=FOUND masked={masked_phone(phone)}")
        print(f"plan={summary_path}")
        if not args.execute:
            print("dry-run only; add --execute for registration, KYC approval, and deposit credit")
            return

        image_path = Path(args.kyc_image or os.environ.get("KYC_IMAGE") or "21000000008072.webp")
        if not image_path.is_file():
            raise ProvisioningError(f"KYC image does not exist: {image_path}")
        if exact_member_exists(args, phone):
            raise ProvisioningError("selected phone became registered before execution")

        deposit_amount = args.deposit_amount or os.environ.get("P0_DEPOSIT_AMOUNT", "1200")
        deposit_pid = args.deposit_pid or os.environ.get("PROVISION_DEPOSIT_PID", "")
        session_path = output_dir / "member-bootstrap-session.json"
        register_path = output_dir / "member-register.json"
        kyc_path = output_dir / "member-kyc.json"
        deposit_path = output_dir / "member-deposit.json"
        child_env = {
            **os.environ,
            "ENV_FILE_PRECEDENCE": "shell",
            "REGISTER_PHONE": phone,
            "CLIENT_PHONE": phone,
            "WRITE_CLIENT_PHONE": phone,
            "KYC_CLIENT_PHONE": phone,
            "CLIENT_OTP_SOURCE": "admin_sms",
            "REGISTER_OTP_SOURCE": "admin_sms",
            "REGISTER_COUNTRY_CODE": os.environ.get("REGISTER_COUNTRY_CODE", "63"),
        }
        child_env.pop("API_TOKEN", None)

        register_records = run_stage(
            "register",
            [
                "--env", args.env,
                "--register",
                "--register-phone", phone,
                "--body-format", "cbor",
                "--out", str(register_path),
                "--session-out", str(session_path),
                *(["--insecure"] if args.insecure else []),
            ],
            child_env,
            register_path,
            output_dir,
        )
        require_business_true(register_records, "register")
        summary["stages"]["register"] = "PASS"
        secure_write(summary_path, summary)
        print("stage_register=PASS")

        kyc_records = run_stage(
            "kyc",
            [
                "--env", args.env,
                "--complete-kyc",
                "--client-phone", phone,
                "--kyc-image", str(image_path),
                "--approval-desc", args.approval_desc,
                "--body-format", "cbor",
                "--session-in", str(session_path),
                "--session-out", str(session_path),
                "--out", str(kyc_path),
                *(["--insecure"] if args.insecure else []),
            ],
            child_env,
            kyc_path,
            output_dir,
        )
        require_business_true(kyc_records, "kyc_submit")
        require_business_true(kyc_records, "admin_kyc_approve")
        approved = require_business_true(kyc_records, "kyc_detail_after_approval")
        if approved.get("actual_kyc_status") != 5:
            raise ProvisioningError("client KYC status did not refresh to 5")
        summary["stages"]["kyc"] = "PASS"
        secure_write(summary_path, summary)
        print("stage_kyc=PASS")

        deposit_arguments = [
            "--env", args.env,
            "--deposit",
            "--approve-deposit",
            "--client-phone", phone,
            "--deposit-amount", deposit_amount,
            "--deposit-cashback-flag", "0",
            "--deposit-rotation-flag", "0",
            "--approval-desc", args.approval_desc,
            "--body-format", "cbor",
            "--session-in", str(session_path),
            "--session-out", str(session_path),
            "--out", str(deposit_path),
            *(["--insecure"] if args.insecure else []),
        ]
        if deposit_pid:
            deposit_arguments.extend(["--deposit-pid", deposit_pid])
        deposit_records = run_stage(
            "deposit",
            deposit_arguments,
            child_env,
            deposit_path,
            output_dir,
        )
        deposit_evidence = validate_deposit_checkpoint(deposit_records, deposit_amount)
        summary["stages"]["deposit"] = "PASS"
        summary["status"] = "PASS"
        summary["deposit_amount"] = deposit_amount
        summary["validation"] = {**deposit_evidence, "requests_replayed": False}
        secure_write(summary_path, summary)
        print("stage_deposit=PASS")
        print(f"provisioning=PASS summary={summary_path}")
    except (ProvisioningError, OSError, ValueError, AttributeError, json.JSONDecodeError) as error:
        if active_extension:
            mark_extension(summary, active_extension, "BLOCKED", error=str(error))
            if core_stages_pass(summary):
                summary["status"] = "PASS"
                summary.pop("error", None)
            else:
                summary["status"] = "BLOCKED"
                summary["error"] = str(error)
        else:
            summary["status"] = "BLOCKED"
            summary["error"] = str(error)
        secure_write(summary_path, summary)
        label = f"extension_{active_extension}=BLOCKED" if active_extension else "provisioning=BLOCKED"
        print(f"{label} summary={summary_path}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
