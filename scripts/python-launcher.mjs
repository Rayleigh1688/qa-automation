import { spawn } from 'node:child_process';
import { pythonExecutable } from './python-runtime.mjs';
const python = pythonExecutable();
const child = spawn(python, process.argv.slice(2), { stdio: 'inherit', env: { ...process.env, QA_PYTHON_EXECUTABLE: python } });
child.once('error', () => { console.error('Python launch failed; check QA_PYTHON_EXECUTABLE.'); process.exitCode = 2; });
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => {
  // Windows console delivers Ctrl+C to Python too; SIGTERM is not a graceful Windows signal.
  if (process.platform !== 'win32') child.kill(signal);
});
child.once('exit', (code, signal) => { process.exitCode = code ?? (signal === 'SIGINT' ? 130 : 1); });
