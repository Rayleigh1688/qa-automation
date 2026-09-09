import { spawnSync } from 'node:child_process';
import path from 'node:path';

// ASCII JSON avoids Windows console-codepage corruption in non-ASCII install paths.
const probe = 'import json,sys; print(json.dumps({"executable":sys.executable,"supported":sys.version_info >= (3,10)},ensure_ascii=True))';

export function pythonExecutable(env = process.env) {
  const explicit = env.QA_PYTHON_EXECUTABLE;
  const venvPython = env.VIRTUAL_ENV && path.join(env.VIRTUAL_ENV, process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
  const source = explicit ? 'QA_PYTHON_EXECUTABLE' : venvPython ? 'VIRTUAL_ENV' : 'system Python';
  const candidates = explicit ? [[explicit]] : venvPython ? [[venvPython]] : process.platform === 'win32' ? [['py', '-3'], ['python'], ['python3']] : [['python3'], ['python']];
  const failures = [];
  for (const [command, ...prefix] of candidates) {
    const result = spawnSync(command, [...prefix, '-c', probe], { encoding: 'utf8', env, timeout: 10000 });
    let reason = result.error?.code || `exit=${result.status ?? result.signal ?? 'unknown'}`;
    if (result.status === 0) {
      try {
        const data = JSON.parse(result.stdout.trim());
        if (data.supported && typeof data.executable === 'string' && data.executable) return data.executable;
        reason = data.supported === false ? 'requires Python 3.10+' : 'invalid probe output';
      } catch { reason = 'invalid probe output'; }
    }
    // Do not print paths, environment values or subprocess output.
    failures.push(reason);
  }
  throw new Error(`Python selection failed [source=${source}; ${failures.join(', ')}]. Set QA_PYTHON_EXECUTABLE to the executable file only (no embedded quotes or arguments), or recreate/select this computer's .venv.`);
}
