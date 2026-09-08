#!/usr/bin/env python3
"""Run the default P0 UI suite and always render the shared UI report."""

from __future__ import annotations

from qa_core.terminal import print_result, print_path

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse


DEFAULT_SPECS = [
    "ui/cases/client-login.spec.mjs",
    "ui/cases/client-main-flow.spec.mjs",
    "ui/cases/client-deposit-contract.spec.mjs",
    "ui/cases/client-game-bet-smoke.spec.mjs",
    "ui/cases/client-p0-positive-negative.spec.mjs",
]

SENSITIVE_MARKERS = ("PASSWORD", "SECRET", "TOKEN", "OTP", "CODE", "PHONE", "EMAIL", "DEVICE")


def run(command: list[str], env: dict[str, str]) -> int:
    print("+ " + " ".join(command), flush=True)
    try:
        return subprocess.run(command, env=env, check=False).returncode
    except OSError as error:
        print(f"command unavailable: {error}", flush=True)
        return 127


def load_env(path: Path) -> dict[str, str]:
    from qa_core.environment import load_environment
    env = load_environment(path)
    env.update({
        "ENV_FILE": str(path),
        "ENV_FILE_PRECEDENCE": "shell",
        "CLIENT_REUSE_P0_AUTH": "true",
    })
    env.pop("API_TOKEN", None)
    env.pop("ADMIN_TOKEN", None)
    return env


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


def preflight(args: argparse.Namespace, env: dict[str, str]) -> None:
    errors: list[str] = []
    required = {"CLIENT_BASE_URL", "CLIENT_PHONE"}
    auth_mode = env.get("CLIENT_AUTH_MODE", "password").strip().lower()
    otp_source = env.get("CLIENT_OTP_SOURCE", "fixed").strip().lower()
    if auth_mode == "password":
        required.add("CLIENT_PASSWORD")
    elif auth_mode == "otp":
        if otp_source == "admin_sms":
            required.update({"ADMIN_URL", "ADMIN_EMAIL", "ADMIN_PASSWORD"})
            if not any(env.get(name, "").strip() for name in (
                "ADMIN_GOOGLE_CODE", "ADMIN_LOGIN_TOTP_SECRET", "ADMIN_APPROVAL_TOTP_SECRET",
            )):
                errors.append("CLIENT_OTP_SOURCE=admin_sms requires an admin login code or TOTP source")
        elif not env.get("CLIENT_OTP", "").strip():
            errors.append("CLIENT_AUTH_MODE=otp requires CLIENT_OTP or CLIENT_OTP_SOURCE=admin_sms")
    else:
        errors.append("CLIENT_AUTH_MODE must be password or otp")
    if args.scope == "UAT" and (auth_mode != "otp" or otp_source != "admin_sms"):
        errors.append("UAT UI requires CLIENT_AUTH_MODE=otp and CLIENT_OTP_SOURCE=admin_sms")

    for name in sorted(required):
        if not env.get(name, "").strip():
            errors.append(f"missing {name}")
    client_url = env.get("CLIENT_BASE_URL", "")
    parsed = urlparse(client_url)
    if client_url and (parsed.scheme != "https" or not parsed.hostname or "<" in client_url):
        errors.append("CLIENT_BASE_URL must be a concrete https URL")
    hostname = (parsed.hostname or "").lower()
    if args.scope == "FAT" and "uat" in hostname:
        errors.append("FAT scope cannot use a UAT CLIENT_BASE_URL")
    if args.scope == "UAT" and "fat" in hostname:
        errors.append("UAT scope cannot use a FAT CLIENT_BASE_URL")
    if args.scope not in {"FAT", "UAT"}:
        errors.append("--scope must be FAT or UAT")
    if not shutil.which("npx"):
        errors.append("missing executable: npx")
    for path in (
        *(Path(spec) for spec in DEFAULT_SPECS),
        Path("playwright.config.mjs"),
        Path("node_modules/.bin/playwright"),
        Path("ui/setup/client-p0-auth.setup.mjs"),
        Path("ui/data/client-p0-default-suite.json"),
        Path("scripts/clean-test-artifacts.py"),
        Path("scripts/render-ui-p0-report.py"),
        Path("scripts/p0_report_template.py"),
    ):
        if not path.is_file():
            errors.append(f"missing dependency: {path}")
    if errors:
        raise SystemExit("P0 UI preflight failed:\n- " + "\n- ".join(errors))
    print_result(f"P0 UI preflight PASS scope={args.scope} auth={auth_mode}", "PASS")


