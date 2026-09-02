#!/usr/bin/env python3
"""Refresh Playwright storage state from the current ignored API session."""

from __future__ import annotations

import argparse
import base64
import importlib.util
import json
import os
from pathlib import Path
from types import ModuleType
from urllib.parse import urlparse

from p0_session import phone_hash


def load_smoke_module() -> ModuleType:
    path = Path(__file__).with_name("api-smoke-runner.py")
    spec = importlib.util.spec_from_file_location("api_smoke_runner_for_storage", path)
    if spec is None or spec.loader is None:
        raise SystemExit("cannot load CBOR codec")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


smoke = load_smoke_module()


def signal_storage_text(value: object) -> str:
    return base64.b64encode(smoke.cbor_encode({"data": value})).decode("ascii")


def upsert_storage(local_storage: list[dict[str, str]], name: str, value: str) -> None:
    item = next((entry for entry in local_storage if entry.get("name") == name), None)
    if item is None:
        item = {"name": name, "value": ""}
        local_storage.append(item)
    item["value"] = value


def load_env(path: Path) -> None:
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if os.environ.get("ENV_FILE_PRECEDENCE") == "shell":
            os.environ.setdefault(key, value)
        else:
            os.environ[key] = value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", default=os.environ.get("ENV_FILE", ".env.fat"))
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
    base_url = os.environ.get("CLIENT_BASE_URL") or os.environ.get("API_URL", "")
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise SystemExit("CLIENT_BASE_URL or API_URL must contain a valid client origin")
    target_origin = f"{parsed.scheme}://{parsed.netloc}"

    state = {"cookies": [], "origins": []}
    if path.is_file():
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            state = loaded
    origins = state.get("origins") if isinstance(state.get("origins"), list) else []
    target = next((item for item in origins if item.get("origin") == target_origin), None)
    if target is None:
        # Never carry cookies or localStorage from FAT into UAT (or vice versa).
        state = {"cookies": [], "origins": []}
        target = {"origin": target_origin, "localStorage": []}
        state["origins"].append(target)
    local_storage = target.get("localStorage")
    if not isinstance(local_storage, list):
        local_storage = []
        target["localStorage"] = local_storage
    account = {"phone": phone, "profile_icon": "", "profile_username": ""}
    for name, value in (
        ("no_clear_signal_api_access_token", token),
        ("no_clear_signal_logged_in_account", account),
    ):
        # FAT currently reads JSON under the plain logical key. UAT uses the
        # same logical signal encoded as CBOR+Base64 for both key and value.
        upsert_storage(local_storage, name, json.dumps({"data": value}, separators=(",", ":")))
        upsert_storage(local_storage, signal_storage_text(name), signal_storage_text(value))
    for consent_name in (
        "signal_736be95_isTermsAndConditionsAgree",
        "signal_736be95_isTermsAndConditionsProceeded",
    ):
        consent = next((item for item in local_storage if item.get("name") == consent_name), None)
        if consent is None:
            consent = {"name": consent_name, "value": ""}
            local_storage.append(consent)
        consent["value"] = json.dumps({"data": True}, separators=(",", ":"))

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    path.chmod(0o600)
    print(f"refreshed {path} from reusable API session (token redacted)")


if __name__ == "__main__":
    main()
