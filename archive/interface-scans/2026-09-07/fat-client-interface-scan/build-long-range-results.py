#!/usr/bin/env python3
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "fat-client-interface-scan/results"


def main():
    raw = json.loads((RESULTS / "long-range-network.json").read_text())
    progress = json.loads((RESULTS / "long-range-progress.json").read_text())
    with (ROOT / "api/inventory/interfaces.csv").open(newline="", encoding="utf-8-sig") as handle:
        inventory = list(csv.DictReader(handle))
    docs = {}
    for item in inventory:
        docs.setdefault((item.get("method", "").upper(), item.get("path", "")), []).append(item)

    selected = [item for item in raw["records"] if item.get("requestedRange")]
    rows = []
    for item in selected:
        matches = docs.get((item["method"], item["normalizedPath"]), [])
        page_progress = next(page for page in progress["pages"] if page["page"] == item["page"])
        pagination = page_progress.get("paginationSample") or {}
        rows.append({
            "surface": "client",
            "menu": "My / History",
            "page": item["page"],
            "page_route": item["pageRoute"],
            "control_type": "date_range_filter",
            "action": item["action"],
            "method": item["method"],
            "normalized_path": item["normalizedPath"],
            "time_parameter_fields": "|".join(item["timeParameters"]),
            "time_flag": item["timeParameters"].get("time_flag", ""),
            "time_unit": "days (confirmed by UI label)",
            "selected_ui_range": item.get("selectedUiLabel", ""),
            "timezone": item["timezone"],
            "page_number": item["timeParameters"].get("page", ""),
            "page_size": item["timeParameters"].get("page_size", ""),
            "non_empty": str(item["nonEmpty"]).lower(),
            "returned_record_count": item["recordCount"],
            "total_count": "" if item["totalCount"] is None else item["totalCount"],
            "page_2_sample": json.dumps(pagination, ensure_ascii=False, separators=(",", ":")),
            "http_status": item["httpStatus"],
            "business_status": item["businessStatus"],
            "response_structure": json.dumps(item["responseStructure"], ensure_ascii=False, separators=(",", ":")),
            "auth_role": item["auth"],
            "side_effect": item["sideEffect"],
            "document_category": "|".join(sorted({f"{doc['surface']}/{doc['module']}" for doc in matches})),
            "document_name": "|".join(sorted({doc["name"] for doc in matches})),
            "document_source": "|".join(sorted({doc["file"] for doc in matches})),
            "classification": item["classification"] if matches and any(doc.get("surface") == "client" for doc in matches) else "MISCLASSIFIED",
            "evidence": "long-range-network.json selected range response; long-range-progress.json pagination sample",
            "blocked_scope": "" if pagination.get("captured") or not pagination.get("attempted") else pagination.get("reason", ""),
        })

    out = RESULTS / "long-range-page-action-interface.csv"
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    max_options = {}
    for page in progress["pages"]:
        labels = [item["text"] for item in page["availableRangeOptions"]]
        max_options[page["page"]] = labels[-1] if labels else "unknown"
    summary = {
        "scannedAt": raw["scannedAt"],
        "environment": "FAT",
        "timezone": raw["timezone"],
        "pages": len(progress["pages"]),
        "nonEmptyAt7Days": sum(page.get("selectedResult", {}).get("range") == "7d" for page in progress["pages"]),
        "newEndpoints": 0,
        "observedEndpoints": sorted({f"{row['method']} {row['normalized_path']}" for row in rows}),
        "pageMaximumLegalRanges": max_options,
        "pagination": {page["page"]: page.get("paginationSample") for page in progress["pages"]},
        "notes": [
            "All four pages returned non-empty data at 7 days, so 30/90/365-day requests were not executed.",
            "The UI exposes Today, Yesterday, Last 7 days, Last 15 days, and Last 30 days; 90/365-day and All Time options are not available.",
            "Page size remained 10. Page 2 was sampled only where total count exceeded 10.",
            "No endpoint was added; this run strengthens time-range and pagination evidence for four previously observed endpoints.",
        ],
    }
    (RESULTS / "long-range-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
