import fs from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";
import { ClientAppPage } from "../elements/client-app.page.mjs";
import { p0StorageStatePath } from "../framework/auth-state.mjs";
import { loadJson } from "../framework/data-loader.mjs";
import { loadEnv } from "../framework/env.mjs";

loadEnv();
test.use({ storageState: p0StorageStatePath });

function safeUrl(value = "") {
  try {
    const target = new URL(value);
    for (const key of target.searchParams.keys()) target.searchParams.set(key, "<redacted>");
    return target.toString();
  } catch {
    return String(value).split("?")[0];
  }
}

function balanceFrom(text = "") {
  const match = String(text).match(/Total Balance\s*:\s*₱\s*([\d,.]+)/i);
  return match ? Number(match[1].replace(/,/g, "")) : null;
}

async function findAmountInput(page) {
  const semantic = page.getByPlaceholder(/amount/i).first();
  if (await semantic.isVisible({ timeout: 1500 }).catch(() => false)) return semantic;

  const inputs = page.locator("input:visible");
  const count = await inputs.count();
  if (!count) throw new Error("withdraw amount input not found");
  return inputs.nth(count - 1);
}

async function findSubmitButton(page) {
  const semantic = page.getByRole("button", { name: /Withdraw Now/i }).first();
  if (await semantic.isVisible({ timeout: 1500 }).catch(() => false)) return semantic;
  return page.getByText(/Withdraw Now/i).last();
}

async function selectWithdrawChannel(page, channel) {
  const tabs = page.getByText(channel, { exact: false });
  const count = await tabs.count();
  for (let index = 0; index < count; index += 1) {
    const tab = tabs.nth(index);
    if (!(await tab.isVisible({ timeout: 800 }).catch(() => false))) continue;
    const label = (await tab.innerText().catch(() => "")).trim();
    if (!new RegExp(`^${channel}$`, "i").test(label)) continue;
    await tab.click({ force: true });
    await page.waitForTimeout(800);
    return true;
  }

  const channelImage = page.locator(`img[alt*="${channel}" i]:visible`).first();
  if (await channelImage.isVisible({ timeout: 800 }).catch(() => false)) {
    await channelImage.click({ force: true });
    await page.waitForTimeout(800);
    return true;
  }
  return false;
}

async function clickConfirmationIfShown(page) {
  const dialog = page.locator('[role="dialog"]:visible').last();
  const dialogVisible = await dialog.isVisible({ timeout: 1200 }).catch(() => false);
  const scope = dialogVisible ? dialog : page;
  const confirmation = scope.getByRole("button", { name: /^(Confirm|Yes)$/i }).last();
  if (!(await confirmation.isVisible({ timeout: 1200 }).catch(() => false))) return false;
  await confirmation.click();
  return true;
}

async function enterWalletPasswordIfShown(page) {
  const title = page.getByText("Enter Wallet Password", { exact: true });
  if (!(await title.isVisible({ timeout: 1500 }).catch(() => false))) return false;

  const walletPassword = process.env.CLIENT_WALLET_PASSWORD || "";
  if (!/^\d+$/.test(walletPassword)) {
    throw new Error("CLIENT_WALLET_PASSWORD is required and must contain digits for the withdraw keypad");
  }
  for (const digit of walletPassword) {
    await page.getByRole("button", { name: new RegExp(`^${digit}$`) }).click();
  }
  return true;
}

async function withdrawPanelIsOpen(page, timeout = 1500) {
  const amountLabel = page.getByText("Withdraw Amount", { exact: true });
  const minimumInput = page.locator('input[placeholder*="Minimum"]:visible').first();
  return Promise.all([
    amountLabel.isVisible({ timeout }).catch(() => false),
    minimumInput.isVisible({ timeout }).catch(() => false),
  ]).then(([labelVisible, inputVisible]) => labelVisible && inputVisible);
}

async function openWithdrawPanel(page, app) {
  await page.goto("/my?action=withdraw", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1500);
  if (await withdrawPanelIsOpen(page)) return "direct_route";

  await app.gotoHome();
  const balance = page.getByRole("button", { name: /₱\s*[\d,.]+/ }).first();
  if (await balance.isVisible({ timeout: 2500 }).catch(() => false)) {
    await balance.click();
    await page.waitForTimeout(800);
    await app.clickFirst(["Withdraw"], 3000);
    if (await withdrawPanelIsOpen(page, 4000)) return "balance_menu";
  }

  await app.gotoHome();
  const menu = page.getByRole("button", { name: /^Menu$/i }).first();
  if (await menu.isVisible({ timeout: 2500 }).catch(() => false)) {
    await menu.click();
    await page.waitForTimeout(600);
    await app.clickFirst(["My", "Account", "Wallet"], 3000);
    await page.waitForTimeout(1200);
    await app.clickFirst(["Withdraw"], 3000);
    if (await withdrawPanelIsOpen(page, 4000)) return "main_menu";
  }

  return "not_found";
}

