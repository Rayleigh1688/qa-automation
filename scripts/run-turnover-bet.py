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
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


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
    parser.add_argument("--env", default=".env")
    parser.add_argument("--phone", default="")
    parser.add_argument("--otp", default="")
    parser.add_argument("--bet-unit", type=int, default=1000)
    parser.add_argument("--max-spins", type=int, default=20)
    parser.add_argument("--game-id", default="beanstalk_243")
    parser.add_argument("--game-page", default="/s-game-page/17453877442826")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--out", default="ui/results/turnover-bet-plan.json")
    args = parser.parse_args()

    load_env_file(Path(args.env))
    phone = args.phone or os.environ.get("BET_CLIENT_PHONE") or os.environ.get("WRITE_CLIENT_PHONE") or os.environ.get("CLIENT_PHONE", "")
    otp = args.otp or os.environ.get("BET_CLIENT_OTP") or os.environ.get("WRITE_CLIENT_OTP") or os.environ.get("CLIENT_OTP", "")
    if not phone or not otp:
        raise SystemExit("phone and otp are required")
    if args.bet_unit <= 0 or args.max_spins <= 0:
        raise SystemExit("bet unit and max spins must be positive")

    before = unfinished_turnover(phone)
    planned_spins = math.ceil(before / Decimal(args.bet_unit)) if before > 0 else 0
    if planned_spins > args.max_spins:
        raise SystemExit(
            f"planned spins {planned_spins} exceed safety cap {args.max_spins}; "
            "raise --max-spins only after reviewing balance and turnover"
        )

    completed = False
    if args.execute and planned_spins > 0:
        ui_env = os.environ.copy()
        ui_env.update({
            "CLIENT_PHONE": phone,
            "CLIENT_OTP": otp,
            "CLIENT_GAME_ID": args.game_id,
            "CLIENT_GAME_PAGE_PATH": args.game_page,
            "CLIENT_GAME_BET_AMOUNT": str(args.bet_unit),
            "CLIENT_GAME_SPIN_COUNT": str(planned_spins),
            "EXECUTE_BET": "true",
            "CLIENT_REUSE_P0_AUTH": "true",
            "CLIENT_AUTH_MODE": "password",
        })
        subprocess.run(["npm", "run", "test:ui:game-bet"], env=ui_env, check=True)
        completed = True

    after = unfinished_turnover(phone) if completed else before
    result = {
        "phone_suffix": phone[-4:],
        "bet_unit": args.bet_unit,
        "turnover_before": str(before),
        "planned_spins": planned_spins,
        "executed": completed,
        "turnover_after": str(after),
        "turnover_cleared": after == 0,
    }
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    if completed and after > 0:
        raise SystemExit(f"turnover remains after UI bets: {after}")


if __name__ == "__main__":
    main()
