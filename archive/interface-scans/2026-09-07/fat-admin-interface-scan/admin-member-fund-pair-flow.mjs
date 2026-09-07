import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { chromium } from "playwright";
import { loadEnv, requiredEnv } from "../ui/framework/env.mjs";
import { decodeCbor } from "../ui/framework/cbor-decoder.mjs";

loadEnv(process.env.ENV_FILE || ".env.fat");
const targetFile = process.env.MEMBER_TARGET_FILE || "/tmp/fat-member-lane-kyc_reject.json";
const target = JSON.parse(fs.readFileSync(targetFile, "utf8"));
if (target.environment !== "FAT" || target.target_ref !== "FAT-KYC-REJECT-01") throw new Error("unexpected FAT target");

const baseUrl = requiredEnv("ADMIN_URL");
const origin = new URL(baseUrl).origin;
const output = path.resolve(process.env.MEMBER_FUND_PAIR_OUTPUT || "fat-admin-interface-scan/results/record-flow-member-kyc-reject-fund-pair-flow.json");
const amount = process.env.MEMBER_FUND_PAIR_AMOUNT || "0.01";
const creditOnly = process.env.MEMBER_FUND_PAIR_CREDIT_ONLY === "true";
const walletRecoveryOnly = process.env.MEMBER_FUND_PAIR_WALLET_RECOVERY_ONLY === "true";
const uidRef = "FAT-UID-KYC-REJECT-01";
const network = [];
const requestActions = new WeakMap();
let action = "login";

const result = {
  captured_at: new Date().toISOString(), environment: "FAT", target_ref: target.target_ref, uid_ref: uidRef,
  page_route: "/member-center/detail/{uid}", amount, branches: {}, network,
  raw_phone_or_uid_persisted: false, secrets_persisted: false,
};

const scrub = value => String(value || "")
  .replace(/\b(?:\d{1,3}\.){3}\d{1,3}\b/g, "<redacted-ip>")
  .replace(/(?:\+?63|0)9\d{9}|\b\d{7,}\b/g, "<redacted>")
  .replace(/\s+/g, " ").trim().slice(0, 400);
const normalizePath = pathname => pathname.replace(/\/member-center\/detail\/[^/]+/, "/member-center/detail/{uid}");
const fieldsOf = body => body && typeof body === "object" && !Array.isArray(body) ? Object.keys(body).sort() : [];
const numericString = value => {
  if (value === null || value === undefined) return null;
  const text = String(value).replace(/,/g, "").trim();
  return /^-?\d+(?:\.\d+)?$/.test(text) ? text : null;
};
const scaled = value => {
  const text = numericString(value); if (text === null) throw new Error(`non-numeric balance: ${String(value)}`);
  const negative = text.startsWith("-"); const clean = negative ? text.slice(1) : text;
  const [whole, fraction = ""] = clean.split(".");
  const number = BigInt(whole || "0") * 100n + BigInt((fraction + "00").slice(0, 2));
  return negative ? -number : number;
};

function base32Decode(value) {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567", normalized = value.replace(/\s|=/g, "").toUpperCase(); let bits = "";
  for (const char of normalized) { const index = alphabet.indexOf(char); if (index < 0) throw new Error("invalid approval TOTP secret"); bits += index.toString(2).padStart(5, "0"); }
  const bytes = []; for (let index = 0; index + 8 <= bits.length; index += 8) bytes.push(parseInt(bits.slice(index, index + 8), 2)); return Buffer.from(bytes);
}
function currentTotp() {
  const key = base32Decode(requiredEnv("ADMIN_APPROVAL_TOTP_SECRET"));
  const algorithm = (process.env.ADMIN_APPROVAL_TOTP_ALGORITHM || "SHA1").toLowerCase().replace("-", "");
  const counter = Math.floor(Date.now() / 1000 / 30), message = Buffer.alloc(8); message.writeBigUInt64BE(BigInt(counter));
  const digest = crypto.createHmac(algorithm, key).update(message).digest(), offset = digest[digest.length - 1] & 15;
  return String((digest.readUInt32BE(offset) & 0x7fffffff) % 1000000).padStart(6, "0");
}

const browser = await chromium.launch({ headless: process.env.ADMIN_SCAN_HEADED !== "false" });
const context = await browser.newContext({ ignoreHTTPSErrors: true, viewport: { width: 1600, height: 1000 }, locale: "en-US" });
const page = await context.newPage();

