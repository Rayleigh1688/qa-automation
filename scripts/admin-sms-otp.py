#!/usr/bin/env python3
"""Resolve one client SMS OTP through the admin API without persisting it."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def load_smoke_module():
    path = ROOT / "scripts/api-smoke-runner.py"
    spec = importlib.util.spec_from_file_location("api_smoke_runner_for_sms_otp", path)
    if spec is None or spec.loader is None:
        raise SystemExit("cannot load API smoke runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", default=os.environ.get("ENV_FILE", ".env.fat"))
    parser.add_argument("--otp-id", required=True)
    parser.add_argument("--timeout", type=float, default=15)
    parser.add_argument("--insecure", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()

    if not args.otp_id.isdigit():
        raise SystemExit("otp id must be numeric")

    smoke = load_smoke_module()
    smoke.load_env_file(Path(args.env))
    os.environ.pop("API_TOKEN", None)
    os.environ.pop("ADMIN_TOKEN", None)
    lookup_args = argparse.Namespace(
        timeout=args.timeout,
        insecure=args.insecure,
        body_format="cbor",
    )
    code = ""
    for attempt in range(5):
        code = smoke.admin_sms_otp(lookup_args, args.otp_id)
        if isinstance(code, str) and code.isdigit() and len(code) == 6:
            break
        if attempt < 4:
            time.sleep(1.5)
    if not (isinstance(code, str) and code.isdigit() and len(code) == 6):
        secret = os.environ.get("ADMIN_APPROVAL_TOTP_SECRET", "")
        algorithm = os.environ.get("ADMIN_APPROVAL_TOTP_ALGORITHM", "SHA1")
        diagnostic = {"admin_token_present": bool(os.environ.get("ADMIN_TOKEN"))}
        if secret and diagnostic["admin_token_present"]:
            google_code = smoke.current_totp(secret, algorithm=algorithm)
            result = smoke.request_once(
                smoke.login_row(
                    f"{{{{admin_url}}}}/admin/sms/auth?code={google_code}&id={args.otp_id}",
                    "{{admin_url}}",
                    method="GET",
                ),
                args.timeout,
                args.insecure,
                body_format="cbor",
            )
            body = result.get("decoded_body")
            data = body.get("data") if isinstance(body, dict) else None
            diagnostic.update({
                "http_status": result.get("status"),
                "business_status": body.get("status") if isinstance(body, dict) else None,
                "response_code": body.get("code") if isinstance(body, dict) else None,
                "message": (
                    body.get("msg") or body.get("message") or ""
                    if isinstance(body, dict) else ""
                ),
                "data_type": type(data).__name__,
                "data_length": len(data) if isinstance(data, str) else None,
                "data_is_digit": data.isdigit() if isinstance(data, str) else None,
                "data_keys": sorted(data.keys()) if isinstance(data, dict) else [],
            })
        raise SystemExit(f"admin SMS OTP lookup failed: {json.dumps(diagnostic, ensure_ascii=False)}")
    if args.check_only:
        print("resolved=yes")
        return
    sys.stdout.write(code)


if __name__ == "__main__":
    main()
