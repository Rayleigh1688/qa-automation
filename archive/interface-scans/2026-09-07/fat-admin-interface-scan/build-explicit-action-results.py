#!/usr/bin/env python3
"""Build explicit-action endpoint rows and combine them with page initialization rows."""

from __future__ import annotations

import csv
import argparse
import json
import re
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "fat-admin-interface-scan/results"
INVENTORY = RESULTS / "fat-admin-explicit-actions.json"
INIT_ROWS = RESULTS / "fat-admin-page-initialization-interface.csv"
COMBINED_OUT = RESULTS / "fat-admin-page-action-interface.csv"

FIELDS = [
    "surface", "top_menu", "page_name", "page_route", "control_type", "action_name",
    "method", "normalized_path", "query_fields", "path_fields", "body_fields",
    "header_fields", "parameter_source", "http_status", "business_status",
    "response_structure", "auth_role", "side_effect", "before_state", "after_state",
    "original_category", "original_name", "original_source_file", "classification",
    "currently_used_by_ui", "evidence", "anomaly", "blocked_scope",
]


def canonical(path):
    path = re.sub(r"/[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}(?=/|$)", "/{id}", path)
    path = re.sub(r"/\d{6,}(?=/|$)", "/{id}", path)
    return re.sub(r"\{[^/]+\}", "{id}", path)


def inventory_maps():
    exact, normalized = defaultdict(list), defaultdict(list)
    with (ROOT / "api/inventory/interfaces.csv").open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            method, path = row.get("method", "").upper(), row.get("path", "")
            if method and path:
                exact[(method, path)].append(row)
                normalized[(method, canonical(path))].append(row)
    return exact, normalized


