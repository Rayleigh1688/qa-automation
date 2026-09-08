import {captureVisual} from '../framework/visual-evidence.mjs';
import fs from "node:fs";
import { readBusinessRequest, requireBusinessResponse } from "../framework/business-response.mjs";
import path from "node:path";
import { expect, test } from "@playwright/test";
import { ClientAppPage } from "../elements/client-app.page.mjs";
import { loadJson } from "../framework/data-loader.mjs";
import { loadEnv, requiredEnv } from "../framework/env.mjs";
import { attachNetworkRecorder } from "../framework/network-recorder.mjs";
import { p0StorageStatePath, reuseP0Auth } from "../framework/auth-state.mjs";

loadEnv();

const storageStatePath = reuseP0Auth
  ? p0StorageStatePath
  : path.resolve("ui/results/client-deposit-storage-state.json");
if (reuseP0Auth || (process.env.CLIENT_REUSE_DEPOSIT_STORAGE === "true" && fs.existsSync(storageStatePath))) {
  test.use({ storageState: storageStatePath });
}

async function visibleControls(page) {
  return page.locator("button, input, [role='button']").evaluateAll((elements) => elements
    .map((element) => {
      const rect = element.getBoundingClientRect();
      return {
        tag: element.tagName,
        text: String(element.innerText || element.textContent || "").trim().slice(0, 120),
        type: element.getAttribute("type") || "",
        placeholder: element.getAttribute("placeholder") || "",
        value: "value" in element ? String(element.value || "") : "",
        x: Math.round(rect.x),
        y: Math.round(rect.y),
        width: Math.round(rect.width),
        height: Math.round(rect.height),
      };
    })
    .filter((item) => item.width > 0 && item.height > 0));
}

test.describe.configure({ retries: 0 });

