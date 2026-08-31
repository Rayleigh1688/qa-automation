"""Read and write ignored local P0 API session tokens."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


def phone_hash(phone: str) -> str:
    normalized = "".join(character for character in phone if character.isdigit())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest() if normalized else ""


def write_session(path: str, client_token: str = "", admin_token: str = "", client_phone: str = "") -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "client": {
            "phone_sha256": phone_hash(client_phone),
            "token": client_token,
        },
        "admin": {"token": admin_token},
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    output.chmod(0o600)


def load_session(path: str, client_phone: str = "") -> dict[str, bool]:
    source = Path(path)
    if not source.exists():
        return {"client": False, "admin": False}
    payload = json.loads(source.read_text(encoding="utf-8"))
    client = payload.get("client") if isinstance(payload, dict) else {}
    admin = payload.get("admin") if isinstance(payload, dict) else {}
    loaded = {"client": False, "admin": False}

    expected_hash = phone_hash(client_phone)
    if isinstance(client, dict) and expected_hash and client.get("phone_sha256") == expected_hash:
        token = client.get("token")
        if isinstance(token, str) and token:
            os.environ["API_TOKEN"] = token
            loaded["client"] = True

    if isinstance(admin, dict):
        token = admin.get("token")
        if isinstance(token, str) and token:
            os.environ["ADMIN_TOKEN"] = token
            loaded["admin"] = True
    return loaded
