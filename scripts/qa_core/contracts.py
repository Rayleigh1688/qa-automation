"""Request contracts shared by asset generation and execution (no I/O)."""

from __future__ import annotations

import json


WITHDRAW_AUDIT_PATH = "/admin/finance/withdraw/risk/audit/list"
MILLISECOND_WINDOW_PATHS = {WITHDRAW_AUDIT_PATH, "/admin/finance/deposit/risk/list", "/admin/finance/deposit/list", "/admin/finance/transaction/list"}
TIME_TOKENS = {
    "{{now_minus_2d}}": (-2 * 86400, 1),
    "{{now_plus_5m}}": (300, 1),
    "{{now_minus_2d_ms}}": (-2 * 86400, 1000),
    "{{now_plus_5m_ms}}": (300, 1000),
}


def normalize_request_template(path: str, raw: str) -> str:
    """Normalize confirmed millisecond list windows, idempotently."""
    if path not in MILLISECOND_WINDOW_PATHS or not raw:
        return raw
    body = json.loads(raw)
    for key in ("start_time", "end_time"):
        value = body.get(key)
        if value in ("{{now_minus_2d}}", "{{now_plus_5m}}"):
            body[key] = value[:-2] + "_ms}}"
    return json.dumps(body, ensure_ascii=False, separators=(",", ":"))


def resolve_dynamic_values(value: object, now: int) -> object:
    """Resolve timestamps while preserving nested request data and types."""
    if isinstance(value, dict):
        return {key: resolve_dynamic_values(item, now) for key, item in value.items()}
    if isinstance(value, list):
        return [resolve_dynamic_values(item, now) for item in value]
    if isinstance(value, str) and value in TIME_TOKENS:
        offset, multiplier = TIME_TOKENS[value]
        return (now + offset) * multiplier
    return value
