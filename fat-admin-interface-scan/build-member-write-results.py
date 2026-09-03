#!/usr/bin/env python3
"""Build sanitized, independent FAT member/KYC write-discovery assets."""

import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "fat-admin-interface-scan/results"


def load(name):
    return json.loads((RESULTS / name).read_text(encoding="utf-8"))


with (ROOT / "api/inventory/interfaces.csv").open(encoding="utf-8-sig", newline="") as handle:
    documented = {(row["method"].upper(), row["path"]): row for row in csv.DictReader(handle) if row.get("path")}


fields = [
    "surface", "top_menu", "page_name", "page_route", "control_type", "action_name",
    "method", "normalized_path", "request_fields", "parameter_source", "http_status",
    "business_status", "response_structure", "auth_role", "side_effect", "before_state",
    "after_state", "original_category", "original_name", "original_source_file",
    "classification", "currently_used_by_ui", "target_ref", "evidence", "blocked_scope",
]
rows = []


def add(*, surface="admin", top_menu="Member Management", page_name="Member", page_route="/member-center/list",
        control_type="button", action_name, method="", path="", request_fields="", parameter_source="",
        http_status="", business_status="", response_structure="", auth_role="authenticated FAT admin",
        side_effect="none", before_state="", after_state="", classification=None,
        currently_used="YES", target_ref="", evidence="", blocked_scope=""):
    doc = documented.get((method, path)) if method and path else None
    if classification is None:
        success = str(http_status) == "200" and str(business_status).lower() == "true"
        classification = ("ACTIVE" if doc else "UNDOCUMENTED_ACTIVE") if success else "ACTIVE_FAILED"
    rows.append({
        "surface": surface, "top_menu": top_menu, "page_name": page_name, "page_route": page_route,
        "control_type": control_type, "action_name": action_name, "method": method,
        "normalized_path": path, "request_fields": request_fields, "parameter_source": parameter_source,
        "http_status": http_status, "business_status": business_status,
        "response_structure": response_structure, "auth_role": auth_role, "side_effect": side_effect,
        "before_state": before_state, "after_state": after_state,
        "original_category": f'{doc.get("surface", "")}/{doc.get("module", "")}' if doc else "",
        "original_name": doc.get("name", "") if doc else "",
        "original_source_file": doc.get("file", "") if doc else "",
        "classification": classification, "currently_used_by_ui": currently_used,
        "target_ref": target_ref, "evidence": evidence, "blocked_scope": blocked_scope,
    })


for label, filename in [
    ("Bet", "record-flow-member-limitation-bet-flow.json"),
    ("Login", "record-flow-member-limitation-login-flow.json"),
]:
    flow = load(filename)
    for phase, action in [("lock", "Lock"), ("restore", "Unlock / Restore")]:
        event = next(item for item in flow[phase]["events"] if item["method"] == "POST")
        add(page_name="Member Detail", page_route="/member-center/detail/{uid}", control_type="record_write",
            action_name=f"Function Limitation: {label} {action}", method=event["method"], path=event["path"],
            request_fields=" | ".join(event["body_fields"]), parameter_source="selected current-run UID; row state; controlled note; approval TOTP",
            http_status=event["http_status"], business_status=event["business_status"], response_structure="data:null",
            auth_role="authenticated FAT admin with member limitation permission; approval TOTP",
            side_effect=f"temporary {label} restriction" if phase == "lock" else f"restored {label} restriction baseline",
            before_state=flow["before_row"] if phase == "lock" else flow["lock"]["after_row"],
            after_state=flow["lock"]["after_row"] if phase == "lock" else flow["restore"]["restored_row"],
            target_ref=flow["target_ref"], evidence=filename)

withdraw = load("record-flow-member-limitation-withdraw-flow.json")
add(page_name="Member Detail", page_route="/member-center/detail/{uid}", control_type="record_state",
    action_name="Function Limitation: Withdraw", classification="DOCUMENTED_UNVERIFIED", currently_used="UI_CONTROL_PRESENT",
    target_ref=withdraw["target_ref"], before_state=withdraw["before_row"], after_state=withdraw["before_row"],
    evidence="record-flow-member-limitation-withdraw-flow.json",
    blocked_scope="Current-run member baseline was already Forbidden; no honest Allowed→Forbidden transition available")

