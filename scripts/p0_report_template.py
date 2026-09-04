#!/usr/bin/env python3
"""Shared HTML/Markdown presentation for P0 API, UI, and main-flow reports."""

from __future__ import annotations

import html
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path


EAST_8 = timezone(timedelta(hours=8))


def format_east8_time(value: datetime | str | None = None) -> str:
    """Return a stable human-readable timestamp in UTC+8."""
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    current = value or datetime.now(EAST_8)
    if current.tzinfo is None:
        current = current.replace(tzinfo=EAST_8)
    return current.astimezone(EAST_8).strftime("%Y-%m-%d %H:%M:%S（UTC+8）")


def format_execution_duration(started_at: object, finished_at: object) -> str:
    """Format run-status ISO timestamps as a concise elapsed duration."""
    if not started_at or not finished_at:
        return ""
    try:
        started = datetime.fromisoformat(str(started_at))
        finished = datetime.fromisoformat(str(finished_at))
        total_seconds = max(0, round((finished - started).total_seconds()))
    except (TypeError, ValueError):
        return ""
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours >= 1:
        return f"{hours}小时{minutes:02d}分{seconds:02d}秒"
    if minutes >= 1:
        return f"{minutes}分{seconds:02d}秒"
    return f"{seconds}秒"


def status_class(status: str) -> str:
    normalized = status.upper()
    if normalized in {"PASS", "PASSED", "通过"}:
        return "pass"
    if normalized in {"FAIL", "FAILED", "BLOCKED", "失败", "未通过"}:
        return "fail"
    return "pending"


def report_verdict(items: list[dict[str, str]], run_status: str = "") -> tuple[str, str]:
    counts = Counter(item.get("status", "UNKNOWN").upper() for item in items)
    if run_status.upper() in {"FAILED", "INTERRUPTED", "BLOCKED"} or counts["FAIL"] or counts["FAILED"]:
        return "BLOCKED", "存在失败或执行中断，请查看失败明细和最后执行阶段。"
    if not items or counts["PENDING"] or counts["SKIPPED"] or counts["NOT_RUN"]:
        return "PARTIAL", "已执行项通过，但仍有未执行或跳过项。"
    return "PASS", "本报告范围内的全部已执行检查均符合预期。"


def write_html_report(
    *,
    title: str,
    scope: str,
    report_kind: str,
    verdict: str,
    verdict_detail: str,
    items: list[dict[str, str]],
    output: Path,
    metadata: list[tuple[str, str]] | None = None,
) -> None:
    groups: dict[str, list[dict[str, str]]] = {}
    for item in items:
        groups.setdefault(item.get("group") or "其他", []).append(item)
    counts = Counter(item.get("status", "UNKNOWN").upper() for item in items)
    metrics = [
        ("执行总数", len(items), ""),
        ("通过", counts["PASS"], "pass"),
        ("失败", counts["FAIL"] + counts["FAILED"], "fail"),
        ("未执行/跳过", counts["PENDING"] + counts["SKIPPED"] + counts["NOT_RUN"], "pending"),
    ]
    cards = "".join(
        f'<div class="metric {css}"><span>{html.escape(label)}</span><strong>{value}</strong></div>'
        for label, value, css in metrics
    )
    navigation = "".join(
        f'<a href="#group-{index}" class="flow"><span>{html.escape(group)}</span><small>{len(group_items)}</small></a>'
        for index, (group, group_items) in enumerate(groups.items(), 1)
    )
    sections: list[str] = []
    for index, (group, group_items) in enumerate(groups.items(), 1):
        rows: list[str] = []
        for item in group_items:
            status = item.get("status", "UNKNOWN")
            detail_rows = [
                ("检查对象", item.get("target", "")),
                ("预期结果", item.get("expected", "")),
                ("实际结果", item.get("actual", "")),
                ("耗时", item.get("duration", "")),
                ("说明", item.get("detail", "")),
            ]
            details = "".join(
                f"<dt>{html.escape(label)}</dt><dd>{html.escape(value or '—')}</dd>"
                for label, value in detail_rows
            )
            rows.append(
                '<details class="case"{}>'.format(" open" if status_class(status) == "fail" else "")
                + f'<summary><span class="badge {status_class(status)}">{html.escape(status)}</span>'
                + f'<b>{html.escape(item.get("id", ""))}</b>'
                + f'<span>{html.escape(item.get("name", ""))}</span>'
                + f'<em>{html.escape(item.get("kind", ""))}</em></summary>'
                + f'<div class="case-body"><dl>{details}</dl></div></details>'
            )
        sections.append(
            f'<section id="group-{index}"><h2>{html.escape(group)} '
            f'<small>{len(group_items)} 项</small></h2>{"".join(rows)}</section>'
        )
    meta = [("环境", scope), ("报告类型", report_kind), *(metadata or [])]
    meta_html = " · ".join(f"{html.escape(key)}：{html.escape(value)}" for key, value in meta if value)
    generated_at = format_east8_time()
    document = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><style>
