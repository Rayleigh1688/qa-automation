#!/usr/bin/env python3
"""Generate read-only interface catalog views from the canonical inventory."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path


SOURCE = Path("api/inventory/interfaces.csv")
OUTPUT = Path("api/catalog")
FIELDS = [
    "surface", "module", "method", "path", "clean_url", "flags",
    "p0_candidate", "source_file", "name",
]


def read_rows() -> list[dict[str, str]]:
    with SOURCE.open(encoding="utf-8", newline="") as handle:
        rows = []
        for row in csv.DictReader(handle):
            if not row.get("method"):
                continue
            rows.append({
                "surface": row.get("surface", "unknown"),
                "module": row.get("module", "other"),
                "method": row.get("method", ""),
                "path": row.get("path", ""),
                "clean_url": row.get("clean_url", ""),
                "flags": row.get("flags", ""),
                "p0_candidate": row.get("p0_candidate", ""),
                "source_file": row.get("file", ""),
                "name": row.get("name", ""),
            })
        return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda row: (row["module"], row["path"], row["method"])))


def main() -> None:
    rows = read_rows()
    surfaces = sorted({row["surface"] for row in rows})
    for surface in surfaces:
        surface_rows = [row for row in rows if row["surface"] == surface]
        write_csv(OUTPUT / f"{surface}.csv", surface_rows)
        if surface == "admin":
            for module in sorted({row["module"] for row in surface_rows}):
                write_csv(
                    OUTPUT / "admin" / f"{module}.csv",
                    [row for row in surface_rows if row["module"] == module],
                )

    surface_counts = Counter(row["surface"] for row in rows)
    admin_counts = Counter(row["module"] for row in rows if row["surface"] == "admin")
    lines = [
        "# API 分类目录",
        "",
        "本目录由 `scripts/build-api-catalog.py` 从 `api/inventory/interfaces.csv` 自动生成，只用于检索；不要手工维护，也不替代 `api/p0/test-cases.csv`。",
        "",
        "## 调用端",
        "",
        "| 调用端 | 接口数 | 文件 |",
        "|---|---:|---|",
    ]
    for surface, count in surface_counts.most_common():
        lines.append(f"| {surface} | {count} | [`{surface}.csv`]({surface}.csv) |")
    lines.extend([
        "",
        "## 管理后台模块",
        "",
        "| 模块 | 接口数 | 文件 |",
        "|---|---:|---|",
    ])
    for module, count in admin_counts.most_common():
        lines.append(f"| {module} | {count} | [`admin/{module}.csv`](admin/{module}.csv) |")
    lines.extend([
        "",
        "## 维护规则",
        "",
        "- `surface` 表示调用端：client、admin、agency 或 unknown。",
        "- `module` 表示业务模块：auth、member、kyc、finance、game、permission、report、promo 或 other。",
        "- P0 执行顺序仍由 `api/p0/test-cases.csv` 与 `main-flow-scenarios.csv` 决定。",
        "- 重新扫描 Bruno 后依次运行 `build-p0-shortlist.py`、`build-p0-test-cases.py` 和本脚本。",
    ])
    (OUTPUT / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT} ({len(rows)} interfaces)")


if __name__ == "__main__":
    main()
