#!/usr/bin/env python3
"""Normalize the curated P0 case index in real business-flow order.

The interface shortlist is discovery input only. It must not determine P0 scope
or execution order. This script keeps approved core cases, adds registered
negative/controlled cases, and writes one ordered test-cases.csv.
"""

from __future__ import annotations

import csv
from pathlib import Path


FIELDNAMES = [
    "case_order", "case_id", "scenario_id", "priority", "polarity", "domain",
    "flow_stage", "flow_stage_label", "account_lane", "case_name",
    "execution_policy", "method", "clean_url", "path", "suggested_base_var",
    "assertions", "source_file", "request_body", "notes",
]

FLOW_LABELS = {
    "01_register_login": "注册登录",
    "02_kyc": "KYC",
    "03_deposit": "充值",
    "04_bet": "投注",
    "05_bet_payout_record": "投注/派彩记录",
    "06_transaction_reconcile": "钱包与账变核对",
    "07_withdraw": "提现",
    "08_admin_reconcile": "后台权限、报表与总核对",
}

FLOW_SCENARIOS = {stage: f"MF-{index:03d}" for index, stage in enumerate(FLOW_LABELS, start=1)}

# Explicitly approved P0 read-only paths. The value is (flow, order in flow).
CORE_PATH_ORDER = {
    "/member/detail": ("01_register_login", 40),
    "/member/kyc/detail": ("02_kyc", 10),
    "/member/kyc/ekyc/info": ("02_kyc", 20),
    "/admin/kyc/pending/count": ("02_kyc", 40),
    "/admin/kyc/config/info": ("02_kyc", 50),
    "/admin/kyc/list": ("02_kyc", 60),
    "/finance/channel/list": ("03_deposit", 10),
    "/finance/deposit/list": ("03_deposit", 40),
    "/admin/finance/deposit/risk/list": ("03_deposit", 50),
    "/admin/finance/deposit/list": ("03_deposit", 70),
    "/member/v2/index": ("04_bet", 10),
    "/member/game/listRw": ("04_bet", 20),
    "/member/game/list/recommend": ("04_bet", 30),
    "/member/game/list/recent": ("04_bet", 40),
    "/member/game/list/history": ("04_bet", 50),
    "/member/game/bet/list": ("05_bet_payout_record", 20),
    "/finance/wallet": ("06_transaction_reconcile", 10),
    "/finance/transaction/types": ("06_transaction_reconcile", 20),
    "/finance/transaction/list": ("06_transaction_reconcile", 30),
    "/admin/finance/transaction/types": ("06_transaction_reconcile", 40),
    "/admin/finance/transaction/list": ("06_transaction_reconcile", 50),
    "/finance/account/list": ("07_withdraw", 10),
    "/finance/payment/bank/list": ("07_withdraw", 20),
    "/finance/payment/tab/list": ("07_withdraw", 30),
    "/finance/withdraw/list": ("07_withdraw", 50),
    "/admin/finance/withdraw/risk/audit/list": ("07_withdraw", 60),
    "/admin/finance/withdraw/list": ("07_withdraw", 80),
    "/admin/me/detail": ("08_admin_reconcile", 10),
    "/admin/priv/list": ("08_admin_reconcile", 20),
    "/admin/group/list": ("08_admin_reconcile", 30),
    "/admin/finance/payment/bank/list": ("08_admin_reconcile", 40),
}

