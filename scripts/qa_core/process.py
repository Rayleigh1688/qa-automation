"""Own and reap a UI stage's process group, including browser descendants."""
import os
import signal
import subprocess
import time
from qa_core.process_command import process_command, process_environment


def run_ui_process(command, **kwargs):
    check = kwargs.pop('check', False)
    project_root = kwargs.pop('project_root', None)
    command = process_command(command, project_root=project_root, environ=kwargs.get('env'))
    kwargs['env'] = process_environment(kwargs.get('env'))
    if os.name == 'nt':
        from qa_core.windows_job import run_windows_process
        result = run_windows_process(command, **kwargs)
        if check and result.returncode:
            raise subprocess.CalledProcessError(result.returncode, command)
        return result
    timeout = kwargs.pop('timeout', None)
    # A fresh session keeps cleanup away from the terminal and other test runs.
    with subprocess.Popen(command, start_new_session=True, **kwargs) as child:
        previous_int = signal.getsignal(signal.SIGINT)
        previous = signal.getsignal(signal.SIGTERM)
        def interrupted(signum, frame):
            raise KeyboardInterrupt('UI stage terminated')
        signal.signal(signal.SIGTERM, interrupted)
        try:
            code = child.wait(timeout=timeout)
        finally:
            # A second console interrupt must not abandon descendant cleanup.
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            try:
                os.killpg(child.pid, signal.SIGTERM)
                deadline = time.monotonic() + 3
                while time.monotonic() < deadline:
                    child.poll()
                    try:
                        os.killpg(child.pid, 0)
                    except ProcessLookupError:
                        break
                    except PermissionError:
                        # macOS can transiently deny signals while the terminated
                        # group is being reaped. Retry within the same deadline;
                        # persistent denial still fails the final SIGKILL below.
                        pass
                    time.sleep(0.1)
                else:
                    os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            finally:
                signal.signal(signal.SIGINT, previous_int)
                signal.signal(signal.SIGTERM, previous)
        if check and code:
            raise subprocess.CalledProcessError(code, command)
        return subprocess.CompletedProcess(command, code)


# Business-neutral name; the original public function remains compatible.
run_process = run_ui_process
