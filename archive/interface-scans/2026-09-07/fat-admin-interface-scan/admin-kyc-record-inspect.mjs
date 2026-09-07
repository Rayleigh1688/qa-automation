import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { chromium } from "playwright";
import { loadEnv, requiredEnv } from "../ui/framework/env.mjs";
import { decodeCbor } from "../ui/framework/cbor-decoder.mjs";

loadEnv(process.env.ENV_FILE || ".env.fat");
const baseUrl = requiredEnv("ADMIN_URL");
const origin = new URL(baseUrl).origin;
const out = path.resolve(process.env.KYC_ADMIN_OUTPUT || "fat-admin-interface-scan/results/record-flow-kyc-ui-inventory.json");
const runtimeTargetPath = process.env.KYC_TARGET_FILE || "/tmp/fat-record-flow-target.json";
const runtimeTarget = fs.existsSync(runtimeTargetPath) ? JSON.parse(fs.readFileSync(runtimeTargetPath, "utf8")) : null;
const queryPhone = String(runtimeTarget?.phone || requiredEnv("KYC_CLIENT_PHONE"));
const targetRef = String(runtimeTarget?.target_ref || "KYC-EXISTING-READONLY");
const reviewDecision = String(process.env.KYC_REVIEW_DECISION || "APPROVE").toUpperCase();
const reviewProbeOnly = process.env.KYC_REVIEW_PROBE_ONLY === "true";
if (!['APPROVE', 'REJECT'].includes(reviewDecision)) throw new Error(`invalid KYC_REVIEW_DECISION=${reviewDecision}`);
const sanitize = (value) => String(value ?? "")
  .replace(/\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi, "<redacted-email>")
  .replace(/(?<!\d)(?:\+?63|0)?9\d{9}(?!\d)/g, "<redacted-phone>")
  .replace(/(?<!\d)\d{6,}(?!\d)/g, "<redacted-numeric-id>")
  .trim();

function shape(decoded) {
  const data = decoded?.data;
  return {
    top_level_keys: decoded && typeof decoded === "object" ? Object.keys(decoded).sort() : [],
    data_type: Array.isArray(data) ? "list" : data === null ? "null" : typeof data,
    data_keys: data && typeof data === "object" && !Array.isArray(data) ? Object.keys(data).sort() : [],
  };
}

function safeSummary(decoded) {
  const data = decoded?.data;
  if (!data || typeof data !== "object") return {};
  const list = Array.isArray(data.d) ? data.d : Array.isArray(data.list) ? data.list : null;
  return {
    ...(list ? { list_count: list.length } : {}),
    ...(typeof data.t === "number" ? { total: data.t } : {}),
    ...(typeof data.s === "number" ? { secondary_count: data.s } : {}),
  };
}

function currentTotp(secret, algorithm = "SHA256") {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  const normalized = secret.replace(/\s+/g, "").replace(/=+$/g, "").toUpperCase();
  let bits = "";
  for (const char of normalized) {
    const value = alphabet.indexOf(char);
    if (value < 0) throw new Error("invalid approval TOTP secret encoding");
    bits += value.toString(2).padStart(5, "0");
  }
  const bytes = [];
  for (let index = 0; index + 8 <= bits.length; index += 8) bytes.push(Number.parseInt(bits.slice(index, index + 8), 2));
  const counter = Math.floor(Date.now() / 1000 / 30);
  const message = Buffer.alloc(8);
  message.writeBigUInt64BE(BigInt(counter));
  const digest = crypto.createHmac(algorithm.toLowerCase().replace("-", ""), Buffer.from(bytes)).update(message).digest();
  const offset = digest[digest.length - 1] & 0x0f;
  const binary = digest.readUInt32BE(offset) & 0x7fffffff;
  return String(binary % 1_000_000).padStart(6, "0");
}

async function dialogControls(page) {
  const dialog = page.locator("[role=dialog]:visible, .ant-modal:visible, .ant-drawer:visible").last();
  if (!(await dialog.count())) return null;
  const result = await dialog.evaluate((node) => ({
    title: (node.querySelector(".ant-modal-title,.ant-drawer-title")?.textContent || "").trim(),
    tabs: [...node.querySelectorAll("[role=tab],.ant-tabs-tab")].map((x) => (x.textContent || "").trim()).filter(Boolean),
    inputs: [...node.querySelectorAll("input,textarea")].map((x) => ({ type: x.type || x.tagName.toLowerCase(), placeholder: x.placeholder || "", disabled: Boolean(x.disabled) })),
    selects: [...node.querySelectorAll(".ant-select")].map((x) => (x.textContent || "").trim()).filter(Boolean),
    buttons: [...node.querySelectorAll("button")].map((x) => ({ text: (x.innerText || x.textContent || "").trim(), title: x.title || "", aria: x.getAttribute("aria-label") || "", disabled: Boolean(x.disabled) })),
    labels: [...node.querySelectorAll("label,.ant-form-item-label")].map((x) => (x.textContent || "").trim()).filter(Boolean),
  }));
  return JSON.parse(JSON.stringify(result), (_key, value) => typeof value === "string" ? sanitize(value) : value);
}

