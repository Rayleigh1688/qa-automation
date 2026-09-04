#!/usr/bin/env python3
"""Top-level P0 automation entrypoint.

Quick mode runs repeatable API/UI gates. Full mode additionally performs the
controlled deposit -> real UI bet -> turnover check -> withdrawal chain.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlparse


SENSITIVE_COMMAND_FLAGS = {
    "--approval-code",
    "--client-otp",
    "--client-phone",
    "--deposit-id",
    "--kyc-uid",
    "--register-phone",
    "--withdraw-client-otp",
    "--withdraw-client-phone",
    "--withdraw-id",
    "--withdraw-external-order-id",
    "--write-client-otp",
    "--write-client-phone",
}


def display_command(command: list[str]) -> str:
    visible: list[str] = []
    redact_next = False
    for value in command:
        if redact_next:
            visible.append("<redacted>")
            redact_next = False
            continue
        visible.append(value)
        redact_next = value in SENSITIVE_COMMAND_FLAGS
    return " ".join(visible)


def load_env(path: Path) -> dict[str, str]:
    env = os.environ.copy()
    if not path.is_file():
        raise SystemExit(f"environment file does not exist: {path}")
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    env["ENV_FILE_PRECEDENCE"] = "shell"
    return env


def run(command: list[str], env: dict[str, str]) -> None:
    print("+ " + display_command(command), flush=True)
    try:
        subprocess.run(command, env=env, check=True)
    except subprocess.CalledProcessError as error:
        raise subprocess.CalledProcessError(error.returncode, display_command(command)) from None


def normalize_phone(value: str) -> str:
    return "".join(character for character in value if character.isdigit())


def preflight_full(args: argparse.Namespace, env: dict[str, str]) -> None:
    errors: list[str] = []

    required = {
        "API_URL",
        "ADMIN_URL",
        "CLIENT_BASE_URL",
        "CLIENT_PHONE",
        "CLIENT_PASSWORD",
        "WRITE_CLIENT_PHONE",
        "WRITE_CLIENT_PASSWORD",
        "KYC_CLIENT_PHONE",
        "PRE_KYC_CLIENT_PHONE",
        "PRE_KYC_CLIENT_PASSWORD",
        "ADMIN_EMAIL",
        "ADMIN_PASSWORD",
        "ADMIN_DEVICE_ID",
    }
    if not (env.get("KYC_CLIENT_PASSWORD") or env.get("CLIENT_PASSWORD")):
        errors.append("missing KYC_CLIENT_PASSWORD or CLIENT_PASSWORD")
    for name in sorted(required):
        if not env.get(name, "").strip():
            errors.append(f"missing {name}")

    for name in ("API_URL", "ADMIN_URL", "CLIENT_BASE_URL"):
        value = env.get(name, "")
        parsed = urlparse(value)
        if value and (parsed.scheme != "https" or not parsed.hostname or "<" in value):
            errors.append(f"{name} must be a concrete https URL")

    scope = str(args.scope).strip().upper()
    if scope not in {"FAT", "UAT"}:
        errors.append("--scope must be FAT or UAT for full P0")
    hostnames = " ".join(
        urlparse(env.get(name, "")).hostname or ""
        for name in ("API_URL", "ADMIN_URL", "CLIENT_BASE_URL")
    ).lower()
    if scope == "FAT" and "uat" in hostnames:
        errors.append("FAT scope cannot use UAT URLs")
    if scope == "UAT" and "fat" in hostnames:
        errors.append("UAT scope cannot use FAT URLs")

    lanes = {
        "fund_flow": normalize_phone(env.get("WRITE_CLIENT_PHONE", "")),
        "kyc": normalize_phone(env.get("KYC_CLIENT_PHONE", "")),
        "permanent_basic": normalize_phone(env.get("PRE_KYC_CLIENT_PHONE", "")),
    }
    populated_lanes = {value: name for name, value in lanes.items() if value}
    if len(populated_lanes) != len([value for value in lanes.values() if value]):
        errors.append("WRITE_CLIENT_PHONE, KYC_CLIENT_PHONE, and PRE_KYC_CLIENT_PHONE must be distinct")
    for alias in ("BET_CLIENT_PHONE", "WITHDRAW_CLIENT_PHONE"):
        if env.get(alias) and normalize_phone(env[alias]) != lanes["fund_flow"]:
            errors.append(f"{alias} must identify the WRITE_CLIENT_PHONE fund-flow account")

    approval_source = env.get("ADMIN_APPROVAL_CODE") or env.get("ADMIN_APPROVAL_TOTP_SECRET")
    if not approval_source:
        errors.append("missing ADMIN_APPROVAL_TOTP_SECRET or ADMIN_APPROVAL_CODE")
    if scope == "UAT":
        if env.get("CLIENT_AUTH_MODE", "").lower() != "otp":
            errors.append("UAT requires CLIENT_AUTH_MODE=otp")
        if env.get("CLIENT_OTP_SOURCE", "").lower() != "admin_sms":
            errors.append("UAT requires CLIENT_OTP_SOURCE=admin_sms")
        if not (env.get("ADMIN_LOGIN_TOTP_SECRET") or env.get("ADMIN_APPROVAL_TOTP_SECRET")):
            errors.append("UAT requires a dynamic admin login TOTP source")
        if env.get("ADMIN_GOOGLE_CODE") == "111111":
            errors.append("UAT must not use fixed ADMIN_GOOGLE_CODE=111111")
    elif scope == "FAT" and not (
        env.get("ADMIN_GOOGLE_CODE")
        or env.get("ADMIN_LOGIN_TOTP_SECRET")
        or env.get("ADMIN_APPROVAL_TOTP_SECRET")
    ):
        errors.append("FAT requires an admin login code or TOTP source")

    for label, value in (("deposit", args.deposit_amount), ("withdraw", args.withdraw_amount)):
        try:
            parsed_amount = Decimal(str(value))
            if not parsed_amount.is_finite() or parsed_amount <= 0:
                raise ValueError
        except (InvalidOperation, TypeError, ValueError):
            errors.append(f"{label} amount must be a positive number")

    kyc_image = Path(env.get("KYC_IMAGE", "21000000008072.webp"))
    if not kyc_image.is_file():
        errors.append(f"KYC_IMAGE does not exist: {kyc_image}")
    for executable in ("python3", "npm", "npx"):
        if not shutil.which(executable):
            errors.append(f"missing executable: {executable}")
    for path in (
        Path("scripts/run-api-tests.py"),
        Path("scripts/api-controlled-flow-runner.py"),
        Path("scripts/run-ui-p0-tests.py"),
        Path("scripts/render-ui-p0-report.py"),
        Path("scripts/render-main-flow-report.py"),
        Path("scripts/p0_report_template.py"),
        Path("scripts/run-turnover-bet.py"),
        Path("scripts/reconcile-p0-flow.py"),
        Path("node_modules/@playwright/test"),
    ):
        if not path.exists():
            errors.append(f"missing dependency: {path}")

    if errors:
        raise SystemExit("full P0 preflight failed:\n- " + "\n- ".join(errors))
    print("full P0 preflight PASS", flush=True)


def ui_failures_are_known() -> bool:
    import json

    path = Path("ui/results/ui-playwright-result.json")
    if not path.is_file():
        return False
    payload = json.loads(path.read_text(encoding="utf-8"))
    titles: list[str] = []

    def walk(value: object) -> None:
        if isinstance(value, dict):
            if value.get("ok") is False and isinstance(value.get("tests"), list):
                titles.append(str(value.get("title") or ""))
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(payload.get("suites", []))
    known_markers = ("未勾选登录条款", "unchecked login terms")
    return bool(titles) and all(any(marker in title for marker in known_markers) for title in titles)


def run_default_ui(env: dict[str, str], allow_known_defect: bool, *, clean: bool = True) -> None:
    command = [
        "python3", "scripts/run-ui-p0-tests.py",
        "--env", env.get("ENV_FILE", ".env.fat"),
        *([] if clean else ["--no-clean"]),
    ]
    ui_env = {
        **env,
        "CLIENT_REUSE_P0_AUTH": "true",
        "CLIENT_AUTH_MODE": env.get("CLIENT_AUTH_MODE", "password"),
        "ENV_FILE_PRECEDENCE": "shell",
    }
    try:
        run(command, ui_env)
    except subprocess.CalledProcessError:
        if not allow_known_defect or not ui_failures_are_known():
            raise
        print("accepted known product defect: 未勾选登录条款仍可登录", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["quick", "full"], default="quick")
    parser.add_argument("--env", default=os.environ.get("ENV_FILE", ".env.fat"))
    parser.add_argument("--scope", default="")
    parser.add_argument("--allow-known-defect", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--deposit-amount", default="1200")
    parser.add_argument("--withdraw-amount", default="1000")
    args = parser.parse_args()
    if not args.scope:
        args.scope = "UAT" if ".uat" in Path(args.env).name.lower() else "FAT"
    env = load_env(Path(args.env))
    env["ENV_FILE"] = args.env

    if args.mode == "quick":
        run(["python3", "scripts/run-api-tests.py", "p0", "--env", args.env, "--scope", args.scope, "--safe-only", "--no-clean"], env)
        run_default_ui(env, args.allow_known_defect)
        return

    preflight_full(args, env)
    write_phone = env.get("WRITE_CLIENT_PHONE", "")
    write_password = env.get("WRITE_CLIENT_PASSWORD") or env.get("CLIENT_PASSWORD", "")
    write_otp = env.get("WRITE_CLIENT_OTP", "")
    if not write_phone or not write_password:
        raise SystemExit("full P0 requires WRITE_CLIENT_PHONE and WRITE_CLIENT_PASSWORD")
    kyc_phone = env.get("KYC_CLIENT_PHONE", "")
    kyc_otp = env.get("KYC_CLIENT_OTP", "")
    if not kyc_phone:
        raise SystemExit("full P0 requires KYC_CLIENT_PHONE")
    pre_kyc_phone = env.get("PRE_KYC_CLIENT_PHONE", "")
    pre_kyc_password = env.get("PRE_KYC_CLIENT_PASSWORD", "")
    if not pre_kyc_phone or not pre_kyc_password:
        raise SystemExit("full P0 requires PRE_KYC_CLIENT_PHONE and PRE_KYC_CLIENT_PASSWORD")
    if normalize_phone(pre_kyc_phone) == normalize_phone(kyc_phone):
        raise SystemExit("PRE_KYC_CLIENT_PHONE must be permanently separate from KYC_CLIENT_PHONE")
    run(["python3", "scripts/clean-test-artifacts.py", "all"], env)
    pre_kyc_env = {
        **env,
        "PRE_KYC_CLIENT_PHONE": pre_kyc_phone,
        "PRE_KYC_CLIENT_PASSWORD": pre_kyc_password,
    }
    run([
        "npx", "playwright", "test",
        "ui/cases/client-unverified-withdraw.spec.mjs", "--workers=1",
    ], pre_kyc_env)
    kyc_password = env.get("KYC_CLIENT_PASSWORD") or env.get("CLIENT_PASSWORD", "")
    if not kyc_password:
        raise SystemExit("full P0 requires KYC_CLIENT_PASSWORD or CLIENT_PASSWORD")
    kyc_env = {
        **env,
        "CLIENT_PHONE": kyc_phone,
        "CLIENT_PASSWORD": kyc_password,
        "CLIENT_OTP": kyc_otp,
        "CLIENT_AUTH_MODE": env.get("KYC_CLIENT_AUTH_MODE", env.get("CLIENT_AUTH_MODE", "password")),
    }
    run([
        "python3", "scripts/api-controlled-flow-runner.py",
        "--env", args.env,
        "--complete-kyc",
        "--client-phone", kyc_phone,
        "--client-otp", kyc_otp,
        "--kyc-uid", env.get("KYC_CLIENT_UID", ""),
        "--kyc-image", env.get("KYC_IMAGE", "21000000008072.webp"),
        "--body-format", "cbor", "--insecure",
        "--out", "api/results/kyc-result.json",
    ], kyc_env)
    run([
        "python3", "scripts/run-api-tests.py", "p0",
        "--env", args.env,
        "--scope", args.scope,
        "--write-client-phone", write_phone,
        "--write-client-otp", write_otp,
        "--deposit-amount", args.deposit_amount,
        "--no-clean",
    ], env)
    fund_env = {
        **env,
        "CLIENT_PHONE": write_phone,
        "CLIENT_PASSWORD": write_password,
        "CLIENT_OTP": write_otp,
        "CLIENT_AUTH_MODE": env.get("CLIENT_AUTH_MODE", "password"),
    }
    run_default_ui(fund_env, args.allow_known_defect, clean=False)
    turnover_env = {**fund_env, "PRESERVE_UI_RESULTS": "true"}
    run(["python3", "scripts/run-turnover-bet.py", "--env", args.env, "--execute"], turnover_env)
    run([
        "python3", "scripts/api-controlled-flow-runner.py",
        "--env", args.env,
        "--withdraw",
        "--check-admin-withdraw-list",
        "--client-phone", write_phone,
        "--client-otp", write_otp,
        "--withdraw-amount", args.withdraw_amount,
        "--body-format", "cbor", "--insecure",
        "--out", "api/results/withdraw-result.json",
    ], fund_env)
    run(["python3", "scripts/reconcile-p0-flow.py"], fund_env)
    run([
        "python3", "scripts/render-main-flow-report.py",
        "--scope", args.scope,
        "--out", "api/results/p0-main-flow-report.md",
        "--html-out", "api/results/p0-main-flow-report.html",
    ], fund_env)
    print(f"HTML report: {Path('api/results/p0-main-flow-report.html').resolve().as_uri()}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        raise SystemExit(str(error)) from None