def match_inventory(method, path, exact, normalized):
    matches = exact.get((method, path)) or normalized.get((method, canonical(path))) or []
    return matches[0] if matches else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", default="read")
    parser.add_argument("--risk", default="READ_INTERACTION")
    args = parser.parse_args()
    raw_path = RESULTS / f"fat-admin-explicit-{args.artifact}-actions.json"
    action_out = RESULTS / f"fat-admin-explicit-{args.artifact}-action-interface.csv"
    summary_out = RESULTS / f"fat-admin-explicit-{args.artifact}-action-summary.json"

    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    planned = json.loads(INVENTORY.read_text(encoding="utf-8"))["actions"]
    exact, normalized = inventory_maps()
    execution_map = {(item["page_route"], item["control_type"], item["action_name"]): item for item in raw["executions"]}

    grouped = {}
    for index, event in enumerate(raw["network"], start=1):
        if event.get("control_type") in {"page_initialization", "login"}:
            continue
        key = (
            event.get("page_route"), event.get("control_type"), event.get("action_name"),
            event.get("method"), event.get("path"), event.get("http_status"), str(event.get("business_status")),
        )
        item = grouped.setdefault(key, {"event": event, "indices": [], "query": set(), "body": set(), "headers": set()})
        item["indices"].append(index)
        item["query"].update(event.get("query_fields", []))
        item["body"].update(event.get("body_fields", []))
        item["headers"].update(event.get("header_fields", []))

    action_meta = {(item["page_route"], item["control_type"], item["action_name"]): item for item in planned}
    rows = []
    observed_actions = set()
    for item in grouped.values():
        event = item["event"]
        key = (event["page_route"], event["control_type"], event["action_name"])
        observed_actions.add(key)
        meta = action_meta.get(key)
        if meta is None:
            page_meta = next(item for item in planned if item["page_route"] == event["page_route"])
            meta = {
                **page_meta,
                "control_type": event["control_type"],
                "action_name": event["action_name"],
                "selector_strategy": "registered Query/Search selector from explicit action inventory",
            }
        documented = match_inventory(event["method"], event["path"], exact, normalized)
        success = 200 <= int(event.get("http_status") or 0) < 300 and event.get("business_status") is not False
        classification = ("ACTIVE" if documented else "UNDOCUMENTED_ACTIVE") if success else "ACTIVE_FAILED"
        response = event.get("response_data_type", "unknown")
        if event.get("response_data_keys"):
            response += "; keys=" + ",".join(event["response_data_keys"])
        sources = []
        if item["query"]: sources.append("Query: current page filter/pagination")
        if item["body"]: sources.append("Body: current page form/filter and UI defaults")
        if item["headers"]: sources.append("Header: authenticated browser session/runtime")
        rows.append({
            "surface": "admin", "top_menu": meta["top_menu"], "page_name": meta["page_name"],
            "page_route": meta["page_route"], "control_type": meta["control_type"], "action_name": meta["action_name"],
            "method": event["method"], "normalized_path": event["path"],
            "query_fields": ",".join(sorted(item["query"])), "path_fields": "id" if "{id}" in event["path"] else "",
            "body_fields": ",".join(sorted(item["body"])), "header_fields": ",".join(sorted(item["headers"])),
            "parameter_source": "; ".join(sources) or "No request parameters observed",
            "http_status": event.get("http_status", ""), "business_status": event.get("business_status", ""),
            "response_structure": response,
            "auth_role": "FAT admin authenticated browser session; exact role/permission mapping pending",
            "side_effect": "No mutation observed; registered low-risk interaction",
            "before_state": "Page reloaded and Network reached quiet state before action",
            "after_state": "Action response captured; no business mutation observed",
            "original_category": f"{documented['surface']}/{documented['module']}" if documented else "",
            "original_name": documented.get("name", "") if documented else "",
            "original_source_file": documented.get("file", "") if documented else "",
            "classification": classification, "currently_used_by_ui": "YES",
            "evidence": f"fat-admin-explicit-read-actions.json Network events {','.join(map(str, item['indices']))}; exact selector {meta['selector_strategy']}",
            "anomaly": "" if success else f"HTTP {event.get('http_status')}; business_status={event.get('business_status')}",
            "blocked_scope": "" if success else "Dependent interactions require separate verification",
        })

    for meta in planned:
        key = (meta["page_route"], meta["control_type"], meta["action_name"])
        if meta["risk"] != args.risk or key in observed_actions:
            continue
        execution = execution_map.get(key, {})
        status = execution.get("status", "NOT_EXECUTED")
        rows.append({
            "surface": "admin", "top_menu": meta["top_menu"], "page_name": meta["page_name"],
            "page_route": meta["page_route"], "control_type": meta["control_type"], "action_name": meta["action_name"],
            "method": "", "normalized_path": "", "query_fields": "", "path_fields": "", "body_fields": "", "header_fields": "",
            "parameter_source": "No request captured",
            "http_status": "", "business_status": "", "response_structure": "unverified",
            "auth_role": "FAT admin authenticated browser session; exact role/permission mapping pending",
            "side_effect": "No mutation observed", "before_state": "Page loaded",
            "after_state": "No request captured",
            "original_category": "", "original_name": "", "original_source_file": "",
            "classification": "DOCUMENTED_UNVERIFIED", "currently_used_by_ui": "CONTROL_PRESENT_NO_REQUEST",
            "evidence": f"fat-admin-explicit-read-actions.json execution status={status}; exact selector {meta['selector_strategy']}",
            "anomaly": execution.get("error", ""),
            "blocked_scope": "Control was not actionable in the fresh page state" if status.startswith("SKIPPED") else "Click produced no XHR/fetch; navigation/DOM effect requires follow-up",
        })

    rows.sort(key=lambda row: (row["page_route"], row["action_name"], row["method"], row["normalized_path"]))
    with action_out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS); writer.writeheader(); writer.writerows(rows)

    with INIT_ROWS.open(encoding="utf-8", newline="") as handle:
        combined = list(csv.DictReader(handle))
    for candidate in sorted(RESULTS.glob("fat-admin-explicit-*-action-interface.csv")):
        with candidate.open(encoding="utf-8", newline="") as handle:
            combined.extend(csv.DictReader(handle))
    with COMBINED_OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS); writer.writeheader(); writer.writerows(combined)

    classifications = defaultdict(int)
    for row in rows: classifications[row["classification"]] += 1
    summary = {
        "generated_at": raw.get("captured_at"), "environment": "FAT",
        "planned_actions": raw.get("actions_planned"), "completed_actions": len(raw.get("executions", [])),
        "clicked_actions": sum(item.get("status") == "CLICKED" for item in raw.get("executions", [])),
        "interacted_actions": sum(item.get("status") == "INTERACTED" for item in raw.get("executions", [])),
        "skipped_actions": sum(str(item.get("status", "")).startswith("SKIPPED") for item in raw.get("executions", [])),
        "error_actions": sum(item.get("status") == "ERROR" for item in raw.get("executions", [])),
        "action_network_events": sum(item.get("control_type") not in {"page_initialization", "login"} for item in raw.get("network", [])),
        "deduplicated_action_rows": len(rows), "classifications": dict(sorted(classifications.items())),
        "combined_initialization_and_action_rows": len(combined), "fatal_error": raw.get("fatal_error"),
    }
    summary_out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
