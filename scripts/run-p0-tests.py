#!/usr/bin/env python3
"""Top-level P0 automation entrypoint.

Quick mode runs repeatable API/UI gates. Full mode additionally performs the
controlled deposit -> real UI bet -> turnover check -> withdrawal chain.
"""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path


def load_env(path: Path) -> dict[str, str]:
    env = os.environ.copy()
    if not path.is_file():
        return env
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    env["ENV_FILE_PRECEDENCE"] = "shell"
    return env


def run(command: list[str], env: dict[str, str]) -> None:
    print("+ " + " ".join(command), flush=True)
    subprocess.run(command, env=env, check=True)


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
    command = ["npm", "run", "test:ui:p0"] if clean else [
        "npx", "playwright", "test",
        "ui/cases/client-login.spec.mjs",
        "ui/cases/client-main-flow.spec.mjs",
        "ui/cases/client-deposit-contract.spec.mjs",
        "ui/cases/client-game-bet-smoke.spec.mjs",
        "ui/cases/client-p0-positive-negative.spec.mjs",
        "--workers=1",
    ]
    ui_env = {
        **env,
        "CLIENT_REUSE_P0_AUTH": "true",
        "CLIENT_AUTH_MODE": "password",
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
    parser.add_argument("--scope", default="FAT")
    parser.add_argument("--allow-known-defect", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--deposit-amount", default="1200")
    parser.add_argument("--withdraw-amount", default="1000")
    args = parser.parse_args()
    env = load_env(Path(args.env))

    if args.mode == "quick":
        run(["python3", "scripts/run-api-tests.py", "p0", "--env", args.env, "--scope", args.scope, "--safe-only", "--no-clean"], env)
        run_default_ui(env, args.allow_known_defect)
        return

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
    normalize_phone = lambda value: "".join(character for character in value if character.isdigit())
    if normalize_phone(pre_kyc_phone) == normalize_phone(kyc_phone):
        raise SystemExit("PRE_KYC_CLIENT_PHONE must be permanently separate from KYC_CLIENT_PHONE")
    run(["python3", "scripts/clean-test-artifacts.py", "ui"], env)
    pre_kyc_env = {
        **env,
        "PRE_KYC_CLIENT_PHONE": pre_kyc_phone,
        "PRE_KYC_CLIENT_PASSWORD": pre_kyc_password,
    }
    run([
        "npx", "playwright", "test",
        "ui/cases/client-unverified-withdraw.spec.mjs", "--workers=1",
    ], pre_kyc_env)
    run([
        "python3", "scripts/run-api-tests.py", "p0",
        "--env", args.env,
        "--scope", args.scope,
        "--write-client-phone", write_phone,
        "--write-client-otp", write_otp,
        "--deposit-amount", args.deposit_amount,
    ], env)
    kyc_password = env.get("KYC_CLIENT_PASSWORD") or env.get("CLIENT_PASSWORD", "")
    if not kyc_password:
        raise SystemExit("full P0 requires KYC_CLIENT_PASSWORD or CLIENT_PASSWORD")
    kyc_env = {
        **env,
        "CLIENT_PHONE": kyc_phone,
        "CLIENT_PASSWORD": kyc_password,
        "CLIENT_OTP": kyc_otp,
        "CLIENT_AUTH_MODE": "password",
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
        "--session-in", "api/results/p0-api-session.json",
        "--session-out", "api/results/p0-kyc-session.json",
        "--out", "api/results/kyc-result.json",
    ], kyc_env)
    fund_env = {
        **env,
        "CLIENT_PHONE": write_phone,
        "CLIENT_PASSWORD": write_password,
        "CLIENT_OTP": write_otp,
        "CLIENT_AUTH_MODE": "password",
    }
    run(["python3", "scripts/import-api-p0-session.py", "--env", args.env], fund_env)
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
        "--session-in", "api/results/p0-api-session.json",
        "--session-out", "api/results/p0-api-session.json",
        "--out", "api/results/withdraw-result.json",
    ], fund_env)
    run(["python3", "scripts/reconcile-p0-flow.py"], fund_env)
    run([
        "python3", "scripts/render-main-flow-report.py",
        "--scope", args.scope,
        "--out", "api/results/p0-main-flow-report.md",
        "--html-out", "api/results/p0-api-report.html",
    ], fund_env)


if __name__ == "__main__":
    main()
