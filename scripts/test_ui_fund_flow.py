import unittest
from ui_fund_flow import require_order, require_success, load_controlled, validate_deposit_resume


class UiFundFlowGuards(unittest.TestCase):
    def test_order_must_match_id_uid_and_amount(self):
        row = {'id': 'order-this-run', 'uid': 'fund-uid', 'amount': '1200.00'}
        require_order(row, 'order-this-run', 'fund-uid', 1200)
        for key, value in [('id', 'historical-order'), ('uid', 'other-account'), ('amount', '1201')]:
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                require_order({**row, key: value}, 'order-this-run', 'fund-uid', 1200)
        with self.assertRaises(RuntimeError):
            require_order(None, 'order-this-run', 'fund-uid', 1200)

    def test_business_rejection_stops_support(self):
        for records in [[], [{'business_status': False}], [{'http_status': 200}], [{'business_status': True}, {'business_status': False}]]:
            with self.subTest(records=records), self.assertRaises(RuntimeError):
                require_success(records)

    def test_shared_parser_keeps_legacy_defaults_and_entry(self):
        parser = load_controlled().build_parser()
        args = parser.parse_args(['--env', '.env.fat', '--operation', 'deposit-check-client', '--deposit-id', 'current-order'])
        self.assertEqual(args.deposit_id, 'current-order')
        self.assertFalse(args.deposit)
        self.assertFalse(args.withdraw)

    def test_resume_cannot_repeat_an_approval_or_use_another_order(self):
        prior = {'runId': 'run', 'status': 'BLOCKED', 'stage': 'deposit_credit', 'depositId': 'order', 'startedAt': 100}
        ui = {'nonBonusConfirmed': True, 'depositResponse': {'businessStatus': True, 'orderId': 'order'}}
        records = [{'reason': 'deposit order not found: id=order'}]
        validate_deposit_resume(prior, ui, records, 'run', 200)
        for modified, evidence, now in [
            ({**prior, 'runId': 'other'}, records, 200),
            ({**prior, 'depositId': 'other-order'}, records, 200),
            (prior, records + [{'name': 'admin_deposit_manual_success', 'business_status': False}], 200),
            (prior, records, 3701),
        ]:
            with self.assertRaises(RuntimeError):
                validate_deposit_resume(modified, ui, evidence, 'run', now)

class FixedPaidBetGuards(unittest.TestCase):
    def test_clear_requires_exact_settled_paid_evidence(self):
        from ui_fund_flow import require_paid_bets, FundApi
        from unittest.mock import Mock
        evidence = {'paidBetRecords': 3, 'betAmount': '300', 'settled': True}
        require_paid_bets(evidence, 3, 100)
        for patch in [{'paidBetRecords': 2}, {'paidBetRecords': 4}, {'settled': False}, {'betAmount': '200'}]:
            with self.assertRaises(RuntimeError):
                require_paid_bets({**evidence, **patch}, 3, 100)
        api = FundApi.__new__(FundApi)
        api.turnover = Mock(return_value=1800)
        api.c = Mock()
        with self.assertRaisesRegex(RuntimeError, 'did not reduce'):
            api.clear_after_ui_bets(evidence, 3, 100, 1800)
        api.c.run_turnover_clear.assert_not_called()

    def test_client_empty_uid_requires_wallet_lane_and_exact_arithmetic(self):
        from ui_fund_flow import require_client_ledger_row
        row = {'uid': '', 'before_amount': '100.00', 'amount': '-10', 'after_amount': '90'}
        require_client_ledger_row(row, 'fund')
        require_client_ledger_row({**row, 'uid': 'fund'}, 'fund')
        for patch in [{'uid': 'other'}, {'uid': None}, {'after_amount': '100'}]:
            with self.assertRaises(RuntimeError):
                require_client_ledger_row({**row, **patch}, 'fund')

