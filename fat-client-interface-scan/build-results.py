#!/usr/bin/env python3
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN = ROOT / "fat-client-interface-scan"
RESULTS = SCAN / "results"
BUSINESS_PATH = re.compile(r"^/(?:member|finance|promo|game|wallet|withdraw|deposit|bonus|activity|kyc|bank|pay|order|record|report|balance|transaction|bet)(?:/|$)", re.I)


def inventory_rows():
    with (ROOT / "api/inventory/interfaces.csv").open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def compact_shape(shape):
    return json.dumps(shape, ensure_ascii=False, separators=(",", ":")) if shape is not None else ""


def write_csv(path, fields, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    raw = json.loads((RESULTS / "fat-client-network.json").read_text())
    progress = json.loads((RESULTS / "fat-client-page-progress.json").read_text())
    inventory = inventory_rows()
    by_key = defaultdict(list)
    for item in inventory:
        by_key[(item.get("method", "").upper(), item.get("path", ""))].append(item)

    groups = defaultdict(list)
    for record in raw["records"]:
        first_party = record["origin"].endswith("filbet2025.com")
        third_party = not first_party
        if first_party and not BUSINESS_PATH.match(record["path"]):
            continue
        if third_party and record["path"].endswith((".wasm", ".json", ".otf")):
            continue
        key = (
            record["actionId"], record["menu"], record["page"], record["pageRoute"],
            record["controlType"], record["action"], record["method"], record["origin"],
            record["normalizedPath"],
        )
        record = {**record, "thirdParty": third_party}
        groups[key].append(record)

    rows = []
    class_counts = Counter()
    observed_doc_keys = set()
    for key, records in groups.items():
        action_id, menu, page, route, control_type, action, method, origin, normalized_path = key
        actual_paths = sorted({item["path"] for item in records})
        docs = []
        for actual in actual_paths:
            docs.extend(by_key.get((method.upper(), actual), []))
        docs = list({(d["file"], d["name"]): d for d in docs}.values())
        if docs:
            observed_doc_keys.update((method.upper(), d["path"]) for d in docs)
        statuses = sorted({item["httpStatus"] for item in records if item["httpStatus"]})
        business = sorted({item["businessStatus"] for item in records if item["businessStatus"] != "UNAVAILABLE"})
        failed = any(item["httpStatus"] >= 400 or item["businessStatus"] == "false" or item["error"] for item in records)
        if records[0]["thirdParty"]:
            classification = "THIRD_PARTY"
        elif failed:
            classification = "ACTIVE_FAILED"
        elif not docs:
            classification = "UNDOCUMENTED_ACTIVE"
        elif docs and not any(d.get("surface") == "client" for d in docs):
            classification = "MISCLASSIFIED"
        else:
            classification = "ACTIVE"
        class_counts[classification] += 1
        auth = "authenticated client session (t header)" if any(r["authRequired"] for r in records) else "guest or no auth header observed"
        shapes = []
        for item in records:
            shape = compact_shape(item["responseShape"])
            if shape and shape not in shapes:
                shapes.append(shape)
        potential_claim = normalized_path == "/promo/task/daily/claim"
        login_session = normalized_path == "/member/v2/login"
        rows.append({
            "surface": "client",
            "menu": menu,
            "page": page,
            "page_route": route,
            "control_type": control_type,
            "action": action,
            "method": method,
            "origin": origin,
            "normalized_path": normalized_path,
            "query_fields": "|".join(sorted({v for r in records for v in r["queryFields"]})),
            "body_fields": "|".join(sorted({v for r in records for v in r["bodyFields"]})),
            "parameter_sources": ";".join(sorted({v for r in records for v in r["parameterSources"]})),
            "http_status": "|".join(map(str, statuses)),
            "business_status": "|".join(business) or "UNAVAILABLE",
            "response_shape": " | ".join(shapes[:4]),
            "auth_role": auth,
            "actual_side_effect": "POTENTIAL_REWARD_CLAIM: endpoint returned business success after clicking Go; durable change not verified" if potential_claim else ("authenticated browser session established" if login_session else ("none observed" if method in ("GET", "HEAD", "OPTIONS") else "request emitted; no durable business change observed by this discovery action")),
            "before_after_change": "before_state=unavailable; after_state=HTTP 200/business true and page remained /s-points-v2; no closure claimed" if potential_claim else ("before=guest login form; after=authenticated home" if login_session else ("not applicable/read-only" if method in ("GET", "HEAD", "OPTIONS") else "no state identifier returned or persisted in sanitized evidence")),
            "document_category": "|".join(sorted({f"{d['surface']}/{d['module']}" for d in docs})),
            "document_name": "|".join(sorted({d["name"] for d in docs})),
            "document_source": "|".join(sorted({d["file"] for d in docs})),
            "classification": classification,
            "currently_used": "yes",
            "evidence": f"fat-client-network.json action={action_id}; records=" + "|".join(map(str, sorted({r["id"] for r in records}))),
            "exception_blocked_scope": "business status false" if failed else "",
            "request_count": len(records),
        })

    rows.sort(key=lambda row: (row["menu"], row["page"], row["action"], row["method"], row["origin"], row["normalized_path"]))
    fields = list(rows[0]) if rows else []
    write_csv(RESULTS / "fat-client-page-action-interface.csv", fields, rows)

    progress_rows = []
    for item in progress["pages"]:
        potential_claim_action = item["status"] == "COMPLETED" and item["page"] == "Earn Filcoins" and item["action"] == "daily task Go 9"
        progress_rows.append({
            "menu": item["menu"], "page": item["page"], "page_route": item["route"],
            "action": item["action"], "control_type": item["controlType"], "status": "COMPLETED_WITH_POTENTIAL_SIDE_EFFECT" if potential_claim_action else item["status"],
            "final_url": item["url"], "request_count": item["requestCount"], "error_or_blocker": item["error"],
            "evidence": f"fat-client-page-progress.json action={item['id']}",
        })
    write_csv(RESULTS / "fat-client-page-progress.csv", list(progress_rows[0]), progress_rows)

    endpoint_groups = defaultdict(list)
    for row in rows:
        endpoint_groups[(row["method"], row["origin"], row["normalized_path"])].append(row)
    endpoint_rows = []
    endpoint_priority = {"ACTIVE_FAILED": 5, "MISCLASSIFIED": 4, "UNDOCUMENTED_ACTIVE": 3, "ACTIVE": 2, "THIRD_PARTY": 1}
    for (method, origin, normalized_path), linked in sorted(endpoint_groups.items()):
        classification = max((row["classification"] for row in linked), key=lambda value: endpoint_priority[value])
        endpoint_rows.append({
            "method": method, "origin": origin, "normalized_path": normalized_path,
            "classification": classification,
            "pages": "|".join(sorted({row["page"] for row in linked})),
            "actions": "|".join(sorted({row["action"] for row in linked})),
            "http_status": "|".join(sorted({value for row in linked for value in row["http_status"].split("|") if value})),
            "business_status": "|".join(sorted({value for row in linked for value in row["business_status"].split("|") if value})),
            "auth_role": "|".join(sorted({row["auth_role"] for row in linked})),
            "actual_side_effect": "|".join(sorted({row["actual_side_effect"] for row in linked})),
            "document_category": "|".join(sorted({value for row in linked for value in row["document_category"].split("|") if value})),
            "document_name": "|".join(sorted({value for row in linked for value in row["document_name"].split("|") if value})),
            "request_count": sum(int(row["request_count"]) for row in linked),
        })
    write_csv(RESULTS / "fat-client-endpoint-summary.csv", list(endpoint_rows[0]), endpoint_rows)

    business_records = [r for r in raw["records"] if r["origin"].endswith("filbet2025.com") and BUSINESS_PATH.match(r["path"])]
    unique_internal = {(r["method"], r["normalizedPath"]) for r in business_records}
    unique_endpoint_classes = {}
    for row in rows:
        endpoint_key = (row["method"], row["origin"], row["normalized_path"])
        current = unique_endpoint_classes.get(endpoint_key)
        priority = {"ACTIVE_FAILED": 5, "MISCLASSIFIED": 4, "UNDOCUMENTED_ACTIVE": 3, "ACTIVE": 2, "THIRD_PARTY": 1}
        if current is None or priority[row["classification"]] > priority[current]:
            unique_endpoint_classes[endpoint_key] = row["classification"]

    comparison_rows = []
    inventory_endpoint_rows = defaultdict(list)
    for item in inventory:
        if item.get("surface") == "client" and item.get("method") and item.get("path"):
            inventory_endpoint_rows[(item["method"].upper(), item["path"])].append(item)
    observed_by_doc_key = defaultdict(list)
    for row in rows:
        if row["classification"] != "THIRD_PARTY":
            observed_by_doc_key[(row["method"].upper(), row["normalized_path"])].append(row)
    for endpoint_key, docs in sorted(inventory_endpoint_rows.items()):
        observed = observed_by_doc_key.get(endpoint_key, [])
        status = "DOCUMENTED_UNVERIFIED"
        if observed:
            status = "ACTIVE_FAILED" if any(r["classification"] == "ACTIVE_FAILED" for r in observed) else "ACTIVE"
        comparison_rows.append({
            "method": endpoint_key[0], "path": endpoint_key[1],
            "document_name": "|".join(sorted({d["name"] for d in docs})),
            "document_category": "|".join(sorted({f"{d['surface']}/{d['module']}" for d in docs})),
            "document_source": "|".join(sorted({d["file"] for d in docs})),
            "classification": status,
            "ui_evidence": "|".join(sorted({r["evidence"] for r in observed})),
            "reason": "observed in FAT UI Network" if observed else "not observed in the current UI interaction coverage; reachability and staleness not yet proven",
        })
    write_csv(RESULTS / "fat-client-inventory-comparison.csv", list(comparison_rows[0]), comparison_rows)

    summary = {
        "scannedAt": raw["scannedAt"], "environment": "FAT",
        "pages": len({p["page"] for p in progress["pages"]}),
        "actions": len(progress["pages"]),
        "completedActions": sum(p["status"] == "COMPLETED" for p in progress["pages"]),
        "failedActions": sum(p["status"] == "FAILED" for p in progress["pages"]),
        "blockedActions": sum(p["status"].startswith("BLOCKED") for p in progress["pages"]),
        "failedOrBlockedActions": sum(p["status"] != "COMPLETED" for p in progress["pages"]),
        "potentialSideEffectActions": sum(p["page"] == "Earn Filcoins" and p["action"] == "daily task Go 9" for p in progress["pages"]),
        "rawXhrFetchRequests": len(raw["records"]),
        "firstPartyBusinessRequests": len(business_records),
        "uniqueFirstPartyBusinessEndpoints": len(unique_internal),
        "mappingRows": len(rows),
        "mappingRowClassificationCounts": dict(sorted(class_counts.items())),
        "uniqueEndpointClassificationCounts": dict(sorted(Counter(unique_endpoint_classes.values()).items())),
        "documentedClientEndpoints": len(inventory_endpoint_rows),
        "documentedClientObserved": sum(bool(observed_by_doc_key.get(key)) for key in inventory_endpoint_rows),
        "documentedClientUnverified": sum(not bool(observed_by_doc_key.get(key)) for key in inventory_endpoint_rows),
        "notes": [
            "The earlier navigation-polluted FAQ/Bonus run was overwritten and is not included.",
            "Discovery defect: Daily task Go 9 unexpectedly emitted GET /promo/task/daily/claim on an existing test member. It is recorded as POTENTIAL_REWARD_CLAIM with unavailable before state and must not be replayed.",
            "ACTIVE means successfully observed real FAT UI traffic; levels are intentionally not assigned yet.",
            "Failed UI controls remain in page progress and are not promoted to successful endpoint mappings.",
        ],
    }
    (RESULTS / "fat-client-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
