from support import ROOT, SCRIPTS
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from filbet.controlled import ControlledFlow
from filbet.ui_fund_flow import load_controlled


class ArchitectureTests(unittest.TestCase):
    def test_new_flow_has_independent_approval_and_report_state(self):
        with patch('filbet.smoke.request_once', side_effect=AssertionError('unexpected I/O')):
            first, second = load_controlled(), load_controlled()
        first.LAST_APPROVAL_CODE = 'used'
        first.ACTIVE_RECORDS = [{'name': 'previous'}]
        first.OPERATION_REPORT_WRITTEN = True
        self.assertEqual(second.LAST_APPROVAL_CODE, '')
        self.assertIsNone(second.ACTIVE_RECORDS)
        self.assertFalse(second.OPERATION_REPORT_WRITTEN)
        self.assertEqual(first.PHONE_CURSOR_DIR, ROOT/'api/local-state')

    def test_exception_keeps_partial_records_and_redacts_error(self):
        flow = ControlledFlow()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'failure.json'
            flow.ACTIVE_ARGS = argparse.Namespace(operation='deposit-create', out=str(output), env='.env.fat')
            flow.ACTIVE_RECORDS = [{'name': 'earlier_step', 'business_status': True}]
            with patch.dict(os.environ, {'CLIENT_PASSWORD': 'secret-sentinel'}), patch.object(flow, 'main', side_effect=RuntimeError('failed secret-sentinel')):
                with self.assertRaisesRegex(SystemExit, 'failed <redacted>'):
                    flow.execute()
            rows = json.loads(output.read_text())
            self.assertEqual([r['name'] for r in rows], ['earlier_step', 'operation_error'])
            self.assertFalse(rows[-1]['business_status'])
            self.assertNotIn('secret-sentinel', output.read_text())
            self.assertTrue(output.with_suffix('.html').is_file())

    def test_kyc_lookup_uses_flow_client_and_fallback_matches_exact_uid(self):
        flow = ControlledFlow()
        args = argparse.Namespace(timeout=1, insecure=True, body_format='cbor')
        responses = [
            {'http_status': 200, 'decoded_body': {'status': True, 'data': []}},
            {'http_status': 200, 'decoded_body': {'status': True, 'data': [{'uid': 'other'}, {'uid': 'target'}]}},
        ]
        with patch.object(flow.smoke, 'request_once', side_effect=responses) as request:
            _, found = flow.find_kyc_record(args, 'target')
        self.assertEqual(found, {'uid': 'target'})
        self.assertEqual(request.call_count, 2)
        self.assertEqual(request.call_args_list[0].args[3]['uid'], 'target')
        self.assertNotIn('uid', request.call_args_list[1].args[3])

    def test_legacy_cli_help_remains_offline_and_compatible(self):
        for name in ('api-controlled-flow-runner.py', 'api-smoke-runner.py'):
            result = subprocess.run([sys.executable, str(SCRIPTS/name), '--help'],
                                    cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('--env', result.stdout)

    def test_legacy_shared_exports_refer_to_same_implementation(self):
        import ui_process
        import p0_report_template
        from qa_core import process
        from filbet import reporting
        self.assertIs(ui_process.run_ui_process, process.run_ui_process)
        self.assertIs(p0_report_template.write_html_report, reporting.write_html_report)
