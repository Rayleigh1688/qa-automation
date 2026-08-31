#!/usr/bin/env python3
"""Refresh Playwright storage state from the current ignored API session."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from p0_session import phone_hash


def load_env(path: Path) -> None:
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", default=".env")
    parser.add_argument("--session", default="api/results/p0-api-session.json")
    parser.add_argument("--storage-state", default="ui/results/client-p0-storage-state.json")
    args = parser.parse_args()

    load_env(Path(args.env))
    phone = os.environ.get("CLIENT_PHONE", "")
    session = json.loads(Path(args.session).read_text(encoding="utf-8"))
    client = session.get("client", {})
    if client.get("phone_sha256") != phone_hash(phone):
        raise SystemExit("API session belongs to a different client account")
    token = client.get("token", "")
    if not isinstance(token, str) or not token:
        raise SystemExit("API session has no client token")

    path = Path(args.storage_state)
    state = json.loads(path.read_text(encoding="utf-8"))
    updated = False
    for origin in state.get("origins", []):
        for item in origin.get("localStorage", []):
            if item.get("name") == "no_clear_signal_api_access_token":
                item["value"] = json.dumps({"data": token}, separators=(",", ":"))
                updated = True
    if not updated:
        raise SystemExit("Playwright access-token storage key not found")
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    path.chmod(0o600)
    print(f"refreshed {path} from reusable API session (token redacted)")


if __name__ == "__main__":
    main()
