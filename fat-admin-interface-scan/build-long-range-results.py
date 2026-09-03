#!/usr/bin/env python3
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
IGNORED = {"/admin/notify/audit/alarm", "/admin/me/detail", "/admin/game/search"}


def load(name):
    return json.loads((RESULTS / name).read_text())


def write_csv(name, rows, fields):
    with (RESULTS / name).open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


main = load("long-range-admin-results.json")
retry = load("long-range-admin-retry-results.json")
retry_by_route = {page["route"]: page for page in retry["pages"]}
pages = [retry_by_route.get(page["route"], page) for page in main["pages"]]

with (RESULTS / "fat-admin-endpoint-summary.csv").open(newline="") as handle:
    catalog = {(row["method"], row["normalized_path"]): row for row in csv.DictReader(handle)}


def relevant(attempt):
    return [event for event in attempt.get("events", []) if event["path"] not in IGNORED]


def time_unit(value):
    text = str(value)
    if text.isdigit():
        number = int(text)
        if number >= 10**12:
            return "epoch_milliseconds"
        if number >= 10**9:
            return "epoch_seconds"
    if len(text) >= 10 and text[4:5] == "-" and text[7:8] == "-":
        return "date_or_datetime_string"
    return "unknown"


def derived_result(page):
    for attempt in page.get("attempts", []):
        if attempt.get("validation") == "NO_BUSINESS_QUERY_REQUEST" or (
            not relevant(attempt) and attempt["range"] != "7d" and page["result"] == "EMPTY_TO_MAX_RANGE"
        ):
            return "UNVERIFIED_LONG_RANGE", attempt["range"]
    if page["result"] == "EMPTY_TO_MAX_RANGE":
        return "EMPTY_TO_MAX_OBSERVED_RANGE", "page_max_observed"
    return page["result"], page.get("stop_range", "")


page_rows = []
mapping_rows = []
endpoint_stats = defaultdict(lambda: {"pages": set(), "ranges": set(), "success": 0, "failed": 0, "non_empty": 0})

for page in pages:
    result, stop_range = derived_result(page)
    attempts = page.get("attempts", [])
    business_events = [event for attempt in attempts for event in relevant(attempt)]
    page_rows.append({
        "order": page["order"], "top_menu": page["top_menu"], "page_name": page["page_name"],
        "page_route": page["route"], "result": result, "stop_range": stop_range,
        "attempted_ranges": " | ".join(attempt["range"] for attempt in attempts),
        "successful_query_requests": sum(event["http_status"] < 400 and event["business_status"] is not False for event in business_events),
        "business_query_requests": len(business_events),
        "endpoints": " | ".join(sorted({f'{event["method"]} {event["path"]}' for event in business_events})),
        "blocking_scope": page.get("error", "") if result == "ERROR" else (
            "date control rejected target value; query not clicked" if result == "UI_DATE_INPUT_BLOCKED" else
            "QUERY_NOT_TRIGGERED_AFTER_7D: only the 7d empty response is verified; 30/90/365/max are unverified" if result == "UNVERIFIED_LONG_RANGE" else
            f'business failure at {stop_range}; retained without a later success override' if result == "ACTIVE_FAILED" else ""
        ),
        "evidence": "long-range-admin-results.json + long-range-admin-retry-results.json",
    })
    for attempt in attempts:
        for event in relevant(attempt):
            key = (event["method"], event["path"])
            original = catalog.get(key, {})
            times = event.get("time_fields", {})
            corrected_times = {name: {"value": item["value"], "unit": time_unit(item["value"])} for name, item in times.items()}
            success = event["http_status"] < 400 and event["business_status"] is not False
            endpoint_stats[key]["pages"].add(page["route"])
            endpoint_stats[key]["ranges"].add(attempt["range"])
            endpoint_stats[key]["success" if success else "failed"] += 1
            endpoint_stats[key]["non_empty"] += int(bool(event.get("non_empty")))
            mapping_rows.append({
                "caller_surface": "admin", "top_menu": page["top_menu"], "page_name": page["page_name"],
                "page_route": page["route"], "control_type": "date_range_filter",
                "action_name": f'{page.get("query_selector_fallback") or "registered Query/Search"} [{attempt["range"]}]',
                "method": event["method"], "normalized_path": event["path"],
                "query_fields": " | ".join(event.get("query_fields", [])),
                "path_fields": "", "body_fields": " | ".join(event.get("body_fields", [])),
                "header_fields": "not persisted; auth/device values excluded",
                "parameter_source": "visible Start/End date controls; existing page size preserved",
                "requested_start": attempt["start"], "requested_end": attempt["end"],
                "accepted_start": attempt.get("accepted_inputs", {}).get("start", ""),
                "accepted_end": attempt.get("accepted_inputs", {}).get("end", ""),
                "timezone": attempt["timezone"], "time_fields_and_units": json.dumps(corrected_times, ensure_ascii=False, sort_keys=True),
                "page_size_fields": json.dumps(event.get("page_size_fields", {}), ensure_ascii=False, sort_keys=True),
                "request_payload": ("decoded" if event.get("request_body_decoded") else
                    f'opaque {event.get("request_payload_format", "unspecified")} ({event.get("request_body_bytes", 0)} bytes)'),
                "http_status": event["http_status"], "business_status": event["business_status"],
                "response_type": event["response_type"], "response_keys": " | ".join(event.get("response_keys", [])),
                "record_count": event.get("record_count"), "non_empty": event.get("non_empty"),
                "auth_role": "authenticated FAT admin; existing role/permission session reused",
                "side_effect": "none (read-only query)", "before_after_change": "none",
                "original_surface": original.get("original_surface", ""), "original_module": original.get("original_module", ""),
                "original_name": original.get("original_name", ""), "original_source_file": original.get("original_source_file", ""),
                "classification": "ACTIVE_FAILED" if not success else original.get("classification", "UNDOCUMENTED_ACTIVE"),
                "currently_used": "yes", "evidence": "validated visible DOM values + same-action FAT Network response",
                "note": "request body values not claimed when payload was opaque",
            })