NEGATIVE_CASES = [
    ("NTC-001", "01_register_login", 50, "auth", "OTP 错误时登录失败", "business_not_true,no_token"),
    ("NTC-002", "01_register_login", 60, "auth", "缺少 OTP 时登录失败", "business_not_true,no_token"),
    ("NTC-003", "01_register_login", 70, "auth", "未登录查询会员详情失败", "protected_rejected,no_key:data.uid"),
    ("NTC-004", "02_kyc", 80, "kyc", "未登录查询 KYC 详情失败", "protected_rejected,no_key:data.uid"),
    ("NTC-013", "02_kyc", 90, "kyc", "KYC 提交缺少必填字段失败", "business_not_true"),
    ("NTC-008", "03_deposit", 90, "finance", "不存在的充值通道不能下单", "business_not_true"),
    ("NTC-014", "03_deposit", 100, "finance", "充值金额低于通道最小限额失败", "business_not_true"),
    ("NTC-015", "03_deposit", 110, "finance", "充值金额高于通道最大限额失败", "business_not_true"),
    ("NTC-016", "03_deposit", 120, "finance", "非法充值记录筛选参数不导致 5xx", "no_5xx,decoded"),
    ("NTC-006", "04_bet", 80, "game", "非法游戏列表参数不导致 5xx", "no_5xx,decoded"),
    ("NTC-005", "06_transaction_reconcile", 80, "finance", "无效 token 查询钱包失败", "protected_rejected,no_key:data.uid"),
    ("NTC-009", "07_withdraw", 100, "finance", "低于最小金额或非法提款账户不能提现", "business_not_true"),
    ("NTC-010", "07_withdraw", 110, "finance", "非法提现记录筛选参数不导致 5xx", "no_5xx,decoded"),
    ("NTC-011", "08_admin_reconcile", 80, "admin", "无效后台 token 不能查询当前用户", "protected_rejected"),
    ("NTC-012", "08_admin_reconcile", 90, "admin", "后台报表非法时间范围不导致 5xx", "no_5xx,decoded"),
]

CONTROLLED_CASES = [
    ("CTC-001", "01_register_login", 10, "positive", "auth", "new_kyc_account", "新号注册成功", "controlled", "POST", "/member/register", "注册账号必须显式来自 090XXXXXXXX 测试池"),
    ("CTC-002", "01_register_login", 20, "positive", "auth", "mature_read_account", "现有成熟账号 OTP 登录成功", "setup", "POST", "/member/otp/login/v2", "safe smoke 的登录前置"),
    ("CTC-003", "02_kyc", 30, "positive", "kyc", "new_kyc_account", "新号或未通过/驳回账号提交 KYC", "planned_controlled", "POST", "/member/kyc/insert", "仅当当前非通过状态且接口允许再次提交时复用；待审状态单独验证"),
    ("CTC-004", "02_kyc", 70, "positive", "kyc", "admin_account", "后台定位并审核本次 KYC", "planned_controlled", "POST", "/admin/kyc/approve|/admin/kyc/reject", "只审核本次提交记录"),
    ("CTC-005", "03_deposit", 20, "positive", "finance", "fund_flow_account", "创建充值订单", "controlled", "GET", "/finance/payment/deposit", "与后续投注、流水核对和提现复用同一主流程账号"),
    ("CTC-006", "03_deposit", 60, "positive", "finance", "admin_account", "后台对本次充值单补单", "controlled", "POST", "/admin/finance/deposit/manual/success", "只操作本次自动化创建订单"),
    ("CTC-007", "04_bet", 60, "positive", "game", "fund_flow_account", "进入真实游戏并完成受控投注", "ui_controlled", "UI", "third-party-game", "复用充值账号；默认关闭，显式 EXECUTE_BET=true 才执行"),
    ("CTC-008", "05_bet_payout_record", 10, "positive", "game", "fund_flow_account", "等待投注结算或派彩完成", "planned_controlled", "WAIT", "bet-settlement", "必须关联本次投注单并等待流水异步统计"),
    ("CTC-009", "07_withdraw", 40, "positive", "finance", "fund_flow_account", "创建提现申请", "controlled", "GET", "/finance/payment/withdraw", "不参加活动；存款基础流水清零且余额、通道可用后执行正例"),
    ("CTC-010", "07_withdraw", 70, "positive", "finance", "admin_account", "后台审核并标记本次提现成功", "controlled", "POST", "/admin/finance/withdraw/agree|/admin/finance/withdraw/success", "不验证项目外实际到账"),
]

BLOCKED_CASES = [
    ("DTC-001", "02_kyc", 100, "已通过 KYC 的账号不能重复提交", "approved_kyc_account"),
    ("DTC-002", "07_withdraw", 120, "未完成 KYC 不能提现", "unverified_account"),
    ("DTC-003", "07_withdraw", 130, "余额不足不能提现", "low_balance_account"),
    ("DTC-004", "07_withdraw", 140, "参加活动且流水未完成时不能提现（独立专项，暂不阻塞主流程）", "restricted_activity_account"),
]


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def account_lane(row: dict[str, str]) -> str:
    if row.get("suggested_base_var") == "{{admin_url}}":
        return "admin_account"
    # safe_smoke uses one stable client session and proves contracts/structure.
    # Stateful correlation is represented by controlled cases with dedicated lanes.
    return "mature_read_account"