page.on("request", request => requestActions.set(request, action));
page.on("response", async response => {
  const request = response.request(); if (!["xhr", "fetch"].includes(request.resourceType())) return;
  let url; try { url = new URL(response.url()); } catch { return; } if (url.origin !== origin) return;
  let body = null, decoded = null;
  try { const raw = request.postDataBuffer(); if (raw?.length) { const type = (request.headers()["content-type"] || "").toLowerCase(); body = type.includes("json") ? JSON.parse(raw.toString("utf8")) : decodeCbor(new Uint8Array(raw)); } } catch {}
  try { decoded = decodeCbor(new Uint8Array(await response.body())); } catch {}
  const data = decoded?.data;
  const event = {
    action: requestActions.get(request) || action, method: request.method(), path: normalizePath(url.pathname),
    query_fields: [...url.searchParams.keys()].filter(key => !["t", "uid", "phone"].includes(key)).sort(), body_fields: fieldsOf(body),
    http_status: response.status(), business_status: decoded?.status ?? null,
    business_message: scrub(decoded?.message ?? decoded?.msg ?? decoded?.error),
    response_type: Array.isArray(data) ? "list" : data === null ? "null" : typeof data,
    response_keys: fieldsOf(data), response_values_persisted: false,
  };
  if (["/admin/finance/adjust/list", "/admin/finance/tokens/transaction/list"].includes(url.pathname)) {
    const rows = Array.isArray(data) ? data : Array.isArray(data?.d) ? data.d : Array.isArray(data?.list) ? data.list : [];
    event.response_row_count = rows.length;
    event.response_total = typeof data?.t === "number" ? data.t : typeof data?.total === "number" ? data.total : null;
  }
  network.push(event);
});

