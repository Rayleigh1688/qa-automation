import fs from "node:fs";
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

test("capture skip-bonus deposit request contract", async ({ page }) => {
  const pageConfig = loadJson("ui/data/client-pages.json");
  const modalConfig = loadJson("ui/data/client-modals.json");
  const app = new ClientAppPage(page, { pageConfig, modalConfig });
  const network = attachNetworkRecorder(page);

  await app.gotoHome();
  const alreadyLoggedIn = !(await page.locator("body").innerText()).includes("Register / Login");
  if (!alreadyLoggedIn) {
    await app.loginWithOtp(requiredEnv("CLIENT_PHONE"), requiredEnv("CLIENT_OTP"));
  }
  await page.context().storageState({ path: storageStatePath });

  await page.goto("/my?action=deposit", { waitUntil: "domcontentloaded" });
  await page.waitForLoadState("networkidle", { timeout: 5000 }).catch(() => {});
  await page.waitForTimeout(1500);

  const beforeControls = await visibleControls(page);
  const bodyText = await page.locator("body").innerText();
  const screenshotDir = path.resolve("ui/results/screenshots");
  fs.mkdirSync(screenshotDir, { recursive: true });
  await page.screenshot({ path: path.join(screenshotDir, "deposit-contract-before.png"), fullPage: false });

  let skipBonusConfirmed = false;
  let depositRequest = null;
  if (process.env.EXECUTE_DEPOSIT_CONTRACT === "true") {
    const amount = String(process.env.CLIENT_DEPOSIT_AMOUNT || "1000");
    await page.locator('input[placeholder*="Enter Amount"]').fill(amount);

    const bonusLabel = page.getByText("Multiple Deposit Bonus", { exact: true });
    await bonusLabel.click({ force: true });
    await page.waitForTimeout(500);

    if (await page.getByText("Skip Bonus?", { exact: true }).isVisible({ timeout: 3000 }).catch(() => false)) {
      await page.screenshot({ path: path.join(screenshotDir, "deposit-contract-skip-confirm.png"), fullPage: false });
      await page.getByRole("button", { name: /^Yes$/i }).click();
      skipBonusConfirmed = true;
      await page.waitForTimeout(500);
    }

    const requestPromise = page.waitForRequest(
      (request) => request.url().includes("/finance/payment/deposit"),
      { timeout: 15_000 },
    );
    await page.getByRole("button", { name: /^Deposit now$/i }).click();
    if (await page.getByText("Skip Bonus?", { exact: true }).isVisible({ timeout: 1500 }).catch(() => false)) {
      await page.screenshot({ path: path.join(screenshotDir, "deposit-contract-skip-confirm.png"), fullPage: false });
      await page.getByRole("button", { name: /^Yes$/i }).click();
      skipBonusConfirmed = true;
    }
    const request = await requestPromise;
    depositRequest = {
      method: request.method(),
      url: request.url(),
      postData: request.postData(),
    };
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(screenshotDir, "deposit-contract-after.png"), fullPage: false });
  }

  const result = {
    scannedAt: new Date().toISOString(),
    pageUrl: page.url(),
    bodyText: bodyText.slice(0, 5000),
    beforeControls,
    skipBonusConfirmed,
    depositRequest,
    network,
  };
  const out = path.resolve("ui/results/client-deposit-contract.json");
  fs.writeFileSync(out, JSON.stringify(result, null, 2));

  expect(page.url()).toContain("/my");
  expect(bodyText).toContain("Deposit");
  expect(bodyText).toMatch(/Payment Methods|Gcash|COINS|QRPH|maya/i);
  expect(beforeControls.some((control) => /Enter Amount/i.test(control.placeholder))).toBeTruthy();
  if (process.env.EXECUTE_DEPOSIT_CONTRACT === "true") {
    expect(skipBonusConfirmed).toBeTruthy();
    expect(depositRequest?.url).toContain("/finance/payment/deposit");
  }
});
