import { spawnSync } from 'node:child_process';
import path from 'node:path';

export function pythonExecutable(env = process.env) {
  if (env.QA_PYTHON_EXECUTABLE) return env.QA_PYTHON_EXECUTABLE;
  const venvPython = env.VIRTUAL_ENV && path.join(env.VIRTUAL_ENV, process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
  const candidates = venvPython ? [[venvPython]] : process.platform === 'win32' ? [['py', '-3'], ['python'], ['python3']] : [['python3'], ['python']];
  for (const [command, ...prefix] of candidates) {
    const result = spawnSync(command, [...prefix, '-c', 'import sys; assert sys.version_info >= (3, 10); print(sys.executable)'], { encoding: 'utf8', env });
    if (result.status === 0 && result.stdout.trim()) return result.stdout.trim();
  }
  throw new Error('Python 3.10+ unavailable; check the active venv or set QA_PYTHON_EXECUTABLE to its executable path.');
}
