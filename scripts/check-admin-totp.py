#!/usr/bin/env python3
"""Check or print the local admin approval TOTP.

By default the script does not print the generated TOTP or the secret.
Provide the current code from the authenticator app to compare it with:

    EXPECTED_ADMIN_APPROVAL_CODE=123456 python3 scripts/check-admin-totp.py

Print the current generated TOTP explicitly with:

    python3 scripts/check-admin-totp.py --show-code
"""

from __future__ import annotations

import argparse
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


def digest_factory(algorithm: str):
    normalized = algorithm.strip().lower().replace("-", "")
    if normalized == "sha1":
        return hashlib.sha1
    if normalized == "sha256":
        return hashlib.sha256
    if normalized == "sha512":
        return hashlib.sha512
    raise SystemExit(f"unsupported TOTP algorithm: {algorithm}")


def current_totp(
    secret: str,
    timestamp: int | None = None,
    step: int = 30,
    digits: int = 6,
    algorithm: str = "SHA1",
) -> str:
    normalized = secret.strip().replace(" ", "").upper()
    padded = normalized + "=" * (-len(normalized) % 8)
    key = base64.b32decode(padded, casefold=True)
    counter = int((timestamp or time.time()) // step)
    digest = hmac.new(key, struct.pack(">Q", counter), digest_factory(algorithm)).digest()
    offset = digest[-1] & 0x0F
    code = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(code % (10**digits)).zfill(digits)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--show-code", action="store_true", help="print the current generated TOTP")
    args = parser.parse_args()

    load_env_file(Path(".env"))
    secret = os.environ.get("ADMIN_APPROVAL_TOTP_SECRET", "")
    if not secret:
        raise SystemExit("ADMIN_APPROVAL_TOTP_SECRET is missing in .env")
    algorithm = os.environ.get("ADMIN_APPROVAL_TOTP_ALGORITHM", "SHA1")

    expected = os.environ.get("EXPECTED_ADMIN_APPROVAL_CODE", "").strip()
    now = int(time.time())
    seconds_remaining = 30 - (now % 30)

    print("secret: present")
    print(f"algorithm: {algorithm.upper()}")
    print(f"system_epoch: {now}")
    print(f"totp_window_seconds_remaining: {seconds_remaining}")
    if args.show_code:
        print(f"current_code: {current_totp(secret, now, algorithm=algorithm)}")

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
    matched = [
        name
        for name, offset in offsets.items()
        if hmac.compare_digest(current_totp(secret, now + offset, algorithm=algorithm), expected)
    ]
    print(f"expected_code: provided ({len(expected)} digits)")
    print(f"match: {'yes' if matched else 'no'}")
    if matched:
        print(f"matched_window: {','.join(matched)}")


if __name__ == "__main__":
    main()
