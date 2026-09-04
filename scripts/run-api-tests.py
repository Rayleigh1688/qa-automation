#!/usr/bin/env python3
"""Run API suites by level.

Examples:
    python3 scripts/run-api-tests.py p0
    python3 scripts/run-api-tests.py p0 p1
    python3 scripts/run-api-tests.py p0 --safe-only
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
import uuid
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse


SENSITIVE_COMMAND_FLAGS = {
    "--approval-code",
    "--client-otp",
    "--client-phone",
    "--deposit-id",
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


def infer_scope(env_path: str, requested_scope: str) -> str:
    if requested_scope:
        return requested_scope.upper()
    return "UAT" if ".uat" in Path(env_path).name.lower() else "FAT"


def preflight(args: argparse.Namespace, env: dict[str, str]) -> None:
    errors: list[str] = []
    required = {"API_URL", "ADMIN_URL", "CLIENT_PHONE", "ADMIN_EMAIL", "ADMIN_PASSWORD"}
    auth_mode = env.get("CLIENT_AUTH_MODE", "password").strip().lower()
    if auth_mode == "password":
        required.add("CLIENT_PASSWORD")
    elif auth_mode == "otp":
        if not (env.get("CLIENT_OTP") or env.get("CLIENT_OTP_SOURCE", "").lower() == "admin_sms"):
            errors.append("CLIENT_AUTH_MODE=otp requires CLIENT_OTP or CLIENT_OTP_SOURCE=admin_sms")
    else:
        errors.append("CLIENT_AUTH_MODE must be password or otp")
    if not (
        env.get("ADMIN_GOOGLE_CODE")
        or env.get("ADMIN_LOGIN_TOTP_SECRET")
        or env.get("ADMIN_APPROVAL_TOTP_SECRET")
    ):
        errors.append("missing admin login code or TOTP source")
    if not args.safe_only:
        for name in ("REGISTER_PASSWORD", "CLIENT_WALLET_PASSWORD", "ADMIN_APPROVAL_TOTP_SECRET"):
            if not env.get(name, "").strip():
                errors.append(f"missing {name} for full controlled API flow")
        if not args.maya_pid.isdigit():
            errors.append("--maya-pid or PROVISION_MAYA_PID must be numeric")
        if not Path(args.kyc_image).is_file():
            errors.append(f"KYC image does not exist: {args.kyc_image}")
    for name in sorted(required):
        if not env.get(name, "").strip():
            errors.append(f"missing {name}")

    for name in ("API_URL", "ADMIN_URL"):
        value = env.get(name, "")
        parsed = urlparse(value)
        if value and (parsed.scheme != "https" or not parsed.hostname or "<" in value):
            errors.append(f"{name} must be a concrete https URL")
    hostnames = " ".join(
        urlparse(env.get(name, "")).hostname or "" for name in ("API_URL", "ADMIN_URL")
    ).lower()
    if args.scope == "FAT" and "uat" in hostnames:
        errors.append("FAT scope cannot use UAT URLs")
    if args.scope == "UAT" and "fat" in hostnames:
        errors.append("UAT scope cannot use FAT URLs")
    if args.scope not in {"FAT", "UAT"}:
        errors.append("--scope must be FAT or UAT")

    if not shutil.which("python3"):
        errors.append("missing executable: python3")
    for path in (
        Path("api/p0/test-cases.csv"),
        Path("scripts/api-smoke-runner.py"),
        Path("scripts/api-p0-negative-runner.py"),
        Path("scripts/render-api-p0-report.py"),
        Path("scripts/p0_report_template.py"),
    ):
        if not path.is_file():
            errors.append(f"missing dependency: {path}")
    if errors:
        raise SystemExit("P0 API preflight failed:\n- " + "\n- ".join(errors))
    print(f"P0 API preflight PASS scope={args.scope} mode={'safe' if args.safe_only else 'controlled-write'}", flush=True)


def run(command: list[str], env: dict[str, str]) -> None:
    print("+ " + display_command(command), flush=True)
    try:
        subprocess.run(command, env=env, check=True)
    except subprocess.CalledProcessError as error:
        raise subprocess.CalledProcessError(error.returncode, display_command(command)) from None


def clean_api_results(env: dict[str, str]) -> None:
    run(["python3", "scripts/clean-test-artifacts.py", "api"], env)


def render_p0_api_report(args: argparse.Namespace, env: dict[str, str]) -> None:
    run(
        [
            "python3",
            "scripts/render-api-p0-report.py",
            "--scope",
            args.scope,
            "--out",
            "api/results/p0-api-report.md",
            "--html-out",
            "api/results/p0-api-report.html",
        ],
        env,
    )


def sanitize_error(error: BaseException, env: dict[str, str]) -> str:
    message = str(error) or type(error).__name__
    sensitive_markers = ("PASSWORD", "SECRET", "TOKEN", "OTP", "CODE", "PHONE", "EMAIL", "DEVICE")
    for name, value in env.items():
        if len(value) >= 4 and any(marker in name.upper() for marker in sensitive_markers):
            message = message.replace(value, "<redacted>")
    message = re.sub(
        r"([?&](?:token|code|otp|phone|email|uid|device_id|x-device-id)=)[^&\s]+",
        r"\1<redacted>",
        message,
        flags=re.IGNORECASE,
    )
    return message[:2000]


def write_run_status(
    args: argparse.Namespace,
    *,
    status: str,
    stage: str,
    started_at: str,
    error: str = "",
    exit_code: int = 0,
    report_error: str = "",
) -> dict[str, object]:
    payload = {
        "status": status,
        "scope": args.scope,
        "mode": "read" if args.safe_only else "controlled-write",
        "stage": stage,
        "started_at": started_at,
        "finished_at": datetime.now().astimezone().isoformat(),
        "exit_code": exit_code,
        "error": error,
        "report_error": report_error,
    }
    output = Path("api/results/p0-run-status.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def write_fallback_report(args: argparse.Namespace, status: dict[str, object]) -> None:
    markdown = f"""# P0 API Run Report

