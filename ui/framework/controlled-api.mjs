import { pythonExecutable } from '../../scripts/python-runtime.mjs';
import fs from 'node:fs';
import { spawn } from 'node:child_process';

// Reuse existing controlled operations; no API operation here creates UI evidence.
export async function runControlledApi(operation, args = [], env = process.env) {
  fs.mkdirSync('api/results/operations', { recursive: true });
  const out = `api/results/operations/ui-${operation}.json`;
  fs.rmSync(out, { force: true });
  const log = fs.openSync(`api/results/operations/ui-${operation}.log`, 'w', 0o600);
  try {
    const code = await new Promise((resolve, reject) => {
      const child = spawn(pythonExecutable(env), ['scripts/api-controlled-flow-runner.py', '--env', env.ENV_FILE,
        '--operation', operation, '--insecure', '--body-format', 'cbor', '--out', out, ...args],
      { env: { ...env, ENV_FILE_PRECEDENCE: 'shell', API_TOKEN: '', ADMIN_TOKEN: '' }, stdio: ['ignore', log, log] });
      child.once('error', reject);
      child.once('exit', resolve);
    });
    if (code !== 0) throw new Error(`controlled ${operation} failed; inspect ${out}`);
    const records = JSON.parse(fs.readFileSync(out, 'utf8'));
    if (!Array.isArray(records) || !records.length || records.some(r => r.business_status === false)) throw new Error(`controlled ${operation} lacks successful evidence`);
    return records;
  } finally { fs.closeSync(log); }
}
