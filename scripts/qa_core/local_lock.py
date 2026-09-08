"""Advisory, per-OS-user, same-machine lock for cooperating QA commands (POSIX)."""
import contextlib
import fcntl
import json
import os
from pathlib import Path
import secrets
import tempfile


class LocalRunBusy(RuntimeError):
    pass


def lock_path():
    # Shared by checkouts for this OS user, independent of environment/account.
    return Path(tempfile.gettempdir()) / f'qa-automation-{os.getuid()}.lock'


@contextlib.contextmanager
def local_run_lock(path=None, *, inherit=True):
    target = Path(path) if path else lock_path()
    fd = os.open(target, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        stat = os.fstat(fd)
        if stat.st_uid != os.getuid() or stat.st_mode & 0o077:
            raise LocalRunBusy('Local lock permissions invalid; ask the file owner to restore mode 0600. Do not delete an active lock.')
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            try:
                data = json.loads(os.read(fd, 4096))
                nested = (inherit and os.environ.get('QA_LOCAL_LOCK_TOKEN') == data['token']
                          and bool(data['token']))
            except (ValueError, KeyError, TypeError):
                nested = False
            if not nested:
                raise LocalRunBusy('Another local QA run holds the lock. Wait for it to finish or stop its owning terminal; do not delete the lock file.') from None
            yield None
            return
        token = secrets.token_hex(24)
        previous = os.environ.get('QA_LOCAL_LOCK_TOKEN')
        os.ftruncate(fd, 0)
        os.write(fd, json.dumps({'pid': os.getpid(), 'token': token}).encode())
        os.environ['QA_LOCAL_LOCK_TOKEN'] = token
        try:
            yield fd
        finally:
            if previous is None:
                os.environ.pop('QA_LOCAL_LOCK_TOKEN', None)
            else:
                os.environ['QA_LOCAL_LOCK_TOKEN'] = previous
        # Closing all inherited descriptors releases flock, including on process exit.
        # Never unlink: an unlinked inode would allow two concurrent locks.
    finally:
        os.close(fd)