:root{{--ink:#17232d;--muted:#64727d;--line:#d9e1e5;--panel:#fff;--bg:#f3f6f5;--pass:#16754b;--fail:#bd3434;--pending:#a76508}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:14px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
main{{max-width:1180px;margin:auto;padding:28px 20px 56px}}header{{display:flex;justify-content:space-between;gap:24px;align-items:start;border-bottom:1px solid var(--line);padding-bottom:22px}}h1{{font-size:26px;margin:0 0 5px}}h2{{font-size:18px;margin:30px 0 10px}}h2 small,.meta{{font-size:13px;font-weight:400;color:var(--muted)}}.verdict{{min-width:240px;border:1px solid var(--line);background:var(--panel);padding:14px 16px;border-left:5px solid var(--pending)}}.verdict.fail{{border-left-color:var(--fail)}}.verdict.pass{{border-left-color:var(--pass)}}.verdict strong{{display:block;font-size:22px;margin-bottom:3px}}.metrics{{display:grid;grid-template-columns:repeat(4,minmax(130px,1fr));gap:10px;margin:20px 0}}.metric{{background:var(--panel);border:1px solid var(--line);padding:12px}}.metric span{{color:var(--muted);display:block}}.metric strong{{font-size:24px}}.metric.pass strong{{color:var(--pass)}}.metric.fail strong{{color:var(--fail)}}.metric.pending strong{{color:var(--pending)}}.flow-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:8px}}.flow{{color:var(--ink);text-decoration:none;background:var(--panel);border:1px solid var(--line);padding:10px 12px}}.flow small{{float:right;color:var(--muted)}}.case{{background:var(--panel);border:1px solid var(--line);margin:6px 0}}summary{{display:grid;grid-template-columns:74px 105px 1fr 100px;gap:10px;align-items:center;padding:11px 12px;cursor:pointer;list-style:none}}summary::-webkit-details-marker{{display:none}}.badge{{font-size:12px;font-weight:700}}.badge.pass{{color:var(--pass)}}.badge.fail{{color:var(--fail)}}.badge.pending{{color:var(--pending)}}summary em{{color:var(--muted);font-style:normal;text-align:right}}.case-body{{border-top:1px solid var(--line);padding:12px 16px;background:#fbfcfc}}dl{{display:grid;grid-template-columns:105px 1fr;gap:7px 14px;margin:0}}dt{{color:var(--muted)}}dd{{margin:0;word-break:break-word}}@media(max-width:700px){{header{{display:block}}.verdict{{margin-top:16px}}.metrics{{grid-template-columns:repeat(2,1fr)}}summary{{grid-template-columns:68px 90px 1fr}}summary em{{display:none}}dl{{grid-template-columns:1fr}}dt{{margin-top:8px}}}}
</style></head><body><main><header><div><h1>{html.escape(title)}</h1><div class="meta">{meta_html} · 生成时间：{html.escape(generated_at)}</div></div><div class="verdict {status_class(verdict)}"><strong>{html.escape(verdict)}</strong><span>{html.escape(verdict_detail)}</span></div></header><div class="metrics">{cards}</div><nav class="flow-grid">{navigation}</nav>{''.join(sections)}</main></body></html>"""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(document, encoding="utf-8")


def write_markdown_report(
    *,
    title: str,
    scope: str,
    verdict: str,
    verdict_detail: str,
    items: list[dict[str, str]],
    output: Path,
) -> None:
    counts = Counter(item.get("status", "UNKNOWN").upper() for item in items)
    lines = [
        f"# {title}", "", f"环境：{scope} · 结论：**{verdict}**", "", verdict_detail, "",
        f"执行总数：{len(items)} · 通过：{counts['PASS']} · 失败：{counts['FAIL'] + counts['FAILED']} · 未执行/跳过：{counts['PENDING'] + counts['SKIPPED'] + counts['NOT_RUN']}", "",
        "| 分组 | ID | 名称 | 类型 | 结果 | 检查对象 | 预期 | 实际 |", "|---|---|---|---|---|---|---|---|",
    ]
    for item in items:
        values = [item.get(key, "") for key in ("group", "id", "name", "kind", "status", "target", "expected", "actual")]
        lines.append("| " + " | ".join(str(value).replace("|", "\\|").replace("\n", " ") for value in values) + " |")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
