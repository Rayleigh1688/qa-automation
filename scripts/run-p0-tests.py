#!/usr/bin/env python3
"""Top-level P0 automation entrypoint.

Quick mode runs repeatable API/UI gates. Full mode additionally performs the
controlled deposit -> real UI bet -> turnover check -> withdrawal chain.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
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
SENSITIVE_MARKERS = ("PASSWORD", "SECRET", "TOKEN", "OTP", "CODE", "PHONE", "EMAIL", "DEVICE")
FULL_STATUS_PATH = Path("api/results/p0-full-run-status.json")
FULL_MARKDOWN_REPORT = Path("api/results/p0-main-flow-report.md")
FULL_HTML_REPORT = Path("api/results/p0-main-flow-report.html")


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
    from qa_core.environment import load_environment
    env = load_environment(path)
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


def sanitize_error(error: BaseException | str, env: dict[str, str]) -> str:
    message = str(error) or (type(error).__name__ if isinstance(error, BaseException) else "unknown error")
    for name, value in env.items():
        if len(value) >= 4 and any(marker in name.upper() for marker in SENSITIVE_MARKERS):
            message = message.replace(value, "<redacted>")
    message = re.sub(
        r"([?&](?:token|code|otp|phone|email|uid|device_id|x-device-id)=)[^&\s]+",
        r"\1<redacted>",
        message,
        flags=re.IGNORECASE,
    )
    return message[:2000]


def write_full_run_status(
    args: argparse.Namespace,
    *,
    status: str,
    stage: str,
    started_at: str,
    exit_code: int,
    error: str = "",
    completed_stages: list[str] | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "status": status,
        "scope": args.scope,
        "mode": args.mode,
        "headed": bool(args.headed),
        "stage": stage,
        "started_at": started_at,
        "finished_at": datetime.now().astimezone().isoformat(),
        "exit_code": exit_code,
        "error": error,
        "completed_stages": completed_stages or [],
        "parameters": {
            "deposit_amount": str(args.deposit_amount),
            "bet_spins": args.bet_spins,
            "clear_remaining_turnover": bool(args.clear_remaining_turnover),
            "withdraw_amount": str(args.withdraw_amount),
        },
    }
    FULL_STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    FULL_STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def write_full_failure_report(status: dict[str, object]) -> None:
    """Always replace the main-flow report with current-run failure evidence."""
    FULL_HTML_REPORT.parent.mkdir(parents=True, exist_ok=True)
    scope = str(status.get("scope") or "unknown")
    stage = str(status.get("stage") or "unknown")
    error = str(status.get("error") or "unknown error")
    completed = [str(item) for item in status.get("completed_stages", []) if item]
    completed_text = " → ".join(completed) if completed else "无"
    FULL_MARKDOWN_REPORT.write_text(
        "\n".join([
            "# P0 Main Flow Report", "",
            f"- 环境：{scope}",
            "- 状态：**BLOCKED**",
            f"- 失败阶段：`{stage}`",
            f"- 退出码：`{status.get('exit_code', 1)}`",
            f"- 已完成阶段：{completed_text}",
            f"- 错误：{error}", "",
            "本报告由完整 P0 Python 入口在失败时自动生成；旧的成功报告已被覆盖，避免误读。", "",
        ]),
        encoding="utf-8",
    )
    FULL_HTML_REPORT.write_text(
        "<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        "<title>P0 主流程失败报告</title><style>body{max-width:900px;margin:40px auto;padding:0 20px;"
        "font:15px/1.6 sans-serif;background:#f3f6f5;color:#17232d}main{background:#fff;border:1px solid #d9e1e5;"
        "border-left:6px solid #bd3434;padding:24px}h1{color:#bd3434}dt{color:#64727d;margin-top:12px}dd{margin:2px 0;word-break:break-word}"
        "code{background:#f3f6f5;padding:2px 5px}</style></head><body><main>"
        "<h1>BLOCKED</h1><p>完整 P0 编排未完成，旧的成功报告已被覆盖。</p><dl>"
        f"<dt>环境</dt><dd>{html.escape(scope)}</dd><dt>失败阶段</dt><dd><code>{html.escape(stage)}</code></dd>"
        f"<dt>退出码</dt><dd>{html.escape(str(status.get('exit_code', 1)))}</dd>"
        f"<dt>已完成阶段</dt><dd>{html.escape(completed_text)}</dd><dt>错误</dt><dd>{html.escape(error)}</dd>"
        "</dl></main></body></html>",
        encoding="utf-8",
    )


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


def run_default_ui(env: dict[str, str], *, clean: bool = True, headed: bool = False) -> None:
    command = [
        "python3", "scripts/run-ui-p0-tests.py",
        "--env", env.get("ENV_FILE", ".env.fat"),
        *([] if clean else ["--no-clean"]),
        *(["--headed"] if headed else []),
    ]
    ui_env = {
        **env,
        "CLIENT_REUSE_P0_AUTH": "true",
        "CLIENT_AUTH_MODE": env.get("CLIENT_AUTH_MODE", "password"),
        "ENV_FILE_PRECEDENCE": "shell",
    }
    run(command, ui_env)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["quick", "full"], default="quick")
    parser.add_argument("--env", default=os.environ.get("ENV_FILE", ".env.fat"))
    parser.add_argument("--scope", default="")
    parser.add_argument("--deposit-amount", default="1200")
    parser.add_argument("--bet-spins", type=int, default=0)
    parser.add_argument("--clear-remaining-turnover", action="store_true")
    parser.add_argument("--withdraw-amount", default="1000")
    parser.add_argument("--headed", action="store_true", help="show Playwright browser windows without Inspector")
    args = parser.parse_args()
    if not args.scope:
        args.scope = "UAT" if ".uat" in Path(args.env).name.lower() else "FAT"
    started_at = datetime.now().astimezone().isoformat()
    env = os.environ.copy()
    stage = "environment"
    completed_stages: list[str] = []
    try:
        env = load_env(Path(args.env))
        env["ENV_FILE"] = args.env
        if args.headed:
            env["PLAYWRIGHT_HEADLESS"] = "false"

        if args.mode == "quick":
            stage = "api_gate"
            run(["python3", "scripts/run-api-tests.py", "p0", "--env", args.env, "--scope", args.scope, "--safe-only", "--no-clean"], env)
            stage = "default_ui"
            run_default_ui(env, headed=args.headed)
            return 0

        stage = "preflight"
        preflight_full(args, env)
        completed_stages.append(stage)
        if args.bet_spins < 0 or args.bet_spins > 20:
            raise SystemExit("--bet-spins must be between 0 and 20")
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
        stage = "clean"
        run(["python3", "scripts/clean-test-artifacts.py", "all"], env)
        completed_stages.append(stage)
        stage = "pre_kyc_withdraw_ui"
        pre_kyc_env = {
            **env,
            "PRE_KYC_CLIENT_PHONE": pre_kyc_phone,
            "PRE_KYC_CLIENT_PASSWORD": pre_kyc_password,
        }
        run([
            "npx", "playwright", "test",
            "ui/cases/client-unverified-withdraw.spec.mjs", "--workers=1",
        ], pre_kyc_env)
        completed_stages.append(stage)
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
        stage = "kyc"
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
        completed_stages.append(stage)
        stage = "api_gate"
        run([
            "python3", "scripts/run-api-tests.py", "p0",
            "--env", args.env,
            "--scope", args.scope,
            "--write-client-phone", write_phone,
            "--write-client-otp", write_otp,
            "--deposit-amount", args.deposit_amount,
            "--safe-only",
            "--no-clean",
        ], env)
        completed_stages.append(stage)
        fund_env = {
            **env,
            "CLIENT_PHONE": write_phone,
            "CLIENT_PASSWORD": write_password,
            "CLIENT_OTP": write_otp,
            "CLIENT_AUTH_MODE": env.get("CLIENT_AUTH_MODE", "password"),
        }
        deposit_command = [
            "python3", "scripts/api-controlled-flow-runner.py",
            "--env", args.env,
            "--deposit",
            "--approve-deposit",
            "--client-phone", write_phone,
            "--client-otp", write_otp,
            "--deposit-amount", args.deposit_amount,
            "--body-format", "cbor", "--insecure",
            "--out", "api/results/fund-flow-seed-result.json",
        ]
        deposit_pid = env.get("P0_DEPOSIT_PID", "").strip()
        if deposit_pid:
            deposit_command.extend(["--deposit-pid", deposit_pid])
        stage = "deposit"
        run(deposit_command, fund_env)
        completed_stages.append(stage)
        stage = "default_ui"
        run_default_ui(fund_env, clean=False, headed=args.headed)
        completed_stages.append(stage)
        turnover_env = {**fund_env, "PRESERVE_UI_RESULTS": "true"}
        turnover_command = ["python3", "scripts/run-turnover-bet.py", "--env", args.env, "--execute"]
        if args.bet_spins:
            turnover_command.extend(["--spin-count", str(args.bet_spins)])
        if args.clear_remaining_turnover:
            turnover_command.append("--allow-remaining-turnover")
        stage = "real_bet_ui"
        run(turnover_command, turnover_env)
        completed_stages.append(stage)
        if args.clear_remaining_turnover:
            stage = "turnover_clear"
            run([
                "python3", "scripts/api-controlled-flow-runner.py",
                "--env", args.env,
                "--clear-turnover",
                "--client-phone", write_phone,
                "--client-otp", write_otp,
                "--body-format", "cbor", "--insecure",
                "--out", "api/results/turnover-clear-result.json",
            ], fund_env)
            completed_stages.append(stage)
        stage = "withdraw"
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
        completed_stages.append(stage)
        stage = "reconcile"
        run(["python3", "scripts/reconcile-p0-flow.py"], fund_env)
        completed_stages.append(stage)
        write_full_run_status(
            args, status="PASS", stage="complete", started_at=started_at,
            exit_code=0, completed_stages=completed_stages,
        )
        stage = "report"
        run([
            "python3", "scripts/render-main-flow-report.py",
            "--scope", args.scope,
            "--run-status", str(FULL_STATUS_PATH),
            "--out", "api/results/p0-main-flow-report.md",
            "--html-out", "api/results/p0-main-flow-report.html",
        ], fund_env)
        completed_stages.append(stage)
        write_full_run_status(
            args, status="PASS", stage="complete", started_at=started_at,
            exit_code=0, completed_stages=completed_stages,
        )
        print(f"P0 full run status=PASS stage=complete headed={args.headed}", flush=True)
        print(f"HTML report: {FULL_HTML_REPORT.resolve().as_uri()}", flush=True)
        return 0
    except KeyboardInterrupt as error:
        exit_code = 130
        status_name = "INTERRUPTED"
        error_message = sanitize_error(error, env) or "execution interrupted"
    except SystemExit as error:
        exit_code = error.code if isinstance(error.code, int) and error.code else 1
        status_name = "FAILED"
        error_message = sanitize_error(error, env)
    except subprocess.CalledProcessError as error:
        exit_code = error.returncode or 1
        status_name = "FAILED"
        error_message = sanitize_error(error, env)
    except BaseException as error:
        exit_code = 1
        status_name = "FAILED"
        error_message = sanitize_error(error, env)

    if args.mode == "full":
        status: dict[str, object] = {
            "status": status_name,
            "scope": args.scope,
            "stage": stage,
            "started_at": started_at,
            "finished_at": datetime.now().astimezone().isoformat(),
            "exit_code": exit_code,
            "error": error_message,
            "completed_stages": completed_stages,
        }
        try:
            status = write_full_run_status(
                args, status=status_name, stage=stage, started_at=started_at,
                exit_code=exit_code, error=error_message, completed_stages=completed_stages,
            )
        except BaseException as status_error:
            status["report_error"] = "status artifact unavailable: " + sanitize_error(status_error, env)
        try:
            write_full_failure_report(status)
        except BaseException as report_error:
            print(f"P0 full failure report unavailable: {sanitize_error(report_error, env)}", file=sys.stderr, flush=True)
        print(f"P0 full run status={status_name} stage={stage}", flush=True)
        print(f"HTML report: {FULL_HTML_REPORT.resolve().as_uri()}", flush=True)
    return int(exit_code)


if __name__ == "__main__":
    raise SystemExit(main())
