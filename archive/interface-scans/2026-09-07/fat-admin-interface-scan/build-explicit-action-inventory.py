#!/usr/bin/env python3
"""Turn the phase-2 DOM snapshot into an explicit, non-executed action inventory."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "fat-admin-interface-scan/results"
SOURCE = RESULTS / "fat-admin-page-initialization.json"
OUTPUT = RESULTS / "fat-admin-explicit-actions.csv"
JSON_OUTPUT = RESULTS / "fat-admin-explicit-actions.json"

FIELDS = [
    "order", "top_menu", "menu_path", "page_name", "page_route", "control_type",
    "action_name", "dom_state", "risk", "execution_status", "parameter_plan",
    "target_data_requirement", "selector_strategy", "selector_ordinal", "evidence", "note",
]


def clean(value):
    value = str(value or "").strip()
    value = re.sub(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", "<redacted-email>", value, flags=re.I)
    value = re.sub(r"(?<!\d)(?:\+?63|0)9\d{9}(?!\d)", "<redacted-phone>", value)
    return re.sub(r"(?<!\d)\d{6,}(?!\d)", "<redacted-numeric-id>", value)


def describe(control_type, item):
    if control_type == "input":
        name = item.get("placeholder") or item.get("aria_label") or item.get("name") or item.get("type") or "unnamed input"
        return clean(name), "INPUT"
    if control_type == "button":
        name = item.get("text") or item.get("aria_label") or item.get("title") or "unnamed button"
        return clean(name), "DISABLED" if item.get("disabled") else "ENABLED"
    if control_type == "tab":
        return clean(item.get("text") or "unnamed tab"), f"selected={item.get('selected', '')}"
    if control_type == "select":
        return clean(item.get("aria_label") or item.get("text") or "unnamed select"), "VISIBLE"
    if control_type == "pagination":
        return clean(item.get("aria_label") or item.get("title") or item.get("text") or "pagination control"), "VISIBLE"
    return clean(item.get("text") or item.get("href") or "unnamed link"), f"href={clean(item.get('href'))}"


def risk_for(control_type, action):
    text = action.lower()
    compact = " ".join(text.split())
    if control_type == "input" or control_type == "select":
        return "READ_FILTER_OR_FORM_INPUT"
    if control_type in {"tab", "pagination", "link"}:
        return "READ_NAVIGATION_TO_VERIFY"
    if compact in {"on closed", "online offline", "yes no", "on off", "cancel", "是 否"}:
        return "WRITE_REQUIRES_CURRENT_RUN_DATA"
    if re.search(r"add|new|create|edit|update|delete|remove|approve|reject|adjust|transfer|clear|enable|disable|lock|unlock|reset password|reset data|reset google|send|grant|import|publish|recalculate|convert to agent|manual reissue|set exchange rate|batch set|save draft|temporary withdrawal limit", text):
        return "WRITE_REQUIRES_CURRENT_RUN_DATA"
    if re.search(r"search|query|filter|reset|refresh|\bview\b|detail|export|download|preview|overview", text):
        return "READ_INTERACTION"
    if re.search(r"chart mode|config|growth log|risk control|reward flow|calculation|cycle|personal|invite|material type|copy|modify|diagram|level map|settings|privacy list|directory|permissions|provider configuration|set share domain", text) or re.search(r"查\s*询|重\s*置|数据导出|搜索|查看|修改|添加|编辑", action):
        return "READ_INTERACTION_REVIEWED"
    return "UNKNOWN_REVIEW_REQUIRED"


def should_exclude(page, control_type, action):
    normalized = " ".join(action.split())
    if not normalized or normalized == "unnamed button":
        return True
    if control_type == "tab":
        if normalized in {page.get("page_name", ""), page.get("top_menu", ""), "Home", "KYC", "Logs"}:
            return True
        if "\n" in action and (re.search(r"\(\d+\)", action) or re.search(r"\n\d+$", action.strip())):
            return True
    if control_type == "input" and normalized.lower() == "search":
        return True
    if control_type == "pagination" and normalized.lower() in {"1", "pagination control"}:
        return True
    if control_type == "button":
        if normalized == "PC" or re.fullmatch(r"[a-z]+_[A-Za-z0-9]+", normalized):
            return True
        if re.fullmatch(r"(?:T|H)\d+", normalized, re.I):
            return True
        if re.fullmatch(r"(?:P\s*)?\d+(?:\.\d+)?", normalized, re.I):
            return True
        if re.fullmatch(r"(?:\d{1,3}\.){3}\d{1,3}", normalized):
            return True
        if "<redacted-numeric-id>" in normalized:
            return True
    return False


def selector_for(control_type, action):
    if control_type == "button":
        return json.dumps({"role": "button", "name": action, "exact": True}, ensure_ascii=False)
    if control_type == "tab":
        return json.dumps({"role": "tab", "name": action, "exact": True}, ensure_ascii=False)
    if control_type == "input":
        return json.dumps({"locator": "input, textarea", "placeholder_or_name": action}, ensure_ascii=False)
    if control_type == "select":
        return json.dumps({"locator": ".ant-layout-content .ant-select", "visible_text": action}, ensure_ascii=False)
    if control_type == "pagination":
        return json.dumps({"locator": ".ant-pagination a, .ant-pagination button", "accessible_name": action}, ensure_ascii=False)
    return json.dumps({"role": "link", "name": action, "exact": True}, ensure_ascii=False)


def main():
    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    rows = []
    seen = set()
    order = 0
    ordinals = {}
    type_map = {
        "inputs": "input", "buttons": "button", "tabs": "tab", "selects": "select",
        "pagination": "pagination", "links": "link",
    }
    for page in payload.get("pages", []):
        for source_type, control_type in type_map.items():
            for item in page.get("controls", {}).get(source_type, []):
                action, state = describe(control_type, item)
                if should_exclude(page, control_type, action):
                    continue
                key = (page.get("route"), control_type, action)
                if key in seen:
                    continue
                seen.add(key)
                ordinal_key = (page.get("route"), control_type, action)
                ordinal = ordinals.get(ordinal_key, 0)
                ordinals[ordinal_key] = ordinal + 1
                order += 1
                risk = risk_for(control_type, action)
                rows.append({
                    "order": order,
                    "top_menu": page.get("top_menu", ""),
                    "menu_path": " > ".join(page.get("menu_path", [])),
                    "page_name": page.get("page_name", ""),
                    "page_route": page.get("route", ""),
                    "control_type": control_type,
                    "action_name": action,
                    "dom_state": state,
                    "risk": risk,
                    "execution_status": "REGISTERED_NOT_EXECUTED",
                    "parameter_plan": "Use current page input/filter/list state; capture field names and origins at execution",
                    "target_data_requirement": "Current-run-created or explicitly designated record only" if risk.startswith("WRITE") else "None for read interaction",
                    "selector_strategy": selector_for(control_type, action),
                    "selector_ordinal": ordinal,
                    "evidence": "fat-admin-page-initialization.json DOM snapshot",
                    "note": "Requires explicit selector/action implementation before phase 3; no broad selector clicking",
                })
    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    JSON_OUTPUT.write_text(json.dumps({"generated_from": SOURCE.name, "actions": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    counts = {}
    for row in rows:
        counts[row["risk"]] = counts.get(row["risk"], 0) + 1
    print(json.dumps({"actions": len(rows), "risk_counts": counts}, ensure_ascii=False))


if __name__ == "__main__":
    main()
