#!/usr/bin/env python3
"""Scan a Bruno collection and generate an interface inventory."""

from __future__ import annotations

import argparse
import csv
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit


METHODS = {"get", "post", "put", "delete", "patch", "head", "options"}


P0_KEYWORDS = {
    "auth": ["login", "logout", "register", "sms", "otp", "refresh/token", "auth", "password"],
    "finance": ["finance", "wallet", "deposit", "withdraw", "payment", "transaction", "account/bank"],
    "game": ["game/list", "game/index", "game/bet", "member/v2/index", "fav", "recent"],
    "kyc": ["kyc", "ekyc", "ocr"],
    "member": ["member/detail", "member/card", "member/vip", "member/agency"],
}


HOST_VAR_MAP = {
    "client-fat.filbet2025.com": "{{api_url}}",
    "client-beta.filbet2025.com": "{{api_url}}",
    "client-beta.filbet.zone": "{{api_url}}",
    "admin-fat.filbet2025.com": "{{admin_url}}",
    "admin-antd.filbet2025.com": "{{admin_url}}",
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def extract_meta(text: str, key: str) -> str:
    match = re.search(rf"(?m)^\s*{re.escape(key)}:\s*(.*)$", text)
    return match.group(1).strip() if match else ""


def extract_request(text: str) -> tuple[str, str]:
    lines = text.splitlines()
    in_request_block = False
    method = ""

    for line in lines:
        stripped = line.strip()
        match = re.match(r"^(get|post|put|delete|patch|head|options)\s*\{", stripped)
        if match:
            in_request_block = True
            method = match.group(1).upper()
            continue

        if in_request_block:
            if stripped == "}":
                break
            match = re.match(r"^url:\s*(.*)", stripped)
            if match:
                return method, match.group(1).strip()

    return method, ""


def host_marker(url: str) -> str:
    url = url.strip()
    if not url:
        return ""
    if url.startswith("{{"):
        return url.split("}}", 1)[0] + "}}"
    if url.startswith("{"):
        return url.split("}", 1)[0] + "}"
    if url.startswith(("http://", "https://")):
        return urlsplit(url).netloc
    if re.match(r"^[\w.-]+:\d+/", url):
        return url.split("/", 1)[0]
    if url.startswith("/"):
        return "(relative_abs)"
    return "(relative_odd)"


def normalize_path(url: str) -> str:
    url = url.strip()
    if not url:
        return ""

    if url.startswith(("http://", "https://")):
        parts = urlsplit(url)
        return re.sub(r"^/+", "/", parts.path or "/")

    url = re.sub(r"^\{\{[^}]+\}\}", "", url)
    url = re.sub(r"^\{[^}]+\}", "", url)

    if re.match(r"^[\w.-]+:\d+/", url):
        url = "/" + url.split("/", 1)[1]
    elif re.match(r"^[\w.-]+/", url):
        url = "/" + url.split("/", 1)[1]

    return re.sub(r"^/+", "/", url.split("?", 1)[0])


def query_string(url: str) -> str:
    url = url.strip()
    if not url:
        return ""
    if url.startswith(("http://", "https://")):
        return urlsplit(url).query
    if "?" not in url:
        return ""
    return url.split("?", 1)[1]


def suggested_base_var(url: str, top: str) -> str:
    host = host_marker(url)
    if host in HOST_VAR_MAP:
        return HOST_VAR_MAP[host]
    if host in {"{{api_url}}", "{{member_url}}"}:
        return "{{api_url}}"
    if host in {"{{admin_url}}", "{{admin_url_new}}", "{{admin_domain}}", "{{cur_admin_url}}"}:
        return "{{admin_url}}"
    if host in {"{{angency}}", "{{angency1}}"}:
        return "{{agency_url}}"
    if top == "前台":
        return "{{api_url}}"
    if top in {"后台", "合规", "游戏集成平台"}:
        return "{{admin_url}}"
    if top in {"代理后台", "代理管理后台"}:
        return "{{agency_url}}"
    return ""


def cleaned_url(url: str, top: str, api_path: str) -> str:
    if not url.strip() or not api_path or api_path == "body: none" or api_path.startswith("func "):
        return ""
    base_var = suggested_base_var(url, top)
    query = query_string(url)
    suffix = f"?{query}" if query else ""
    if base_var:
        return f"{base_var}{api_path}{suffix}"
    if api_path.startswith("/"):
        return f"{api_path}{suffix}"
    return ""


def has_hardcoded_env(url: str) -> bool:
    url = url.strip()
    if not url:
        return False
    if url.startswith(("{{", "{", "/")):
        return False
    return bool(re.match(r"^(https?://|[\w.-]+:\d+/|[\w.-]+\.)", url))


def risk_flags(relative_path: str, name: str, url: str, api_path: str) -> list[str]:
    blob = f"{relative_path} {name}".lower()
    flags: list[str] = []

    if any(token in blob for token in ["弃用", "废", "deprecated"]):
        flags.append("deprecated")
    if any(token in blob for token in ["老", "旧", "copy"]):
        flags.append("old_or_copy")
    if "todo" in blob:
        flags.append("todo")
    if "/v2" in api_path.lower():
        flags.append("url_v2")
    elif "v2" in blob:
        flags.append("name_v2")
    if has_hardcoded_env(url):
        flags.append("hardcoded_env")
    if url.strip() and host_marker(url) == "(relative_odd)":
        flags.append("odd_relative_url")
    if api_path in {"", "body: none"} or api_path.startswith("func "):
        flags.append("invalid_url")

    return flags


def classify_p0(top: str, relative_path: str, api_path: str, flags: list[str]) -> tuple[bool, str]:
    if "deprecated" in flags or "invalid_url" in flags:
        return False, ""

    blob = f"{top}/{relative_path} {api_path}".lower()
    matched_domains = []
    for domain, keywords in P0_KEYWORDS.items():
        if any(keyword in blob for keyword in keywords):
            matched_domains.append(domain)

    if not matched_domains:
        return False, ""

    if top == "前台":
        return True, ",".join(matched_domains)

    if any(part in relative_path for part in ["风控管理/存-提审核", "财务管理", "kyc", "KYC"]):
        return True, ",".join(matched_domains)

    return False, ",".join(matched_domains)


def collect_rows(source: Path) -> list[dict[str, str]]:
    rows = []
    for path in sorted(source.rglob("*.bru")):
        text = read_text(path)
        method, url = extract_request(text)
        relative_path = str(path.relative_to(source))
        parts = path.relative_to(source).parts
        top = parts[0] if len(parts) > 1 else "(root)"
        name = extract_meta(text, "name")
        api_path = normalize_path(url)
        flags = ["non_request"] if not method else risk_flags(relative_path, name, url, api_path)
        is_p0, p0_domain = classify_p0(top, relative_path, api_path, flags)
        base_var = suggested_base_var(url, top) if method else ""

        rows.append(
            {
                "file": relative_path,
                "top_domain": top,
                "name": name,
                "method": method,
                "url": url,
                "host": host_marker(url),
                "path": api_path,
                "suggested_base_var": base_var,
                "clean_url": cleaned_url(url, top, api_path) if method else "",
                "flags": ",".join(flags),
                "p0_candidate": "yes" if is_p0 else "",
                "p0_domain": p0_domain,
            }
        )
    return rows


def write_csv(rows: list[dict[str, str]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "file",
        "top_domain",
        "name",
        "method",
        "host",
        "path",
        "suggested_base_var",
        "clean_url",
        "flags",
        "p0_candidate",
        "p0_domain",
        "url",
    ]
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def table(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    header = rows[0]
    body = rows[1:]
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    lines.extend("| " + " | ".join(item.replace("|", "\\|") for item in row) + " |" for row in body)
    return "\n".join(lines)


def write_markdown(rows: list[dict[str, str]], source: Path, csv_output: Path, output: Path) -> None:
    http_rows = [row for row in rows if row["method"]]
    request_rows = [row for row in http_rows if "invalid_url" not in row["flags"]]
    flag_counter = Counter(flag for row in rows for flag in row["flags"].split(",") if flag)
    top_counter = Counter(row["top_domain"] for row in rows)
    method_counter = Counter(row["method"] or "NO_METHOD" for row in rows)
    host_counter = Counter(row["host"] or "(empty)" for row in http_rows)
    clean_var_counter = Counter(row["suggested_base_var"] or "(empty)" for row in http_rows)
    p0_rows = [row for row in request_rows if row["p0_candidate"] == "yes"]

    summary_rows = [
        ["指标", "数量"],
        ["Bruno 文件", str(len(rows))],
        ["HTTP 请求", str(len(http_rows))],
        ["可用 URL 请求", str(len(request_rows))],
        ["非请求或未解析请求", str(len(rows) - len(http_rows))],
        ["URL 含 /v2", str(flag_counter["url_v2"])],
        ["文件名/目录含 v2 但 URL 非 /v2", str(flag_counter["name_v2"])],
        ["todo 标记", str(flag_counter["todo"])],
        ["弃用标记", str(flag_counter["deprecated"])],
        ["老接口或 copy 标记", str(flag_counter["old_or_copy"])],
        ["硬编码环境 URL", str(flag_counter["hardcoded_env"])],
        ["可归一到 {{api_url}}", str(clean_var_counter["{{api_url}}"])],
        ["可归一到 {{admin_url}}", str(clean_var_counter["{{admin_url}}"])],
        ["可归一到 {{agency_url}}", str(clean_var_counter["{{agency_url}}"])],
        ["P0 候选请求", str(len(p0_rows))],
    ]

    top_rows = [["业务域", "文件数"]] + [[key, str(value)] for key, value in top_counter.most_common(12)]
    method_rows = [["方法", "数量"]] + [[key, str(value)] for key, value in method_counter.most_common()]
    host_rows = [["Host/变量", "请求数"]] + [[key, str(value)] for key, value in host_counter.most_common(12)]
    clean_var_rows = [["建议变量", "请求数"]] + [[key, str(value)] for key, value in clean_var_counter.most_common()]

    p0_table_rows = [["业务域", "方法", "Path", "建议变量", "标记", "文件"]]
    for row in p0_rows[:80]:
        p0_table_rows.append(
            [
                row["p0_domain"],
                row["method"],
                row["path"],
                row["suggested_base_var"],
                row["flags"],
                row["file"],
            ]
        )

    flagged_rows = [["标记", "方法", "Path", "文件"]]
    for row in request_rows:
        if any(flag in row["flags"] for flag in ["deprecated", "old_or_copy", "todo", "invalid_url", "odd_relative_url"]):
            flagged_rows.append([row["flags"], row["method"], row["path"], row["file"]])
        if len(flagged_rows) >= 80:
            break

    md = f"""# Bruno 接口资产扫描

扫描来源：`{source}`

全量明细：`{csv_output}`

## 总览

{table(summary_rows)}

## 业务域分布

{table(top_rows)}

## 方法分布

{table(method_rows)}

## Host 与环境变量分布

{table(host_rows)}

## 建议 URL 变量分布

{table(clean_var_rows)}

## 初步判断

- 该集合同时包含前台、后台、活动、合规、代理后台、游戏集成平台等多个业务域。
- `/v2` 不能只按 URL 判断；有些新版模块体现在文件名或目录，例如 `Vipv2`。
- `todo`、`弃用`、`老页面`、`旧`、`copy`、硬编码环境 URL 都需要在正式自动化前单独复核。
- `client-fat.filbet2025.com`、`client-beta.filbet2025.com` 等客户端硬编码地址建议归一为 `{{{{api_url}}}}`。
- `admin-fat.filbet2025.com`、`admin-antd.filbet2025.com` 等后台硬编码地址建议归一为 `{{{{admin_url}}}}`。
- P0 候选应先从前台登录注册、财务、游戏、KYC、会员信息，以及后台风控和财务审核相关接口中筛选。

## P0 候选接口

以下是按规则初筛的前 80 条 P0 候选，仍需人工确认是否仍在线上使用、是否有副作用、是否适合自动化。

{table(p0_table_rows)}

## 需复核接口样本

以下是带 `todo`、弃用、老接口、异常相对路径等标记的样本。全量请查看 CSV。

{table(flagged_rows)}
"""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(md, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        default="/Users/rayleigh/API/FB/filbet",
        help="Path to the Bruno collection",
    )
    parser.add_argument(
        "--csv",
        default="api/inventory/interfaces.csv",
        help="CSV output path",
    )
    parser.add_argument(
        "--md",
        default="api/inventory/interfaces.md",
        help="Markdown summary output path",
    )
    args = parser.parse_args()

    source = Path(args.source).expanduser().resolve()
    if not source.exists():
        raise SystemExit(f"source path does not exist: {source}")

    rows = collect_rows(source)
    csv_output = Path(args.csv).resolve()
    md_output = Path(args.md).resolve()
    write_csv(rows, csv_output)
    write_markdown(rows, source, csv_output, md_output)
    print(f"scanned {len(rows)} .bru files")
    print(f"wrote {csv_output}")
    print(f"wrote {md_output}")


if __name__ == "__main__":
    main()
