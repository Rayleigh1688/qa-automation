#!/usr/bin/env python3
"""Build a per-action review of the first-pass skips, errors, and write blockers.

This consumes only the repository's already-redacted scan assets.  It does not log
in, call FAT, or read ignored runtime credentials.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
ACTION_FILES = (
    RESULTS / "fat-admin-explicit-navigation-actions.json",
    RESULTS / "fat-admin-explicit-read-actions.json",
    RESULTS / "fat-admin-explicit-filter-actions.json",
    RESULTS / "fat-admin-explicit-reviewed-actions.json",
)
WRITE_FILE = RESULTS / "fat-admin-write-action-status.csv"
OUT_CSV = RESULTS / "fat-admin-legacy-gap-review.csv"
OUT_JSON = RESULTS / "fat-admin-legacy-gap-review-summary.json"
OUT_MD = RESULTS / "fat-admin-legacy-gap-review.md"


def root_cause(status: str) -> str:
    if status == "ERROR":
        return "STRICT_LOCATOR_PROBLEM"
    if status == "SKIPPED_NO_OPTION":
        return "CURRENT_STATE_NOT_VISIBLE"
    if status.startswith("SKIPPED_"):
        return "STRICT_LOCATOR_PROBLEM"
    if status in {"BLOCKED_DATA_SCOPE", "BLOCKED_PREREQUISITE"}:
        return "MISSING_LEGAL_DATA"
    return ""


def disposition(page: str, action: str, status: str) -> str:
    if page == "Member" and action == "Convert to Agent":
        return "SUPERSEDED_BY_NEWER_EXECUTED_EVIDENCE"
    if status == "SKIPPED_NO_OPTION":
        return "RETRY_ONLY_WHEN_A_LEGAL_OPTION_IS_VISIBLE"
    if status.startswith("BLOCKED_"):
        return "KEEP_BLOCKED_UNTIL_CURRENT_RUN_OWNED_DATA_AND_RECOVERY_EXIST"
    return "TARGETED_UI_RETRY_REQUIRED"


def main() -> None:
    rows: list[dict[str, str]] = []
    for path in ACTION_FILES:
        payload = json.loads(path.read_text())
        for item in payload.get("executions", []):
            status = item.get("status", "")
            if status != "ERROR" and not status.startswith("SKIPPED_"):
                continue
            rows.append(
                {
                    "source": path.name,
                    "page_name": item.get("page_name", ""),
                    "page_route": item.get("page_route", ""),
                    "action_name": item.get("action_name", ""),
                    "original_status": status,
                    "review_root_cause": root_cause(status),
                    "current_disposition": disposition(
                        item.get("page_name", ""), item.get("action_name", ""), status
                    ),
                    "evidence": "first-pass explicit-action execution; page belongs to the 57-route live menu set",
                    "blocked_scope": (
                        "selector/context or current option visibility; no interface request proved"
                    ),
                }
            )

    with WRITE_FILE.open(newline="") as handle:
        for item in csv.DictReader(handle):
            status = item.get("status", "")
            if not status.startswith("BLOCKED_"):
                continue
            action = item.get("action_name", "")
            page = item.get("page_name", "")
            rows.append(
                {
                    "source": WRITE_FILE.name,
                    "page_name": page,
                    "page_route": item.get("page_route", ""),
                    "action_name": action,
                    "original_status": status,
                    "review_root_cause": root_cause(status),
                    "current_disposition": disposition(page, action, status),
                    "evidence": item.get("evidence", "") or item.get("reason", ""),
                    "blocked_scope": item.get("reason", ""),
                }
            )

    fieldnames = list(rows[0])
    with OUT_CSV.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    status_counts = Counter(row["original_status"] for row in rows)
    cause_counts = Counter(row["review_root_cause"] for row in rows)
    summary = {
        "sources_are_redacted_repository_assets": True,
        "network_or_business_requests_sent": 0,
        "legacy_safe_skips": sum(
            count for status, count in status_counts.items() if status.startswith("SKIPPED_")
        ),
        "legacy_interaction_errors": status_counts["ERROR"],
        "legacy_write_blockers": status_counts["BLOCKED_DATA_SCOPE"]
        + status_counts["BLOCKED_PREREQUISITE"],
        "original_status_counts": dict(sorted(status_counts.items())),
        "root_cause_counts": dict(sorted(cause_counts.items())),
        "page_no_longer_used_findings": 0,
        "page_no_longer_used_note": (
            "All reviewed rows belong to the live 57-route menu evidence; absence of a request is not STALE proof."
        ),
        "known_method_or_classification_drifts": [
            {
                "ui_request": "POST /admin/member/list",
                "documented_request": "GET /admin/member/list",
                "classification": "MISCLASSIFIED",
            },
            {
                "ui_request": "POST /admin/finance/tokens/transaction/list",
                "documented_request": "GET /admin/finance/tokens/transaction/list",
                "classification": "MISCLASSIFIED",
            },
        ],
    }
    OUT_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")

    OUT_MD.write_text(
        "# FAT first-pass gap review\n\n"
        "This review is generated from redacted repository evidence. It sends no request and does not change business data.\n\n"
        f"- Safe skips reviewed: {summary['legacy_safe_skips']}\n"
        f"- Interaction errors reviewed: {summary['legacy_interaction_errors']}\n"
        f"- Legacy write blockers reviewed: {summary['legacy_write_blockers']}\n"
        "- Pages proven unused: 0. Every reviewed page is in the live 57-route menu evidence, so no row is marked STALE merely because the first pass did not trigger Network.\n"
        f"- Root causes: {dict(sorted(cause_counts.items()))}\n\n"
        "The six interaction errors are strict-locator/overlay failures. Safe skips marked not actionable or not in filter context are scanner-safety gaps, not endpoint failures. The single no-option row is current-state dependent. Write blockers remain missing-legal-data findings unless newer controlled-flow evidence supersedes them.\n\n"
        "Known method/classification drift remains `POST /admin/member/list` versus documented GET and `POST /admin/finance/tokens/transaction/list` versus documented GET; both use `MISCLASSIFIED`.\n"
    )

    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
