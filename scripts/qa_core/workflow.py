"""Serial, shell-free local workflow with one project lock across all stages."""
import os
from pathlib import Path

from .local_lock import local_run_lock
from .process import run_process


def run_stages(stages, *, project_root, namespace='qa-automation', env=None, extra_args=()):
    """Run argv arrays, stop on failure, append extra arguments only to the final stage.

    Leading NAME=value entries are stage-local environment overrides. Validate every
    stage before acquiring the lock or executing anything. Caller data is never mutated.
    """
    if not isinstance(stages, (list, tuple)) or not stages:
        raise ValueError('workflow requires at least one stage')
    if not isinstance(extra_args, (list, tuple)) or not all(isinstance(arg, str) for arg in extra_args):
        raise ValueError('extra_args must be an array of strings')
    prepared = []
    base_env = dict(os.environ if env is None else env)
    for stage in stages:
        if not isinstance(stage, (list, tuple)) or not stage or not all(isinstance(arg, str) for arg in stage):
            raise ValueError('each stage must be a nonempty array of strings')
        command = list(stage)
        stage_env = dict(base_env)
        while command and '=' in command[0] and command[0].split('=', 1)[0].isidentifier():
            name, value = command.pop(0).split('=', 1)
            stage_env[name] = value
        if not command or not command[0]:
            raise ValueError('stage is missing an executable')
        prepared.append((command, stage_env))
    prepared[-1][0].extend(extra_args)
    root = Path(project_root).resolve()
    if not root.is_dir():
        raise ValueError('project_root must be an existing directory')
    with local_run_lock(namespace=namespace) as fd:
        for command, stage_env in prepared:
            # The token is generated when the lock is acquired, after base_env was copied.
            stage_env['QA_LOCAL_LOCK_TOKEN'] = os.environ['QA_LOCAL_LOCK_TOKEN']
            result = run_process(command, project_root=root, cwd=root, env=stage_env,
                                 pass_fds=(() if fd is None else (fd,)))
            if result.returncode:
                return result.returncode
    return 0
