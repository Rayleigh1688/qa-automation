import {captureSafeStatus} from '../framework/visual-evidence.mjs';
import fs from 'node:fs';
import { runControlledApi } from '../framework/controlled-api.mjs';
import path from 'node:path';
import { expect, test } from '@playwright/test';
import { ClientAppPage } from '../elements/client-app.page.mjs';
import { loadJson } from '../framework/data-loader.mjs';
import { ClientKycPage } from '../elements/client-kyc.page.mjs';
import { p0StorageStatePath } from '../framework/auth-state.mjs';

// Only the controlled runner supplies fresh authentication and validates the lane.
test.use({ storageState: p0StorageStatePath, trace: 'off', video: 'off', screenshot: 'off' });
test.describe.configure({ retries: 0 });
test(process.env.KYC_RESUME_APPROVED === 'true' ? 'KYC UI resumes this-run approved status refresh' : 'KYC UI submits this-run identity and refreshes pending status', async ({ page }) => {
  test.skip(process.env.EXECUTE_KYC_UI !== 'true', 'Use the controlled KYC runner');
  test.setTimeout(240_000);
  const kyc = new ClientKycPage(page);
  const resume = process.env.KYC_RESUME_APPROVED === 'true';
  const result = resume ? JSON.parse(fs.readFileSync('ui/results/client-kyc-submit.json', 'utf8')) : { runId: process.env.UI_BUSINESS_RUN_ID, scope: process.env.UI_BUSINESS_SCOPE, status: 'BLOCKED', stage: 'precondition', uiSubmitted: false };
  result.visualEvidence ||= {};
  result.network ||= [];
  result.network = result.network.filter(item => /^\/member\/(kyc|oss|detail)/.test(item.path));
  page.on('response', response => {
    if (!['xhr', 'fetch'].includes(response.request().resourceType()) || !/^\/member\/(kyc|oss|detail)/.test(new URL(response.url()).pathname)) return;
    result.network.push({ path: new URL(response.url()).pathname, method: response.request().method(), httpStatus: response.status() });
  });
  try {
    const before = await kyc.open();
    if (resume) {
      expect(result.runId).toBe(process.env.UI_BUSINESS_RUN_ID);
      expect(before.uid).toBe(result.uid);
      expect(before.status).toBe(kyc.config.approvedStatus);
      result.approvedStatus = before.status;
      result.visualEvidence.approved = await captureSafeStatus(page, 'kyc-approved-status', kyc.config.visualStatusPatterns.approved, {title:'KYC 审核后状态区', assertion:'fresh UI 会话同 UID 状态 5；截图仅展示状态文字', status:'PASS'});
      result.resumedRefresh = true;
      result.status = 'APPROVED';
      result.stage = 'complete';
      return;
    }
    result.uid = before.uid;
    result.beforeStatus = before.status;
    expect(kyc.config.submitReadyStatuses, 'account must be submit-ready; existing approval is not a UI pass').toContain(before.status);
    result.stage = 'form';
    await kyc.fill(path.resolve(process.env.KYC_IMAGE));
    result.stage = 'submit';
    result.submission = await kyc.submit();
    result.uiSubmitted = true;
    result.visualEvidence.submitted = await captureSafeStatus(page, 'kyc-submitted-status', kyc.config.visualStatusPatterns.submitted, {title:'KYC 提交成功提示', assertion:'页面 KYC successful 可见；提交后状态 2', status:'PASS'});
    result.stage = 'refresh';
    const after = await kyc.refresh();
    result.afterStatus = after.status;
    expect(after.uid).toBe(before.uid);
    expect(after.status).toBe(kyc.config.pendingStatus);
    result.status = 'SUBMITTED_PENDING';
    if (process.env.APPROVE_KYC_UI === 'true') {
      result.stage = 'admin_approval';
      const records = await runControlledApi('kyc-approve', ['--kyc-uid', before.uid]);
      const approval = records.find(r => r.name === 'admin_kyc_approve');
      expect(approval?.business_status).toBe(true);
      expect(String(approval?.uid)).toBe(before.uid);
      result.adminApproved = true;
      result.stage = 'approved_refresh';
      // The API runner logs in afresh and can invalidate the original UI session.
      await page.context().clearCookies();
      // Match the shared home navigation: resource loading is not KYC readiness.
      // loginWithPassword and kyc.open below assert the actual UI/session state.
      await page.goto('/', { waitUntil: 'domcontentloaded' });
      await page.evaluate(() => { localStorage.clear(); sessionStorage.clear(); });
      const app = new ClientAppPage(page, { pageConfig: loadJson('ui/data/client-pages.json'), modalConfig: loadJson('ui/data/client-modals.json') });
      await app.loginWithPassword(process.env.CLIENT_PHONE, process.env.CLIENT_PASSWORD);
      const approved = await kyc.open();
      expect(approved.uid).toBe(before.uid);
      expect(approved.status).toBe(kyc.config.approvedStatus);
      result.approvedStatus = approved.status;
      result.visualEvidence.approved = await captureSafeStatus(page, 'kyc-approved-status', kyc.config.visualStatusPatterns.approved, {title:'KYC 审核后状态区', assertion:'fresh UI 会话同 UID 状态 5；截图仅展示状态文字', status:'PASS'});
      result.status = 'APPROVED';
    }
    result.stage = 'complete';
  } catch (error) {
    result.status = 'BLOCKED';
    throw error;
  } finally {
    // No names, phone, document image, payload or auth material in the summary.
    fs.writeFileSync('ui/results/client-kyc-submit.json', JSON.stringify(result, null, 2), { mode: 0o600 });
  }
});
