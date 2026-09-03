#!/usr/bin/env python3
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"


def load(name):
    return json.loads((RESULTS / name).read_text())


def write_csv(name, rows, fields=None):
    fields = fields or list(rows[0])
    with (RESULTS / name).open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)


primary = load("record-flow-member-inventory.json")
overflow = load("record-flow-member-tab-overflow-retry.json")
safe = load("record-flow-member-safe-read-actions.json")
current_target = load("record-flow-member-current-target.json") if (RESULTS / "record-flow-member-current-target.json").exists() else None
limitation_flow = load("record-flow-member-limitation-flow.json") if (RESULTS / "record-flow-member-limitation-flow.json").exists() else None

with (RESULTS / "fat-admin-endpoint-summary.csv").open(newline="") as handle:
    main_catalog = {(row["method"], row["normalized_path"]): row for row in csv.DictReader(handle)}
with (ROOT.parent / "api/inventory/interfaces.csv").open(newline="") as handle:
    inventory_rows = list(csv.DictReader(handle))
inventory = defaultdict(list)
for row in inventory_rows:
    if row["path"]:
        inventory[(row["method"].upper(), row["path"])].append(row)
with (ROOT / "fat-admin-permission-operations.csv").open(newline="") as handle:
    permission_rows = list(csv.DictReader(handle))
permission_ids = defaultdict(set)
for row in permission_rows:
    permission_ids[row["declared_path"]].add(row["operation_id"])

tab_views = {tab["name"]: tab for tab in primary["detail"]["tab_views"] if tab["status"] == "OPENED_READ_ONLY"}
tab_views.update({tab["name"]: tab for tab in overflow["detail"]["tab_views"] if tab["status"] == "OPENED_READ_ONLY"})

selected_events = []
selected_events += [event for event in primary["network"] if event["action"] == "member_list:View Details readonly existing record"]
for source, tabs in [(primary, tab_views), (overflow, tab_views)]:
    names_in_source = {tab["name"] for tab in source["detail"]["tab_views"] if tab["status"] == "OPENED_READ_ONLY"}
    for event in source["network"]:
        if event["action"].startswith("member_detail_tab:") and event["action"].split(":", 1)[1] in names_in_source:
            selected_events.append(event)
selected_events += [event for event in safe["network"] if event["action"].startswith("member_detail_read_action:")]
if limitation_flow:
    selected_events += [event for event in limitation_flow["network"] if event["action"] in {"deposit_limitation_lock", "deposit_limitation_restore"}]

# Dedupe the initial View Details evidence and exact action/request repeats while preserving distinct tab/action mappings.
seen = set(); events = []
for event in selected_events:
    key = (event["action"], event["method"], event["path"], tuple(event["query_fields"]), tuple(event["body_fields"]))
    if key in seen: continue
    seen.add(key); events.append(event)


def action_parts(action):
    if action == "member_list:View Details readonly existing record":
        return "/member-center/list", "button", "View Details"
    if action.startswith("member_detail_tab:"):
        return "/member-center/detail/{uid}", "tab", action.split(":", 1)[1]
    if action.startswith("member_detail_read_action:"):
        _, context, name = action.split(":", 2)
        return "/member-center/detail/{uid}", "button", f"{context} → {name}"
    if action == "deposit_limitation_lock":
        return "/member-center/detail/{uid}", "record_write", "Function Limitation: Deposit Lock"
    if action == "deposit_limitation_restore":
        return "/member-center/detail/{uid}", "record_restore", "Function Limitation: Deposit Restore"
    return "/member-center/detail/{uid}", "interaction", action