function checkpoint() { fs.writeFileSync(output, `${JSON.stringify(result, null, 2)}\n`); }
async function quiet() { let last = network.length, stable = Date.now(); for (let index = 0; index < 100; index += 1) { await page.waitForTimeout(100); if (last !== network.length) { last = network.length; stable = Date.now(); } else if (Date.now() - stable > 800) return; } }
async function login() {
  await page.goto(baseUrl, { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.getByPlaceholder(/请输入用户名|user\s*name|email/i).fill(requiredEnv("ADMIN_EMAIL"));
  await page.getByPlaceholder(/请输入密码|password/i).fill(requiredEnv("ADMIN_PASSWORD"));
  await page.getByRole("button", { name: /登\s*录|log\s*in/i }).click();
  const code = page.getByPlaceholder(/谷歌验证|google.*(?:code|verification|authenticator)/i); await code.waitFor({ state: "visible", timeout: 10000 }); await code.fill(requiredEnv("ADMIN_GOOGLE_CODE"));
  await page.getByRole("button", { name: /确\s*定|confirm|ok/i }).click(); await page.waitForURL(url => !url.pathname.startsWith("/user/login"), { timeout: 20000 });
}
async function openDetail(nextAction) {
  action = nextAction;
  const responsePromise = page.waitForResponse(response => new URL(response.url()).pathname === "/admin/member/detail", { timeout: 15000 });
  const walletPromise = page.waitForResponse(response => new URL(response.url()).pathname === "/admin/finance/member/wallet", { timeout: 15000 });
  const targetUrl = new URL(`/member-center/detail/${target.uid}`, baseUrl).toString();
  if (new URL(page.url()).pathname === new URL(targetUrl).pathname) await page.reload({ waitUntil: "domcontentloaded", timeout: 25000 });
  else await page.goto(targetUrl, { waitUntil: "domcontentloaded", timeout: 25000 });
  const [response, walletResponse] = await Promise.all([responsePromise, walletPromise]); const decoded = decodeCbor(new Uint8Array(await response.body())); const walletDecoded = decodeCbor(new Uint8Array(await walletResponse.body())); await quiet();
  if (decoded?.status !== true) throw new Error(`member detail business status ${String(decoded?.status)}`);
  return { wallet: numericString(walletDecoded?.data?.balance) || numericString(decoded?.data?.balance), tokens: numericString(decoded?.data?.tokens_balance) };
}
async function reloadDetailState(nextAction) {
  action = nextAction;
  const responsePromise = page.waitForResponse(response => new URL(response.url()).pathname === "/admin/member/detail", { timeout: 15000 });
  const walletPromise = page.waitForResponse(response => new URL(response.url()).pathname === "/admin/finance/member/wallet", { timeout: 15000 });
  await page.reload({ waitUntil: "domcontentloaded", timeout: 25000 }); const response = await responsePromise;
  const walletResponse = await walletPromise; const decoded = decodeCbor(new Uint8Array(await response.body())); const walletDecoded = decodeCbor(new Uint8Array(await walletResponse.body())); await quiet();
  if (decoded?.status !== true) throw new Error(`detail verification business status ${String(decoded?.status)}`);
  return { wallet: numericString(walletDecoded?.data?.balance) || numericString(decoded?.data?.balance), tokens: numericString(decoded?.data?.tokens_balance) };
}
async function freshTotp() { const remaining = 30 - (Math.floor(Date.now() / 1000) % 30); if (remaining < 8) await page.waitForTimeout((remaining + 1) * 1000); return currentTotp(); }
async function formSnapshot(modal) {
  return {
    title: scrub(await modal.locator(".ant-modal-title,.ant-drawer-title").first().innerText().catch(() => "")),
    fields: await modal.locator(".ant-form-item").evaluateAll(items => items.map(item => ({ label: item.querySelector(".ant-form-item-label")?.innerText.replace(/\s+/g, " ").trim() || "", required: Boolean(item.querySelector(".ant-form-item-required")), control_types: [...item.querySelectorAll("input,textarea")].map(element => element.getAttribute("type") || element.tagName.toLowerCase()) }))),
    radios: (await modal.locator(".ant-radio-wrapper:visible").allInnerTexts()).map(scrub), buttons: (await modal.locator("button:visible").allInnerTexts()).map(scrub).filter(Boolean),
  };
}
async function labeledItem(modal, pattern) {
  const items = modal.locator(".ant-form-item:visible");
  for (let index = 0; index < await items.count(); index += 1) {
    const item = items.nth(index); const label = (await item.locator(".ant-form-item-label").innerText().catch(() => "")).replace(/\s+/g, " ").trim();
    if (pattern.test(label)) return item;
  }
  throw new Error(`form label not found: ${String(pattern)}`);
}
async function fillItem(modal, pattern, value) { const item = await labeledItem(modal, pattern); await item.locator('input:not([type="radio"]):not([type="hidden"]),textarea').first().fill(value); }
async function openExactButton(name, nextAction) {
  action = nextAction;
  const aliases = {
    "Credit or Debit": /^(?:Credit or Debit|上下分)$/i,
    "Token Top-Up and Withdrawal": /^(?:Token Top-Up and Withdrawal|代币上下分)$/i,
  };
  const pattern = aliases[name] || new RegExp(`^${name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}$`, "i");
  const button = page.locator("button:visible").filter({ hasText: pattern }).last();
  await button.waitFor({ state: "visible", timeout: 10000 }); await button.click();
  const modal = page.locator(".ant-modal:visible,.ant-drawer:visible,[role=dialog]:visible").last(); await modal.waitFor({ state: "visible", timeout: 8000 }); return modal;
}
async function submitAdjustment({ buttonName, radioName, branchName, submitAction, wallet = false, creditTurnover = false }) {
  const modal = await openExactButton(buttonName, `open_${submitAction}`); const form = await formSnapshot(modal);
  await modal.getByText(radioName, { exact: true }).click();
  await fillItem(modal, wallet ? /^Adjustment Amount$/i : /^Adjust Token Amount$/i, amount);
  if (creditTurnover) {
    await fillItem(modal, /^Turnover Requirement/i, "0");
    const restrictionItem = await labeledItem(modal, /Turnover Venue\/Game Restrictions|流水.*(?:场馆|游戏)/i);
    const treeSelect = restrictionItem.locator(".ant-tree-select").first();
    await page.waitForFunction(element => !/loading/i.test(element.innerText), await treeSelect.elementHandle(), { timeout: 15000 });
    await treeSelect.click();
    const allGames = page.locator(".ant-select-dropdown:visible .ant-select-tree-treenode:visible").filter({ hasText: /^(?:所有游戏|All Games)$/i }).first();
    await allGames.waitFor({ state: "visible", timeout: 8000 }); await allGames.click();
  }
  await fillItem(modal, /^Adjustment Reason$/i, `FAT current-run reversible ${branchName}`);
  await fillItem(modal, /Google Verification Code/i, await freshTotp());
  const start = network.length; action = submitAction; await modal.getByRole("button", { name: /^OK$/i, exact: true }).click(); await quiet();
  const event = network.slice(start).find(item => !["GET", "HEAD", "OPTIONS"].includes(item.method));
  const validation_errors = await modal.locator(".ant-form-item-explain-error:visible").allInnerTexts().catch(() => []);
  const notifications = (await page.locator(".ant-message-notice:visible,.ant-notification-notice:visible").allInnerTexts()).map(scrub);
  if (!event || event.http_status >= 400 || event.business_status !== true) {
    await page.keyboard.press("Escape").catch(() => {});
    return { form, success: false, event: event || null, validation_errors, notifications };
  }
  await modal.waitFor({ state: "hidden", timeout: 10000 }).catch(() => {});
  return { form, success: true, event, validation_errors, notifications };
}
async function captureCreditLog(nextAction) {
  action = nextAction; const button = page.locator("button:visible").filter({ hasText: /^(?:View Credit\/Debit Records|查看上下分记录)$/i }).last();
  if (!await button.isVisible().catch(() => false)) return { status: "BUTTON_NOT_VISIBLE" };
  const start = network.length; await button.click(); await quiet();
  const event = network.slice(start).find(item => item.path === "/admin/finance/adjust/list");
  return event ? { status: "CAPTURED", method: event.method, path: event.path, http_status: event.http_status, business_status: event.business_status, response_row_count: event.response_row_count, response_total: event.response_total } : { status: "REQUEST_NOT_CAPTURED" };
}
async function enterTokenWallet(nextAction) {
  action = nextAction; const button = page.locator("button:visible").filter({ hasText: /^(?:View Token Wallet|查看代币钱包)$/i }).last(); await button.waitFor({ state: "visible", timeout: 10000 });
  const start = network.length; await button.click(); await quiet();
  const event = network.slice(start).find(item => item.path === "/admin/finance/tokens/transaction/list");
  return event ? { status: "CAPTURED", method: event.method, path: event.path, http_status: event.http_status, business_status: event.business_status, response_row_count: event.response_row_count, response_total: event.response_total } : { status: "REQUEST_NOT_CAPTURED" };
}

try {
  await login();
  const baseline = await openDetail("wallet_baseline");
  result.branches.credit_debit = { status: "RUNNING", before: { wallet: baseline.wallet }, writes_confirmed: 0 };
  checkpoint();
  try {
    if (walletRecoveryOnly) {
      const debit = await submitAdjustment({ buttonName: "Credit or Debit", radioName: "Debit Deduction", branchName: "wallet debit recovery", submitAction: "wallet_debit_recovery", wallet: true });
      result.branches.credit_debit.debit_recovery = debit; checkpoint();
      if (!debit.success) throw new Error("debit recovery write failed");
      result.branches.credit_debit.writes_confirmed = 1;
      const restored = await reloadDetailState("verify_wallet_recovery"); result.branches.credit_debit.after_recovery = { wallet: restored.wallet };
      result.branches.credit_debit.expected_restored_wallet = String(Number(baseline.wallet) - Number(amount));
      result.branches.credit_debit.restored = scaled(restored.wallet) === scaled(baseline.wallet) - scaled(amount);
      result.branches.credit_debit.restore_log = await captureCreditLog("verify_wallet_recovery_log");
      result.branches.credit_debit.status = result.branches.credit_debit.restored ? "RECOVERY_EXECUTED_RESTORED" : "RECOVERY_STATE_MISMATCH";
    } else {
    const credit = await submitAdjustment({ buttonName: "Credit or Debit", radioName: "Credit Top‑up", branchName: "wallet credit", submitAction: "wallet_credit", wallet: true, creditTurnover: true });
    result.branches.credit_debit.credit = credit; checkpoint();
    if (!credit.success) throw new Error("credit write failed; debit not attempted");
    result.branches.credit_debit.writes_confirmed += 1;
    const afterCredit = await reloadDetailState("verify_wallet_credit"); result.branches.credit_debit.after_credit = { wallet: afterCredit.wallet };
    if (scaled(afterCredit.wallet) !== scaled(baseline.wallet) + scaled(amount)) throw new Error("wallet credit state mismatch");
    result.branches.credit_debit.credit_log = await captureCreditLog("verify_wallet_credit_log");
    await openDetail("return_detail_for_wallet_restore");
    const debit = await submitAdjustment({ buttonName: "Credit or Debit", radioName: "Debit Deduction", branchName: "wallet debit restore", submitAction: "wallet_debit_restore", wallet: true });
    result.branches.credit_debit.debit_restore = debit; checkpoint();
    if (!debit.success) throw new Error("debit restore write failed");
    result.branches.credit_debit.writes_confirmed += 1;
    const restored = await reloadDetailState("verify_wallet_restored"); result.branches.credit_debit.after_restore = { wallet: restored.wallet };
    result.branches.credit_debit.restored = scaled(restored.wallet) === scaled(baseline.wallet);
    result.branches.credit_debit.restore_log = await captureCreditLog("verify_wallet_restore_log");
    result.branches.credit_debit.status = result.branches.credit_debit.restored ? "EXECUTED_RESTORED" : "RESTORE_STATE_MISMATCH";
    }
  } catch (error) {
    await page.keyboard.press("Escape").catch(() => {}); await page.waitForTimeout(250);
    result.branches.credit_debit.status = result.branches.credit_debit.writes_confirmed ? "FAILED_AFTER_SIDE_EFFECT" : "FAILED_STOPPED_BRANCH";
    result.branches.credit_debit.error = scrub(error?.message || error);
  }
  checkpoint();

  if (!creditOnly && !walletRecoveryOnly) {
  const tokenBaseline = await openDetail("token_baseline");
  result.branches.token_topup_withdrawal = { status: "RUNNING", before: { tokens: tokenBaseline.tokens }, writes_confirmed: 0 };
  result.branches.token_topup_withdrawal.baseline_log = await enterTokenWallet("token_wallet_baseline_log"); checkpoint();
  try {
    const topup = await submitAdjustment({ buttonName: "Token Top-Up and Withdrawal", radioName: "Token Top-Up", branchName: "token top-up", submitAction: "token_topup" });
    result.branches.token_topup_withdrawal.topup = topup; checkpoint();
    if (!topup.success) throw new Error("token top-up failed; withdrawal not attempted");
    result.branches.token_topup_withdrawal.writes_confirmed += 1;
    const afterTopup = await reloadDetailState("verify_token_topup"); result.branches.token_topup_withdrawal.after_topup = { tokens: afterTopup.tokens };
    if (scaled(afterTopup.tokens) !== scaled(tokenBaseline.tokens) + scaled(amount)) throw new Error("token top-up state mismatch");
    result.branches.token_topup_withdrawal.topup_log = await enterTokenWallet("verify_token_topup_log");
    await openDetail("return_detail_for_token_restore"); await enterTokenWallet("return_token_wallet_for_restore");
    const withdrawal = await submitAdjustment({ buttonName: "Token Top-Up and Withdrawal", radioName: "Token Withdrawal", branchName: "token withdrawal restore", submitAction: "token_withdrawal_restore" });
    result.branches.token_topup_withdrawal.withdrawal_restore = withdrawal; checkpoint();
    if (!withdrawal.success) throw new Error("token withdrawal restore failed");
    result.branches.token_topup_withdrawal.writes_confirmed += 1;
    const tokenRestored = await reloadDetailState("verify_token_restored"); result.branches.token_topup_withdrawal.after_restore = { tokens: tokenRestored.tokens };
    result.branches.token_topup_withdrawal.restored = scaled(tokenRestored.tokens) === scaled(tokenBaseline.tokens);
    result.branches.token_topup_withdrawal.restore_log = await enterTokenWallet("verify_token_restore_log");
    result.branches.token_topup_withdrawal.status = result.branches.token_topup_withdrawal.restored ? "EXECUTED_RESTORED" : "RESTORE_STATE_MISMATCH";
  } catch (error) {
    await page.keyboard.press("Escape").catch(() => {}); await page.waitForTimeout(250);
    result.branches.token_topup_withdrawal.status = result.branches.token_topup_withdrawal.writes_confirmed ? "FAILED_AFTER_SIDE_EFFECT" : "FAILED_STOPPED_BRANCH";
    result.branches.token_topup_withdrawal.error = scrub(error?.message || error);
  }
  }
} catch (error) {
  result.fatal_error = scrub(error?.message || error);
} finally {
  result.captured_at = new Date().toISOString(); checkpoint(); await browser.close();
}

console.log(JSON.stringify({ target_ref: result.target_ref, amount: result.amount, branches: Object.fromEntries(Object.entries(result.branches).map(([name, value]) => [name, { status: value.status, writes_confirmed: value.writes_confirmed, restored: value.restored ?? false, error: value.error || "" }])), fatal_error: result.fatal_error || "" }));
