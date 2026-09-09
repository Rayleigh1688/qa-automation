"""FILBET turnover operations on one ControlledFlow instance."""
from __future__ import annotations
import argparse
import time
from decimal import Decimal


class TurnoverOperations:
    def remaining_turnover(self, rows: list[dict[str, object]]) -> Decimal:
        total = Decimal("0")
        for item in rows:
            if int(item.get("state") or 0) != 1:
                continue
            turnover = self.decimal_value(item.get("turnover")) or Decimal("0")
            finished = self.decimal_value(item.get("finished")) or Decimal("0")
            total += max(turnover - finished, Decimal("0"))
        return total


    def query_admin_turnover(self, 
        args: argparse.Namespace,
        uid: str,
        name: str,
    ) -> tuple[dict[str, object], Decimal]:
        rows = []
        seen = set()
        total = None
        record = None
        pages = []
        for page in range(1, 101):
            result = self.smoke.request_once(
                self.row("GET", f"{{{{admin_url}}}}/admin/finance/turnover/list?uid={uid}&page={page}&page_size=100", "{{admin_url}}"),
                args.timeout, args.insecure,
            )
            current = self.result_record(name, result)
            if record is None:
                record = current
            data = self.data_of(result)
            batch = self.list_rows(data)
            pages.append({'page': page, 'row_count': len(batch), 'http_status': current.get('http_status'), 'business_status': current.get('business_status')})
            reason = None
            count = data.get('t') if isinstance(data, dict) else None
            raw_rows = data.get('d') if isinstance(data, dict) else None
            # Confirmed empty response: d=null, t=0, s=0. Other malformed shapes still fail.
            if (isinstance(data, dict) and 'd' in data and raw_rows is None
                    and type(count) is int and count == 0
                    and type(data.get('s')) is int and data['s'] == 0):
                raw_rows = []
            if current.get('business_status') is not True or not 200 <= int(current.get('http_status') or 0) < 300:
                reason = 'Turnover page request failed'
            elif not isinstance(data, dict) or not isinstance(raw_rows, list) or not isinstance(count, int) or isinstance(count, bool) or count < 0:
                reason = 'Invalid turnover pagination shape'
            elif len(batch) != len(raw_rows):
                reason = 'Invalid non-object row in turnover page'
            elif total is not None and total != count:
                reason = 'Turnover total changed during pagination'
            else:
                total = count
                for item in batch:
                    ident = str(item.get('id') or '')
                    if not ident or ident in seen or str(item.get('uid') or '') != str(uid):
                        reason = 'Duplicate, missing ID or wrong UID in turnover pages'
                        break
                    seen.add(ident)
                if reason is None:
                    rows.extend(batch)
                    if len(rows) > total or (len(rows) < total and len(batch) != 100):
                        reason = 'Incomplete turnover page or inconsistent total'
            if reason:
                record.update(business_status=False, reason=reason, pagination_complete=False, pages=pages)
                return record, Decimal('0')
            if len(rows) == total:
                remaining = self.remaining_turnover(rows)
                record.update(data={'d': rows, 't': total, 's': len(rows)}, row_count=len(rows), remaining_turnover=str(remaining), pagination_complete=True, pages=pages)
                return record, remaining
        record.update(business_status=False, reason='Turnover pagination exceeded 100 pages', pagination_complete=False, pages=pages)
        return record, Decimal('0')


    def run_turnover_clear(self, 
        args: argparse.Namespace,
        uid: str,
        expected_locked: Decimal | None = None,
    ) -> list[dict[str, object]]:
        before_record, before = self.query_admin_turnover(args, uid, "turnover_before_clear")
        records = [before_record]
        if before_record.get("business_status") is not True:
            return records
        discovery_attempts = max(1, int(getattr(args, "turnover_discovery_attempts", 30)))
        discovery_interval = max(0.0, float(getattr(args, "turnover_discovery_interval", 1)))
        if expected_locked is not None and expected_locked > 0:
            for attempt in range(1, discovery_attempts + 1):
                before_record["discovery_attempts"] = attempt
                if before > 0 or int(before_record.get("row_count") or 0) > 0:
                    break
                if attempt < discovery_attempts:
                    time.sleep(discovery_interval)
                    before_record, before = self.query_admin_turnover(args, uid, "turnover_before_clear")
                    records[0] = before_record
                    if before_record.get("business_status") is not True:
                        return records
            if before == 0 and int(before_record.get("row_count") or 0) == 0:
                before_record["business_status"] = False
                before_record["reason"] = (
                    f"wallet remains locked={expected_locked} but no turnover record appeared "
                    f"within {discovery_attempts} attempts"
                )
                return records
        if before == 0:
            records.append({
                "name": "turnover_clear",
                "business_status": True,
                "skipped": True,
                "reason": "remaining turnover is already zero",
            })
            return records
        body = self.add_approval_code(
            {"uid": uid, "remark": args.turnover_clear_remark},
            args,
        )
        result = self.smoke.request_once(
            self.row("POST", "{{admin_url}}/admin/finance/turnover/clear", "{{admin_url}}"),
            args.timeout,
            args.insecure,
            body,
            "cbor",
            content_type="application/x-www-form-urlencoded",
        )
        records.append(self.result_record("turnover_clear", result))
        if not self.business_ok(result):
            return records
        attempts = max(1, int(getattr(args, "turnover_clear_attempts", 10)))
        interval = max(0.0, float(getattr(args, "turnover_clear_interval", 1)))
        after_record: dict[str, object] = {}
        after = before
        for attempt in range(1, attempts + 1):
            after_record, after = self.query_admin_turnover(args, uid, "turnover_after_clear")
            after_record["poll_attempts"] = attempt
            if after == 0 or attempt == attempts:
                break
            time.sleep(interval)
        after_record["business_status"] = after_record.get("business_status") is True and after == 0
        if after != 0:
            after_record["reason"] = f"remaining turnover is not zero after clear: {after}"
        records.append(after_record)
        return records