risk = load("record-flow-member-risk-control-flow.json")
for phase, name, before, after, effect in [
    ("block", "Risk Control", "status=0; Risk Control visible", "status=1; Unrisk Control visible", "member placed under risk control"),
    ("restore", "Unrisk Control", "status=1; Unrisk Control visible", "status=0; Risk Control visible", "risk control removed; baseline restored"),
]:
    event = risk[phase]["write"]
    add(action_name=name, method=event["method"], path=event["path"], request_fields=" | ".join(event["body_fields"]),
        parameter_source="selected current-run UID; controlled reason; status chosen by row action; approval TOTP",
        http_status=event["http_status"], business_status=event["business_status"], response_structure="data:null",
        auth_role="authenticated FAT admin with member update permission; approval TOTP", side_effect=effect,
        before_state=before, after_state=after, target_ref=risk["target_ref"], evidence="record-flow-member-risk-control-flow.json")

convert = load("record-flow-member-convert-agent.json")
event = convert["submitted"]
add(action_name="Convert to Agent", method=event["method"], path=event["path"], request_fields=" | ".join(event["body_fields"]),
    parameter_source="selected current-run UID; fixed Weekly Settlement; account type; approval TOTP",
    http_status=event["http_status"], business_status=event["business_status"], response_structure="data:null",
    auth_role="authenticated FAT admin with agent-conversion permission; approval TOTP",
    side_effect="terminal test member converted to agent", before_state="is_agent=false", after_state="is_agent=true (GET /admin/member/detail)",
    target_ref=convert["target_ref"], evidence="record-flow-member-convert-agent.json")

for action, filename, reason in [
    ("Reset Password", "record-flow-member-terminal-reset-password-probe.json", "Requires member notification method and member-side verification code; no legal code captured"),
    ("Transfer", "record-flow-member-terminal-transfer-probe.json", "Form mapped; submission deferred until a valid current-run inviter relationship is proven"),
]:
    probe = load(filename)
    labels = [item["label"] for item in (probe.get("form") or {}).get("fields", []) if item.get("label")]
    add(action_name=action, request_fields=" | ".join(labels), parameter_source="live form controls",
        classification="DOCUMENTED_UNVERIFIED", currently_used="UI_CONTROL_PRESENT", target_ref=probe["target_ref"],
        evidence=filename, blocked_scope=reason)

rate_controls = load("record-flow-member-recharge-rate-controls.json")
rate_log = next(item for item in rate_controls["network"] if item["path"] == "/admin/member/deposit/multiple/log")
add(page_name="Member Detail", page_route="/member-center/detail/{uid}", control_type="button",
    action_name="General recharge rate → operating record", method=rate_log["method"], path=rate_log["path"],
    request_fields=" | ".join(rate_log["query_fields"]),
    parameter_source="uid from current member detail; page/page_size from operation-record modal defaults",
    http_status=rate_log["http_status"], business_status=rate_log["business_status"],
    response_structure="list; count=0; columns=change time|type|before|after|remarks|executor",
    auth_role="authenticated FAT admin with member recharge-rate log permission (permission 10016)",
    side_effect="none; operation history read only", before_state="modal closed", after_state="empty operation-history table rendered",
    target_ref=rate_controls["target_ref"], evidence="record-flow-member-recharge-rate-controls.json",
    blocked_scope="Runtime UI omitted documented operator_types query parameter; request still succeeded")

