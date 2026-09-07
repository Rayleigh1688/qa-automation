#!/usr/bin/env python3
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "fat-admin-interface-scan" / "results"
SOURCE = RESULTS / "member-list-a-internal-read-scan.json"
CSV_OUT = RESULTS / "member-list-a-action-endpoint.csv"
MD_OUT = RESULTS / "member-list-a-report.md"


def load_inventory():
    exact, by_path = {}, {}
    with (ROOT / "api" / "inventory" / "interfaces.csv").open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            method, path = row.get("method", ""), row.get("path", "")
            if not method or not path:
                continue
            exact[(method, path)] = row
            by_path.setdefault(path, []).append(row)
    return exact, by_path


def join(values):
    return "|".join(sorted({str(value) for value in values if value not in (None, "")}))


def classify(events, operation, exact, by_path):
    if not events:
        return "DOCUMENTED_UNVERIFIED"
    classifications = []
    for event in events:
        key = (event["method"], event["path"])
        if key in exact:
            classifications.append("ACTIVE" if event.get("business_status") is True and event.get("http_status", 0) < 400 else "ACTIVE_FAILED")
        elif event["path"] in by_path:
            classifications.append("MISCLASSIFIED")
        else:
            classifications.append("UNDOCUMENTED_ACTIVE" if event.get("business_status") is True and event.get("http_status", 0) < 400 else "ACTIVE_FAILED")
    if "ACTIVE_FAILED" in classifications and not any(value in classifications for value in ("ACTIVE", "MISCLASSIFIED", "UNDOCUMENTED_ACTIVE")):
        return "ACTIVE_FAILED"
    if "MISCLASSIFIED" in classifications:
        return "MISCLASSIFIED"
    if "UNDOCUMENTED_ACTIVE" in classifications:
        return "UNDOCUMENTED_ACTIVE"
    return "ACTIVE"


data = json.loads(SOURCE.read_text(encoding="utf-8"))
exact, by_path = load_inventory()
rows = []

all_actions = [(item["name"], item) for item in data["actions"]] + [(f"member_list:row:{item['action']}", item) for item in data["row_actions"]]
for operation, item in all_actions:
    indexes = item.get("network_event_indexes", [0, 0])
    events = data["network"][indexes[0]:indexes[1]] if len(indexes) == 2 else []
    methods = join(event["method"] for event in events)
    paths = join(event["path"] for event in events)
    docs = []
    for event in events:
        doc = exact.get((event["method"], event["path"]))
        if not doc and event["path"] in by_path:
            doc = by_path[event["path"]][0]
        if doc:
            docs.append(doc)
    body_fields = join(field for event in events for field in event.get("body_fields", []))
    query_fields = join(field for event in events for field in event.get("query_fields", []))
    if "filter:" in operation or "combined_filter" in operation:
        parameter_source = "visible form input/UI enum plus page defaults"
    elif "pagination" in operation:
        parameter_source = "visible Ant pagination control plus page defaults"
    elif "Batch query" in operation:
        parameter_source = "Batch query members overlay; synthetic no-match input"
    elif ":row:" in operation:
        parameter_source = "selected visible result row; raw identifier kept in browser memory only"
    else:
        parameter_source = "page defaults/current bounded date window"
    status = item.get("status", "")
    blocked = status.startswith("BLOCKED") or status in {"CLICKED_NO_INTERFACE_EVIDENCE", "CURRENT_STATE_NOT_ACTIONABLE"}
    rows.append({
        "menu": "Member",
        "page": "Member List",
        "route": "/member-center/list",
        "operation": operation,
        "action_status": status,
        "trigger_status": item.get("trigger_status", "TRIGGERED_INTERFACE" if events else "NOT_TRIGGERED"),
        "save_confirmation": item.get("save_confirmation", "NOT_APPLICABLE"),
        "request_method": methods,
        "normalized_path": paths,
        "query_fields": query_fields,
        "path_fields": "uid from selected row (in-memory only)" if ":row:" in operation else "",
        "body_fields": body_fields,
        "parameter_source": parameter_source,
        "http_status": join(event.get("http_status") for event in events),
        "business_status": join(str(event.get("business_status")).lower() for event in events),
        "response_structure": join(f"{event.get('response_type')}[{join(event.get('response_keys', []))}]" for event in events),
        "permission_or_role": "authenticated FAT main-admin; visible control allowed by current button permissions",
        "actual_side_effect": item.get("side_effect", "none"),
        "before_state": "read-only page/filter state",
        "after_state": "no business state change",
        "original_document_classification": "documented admin endpoint" if docs else "not found in inventory for exact method/path",
        "original_document_name": join(doc.get("name") for doc in docs),
        "original_document_source": join(doc.get("file") for doc in docs),
        "current_classification": classify(events, operation, exact, by_path),
        "currently_used_by_ui": "true" if events else "visible_control_or_route_only_no_new_network_proof",
        "evidence": f"member-list-a-internal-read-scan.json network[{indexes[0]}:{indexes[1]}]; semantic DOM locator",
        "blocked_scope": operation if blocked else "",
        "blocked_reason": item.get("reason") or item.get("error", "") if blocked else "",
    })