const browser = await chromium.launch({ headless: process.env.ADMIN_SCAN_HEADED === "false" });
const context = await browser.newContext({ ignoreHTTPSErrors: true, viewport: { width: 1440, height: 1000 }, locale: "en-US" });
const page = await context.newPage();
const network = [];
const actions = [];
let currentAction = "login";
let rowFound = false;

page.on("response", async (response) => {
  const request = response.request();
  if (!["xhr", "fetch"].includes(request.resourceType())) return;
  const url = new URL(response.url());
  if (url.origin !== origin) return;
  const event = { action: currentAction, method: request.method(), path: url.pathname, query_fields: [...url.searchParams.keys()].filter((x) => x !== "t").sort(), body_fields: [], http_status: response.status(), business_status: null, response_shape: {}, response_summary: {} };
  try {
    const raw = request.postDataBuffer();
    if (raw?.length) {
      const decoded = decodeCbor(new Uint8Array(raw));
      if (decoded && typeof decoded === "object" && !Array.isArray(decoded)) event.body_fields = Object.keys(decoded).sort();
    }
  } catch {}
  try {
    const decoded = decodeCbor(new Uint8Array(await response.body()));
    event.business_status = decoded?.status ?? null;
    event.response_shape = shape(decoded);
    event.response_summary = safeSummary(decoded);
  } catch {}
  network.push(event);
});

async function login() {
  await page.goto(baseUrl, { waitUntil: "domcontentloaded" });
  await page.getByPlaceholder(/请输入用户名|user\s*name|email/i).fill(requiredEnv("ADMIN_EMAIL"));
  await page.getByPlaceholder(/请输入密码|password/i).fill(requiredEnv("ADMIN_PASSWORD"));
  await page.getByRole("button", { name: /登\s*录|log\s*in/i }).click();
  const verification = page.getByPlaceholder(/谷歌验证|google.*(?:code|verification|authenticator)/i);
  await verification.waitFor({ state: "visible", timeout: 10_000 });
  await verification.fill(requiredEnv("ADMIN_GOOGLE_CODE"));
  await page.getByRole("button", { name: /确\s*定|confirm|ok/i }).click();
  await page.waitForURL((url) => !url.pathname.startsWith("/user/login"), { timeout: 20_000 });
}

async function recordAction(name, fn) {
  currentAction = name;
  const start = network.length;
  let status = "COMPLETED", error = "", controls = null;
  try { await fn(); await page.waitForTimeout(700); controls = await dialogControls(page); }
  catch (caught) { status = "FAILED"; error = sanitize(caught?.message || caught); }
  actions.push({ name, status, final_path: new URL(page.url()).pathname, dialog_or_drawer_controls: controls, network_event_indexes: Array.from({ length: network.length - start }, (_, index) => start + index), error });
}