def write_run_status(
    *,
    scope: str,
    status: str,
    stage: str,
    started_at: str,
    exit_code: int,
    error: str = "",
    report_error: str = "",
) -> dict[str, object]:
    payload: dict[str, object] = {
        "status": status,
        "scope": scope,
        "stage": stage,
        "started_at": started_at,
        "finished_at": datetime.now().astimezone().isoformat(),
        "exit_code": exit_code,
        "error": error,
        "report_error": report_error,
    }
    output = Path("ui/results/p0-ui-run-status.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def write_fallback_report(status: dict[str, object]) -> None:
    """Write a dependency-free report when the normal renderer is unavailable."""
    report_dir = Path("ui/reports")
    report_dir.mkdir(parents=True, exist_ok=True)
    scope = str(status.get("scope") or "unknown")
    stage = str(status.get("stage") or "unknown")
    error = str(status.get("error") or status.get("report_error") or "报告生成阶段发生异常")
    report_error = str(status.get("report_error") or "")
    test_status = str(status.get("status") or "FAILED")
    safe_scope = html.escape(scope)
    safe_stage = html.escape(stage)
    safe_error = html.escape(error)
    safe_report_error = html.escape(report_error)
    (report_dir / "p0-ui-report.md").write_text(
        "\n".join([
            "# P0 UI 执行报告",
            "",
            f"- 环境：{scope}",
            "- 结论：**BLOCKED**",
            f"- UI 运行状态：**{test_status}**",
            f"- 最后阶段：`{stage}`",
            f"- 错误：{error}",
            f"- 报告错误：{report_error or '无'}",
            "- 说明：标准报告渲染失败；这是 UI runner 生成的最小兜底报告。",
            "",
        ]),
        encoding="utf-8",
    )
    (report_dir / "p0-ui-report.html").write_text(
        "<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        "<title>P0 UI 执行报告</title></head><body><main>"
        f"<h1>P0 UI BLOCKED</h1><p>环境：{safe_scope}</p>"
        f"<p>最后阶段：{safe_stage}</p><pre>{safe_error}</pre>"
        f"<p>报告错误：</p><pre>{safe_report_error or '无'}</pre>"
        "<p>标准报告渲染失败；这是 UI runner 生成的最小兜底报告。</p>"
        "</main></body></html>",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", default=os.environ.get("ENV_FILE", ".env.fat"))
    parser.add_argument("--scope", default="")
    parser.add_argument("--no-clean", action="store_true")
    parser.add_argument("--headed", action="store_true", help="show Playwright browser windows")
    args = parser.parse_args()
    args.scope = args.scope.upper() if args.scope else ("UAT" if ".uat" in Path(args.env).name.lower() else "FAT")
    started_at = datetime.now().astimezone().isoformat()
    env = os.environ.copy()
    stage = "initialize"
    run_status = "PASS"
    exit_code = 0
    error_message = ""

    try:
        if not args.no_clean:
            stage = "clean"
            clean_code = run(["python3", "scripts/clean-test-artifacts.py", "ui"], env)
            if clean_code:
                raise RuntimeError(f"artifact cleanup failed with exit code {clean_code}")
        stage = "environment"
        env = load_env(Path(args.env))
        if args.headed:
            env["PLAYWRIGHT_HEADLESS"] = "false"
        stage = "preflight"
        preflight(args, env)
        stage = "playwright"
        playwright_code = run(["npx", "playwright", "test", *DEFAULT_SPECS, "--workers=1"], env)
        if playwright_code:
            run_status = "FAILED"
            exit_code = playwright_code
            error_message = f"Playwright suite failed with exit code {playwright_code}"
        else:
            stage = "complete"
    except KeyboardInterrupt as error:
        run_status = "INTERRUPTED"
        exit_code = 130
        error_message = sanitize_error(error, env) or "execution interrupted"
    except SystemExit as error:
        run_status = "FAILED"
        exit_code = error.code if isinstance(error.code, int) and error.code else 1
        error_message = sanitize_error(error, env)
    except BaseException as error:
        run_status = "FAILED"
        exit_code = 1
        error_message = sanitize_error(error, env)

    try:
        status = write_run_status(
            scope=args.scope, status=run_status, stage=stage, started_at=started_at,
            exit_code=exit_code, error=error_message,
        )
    except BaseException as status_failure:
        exit_code = exit_code or 1
        status = {
            "status": "FAILED", "scope": args.scope, "stage": "report_status",
            "started_at": started_at, "finished_at": datetime.now().astimezone().isoformat(),
            "exit_code": exit_code, "error": error_message or "status artifact failed",
            "report_error": sanitize_error(status_failure, env),
        }

    html_report = Path("ui/reports/p0-ui-report.html")
    try:
        report_code = run([
            "python3", "scripts/render-ui-p0-report.py", "--scope", args.scope,
            "--run-status", str(status.get("status") or "FAILED"),
            "--run-status-file", "ui/results/p0-ui-run-status.json",
            "--html-out", str(html_report),
        ], env)
    except KeyboardInterrupt:
        report_code = 130
        status.update({
            "status": "INTERRUPTED", "stage": "report", "exit_code": 130,
            "error": "report generation interrupted",
        })
    except BaseException as report_failure:
        report_code = 1
        status.update({
            "status": "FAILED", "stage": "report", "exit_code": int(status.get("exit_code") or 1),
            "error": "main report generation failed",
            "report_error": sanitize_error(report_failure, env),
        })
    if report_code != 0 or not html_report.is_file():
        report_error = str(status.get("report_error") or f"standard report generation failed with exit code {report_code}")
        if status.get("status") == "PASS":
            status.update({
                "status": "FAILED", "stage": "report", "exit_code": report_code or 1,
                "error": "main report generation failed",
            })
        status["report_error"] = report_error
        exit_code = int(status.get("exit_code") or report_code or 1)
        try:
            status = write_run_status(
                scope=args.scope, status=str(status.get("status") or "FAILED"),
                stage=str(status.get("stage") or "report"), started_at=started_at,
                exit_code=exit_code, error=str(status.get("error") or ""),
                report_error=report_error,
            )
        except BaseException as status_failure:
            status["report_error"] = sanitize_error(status_failure, env)
        try:
            write_fallback_report(status)
            print(f"wrote fallback {html_report.resolve()}", flush=True)
        except BaseException as error:
            print(f"P0 UI fallback report unavailable: {sanitize_error(error, env)}", file=sys.stderr, flush=True)
    print_result(
        f"P0 UI run status={status.get('status')} stage={status.get('stage')}",
        status.get('status'),
    )
    print_path(f"HTML report: {html_report.resolve().as_uri()}", flush=True)
    return int(status.get("exit_code") or report_code or 0)


if __name__ == "__main__":
    raise SystemExit(main())