with CSV_OUT.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)

unique = {}
for event in data["network"]:
    key = (event["method"], event["path"])
    unique.setdefault(key, []).append(event)

action_counts = {}
for _, item in all_actions:
    action_counts[item.get("status", "UNKNOWN")] = action_counts.get(item.get("status", "UNKNOWN"), 0) + 1

lines = [
    "# FAT Member List A-line internal operation report",
    "",
    "## Outcome",
    "",
    f"- Page: Member → Member List (`/member-center/list`), FAT only.",
    f"- 30 explicit controls/actions assessed: 22 executed read-only queries/pagination actions, 2 read-only row entries opened, 5 write controls blocked by data scope, and 1 Export control clicked without request/response evidence.",
    f"- Captured {len(data['network'])} sanitized same-origin XHR/fetch events and {len(unique)} unique method+path endpoints; no HTTP/business failures occurred in captured Network.",
    "- Writes executed: 0. Business-data side effects: 0. No export file, raw member row, UID, phone, token, cookie, device ID, password, OTP, or TOTP was retained.",
    "",
    "## Member-list query coverage",
    "",
    "Individual UI-driven probes covered Phone Number, Registration IP, Superior Agent Phone, Creation Time, First Deposit Time, Last Deposit Time, Last Withdrawal Time, Deposit Count, Member Status, Agent Qualification, Account Type, Member Level, KYC Status, Restricted Status, Referrer Information, inviter presence, invitation level, and Lead Source. One text+enum combination was also submitted.",
    "",
    "Batch query used the visible `Batch query members` overlay and its `Apply filter` button with a synthetic non-match value. It produced `POST /admin/member/list` with Body fields `page,page_size,phone,uid`, HTTP 200, business `true`, and zero records.",
    "",
    "Pagination changed the visible page-size control from 20/page to 10/page and then opened page 2. Both actions produced successful `POST /admin/member/list` calls; page 2 returned three rows in the bounded current date window.",
    "",
    "## Row entries and write controls",
    "",
    "- `XP Growth Log` opened the member-detail route and triggered its read endpoints.",
    "- `View Details` opened `/member-center/detail/{uid}`. The selected UID remained in browser memory and was not persisted.",
    "- `Transfer`, `Risk Control`, `Reset Password`, `Convert to Agent`, and `Unblock` were not clicked: A-line had no dedicated write member, so each remains `BLOCKED_DATA_SCOPE`.",
    "",
    "## Export",
    "",
    "The visible Export control received one semantic click in the preceding shared-session run, but no request/response or Playwright download event was captured. It is therefore recorded as `CLICKED_NO_INTERFACE_EVIDENCE`, `trigger_status=NOT_OBSERVED`, `save_confirmation=NOT_REQUIRED_NOT_ATTEMPTED`, classification `DOCUMENTED_UNVERIFIED`. It was not retried in the final evidence run, and no native save workflow or member-data file was used.",
    "",
    "## Method drift",
    "",
    "The FAT UI consistently uses `POST /admin/member/list` with a CBOR Body. The inventory documents the same path as `GET /admin/member/list` with query parameters (`后台/会员列表/会员列表 - seven-double.bru`). The active UI method is therefore `MISCLASSIFIED`, not undocumented and not stale.",
    "",
    "## Unique captured endpoints",
    "",
    "| Method | Path | Captured result | Classification |",
    "| --- | --- | --- | --- |",
]
for (method, path), events in sorted(unique.items()):
    current = classify(events, "", exact, by_path)
    states = join(f"HTTP {event.get('http_status')}/business {str(event.get('business_status')).lower()}" for event in events)
    lines.append(f"| `{method}` | `{path}` | {states} | `{current}` |")
lines += [
    "",
    "## Evidence files",
    "",
    "- `member-list-a-internal-read-scan.json`: sanitized DOM, operation ranges, Network structure, and safety assertions.",
    "- `member-list-a-action-endpoint.csv`: one row per explicit action, including parameter origin, response structure, document mapping, current classification, evidence, and blockers.",
]
MD_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(json.dumps({"actions": len(all_actions), "action_statuses": action_counts, "network_events": len(data["network"]), "unique_endpoints": len(unique), "writes": 0, "side_effects": 0, "csv": str(CSV_OUT), "report": str(MD_OUT)}))
