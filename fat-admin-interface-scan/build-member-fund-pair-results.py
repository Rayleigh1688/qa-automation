#!/usr/bin/env python3
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
CREDIT = json.loads((RESULTS / "record-flow-member-kyc-reject-credit-pair-retry.json").read_text())
RECOVERY = json.loads((RESULTS / "record-flow-member-kyc-reject-wallet-recovery.json").read_text())
TOKEN = json.loads((RESULTS / "record-flow-member-kyc-reject-fund-pair-flow.json").read_text())

credit = CREDIT["branches"]["credit_debit"]
recovery = RECOVERY["branches"]["credit_debit"]
token = TOKEN["branches"]["token_topup_withdrawal"]
credit_event = credit["credit"]["event"]
debit_event = recovery["debit_recovery"]["event"]

columns = [
    "surface", "menu", "page", "route", "control_type", "action", "method", "path",
    "query_fields", "path_fields", "body_fields", "header_fields", "parameter_sources",
    "http_status", "business_status", "response_structure", "auth_role", "permission_id",
    "side_effect", "before_state", "after_state", "restored_state", "doc_category", "doc_name",
    "doc_source", "classification", "currently_used", "evidence", "exception_or_blocker",
]

common = {
    "surface": "admin", "menu": "Member Management", "page": "Member Detail",
    "route": "/member-center/detail/{uid}", "control_type": "button",
    "query_fields": "", "path_fields": "uid", "header_fields": "authenticated browser session headers (values not persisted)",
    "auth_role": "authenticated FAT admin with member finance permissions", "permission_id": "40202",
}

rows = [
    {**common, "action": "Credit or Debit → Credit Top-up", "method": credit_event["method"], "path": credit_event["path"],
     "body_fields": "|".join(credit_event["body_fields"]),
     "parameter_sources": "action=selected Credit Top-up; amount=UI 0.01; bet_multiplier=UI 0; plats=UI All Games; remark=current-run reason; uid=detail route; google_code=runtime approval TOTP",
     "http_status": credit_event["http_status"], "business_status": credit_event["business_status"], "response_structure": "decoded data string; values not persisted",
     "side_effect": "+0.01 member wallet credit", "before_state": "wallet=0", "after_state": "wallet=0.01", "restored_state": "wallet=0 after matching Debit",
     "doc_category": "admin/finance", "doc_name": "余额调整 | 添加手动上下分-wesley", "doc_source": "api/inventory/interfaces.csv; api/catalog/admin/finance.csv",
     "classification": "ACTIVE", "currently_used": "yes", "evidence": "record-flow-member-kyc-reject-credit-pair-retry.json; dynamic-fields.json; wallet-recovery.json",
     "exception_or_blocker": "Initial submit was blocked before Network until required Turnover Venue/Game Restrictions=All Games was selected; no write occurred on that attempt"},
    {**common, "action": "Credit or Debit → Debit Deduction (restore)", "method": debit_event["method"], "path": debit_event["path"],
     "body_fields": "|".join(debit_event["body_fields"]),
     "parameter_sources": "action=selected Debit Deduction; amount=UI 0.01; remark=current-run recovery reason; uid=detail route; google_code=runtime approval TOTP",
     "http_status": debit_event["http_status"], "business_status": debit_event["business_status"], "response_structure": "decoded data string; values not persisted",
     "side_effect": "-0.01 member wallet debit restoring prior credit", "before_state": "wallet=0.01", "after_state": "wallet=0", "restored_state": "wallet=0; exact original baseline restored",
     "doc_category": "admin/finance", "doc_name": "余额调整 | 添加手动上下分-wesley", "doc_source": "api/inventory/interfaces.csv; api/catalog/admin/finance.csv",
     "classification": "ACTIVE", "currently_used": "yes", "evidence": "record-flow-member-kyc-reject-wallet-recovery.json",
     "exception_or_blocker": "Debit form correctly omits Credit-only turnover fields"},
    {**common, "action": "Credit/Debit Records verification", "method": "POST", "path": "/admin/finance/adjust/list",
     "body_fields": "", "parameter_sources": "uid from selected detail record; list defaults from UI",
     "http_status": 200, "business_status": True, "response_structure": "object keys d|s|t; one matching row observed after each write",
     "side_effect": "none (read-only log)", "before_state": "not queried in this subflow", "after_state": "1 row observed", "restored_state": "1 row observed after restore",
     "doc_category": "admin/finance", "doc_name": "系统调整", "doc_source": "api/inventory/interfaces.csv",
     "classification": "ACTIVE", "currently_used": "yes", "evidence": "credit-pair-retry.json; wallet-recovery.json",
     "exception_or_blocker": "A separate inventory entry documents GET for the same path; this UI used POST"},
    {**common, "permission_id": "100313", "action": "View Token Wallet", "method": "POST", "path": "/admin/finance/tokens/transaction/list",
     "body_fields": "", "parameter_sources": "uid/current detail context and UI list defaults; request body could not be decoded to fields in this observation",
     "http_status": 200, "business_status": False, "response_structure": "decoded data string; no rows; response values not persisted",
     "side_effect": "none", "before_state": "tokens_balance=0.00000000", "after_state": "unchanged", "restored_state": "not applicable",
     "doc_category": "admin/finance", "doc_name": "代币账变列表", "doc_source": "api/inventory/interfaces.csv documents GET; current UI emitted POST",
     "classification": "ACTIVE_FAILED", "currently_used": "yes", "evidence": "record-flow-member-kyc-reject-fund-pair-flow.json",
     "exception_or_blocker": "HTTP 200 but business=false; stopped Token branch and did not attempt adjustment"},
    {**common, "permission_id": "100315", "action": "Token Top-Up and Withdrawal", "method": "", "path": "/admin/finance/tokens/adjust",
     "body_fields": "", "parameter_sources": "form mapped: adjustment type, token amount, reason, runtime approval TOTP, uid from detail route",
     "http_status": "", "business_status": "", "response_structure": "not observed",
     "side_effect": "none", "before_state": "tokens_balance=0.00000000", "after_state": "unchanged", "restored_state": "not required",
     "doc_category": "admin/finance", "doc_name": "代币上下分", "doc_source": "api/inventory/interfaces.csv; api/catalog/admin/finance.csv",
     "classification": "DOCUMENTED_UNVERIFIED", "currently_used": "control present, request not triggered", "evidence": "token form probe; fund-pair-flow.json",
     "exception_or_blocker": "BLOCKED_UPSTREAM_BUSINESS_FAILURE: Token Wallet list returned business=false, so no Top-Up or Withdrawal was attempted"},
]

