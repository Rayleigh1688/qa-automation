#!/usr/bin/env python3
"""Export the ignored Playwright client token into the ignored API session."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from p0_session import load_session, write_session


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
    parser.add_argument("--storage-state", default="ui/results/client-p0-storage-state.json")
    parser.add_argument("--session-out", default="api/results/p0-api-session.json")
    args = parser.parse_args()

    load_env(Path(args.env))
    state = json.loads(Path(args.storage_state).read_text(encoding="utf-8"))
    client_token = ""
    for origin in state.get("origins", []):
        for item in origin.get("localStorage", []):
            if item.get("name") != "no_clear_signal_api_access_token":
                continue
            value = json.loads(item.get("value", "{}"))
            if isinstance(value, dict) and isinstance(value.get("data"), str):
                client_token = value["data"]
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
