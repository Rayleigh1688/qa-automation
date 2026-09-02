#!/usr/bin/env python3
"""Build a focused P0 API shortlist from the interface inventory."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path


DOMAIN_ORDER = {
    "auth": 10,
    "finance": 20,
    "game": 30,
    "kyc": 40,
    "member": 50,
}


SAFE_GET_HINTS = [
    "/member/v2/index",
    "/member/game/list",
    "/member/game/list/recommend",
    "/member/game/list/recent",
    "/member/game/bet/list",
    "/finance/wallet",
    "/finance/deposit/list",
    "/finance/withdraw/list",
    "/finance/transaction/list",
    "/finance/transaction/types",
    "/finance/channel/list",
    "/finance/payment/tab/list",
    "/finance/account/list",
    "/finance/payment/bank/list",
    "/member/kyc/detail",
    "/member/kyc/ekyc/info",
    "/member/vip",
    "/member/detail",
    "/member/fav/list",
    "/member/agency/audit/results",
    "/member/agency/problem/list",
    "/promo/task/transaction",
    "/promo/vip/config",
    "/promo/vip/sign/in/config",
]


KNOWN_REPLACEMENTS = {
    "/member/game/list": "/member/v2/index or /member/game/listRw",
    "/member/vip": "/promo/vip/config and /promo/vip/sign/in/config",
}


SIDE_EFFECT_HINTS = [
    "insert",
    "update",
    "delete",
    "claim",
    "deposit",
    "withdraw",
    "payment/deposit",
    "payment/withdraw",
    "callback",
    "approve",
    "reject",
    "send",
    "clear",
    "manual",
    "upgrade",
    "exchange",
    "bind",
    "unbind",
]


def first_domain(p0_domain: str) -> str:
    domains = [item for item in p0_domain.split(",") if item]
    if not domains:
        return ""
    return sorted(domains, key=lambda item: DOMAIN_ORDER.get(item, 999))[0]


def has_any(value: str, hints: list[str]) -> bool:
    lowered = value.lower()
    return any(hint.lower() in lowered for hint in hints)


def execution_policy(row: dict[str, str]) -> str:
    path = row["path"]
    flags = row["flags"]
    method = row["method"]

    if path in KNOWN_REPLACEMENTS:
        return "review_only"
    if any(flag in flags.split(",") for flag in ["deprecated", "old_or_copy", "todo", "invalid_url"]):
        return "review_only"
    if method != "GET":
        return "manual_review"
    if has_any(path, SIDE_EFFECT_HINTS) and not has_any(path, SAFE_GET_HINTS):
        return "manual_review"
    if row["suggested_base_var"] == "{{api_url}}" and has_any(path, SAFE_GET_HINTS):
        return "safe_smoke"
    if row["suggested_base_var"] in {"{{admin_url}}", "{{agency_url}}"}:
        return "token_required"
    return "token_required"


def priority_score(row: dict[str, str]) -> tuple[int, int, str]:
    domain = row["domain"]
    policy = execution_policy(row)
    policy_rank = {
        "safe_smoke": 0,
        "token_required": 1,
        "manual_review": 2,
        "review_only": 3,
    }.get(policy, 9)
    return (DOMAIN_ORDER.get(domain, 999), policy_rank, row["path"])


def read_inventory(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(rows: list[dict[str, str]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "priority",
        "surface",
        "module",
        "domain",
        "execution_policy",
        "method",
        "clean_url",
        "path",
        "suggested_base_var",
        "flags",
        "source_file",
        "name",
    ]
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def table(rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(rows[0]) + " |",
        "| " + " | ".join("---" for _ in rows[0]) + " |",
    ]
    for row in rows[1:]:
        lines.append("| " + " | ".join(item.replace("|", "\\|") for item in row) + " |")
    return "\n".join(lines)


def write_markdown(rows: list[dict[str, str]], output: Path, csv_output: Path) -> None:
    policy_counter = Counter(row["execution_policy"] for row in rows)
    domain_counter = Counter(row["domain"] for row in rows)
    surface_counter = Counter(row["surface"] for row in rows)
    module_counter = Counter(row["module"] for row in rows)

    summary = [
        ["指标", "数量"],
        ["P0 shortlist 接口", str(len(rows))],
        ["可直接冒烟 safe_smoke", str(policy_counter["safe_smoke"])],
        ["需要 token token_required", str(policy_counter["token_required"])],
        ["需要人工复核 manual_review", str(policy_counter["manual_review"])],
        ["仅复核 review_only", str(policy_counter["review_only"])],
    ]
    domains = [["领域", "数量"]] + [[key, str(value)] for key, value in domain_counter.most_common()]
    surfaces = [["调用端", "数量"]] + [[key, str(value)] for key, value in surface_counter.most_common()]
    modules = [["模块", "数量"]] + [[key, str(value)] for key, value in module_counter.most_common()]

    smoke_rows = [["优先级", "领域", "方法", "Clean URL", "来源"]]
    for row in rows:
        if row["execution_policy"] == "safe_smoke":
            smoke_rows.append([row["priority"], row["domain"], row["method"], row["clean_url"], row["source_file"]])
        if len(smoke_rows) >= 31:
            break

    top_rows = [["优先级", "策略", "领域", "方法", "Clean URL", "标记", "来源"]]
    for row in rows[:80]:
        top_rows.append(
            [
                row["priority"],
                row["execution_policy"],
                row["domain"],
                row["method"],
                row["clean_url"],
                row["flags"],
                row["source_file"],
            ]
        )

    output.write_text(
        f"""# P0 接口候选清单

来源：`api/inventory/interfaces.csv`

全量清单：`{csv_output.resolve()}`

## 总览

{table(summary)}

## 领域分布

{table(domains)}

## 调用端与模块分布

{table(surfaces)}

{table(modules)}

## 可先冒烟的 GET 接口

这些接口优先用于连通性和基础响应结构验证。真正进入门禁前仍需确认是否需要 token、设备号、语言或特殊 header。

{table(smoke_rows)}

## P0 shortlist

{table(top_rows)}
""",
        encoding="utf-8",
    )


def main() -> None:
    inventory = Path("api/inventory/interfaces.csv")
    csv_output = Path("api/p0/interface-shortlist.csv")

    rows = []
    for row in read_inventory(inventory):
        if row["p0_candidate"] != "yes":
            if row["path"] not in {"/promo/vip/config", "/promo/vip/sign/in/config"}:
                continue
        if not row["clean_url"]:
            continue
        domain = first_domain(row["p0_domain"])
        if not domain and row["path"].startswith("/promo/vip/"):
            domain = "member"
        policy = execution_policy(row)
        rows.append(
            {
                "priority": "",
                "surface": row.get("surface", "unknown"),
                "module": row.get("module", domain or "other"),
                "domain": domain,
                "execution_policy": policy,
                "method": row["method"],
                "clean_url": row["clean_url"],
                "path": row["path"],
                "suggested_base_var": row["suggested_base_var"],
                "flags": row["flags"],
                "source_file": row["file"],
                "name": row["name"],
            }
        )

    rows.sort(key=priority_score)
    for index, row in enumerate(rows, start=1):
        row["priority"] = f"P0-{index:03d}"

    write_csv(rows, csv_output)
    print(f"wrote {csv_output.resolve()}")


if __name__ == "__main__":
    main()
