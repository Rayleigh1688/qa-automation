"""A stalled delivery stage must time out and release its process tree."""
import subprocess
import sys
import time
import unittest
from support import ROOT
from qa_core.process import run_process


class DeliveryProcessTimeoutTests(unittest.TestCase):
    def test_stage_timeout_is_bounded(self):
        started = time.monotonic()
        with self.assertRaises(subprocess.TimeoutExpired):
            run_process([sys.executable, '-c', 'import time; time.sleep(30)'],
                        project_root=ROOT, timeout=0.2, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.assertLess(time.monotonic() - started, 8)
