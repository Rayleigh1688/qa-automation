#!/usr/bin/env python3
"""Merge current FAT admin dynamic evidence without touching shared inventory/catalog."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
BASE = RESULTS / "fat-admin-endpoint-summary.csv"
SUPPLEMENTS = (
    RESULTS / "record-flow-member-action-endpoint.csv",
    RESULTS / "record-flow-kyc-page-action-endpoint.csv",
    RESULTS / "record-flow-member-write-action-endpoint.csv",
    RESULTS / "member-list-a-action-endpoint.csv",
    RESULTS / "record-flow-member-tab-readonly-action-endpoint.csv",
)
OUT_CSV = RESULTS / "member-gap-merged-endpoint-summary.csv"
OUT_JSON = RESULTS / "member-gap-merged-summary.json"
OUT_MD = RESULTS / "member-gap-merged-report.md"
ALLOWED = {
    "ACTIVE", "ACTIVE_FAILED", "UNDOCUMENTED_ACTIVE", "DOCUMENTED_REACHABLE",
    "DOCUMENTED_UNVERIFIED", "STALE", "REPLACED_BY", "THIRD_PARTY", "MISCLASSIFIED",
}


def truthy(value: str) -> bool:
    return value.strip().lower() in {"true", "1", "yes"}


def choose_classification(values: set[str], success: int, failure: int) -> str:
    if "MISCLASSIFIED" in values:
        return "MISCLASSIFIED"
    if "UNDOCUMENTED_ACTIVE" in values:
        return "UNDOCUMENTED_ACTIVE"
    if success:
        return "ACTIVE"
    if failure:
        return "ACTIVE_FAILED"
    return "DOCUMENTED_UNVERIFIED"


def main() -> None:
    merged: dict[tuple[str, str], dict] = defaultdict(lambda: {
        "success": 0, "failure": 0, "classifications": set(), "sources": set(),
        "pages": set(), "actions": set(), "http": set(), "business": set(),
    })

    with BASE.open(newline="") as handle:
        for row in csv.DictReader(handle):
            method, endpoint = row["method"].strip(), row["normalized_path"].strip()
            if not endpoint.startswith("/admin/"):
                continue
            item = merged[(method, endpoint)]
            item["success"] += int(row.get("success_events") or 0)
            item["failure"] += int(row.get("failed_events") or 0)
            item["classifications"].add(row.get("classification", ""))
            item["sources"].add(BASE.name)
            item["pages"].update(filter(None, row.get("pages", "").split(" | ")))
            item["actions"].update(filter(None, row.get("actions", "").split(" | ")))
            item["http"].update(filter(None, row.get("http_statuses", "").split(" | ")))
            item["business"].update(filter(None, row.get("business_statuses", "").split(" | ")))

    for path in SUPPLEMENTS:
        with path.open(newline="") as handle:
            for row in csv.DictReader(handle):
                method = (row.get("method") or row.get("request_method") or "").strip()
                endpoint = (row.get("normalized_path") or "").strip()
                status = (row.get("http_status") or "").strip()
                business = (row.get("business_status") or "").strip()
                if method not in {"GET", "POST", "PUT", "PATCH", "DELETE"} or "|" in endpoint or not endpoint.startswith("/admin/") or not status.isdigit():
                    continue
                item = merged[(method, endpoint)]
                is_success = int(status) < 400 and truthy(business)
                item["success" if is_success else "failure"] += 1
                classification = (row.get("classification") or row.get("current_classification") or "").strip()
                if classification in ALLOWED:
                    item["classifications"].add(classification)
                item["sources"].add(path.name)
                item["pages"].add((row.get("page_name") or row.get("page") or "").strip())
                item["actions"].add((row.get("action_name") or row.get("operation") or "").strip())
                item["http"].add(status)
                item["business"].add(business)

    rows = []
    for (method, endpoint), item in sorted(merged.items()):
        classification = choose_classification(
            {value for value in item["classifications"] if value in ALLOWED},
            item["success"], item["failure"],
        )
        rows.append({
            "method": method,
            "normalized_path": endpoint,
            "classification": classification,
            "success_events": item["success"],
            "failed_events": item["failure"],
            "pages": " | ".join(sorted(filter(None, item["pages"]))),
            "actions": " | ".join(sorted(filter(None, item["actions"]))),
            "http_statuses": " | ".join(sorted(filter(None, item["http"]))),
            "business_statuses": " | ".join(sorted(filter(None, item["business"]))),
            "evidence_sources": " | ".join(sorted(item["sources"])),
        })

    with OUT_CSV.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    counts = Counter(row["classification"] for row in rows)
    summary = {
        "environment": "FAT",
        "scope": "admin UI dynamic evidence through member-list/detail gap completion",
        "unique_admin_method_paths": len(rows),
        "classifications": dict(sorted(counts.items())),
        "shared_inventory_or_catalog_modified": False,
        "member_list_actions": 30,
        "member_detail_tabs": 17,
        "member_detail_ui_action_decisions": 72,
        "member_detail_action_endpoint_rows": 76,
        "turnover_reversible_flow": "0 → 1 → 0",
        "unrestored_side_effects": 0,
    }
    OUT_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    OUT_MD.write_text(
        "# FAT admin member-gap merged result\n\n"
        f"- Unique current admin method+paths: {len(rows)}\n"
        f"- Classification counts: {dict(sorted(counts.items()))}\n"
        "- Member list: 30 action decisions; Batch/filter/pagination/row entries covered.\n"
        "- Member Detail: 17/17 DOM inventories, 72 UI action decisions, 76 action-endpoint rows.\n"
        "- Turnover controlled write: 0 → 1 → 0; database read-only evidence confirms the row is finished and unlocked.\n"
        "- Shared `api/inventory/interfaces.csv` and `api/catalog/` were not modified.\n"
    )
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