test("withdraw UI rejects an invalid amount and can create a legal order", async ({ page }) => {
  const app = new ClientAppPage(page, {
    pageConfig: loadJson("ui/data/client-pages.json"),
    modalConfig: loadJson("ui/data/client-modals.json"),
  });
  const withdrawEvents = [];
  page.on("request", (request) => {
    if (!request.url().includes("/finance/payment/withdraw")) return;
    withdrawEvents.push({ kind: "request", method: request.method(), url: safeUrl(request.url()), ts: Date.now() });
  });
  page.on("response", (response) => {
    if (!response.url().includes("/finance/payment/withdraw")) return;
    withdrawEvents.push({ kind: "response", status: response.status(), url: safeUrl(response.url()), ts: Date.now() });
  });

  const openMode = await openWithdrawPanel(page, app);
  expect(openMode).not.toBe("not_found");

  const withdrawChannel = String(process.env.CLIENT_WITHDRAW_CHANNEL || "Maya");
  const channelSelected = await selectWithdrawChannel(page, withdrawChannel);
  expect(channelSelected).toBeTruthy();

  const bodyBefore = await page.locator("body").innerText();
  const balanceBefore = balanceFrom(bodyBefore);
  expect(bodyBefore).toContain("Withdraw Amount");
  const amountInput = await findAmountInput(page);
  const minimumHint = await amountInput.getAttribute("placeholder") || "";
  expect(minimumHint).toMatch(/Minimum/i);
  const minimumMatch = minimumHint.match(/Minimum\s*:\s*([\d,.]+)/i)
    || bodyBefore.match(/Minimum Amount\s*:\s*([\d,.]+)/i);
  const minimum = Number((minimumMatch?.[1] || "100").replace(/,/g, ""));
  const invalidAmount = String(process.env.CLIENT_WITHDRAW_INVALID_AMOUNT || Math.max(0, minimum - 90));
  const legalAmount = String(process.env.CLIENT_WITHDRAW_AMOUNT || "1000");
  const submit = await findSubmitButton(page);

  await amountInput.fill(invalidAmount);
  await page.waitForTimeout(500);
  const invalidBody = await page.locator("body").innerText();
  const invalidSubmitEnabled = await submit.isEnabled().catch(() => false);
  const invalidEventCount = withdrawEvents.length;
  if (invalidSubmitEnabled) {
    await submit.click();
    await page.waitForTimeout(1500);
  }
  const invalidGeneratedRequest = withdrawEvents.length > invalidEventCount;

  const screenshotDir = path.resolve("ui/results/screenshots");
  fs.mkdirSync(screenshotDir, { recursive: true });
  await page.screenshot({ path: path.join(screenshotDir, "withdraw-invalid-amount.png"), fullPage: false });

  expect(Number(invalidAmount)).toBeLessThan(minimum);
  expect(`${minimumHint} ${invalidBody}`).toMatch(/Minimum Amount|minimum|invalid/i);
  expect(invalidGeneratedRequest).toBeFalsy();

  let confirmationClicked = false;
  let walletPasswordEntered = false;
  if (process.env.EXECUTE_WITHDRAW_UI === "true") {
    await amountInput.fill(legalAmount);
    await page.waitForTimeout(500);
    await expect(submit).toBeEnabled();
    await submit.click();
    walletPasswordEntered = await enterWalletPasswordIfShown(page);
    confirmationClicked = await clickConfirmationIfShown(page);
    await page.waitForTimeout(3000);
    await page.screenshot({ path: path.join(screenshotDir, "withdraw-legal-amount.png"), fullPage: false });
  }

  const legalResponses = withdrawEvents.filter((item) => item.kind === "response" && item.status >= 200 && item.status < 300);
  const bodyAfter = await page.locator("body").innerText();
  const balanceAfter = balanceFrom(bodyAfter);
  const balanceDelta = balanceBefore != null && balanceAfter != null
    ? Number((balanceBefore - balanceAfter).toFixed(2))
    : null;
  const channelUnavailable = /Payment channel unavailable/i.test(bodyAfter);
  const legalOrderCreated = /Withdrawal request successful|Transaction Details/i.test(bodyAfter);
  const transactionId = bodyAfter.match(/Transaction ID\s*([0-9]+)/i)?.[1] || "";
  const withdrawalMethod = bodyAfter.match(/Withdrawal Method\s*([A-Za-z]+)/i)?.[1] || "";
  const result = {
    executedAt: new Date().toISOString(),
    pageUrl: page.url().replace(/^https?:\/\/[^/]+/i, ""),
    openMode,
    withdrawChannel,
    channelSelected,
    minimum,
    invalidAmount,
    invalidSubmitEnabled,
    invalidGeneratedRequest,
    legalAmount: process.env.EXECUTE_WITHDRAW_UI === "true" ? legalAmount : null,
    walletPasswordEntered,
    confirmationClicked,
    balanceBefore,
    balanceAfter,
    balanceDelta,
    channelUnavailable,
    legalOrderCreated,
    transactionId,
    withdrawalMethod,
    withdrawEvents,
    bodyBefore: bodyBefore.slice(0, 3000),
    bodyAfter: bodyAfter.slice(0, 3000),
  };
  const out = path.resolve("ui/results/client-withdraw-contract.json");
  fs.writeFileSync(out, JSON.stringify(result, null, 2));

  if (process.env.EXECUTE_WITHDRAW_UI === "true") {
    expect(withdrawEvents.some((item) => item.kind === "request")).toBeTruthy();
    expect(legalResponses.length).toBeGreaterThan(0);
    expect(channelUnavailable).toBeFalsy();
    expect(legalOrderCreated).toBeTruthy();
    expect(transactionId).toMatch(/^\d+$/);
    expect(withdrawalMethod.toLowerCase()).toBe(withdrawChannel.toLowerCase());
  }
});
