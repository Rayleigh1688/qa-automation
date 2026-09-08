import fs from 'node:fs';

export function validateKycEnvironment(env, { approve = false } = {}) {
  const expected = {
    CLIENT_BASE_URL: 'https://client-fat.filbet2025.com',
    API_URL: 'https://client-fat.filbet2025.com',
    ADMIN_URL: 'https://admin-fat.filbet2025.com',
  };
  for (const [key, origin] of Object.entries(expected)) {
    if (!env[key] || new URL(env[key]).origin !== origin) throw new Error(`${key} must point to the designated FAT environment`);
  }
  for (const key of ['KYC_CLIENT_PHONE', 'KYC_CLIENT_PASSWORD', 'PRE_KYC_CLIENT_PHONE', 'WRITE_CLIENT_PHONE', 'KYC_IMAGE']) {
    if (!env[key]) throw new Error(`${key} is required`);
  }
  const normalize = value => String(value).replace(/\D/g, '').replace(/^63/, '').replace(/^0/, '');
  const phone = normalize(env.KYC_CLIENT_PHONE);
  if (!/^9\d{9}$/.test(phone)) throw new Error('KYC account must be a valid test phone');
  if ([env.PRE_KYC_CLIENT_PHONE, env.WRITE_CLIENT_PHONE].some(value => normalize(value) === phone)) throw new Error('KYC lane must be separate from permanent BASIC and fund flow lanes');
  if (!fs.statSync(env.KYC_IMAGE).isFile()) throw new Error('KYC_IMAGE must be a local file');
  if (approve && !env.ADMIN_APPROVAL_TOTP_SECRET) throw new Error('ADMIN_APPROVAL_TOTP_SECRET is required for approval');
}

export function validateKycResume(prior, run, now = Date.now()) {
  const age = now - Date.parse(run?.startedAt);
  if (!prior?.runId || prior.runId !== run?.runId || prior.scope !== 'FAT'
    || prior.stage !== 'approved_refresh' || prior.adminApproved !== true
    || prior.beforeStatus !== 0 || prior.afterStatus !== 2 || prior.uiSubmitted !== true
    || prior.submission?.businessStatus !== true || prior.submission?.successVisible !== true
    || prior.submission?.successfulUploads !== 3 || !prior.uid
    || !Number.isFinite(age) || age < 0 || age > 3600000) {
    throw new Error('Resume requires the current, recent UI submission and approval evidence; no historical status substitution');
  }
}
