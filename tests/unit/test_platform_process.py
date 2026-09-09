from support import ROOT, SCRIPTS
"""Offline process regressions; real Windows kernel branches run only on Windows."""
import errno
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch
from qa_core import process_command as commands
from qa_core import windows_job, local_lock
from qa_core.process import run_ui_process



class PlatformProcessTests(unittest.TestCase):
    def test_python_and_playwright_preserve_literal_arguments(self):
        args = ['two words', '"quoted"', '%PATH%', '&', '$(false)', '中文', 'C:\\with space\\']
        self.assertEqual(commands.process_command(['python3', *args]), [sys.executable, *args])
        cmd = commands.process_command(['npx', 'playwright', 'test', *args])
        self.assertEqual(cmd[1:], [str(ROOT/'node_modules/playwright/cli.js'), 'test', *args])
        result = subprocess.run([sys.executable, str(ROOT/'scripts/run-local.py'), '--', sys.executable,
                                 '-c', 'import json,sys; print(json.dumps(sys.argv[1:]))', *args],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), args)

    def test_windows_lock_metadata_does_not_overlap_locked_byte(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'lock'
            backend = Mock(LK_NBLCK=1)
            backend.locking.side_effect = [None, OSError(errno.EACCES, 'busy'), OSError(errno.EACCES, 'busy')]
            with patch.object(local_lock, 'WINDOWS', True), patch.object(local_lock, 'msvcrt', backend, create=True):
                with local_lock.local_run_lock(path):
                    self.assertTrue(json.loads(path.read_bytes()[1:])['token'])
                    with local_lock.local_run_lock(path) as nested:
                        self.assertIsNone(nested)
                    with self.assertRaises(local_lock.LocalRunBusy):
                        with local_lock.local_run_lock(path, inherit=False):
                            pass
                self.assertEqual(backend.locking.call_count, 3)

    def test_windows_npm_uses_node_cli_without_shell(self):
        with tempfile.TemporaryDirectory(prefix='qa space ') as directory:
            cli = Path(directory)/'npm-cli.js'; cli.write_text('')
            with patch.object(commands, 'WINDOWS', True), patch.dict(os.environ, {'npm_execpath': str(cli)}):
                command = commands.process_command(['npm', 'run', 'example', '--', '&literal'])
                self.assertEqual(command[1:], [str(cli), 'run', 'example', '--', '&literal'])

    def test_active_venv_and_python_child_selection(self):
        # Fake venv path exercises runtime selection, using the current Python executable.
        with tempfile.TemporaryDirectory(prefix='qa 中文 venv ') as directory:
            subprocess.run([sys.executable, '-m', 'venv', '--without-pip', directory], check=True)
            expected = Path(directory)/('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
            env = {**os.environ, 'VIRTUAL_ENV': directory}
            env.pop('QA_PYTHON_EXECUTABLE', None)
            result = subprocess.run(['node', 'scripts/python-launcher.mjs', '-c',
                'import json,sys; print(json.dumps([sys.executable, sys.prefix]))'], env=env, text=True, capture_output=True, check=True)
            executable, prefix = json.loads(result.stdout)
            self.assertEqual(Path(executable).parent.resolve(), expected.parent.resolve())
            self.assertEqual(Path(prefix).resolve(), Path(directory).resolve())
            self.assertEqual(commands.process_environment({'QA_PYTHON_EXECUTABLE': 'stale'})['QA_PYTHON_EXECUTABLE'], sys.executable)

    def test_explicit_python_is_validated_without_leaking_its_value(self):
        env = {**os.environ, 'QA_PYTHON_EXECUTABLE': '/missing-private-sentinel/python'}
        result = subprocess.run(['node', 'scripts/python-launcher.mjs', '-c', 'print("MUST_NOT_RUN")'],
                                env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('source=QA_PYTHON_EXECUTABLE', result.stderr)
        self.assertIn('ENOENT', result.stderr)
        self.assertNotIn('private-sentinel', result.stderr)
        self.assertNotIn('MUST_NOT_RUN', result.stdout)

    def test_explicit_python_with_spaces_uses_current_interpreter(self):
        env = {**os.environ, 'QA_PYTHON_EXECUTABLE': sys.executable, 'VIRTUAL_ENV': '/missing-venv'}
        result = subprocess.run(['node', 'scripts/python-launcher.mjs', '-c',
                                 'import json,sys; print(json.dumps(sys.executable))'],
                                env=env, capture_output=True, text=True, check=True)
        self.assertEqual(Path(json.loads(result.stdout)).resolve(), Path(sys.executable).resolve())

    def test_owned_descendant_stops_after_leader_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            heartbeat = Path(directory)/'heartbeat'
            worker = 'import time,sys\nfrom pathlib import Path\np=Path(sys.argv[1])\nfor i in range(1000):\n p.write_text(str(i)); time.sleep(.02)'
            leader = 'import subprocess,sys,time\nfrom pathlib import Path\nsubprocess.Popen([sys.executable,"-c",sys.argv[2],sys.argv[1]])\nwhile not Path(sys.argv[1]).exists(): time.sleep(.01)'
            self.assertEqual(run_ui_process([sys.executable, '-c', leader, str(heartbeat), worker]).returncode, 0)
            before = heartbeat.read_text()
            time.sleep(.15)
            self.assertEqual(heartbeat.read_text(), before)

    def test_windows_assignment_failure_never_opens_gate_and_reaps_child(self):
        child = Mock()
        child.poll.return_value = None
        with patch.object(windows_job, 'Job') as job, patch.object(windows_job.subprocess, 'Popen', return_value=child), patch.object(windows_job.subprocess, 'CREATE_NEW_PROCESS_GROUP', 512, create=True), patch.object(windows_job.signal, 'SIGBREAK', 21, create=True), patch.object(windows_job.signal, 'signal'), patch.object(Path, 'touch') as gate:
            job.return_value.assign.side_effect = OSError('assignment failed')
            with self.assertRaises(OSError):
                windows_job.run_windows_process(['unused'], pass_fds=(123,))
            gate.assert_not_called()
            child.kill.assert_called_once()
            child.wait.assert_called_once()
            job.return_value.close.assert_called()

    def test_windows_interrupt_and_success_close_job_and_restore_handlers(self):
        for interrupted in (False, True):
            child = Mock()
            child.wait.side_effect = [KeyboardInterrupt(), 0] if interrupted else [7, 7]
            child.poll.return_value = 7
            with patch.object(windows_job, 'Job') as job, patch.object(windows_job.subprocess, 'Popen', return_value=child) as launch, patch.object(windows_job.subprocess, 'CREATE_NEW_PROCESS_GROUP', 512, create=True), patch.object(windows_job.signal, 'SIGBREAK', 21, create=True), patch.object(windows_job.signal, 'signal', return_value=signal.SIG_DFL) as handlers:
                if interrupted:
                    with self.assertRaises(KeyboardInterrupt):
                        windows_job.run_windows_process(['unused'])
                else:
                    self.assertEqual(windows_job.run_windows_process(['unused']).returncode, 7)
                job.return_value.assign.assert_called_once_with(child)
                job.return_value.terminate_and_wait.assert_called_once()
                self.assertNotIn('start_new_session', launch.call_args.kwargs)
                self.assertEqual(handlers.call_args.args, (21, signal.SIG_DFL))

    def test_recipes_preserve_existing_public_commands_and_short_circuit(self):
        recipes = json.loads((ROOT/'config/local-commands.json').read_text())
        self.assertEqual(recipes['test:p0:api'], [['python3', 'scripts/run-api-tests.py', 'p0']])
        result = subprocess.run([sys.executable, 'scripts/run-local.py', '--shell',
            "python3 -c 'raise SystemExit(9)' && python3 -c 'print(\"MUST_NOT_RUN\")'"], text=True, capture_output=True)
        self.assertEqual(result.returncode, 9)
        self.assertNotIn('MUST_NOT_RUN', result.stdout)
