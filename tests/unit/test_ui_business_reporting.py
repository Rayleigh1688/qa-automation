from support import ROOT, SCRIPTS
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from ui_business_artifacts import prepare_business_artifacts
from ui_business_report import collect_assertions, render_report


def save(root, path, value):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value))


class UiBusinessReporting(unittest.TestCase):
    def test_completed_stage_without_evidence_is_not_a_passing_assertion(self):
        with tempfile.TemporaryDirectory() as directory:
            rows = collect_assertions({'completed': ['kyc_ui'], 'status': 'PASS'}, Path(directory))
            self.assertTrue(all(r['status'] == 'NOT_RECORDED' for r in rows if r['phase'] == 'kyc_ui'))
            self.assertTrue(all(r['status'] == 'NOT_RUN' for r in rows if r['phase'] != 'kyc_ui'))

    def test_stale_kyc_and_game_evidence_is_not_linked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            save(root, 'ui/results/client-kyc-submit.json', {'runId': 'old', 'beforeStatus': 0})
            save(root, 'ui/results/client-game-bet-smoke.json', {'scannedAt': '2020-01-01T00:00:00Z', 'paidEvidence': {'paidBetRecords': 3, 'accepted': True}})
            state = {'completed': ['kyc_ui', 'bet_ui'], 'kycRunId': 'current', 'status': 'PASS', 'startedAt': 1800000000, 'finishedAt': 1800000010, 'paidBetTarget': 3}
            rows = collect_assertions(state, root)
            self.assertFalse(any(r['status'] == 'PASS' for r in rows))

    def test_free_branch_untriggered_and_mismatch_visible_and_html_escaped(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            save(root, 'ui/results/game-round-state.json', {'events': [{'ts': 2000, 'state': 'ready'}]})
            state = {'completed': ['bet_ui', 'bet_reconcile'], 'status': 'PASS', 'stage': 'complete', 'startedAt': 1, 'finishedAt': 3, 'paidBetTarget': 3, 'betReconciliation': {'betAmount': '200'}}
            rows = collect_assertions(state, root)
            self.assertEqual(next(r for r in rows if '免费旋转' in r['name'])['status'], 'NOT_TRIGGERED')
            self.assertEqual(next(r for r in rows if '付费金额合计' in r['name'])['status'], 'FAIL')
            state['assertions'] = [{'name': 'safe', 'status': 'PASS', 'expected': '<script>', 'actual': '<img>', 'detail': 'evidence'}]
            render_report(state, root)
            html = (root / 'ui/reports/ui-business-report.html').read_text()
            self.assertIn('<th>期望值</th><th>实际值</th>', html)
            self.assertIn('&lt;script&gt;', html)
            self.assertIn('&lt;img&gt;', html)

    def test_changed_support_digest_does_not_supply_old_account_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            save(root, 'api/results/ui-fund-support.json', [{'name': 'fund_kyc', 'data': {'kyc_status': 5}}, {'name': 'admin_deposit_manual_success', 'deposit_id': 'order'}])
            rows = collect_assertions({'completed': ['fund_preflight'], 'status': 'PASS', 'depositId': 'order', 'supportSha256': 'different'}, root)
            self.assertEqual(rows[0]['status'], 'NOT_RECORDED')


class LatestUiArtifacts(unittest.TestCase):
    def test_fresh_run_cleans_nested_images_and_only_ui_owned_api_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for path in ['ui/results/screenshots/old.png', 'ui/reports/old.html', 'test-results/old/video.webm', 'playwright-report/old.html', 'api/results/ui-fund-support.json', 'api/results/operations/ui-kyc-approve.json', 'api/results/api-only.json']:
                save(root, path, {})
            prepare_business_artifacts(root=root)
            self.assertFalse((root / 'ui/results/screenshots/old.png').exists())
            self.assertFalse((root / 'test-results/old/video.webm').exists())
            self.assertFalse((root / 'ui/reports/old.html').exists())
            self.assertFalse((root / 'api/results/ui-fund-support.json').exists())
            self.assertTrue((root / 'api/results/api-only.json').exists())
            save(root, 'ui/results/screenshots/current.png', {})
            prepare_business_artifacts(root=root)
            self.assertFalse((root / 'ui/results/screenshots/current.png').exists())

    def test_resume_preserves_all_same_run_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            save(root, 'ui/results/checkpoint.json', {'deposit': 'one'})
            save(root, 'ui/results/screenshots/current.png', {})
            prepare_business_artifacts(root=root, resume=True)
            self.assertTrue((root / 'ui/results/checkpoint.json').exists())
            self.assertTrue((root / 'ui/results/screenshots/current.png').exists())

    def test_linked_kyc_preserved_but_mismatch_does_not_clean(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = {'runId': 'current', 'status': 'APPROVED', 'startedAt': datetime.now(timezone.utc).isoformat()}
            for path in ['ui/results/client-kyc-submit.json', 'ui/results/kyc-ui-run-status.json', 'ui/results/old.json']:
                save(root, path, payload)
            with self.assertRaises(RuntimeError):
                prepare_business_artifacts(root=root, kyc_run_id='wrong')
            self.assertTrue((root / 'ui/results/old.json').exists())
            prepare_business_artifacts(root=root, kyc_run_id='current')
            self.assertTrue((root / 'ui/results/client-kyc-submit.json').exists())
            self.assertFalse((root / 'ui/results/old.json').exists())

class TurnoverFailureReport(unittest.TestCase):
    def test_failed_guard_shows_values_and_withdrawal_stays_not_run(self):
        with tempfile.TemporaryDirectory() as directory:
            state = {'status': 'BLOCKED', 'stage': 'turnover_clear', 'completed': ['bet_ui'], 'turnover': {'baselineStatus': 'READY', 'beforeBets': '1800', 'afterBets': '1800'}}
            rows = collect_assertions(state, Path(directory))
            guard = next(r for r in rows if '降低流水' in r['name'])
            self.assertEqual((guard['status'], guard['actual']), ('FAIL', '1800'))
            self.assertTrue(all(r['status'] == 'NOT_RUN' for r in rows if r['phase'] == 'withdraw_ui'))

    def test_baseline_timeout_visible(self):
        with tempfile.TemporaryDirectory() as directory:
            rows = collect_assertions({'status': 'BLOCKED', 'stage': 'bet_baseline', 'turnover': {'baselineStatus': 'TIMEOUT'}}, Path(directory))
            baseline = next(r for r in rows if '流水已就绪' in r['name'])
            self.assertEqual((baseline['status'], baseline['actual']), ('FAIL', 'TIMEOUT'))