with (RESULTS / "record-flow-member-fund-pair-action-endpoint.csv").open("w", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=columns)
    writer.writeheader(); writer.writerows(rows)

summary = {
    "captured_at": RECOVERY["captured_at"], "environment": "FAT", "target_ref": "FAT-KYC-REJECT-01", "uid_ref": "FAT-UID-KYC-REJECT-01",
    "scope": "Member Detail Credit/Debit and Token Wallet reversible pair",
    "wallet_pair": {
        "status": "EXECUTED_RESTORED", "amount": "0.01", "writes_confirmed": 2,
        "state_chain": ["wallet=0", "wallet=0.01", "wallet=0"], "restored": True,
        "write_endpoint": "POST /admin/finance/adjust/insert", "log_endpoint": "POST /admin/finance/adjust/list",
        "credit_body_fields": credit_event["body_fields"], "debit_body_fields": debit_event["body_fields"],
    },
    "token_pair": {
        "status": "BLOCKED_UPSTREAM_BUSINESS_FAILURE", "writes_confirmed": 0, "state": "tokens_balance=0.00000000 unchanged",
        "failed_endpoint": "POST /admin/finance/tokens/transaction/list", "http_status": 200, "business_status": False,
        "adjust_endpoint": "POST /admin/finance/tokens/adjust", "adjust_request_triggered": False,
    },
    "unique_observed_endpoints": ["POST /admin/finance/adjust/insert", "POST /admin/finance/adjust/list", "POST /admin/finance/tokens/transaction/list"],
    "classifications": {"ACTIVE": 2, "ACTIVE_FAILED": 1, "DOCUMENTED_UNVERIFIED": 1},
    "raw_phone_or_uid_persisted": False, "secrets_persisted": False,
}
(RESULTS / "record-flow-member-fund-pair-summary.json").write_text(json.dumps(summary, indent=2) + "\n")

report = f"""# FAT Member Detail Fund Pair Result

- Target: `FAT-KYC-REJECT-01` / `FAT-UID-KYC-REJECT-01` (repository-safe references only)
- Wallet Credit/Debit: **EXECUTED_RESTORED**; `0 → 0.01 → 0`; two confirmed successful UI writes.
- Wallet endpoint: `POST /admin/finance/adjust/insert`; verification: `POST /admin/finance/adjust/list` plus detail/wallet reread.
- Token Top-Up/Withdrawal: **BLOCKED_UPSTREAM_BUSINESS_FAILURE**; `POST /admin/finance/tokens/transaction/list` returned HTTP 200 / business false. No token adjustment request or side effect occurred.
- Final state: wallet restored to the original value; token balance unchanged.

The first Credit attempt was stopped by a front-end validation requiring **Turnover Venue/Game Restrictions**. A read-only form probe identified the dynamic tree and its `所有游戏` (All Games) option. The single permitted retry selected it and succeeded. The matching Debit form omitted Credit-only turnover fields; after correcting that UI-field assumption, the recovery request succeeded.
"""
(RESULTS / "record-flow-member-fund-pair-report.md").write_text(report)
print(json.dumps({"rows": len(rows), **summary["wallet_pair"], "token_status": summary["token_pair"]["status"]}))