def normalized_safe_cases(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    selected: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        if row.get("execution_policy") != "safe_smoke" or row.get("path") not in CORE_PATH_ORDER:
            continue
        selected[(row["path"], row.get("suggested_base_var", ""))] = row
    result = []
    for row in selected.values():
        stage, within = CORE_PATH_ORDER[row["path"]]
        item = {field: row.get(field, "") for field in FIELDNAMES}
        item.update({
            "scenario_id": FLOW_SCENARIOS[stage], "polarity": "positive",
            "flow_stage": stage, "flow_stage_label": FLOW_LABELS[stage],
            "account_lane": account_lane(row), "execution_policy": "safe_smoke",
            "_within": within,
        })
        result.append(item)
    return result


def metadata_cases() -> list[dict[str, str]]:
    result = []
    for case_id, stage, within, polarity, domain, lane, name, policy, method, path, notes in CONTROLLED_CASES:
        result.append({
            "case_id": case_id, "scenario_id": FLOW_SCENARIOS[stage], "priority": "P0",
            "polarity": polarity, "domain": domain, "flow_stage": stage,
            "flow_stage_label": FLOW_LABELS[stage], "account_lane": lane,
            "case_name": name, "execution_policy": policy, "method": method,
            "clean_url": path, "path": path, "suggested_base_var": "",
            "assertions": "", "source_file": "curated-main-flow", "request_body": "",
            "notes": notes, "_within": within,
        })
    for case_id, stage, within, domain, name, assertion in NEGATIVE_CASES:
        result.append({
            "case_id": case_id, "scenario_id": FLOW_SCENARIOS[stage], "priority": "P0",
            "polarity": "negative", "domain": domain, "flow_stage": stage,
            "flow_stage_label": FLOW_LABELS[stage], "account_lane": "mature_read_account",
            "case_name": name, "execution_policy": "negative_smoke", "method": "DYNAMIC",
            "clean_url": "", "path": "", "suggested_base_var": "",
            "assertions": assertion, "source_file": "scripts/api-p0-negative-runner.py",
            "request_body": "", "notes": "反例请求由 negative runner 按 case_id 执行", "_within": within,
        })
    for case_id, stage, within, name, lane in BLOCKED_CASES:
        blocked_note = (
            "独立活动流水专项；暂不阻塞不参加活动的主正向链路"
            if case_id == "DTC-004"
            else "需要固定状态账号"
        )
        result.append({
            "case_id": case_id, "scenario_id": FLOW_SCENARIOS[stage], "priority": "P0",
            "polarity": "negative", "domain": "kyc" if stage == "02_kyc" else "finance",
            "flow_stage": stage, "flow_stage_label": FLOW_LABELS[stage], "account_lane": lane,
            "case_name": name, "execution_policy": "blocked_by_test_data", "method": "DYNAMIC",
            "clean_url": "", "path": "", "suggested_base_var": "", "assertions": "business_not_true,no_side_effect",
            "source_file": "curated-main-flow", "request_body": "",
            "notes": blocked_note, "_within": within,
        })
    return result


def main() -> None:
    path = Path("api/p0/test-cases.csv")
    rows = normalized_safe_cases(read_rows(path)) + metadata_cases()
    flow_index = {stage: index for index, stage in enumerate(FLOW_LABELS, start=1)}
    rows.sort(key=lambda row: (flow_index[row["flow_stage"]], int(row["_within"]), row["case_id"]))
    positive_index = 1
    for order, row in enumerate(rows, start=1):
        row["case_order"] = f"{order:03d}"
        if row["execution_policy"] == "safe_smoke":
            row["case_id"] = f"TC-{positive_index:03d}"
            positive_index += 1
        row.pop("_within", None)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {path.resolve()} ({len(rows)} total, {positive_index - 1} safe_smoke)")


if __name__ == "__main__":
    main()
