#!/usr/bin/env python3
"""Build a deduplicated, redacted page/action/API mapping from the admin UI scan."""

from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCAN_DIR = ROOT / "fat-admin-interface-scan"
RESULT_DIR = SCAN_DIR / "results"
RAW_PATH = RESULT_DIR / "fat-admin-page-initialization.json"
OUT_PATH = RESULT_DIR / "fat-admin-page-initialization-interface.csv"
SUMMARY_PATH = RESULT_DIR / "fat-admin-page-initialization-summary.json"


FIELDS = [
    "surface", "top_menu", "page_name", "page_route", "control_type", "action_name",
    "method", "normalized_path", "query_fields", "path_fields", "body_fields",
    "header_fields", "parameter_source", "http_status", "business_status",
    "response_structure", "auth_role", "side_effect", "before_state", "after_state",
    "original_category", "original_name", "original_source_file", "classification",
    "currently_used_by_ui", "evidence", "anomaly", "blocked_scope",
]


def normalize_path(value: str) -> tuple[str, list[str]]:
    fields: list[str] = []
    parts = []
    for part in value.split("/"):
        if re.fullmatch(r"\d+", part):
            fields.append("id")
            parts.append("{id}")
        elif re.fullmatch(r"[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}", part):
            fields.append("uuid")
            parts.append("{uuid}")
        else:
            parts.append(part)
    return "/".join(parts), fields


def load_inventory():
    exact = defaultdict(list)
    canonical = defaultdict(list)
    with (ROOT / "api/inventory/interfaces.csv").open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            method, path = row.get("method", "").upper(), row.get("path", "")
            if not method or not path:
                continue
            exact[(method, path)].append(row)
            normalized, _ = normalize_path(path)
            normalized = re.sub(r"\{[^/]+\}", "{id}", normalized)
            canonical[(method, normalized)].append(row)
    return exact, canonical


def inventory_match(event, exact, canonical):
    method, path = event["method"].upper(), event["path"]
    rows = exact.get((method, path), [])
    if rows:
        return rows[0]
    normalized, _ = normalize_path(path)
    normalized = re.sub(r"\{[^/]+\}", "{id}", normalized)
    rows = canonical.get((method, normalized), [])
    return rows[0] if rows else None


def main():
    payload = json.loads(RAW_PATH.read_text(encoding="utf-8"))
    exact, canonical = load_inventory()

    pages = {item["route"]: item for item in payload.get("pages", [])}
    grouped = {}
    for index, event in enumerate(payload.get("network", []), start=1):
        key = (
            event.get("page_route", ""), event.get("control_type", ""), event.get("action_name", ""),
            event.get("method", ""), event.get("path", ""), event.get("http_status"),
            str(event.get("business_status")),
        )
        if key not in grouped:
            grouped[key] = {"event": event, "indices": [], "query": set(), "body": set(), "headers": set()}
        item = grouped[key]
        item["indices"].append(index)
        item["query"].update(event.get("query_fields", []))
        item["body"].update(event.get("body_fields", []))
        item["headers"].update(event.get("header_fields", []))

    rows = []
    classifications = defaultdict(int)
    for item in grouped.values():
        event = item["event"]
        route = event.get("page_route", "")
        page = pages.get(route, {})
        page_name = page.get("page_name") or ("Login" if route == "login" else route)
        matched = inventory_match(event, exact, canonical)
        normalized, path_fields = normalize_path(event.get("path", ""))
        success = 200 <= int(event.get("http_status") or 0) < 300 and event.get("business_status") is not False
        classification = ("ACTIVE" if matched else "UNDOCUMENTED_ACTIVE") if success else "ACTIVE_FAILED"
        classifications[classification] += 1
        response_keys = event.get("response_data_keys", [])
        response_structure = event.get("response_data_type", "unknown")
        if response_keys:
            response_structure += f"; keys={','.join(response_keys)}"
        sources = []
        if item["query"]:
            sources.append("Query: route/filter/pagination values emitted by current UI state")
        if path_fields:
            sources.append("Path: current page/list record")
        if item["body"]:
            sources.append("Body: page form/filter or UI defaults")
        if item["headers"]:
            sources.append("Header: browser session/runtime")
        control_type = event.get("control_type", "")
        read_observation = control_type in {"page_initialization", "button", "pagination", "tab"}
        anomaly = "" if success else f"HTTP {event.get('http_status')}; business_status={event.get('business_status')}"
        rows.append({
            "surface": "admin",
            "top_menu": page.get("top_menu") or ("Login/Auth" if route == "login" else "TO_MAP"),
            "page_name": page_name,
            "page_route": route,
            "control_type": control_type,
            "action_name": event.get("action_name", ""),
            "method": event.get("method", ""),
            "normalized_path": normalized,
            "query_fields": ",".join(sorted(item["query"])),
            "path_fields": ",".join(path_fields),
            "body_fields": ",".join(sorted(item["body"])),
            "header_fields": ",".join(sorted(item["headers"])),
            "parameter_source": "; ".join(sources) or "No request parameters observed",
            "http_status": event.get("http_status", ""),
            "business_status": event.get("business_status", ""),
            "response_structure": response_structure,
            "auth_role": "FAT admin authenticated browser session; exact permission/role mapping pending",
            "side_effect": "No mutation observed in this discovery action" if read_observation else "TO_VERIFY",
            "before_state": "Not applicable for observed read interaction",
            "after_state": "Page/network response rendered; business data values not persisted",
            "original_category": f"{matched['surface']}/{matched['module']}" if matched else "",
            "original_name": matched.get("name", "") if matched else "",
            "original_source_file": matched.get("file", "") if matched else "",
            "classification": classification,
            "currently_used_by_ui": "YES",
            "evidence": f"fat-admin-page-initialization.json network events {','.join(map(str, item['indices']))}; live-menu route and DOM control snapshot",
            "anomaly": anomaly,
            "blocked_scope": "" if success else "Dependent interactions on this failed response require separate verification",
        })

    rows.sort(key=lambda row: (row["page_route"], row["action_name"], row["method"], row["normalized_path"]))
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "generated_at": payload.get("captured_at"),
        "environment": payload.get("environment"),
        "completed_pages": len(payload.get("pages", [])),
        "total_pages": len(payload.get("routes", [])),
        "raw_network_events": len(payload.get("network", [])),
        "deduplicated_page_action_endpoints": len(rows),
        "unique_method_paths": len({(row["method"], row["normalized_path"]) for row in rows}),
        "classifications": dict(sorted(classifications.items())),
        "page_errors": sum(bool(page.get("error")) for page in payload.get("pages", [])),
        "fatal_error": payload.get("fatal_error"),
    }
    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
