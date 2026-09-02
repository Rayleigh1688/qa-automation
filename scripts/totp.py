"""Minimal RFC 6238 TOTP helper shared by admin login and approvals."""

from __future__ import annotations

import base64
import hashlib
import hmac
import struct
import time


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