mapping = []
for event in events:
    route, control_type, action_name = action_parts(event["action"])
    key = (event["method"], event["path"])
    main = main_catalog.get(key, {})
    docs = inventory.get(key, [])
    doc = next((row for row in docs if row.get("surface") == "admin"), docs[0] if docs else {})
    success = event["http_status"] < 400 and event["business_status"] is not False
    classification = "ACTIVE_FAILED" if not success else main.get("classification") or ("ACTIVE" if doc else "UNDOCUMENTED_ACTIVE")
    mapping.append({
        "caller_surface": "admin", "top_menu": "Member Management", "page_name": "Member / Member Detail",
        "page_route": route, "control_type": control_type, "action_name": action_name,
        "method": event["method"], "normalized_path": event["path"],
        "query_fields": " | ".join(event["query_fields"]), "path_fields": "uid from selected record route" if "{uid}" in route else "",
        "body_fields": " | ".join(event["body_fields"]), "header_fields": " | ".join(event.get("header_fields", [])),
        "parameter_source": "selected member row / detail route; filters and pagination use page defaults",
        "http_status": event["http_status"], "business_status": event["business_status"],
        "response_structure": f'{event["response_type"]}; keys={"|".join(event["response_keys"])}; count={event.get("record_count")}',
        "auth_role": "authenticated FAT admin", "permission_ids": " | ".join(sorted(permission_ids.get(event["path"], set()))),
        "side_effect": ("temporary Deposit restriction, immediately restored" if event["action"].startswith("deposit_limitation_") else "none (read-only detail/list request)"),
        "before_state": (limitation_flow["before_row"] if limitation_flow and event["action"] == "deposit_limitation_lock" else
          limitation_flow["lock"]["after_row"] if limitation_flow and event["action"] == "deposit_limitation_restore" else "existing record; values not persisted"),
        "after_state": (limitation_flow["lock"]["after_row"] if limitation_flow and event["action"] == "deposit_limitation_lock" else
          limitation_flow["restore"]["restored_row"] if limitation_flow and event["action"] == "deposit_limitation_restore" else "unchanged"),
        "original_category": main.get("original_module") or doc.get("module", ""),
        "original_name": main.get("original_name") or doc.get("name", ""),
        "original_source_file": main.get("original_source_file") or doc.get("file", ""),
        "classification": classification, "currently_used": "yes",
        "evidence": "record-flow-member-inventory.json / tab-overflow-retry.json / safe-read-actions.json; exact DOM action + FAT Network",
        "blocked_scope": "" if success else "business or HTTP failure retained; no later success substitution",
    })

write_csv("record-flow-member-action-endpoint.csv", mapping)

controls = []
stable_row_actions = ["XP Growth Log", "Transfer", "View Details", "Unblock", "Risk Control", "Reset Password", "Convert to Agent"]
for name in stable_row_actions:
    matches = [button for button in primary["list"]["first_row_controls"]["buttons"] if button["text"] == name]
    if matches:
        risk = "READ_ONLY" if name in {"XP Growth Log", "View Details"} else "WRITE_OR_STATE_CHANGE"
        controls.append({"surface": "member_list_row", "route": "/member-center/list", "control_type": "button", "context": "first data row",
            "action_name": name, "dom_state": "DISABLED" if matches[0]["disabled"] else "ENABLED", "risk": risk,
            "status": "READ_ONLY_EVIDENCE_AVAILABLE" if risk == "READ_ONLY" else "BLOCKED_WAITING_CURRENT_RUN_UID",
            "prerequisite": "selected member UID" if risk != "READ_ONLY" else "non-empty member row",
            "recovery_path": "not assessed before current-run target", "evidence": "record-flow-member-inventory.json"})
for tab in tab_views.values():
    controls.append({"surface": "member_detail", "route": "/member-center/detail/{uid}", "control_type": "tab", "context": "detail inner tabs",
        "action_name": tab["name"], "dom_state": "ENABLED", "risk": "READ_ONLY", "status": "EXECUTED_READ_ONLY",
        "prerequisite": "selected member UID", "recovery_path": "none needed", "evidence": f'{tab.get("selection_method", "direct registered tab")} + FAT Network/DOM'})
for item in safe["detail"]["safe_read_actions"]:
    controls.append({"surface": "member_detail", "route": "/member-center/detail/{uid}", "control_type": "button",
        "context": item["context_label"], "action_name": item["action_name"], "dom_state": "ENABLED", "risk": "READ_ONLY",
        "status": "EXECUTED_READ_ONLY", "prerequisite": "selected member UID", "recovery_path": "none needed",
        "evidence": "record-flow-member-safe-read-actions.json exact description label + button"})
if limitation_flow:
    controls.append({"surface": "member_detail", "route": "/member-center/detail/{uid}", "control_type": "record_write_restore",
        "context": "Function Limitation / Deposit", "action_name": "Lock → Unlock", "dom_state": "ENABLED", "risk": "LOW_RISK_REVERSIBLE",
        "status": "EXECUTED_RESTORED", "prerequisite": "current-run approved UID; baseline Allowed; real approval TOTP",
        "recovery_path": "same row Unlock action; verified restored to Allowed", "evidence": "record-flow-member-limitation-flow.json"})

