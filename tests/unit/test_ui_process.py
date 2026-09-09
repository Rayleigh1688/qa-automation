from support import ROOT, SCRIPTS
import os
import signal
import subprocess
import sys
import unittest
from unittest.mock import Mock, patch
from qa_core.process import run_ui_process


class UiProcessCleanup(unittest.TestCase):
    def test_real_success_and_failure_exit_codes(self):
        self.assertEqual(run_ui_process([sys.executable, '-c', 'pass']).returncode, 0)
        with self.assertRaises(subprocess.CalledProcessError) as error:
            run_ui_process([sys.executable, '-c', 'raise SystemExit(7)'], check=True)
        self.assertEqual(error.exception.returncode, 7)

    @unittest.skipIf(os.name == 'nt', 'POSIX process group branch')
    def test_interrupt_cleans_only_owned_group_and_restores_handler(self):
        child = Mock(pid=12345)
        child.wait.side_effect = KeyboardInterrupt
        with patch('qa_core.process.subprocess.Popen') as launch, patch('qa_core.process.os.killpg', side_effect=[None, ProcessLookupError]) as kill, patch('qa_core.process.signal.signal') as handler, patch('qa_core.process.signal.getsignal', return_value=signal.SIG_DFL):
            launch.return_value.__enter__.return_value = child
            with self.assertRaises(KeyboardInterrupt):
                run_ui_process(['test-stage'])
            self.assertTrue(launch.call_args.kwargs['start_new_session'])
            self.assertEqual(kill.call_args_list[0].args, (12345, signal.SIGTERM))
            self.assertEqual(handler.call_args.args, (signal.SIGTERM, signal.SIG_DFL))