write_csv("long-range-page-summary.csv", page_rows, list(page_rows[0]))
write_csv("long-range-page-action-endpoint.csv", mapping_rows, list(mapping_rows[0]))

endpoint_rows = []
for key, stats in sorted(endpoint_stats.items()):
    original = catalog.get(key, {})
    endpoint_rows.append({
        "method": key[0], "normalized_path": key[1], "classification": original.get("classification", "UNDOCUMENTED_ACTIVE"),
        "success_events": stats["success"], "failed_events": stats["failed"], "non_empty_events": stats["non_empty"],
        "pages": " | ".join(sorted(stats["pages"])), "ranges": " | ".join(sorted(stats["ranges"])),
        "already_in_main_endpoint_summary": "yes" if key in catalog else "no",
        "original_module": original.get("original_module", ""), "original_name": original.get("original_name", ""),
        "original_source_file": original.get("original_source_file", ""),
    })
write_csv("long-range-endpoint-summary.csv", endpoint_rows, list(endpoint_rows[0]))

counts = Counter(row["result"] for row in page_rows)
classifications = Counter(row["classification"] for row in endpoint_rows)
summary = {
    "environment": "FAT", "timezone": "Asia/Manila", "menu_baseline_pages": 57,
    "focused_pages": len(page_rows), "page_results": dict(sorted(counts.items())),
    "business_query_requests": sum(row["business_query_requests"] for row in page_rows),
    "successful_query_requests": sum(row["successful_query_requests"] for row in page_rows),
    "unique_endpoints": len(endpoint_rows), "new_endpoints_vs_main": sum(row["already_in_main_endpoint_summary"] == "no" for row in endpoint_rows),
    "endpoint_classifications": dict(sorted(classifications.items())),
    "pages_by_result": {result: [row["page_name"] for row in page_rows if row["result"] == result] for result in sorted(counts)},
    "changes_main_endpoint_count": False,
    "notes": [
        "2020-01-01 through scan date is an observed accepted fallback, not a claimed product-wide configured maximum.",
        "Opaque POST payloads retain only content type/byte length; time parameters are evidenced by accepted UI values without inventing body fields.",
        "No write operation or database mutation was performed.",
    ],
}
(RESULTS / "long-range-admin-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")

lines = [
    "# FAT admin long-range supplemental scan", "",
    f'- Focused pages: {summary["focused_pages"]}/57; unique endpoints: {summary["unique_endpoints"]}; new vs main: {summary["new_endpoints_vs_main"]}.',
    f'- Page results: {json.dumps(summary["page_results"], ensure_ascii=False, sort_keys=True)}.',
    f'- Business query requests: {summary["business_query_requests"]}; successful: {summary["successful_query_requests"]}.',
    "- This is additive evidence only and does not change the 109-endpoint main scan count.", "",
    "## Exceptions", "",
]
for row in page_rows:
    if row["result"] != "NON_EMPTY":
        lines.append(f'- {row["page_name"]} `{row["page_route"]}`: {row["result"]}; ranges={row["attempted_ranges"] or "none"}; {row["blocking_scope"]}')
lines += ["", "## Evidence", "", "- `long-range-page-summary.csv`", "- `long-range-page-action-endpoint.csv`", "- `long-range-endpoint-summary.csv`", "- Raw: `long-range-admin-results.json`, `long-range-admin-retry-results.json`", ""]
(RESULTS / "long-range-admin-report.md").write_text("\n".join(lines))
print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