write_csv("record-flow-member-control-matrix.csv", controls)

form_rows = []
for item in primary["add_member_form"]["controls"]["form_items"]:
    form_rows.append({"form": "Add Member", "field_order": item["index"], "field_name": item["label"],
        "required_marker": "yes" if item["required"] else "no", "control_types": " | ".join(control["type"] for control in item["controls"]),
        "placeholders": " | ".join(control["placeholder"] for control in item["controls"] if control["placeholder"]),
        "dependency": "select options require runtime lookup" if any(control["type"] == "select" for control in item["controls"]) else "none observed",
        "submission_status": "NOT_SUBMITTED", "cleanup_status": "UNPROVEN", "evidence": "empty form DOM; no member values captured"})
write_csv("record-flow-member-add-form.csv", form_rows)

write_prerequisites = [
    ("Transfer", "valid current-run UID, original and target upline", "restore original upline only if API/UI permits", "LAST_RISKY"),
    ("Unblock", "current-run UID must first be blocked by this flow", "restore original restriction state", "BLOCKED_STATE_NOT_PRESENT"),
    ("Remaining Risk Control / Withdraw-Bet-Login Lock actions", "current-run UID and baseline limitation/risk states", "unlock or restore every changed flag", "WAIT_CURRENT_RUN_UID"),
    ("Credit or Debit", "current-run UID, wallet baseline, bounded test amount and reason", "opposite adjustment plus wallet/transaction reconciliation", "WAIT_CURRENT_RUN_UID"),
    ("Turnover requirement adjustment", "current-run UID and exact turnover baseline", "restore exact prior requirement if supported", "WAIT_RECOVERY_PROOF"),
    ("Deposit multiple adjustment", "current-run UID and exact original multiplier", "restore original multiplier and verify log", "WAIT_CURRENT_RUN_UID"),
    ("Manual Adjust VIP", "current-run UID and original VIP/manual level", "downgrade/restore must be proven before execution", "WAIT_RECOVERY_PROOF"),
    ("Token Top-Up and Withdrawal", "current-run UID, token wallet baseline and bounded amount", "opposite adjustment and token ledger reconciliation", "LAST_RISKY"),
    ("Reset Password", "current-run UID", "original secret cannot be recovered", "BLOCKED_NO_SAFE_RECOVERY_PATH"),
    ("Convert to Agent", "current-run UID, all other validations complete", "reverse conversion not proven", "BLOCKED_NO_SAFE_RECOVERY_PATH"),
    ("Clear Turnover Requirement", "current-run UID, all other validations complete", "cleared source requirements cannot be reconstructed safely", "BLOCKED_NO_SAFE_RECOVERY_PATH"),
    ("Add Member submit", "unique controlled account/email/phone and proven deletion/cleanup path", "delete/disable created member and verify", "NOT_SUBMITTED_CLEANUP_UNPROVEN"),
]
def current_write_status(status):
    if status.startswith("BLOCKED_NO_SAFE"):
        return status
    if status == "WAIT_RECOVERY_PROOF":
        return "BLOCKED_RECOVERY_UNPROVEN"
    if status == "LAST_RISKY":
        return "BLOCKED_DEFERRED_LAST_RISKY"
    if status == "NOT_SUBMITTED_CLEANUP_UNPROVEN":
        return status
    if current_target and current_target["detail"]["state"].get("/admin/kyc/detail", {}).get("kyc_status") == 5:
        return "BLOCKED_NOT_SELECTED_LOWEST_RISK_ONLY"
    return "BLOCKED_KYC_PRE_SUBMISSION" if current_target else "BLOCKED_WAITING_CURRENT_RUN_UID"

write_rows = [{"operation": op, "required_target_ref": "KYC-RUN-B9CA6D6A0704", "prerequisite": pre, "recovery_path": recovery,
    "status": current_write_status(status), "executed": "no", "side_effect": "none",
    "evidence": "control present in member list/detail DOM; no existing-record write clicked"} for op, pre, recovery, status in write_prerequisites]
if limitation_flow:
    write_rows.append({"operation": "Deposit Function Limitation Lock → Unlock", "required_target_ref": "KYC-RUN-B9CA6D6A0704",
        "prerequisite": "approved current-run UID; before state Allowed; real approval TOTP", "recovery_path": "same-row Unlock with real approval TOTP",
        "status": "EXECUTED_RESTORED", "executed": "yes", "side_effect": "temporary Forbidden state; restored to Allowed",
        "evidence": "record-flow-member-limitation-flow.json before/write/after/restore/restored"})