rate_write = load("record-flow-member-recharge-rate-write-flow.json")
rate_update = next(item for item in rate_write["network"] if item["path"] == "/admin/member/deposit/multiple/update")
baseline = rate_write["before"]
restored = rate_write["after_restore"]
add(page_name="Member Detail", page_route="/member-center/detail/{uid}", control_type="record_write",
    action_name="General recharge rate → Custom / Platform Configuration", method=rate_update["method"], path=rate_update["path"],
    request_fields=" | ".join(rate_update["body_fields"]),
    parameter_source="uid from current member detail; explicit rate-mode selection; bounded one-decimal rate when Custom; controlled remark; runtime approval TOTP",
    http_status=rate_update["http_status"], business_status=rate_update["business_status"],
    response_structure="object; top-level keys=data|status; status=true",
    auth_role="authenticated FAT admin with member recharge-rate update permission (permission 10015); approval TOTP",
    side_effect="current-run Custom 1.0 state restored to original Platform Configuration 1.5",
    before_state=f'deposit_multiple={baseline["deposit_multiple"]}; deposit_multiple_type={baseline["deposit_multiple_type"]}; platform_deposit_multiple={baseline["platform_deposit_multiple"]}',
    after_state=f'deposit_multiple={restored["deposit_multiple"]}; deposit_multiple_type={restored["deposit_multiple_type"]}; platform_deposit_multiple={restored["platform_deposit_multiple"]}',
    target_ref=rate_write["target_ref"], evidence="record-flow-member-recharge-rate-write-flow.json",
    blocked_scope="Earlier status=false probes used the FAT login fixed code as a business approval code and are invalidated; runtime TOTP restore succeeded")

tree = load("record-flow-member-turnover-game-tree.json")
for path in ["/admin/gameclass/list", "/admin/game/search"]:
    event = next(item for item in tree["network"] if item["action"] == "open_turnover_adjustment" and item["path"] == path)
    profile = tree["response_profiles"][path]
    add(page_name="Member Detail", page_route="/member-center/detail/{uid}", control_type="tree_data_load",
        action_name="流水要求调整 → open game restriction tree", method=event["method"], path=path,
        request_fields=" | ".join(event["body_fields"]), parameter_source="opening the current member turnover-adjustment modal",
        http_status=event["http_status"], business_status=event["business_status"],
        response_structure=f'{profile["type"]}; count={profile.get("count", "")}; item_keys={"|".join(profile.get("item_keys", []))}',
        auth_role="authenticated FAT admin with turnover-adjustment visibility", side_effect="none; tree data loaded only",
        before_state="tree closed", after_state="7 categories / 72 category-provider pairs / 5731 games available",
        target_ref=tree["target_ref"], evidence="record-flow-member-turnover-game-tree.json")

for action, filename, reason in [
    ("changed / 转移代理线", "record-flow-member-reversible-detail-changed-probe.json", "Requires a proven current-run new referrer ID and relationship recovery strategy"),
]:
    probe = load(filename)
    labels = [item["label"] for item in (probe.get("form") or {}).get("fields", []) if item.get("label")]
    add(page_name="Member Detail", page_route="/member-center/detail/{uid}", action_name=action,
        request_fields=" | ".join(labels), parameter_source="live state-dependent form controls",
        classification="DOCUMENTED_UNVERIFIED", currently_used="UI_CONTROL_PRESENT", target_ref=probe["target_ref"],
        evidence=filename, blocked_scope=reason)


def import_independent_csv(filename, vip_format=False):
    with (RESULTS / filename).open(encoding="utf-8", newline="") as handle:
        for item in csv.DictReader(handle):
            path_key = "standardized_path" if vip_format else "path"
            action_key = "action_name" if vip_format else "action"
            class_key = "current_classification" if vip_format else "classification"
            used_key = "current_use" if vip_format else "currently_used"
            before_key = "before_state"
            after_key = "after_state"
            side_key = "actual_side_effect" if vip_format else "side_effect"
            blocker_key = "blocker_or_note" if vip_format else "exception_or_blocker"
            page_key = "page" if not vip_format else "page"
            add(
                page_name=item[page_key], page_route=item.get("page_route") or item.get("route", ""),
                control_type=item["control_type"], action_name=item[action_key], method=item["method"],
                path=item[path_key], request_fields=" | ".join(filter(None, [item.get("query_fields", ""), item.get("body_fields", "")])),
                parameter_source=item.get("parameter_source") or item.get("parameter_sources", ""),
                http_status=item["http_status"], business_status=item["business_status"],
                response_structure=item["response_structure"], auth_role=item["auth_role"],
                side_effect=item[side_key], before_state=item[before_key], after_state=item[after_key],
                classification=item[class_key], currently_used=item[used_key].upper(),
                target_ref="FAT-MEMBER-REV-01" if vip_format else "FAT-KYC-REJECT-01",
                evidence=item["evidence"], blocked_scope=item[blocker_key],
            )


