#!/usr/bin/env python3
"""Build executable P0 API test cases from the P0 shortlist."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path


ASSERTION_PROFILES = {
    "/finance/channel/list": "status_true,data_list",
    "/finance/deposit/list": "status_true,data_object,keys:data.d|data.t|data.s",
    "/finance/payment/tab/list": "status_true,data_list",
    "/finance/transaction/list": "status_true,data_object,keys:data.data|data.t|data.s",
    "/finance/transaction/types": "status_true,data_list",
    "/finance/wallet": "status_true,data_object,keys:data.uid|data.balance|data.withdrawable|data.locked",
    "/finance/withdraw/list": "status_true,data_object,keys:data.d|data.t|data.s",
    "/member/game/bet/list": "status_true,data_object,keys:data.d|data.t",
    "/member/game/list/history": "status_true",
    "/member/game/list/recent": "status_true,data_object,keys:data.d|data.t|data.s",
    "/member/game/list/recommend": "status_true,data_object,keys:data.d|data.t|data.s",
    "/member/game/listRw": "status_true,data_object,keys:data.d|data.t|data.s",
    "/member/v2/index": "status_true,data_object,keys:data.banners",
    "/member/kyc/detail": "status_true,data_object,keys:data.uid|data.phone",
    "/member/detail": "status_true,data_object,keys:data.uid|data.username|data.phone",
    "/member/vip/level/detail": "status_true,data_object,keys:data.uid|data.level",
    "/promo/vip/config": "status_true,data_object",
    "/promo/vip/sign/in/config": "status_true,data_object,keys:data.level|data.ty",
}


CASE_NAMES = {
    "/finance/channel/list": "获取充值/提现渠道列表",
    "/finance/deposit/list": "查询会员充值记录",
    "/finance/payment/tab/list": "查询提现 tab 配置",
    "/finance/transaction/list": "查询会员账变记录",
    "/finance/transaction/types": "查询账变类型字典",
    "/finance/wallet": "查询会员钱包",
    "/finance/withdraw/list": "查询会员提现记录",
    "/member/game/bet/list": "查询会员游戏记录",
    "/member/game/list/history": "查询历史游戏",
    "/member/game/list/recent": "查询最近游戏",
    "/member/game/list/recommend": "查询推荐游戏",
    "/member/game/listRw": "查询新版游戏列表组合",
    "/member/v2/index": "查询新版首页游戏聚合",
    "/member/kyc/detail": "查询会员 KYC 详情",
    "/member/detail": "查询会员基础信息",
    "/member/vip/level/detail": "查询会员 VIP 等级详情",
    "/promo/vip/config": "查询新版 VIP 配置",
    "/promo/vip/sign/in/config": "查询新版 VIP 签到配置",
}


FLOW_STAGES = {
    "/member/kyc/detail": "02_kyc",
    "/finance/channel/list": "03_deposit",
    "/finance/deposit/list": "03_deposit_check",
    "/finance/payment/tab/list": "06_withdraw",
    "/finance/withdraw/list": "06_withdraw_check",
    "/member/v2/index": "04_bet",
    "/member/game/listRw": "04_bet",
    "/member/game/list/recommend": "04_bet",
    "/member/game/list/recent": "04_bet",
    "/member/game/list/history": "04_bet",
    "/member/game/bet/list": "05_payout_check",
    "/finance/wallet": "07_related_data_check",
    "/finance/transaction/list": "07_related_data_check",
    "/finance/transaction/types": "07_related_data_check",
    "/member/detail": "07_related_data_check",
    "/member/vip/level/detail": "07_related_data_check",
    "/promo/vip/config": "07_related_data_check",
    "/promo/vip/sign/in/config": "07_related_data_check",
}


FLOW_STAGE_LABELS = {
    "01_register_login": "注册登录",
    "02_kyc": "KYC",
    "03_deposit": "充值",
    "03_deposit_check": "充值相关数据检查",
    "04_bet": "投注",
    "05_payout_check": "派彩/投注相关数据检查",
    "06_withdraw": "提现",
    "06_withdraw_check": "提现相关数据检查",
    "07_related_data_check": "以上相关数据检查",
    "08_admin_report_approval": "后台报表展示和审批",
}


FLOW_ORDER = {stage: index for index, stage in enumerate(FLOW_STAGE_LABELS)}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(rows: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "case_id",
        "priority",
        "domain",
        "flow_stage",
        "flow_stage_label",
        "case_name",
        "execution_policy",
        "method",
        "clean_url",
        "path",
        "suggested_base_var",
        "assertions",
        "source_file",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
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


def write_markdown(rows: list[dict[str, str]], path: Path, csv_path: Path) -> None:
    domain_counter = Counter(row["domain"] for row in rows)
    summary = [
        ["指标", "数量"],
        ["P0 可执行用例", str(len(rows))],
        ["safe_smoke", str(sum(row["execution_policy"] == "safe_smoke" for row in rows))],
    ]
    domains = [["领域", "数量"]] + [[key, str(value)] for key, value in domain_counter.most_common()]
    case_rows = [["用例ID", "流程阶段", "领域", "用例", "方法", "Clean URL", "断言"]]
    for row in rows:
        case_rows.append(
            [
                row["case_id"],
                row["flow_stage_label"],
                row["domain"],
                row["case_name"],
                row["method"],
                row["clean_url"],
                row["assertions"],
            ]
        )

    path.write_text(
        f"""# P0 API 测试用例

来源：`api/p0-interface-shortlist.csv`

全量 CSV：`{csv_path.resolve()}`

## 总览

{table(summary)}

## 领域分布

{table(domains)}

## 用例清单

{table(case_rows)}
""",
        encoding="utf-8",
    )


def main() -> None:
    source = Path("api/p0-interface-shortlist.csv")
    csv_path = Path("api/p0-test-cases.csv")
    md_path = Path("api/p0-test-cases.md")

    cases = []
    for row in read_rows(source):
        if row["execution_policy"] != "safe_smoke":
            continue
        assertions = ASSERTION_PROFILES.get(row["path"])
        if not assertions:
            continue
        cases.append(
            {
                "case_id": f"TC-{len(cases) + 1:03d}",
                "priority": row["priority"],
                "domain": row["domain"],
                "flow_stage": FLOW_STAGES.get(row["path"], "07_related_data_check"),
                "flow_stage_label": FLOW_STAGE_LABELS.get(
                    FLOW_STAGES.get(row["path"], "07_related_data_check"),
                    "以上相关数据检查",
                ),
                "case_name": CASE_NAMES.get(row["path"], row["name"]),
                "execution_policy": row["execution_policy"],
                "method": row["method"],
                "clean_url": row["clean_url"],
                "path": row["path"],
                "suggested_base_var": row["suggested_base_var"],
                "assertions": assertions,
                "source_file": row["source_file"],
            }
        )

    cases.sort(key=lambda row: (FLOW_ORDER.get(row["flow_stage"], 999), row["domain"], row["path"]))
    for index, row in enumerate(cases, start=1):
        row["case_id"] = f"TC-{index:03d}"

    write_csv(cases, csv_path)
    write_markdown(cases, md_path, csv_path)
    print(f"wrote {csv_path.resolve()}")
    print(f"wrote {md_path.resolve()}")


if __name__ == "__main__":
    main()
