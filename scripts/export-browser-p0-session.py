#!/usr/bin/env python3
"""Export the ignored Playwright client token into the ignored API session."""

from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path

from p0_session import load_session, write_session


def load_smoke_module():
    from filbet import smoke
    return smoke


smoke = load_smoke_module()


def decoded_signal(value: str) -> object:
    try:
        decoded = smoke.cbor_decode(base64.b64decode(value, validate=True))
    except (ValueError, TypeError):
        return None
    return decoded.get("data") if isinstance(decoded, dict) else None


def load_env(path: Path) -> None:
    from qa_core.environment import load_environment
    os.environ.update(load_environment(path, required=True))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", default=os.environ.get("ENV_FILE", ".env.fat"))
    parser.add_argument("--storage-state", default="ui/results/client-p0-storage-state.json")
    parser.add_argument("--session-out", default="api/results/p0-api-session.json")
    args = parser.parse_args()

    load_env(Path(args.env))
    state = json.loads(Path(args.storage_state).read_text(encoding="utf-8"))
    client_token = ""
    for origin in state.get("origins", []):
        for item in origin.get("localStorage", []):
            name = item.get("name", "")
            raw_value = item.get("value", "")
            if name == "no_clear_signal_api_access_token":
                value = json.loads(raw_value or "{}")
                if isinstance(value, dict) and isinstance(value.get("data"), str):
                    client_token = value["data"]
                    break
            if decoded_signal(name) == "no_clear_signal_api_access_token":
                value = decoded_signal(raw_value)
                if isinstance(value, str) and value:
                    client_token = value
                    break
    if not client_token:
        raise SystemExit("client token not found in Playwright storage state")

    load_session(args.session_out, os.environ.get("CLIENT_PHONE", ""))
    write_session(
        args.session_out,
        client_token=client_token,
        admin_token=os.environ.get("ADMIN_TOKEN", ""),
        client_phone=os.environ.get("CLIENT_PHONE", ""),
    )
    print(f"wrote reusable client session to {args.session_out} (token redacted)")


if __name__ == "__main__":
    main()