class DepositTurnoverBaseline(unittest.TestCase):
    def make_api(self, snapshots):
        from ui_fund_flow import FundApi
        from unittest.mock import Mock
        from decimal import Decimal
        api = FundApi.__new__(FundApi)
        api.uid, api.records = 'fund', []
        api.args = Mock()
        def query():
            remaining, rows = next(snapshots)
            api.records.append({'data': {'d': rows}})
            return Decimal(remaining)
        api.turnover = Mock(side_effect=query)
        return api

    def row(self, **changes):
        return dict({'bill_no': 'current', 'uid': 'fund', 'ty': 3, 'bonus': '1200', 'turnover': '1800', 'finished': '0', 'state': 1}, **changes)

    def test_waits_for_exact_deposit_even_with_old_remaining_turnover(self):
        from unittest.mock import patch, Mock
        api = self.make_api(iter([('1500', [self.row(bill_no='old')]), ('3300', [self.row()])]))
        evidence, persist = {}, Mock()
        with patch('ui_fund_flow.time.sleep') as sleep:
            self.assertEqual(api.wait_deposit_turnover('current', 1200, evidence, persist), 3300)
        sleep.assert_called_once()
        self.assertEqual(evidence['beforeBets'], '3300')
        self.assertEqual(evidence['baselineStatus'], 'READY')
        self.assertEqual(len(evidence['baselinePolls']), 2)
        self.assertGreaterEqual(persist.call_count, 2)

    def test_timeout_keeps_last_zero_observation(self):
        api = self.make_api(iter([('0', [])]))
        evidence = {}
        with self.assertRaisesRegex(RuntimeError, 'Timed out'):
            api.wait_deposit_turnover('current', 1200, evidence, timeout=0)
        self.assertEqual(evidence['baselineStatus'], 'TIMEOUT')
        self.assertEqual(evidence['baselinePolls'][-1]['remaining'], '0')

    def test_wrong_account_amount_consumed_or_duplicate_baseline_blocks(self):
        for rows in [[self.row(uid='other')], [self.row(bonus='1000')], [self.row(finished='100')], [self.row(), self.row()]]:
            with self.subTest(rows=rows), self.assertRaises(RuntimeError):
                self.make_api(iter([('1800', rows)])).wait_deposit_turnover('current', 1200, {})

    def test_clear_failure_preserves_observation_before_raising(self):
        from unittest.mock import Mock
        api = self.make_api(iter([('1800', [])]))
        api.c = Mock()
        evidence, saved = {}, []
        with self.assertRaisesRegex(RuntimeError, '1800 -> 1800'):
            api.clear_after_ui_bets({'paidBetRecords': 3, 'betAmount': '300', 'settled': True}, 3, 100, 1800, evidence, lambda: saved.append(dict(evidence)))
        self.assertEqual(saved[-1]['afterBets'], '1800')
        api.c.run_turnover_clear.assert_not_called()

    def test_clear_failure_after_request_preserves_nonzero_result(self):
        from unittest.mock import Mock, patch
        api = self.make_api(iter([('1500', []), ('1500', [])]))
        api.c, api.record = Mock(), Mock()
        evidence = {}
        with patch.dict('os.environ', {'ADMIN_APPROVAL_TOTP_SECRET': 'test-only'}):
            with self.assertRaisesRegex(RuntimeError, 'Turnover remains'):
                api.clear_after_ui_bets({'paidBetRecords': 3, 'betAmount': '300', 'settled': True}, 3, 100, 1800, evidence)
        self.assertEqual(evidence['afterAdminClear'], '1500')
        api.c.run_turnover_clear.assert_called_once()

class AdminLedgerArrival(unittest.TestCase):
    def test_only_missing_records_may_wait_and_differences_fail(self):
        from ui_fund_flow import require_admin_ledger_matches
        row = {'id': 'a', 'amount': '-1000', 'before_amount': '2000', 'after_amount': '1000'}
        self.assertFalse(require_admin_ledger_matches([row], {}))
        self.assertTrue(require_admin_ledger_matches([row], {'a': dict(row)}))
        with self.assertRaises(RuntimeError):
            require_admin_ledger_matches([row], {'a': {**row, 'amount': '-999'}})
