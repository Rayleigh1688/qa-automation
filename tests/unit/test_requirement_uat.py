"""UAT requirement execution must stay isolated from FAT and fixed OTPs."""
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
from support import ROOT
from filbet.requirement_adapter import Adapter
from filbet.requirement_kyc import reserve_phone
from qa_core.plan_runner import execute


class RequirementUatTests(unittest.TestCase):
    def setUp(self):
        self.config = {'ADMIN_URL':'https://admin-antd.filbet.zone',
                       'API_URL':'https://client-beta.filbet.zone',
                       'ADMIN_EMAIL':'a@example.test','ADMIN_LOGIN_TOTP_SECRET':'test-a',
                       'ADMIN_APPROVAL_TOTP_SECRET':'test-a','REGISTER_OTP_SOURCE':'admin_sms'}
        self.overlay = {'ADMIN_URL':self.config['ADMIN_URL'],'ADMIN_EMAIL':'b@example.test',
                        'ADMIN_PASSWORD':'test-only','ADMIN_LOGIN_TOTP_SECRET':'test-b'}
        self.cases = [{'steps':[{'action':'method','method':'kyc_fixture','actor':'A'}]}]

    def adapter(self, config=None, story='ISOP-2027', env='.env.uat'):
        with patch('filbet.requirement_adapter.load_environment', return_value=config or self.config):
            return Adapter({'requirement':story},SimpleNamespace(env=env,allow_write=['kyc-review']),Path('/tmp/unused'))

    def test_uat_role_uses_own_overlay_and_reports_uat(self):
        a=self.adapter()
        with patch('filbet.requirement_adapter.read_values', return_value=self.overlay) as read:
            a.preflight(self.cases)
        self.assertEqual(a.environment,'UAT')
        read.assert_called_once_with('.env.uat.reviewer.local')
        self.assertEqual(a.reviewer['ADMIN_LOGIN_TOTP_SECRET'],'test-b')

    def test_mixed_hosts_other_stories_and_fixed_codes_rejected(self):
        for changed in [ {'API_URL':'https://client-fat.filbet2025.com'},
                         {'ADMIN_GOOGLE_CODE':'111111'}, {'REGISTER_OTP':'111111'},
                         {'CLIENT_OTP':'111111'}, {'REGISTER_OTP_SOURCE':'fixed'} ]:
            with self.subTest(changed=changed):
                a=self.adapter({**self.config,**changed})
                with self.assertRaises(ValueError):a.preflight(self.cases)
        with self.assertRaises(ValueError):self.adapter(story='ISOP-2028').preflight(self.cases)
        with self.assertRaises(ValueError):self.adapter(env='.env.fat').preflight(self.cases)

    def test_reviewer_cannot_inherit_a_secret_or_point_to_fat(self):
        for changed in [{'ADMIN_LOGIN_TOTP_SECRET':''},
                        {'ADMIN_URL':'https://admin-fat.filbet2025.com'},
                        {'ADMIN_EMAIL':'a@example.test'}, {'ADMIN_GOOGLE_CODE':'111111'}]:
            with self.subTest(changed=changed), patch('filbet.requirement_adapter.read_values',return_value={**self.overlay,**changed}):
                with self.assertRaises(ValueError):self.adapter().preflight(self.cases)

    def test_admin_can_use_existing_dynamic_approval_secret_fallback(self):
        config={**self.config,'ADMIN_LOGIN_TOTP_SECRET':''}
        with patch('filbet.requirement_adapter.read_values',return_value=self.overlay):
            self.adapter(config).preflight(self.cases)
        with self.assertRaises(ValueError):
            self.adapter({**config,'ADMIN_APPROVAL_TOTP_SECRET':''}).preflight(self.cases)

    def test_login_failure_is_not_repeated_for_later_cases(self):
        a=self.adapter()
        a.args.timeout=1;a.args.insecure=False
        with patch('filbet.requirement_adapter.Session') as session:
            session.return_value.login.side_effect=RuntimeError('login rejected')
            for _ in range(2):
                with self.assertRaises(RuntimeError):a.session('A')
            self.assertEqual(session.return_value.login.call_count,1)
        self.assertTrue(a.case_blocker(self.cases[0]))

    def test_known_precondition_failure_does_not_inflate_execution_errors(self):
        a=self.adapter()
        shared={'steps':[{'action':'method','actor':'A','method':'kyc_reuse_processed_ui'}]}
        query={'steps':[{'action':'api','actor':'A','contract':'read'}]}
        self.assertTrue(a.case_blocker(shared))
        a.fixture_preparation_failed=True
        self.assertTrue(a.case_blocker(shared))
        self.assertFalse(a.case_blocker(query))
        a.recovery_failed=True
        self.assertTrue(a.case_blocker(query))

    def test_phone_reservations_do_not_cross_environments(self):
        with tempfile.TemporaryDirectory() as directory:
            flow=SimpleNamespace(PHONE_CURSOR_DIR=Path(directory),load_phone_cursor=lambda p:'9000000001',
                 phone_cursor_path=lambda e:None,allocate_registration_phone=lambda args:(args.register_phone,{}))
            fat=SimpleNamespace(env='.env.fat');uat=SimpleNamespace(env='.env.uat')
            reserve_phone(flow,fat);reserve_phone(flow,fat);reserve_phone(flow,uat)
            self.assertEqual(fat.register_phone,'9000000003')
            self.assertEqual(uat.register_phone,'9000000002')

    def test_failed_registration_blocks_later_fixtures_but_allows_readonly(self):
        a=self.adapter()
        calls=[]
        def request(step,case_id):
            calls.append(case_id)
            if case_id=='first':
                a.fixture_preparation_failed=True
                raise RuntimeError('registration failed')
            return {'summary':'read only'}
        a.execute=request
        fixture={'actor':'A','id':'prepare','method':'kyc_fixture'}
        cases=[{'id':'first','variables':{},'steps':[fixture]},
               {'id':'second','variables':{},'steps':[fixture]},
               {'id':'query','variables':{},'steps':[{'actor':'A','id':'query'}]}]
        result=execute(cases,a,'offline')
        self.assertEqual([r['status'] for r in result],['ERROR','NOT_RUN','PASS'])
        self.assertEqual(calls,['first','query'])


if __name__ == '__main__': unittest.main()
