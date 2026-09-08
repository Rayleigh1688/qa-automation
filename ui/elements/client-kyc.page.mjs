import { expect } from '@playwright/test';
import { loadJson } from '../framework/data-loader.mjs';
import { requireBusinessResponse } from '../framework/business-response.mjs';

// Adapted from the frozen client-kyc-ui-submit specialist; no archive dependency.
export class ClientKycPage {
  constructor(page) {
    this.page = page;
    this.config = loadJson('ui/data/client-kyc-flow.json');
  }
  button(key) {
    const name = this.config.buttonPatterns?.[key] ? new RegExp(this.config.buttonPatterns[key]) : this.config.buttons[key];
    return this.page.getByRole('button', { name, exact: true }).last();
  }
  field(key) { return this.page.getByPlaceholder(this.config.placeholders[key], { exact: true }).first(); }
  async openPicker(key) {
    const field = this.field(key);
    // The historical UI uses a readonly input inside a clickable field container.
    const container = await field.evaluateHandle((node, selector) => node.closest(selector) || node.parentElement || node, this.config.selectors.pickerContainer);
    await container.asElement().click();
    await container.dispose();
  }
  async choose(key, name) {
    await this.openPicker(key);
    await this.page.getByRole('button', { name }).first().click();
    await this.button('confirm').click();
  }
  async detailAfter(action) {
    const [response] = await Promise.all([
      this.page.waitForResponse(r => new URL(r.url()).pathname === this.config.detailPath && r.request().method() === 'GET'),
      action(),
    ]);
    const body = await requireBusinessResponse(response);
    if (!body.data || !Number.isInteger(body.data.kyc_status) || !body.data.uid) throw new Error('KYC detail missing uid/status');
    return { uid: String(body.data.uid), status: body.data.kyc_status };
  }
  async open() { return this.detailAfter(() => this.page.goto(this.config.route, { waitUntil: 'domcontentloaded' })); }
  async refresh() { return this.detailAfter(() => this.page.reload({ waitUntil: 'domcontentloaded' })); }
  async fill(imagePath) {
    for (let i = 0; i < 2; i += 1) {
      if (await this.field('idType').isVisible().catch(() => false)) break;
      await this.button('verify').click();
      await this.field('idType').waitFor({ state: 'visible', timeout: 1500 }).catch(() => {});
    }
    await this.choose('idType', this.config.buttons.idType);
    const files = this.page.locator(this.config.selectors.file);
    await expect(files).toHaveCount(3);
    for (let i = 0; i < 3; i += 1) {
      await files.nth(i).setInputFiles(imagePath);
      await expect(this.page.locator(this.config.selectors.preview)).toHaveCount(i + 1);
    }
    await this.button('next').click();
    await this.field('address').fill(this.config.fixture.address);
    for (const key of ['branch', 'work', 'income']) await this.choose(key, new RegExp(this.config.options[key], 'i'));
    await this.button('next').click();
    for (const key of ['firstName', 'middleName', 'lastName', 'province']) await this.field(key).fill(this.config.fixture[key]);
    await this.button('gender').click();
    await this.openPicker('birthday');
    await this.button('confirm').click();
    // Preserve the specialist's default adult date, but verify it is actually adult.
    const birthday = await this.field('birthday').inputValue();
    const birth = new Date(birthday);
    const adultCutoff = new Date(); adultCutoff.setFullYear(adultCutoff.getFullYear() - 21);
    if (!Number.isFinite(birth.getTime()) || birth > adultCutoff) throw new Error('KYC birthday picker did not select an adult date');
    await this.choose('nationality', this.config.buttons.nationality);
    await this.button('next').click();
    await expect(this.page.getByText(this.config.reviewText, { exact: true })).toBeVisible();
  }
  async submit() {
    const uploads = [];
    const captureUpload = response => {
      if (new URL(response.url()).pathname !== this.config.uploadPath || response.request().method() !== 'POST') return;
      const validated = requireBusinessResponse(response);
      validated.catch(() => {});
      uploads.push(validated);
    };
    this.page.on('response', captureUpload);
    try {
      const [response] = await Promise.all([
        this.page.waitForResponse(r => this.config.submitPaths.includes(new URL(r.url()).pathname) && r.request().method() === 'POST'),
        this.button('submit').click(),
      ]);
      await requireBusinessResponse(response);
      await Promise.all(uploads);
      expect(uploads).toHaveLength(3);
      await expect(this.page.getByText(this.config.successText, { exact: true })).toBeVisible();
      return { path: new URL(response.url()).pathname, httpStatus: response.status(), businessStatus: true, successVisible: true, successfulUploads: uploads.length };
    } finally { this.page.off('response', captureUpload); }
  }
}
