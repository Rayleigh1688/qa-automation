import { spawn } from 'node:child_process';
import { pythonExecutable } from './python-runtime.mjs';

try {
  const args = process.argv.slice(2);
  const preferProjectVenv = args[0] === '--prefer-project-venv';
  if (preferProjectVenv) args.shift();
  const python = pythonExecutable(process.env, { preferProjectVenv });
  const child = spawn(python, args, { stdio: 'inherit', env: { ...process.env, QA_PYTHON_EXECUTABLE: python } });
  child.once('error', (error) => {
    console.error(`Python launch failed [${error.code || 'unknown'}] after interpreter selection; check executable access and the working directory.`);
    process.exitCode = 2;
  });
  for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => {
    // Windows console delivers Ctrl+C to Python too; SIGTERM is not a graceful Windows signal.
    if (process.platform !== 'win32') child.kill(signal);
  });
  child.once('exit', (code, signal) => { process.exitCode = code ?? (signal === 'SIGINT' ? 130 : 1); });
} catch (error) {
  console.error(error.message);
  process.exitCode = 2;
}
