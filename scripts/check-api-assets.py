#!/usr/bin/env python3
"""Validate generated API assets, classification, and secret redaction."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit
from qa_core.contracts import MILLISECOND_WINDOW_PATHS


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def sensitive_key(key: str) -> bool:
    lowered = key.lower().replace("-", "_")
    exact = {
        "authorization", "code", "device_id", "email", "hash_code", "mobile",
        "otp", "password", "phone", "player_id", "secret", "session",
        "session_id", "t", "token", "uid", "x_device_id",
    }
    return (
        lowered in exact
        or lowered.endswith(("_phone", "_mobile", "_uid", "_token", "_session", "_session_id"))
        or any(part in lowered for part in ("password", "authorization", "hash_code", "player_id"))
    )


def query_pairs(value: str) -> list[tuple[str, str]]:
    query = urlsplit(value).query if value.startswith(("http://", "https://")) else value.partition("?")[2]
    return parse_qsl(query, keep_blank_values=True)


def main() -> None:
    inventory_path = Path("api/inventory/interfaces.csv")
    cases_path = Path("api/p0/test-cases.csv")
    inventory = read_csv(inventory_path)
    cases = read_csv(cases_path)
    errors: list[str] = []

    for row in cases:
        if row.get("path") in MILLISECOND_WINDOW_PATHS and row.get("execution_policy") == "safe_smoke":
            body = json.loads(row.get("request_body") or "{}")
            expected = {"start_time": "{{now_minus_2d_ms}}", "end_time": "{{now_plus_5m_ms}}"}
            if any(body.get(key) != value for key, value in expected.items()):
                errors.append(f"{row.get('case_id')}: withdrawal audit requires millisecond time tokens")

    for required in ("surface", "module", "clean_url", "url"):
        if inventory and required not in inventory[0]:
            errors.append(f"inventory missing column: {required}")
    for row in inventory:
        if row.get("method") and row.get("surface") not in {"client", "admin", "agency", "unknown"}:
            errors.append(f"invalid surface: {row.get('file')}")
        for column in ("url", "clean_url"):
            for key, value in query_pairs(row.get(column, "")):
                if sensitive_key(key) and value not in {"", "<redacted>"} and not value.startswith("{{"):
                    errors.append(f"unredacted query value: {row.get('file')}:{column}:{key}")

    inventory_text = inventory_path.read_text(encoding="utf-8")
    if re.search(r"(?<!\d)(?:09|9)\d{8,10}(?!\d)", inventory_text):
        errors.append("inventory contains a phone-like literal")
    if re.search(r"(?<!\d)\d{16,20}(?!\d)", inventory_text):
        errors.append("inventory contains a UID-like literal")

    case_ids = [row.get("case_id", "") for row in cases]
    orders = [row.get("case_order", "") for row in cases]
    if len(case_ids) != len(set(case_ids)):
        errors.append("P0 case_id values are not unique")
    if len(orders) != len(set(orders)):
        errors.append("P0 case_order values are not unique")
    if any(not row.get("surface") or not row.get("module") for row in cases):
        errors.append("P0 cases contain empty surface/module")
    if len({row.get("scenario_id") for row in cases}) != 8:
        errors.append("P0 cases must map to exactly eight main-flow scenarios")

    catalog_rows = sum(
        len(read_csv(Path("api/catalog") / f"{surface}.csv"))
        for surface in ("client", "admin", "agency", "unknown")
    )
    request_rows = sum(bool(row.get("method")) for row in inventory)
    if catalog_rows != request_rows:
        errors.append(f"catalog row count {catalog_rows} != inventory request count {request_rows}")

    if errors:
        raise SystemExit("\n".join(f"ERROR: {error}" for error in errors))
    print(
        f"api assets valid: inventory={len(inventory)} requests={request_rows} "
        f"p0_cases={len(cases)}"
    )


if __name__ == "__main__":
    main()
