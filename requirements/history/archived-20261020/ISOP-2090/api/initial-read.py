#!/usr/bin/env python3
"""Collect only the existing FAT activity-list contract for ISOP-2090.

No configuration, reward, settlement, or client business route is called.
Raw responses are private evidence; the terminal only receives an allowlist.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "scripts"))

from filbet.requirement_session import Session
from qa_core.environment import load_environment
from qa_core.output_paths import repository_output_path
from qa_core.redaction import sanitize_error

PATH = "/admin/promo/list"
DEFAULT_OUT = ROOT / "reports/qa/ISOP-2090/20261012-full/evidence"


def public_name(value):
    if not isinstance(value, str):
        return None
    value = re.sub(r"[\w.+-]+@[\w.-]+", "<redacted>", value)
    value = re.sub(r"\d{7,}", "<redacted>", value)
    return value[:120]


def rows_of(response):
    body = response.get("body")
    data = body.get("data") if isinstance(body, dict) else None
    rows = data.get("d") if isinstance(data, dict) else None
    return rows if isinstance(rows, list) else [], data


def summarize(label, query, response):
    body = response.get("body")
    rows, data = rows_of(response)
    activities = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        item = {key: row[key] for key in ("id", "activity_id", "state")
                if key in row and isinstance(row[key], (int, bool))}
        for key in ("activity_name", "name", "title"):
            value = public_name(row.get(key))
            if value is not None:
                item[key] = value
        # Field names aid live contract discovery without exposing row values.
        item["field_names"] = sorted(row)
        activities.append(item)
    return {
        "probe": label, "method": "GET", "path": PATH, "query": query,
        "http": response.get("http"),
        "business_status": body.get("status") if isinstance(body, dict)
        and type(body.get("status")) is bool else None,
        "data_type": type(data).__name__, "row_count": len(rows),
        "total": data.get("t") if isinstance(data, dict)
        and type(data.get("t")) is int else None,
        "activities": activities,
        "elapsed_ms": response.get("elapsed_ms"),
    }


def private_json(path, payload):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", default=".env.fat")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--insecure", action="store_true")
    parser.add_argument("--out", type=lambda value: repository_output_path(value, ROOT), default=str(DEFAULT_OUT))
    args = parser.parse_args()
    if Path(args.env).name != ".env.fat":
        parser.error("this initial collector only supports explicit .env.fat")
    queries = [("loss-name", {"page": 1, "page_size": 100, "activity_name": "输值"}),
               ("all-first-page", {"page": 1, "page_size": 100})]
    if not args.execute:
        print(json.dumps({"environment": "FAT", "login": "fresh admin",
                          "queries": queries, "path": PATH,
                          "execute": False}, ensure_ascii=False))
        return 0
    config = load_environment(args.env)
    if (config.get("ADMIN_URL"), config.get("API_URL")) != (
        "https://admin-fat.filbet2025.com", "https://client-fat.filbet2025.com"
    ):
        raise ValueError("selected environment must contain matching FAT endpoints")
    args.out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(ZoneInfo("Asia/Manila")).strftime("%Y%m%dT%H%M%S%f")
    summary = {"requirement": "ISOP-2090", "environment": "FAT",
               "run_at": datetime.now(ZoneInfo("Asia/Manila")).isoformat(),
               "deployment": "未提供", "probes": [],
               "scope": "fresh admin login; existing GET activity list only"}
    session = Session(config["ADMIN_URL"], config, timeout=15, insecure=args.insecure)
    try:
        session.login()
        summary["login"] = "success"
        for label, query in queries:
            response = session.request("GET", PATH, query=query)
            evidence = args.out / f"initial-{stamp}-{label}-private.json"
            private_json(evidence, {"method": "GET", "path": PATH,
                                   "query": query, "response": response})
            observation = summarize(label, query, response)
            observation["private_evidence"] = str(evidence.relative_to(ROOT))
            summary["probes"].append(observation)
            if response.get("http") != 200 or observation["business_status"] is not True:
                summary["stopped"] = "list query failed; no further requests"
                break
    except Exception as error:
        summary["error"] = sanitize_error(error, config)
    finally:
        session.token = ""
    target = args.out / f"initial-{stamp}-summary.json"
    with target.open("x", encoding="utf-8") as stream:
        json.dump(summary, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("Summary: " + str(target))
    return 1 if "error" in summary or "stopped" in summary else 0


if __name__ == "__main__":
    sys.exit(main())