- 状态：**{status.get('status', 'FAILED')}**
- 环境：{status.get('scope', args.scope)}
- 模式：{status.get('mode', '')}
- 最后阶段：`{status.get('stage', 'unknown')}`
- 退出码：{status.get('exit_code', 1)}
- 错误：{status.get('error') or '报告生成阶段发生异常'}
- 报告错误：{status.get('report_error') or '无'}

正式 API 报告生成失败，本文件是稳定兜底报告。已有阶段原始结果仍保留在 `api/results/`。
"""
    output_dir = Path("api/results")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "p0-api-report.md").write_text(markdown, encoding="utf-8")
    error = html.escape(str(status.get("error") or status.get("report_error") or "unknown error"))
    stage = html.escape(str(status.get("stage") or "unknown"))
    scope = html.escape(str(status.get("scope") or args.scope))
    (output_dir / "p0-api-report.html").write_text(
        f"<!doctype html><html lang='zh-CN'><meta charset='utf-8'><title>P0 API Report</title>"
        f"<body><h1>P0 API BLOCKED</h1><p>环境：{scope}</p><p>阶段：{stage}</p><pre>{error}</pre></body></html>",
        encoding="utf-8",
    )


def render_report_resilient(
    args: argparse.Namespace,
    env: dict[str, str],
    status: dict[str, object],
    started_at: str,
) -> dict[str, object]:
    try:
        render_p0_api_report(args, env)
    except BaseException as report_failure:
        report_error = sanitize_error(report_failure, env)
        if status.get("status") == "PASS":
            status.update({
                "status": "FAILED",
                "stage": "report",
                "error": "main report generation failed",
                "exit_code": 1,
            })
        status["report_error"] = report_error
        try:
            status = write_run_status(
                args,
                status=str(status.get("status") or "FAILED"),
                stage=str(status.get("stage") or "report"),
                started_at=started_at,
                error=str(status.get("error") or ""),
                exit_code=int(status.get("exit_code") or 1),
                report_error=report_error,
            )
        except BaseException as status_failure:
            status["report_error"] = (
                f"{report_error}; status artifact failed: {sanitize_error(status_failure, env)}"
            )[:2000]
        try:
            write_fallback_report(args, status)
        except BaseException as fallback_failure:
            status["report_error"] = (
                f"{status.get('report_error')}; fallback report failed: "
                f"{sanitize_error(fallback_failure, env)}"
            )[:2000]
            print(
                f"P0 API fallback report unavailable: {status['report_error']}",
                file=sys.stderr,
                flush=True,
            )
    return status


def run_p0(args: argparse.Namespace, env: dict[str, str]) -> None:
    cases = Path("api/p0/test-cases.csv")
    if not cases.exists():
        raise SystemExit("missing api/p0/test-cases.csv")

    args.current_stage = "safe_smoke"
    run(
        [
            "python3",
            "scripts/api-smoke-runner.py",
            "--cases",
            str(cases),
            "--env",
            args.env,
            "--with-client-login",
            "--with-admin-login",
            "--limit",
            "0",
            "--execute",
            "--body-format",
            args.body_format,
            "--out",
            "api/results/p0-smoke-result.json",
            *(["--insecure"] if args.insecure else []),
        ],
        env,
    )
    args.current_stage = "safe_smoke_report"
    run(
        [
            "python3",
            "scripts/render-p0-smoke-report.py",
            "--result",
            "api/results/p0-smoke-result.json",
            "--cases",
            str(cases),
            "--out",
            "api/results/p0-smoke-report.md",
            "--scope",
            args.scope,
        ],
        env,
    )
    args.current_stage = "negative"
    run(
        [
            "python3",
            "scripts/api-p0-negative-runner.py",
            "--env",
            args.env,
            "--body-format",
            args.body_format,
            "--scope",
            args.scope,
            "--out",
            "api/results/p0-negative-result.json",
            "--report",
            "api/results/p0-negative-report.md",
            *(["--insecure"] if args.insecure else []),
        ],
        env,
    )
    if not args.safe_only:
        args.current_stage = "controlled_full_flow"
        run(
            [
                "python3",
                "scripts/api-controlled-flow-runner.py",
                "--env",
                args.env,
                "--register",
                "--complete-kyc",
                "--deposit",
                "--approve-deposit",
                "--clear-turnover",
                "--prepare-withdraw-account",
                "--withdraw",
                "--check-client-withdraw-list",
                "--check-admin-withdraw-list",
                "--approve-withdraw",
                "--use-register-phone",
                "--flow-name",
                "p0-api-full",
                "--body-format",
                args.body_format,
                "--deposit-pid",
                args.deposit_pid,
                "--deposit-amount",
                args.deposit_amount,
                "--maya-pid",
                args.maya_pid,
                "--kyc-image",
                args.kyc_image,
                "--withdraw-amount",
                args.withdraw_amount,
                "--out",
                "api/results/p0-controlled-flow-result.json",
                *(["--insecure"] if args.insecure else []),
            ],
            env,
        )


def run_generic_level(level: str, args: argparse.Namespace, env: dict[str, str]) -> None:
    cases = Path(f"api/{level}/test-cases.csv")
    if not cases.exists():
        print(f"skip {level}: missing {cases}")
        return
    output = f"api/results/{level}-smoke-result.json"
    report = f"api/results/{level}-smoke-report.md"
    run(
        [
            "python3",
            "scripts/api-smoke-runner.py",
            "--cases",
            str(cases),
            "--env",
            args.env,
            "--with-client-login",
            "--with-admin-login",
            "--execute",
            "--body-format",
            args.body_format,
            "--out",
            output,
            *(["--insecure"] if args.insecure else []),
        ],
        env,
    )
    run(
        [
            "python3",
            "scripts/render-p0-smoke-report.py",
            "--result",
            output,
            "--cases",
            str(cases),
            "--out",
            report,
            "--title",
            f"{level.upper()} API Smoke Report",
            "--scope",
            args.scope,
        ],
        env,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("levels", nargs="+", help="test levels to run, for example: p0 p1")
    parser.add_argument(
        "--env",
        default=os.environ.get("ENV_FILE", ".env.fat"),
        help="dotenv file loaded before launching child runners (default: ENV_FILE or .env.fat)",
    )
    parser.add_argument("--scope", default="")
    parser.add_argument("--body-format", choices=["json", "cbor"], default="cbor")
    parser.add_argument("--insecure", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--include-write", action="store_true", help="compatibility flag; P0 already includes controlled deposit seeding by default")
    parser.add_argument("--safe-only", action="store_true", help="skip controlled P0 writes and run only read/negative checks")
    parser.add_argument("--no-clean", action="store_true", help="preserve existing controlled-flow evidence while refreshing repeatable gates")
    parser.add_argument(
        "--deposit-pid",
        default=os.environ.get("P0_DEPOSIT_PID", ""),
        help="Optional environment-specific deposit channel; empty selects a current mode=1 channel",
    )
    parser.add_argument("--deposit-amount", default="1200")
    parser.add_argument("--withdraw-amount", default="100")
    parser.add_argument("--maya-pid", default=os.environ.get("PROVISION_MAYA_PID", ""))
    parser.add_argument("--kyc-image", default=os.environ.get("KYC_IMAGE", "21000000008072.webp"))
    parser.add_argument("--write-client-phone", default="")
    parser.add_argument("--write-client-otp", default="")
    parser.add_argument("--withdraw-client-phone", default="")
    parser.add_argument("--withdraw-client-otp", default="")
    parser.add_argument("--register-phone", default="")
    args = parser.parse_args()
    args.scope = infer_scope(args.env, args.scope)
    args.current_stage = "initialize"
    started_at = datetime.now().astimezone().isoformat()
    env = os.environ.copy()
    exit_code = 0
    error_message = ""
    run_state = "PASS"

    try:
        if not args.no_clean:
            args.current_stage = "clean"
            clean_api_results(env)

        args.current_stage = "environment"
        env = load_env(Path(args.env))
        args.maya_pid = args.maya_pid or env.get("PROVISION_MAYA_PID", "")
        env.pop("API_TOKEN", None)
        env.pop("ADMIN_TOKEN", None)
        if not env.get("ADMIN_DEVICE_ID"):
            env["ADMIN_DEVICE_ID"] = str(uuid.uuid4())

        args.current_stage = "preflight"
        if args.safe_only and args.include_write:
            raise SystemExit("--safe-only and --include-write cannot be used together")
        preflight(args, env)

        for level in [item.lower() for item in args.levels]:
            if level == "p0":
                run_p0(args, env)
            elif level in {"p1", "p2"}:
                args.current_stage = level
                run_generic_level(level, args, env)
            else:
                raise SystemExit(f"unsupported level: {level}")
        args.current_stage = "complete"
    except KeyboardInterrupt as error:
        run_state = "INTERRUPTED"
        exit_code = 130
        error_message = sanitize_error(error, env) or "execution interrupted"
    except SystemExit as error:
        run_state = "FAILED"
        exit_code = error.code if isinstance(error.code, int) and error.code else 1
        error_message = sanitize_error(error, env)
    except subprocess.CalledProcessError as error:
        run_state = "FAILED"
        exit_code = error.returncode or 1
        error_message = f"subprocess failed during {args.current_stage}; exit code {exit_code}"
    except BaseException as error:
        run_state = "FAILED"
        exit_code = 1
        error_message = sanitize_error(error, env)

    try:
        status = write_run_status(
            args,
            status=run_state,
            stage=args.current_stage,
            started_at=started_at,
            error=error_message,
            exit_code=exit_code,
        )
    except BaseException as status_failure:
        exit_code = exit_code or 1
        status = {
            "status": "FAILED",
            "scope": args.scope,
            "mode": "read" if args.safe_only else "controlled-write",
            "stage": "report_status",
            "started_at": started_at,
            "finished_at": datetime.now().astimezone().isoformat(),
            "exit_code": exit_code,
            "error": error_message or "test execution completed but status artifact failed",
            "report_error": sanitize_error(status_failure, env),
        }
    if "p0" in [item.lower() for item in args.levels]:
        status = render_report_resilient(args, env, status, started_at)
        exit_code = int(status.get("exit_code") or 0)
    print(
        f"P0 API run status={status.get('status')} stage={status.get('stage')}",
        flush=True,
    )
    print(
        f"HTML report: {Path('api/results/p0-api-report.html').resolve().as_uri()}",
        flush=True,
    )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
