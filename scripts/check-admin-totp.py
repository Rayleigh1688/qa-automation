#!/usr/bin/env python3
"""Check whether local admin approval TOTP matches a provided current code.

The script intentionally does not print the generated TOTP or the secret.
Provide the current code from the authenticator app with:

    EXPECTED_ADMIN_APPROVAL_CODE=123456 python3 scripts/check-admin-totp.py
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import struct
import time
from pathlib import Path


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def current_totp(secret: str, timestamp: int | None = None, step: int = 30, digits: int = 6) -> str:
    normalized = secret.strip().replace(" ", "").upper()
    padded = normalized + "=" * (-len(normalized) % 8)
    key = base64.b32decode(padded, casefold=True)
    counter = int((timestamp or time.time()) // step)
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(code % (10**digits)).zfill(digits)


def main() -> None:
    load_env_file(Path(".env"))
    secret = os.environ.get("ADMIN_APPROVAL_TOTP_SECRET", "")
    if not secret:
        raise SystemExit("ADMIN_APPROVAL_TOTP_SECRET is missing in .env")

    expected = os.environ.get("EXPECTED_ADMIN_APPROVAL_CODE", "").strip()
    now = int(time.time())
    seconds_remaining = 30 - (now % 30)

    print("secret: present")
    print(f"system_epoch: {now}")
    print(f"totp_window_seconds_remaining: {seconds_remaining}")

    if not expected:
        print("expected_code: not provided")
        print("match: not checked")
        return

    if not (expected.isdigit() and len(expected) == 6):
        raise SystemExit("EXPECTED_ADMIN_APPROVAL_CODE must be a 6 digit code")

    offsets = {
        "previous_window": -30,
        "current_window": 0,
        "next_window": 30,
    }
    matched = [name for name, offset in offsets.items() if hmac.compare_digest(current_totp(secret, now + offset), expected)]
    print(f"expected_code: provided ({len(expected)} digits)")
    print(f"match: {'yes' if matched else 'no'}")
    if matched:
        print(f"matched_window: {','.join(matched)}")


if __name__ == "__main__":
    main()
