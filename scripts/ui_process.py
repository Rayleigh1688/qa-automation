"""Own and reap a UI stage's process group, including browser descendants."""
import os
import signal
import subprocess
import time


def run_ui_process(command, **kwargs):
    check = kwargs.pop('check', False)
    # A fresh session keeps cleanup away from the terminal and other test runs.
    with subprocess.Popen(command, start_new_session=True, **kwargs) as child:
        previous = signal.getsignal(signal.SIGTERM)
        def interrupted(signum, frame):
            raise KeyboardInterrupt('UI stage terminated')
        signal.signal(signal.SIGTERM, interrupted)
        try:
            code = child.wait()
        finally:
            try:
                os.killpg(child.pid, signal.SIGTERM)
                deadline = time.monotonic() + 3
                while time.monotonic() < deadline:
                    child.poll()
                    try:
                        os.killpg(child.pid, 0)
                    except ProcessLookupError:
                        break
                    time.sleep(0.1)
                else:
                    os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            finally:
                signal.signal(signal.SIGTERM, previous)
        if check and code:
            raise subprocess.CalledProcessError(code, command)
        return subprocess.CompletedProcess(command, code)
