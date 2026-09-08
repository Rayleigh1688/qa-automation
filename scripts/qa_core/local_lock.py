"""Advisory, per-OS-user, same-machine lock for cooperating QA commands (POSIX / Windows)."""
import contextlib
import os
import errno
import hashlib

WINDOWS = os.name == "nt"

if WINDOWS:
    import msvcrt
else:
    import fcntl
import json
from pathlib import Path
import secrets
import tempfile


class LocalRunBusy(RuntimeError):
    pass


def lock_path():
    # Shared by checkouts for this OS user, independent of environment/account.
    identity = os.getuid() if not WINDOWS else hashlib.sha256(os.getlogin().encode()).hexdigest()[:16]
    return Path(tempfile.gettempdir()) / f'qa-automation-{identity}.lock'


@contextlib.contextmanager
def local_run_lock(path=None, *, inherit=True):
    target = Path(path) if path else lock_path()
    fd = os.open(target, os.O_RDWR | os.O_CREAT | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_BINARY', 0), 0o600)
    try:
        stat = os.fstat(fd)
        if not WINDOWS and (stat.st_uid != os.getuid() or stat.st_mode & 0o077):
            raise LocalRunBusy('Local lock permissions invalid; ask the file owner to restore mode 0600. Do not delete an active lock.')
        try:
            if WINDOWS:
                # Lock byte zero; metadata starts at byte one so nested readers can read it.
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            else:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            if error.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                raise
            try:
                os.lseek(fd, 1 if WINDOWS else 0, os.SEEK_SET)
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
        offset = 1 if WINDOWS else 0
        os.ftruncate(fd, offset)
        os.lseek(fd, offset, os.SEEK_SET)
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
