#!/usr/bin/env python3
"""Build a sanitized FAT admin discovery baseline from runtime and static evidence."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit


UI_PREFIXES = (
    "/member-center",
    "/member-management",
    "/game",
    "/gamev2",
    "/logs",
    "/operations",
    "/promo-marketing",
    "/report-management",
    "/risk-control",
    "/system",
    "/user",
    "/whitelist",
)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def response_data(row: dict):
    body = row.get("decoded_body")
    return body.get("data") if isinstance(body, dict) else None


def top_menu_for_route(route: str) -> str:
    mapping = {
        "/member-center": "会员",
        "/member-management": "会员",
        "/risk-control": "风控管理",
        "/game": "游戏",
        "/gamev2": "游戏",
        "/system": "系统",
        "/user": "系统",
        "/whitelist": "系统",
        "/logs": "日志",
        "/report-management": "报表",
        "/operations": "运营管理",
        "/promo-marketing": "运营管理",
    }
    return next((name for prefix, name in mapping.items() if route.startswith(prefix)), "待确认")


def normalize_path(url: str) -> str:
    return urlsplit(url).path.rstrip("/") or "/"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--safe", type=Path, required=True)
    parser.add_argument("--menu", type=Path, required=True)
    parser.add_argument("--deep-menu", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, default=Path("api/inventory/interfaces.csv"))
    parser.add_argument("--out-dir", type=Path, default=Path("fat-admin-interface-scan"))
    args = parser.parse_args()

    safe = read_json(args.safe)
    menu = read_json(args.menu)
    deep = read_json(args.deep_menu)
    bundle = args.bundle.read_text(encoding="utf-8", errors="ignore")
    args.out_dir.mkdir(parents=True, exist_ok=True)

    root_names = {
        "10000": "会员", "20000": "KYC", "30000": "财务管理", "40000": "风控管理",
        "50000": "游戏", "60000": "系统", "70000": "日志", "80000": "报表",
        "90000": "运营管理", "100000": "活动管理", "120600": "代理管理", "130000": "素材管理",
    }
    direct = []
    for result in menu:
        rows = response_data(result)
        if not isinstance(rows, list):
            continue
        for row in rows:
            item = {k: row.get(k) for k in ("id", "pid", "name", "module", "routeName", "state", "flag")}
            item["top_menu"] = root_names.get(str(row.get("pid")), "")
            direct.append(item)

    deep_by_parent: dict[str, list[dict]] = {}
    for result in deep:
        rows = response_data(result)
        pid = str(result.get("case_id", "")).removeprefix("MENU-")
        if isinstance(rows, list):
            deep_by_parent[pid] = rows

    pages_path = args.out_dir / "fat-admin-page-inventory.csv"
    with pages_path.open("w", encoding="utf-8", newline="") as handle:
        fields = ["top_menu", "permission_id", "permission_name", "permission_module", "route_name", "state", "flag", "child_operation_count", "source", "ui_scan_status"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in direct:
            writer.writerow({
                "top_menu": row["top_menu"],
                "permission_id": row.get("id", ""),
                "permission_name": row.get("name", ""),
                "permission_module": row.get("module", ""),
                "route_name": row.get("routeName", ""),
                "state": row.get("state", ""),
                "flag": row.get("flag", ""),
                "child_operation_count": len(deep_by_parent.get(str(row.get("id")), [])),
                "source": "GET /admin/priv/list",
                "ui_scan_status": "PENDING_UI_SCAN",
            })

    operations_path = args.out_dir / "fat-admin-permission-operations.csv"
    with operations_path.open("w", encoding="utf-8", newline="") as handle:
        fields = ["top_menu", "parent_permission_id", "parent_permission_name", "operation_id", "operation_name", "declared_path", "documented", "inventory_name", "inventory_file", "runtime_request_status"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        with args.inventory.open(encoding="utf-8", newline="") as inv_handle:
            inventory = list(csv.DictReader(inv_handle))
        by_path: dict[str, list[dict]] = {}
        for row in inventory:
            if row.get("surface") == "admin":
                by_path.setdefault(normalize_path(row.get("path", "")), []).append(row)
        for parent in direct:
            for operation in deep_by_parent.get(str(parent.get("id")), []):
                declared = normalize_path(str(operation.get("module") or "")) if operation.get("module") else ""
                matches = by_path.get(declared, [])
                writer.writerow({
                    "top_menu": parent["top_menu"],
                    "parent_permission_id": parent.get("id", ""),
                    "parent_permission_name": parent.get("name", ""),
                    "operation_id": operation.get("id", ""),
                    "operation_name": operation.get("name", ""),
                    "declared_path": declared,
                    "documented": "YES" if matches else "NO",
                    "inventory_name": " | ".join(sorted({m.get("name", "") for m in matches})),
                    "inventory_file": " | ".join(sorted({m.get("file", "") for m in matches})),
                    "runtime_request_status": "NOT_TRIGGERED_FROM_UI",
                })

    quoted_paths = set(re.findall(r"[\"'](/[^\"'?#]{1,180})(?:\?[^\"']*)?[\"']", bundle))
    ui_routes = sorted(path for path in quoted_paths if path.startswith(UI_PREFIXES))
    routes_path = args.out_dir / "fat-admin-static-routes.csv"
    with routes_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["top_menu", "route", "source", "runtime_status"])
        writer.writeheader()
        for route in ui_routes:
            writer.writerow({"top_menu": top_menu_for_route(route), "route": route, "source": "FAT current umi bundle", "runtime_status": "NOT_OPENED_NO_BROWSER"})

    executed = {}
    evidence = []
    for row in safe:
        url = str(row.get("url") or "")
        path = normalize_path(url) if url else ""
        body = row.get("decoded_body")
        business_status = body.get("status") if isinstance(body, dict) else None
        data = body.get("data") if isinstance(body, dict) else None
        if path:
            executed[path] = row
        evidence.append({
            "case_id": row.get("case_id", ""),
            "method": row.get("method", ""),
            "path": path,
            "http_status": row.get("status"),
            "business_status": business_status,
            "elapsed_ms": row.get("elapsed_ms"),
            "assertion_passed": row.get("assertion_passed", row.get("ok")),
            "data_type": type(data).__name__ if data is not None else "null",
            "data_keys": sorted(data.keys()) if isinstance(data, dict) else [],
        })
    (args.out_dir / "fat-admin-api-evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    api_paths = sorted(set(re.findall(r"[\"'](/admin/[A-Za-z0-9_./-]+)[\"']", bundle)))
    interface_path = args.out_dir / "fat-admin-static-interface-comparison.csv"
    with interface_path.open("w", encoding="utf-8", newline="") as handle:
        fields = ["path", "bundle_referenced", "documented", "documented_methods", "inventory_names", "runtime_api_executed", "http_status", "business_status", "classification", "classification_basis"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for path in api_paths:
            matches = by_path.get(normalize_path(path), [])
            run = executed.get(normalize_path(path))
            if run and matches:
                classification = "DOCUMENTED_REACHABLE"
                basis = "API probe succeeded; browser page trigger not yet observed"
            elif run:
                classification = "UNDOCUMENTED_CANDIDATE"
                basis = "API probe succeeded; absent from inventory; browser page trigger not yet observed"
            elif matches:
                classification = "DOCUMENTED_UNVERIFIED"
                basis = "Referenced by current FAT bundle; not executed from UI"
            else:
                classification = "UNDOCUMENTED_CANDIDATE"
                basis = "Referenced by current FAT bundle; absent from inventory; not executed from UI"
            body = run.get("decoded_body") if run else None
            writer.writerow({
                "path": path,
                "bundle_referenced": "YES",
                "documented": "YES" if matches else "NO",
                "documented_methods": " | ".join(sorted({m.get("method", "") for m in matches})),
                "inventory_names": " | ".join(sorted({m.get("name", "") for m in matches})),
                "runtime_api_executed": "YES" if run else "NO",
                "http_status": run.get("status", "") if run else "",
                "business_status": body.get("status", "") if isinstance(body, dict) else "",
                "classification": classification,
                "classification_basis": basis,
            })

    association_path = args.out_dir / "fat-admin-page-action-interface.csv"
    association_count = 0
    with association_path.open("w", encoding="utf-8", newline="") as handle:
        fields = [
            "top_menu", "page_name", "page_permission_path", "action_name", "method",
            "normalized_path", "parameter_fields", "parameter_source", "http_status",
            "business_status", "response_structure", "auth_role", "side_effect",
            "before_state", "after_state", "original_category", "original_name",
            "classification", "currently_used_by_ui", "evidence", "blocked_scope",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for parent in direct:
            for operation in deep_by_parent.get(str(parent.get("id")), []):
                declared = normalize_path(str(operation.get("module") or "")) if operation.get("module") else ""
                if not declared:
                    continue
                association_count += 1
                matches = by_path.get(declared, [])
                run = executed.get(declared)
                body = run.get("decoded_body") if run else None
                query_names = set()
                for match in matches:
                    query_names.update(key for key, _ in parse_qsl(urlsplit(match.get("clean_url", "")).query, keep_blank_values=True))
                if run:
                    query_names.update(key for key, _ in parse_qsl(urlsplit(str(run.get("url") or "")).query, keep_blank_values=True))
                if run and matches:
                    classification = "DOCUMENTED_REACHABLE"
                elif run:
                    classification = "UNDOCUMENTED_CANDIDATE"
                elif matches:
                    classification = "DOCUMENTED_UNVERIFIED"
                else:
                    classification = "UNDOCUMENTED_CANDIDATE"
                data = body.get("data") if isinstance(body, dict) else None
                if isinstance(data, dict):
                    structure = "object:" + "|".join(sorted(data.keys()))
                elif isinstance(data, list):
                    structure = "list"
                elif data is None:
                    structure = "unverified"
                else:
                    structure = type(data).__name__
                writer.writerow({
                    "top_menu": parent["top_menu"],
                    "page_name": parent.get("name", ""),
                    "page_permission_path": parent.get("module", ""),
                    "action_name": operation.get("name", ""),
                    "method": " | ".join(sorted({m.get("method", "") for m in matches})),
                    "normalized_path": declared,
                    "parameter_fields": "|".join(sorted(query_names)) or "TO_CAPTURE",
                    "parameter_source": "inventory/runtime query names only; body and UI source TO_CAPTURE",
                    "http_status": run.get("status", "") if run else "",
                    "business_status": body.get("status", "") if isinstance(body, dict) else "",
                    "response_structure": structure,
                    "auth_role": "current FAT admin; exact role name TO_CAPTURE",
                    "side_effect": "none observed" if run else "TO_VERIFY_BEFORE_WRITE",
                    "before_state": "not captured",
                    "after_state": "not captured",
                    "original_category": " | ".join(sorted({f"{m.get('surface','')}/{m.get('module','')}" for m in matches})),
                    "original_name": " | ".join(sorted({m.get("name", "") for m in matches})),
                    "classification": classification,
                    "currently_used_by_ui": "UNVERIFIED_PENDING_UI_SCAN",
                    "evidence": "fat-admin-api-evidence.json" if run else "permission tree + FAT bundle",
                    "blocked_scope": "awaiting UI interaction and Network evidence",
                })

    summary = {
        "page_permissions": len(direct),
        "permission_operations": sum(len(v) for v in deep_by_parent.values()),
        "page_action_interface_rows": association_count,
        "static_ui_routes": len(ui_routes),
        "bundle_admin_api_paths": len(api_paths),
        "bundle_documented_paths": sum(1 for path in api_paths if by_path.get(normalize_path(path))),
        "bundle_undocumented_candidates": sum(1 for path in api_paths if not by_path.get(normalize_path(path))),
        "api_probe_records": len(evidence),
        "api_probe_successes": sum(1 for row in evidence if row["http_status"] == 200 and row["business_status"] is True),
        "bundle_sha256": hashlib.sha256(args.bundle.read_bytes()).hexdigest(),
    }
    (args.out_dir / "fat-admin-baseline-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
