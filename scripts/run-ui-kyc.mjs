import { styled } from '../ui/framework/terminal.mjs';
import fs from 'node:fs';
import crypto from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { validateKycEnvironment, validateKycResume } from '../ui/framework/kyc-preflight.mjs';
import { loadEnv } from '../ui/framework/env.mjs';

const out = 'ui/results/kyc-ui-run-status.json';
fs.mkdirSync('ui/results', { recursive: true });
const resume = process.argv.includes('--resume-refresh');
const result = { runId: crypto.randomUUID(), startedAt: new Date().toISOString(), status: 'BLOCKED', stage: 'preflight' };
let exitCode = 1;
if (!resume) fs.rmSync('ui/results/client-kyc-submit.json', { force: true });
fs.rmSync('ui/results/kyc-ui-storage-state.json', { force: true });
for (const suffix of ['failure.json', 'failure.png', 'session.json']) fs.rmSync(`ui/results/kyc-ui-auth-${suffix}`, { force: true });
try {
  if (process.argv.slice(2).some(arg => !['--approve', '--resume-refresh'].includes(arg))) throw new Error('Only --approve or --resume-refresh is supported');
  const approve = process.argv.includes('--approve');
  if (approve && resume) throw new Error('Resume only reads approved state; do not combine with --approve');
  if (resume) {
    const prior = JSON.parse(fs.readFileSync('ui/results/client-kyc-submit.json', 'utf8'));
    const run = JSON.parse(fs.readFileSync(out, 'utf8'));
    validateKycResume(prior, run);
    result.runId = prior.runId;
    result.startedAt = run.startedAt;
    result.resumedAt = new Date().toISOString();
  }
  if (!process.env.ENV_FILE) throw new Error('Explicit ENV_FILE=.env.fat is required');
  if (!fs.existsSync(process.env.ENV_FILE)) throw new Error('Selected environment file does not exist');
  loadEnv();
  validateKycEnvironment(process.env, { approve });
  result.scope = 'FAT';
  result.approvalRequested = approve;
  const env = {
    ...process.env, ENV_FILE_PRECEDENCE: 'shell',
    CLIENT_PHONE: process.env.KYC_CLIENT_PHONE, CLIENT_PASSWORD: process.env.KYC_CLIENT_PASSWORD,
    CLIENT_AUTH_MODE: process.env.KYC_CLIENT_AUTH_MODE || 'password',
    CLIENT_OTP: process.env.KYC_CLIENT_OTP || '',
    CLIENT_REUSE_P0_AUTH: 'true', CLIENT_AUTH_LANE: 'kyc_account', CLIENT_AUTH_ARTIFACT_PREFIX: 'kyc-ui-auth',
    CLIENT_P0_STORAGE_STATE_PATH: 'ui/results/kyc-ui-storage-state.json',
    KYC_RESUME_APPROVED: String(resume), EXECUTE_KYC_UI: 'true', APPROVE_KYC_UI: String(approve), UI_BUSINESS_RUN_ID: result.runId, UI_BUSINESS_SCOPE: result.scope,
    EXECUTE_BET: 'false', EXECUTE_DEPOSIT_CONTRACT: 'false', EXECUTE_WITHDRAW_UI: 'false',
  };
  result.stage = 'kyc_ui';
  const child = spawnSync('npx', ['playwright', 'test', 'ui/cases/client-kyc-submit.spec.mjs', '--workers=1', '--retries=0'], { env, stdio: 'inherit' });
  if (child.error || child.status !== 0) throw new Error('KYC UI failed; inspect current Playwright and KYC evidence');
  const submission = JSON.parse(fs.readFileSync('ui/results/client-kyc-submit.json', 'utf8'));
  if (submission.runId !== result.runId || submission.status !== (approve || resume ? 'APPROVED' : 'SUBMITTED_PENDING') || !submission.uiSubmitted) throw new Error('Missing this-run KYC UI submission evidence');
  result.status = submission.status;
  result.stage = 'complete';
  exitCode = 0;
} catch (error) {
  result.error = error.message;
  console.error(styled(result.error, 'FAIL', process.stderr));
} finally {
  result.finishedAt = new Date().toISOString();
  result.exitCode = exitCode;
  fs.writeFileSync(out, JSON.stringify(result, null, 2));
  fs.mkdirSync('ui/reports', { recursive: true });
  const escape = value => String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;');
  fs.writeFileSync('ui/reports/kyc-ui-report.html', `<!doctype html><html lang="zh"><meta charset="utf-8"><title>KYC UI</title><style>body{font:16px system-ui;max-width:900px;margin:40px auto;padding:20px}pre{white-space:pre-wrap;background:#f3f5f7;padding:20px}</style><h1>KYC UI：${escape(result.status)}</h1><p>SUBMITTED_PENDING 表示本轮页面提交后待审；APPROVED 还要求本轮后台审核与浏览器刷新为 5。该报告不代表默认页面回归或资金全流程通过。</p><pre>${escape(JSON.stringify(result, null, 2))}</pre><a href="../results/kyc-ui-run-status.json">运行状态</a></html>`);
  fs.rmSync('ui/results/kyc-ui-storage-state.json', { force: true });
}
console.log(styled(`KYC UI ${result.status}`, exitCode === 0 ? 'PASS' : 'BLOCKED'));
console.log(styled('HTML report: ui/reports/kyc-ui-report.html', 'PATH'));
process.exitCode = exitCode;