import_independent_csv("record-flow-member-fund-pair-action-endpoint.csv")
import_independent_csv("record-flow-member-reversible-vip-turnover-action-endpoint.csv", vip_format=True)

reject = load("record-flow-kyc-reject-admin.json")
event = next(item for item in reject["network"] if item["path"] == "/admin/kyc/reject")
add(top_menu="KYC", page_name="KYC", page_route="/kyc", action_name="Review → Reject Application → OK",
    method=event["method"], path=event["path"], request_fields=" | ".join(event["body_fields"]),
    parameter_source="exact current-run pending UID; Reject Application selection; controlled remarks",
    http_status=event["http_status"], business_status=event["business_status"], response_structure="data:null",
    auth_role="authenticated FAT admin with KYC review permission", side_effect="KYC rejected",
    before_state="kyc_status=2", after_state="kyc_status=3", target_ref=reject["target_ref"],
    evidence="record-flow-kyc-reject-admin.json + sanitized member lane state")

approve = load("record-flow-kyc-resubmit-approve-admin.json")
event = next(item for item in approve["network"] if item["path"] == "/admin/kyc/approve")
add(top_menu="KYC", page_name="KYC", page_route="/kyc", action_name="Review → Approve Application → OK",
    method=event["method"], path=event["path"], request_fields=" | ".join(event["body_fields"]),
    parameter_source="exact current-run re-submitted UID; Approve Application selection; controlled remarks",
    http_status=event["http_status"], business_status=event["business_status"], response_structure="data:null",
    auth_role="authenticated FAT admin with KYC review permission", side_effect="KYC approved",
    before_state="kyc_status=2 after re-submit", after_state="kyc_status=5", target_ref=approve["target_ref"],
    evidence="record-flow-kyc-resubmit-approve-admin.json + sanitized member lane state")

resubmit = load("record-flow-kyc-reject-client-resubmit.json")
for event in [item for item in resubmit["network"] if item["action"] == "submit this-run KYC record" and item["method"] == "POST"]:
    add(surface="client", top_menu="Account", page_name="KYC", page_route="/s-kyc-v2", action_name="Re-KYC verification → Submit",
        method=event["method"], path=event["path"], request_fields=" | ".join(event["body_fields"]),
        parameter_source="rejected current-run member; controlled KYC form and test images",
        http_status=event["http_status"], business_status=event["business_status"],
        response_structure=f'data:{event["response_shape"].get("data_type", "unknown")}',
        auth_role="authenticated FAT member", side_effect="test attachment uploaded" if event["path"].endswith("upload") else "KYC re-submitted",
        before_state="kyc_status=3", after_state="kyc_status=2" if event["path"].endswith("insert") else "attachment ID returned to form runtime",
        classification="MISCLASSIFIED" if documented.get((event["method"], event["path"]), {}).get("surface") not in {None, "client"} else None,
        target_ref=resubmit["target_ref"], evidence="record-flow-kyc-reject-client-resubmit.json")

with (RESULTS / "record-flow-member-write-action-endpoint.csv").open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=fields)
    writer.writeheader(); writer.writerows(rows)

summary = {
    "environment": "FAT", "data_scope": "THIS_RUN_CREATED_ONLY", "rows": len(rows),
    "unique_live_endpoints": len({(row["method"], row["normalized_path"]) for row in rows if row["method"] and row["currently_used_by_ui"].upper() == "YES"}),
    "classifications": dict(Counter(row["classification"] for row in rows)),
    "restored_flows": ["Bet limitation", "Login limitation", "Risk Control", "Wallet Credit/Debit", "VIP manual level", "Member recharge rate", "Turnover requirement +1/-1"],
    "terminal_flows": ["Convert to Agent"],
    "kyc_transition": "0 → 2 → 3 → 2 → 5",
    "unrestored_accidental_side_effects": 0,
    "pending_intentional_state": "FAT-KYC-REJECT-01 is approved (kyc_status=5); token-list branch returned business status=false with no state change; turnover add/sub restored FAT-MEMBER-REV-01 to left_turnover_count=0",
    "raw_phone_uid_or_otp_persisted": False,
}
(RESULTS / "record-flow-member-write-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False))
