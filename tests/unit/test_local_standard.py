from support import ROOT, SCRIPTS
"""Offline regressions for configuration, lock ownership and doctor boundaries."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from qa_core.environment import load_environment
from qa_core.local_lock import local_run_lock, LocalRunBusy

spec = importlib.util.spec_from_file_location('doctor', ROOT / 'scripts/doctor.py')
doctor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(doctor)


class LocalStandardTests(unittest.TestCase):
    def test_layering_matches_node_and_preserves_shell_child_overrides(self):
        with tempfile.TemporaryDirectory() as directory:
            base, personal = Path(directory)/'base', Path(directory)/'personal'
            base.write_text('CLIENT_PHONE=base\nCLIENT_PASSWORD=base-pass\n')
            personal.write_text('CLIENT_PHONE=personal\nCLIENT_PASSWORD=\n')
            for precedence, expected in [('', 'personal'), ('shell', 'shell')]:
                env = {**os.environ, 'QA_ENV_LOCAL': str(personal), 'ENV_FILE_PRECEDENCE': precedence, 'CLIENT_PHONE': 'shell'}
                python = load_environment(base, environ=env)
                js = subprocess.run(['node', '--input-type=module', '-e',
                    "import {loadEnv} from './ui/framework/env.mjs'; loadEnv(process.argv[1]); console.log(JSON.stringify([process.env.CLIENT_PHONE,process.env.CLIENT_PASSWORD]));", str(base)], env=env, capture_output=True, text=True, check=True)
                self.assertEqual(python['CLIENT_PHONE'], expected)
                self.assertEqual(json.loads(js.stdout), [python['CLIENT_PHONE'], python['CLIENT_PASSWORD']])

    def test_missing_explicit_personal_file_fails_closed(self):
        with self.assertRaises(SystemExit):
            load_environment('missing', environ={'QA_ENV_LOCAL': '/missing-personal'}, required=False)

    def test_default_legacy_file_wins(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory)/'env'; file.write_text('X=file\n')
            self.assertEqual(load_environment(file, environ={'X': 'shell'})['X'], 'file')

    def test_lock_contends_reenters_and_releases_after_exception(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'lock'
            with self.assertRaisesRegex(RuntimeError, 'test'):
                with local_run_lock(path):
                    with local_run_lock(path) as nested:
                        self.assertIsNone(nested)
                    with self.assertRaises(LocalRunBusy):
                        with local_run_lock(path, inherit=False):
                            pass
                    env = {**os.environ, 'PYTHONPATH': str(ROOT/'scripts')}
                    env.pop('QA_LOCAL_LOCK_TOKEN', None)
                    result = subprocess.run([sys.executable, '-c', 'from qa_core.local_lock import local_run_lock\nimport sys\nwith local_run_lock(sys.argv[1]): pass', str(path)], env=env, capture_output=True)
                    self.assertNotEqual(result.returncode, 0)
                    raise RuntimeError('test')
            with local_run_lock(path, inherit=False) as fd:
                self.assertIsInstance(fd, int)

    def test_process_crash_releases_kernel_lock_without_deleting_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'lock'
            env = {**os.environ, 'PYTHONPATH': str(ROOT/'scripts')}
            result = subprocess.run([sys.executable, '-c',
                'from qa_core.local_lock import local_run_lock\nimport os,sys\nwith local_run_lock(sys.argv[1]): os._exit(4)', str(path)], env=env)
            self.assertEqual(result.returncode, 4)
            self.assertTrue(path.exists())
            with local_run_lock(path, inherit=False) as fd:
                self.assertIsInstance(fd, int)

    def test_lock_rejects_forged_inherited_token(self):
        with tempfile.TemporaryDirectory() as directory:
            with local_run_lock(Path(directory)/'lock'):
                with patch.dict(os.environ, {'QA_LOCAL_LOCK_TOKEN': 'wrong'}):
                    with self.assertRaises(LocalRunBusy):
                        with local_run_lock(Path(directory)/'lock'):
                            pass

    def test_npm_wrapper_forwards_literal_args_and_nested_lock(self):
        result = subprocess.run([sys.executable, 'scripts/run-local.py', '--shell',
            'python3 scripts/run-local.py -- python3 -c '+"'import sys; print(repr(sys.argv[1:])); sys.exit(7)'", '--', 'two words', '$(false)', ';'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 7, result.stderr)
        self.assertIn("['two words', '$(false)', ';']", result.stdout)

    def doctor_env(self):
        return {'API_URL': 'https://client-fat.invalid', 'ADMIN_URL': 'https://admin-fat.invalid', 'CLIENT_BASE_URL': 'https://client-fat.invalid', 'CLIENT_PHONE': 'fake-account', 'CLIENT_PASSWORD': 'secret-sentinel', 'ADMIN_EMAIL': 'fake-admin', 'ADMIN_PASSWORD': 'secret-admin', 'ADMIN_GOOGLE_CODE': 'fake-code'}

    def test_doctor_offline_and_network_opt_in(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory)/'.env.fat'; file.write_text(''); file.chmod(0o600)
            args = SimpleNamespace(env=str(file), scope='FAT', target='api', network=False)
            with patch.object(doctor, 'load_environment', return_value=self.doctor_env()), patch.object(doctor, 'probe', return_value=True) as probe:
                self.assertEqual(doctor.check(args), [])
                probe.assert_not_called()
                args.network = True
                self.assertEqual(doctor.check(args), [])
                self.assertEqual(probe.call_count, 3)

    def test_doctor_rejects_lane_collision_without_leaking_values_or_network(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory)/'.env.fat'; file.write_text(''); file.chmod(0o600)
            env = {**self.doctor_env(), 'WRITE_CLIENT_PHONE': '+639123456789', 'PRE_KYC_CLIENT_PHONE': '09123456789'}
            args = SimpleNamespace(env=str(file), scope='FAT', target='api', network=True)
            with patch.object(doctor, 'load_environment', return_value=env), patch.object(doctor, 'probe') as probe:
                failures = doctor.check(args)
                self.assertTrue(failures)
                for value in env.values():
                    self.assertNotIn(value, '\n'.join(failures))
                probe.assert_not_called()

    def test_environment_templates_share_schema_and_disable_writes(self):
        from qa_core.environment import read_values
        fat = read_values(ROOT/'config/environments/fat.env.example')
        uat = read_values(ROOT/'config/environments/uat.env.example')
        self.assertEqual(set(fat), set(uat))
        self.assertEqual(set(fat), set(read_values(ROOT/'.env.example')))
        for env in (fat, uat):
            for key in ('EXECUTE_BET', 'EXECUTE_DEPOSIT_CONTRACT', 'EXECUTE_WITHDRAW_UI'):
                self.assertEqual(env[key], 'false')
        self.assertEqual(uat['REGISTER_OTP_SOURCE'], 'admin_sms')


if __name__ == '__main__':
    unittest.main()
