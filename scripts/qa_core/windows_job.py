"""Windows stage containment. Gate execution until assignment to a kill-on-close Job."""
import ctypes
from ctypes import wintypes as w
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time


class Job:
    def __init__(self):
        self.api = ctypes.WinDLL('kernel32', use_last_error=True)
        for name, args, result in [
            ('CreateJobObjectW', [w.LPVOID, w.LPCWSTR], w.HANDLE),
            ('SetInformationJobObject', [w.HANDLE, ctypes.c_int, w.LPVOID, w.DWORD], w.BOOL),
            ('AssignProcessToJobObject', [w.HANDLE, w.HANDLE], w.BOOL),
            ('TerminateJobObject', [w.HANDLE, w.UINT], w.BOOL),
            ('QueryInformationJobObject', [w.HANDLE, ctypes.c_int, w.LPVOID, w.DWORD, w.LPVOID], w.BOOL),
            ('CloseHandle', [w.HANDLE], w.BOOL),
        ]:
            fn = getattr(self.api, name); fn.argtypes = args; fn.restype = result
        class Basic(ctypes.Structure):
            _fields_ = [('process_time', ctypes.c_longlong), ('job_time', ctypes.c_longlong),
                        ('flags', w.DWORD), ('min_ws', ctypes.c_size_t), ('max_ws', ctypes.c_size_t),
                        ('active', w.DWORD), ('affinity', ctypes.c_size_t), ('priority', w.DWORD), ('scheduling', w.DWORD)]
        class IO(ctypes.Structure):
            _fields_ = [(name, ctypes.c_ulonglong) for name in ('ro', 'wo', 'oo', 'rb', 'wb', 'ob')]
        class Extended(ctypes.Structure):
            _fields_ = [('basic', Basic), ('io', IO), ('process_memory', ctypes.c_size_t),
                        ('job_memory', ctypes.c_size_t), ('peak_process', ctypes.c_size_t), ('peak_job', ctypes.c_size_t)]
        self.handle = self.api.CreateJobObjectW(None, None)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        info = Extended(); info.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.api.SetInformationJobObject(self.handle, 9, ctypes.byref(info), ctypes.sizeof(info)):
            error = ctypes.WinError(ctypes.get_last_error()); self.close(); raise error

    def assign(self, child):
        if not self.api.AssignProcessToJobObject(self.handle, w.HANDLE(int(child._handle))):
            raise ctypes.WinError(ctypes.get_last_error())

    def terminate_and_wait(self):
        if not self.api.TerminateJobObject(self.handle, 1):
            raise ctypes.WinError(ctypes.get_last_error())
        class Accounting(ctypes.Structure):
            _fields_ = [(name, ctypes.c_longlong) for name in ('user', 'kernel', 'period_user', 'period_kernel')] + [
                (name, w.DWORD) for name in ('faults', 'total', 'active', 'terminated')]
        info = Accounting()
        deadline = time.monotonic() + 10
        while True:
            if not self.api.QueryInformationJobObject(self.handle, 1, ctypes.byref(info), ctypes.sizeof(info), None):
                raise ctypes.WinError(ctypes.get_last_error())
            if not info.active:
                return
            if time.monotonic() >= deadline:
                raise OSError('Windows stage cleanup timed out; inspect remaining test processes')
            time.sleep(0.01)

    def close(self):
        if self.handle:
            self.api.CloseHandle(self.handle)
            self.handle = None


def run_windows_process(command, **kwargs):
    timeout = kwargs.pop('timeout', None)
    # No pass_fds on Windows: the owning wrapper holds the kernel lock until its Job is closed.
    kwargs.pop('pass_fds', None)
    job = Job()
    previous = {}
    child = None
    try:
        with tempfile.TemporaryDirectory(prefix='qa-stage-') as directory:
            gate = Path(directory) / 'ready'
            child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), str(gate), *command],
                                     creationflags=subprocess.CREATE_NEW_PROCESS_GROUP, **kwargs)
            def interrupted(signum, frame):
                raise KeyboardInterrupt('QA stage terminated')
            for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGBREAK):
                previous[sig] = signal.signal(sig, interrupted)
            try:
                job.assign(child)
                gate.touch()
                return subprocess.CompletedProcess(command, child.wait(timeout=timeout))
            finally:
                # Includes descendants even when the stage leader has already exited.
                for sig in previous:
                    signal.signal(sig, signal.SIG_IGN)
                try:
                    job.terminate_and_wait()
                finally:
                    job.close()
                    if child.poll() is None:
                        child.kill()  # Also covers assignment failure before any command ran.
                    child.wait()
    finally:
        job.close()
        for sig, handler in previous.items():
            signal.signal(sig, handler)


if __name__ == '__main__':
    import time
    gate = Path(sys.argv[1])
    deadline = time.monotonic() + 30
    while not gate.exists():
        if time.monotonic() >= deadline:
            sys.exit(2)
        time.sleep(0.01)
    sys.exit(subprocess.call(sys.argv[2:]))
