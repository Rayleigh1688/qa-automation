#!/usr/bin/env python3
"""Register the allocated FAT KYC record member without exposing its phone."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "api/results/provisioning/kyc-record-flow"
SUMMARY = RUNTIME / "member-bootstrap-summary.json"
RAW_RESULT = RUNTIME / "register-result.json"
RAW_SESSION = RUNTIME / "register-session.json"
PUBLIC_RESULT = ROOT / "fat-admin-interface-scan/results/record-flow-kyc-registration.json"


def main() -> int:
    source = json.loads(SUMMARY.read_text(encoding="utf-8"))
    phone = str(source.get("phone") or "")
    if not phone.isdigit():
        raise SystemExit("allocated phone is absent or invalid")
    target_ref = "KYC-RUN-" + hashlib.sha256(
        ("fat-kyc-record-flow-v1|" + phone).encode("utf-8")
    ).hexdigest()[:12].upper()
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/api-controlled-flow-runner.py"),
            "--env", ".env.fat",
            "--insecure",
            "--body-format", "cbor",
            "--register",
            "--register-phone", phone,
            "--out", str(RAW_RESULT),
            "--session-out", str(RAW_SESSION),
        ],
        cwd=ROOT,
        env=os.environ.copy(),
        text=True,
        capture_output=True,
        check=False,
    )
    raw_records = json.loads(RAW_RESULT.read_text(encoding="utf-8")) if RAW_RESULT.exists() else []
    public_records = []
    for record in raw_records if isinstance(raw_records, list) else []:
        public_records.append({
            "name": record.get("name"),
            "method": "POST",
            "path": "/member/sms" if record.get("name") == "register_sms" else "/member/register",
            "http_status": record.get("http_status"),
            "business_status": record.get("business_status"),
            "request_fields": ["country_code", "phone", "reason"] if record.get("name") == "register_sms" else ["otp_id", "code", "password", "invite_code", "i"],
            "response_data_type": type(record.get("data")).__name__,
            "skipped": bool(record.get("skipped", False)),
            "reason": record.get("reason", ""),
        })
    payload = {
        "captured_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "environment": "FAT",
        "target_ref": target_ref,
        "data_scope": "THIS_RUN_CREATED",
        "before_state": {"exact_admin_lookup": "ABSENT", "source": "controlled provisioning allocator"},
        "process_exit_code": completed.returncode,
        "records": public_records,
        "raw_evidence": "ignored api/results/provisioning/kyc-record-flow/register-result.json",
    }
    PUBLIC_RESULT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"target_ref": target_ref, "exit_code": completed.returncode, "records": len(public_records)}))
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