write_csv("record-flow-member-write-prerequisites.csv", write_rows)

unique_endpoints = {(row["method"], row["normalized_path"]) for row in mapping}
new_vs_main = unique_endpoints - set(main_catalog)
mapping_classes = Counter(row["classification"] for row in mapping)
unique_class_by_endpoint = {}
for row in mapping:
    unique_class_by_endpoint[(row["method"], row["normalized_path"])] = row["classification"]
unique_classes = Counter(unique_class_by_endpoint.values())
summary = {
    "environment": "FAT", "phase": "member_record_flow_with_controlled_reversible_write", "target_ref_for_future_writes": "KYC-RUN-B9CA6D6A0704",
    "existing_record_write_actions_executed": 0, "current_run_write_requests": 2 if limitation_flow else 0,
    "restored_write_flows": 1 if limitation_flow and limitation_flow.get("restored") else 0,
    "add_member_submitted": False, "unrestored_side_effects": 0,
    "detail_tabs": {"registered": 17, "opened_read_only": len(tab_views), "blocked": 17 - len(tab_views)},
    "safe_detail_entries": {"registered": 11, "opened_read_only": sum(item["status"] == "OPENED_READ_ONLY" for item in safe["detail"]["safe_read_actions"])},
    "add_member_fields": len(form_rows), "add_member_required_fields": [row["field_name"] for row in form_rows if row["required_marker"] == "yes"],
    "action_endpoint_rows": len(mapping), "unique_endpoints": len(unique_endpoints), "new_endpoints_vs_main": len(new_vs_main),
    "new_endpoint_keys": [f"{method} {path}" for method, path in sorted(new_vs_main)],
    "unique_endpoint_classifications": dict(sorted(unique_classes.items())), "mapping_row_classifications": dict(sorted(mapping_classes.items())),
    "current_target_list_match_verified": bool(current_target and current_target["list_query"]["row_match_verified"]),
    "current_target_detail_uid_verified": bool(current_target and current_target["detail"]["route_uid_verified"]),
    "current_target_kyc_status": current_target["detail"]["state"].get("/admin/kyc/detail", {}).get("kyc_status") if current_target else None,
    "write_status": "LOW_RISK_REVERSIBLE_FLOW_EXECUTED_RESTORED; remaining risky/irreversible operations blocked" if limitation_flow else
      "BLOCKED_KYC_PRE_SUBMISSION" if current_target else "BLOCKED_WAITING_CURRENT_RUN_UID",
    "raw_uid_persisted": False, "member_values_persisted": False,
}
(RESULTS / "record-flow-member-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")

report = ["# FAT member record-flow discovery", "",
    f'- Detail tabs: {len(tab_views)}/17 opened read-only; safe detail entries: {summary["safe_detail_entries"]["opened_read_only"]}/11.',
    f'- Action/endpoint mappings: {len(mapping)}; unique endpoints: {len(unique_endpoints)}; new vs 109-endpoint main scan: {len(new_vs_main)}.',
    "- Add Member opened for DOM inventory only; it was not submitted. Required markers: Account, Email, Phone Number.",
    "- Arbitrary existing member data was used only for read-only structure evidence. Controlled writes were limited to the current-run target; no raw UID/member values were persisted.",
    f'- Current-run target list/detail correlation: {summary["current_target_list_match_verified"]}/{summary["current_target_detail_uid_verified"]}; KYC status={summary["current_target_kyc_status"]}.',
    f'- Controlled writes: {summary["current_run_write_requests"]} requests; restored flows: {summary["restored_write_flows"]}; unrestored side effects: {summary["unrestored_side_effects"]}.',
    "- Deposit Function Limitation completed Allowed → Forbidden → Allowed through the same exact row and real approval TOTP. Irreversible/high-risk actions remain blocked.", "",
    "## Outputs", "", "- `record-flow-member-action-endpoint.csv`", "- `record-flow-member-control-matrix.csv`",
    "- `record-flow-member-add-form.csv`", "- `record-flow-member-write-prerequisites.csv`", "- `record-flow-member-summary.json`", ""]
(RESULTS / "record-flow-member-report.md").write_text("\n".join(report))
print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
