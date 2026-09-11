"""Sequential JSON-lines worker with bounded RPC and owned descendant cleanup."""
import json
import os
import queue
import signal
import subprocess
import threading
from qa_core.process_command import process_command, process_environment


class JsonWorker:
    def __init__(self, command, *, cwd):
        self.job = None
        self.closed = False
        self.previous_term = None
        self.child = subprocess.Popen(process_command(command, project_root=cwd), cwd=cwd,
            env=process_environment(), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, encoding='utf-8', start_new_session=os.name != 'nt')
        if os.name == 'nt':
            from qa_core.windows_job import Job
            self.job = Job()
            # The Node entry does no work before the first stdin command.
            try: self.job.assign(self.child)
            except BaseException:
                self.job.close(); self.child.kill(); self.child.wait(); raise
        self.lines = queue.Queue()
        def reader():
            try:
                for line in self.child.stdout: self.lines.put(line)
            finally: self.lines.put(None)
        self.reader = threading.Thread(target=reader, daemon=True)
        self.reader.start()
        if threading.current_thread() is threading.main_thread():
            self.previous_term = signal.getsignal(signal.SIGTERM)
            def interrupted(signum, frame):
                raise KeyboardInterrupt('UI worker interrupted')
            signal.signal(signal.SIGTERM, interrupted)

    def call(self, value, timeout=60):
        if self.closed: raise RuntimeError('worker is closed')
        try:
            self.child.stdin.write(json.dumps(value)+'\n')
            self.child.stdin.flush()
            line = self.lines.get(timeout=timeout)
            if line is None: raise RuntimeError('worker exited')
            return json.loads(line)
        except (queue.Empty, BrokenPipeError, ValueError):
            self.close()
            raise RuntimeError('worker response unavailable') from None

    def close(self):
        if self.closed: return
        self.closed = True
        previous_int = None
        if threading.current_thread() is threading.main_thread():
            previous_int = signal.getsignal(signal.SIGINT)
            if self.previous_term is None: self.previous_term = signal.getsignal(signal.SIGTERM)
            signal.signal(signal.SIGINT,signal.SIG_IGN)
            signal.signal(signal.SIGTERM,signal.SIG_IGN)
        try:
            self._close()
        finally:
            if previous_int is not None:
                signal.signal(signal.SIGINT,previous_int)
                signal.signal(signal.SIGTERM,self.previous_term)

    def _close(self):
        if self.child.stdin and not self.child.stdin.closed: self.child.stdin.close()
        try: self.child.wait(timeout=3)
        except subprocess.TimeoutExpired: pass
        try:
            if self.job:
                self.job.terminate_and_wait()
            elif os.name != 'nt':
                try: os.killpg(self.child.pid, signal.SIGKILL)
                except ProcessLookupError: pass
            elif self.child.poll() is None: self.child.kill()
        finally:
            if self.job: self.job.close(); self.job = None
            self.child.wait(timeout=5)
            self.reader.join(timeout=2)
            self.child.stdout.close()