try {
  await login();
  await recordAction("open KYC page", async () => {
    await page.goto(new URL("/kyc", baseUrl).toString(), { waitUntil: "domcontentloaded" });
    await page.waitForURL((url) => url.pathname === "/kyc", { timeout: 15_000 });
  });
  if (new URL(page.url()).pathname !== "/kyc") throw new Error(`KYC route guard failed; final=${new URL(page.url()).pathname}`);
  const headers = await page.locator(".ant-table-thead th").allTextContents();
  const topControls = {
    table_headers: headers.map(sanitize).filter(Boolean),
    inputs: (await page.locator(".ant-layout-content input").evaluateAll((nodes) => nodes.map((x) => ({ type: x.type, placeholder: x.placeholder || "", disabled: Boolean(x.disabled) })))).map((item) => ({ ...item, placeholder: sanitize(item.placeholder) })),
    buttons: (await page.locator(".ant-layout-content button").evaluateAll((nodes) => nodes.map((x) => ({ text: (x.innerText || x.textContent || "").trim(), title: x.title || "", aria: x.getAttribute("aria-label") || "", disabled: Boolean(x.disabled) })))).map((item) => Object.fromEntries(Object.entries(item).map(([key, value]) => [key, typeof value === "string" ? sanitize(value) : value]))),
    selects: (await page.locator(".ant-layout-content .ant-select").evaluateAll((nodes) => nodes.map((x) => ({ text: (x.textContent || "").trim(), class_name: x.className || "" })))).map((item) => ({ ...item, text: sanitize(item.text) })),
  };

  await recordAction("open EKYC Config", async () => { await page.getByRole("button", { name: "EKYC Config", exact: true }).click(); });
  const closeConfig = page.locator(".ant-modal:visible .ant-modal-close, .ant-drawer:visible .ant-drawer-close").last();
  if (await closeConfig.isVisible().catch(() => false)) await closeConfig.click();

  await recordAction("confirm under review status", async () => {
    const statusText = await page.locator(".ant-layout-content .ant-select").first().innerText();
    if (!/Under Review/i.test(statusText)) throw new Error(`expected Under Review status; actual=${sanitize(statusText)}`);
  });

  await recordAction("query configured read-only KYC member", async () => {
    await page.getByPlaceholder("Please Enter Phone Number").fill(queryPhone);
    await page.getByRole("button", { name: "Query", exact: true }).click();
  });

  const rows = page.locator(".ant-table-tbody tr.ant-table-row");
  const rowCount = await rows.count();
  const queryEvent = [...network].reverse().find((item) => item.action === "query configured read-only KYC member" && item.path === "/admin/kyc/list");
  rowFound = rowCount === 1 || queryEvent?.response_summary?.list_count === 1;
  let rowActionControls = [];
  if (rowFound) {
    const row = rows.first();
    rowActionControls = await row.locator("button,a,[role=button]").evaluateAll((nodes) => nodes.map((x) => ({ text: (x.innerText || x.textContent || "").trim(), title: x.title || "", aria: x.getAttribute("aria-label") || "", disabled: Boolean(x.disabled), icon: x.querySelector("svg")?.getAttribute("data-icon") || "", class_name: x.className || "" })));
    rowActionControls = rowActionControls.map((item) => Object.fromEntries(Object.entries(item).map(([key, value]) => [key, typeof value === "string" ? sanitize(value) : value])));
    const safeAction = row.locator('button[title*="detail" i],button[aria-label*="detail" i],a[title*="detail" i],button[title*="view" i],a[title*="view" i],button:has(svg[data-icon*="eye" i]),a:has(svg[data-icon*="eye" i])').first();
    if (await safeAction.isVisible({ timeout: 1000 }).catch(() => false)) {
      await recordAction("open configured member row detail", async () => { await safeAction.click(); });
    }
    for (const controlName of ["Edit", "Change Log"]) {
      await recordAction(`open this-run KYC ${controlName}`, async () => {
        await row.getByRole("button", { name: new RegExp(`^${controlName}$`, "i") }).click();
      });
      const close = page.locator(".ant-modal:visible .ant-modal-close, .ant-drawer:visible .ant-drawer-close").last();
      if (await close.isVisible({ timeout: 1000 }).catch(() => false)) await close.click();
      else {
        const cancel = page.locator(".ant-modal:visible").getByRole("button", { name: /^No$|^Cancel$|^Close$/i }).first();
        if (await cancel.isVisible({ timeout: 1000 }).catch(() => false)) await cancel.click();
      }
    }
    await recordAction("open this-run KYC Review", async () => {
      await row.getByRole("button", { name: /^Review$/i }).click();
    });
    await recordAction(`confirm ${reviewDecision === 'REJECT' ? 'Reject' : 'Approve'} Application selection`, async () => {
      const review = page.locator(".ant-modal:visible").last();
      if (reviewDecision === 'REJECT') {
        await review.locator('.ant-select').first().click();
        const reject = page.locator('.ant-select-dropdown:visible .ant-select-item-option').filter({ hasText: /^\s*Reject Application\s*$/i }).first();
        await reject.click();
      }
      const remarks = review.getByPlaceholder("Please Enter Remarks");
      if (await remarks.isVisible({ timeout: 1000 }).catch(() => false)) await remarks.fill("FAT controlled KYC interface discovery");
      if (!reviewProbeOnly) await review.getByRole("button", { name: /^OK$/i }).click();
    });
    const reviewPath = reviewDecision === 'REJECT' ? '/admin/kyc/reject' : '/admin/kyc/approve';
    let reviewEvent = [...network].reverse().find((item) => item.path === reviewPath);
    if (!reviewProbeOnly && reviewEvent?.business_status === false) throw new Error(`admin KYC ${reviewDecision.toLowerCase()} business failure; branch stopped`);
    if (!reviewProbeOnly && !reviewEvent) {
      await recordAction("dynamic TOTP approval confirmation", async () => {
        const secret = process.env.ADMIN_APPROVAL_TOTP_SECRET || "";
        if (!secret) throw new Error("ADMIN_APPROVAL_TOTP_SECRET unavailable");
        const modal = page.locator(".ant-modal:visible").last();
        const verification = modal.locator("input:visible").last();
        if (!(await verification.isVisible({ timeout: 3000 }).catch(() => false))) throw new Error("approval verification input unavailable");
        await verification.fill(currentTotp(secret, process.env.ADMIN_APPROVAL_TOTP_ALGORITHM || "SHA256"));
        const confirm = modal.getByRole("button", { name: /^OK$|^Confirm$/i }).last();
        await confirm.click();
      });
      reviewEvent = [...network].reverse().find((item) => item.path === reviewPath);
      if (!reviewEvent || reviewEvent.business_status !== true) throw new Error(`dynamic TOTP KYC ${reviewDecision.toLowerCase()} did not return business success`);
    }
  }

  fs.writeFileSync(out, JSON.stringify({ captured_at: new Date().toISOString(), environment: "FAT", target_ref: targetRef, page: "/kyc", top_controls: topControls, row_found: rowFound, row_action_controls: rowActionControls, actions, network }, null, 2) + "\n");
} finally {
  await browser.close();
}

console.log(JSON.stringify({ actions: actions.length, rowFound, network: network.length }));
