"""API support for UI-created orders. Never creates deposits or withdrawals."""
from __future__ import annotations
import importlib.util
import os
import time
from decimal import Decimal
from pathlib import Path


def load_controlled():
    spec = importlib.util.spec_from_file_location('ui_controlled_support', Path(__file__).with_name('api-controlled-flow-runner.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def require_success(records):
    if not records or any(r.get('business_status') is not True or not isinstance(r.get('http_status'), int) or not 200 <= r['http_status'] < 300 for r in records):
        raise RuntimeError('API support operation failed; no later business action is allowed')


def require_order(order, order_id, uid, amount):
    if not isinstance(order, dict):
        raise RuntimeError('This-run UI order was not found')
    ids = [str(order.get(key) or '') for key in ('id', 'order_id', 'order_no', 'external_order_id', 'merchant_order_id', 'transaction_id')]
    if not order_id or str(order_id) not in ids or str(order.get('uid') or '') != str(uid):
        raise RuntimeError('UI order ID or fund account UID mismatch')
    if Decimal(str(order.get('amount'))) != Decimal(str(amount)):
        raise RuntimeError('UI order amount mismatch')


class FundApi:
    def __init__(self, env_file):
        self.c = load_controlled()
        self.c.smoke.load_env_file(Path(env_file))
        os.environ['CLIENT_PHONE'] = os.environ['WRITE_CLIENT_PHONE']
        os.environ['CLIENT_PASSWORD'] = os.environ['WRITE_CLIENT_PASSWORD']
        os.environ['CLIENT_AUTH_MODE'] = 'password'
        self.args = self.c.build_parser().parse_args(['--env', env_file, '--insecure', '--body-format', 'cbor'])
        self.args.client_phone = os.environ['WRITE_CLIENT_PHONE']
        self.args.client_otp = ''
        self.uid = ''
        self.records = []
        os.environ.pop('ADMIN_TOKEN', None)

    def record(self, records):
        self.records.extend(records)
        require_success(records)
        return records

    def fresh_client(self):
        os.environ.pop('API_TOKEN', None)
        self.record(self.c.client_login(self.args))

    def admin(self):
        self.record(self.c.admin_login(self.args))

    def query(self, path, name):
        response = self.c.smoke.request_once(self.c.row('GET', '{{api_url}}' + path), self.args.timeout, True)
        record = self.c.result_record(name, response)
        self.record([record])
        return record

    def wallet(self, name):
        record = self.c.query_wallet(self.args, name)
        self.record([record])
        if str(record.get('data', {}).get('uid') or '') != self.uid:
            raise RuntimeError('Wallet UID does not match fund account')
        return record

    def turnover(self):
        self.admin()
        record, remaining = self.c.query_admin_turnover(self.args, self.uid, 'ui_fund_turnover')
        self.record([record])
        if isinstance(record.get('data'), dict) and int(record['data'].get('t') or 0) > record.get('row_count', 0):
            raise RuntimeError('Turnover result is paginated; cannot prove zero remaining')
        return remaining

    def preflight(self, withdraw_amount, allow_turnover=False):
        self.fresh_client()
        detail = self.query('/member/kyc/detail', 'fund_kyc')['data']
        self.uid = str(detail.get('uid') or '')
        if not self.uid or detail.get('kyc_status') != 5:
            raise RuntimeError('Fund account must already be KYC approved')
        wallet = self.wallet('ui_fund_wallet_before')
        accounts = self.query('/finance/account/list', 'fund_accounts')['data']
        if not isinstance(accounts, list) or not any(a.get('status') == 1 for a in accounts):
            raise RuntimeError('Fund account has no active withdrawal account')
        if self.turnover() != 0 and not allow_turnover:
            raise RuntimeError('Fund account has pre-existing turnover; no deposit is allowed')
        return wallet

    def approve_ui_deposit(self, order_id, amount, wallet_before):
        self.fresh_client()
        client = self.c.check_client_deposit_list(self.args, order_id)
        self.record(client)
        # Client lists may omit UID; the fresh client session fixes that lane.
        client_order = client[-1].get('matched_order')
        require_order({**(client_order or {}), 'uid': (client_order or {}).get('uid', self.uid)}, order_id, self.uid, amount)
        self.admin()
        record, order = self.c.find_deposit_order(self.args, order_id)
        self.record([record])
        require_order(order, order_id, self.uid, amount)
        self.record(self.c.approve_deposit(self.args, order))
        after = self.c.wait_for_deposit_credit(self.args, wallet_before, str(amount))
        self.record([after])
        if Decimal(str(after['data']['balance'])) - Decimal(str(wallet_before['data']['balance'])) != Decimal(str(amount)):
            raise RuntimeError('Wallet credit is not exactly the UI deposit amount')
        return after

    def prepare_kyc_account(self):
        if not os.environ.get('REGISTER_PASSWORD'):
            raise RuntimeError('REGISTER_PASSWORD is required for a fresh KYC test account')
        self.admin()
        phone, allocation = self.c.allocate_registration_phone(self.args)
        self.records.append(allocation)
        self.args.register_phone = phone
        try:
            self.record(self.c.register_new_user(self.args))
        finally:
            self.args.client_phone = os.environ['WRITE_CLIENT_PHONE']
            os.environ['CLIENT_PHONE'] = os.environ['WRITE_CLIENT_PHONE']
            os.environ['CLIENT_PASSWORD'] = os.environ['WRITE_CLIENT_PASSWORD']
            os.environ.pop('API_TOKEN', None)
        # Registration is preparation only; KYC submission must still use UI.
        return {'KYC_CLIENT_PHONE': phone, 'KYC_CLIENT_PASSWORD': os.environ['REGISTER_PASSWORD'], 'KYC_CLIENT_UID': ''}

    def wait_deposit_turnover(self, order_id, amount, evidence, persist=lambda: None, timeout=60, interval=5):
        """Wait for this UI deposit's turnover, not just its wallet credit."""
        deadline = time.monotonic() + timeout
        evidence['baselineStatus'] = 'WAITING'
        evidence['baselinePolls'] = []
        while True:
            remaining = self.turnover()
            rows = self.records[-1].get('data', {}).get('d', [])
            matches = [r for r in rows if str(r.get('bill_no') or '') == str(order_id)]
            evidence['baselinePolls'].append({'remaining': str(remaining), 'matchedRows': len(matches)})
            persist()
            if matches:
                if len(matches) != 1:
                    raise RuntimeError('Ambiguous turnover rows for this UI deposit')
                row = matches[0]
                required = Decimal(str(row.get('turnover')))
                finished = Decimal(str(row.get('finished')))
                if (str(row.get('uid')) != self.uid or row.get('ty') != 3
                        or Decimal(str(row.get('bonus'))) != Decimal(str(amount))
                        or not required.is_finite() or required <= 0
                        or not finished.is_finite() or finished != 0
                        or row.get('state') != 1 or remaining < required):
                    raise RuntimeError('This UI deposit turnover baseline is invalid or already consumed')
                evidence.update(baselineStatus='READY', beforeBets=str(remaining), depositRequired=str(required), depositFinished=str(finished))
                persist()
                return remaining
            if time.monotonic() >= deadline:
                evidence['baselineStatus'] = 'TIMEOUT'
                persist()
                raise RuntimeError('Timed out waiting for this UI deposit turnover; UI betting blocked')
            time.sleep(min(interval, max(0, deadline - time.monotonic())))

    def clear_after_ui_bets(self, reconciliation, expected_bets, unit, turnover_before, evidence=None, persist=lambda: None):
        require_paid_bets(reconciliation, expected_bets, unit)
        evidence = evidence if evidence is not None else {}
        evidence.update(mode='admin_clear_after_ui_bets', beforeBets=str(turnover_before))
        before = self.turnover()
        evidence['afterBets'] = str(before)
        persist()
        if before >= turnover_before:
            raise RuntimeError(f'UI bets did not reduce turnover: {turnover_before} -> {before}; admin clear is blocked')
        if before > 0:
            if not os.environ.get('ADMIN_APPROVAL_TOTP_SECRET'):
                raise RuntimeError('Live approval TOTP is required for turnover clear')
            self.record(self.c.run_turnover_clear(self.args, self.uid))
        after = self.turnover()
        evidence.update(afterAdminClear=str(after), clearSkipped=before == 0)
        persist()
        if after != 0:
            raise RuntimeError('Turnover remains after admin clear; withdrawal blocked')
        return evidence

    def before_withdraw(self, amount):
        self.fresh_client()
        if self.turnover() != 0:
            raise RuntimeError('Turnover is not zero; UI withdrawal is blocked')
        wallet = self.wallet('ui_fund_wallet_before_withdraw')
        if Decimal(str(wallet['data']['withdrawable'])) < Decimal(str(amount)):
            raise RuntimeError('Insufficient withdrawable balance')
        return wallet

    def reconcile_ui_withdraw(self, order_id, amount):
        self.fresh_client()
        client = self.c.check_client_withdraw_list(self.args, order_id)
        self.record(client)
        client_order = client[-1].get('matched_order')
        require_order({**(client_order or {}), 'uid': (client_order or {}).get('uid', self.uid)}, order_id, self.uid, amount)
        self.admin()
        record, order = self.c.find_withdraw_order(self.args, order_id)
        self.record([record])
        require_order(order, order_id, self.uid, amount)
        if order.get('status') != 'under_review':
            raise RuntimeError('Withdrawal does not meet the current under_review acceptance criterion')
        return {'orderId': str(order_id), 'amount': str(amount), 'status': order['status'], 'sameUid': True}

    def transactions(self):
        data = self.query('/finance/transaction/list?time_flag=15&page=1&page_size=100', 'ui_fund_transactions')['data']
        if not isinstance(data, dict) or not isinstance(data.get('data'), list):
            raise RuntimeError('Transaction response shape changed')
        return data

    def bets(self):
        data = self.query('/member/game/bet/list?page_size=100&time_flag=0&page=1', 'ui_fund_bets')['data']
        return bet_rows(data)

    def reconcile_bets(self, baseline, wallet_before, spins, unit):
        self.fresh_client()
        old_ids = {str(r['id']) for r in baseline}
        for attempt in range(15):
            current = [r for r in self.bets() if str(r['id']) not in old_ids]
            total_bet = sum((Decimal(str(r['bet_amount'])) for r in current), Decimal(0))
            total_net = sum((Decimal(str(r['net_amount'])) for r in current), Decimal(0))
            wallet_after = self.wallet('ui_fund_wallet_after_bet')
            delta = Decimal(str(wallet_after['data']['balance'])) - Decimal(str(wallet_before['data']['balance']))
            paid = [r for r in current if Decimal(str(r['bet_amount'])) > 0]
            if (paid and len(paid) <= spins and all(Decimal(str(r['bet_amount'])) in (Decimal(0), Decimal(str(unit))) for r in current)
                and delta == total_net and all(r.get('status') == 1 for r in current)):
                return {'newRecords': len(current), 'uiClicks': spins, 'paidBetRecords': len(paid), 'zeroBetRecords': len(current) - len(paid), 'betAmount': str(total_bet), 'netAmount': str(total_net), 'walletDelta': str(delta), 'settled': True}
            if attempt < 14: time.sleep(2)
        raise RuntimeError('This-run settled bet amounts/net payout do not reconcile to wallet')

    def reconcile_transactions(self, baseline, wallet_before, started_at):
        for attempt in range(10):
            current = self.transactions()
            baseline_ids = {str(r['id']) for r in baseline['data']}
            new_rows = [r for r in current['data'] if str(r['id']) not in baseline_ids]
            expected_count = int(current['t']) - int(baseline['t'])
            wallet_after = self.wallet('ui_fund_wallet_final')
            delta = Decimal(str(wallet_after['data']['balance'])) - Decimal(str(wallet_before['data']['balance']))
            total = sum((Decimal(str(r['amount'])) for r in new_rows), Decimal(0))
            if expected_count > 0 and len(new_rows) == expected_count and total == delta: break
            if attempt == 9: raise RuntimeError('Transaction window is incomplete or wallet delta differs')
            time.sleep(2)
        for row in new_rows:
            require_client_ledger_row(row, self.uid)
        self.admin()
        deadline = time.monotonic() + 60
        ledger_polls = 0
        while True:
            ledger_polls += 1
            admin_rows = []
            # The endpoint filters one cash type. Read every type present in this run,
            # including betting, payout and withdrawal, not only deposit (2001).
            for cash_type in sorted({int(row['cash_type']) for row in new_rows}):
                response = self.c.smoke.request_once(self.c.row('POST', f'{{{{admin_url}}}}/admin/finance/transaction/list?cash_type={cash_type}&page=1&page_size=100', '{{admin_url}}'), self.args.timeout, True, {'uid': self.uid, 'start_time': (int(started_at) - 60) * 1000, 'end_time': (int(time.time()) + 300) * 1000}, 'cbor')
                record = self.c.result_record('ui_fund_admin_transactions', response)
                self.record([record])
                admin_rows.extend(self.c.list_rows(record['data']))
            by_id = {str(r.get('id')): r for r in admin_rows if str(r.get('uid')) == self.uid}
            if require_admin_ledger_matches(new_rows, by_id):
                break
            if time.monotonic() >= deadline:
                raise RuntimeError('This-run client transaction missing in admin ledger after 60s')
            time.sleep(min(5, max(0, deadline - time.monotonic())))
        return {'newRecords': len(new_rows), 'clientAdminMatched': len(new_rows), 'walletDelta': str(delta), 'transactionSum': str(total), 'clientUidSource': 'authenticated_wallet_when_row_uid_empty', 'adminLedgerPolls': ledger_polls}


def bet_rows(data):
    if isinstance(data, dict) and data.get('t') == 0 and data.get('d') is None:
        return []
    if not isinstance(data, dict) or not isinstance(data.get('d'), list):
        raise RuntimeError('Bet history response shape changed')
    return data['d']


def validate_deposit_resume(prior, ui, records, run_id, now):
    if prior.get('runId') != run_id or prior.get('status') != 'BLOCKED' or prior.get('stage') not in ('deposit_credit', 'bet_baseline', 'bet_ui'):
        raise RuntimeError('Resume is limited to this-run pre-bet deposit checkpoints')
    response = ui.get('depositResponse', {})
    if response.get('businessStatus') is not True or not ui.get('nonBonusConfirmed') or not prior.get('depositId') or response.get('orderId') != prior['depositId']:
        raise RuntimeError('Missing this-run non-bonus UI deposit evidence')
    if not 0 <= now - prior.get('startedAt', 0) <= 3600:
        raise RuntimeError('Deposit continuation is stale')
    approvals = [r for r in records if r.get('name') == 'admin_deposit_manual_success']
    if approvals:
        credited = [r for r in records if r.get('name') == 'wallet_after_deposit']
        amount = str(ui.get('depositRequest', {}).get('amount', ''))
        if (len(approvals) == 1 and approvals[0].get('business_status') is True
            and str(approvals[0].get('deposit_id')) == prior['depositId']
            and len(credited) == 1 and credited[0].get('business_status') is True
            and Decimal(str(credited[0].get('actual_balance_delta'))) == Decimal(amount)
            and ((prior.get('error') == 'RuntimeError: Bet history response shape changed'
                  and records[-1].get('name') == 'ui_fund_bets' and records[-1].get('data') == {'t': 0, 'wt': '0', 'bt': '0', 'd': None})
                 or (prior.get('stage') == 'bet_ui' and any(r.get('name') == 'ui_fund_bets' and r.get('business_status') is True for r in records)))):
            return 'credited'
        raise RuntimeError('A deposit approval was already attempted; do not retry the write')
    if not records or not records[-1].get('reason', '').startswith('deposit order not found:'):
        raise RuntimeError('Only a failed read-only order lookup may be resumed')
    return 'lookup'


def require_paid_bets(evidence, expected, unit):
    if (evidence.get('paidBetRecords') != expected or evidence.get('settled') is not True
            or Decimal(str(evidence.get('betAmount', -1))) != Decimal(expected * unit)):
        raise RuntimeError('Exact settled UI paid bets required before admin clear')


def require_client_ledger_row(row, uid):
    # FAT client rows retain an empty UID field; the authenticated wallet fixes
    # the lane. Nonempty mismatches and missing fields still fail. Admin UID is
    # always checked strictly during the ID/amount join.
    if str(row.get('uid')) not in ('', str(uid)) or Decimal(str(row['before_amount'])) + Decimal(str(row['amount'])) != Decimal(str(row['after_amount'])):
        raise RuntimeError('Client transaction UID or arithmetic mismatch')


def require_admin_ledger_matches(rows, by_id):
    missing = False
    for row in rows:
        matched = by_id.get(str(row['id']))
        if matched is None:
            missing = True
            continue
        if any(Decimal(str(matched.get(key))) != Decimal(str(row[key])) for key in ('amount', 'before_amount', 'after_amount')):
            raise RuntimeError('This-run client transaction differs from admin ledger')
    return not missing
