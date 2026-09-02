import fs from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";
import { ClientAppPage } from "../elements/client-app.page.mjs";
import { loadJson } from "../framework/data-loader.mjs";
import { loadEnv } from "../framework/env.mjs";

loadEnv();
test.use({ storageState: { cookies: [], origins: [] } });

function required(name, fallback = "") {
  const value = String(process.env[name] || fallback).trim();
  if (!value) throw new Error(`${name} is required for the pre-KYC withdrawal test`);
  return value;
}

test("new account is blocked from withdrawal before wallet password and KYC", async ({ page }) => {
  const app = new ClientAppPage(page, {
    pageConfig: loadJson("ui/data/client-pages.json"),
    modalConfig: loadJson("ui/data/client-modals.json"),
  });
  const withdrawRequests = [];
  page.on("request", (request) => {
    try {
      if (new URL(request.url()).pathname !== "/finance/payment/withdraw") return;
      withdrawRequests.push({ method: request.method(), ts: Date.now() });
    } catch {}
  });

  const phone = required("PRE_KYC_CLIENT_PHONE");
  const password = required("PRE_KYC_CLIENT_PASSWORD");
  await app.loginWithPassword(phone, password);

  const kycGate = page.getByText(/Your current account type is a basic account/i).first();
  await expect(kycGate).toBeVisible();
  expect(await app.closeBasicAccountKycGate()).toBeTruthy();
  await expect(kycGate).toBeHidden();

  await page.goto("/my?action=withdraw", { waitUntil: "domcontentloaded" });

  const securityTitle = page.getByText("Security Requirements", { exact: true });
  await expect(securityTitle).toBeVisible();
  await expect(page.getByText("Set Wallet Password", { exact: true })).toBeVisible();
  await expect(page.getByText("KYC Verify", { exact: true })).toBeVisible();
  expect(withdrawRequests).toHaveLength(0);

  const screenshotDir = path.resolve("ui/results/screenshots");
  fs.mkdirSync(screenshotDir, { recursive: true });
  await page.screenshot({ path: path.join(screenshotDir, "withdraw-blocked-before-kyc.png"), fullPage: false });
  fs.writeFileSync(path.resolve("ui/results/client-unverified-withdraw.json"), JSON.stringify({
    executedAt: new Date().toISOString(),
    accountLane: "new_kyc_account",
    kycGateClosed: true,
    securityRequirementsVisible: true,
    walletPasswordRequired: true,
    kycRequired: true,
    withdrawRequestCount: withdrawRequests.length,
  }, null, 2));
});
