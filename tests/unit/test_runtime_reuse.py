from support import ROOT, SCRIPTS
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from qa_core.export import export_runtime, CORE_FILES, JS_FILES
from qa_core.local_lock import local_run_lock, lock_path, LocalRunBusy
from qa_core.process_command import process_command
from qa_core.workflow import run_stages


class RuntimeReuseTests(unittest.TestCase):
    def test_export_runs_without_business_package_from_unicode_project(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)/'new 中文 project'
            manifest = export_runtime(target)
            self.assertEqual(len(manifest['files']), len(CORE_FILES)+len(JS_FILES)+1)
            self.assertFalse((target/'scripts/filbet').exists())
            self.assertFalse((target/'scripts/qa_core/contracts.py').exists())
            (target/'settings.env').write_text('PROJECT_VALUE=synthetic\n')
            entry = target/'scripts/check.py'
            entry.write_text('''from pathlib import Path
import sys
from qa_core.workflow import run_stages
from qa_core.environment import load_environment
from qa_core.reporting import write_html_report
root = Path(__file__).resolve().parents[1]
assert load_environment(root/'settings.env', environ={})['PROJECT_VALUE'] == 'synthetic'
write_html_report(title='Example', scope='LOCAL', report_kind='Example', verdict='PASS', verdict_detail='offline', items=[], output=root/'report.html')
assert not any(n == 'filbet' or n.startswith('filbet.') for n in sys.modules)
raise SystemExit(run_stages([['python', '-c', 'import sys; print("isolated-ok"); sys.exit(7)']], project_root=root, namespace='qa-runtime-export-test'))
''')
            env = dict(os.environ);env.pop('PYTHONPATH', None)
            result = subprocess.run([sys.executable, str(entry)], cwd=target, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 7, result.stderr)
            self.assertIn('isolated-ok', result.stdout)
            self.assertTrue((target/'report.html').is_file())
            import hashlib
            for relative, digest in manifest['files'].items():
                self.assertEqual(hashlib.sha256((target/relative).read_bytes()).hexdigest(), digest)
            with self.assertRaises(FileExistsError):
                export_runtime(target)

    def test_namespaces_are_independent_and_legacy_default_is_unchanged(self):
        self.assertTrue(lock_path().name.startswith('qa-automation-'))
        with local_run_lock(namespace='qa-reuse-one'):
            with local_run_lock(namespace='qa-reuse-two'):
                with self.assertRaises(LocalRunBusy):
                    with local_run_lock(namespace='qa-reuse-one', inherit=False): pass
        with self.assertRaises(ValueError): lock_path('../escape')

    def test_workflow_validation_precedes_execution_and_does_not_mutate_recipe(self):
        recipe = [['FLAG=on', 'python', '-c', 'pass'], ['python', '-c', 'pass']]
        original = copy.deepcopy(recipe)
        with patch('qa_core.workflow.run_process') as run:
            run.return_value.returncode = 9
            self.assertEqual(run_stages(recipe, project_root=ROOT, namespace='qa-reuse-stages', env={'PATH': os.environ.get('PATH','')}, extra_args=['&literal']), 9)
            self.assertEqual(run.call_count, 1)
            self.assertEqual(run.call_args.kwargs['env']['FLAG'], 'on')
        self.assertEqual(recipe, original)
        with patch('qa_core.workflow.run_process') as run:
            with self.assertRaises(ValueError):run_stages([['python', '-c', 'pass'], []], project_root=ROOT)
            run.assert_not_called()

    def test_target_project_playwright_path_and_stage_environment(self):
        with tempfile.TemporaryDirectory(prefix='project space ') as directory:
            command = process_command(['npx', 'playwright', '--version'], project_root=directory)
            self.assertEqual(command[1], str(Path(directory).resolve()/'node_modules/playwright/cli.js'))
        with patch('qa_core.workflow.run_process') as run:
            run.return_value.returncode = 0
            run_stages([['FLAG=one','python','-V'],['python','-V']], project_root=ROOT, namespace='qa-reuse-env', env={}, extra_args=['two words'])
            self.assertNotIn('FLAG', run.call_args_list[1].kwargs['env'])
            self.assertEqual(run.call_args_list[1].args[0][-1], 'two words')

    def test_report_defaults_are_generic_and_legacy_adapter_preserves_copy(self):
        from qa_core.reporting import write_html_report
        from filbet.reporting import write_html_report as legacy_report
        with tempfile.TemporaryDirectory() as directory:
            evidence = {'checks': [{'name': 'synthetic', 'status': 'PASS', 'detail': 'ok'}]}
            before = copy.deepcopy(evidence)
            args = dict(title='Example', scope='LOCAL', report_kind='Example', verdict='PASS', verdict_detail='offline', items=[], evidence=evidence)
            generic = Path(directory)/'generic.html'
            legacy = Path(directory)/'legacy.html'
            write_html_report(**args, output=generic)
            legacy_report(**args, output=legacy)
            self.assertIn('断言核对', generic.read_text())
            self.assertNotIn('资金链', generic.read_text())
            self.assertIn('统一资金链核对', legacy.read_text())
            self.assertEqual(evidence, before)
