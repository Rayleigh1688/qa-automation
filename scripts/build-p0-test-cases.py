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
    "case_order", "case_id", "scenario_id", "priority", "polarity", "surface", "module", "domain",
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
    ("NTC-009", "07_withdraw", 100, "finance", "提现金额低于通道最小金额时不能生成订单", "business_not_true"),
    ("NTC-010", "07_withdraw", 110, "finance", "非法提现记录筛选参数不导致 5xx", "no_5xx,decoded"),
    ("NTC-011", "08_admin_reconcile", 80, "admin", "无效后台 token 不能查询当前用户", "protected_rejected"),
    ("NTC-012", "08_admin_reconcile", 90, "admin", "后台报表非法时间范围不导致 5xx", "no_5xx,decoded"),
]

CONTROLLED_CASES = [
    ("CTC-001", "01_register_login", 10, "positive", "auth", "new_kyc_account", "新号注册成功", "controlled", "POST", "/member/register", "注册账号必须显式来自 090XXXXXXXX 测试池"),
    ("CTC-002", "01_register_login", 20, "positive", "auth", "mature_read_account", "现有成熟账号密码登录成功", "setup", "SETUP", "client-login", "UI/API 默认密码登录；OTP 仅用于注册、首次设密和显式 OTP 专项"),
    ("CTC-003", "02_kyc", 30, "positive", "kyc", "new_kyc_account", "新号或未通过/驳回账号提交 KYC", "controlled", "POST", "/member/kyc/insert", "仅当当前非通过状态且接口允许再次提交时复用；待审状态单独验证"),
    ("CTC-004", "02_kyc", 70, "positive", "kyc", "admin_account", "后台定位并审核本次 KYC", "controlled", "POST", "/admin/kyc/approve|/admin/kyc/reject", "只审核本次提交记录"),
    ("CTC-005", "03_deposit", 20, "positive", "finance", "fund_flow_account", "创建充值订单", "controlled", "GET", "/finance/payment/deposit", "与后续投注、流水核对和提现复用同一主流程账号"),
    ("CTC-006", "03_deposit", 60, "positive", "finance", "admin_account", "后台对本次充值单补单", "controlled", "POST", "/admin/finance/deposit/manual/success", "只操作本次自动化创建订单"),
    ("CTC-007", "04_bet", 60, "positive", "game", "fund_flow_account", "进入真实游戏并完成受控投注", "ui_controlled", "UI", "third-party-game", "复用充值账号；默认关闭，显式 EXECUTE_BET=true 才执行"),
    ("CTC-008", "05_bet_payout_record", 10, "positive", "game", "fund_flow_account", "等待投注结算或派彩完成", "controlled", "WAIT", "bet-settlement", "已由流水轮询和本轮投注结果关联断言覆盖"),
    ("CTC-009", "07_withdraw", 40, "positive", "finance", "fund_flow_account", "通过 API 创建提现申请", "controlled", "GET", "/finance/payment/withdraw", "存款基础流水清零且余额、提款账户与通道可用后执行"),
    ("CTC-010", "07_withdraw", 70, "positive", "finance", "admin_account", "后台定位本次提现并记录审核状态", "controlled", "POST", "/admin/finance/withdraw/risk/audit/list", "FAT 当前以订单进入待审且前后台一致验收；真实出款恢复后增强复验"),
]

UI_STATE_CASES = [
    ("DTC-002", "07_withdraw", 120, "永久 BASIC 账号未完成 KYC 时不能提现", "permanent_unverified_account"),
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


def metadata_surface(lane: str, domain: str) -> str:
    return "admin" if lane == "admin_account" or domain == "admin" else "client"


def metadata_module(domain: str) -> str:
    return "permission" if domain == "admin" else domain


def normalized_safe_cases(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    selected: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        if row.get("execution_policy") != "safe_smoke" or row.get("path") not in CORE_PATH_ORDER:
            continue
        selected[(row["path"], row.get("suggested_base_var", ""))] = row
    result = []
    for row in selected.values():
        stage, within = CORE_PATH_ORDER[row["path"]]
        module = row.get("module") or row.get("domain", "other")
        if module == "admin":
            module = "permission"
        item = {field: row.get(field, "") for field in FIELDNAMES}
        item.update({
            "scenario_id": FLOW_SCENARIOS[stage], "polarity": "positive",
            "surface": row.get("surface") or ("admin" if row.get("suggested_base_var") == "{{admin_url}}" else "client"),
            "module": module,
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
            "polarity": polarity, "surface": metadata_surface(lane, domain),
            "module": metadata_module(domain), "domain": domain, "flow_stage": stage,
            "flow_stage_label": FLOW_LABELS[stage], "account_lane": lane,
            "case_name": name, "execution_policy": policy, "method": method,
            "clean_url": path, "path": path, "suggested_base_var": "",
            "assertions": "", "source_file": "curated-main-flow", "request_body": "",
            "notes": notes, "_within": within,
        })
    for case_id, stage, within, domain, name, assertion in NEGATIVE_CASES:
        policy = "known_defect_probe" if case_id in {"NTC-014", "NTC-015"} else "negative_smoke"
        result.append({
            "case_id": case_id, "scenario_id": FLOW_SCENARIOS[stage], "priority": "P0",
            "polarity": "negative", "surface": metadata_surface("", domain),
            "module": metadata_module(domain), "domain": domain, "flow_stage": stage,
            "flow_stage_label": FLOW_LABELS[stage], "account_lane": "mature_read_account",
            "case_name": name, "execution_policy": policy, "method": "DYNAMIC",
            "clean_url": "", "path": "", "suggested_base_var": "",
            "assertions": assertion, "source_file": "scripts/api-p0-negative-runner.py",
            "request_body": "", "notes": (
                "FAT 已确认缺陷探针，修复后显式复验，不阻塞默认 P0"
                if policy == "known_defect_probe"
                else "反例请求由 negative runner 按 case_id 执行"
            ), "_within": within,
        })
    for case_id, stage, within, name, lane in UI_STATE_CASES:
        result.append({
            "case_id": case_id, "scenario_id": FLOW_SCENARIOS[stage], "priority": "P0",
            "polarity": "negative", "surface": "client",
            "module": "kyc" if stage == "02_kyc" else "finance",
            "domain": "kyc" if stage == "02_kyc" else "finance",
            "flow_stage": stage, "flow_stage_label": FLOW_LABELS[stage], "account_lane": lane,
            "case_name": name, "execution_policy": "ui_controlled", "method": "UI",
            "clean_url": "", "path": "/my?action=withdraw", "suggested_base_var": "", "assertions": "security_requirements,no_withdraw_request",
            "source_file": "ui/cases/client-unverified-withdraw.spec.mjs", "request_body": "",
            "notes": "固定账号永久保持未 KYC 且不设置钱包密码；断言同时提示钱包密码和 KYC 前置", "_within": within,
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