test("capture skip-bonus deposit request contract", async ({ page }) => {
  const pageConfig = loadJson("ui/data/client-pages.json");
  const modalConfig = loadJson("ui/data/client-modals.json");
  const app = new ClientAppPage(page, { pageConfig, modalConfig });
  const network = attachNetworkRecorder(page);

  await app.gotoHome();
  const alreadyLoggedIn = !(await page.locator("body").innerText()).includes("Register / Login");
  if (!alreadyLoggedIn) {
    await app.loginWithPassword(requiredEnv("CLIENT_PHONE"), requiredEnv("CLIENT_PASSWORD"));
  }
  await page.context().storageState({ path: storageStatePath });

  await page.goto("/my?action=deposit", { waitUntil: "domcontentloaded" });
  await page.waitForLoadState("networkidle", { timeout: 5000 }).catch(() => {});
  await page.waitForTimeout(1500);

  const beforeControls = await visibleControls(page);
  const bodyText = await page.locator("body").innerText();
  const visualEvidence = {};
  const screenshotDir = path.resolve("ui/results/screenshots");
  fs.mkdirSync(screenshotDir, { recursive: true });
  await page.screenshot({ path: path.join(screenshotDir, "deposit-contract-before.png"), fullPage: false });

  let skipBonusConfirmed = false;
  let bonusControlPresent = false;
  let nonBonusConfirmed = false;
  let depositRequest = null;
  let depositResponse = null;
  if (process.env.EXECUTE_DEPOSIT_CONTRACT === "true") {
    const amount = String(process.env.CLIENT_DEPOSIT_AMOUNT || "1000");
    // Abort unintended money/activity parameters before the request reaches FAT.
    await page.route('**/finance/payment/deposit?*', async route => {
      const submitted = readBusinessRequest(route.request());
      const allowed = Number(submitted.amount) === Number(amount)
        && submitted.rotation_flag === '0' && submitted.cashback_flag === '0' && !submitted.product_id;
      if (!allowed) {
        fs.writeFileSync('ui/results/client-deposit-guard.json', JSON.stringify({ amount: submitted.amount, rotationFlag: submitted.rotation_flag, cashbackFlag: submitted.cashback_flag, productPresent: Boolean(submitted.product_id), blockedBeforeSend: true }));
        return route.abort('blockedbyclient');
      }
      return route.continue();
    });
    await page.locator('input[placeholder*="Enter Amount"]').fill(amount);

    const bonusLabel = page.getByText("Multiple Deposit Bonus", { exact: true });
    bonusControlPresent = await bonusLabel.isVisible();
    if (bonusControlPresent) {
      await bonusLabel.click({ force: true });
      await page.waitForTimeout(500);
    }

    if (await page.getByText("Skip Bonus?", { exact: true }).isVisible({ timeout: 3000 }).catch(() => false)) {
      await page.screenshot({ path: path.join(screenshotDir, "deposit-contract-skip-confirm.png"), fullPage: false });
      await page.getByRole("button", { name: /^Yes$/i }).click();
      skipBonusConfirmed = true;
      await page.waitForTimeout(500);
    }

    const responsePromise = page.waitForResponse(
      (response) => new URL(response.url()).pathname === "/finance/payment/deposit" && response.request().method() === "GET",
      { timeout: 15_000 },
    );
    responsePromise.catch(() => {});
    await page.getByRole("button", { name: /^Deposit now$/i }).click();
    if (await page.getByText("Skip Bonus?", { exact: true }).isVisible({ timeout: 1500 }).catch(() => false)) {
      await page.screenshot({ path: path.join(screenshotDir, "deposit-contract-skip-confirm.png"), fullPage: false });
      await page.getByRole("button", { name: /^Yes$/i }).click();
      skipBonusConfirmed = true;
    }
    const response = await responsePromise;
    const body = await requireBusinessResponse(response);
    const request = response.request();
    const submitted = readBusinessRequest(request);
    expect(Number(submitted.amount)).toBe(Number(amount));
    expect(Number(submitted.rotation_flag)).toBe(0);
    expect(Number(submitted.cashback_flag)).toBe(0);
    expect(submitted.product_id || "").toBe("");
    nonBonusConfirmed = true;
    const orderId = String(body.data?.order_id || body.data?.id || "");
    expect(orderId, "deposit response must identify this UI order").not.toBe("");
    depositResponse = { httpStatus: response.status(), businessStatus: true, orderId };
    depositRequest = {
      method: request.method(),
      path: new URL(request.url()).pathname,
      amount: submitted.amount,
      rotationFlag: submitted.rotation_flag,
    };
    await page.waitForTimeout(1000);
    visualEvidence.after = await captureVisual(page, 'deposit-contract-after', {title:'UI 充值建单后页面', kind:'DOM assertion screenshot', status:'PASS', assertion:'建单业务成功；金额与非活动参数已核对；支付页不代表到账'}, {fullPage:false});
  }

  const result = {
    runId: process.env.UI_BUSINESS_RUN_ID,
    visualEvidence,
    scannedAt: new Date().toISOString(),
    pageUrl: page.url(),
    bodyText: bodyText.slice(0, 5000),
    beforeControls,
    skipBonusConfirmed,
    bonusControlPresent,
    nonBonusConfirmed,
    depositRequest,
    depositResponse,
    network,
  };
  const out = path.resolve("ui/results/client-deposit-contract.json");
  fs.writeFileSync(out, JSON.stringify(result, null, 2));

  expect(page.url()).toContain("/my");
  expect(bodyText).toContain("Deposit");
  expect(bodyText).toMatch(/Payment Methods|Gcash|COINS|QRPH|maya/i);
  expect(beforeControls.some((control) => /Enter Amount/i.test(control.placeholder))).toBeTruthy();
  if (process.env.EXECUTE_DEPOSIT_CONTRACT === "true") {
    expect(nonBonusConfirmed).toBeTruthy();
    expect(depositRequest?.path).toContain("/finance/payment/deposit");
  }
});
