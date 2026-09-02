#!/usr/bin/env python3
"""Plan and optionally execute fixed-unit UI bets until current turnover is covered.

The database is queried read-only before and after Playwright. The script never
updates wallet, turnover, or member state directly.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import time
from decimal import Decimal
from pathlib import Path


def load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if os.environ.get("ENV_FILE_PRECEDENCE") == "shell":
            os.environ.setdefault(key, value)
        else:
            os.environ[key] = value


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"missing required environment variable: {name}")
    return value


def unfinished_turnover(phone: str) -> Decimal:
    if not phone.isdigit():
        raise SystemExit("client phone must contain digits only")
    sql = (
        "SELECT COALESCE(SUM(CASE WHEN t.state=1 "
        "THEN GREATEST(t.turnover-t.finished,0) ELSE 0 END),0) "
        "FROM fb_members_turnover t "
        "JOIN fb_members m ON m.uid=t.uid "
        f"WHERE m.phone='{phone}';"
    )
    command = [
        "mysql",
        "--connect-timeout=8",
        "-h", required("DB_HOST"),
        "-P", required("DB_PORT"),
        "-u", required("DB_USER"),
        required("DB_NAME"),
        "-N",
        "-e", sql,
    ]
    mysql_env = os.environ.copy()
    mysql_env["MYSQL_PWD"] = required("DB_PASSWORD")
    result = subprocess.run(command, env=mysql_env, check=True, capture_output=True, text=True)
    return Decimal(result.stdout.strip() or "0")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", default=os.environ.get("ENV_FILE", ".env.fat"))
    parser.add_argument("--phone", default="")
    parser.add_argument("--password", default="")
    parser.add_argument("--bet-unit", type=int)
    parser.add_argument("--max-spins", type=int, default=20)
    parser.add_argument("--poll-interval", type=float, default=5)
    parser.add_argument("--poll-timeout", type=float, default=60)
    parser.add_argument("--game-id", default="")
    parser.add_argument("--game-page", default="")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--out", default="ui/results/turnover-bet-plan.json")
    args = parser.parse_args()

    load_env_file(Path(args.env))
    args.bet_unit = args.bet_unit or int(os.environ.get("CLIENT_GAME_BET_AMOUNT", "1000"))
    args.game_id = args.game_id or os.environ.get("CLIENT_GAME_ID", "beanstalk_243")
    args.game_page = args.game_page or os.environ.get("CLIENT_GAME_PAGE_PATH", "/s-game-page/17453877442826")
    phone = args.phone or os.environ.get("BET_CLIENT_PHONE") or os.environ.get("WRITE_CLIENT_PHONE") or os.environ.get("CLIENT_PHONE", "")
    password = args.password or os.environ.get("BET_CLIENT_PASSWORD") or os.environ.get("WRITE_CLIENT_PASSWORD") or os.environ.get("CLIENT_PASSWORD", "")
    if not phone or not password:
        raise SystemExit("phone and password are required")
    if args.bet_unit <= 0 or args.max_spins <= 0:
        raise SystemExit("bet unit and max spins must be positive")

    before = unfinished_turnover(phone)
    initial_planned_spins = math.ceil(before / Decimal(args.bet_unit)) if before > 0 else 0
    if initial_planned_spins > args.max_spins:
        raise SystemExit(
            f"planned spins {initial_planned_spins} exceed safety cap {args.max_spins}; "
            "raise --max-spins only after reviewing balance and turnover"
        )

    executed = False
    total_planned = 0
    total_completed = 0
    batches: list[dict[str, object]] = []
    current = before
    while args.execute and current > 0:
        batch_spins = math.ceil(current / Decimal(args.bet_unit))
        if total_planned + batch_spins > args.max_spins:
            raise SystemExit(
                f"total planned spins {total_planned + batch_spins} exceed safety cap {args.max_spins}"
            )
        ui_env = os.environ.copy()
        ui_env.update({
            "CLIENT_PHONE": phone,
            "CLIENT_PASSWORD": password,
            "CLIENT_GAME_ID": args.game_id,
            "CLIENT_GAME_PAGE_PATH": args.game_page,
            "CLIENT_GAME_BET_AMOUNT": str(args.bet_unit),
            "CLIENT_GAME_SPIN_COUNT": str(batch_spins),
            "EXECUTE_BET": "true",
            "CLIENT_REUSE_P0_AUTH": "true",
            "CLIENT_AUTH_MODE": "password",
        })
        batch_before = current
        command = ["npm", "run", "test:ui:game-bet"]
        if os.environ.get("PRESERVE_UI_RESULTS") == "true":
            command = [
                "npx", "playwright", "test",
                "ui/cases/client-game-bet-smoke.spec.mjs", "--workers=1",
            ]
        subprocess.run(command, env=ui_env, check=True)
        game_result = json.loads(Path("ui/results/client-game-bet-smoke.json").read_text(encoding="utf-8"))
        completed_spins = int(game_result.get("completedSpinCount") or 0)
        total_planned += batch_spins
        total_completed += completed_spins
        executed = True

        deadline = time.monotonic() + args.poll_timeout
        observed = unfinished_turnover(phone)
        while observed > 0 and time.monotonic() < deadline:
            time.sleep(max(0.5, args.poll_interval))
            observed = unfinished_turnover(phone)
        batches.append({
            "turnover_before": str(batch_before),
            "planned_spins": batch_spins,
            "completed_spins": completed_spins,
            "turnover_after_poll": str(observed),
        })
        if observed >= batch_before:
            current = observed
            break
        current = observed

    after = current if executed else before
    result = {
        "phone_suffix": phone[-4:],
        "bet_unit": args.bet_unit,
        "turnover_before": str(before),
        "planned_spins": total_planned if executed else initial_planned_spins,
        "completed_spins": total_completed,
        "executed": executed,
        "turnover_after": str(after),
        "turnover_cleared": after == 0,
        "batches": batches,
    }
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    if executed and after > 0:
        raise SystemExit(f"turnover remains after UI bets: {after}")


if __name__ == "__main__":
    main()
