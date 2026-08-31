#!/usr/bin/env python3
"""Reconcile artifacts produced by one controlled P0 fund flow.

This script never changes remote state. It links the deposit, UI bet/turnover,
wallet and withdrawal evidence created by the current run and emits one stable
JSON contract for the main-flow report.
"""

from __future__ import annotations

import argparse
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path


def load(path: str) -> object:
    source = Path(path)
    return json.loads(source.read_text(encoding="utf-8")) if source.is_file() else []


def records(value: object) -> dict[str, dict[str, object]]:
    if not isinstance(value, list):
        return {}
    return {
        str(item.get("name")): item
        for item in value
        if isinstance(item, dict) and item.get("name")
    }


def decimal(value: object) -> Decimal | None:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def add(checks: list[dict[str, object]], check_id: str, passed: bool, detail: str) -> None:
    checks.append({"id": check_id, "passed": bool(passed), "detail": detail})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--deposit", default="api/results/fund-flow-seed-result.json")
    parser.add_argument("--turnover", default="ui/results/turnover-bet-plan.json")
    parser.add_argument("--game", default="ui/results/client-game-bet-smoke.json")
    parser.add_argument("--withdraw", default="api/results/withdraw-result.json")
    parser.add_argument("--out", default="api/results/p0-reconciliation-result.json")
    args = parser.parse_args()

    deposit = records(load(args.deposit))
    withdraw = records(load(args.withdraw))
    turnover = load(args.turnover)
    game = load(args.game)
    checks: list[dict[str, object]] = []
    context: dict[str, object] = {}

    deposit_create = deposit.get("deposit_create", {})
    deposit_approve = deposit.get("admin_deposit_manual_success", {})
    wallet_before = deposit.get("wallet_before", {}).get("data", {})
    wallet_after = deposit.get("wallet_after", {}).get("data", {})
    deposit_data = deposit_create.get("data", {})
    deposit_id = str(deposit_data.get("order_id") or "") if isinstance(deposit_data, dict) else ""
    approved_id = str(deposit_approve.get("deposit_id") or "")
    deposit_amount = decimal(deposit_create.get("amount"))
    before_balance = decimal(wallet_before.get("balance")) if isinstance(wallet_before, dict) else None
    after_balance = decimal(wallet_after.get("balance")) if isinstance(wallet_after, dict) else None
    deposit_uid = str(wallet_after.get("uid") or "") if isinstance(wallet_after, dict) else ""
    add(checks, "deposit_created", bool(deposit_id and deposit_create.get("business_status") is True), f"deposit_id={deposit_id or '<missing>'}")
    add(checks, "deposit_admin_same_order", bool(deposit_id and deposit_id == approved_id and deposit_approve.get("business_status") is True), f"created={deposit_id or '<missing>'}, approved={approved_id or '<missing>'}")
    delta = after_balance - before_balance if before_balance is not None and after_balance is not None else None
    add(checks, "deposit_wallet_delta", bool(delta is not None and deposit_amount is not None and delta == deposit_amount), f"delta={delta}, expected={deposit_amount}")
    context.update({"uid": deposit_uid, "deposit_id": deposit_id, "deposit_amount": str(deposit_amount) if deposit_amount is not None else ""})

    turnover_data = turnover if isinstance(turnover, dict) else {}
    game_data = game if isinstance(game, dict) else {}
    planned = int(turnover_data.get("planned_spins") or 0)
    completed = int(turnover_data.get("completed_spins") or game_data.get("completedSpinCount") or 0)
    add(checks, "bet_executed", bool(turnover_data.get("executed") is True and planned > 0 and completed == planned), f"planned={planned}, completed={completed}")
    turnover_after = decimal(turnover_data.get("turnover_after"))
    add(checks, "turnover_cleared", turnover_data.get("turnover_cleared") is True and turnover_after == 0, f"before={turnover_data.get('turnover_before')}, after={turnover_data.get('turnover_after')}")
    context.update({"bet_unit": turnover_data.get("bet_unit"), "planned_spins": planned, "completed_spins": completed})

    withdraw_create = withdraw.get("withdraw_create", {})
    withdraw_data = withdraw_create.get("data", {})
    withdraw_id = str(withdraw_data.get("order_no") or withdraw_data.get("id") or "") if isinstance(withdraw_data, dict) else ""
    withdraw_amount = decimal(withdraw_create.get("amount"))
    withdraw_list = withdraw.get("admin_withdraw_risk_audit_list", {})
    withdraw_order = withdraw_list.get("matched_order", {})
    admin_withdraw_id = str(withdraw_order.get("id") or "") if isinstance(withdraw_order, dict) else ""
    admin_withdraw_amount = decimal(withdraw_order.get("amount")) if isinstance(withdraw_order, dict) else None
    withdraw_uid = str(withdraw_order.get("uid") or "") if isinstance(withdraw_order, dict) else ""
    add(checks, "withdraw_created", bool(withdraw_id and withdraw_create.get("business_status") is True), f"source=api, withdraw_id={withdraw_id or '<missing>'}")
    add(checks, "withdraw_admin_same_order", bool(withdraw_id and withdraw_id == admin_withdraw_id and withdraw_list.get("business_status") is True), f"created={withdraw_id or '<missing>'}, admin={admin_withdraw_id or '<missing>'}")
    add(checks, "withdraw_amount_matches", bool(withdraw_amount is not None and withdraw_amount == admin_withdraw_amount), f"client={withdraw_amount}, admin={admin_withdraw_amount}")
    add(checks, "withdraw_status_under_review", bool(isinstance(withdraw_order, dict) and withdraw_order.get("status") == "under_review"), f"status={withdraw_order.get('status') if isinstance(withdraw_order, dict) else '<missing>'}")
    add(checks, "flow_uid_matches", bool(deposit_uid and withdraw_uid and deposit_uid == withdraw_uid), f"deposit_uid={deposit_uid or '<missing>'}, withdraw_uid={withdraw_uid or '<missing>'}")
    context.update({"withdraw_id": withdraw_id, "withdraw_amount": str(withdraw_amount) if withdraw_amount is not None else "", "withdraw_status": withdraw_order.get("status") if isinstance(withdraw_order, dict) else ""})

    result = {
        "status": "PASS" if checks and all(item["passed"] for item in checks) else "FAIL",
        "context": context,
        "checks": checks,
    }
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] != "PASS":
        raise SystemExit("P0 flow reconciliation failed")


if __name__ == "__main__":
    main()
