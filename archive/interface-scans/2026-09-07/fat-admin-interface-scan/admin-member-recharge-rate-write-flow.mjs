import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { chromium } from "playwright";
import { loadEnv, requiredEnv } from "../ui/framework/env.mjs";
import { decodeCbor } from "../ui/framework/cbor-decoder.mjs";

loadEnv(process.env.ENV_FILE || ".env.fat");
const target = JSON.parse(fs.readFileSync(process.env.MEMBER_TARGET_FILE || "/tmp/fat-member-lane-kyc_reject.json", "utf8"));
if (target.environment !== "FAT" || target.target_ref !== "FAT-KYC-REJECT-01") throw new Error("unexpected approved FAT target");
const baseUrl = requiredEnv("ADMIN_URL");
const origin = new URL(baseUrl).origin;
const output = path.resolve("fat-admin-interface-scan/results/record-flow-member-recharge-rate-write-flow.json");
const network = [];
const states = [];
const requestActions = new WeakMap();
let action = "login";
const safeMessage = value => String(value || "").replace(/(?:\+?63|0)9\d{9}|\b\d{7,}\b/g, "<redacted>").replace(/\s+/g, " ").trim().slice(0, 300);

function base32Decode(value) {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  const normalized = value.replace(/\s|=/g, "").toUpperCase();
  let bits = "";
  for (const char of normalized) {
    const index = alphabet.indexOf(char);
    if (index < 0) throw new Error("invalid approval TOTP secret");
    bits += index.toString(2).padStart(5, "0");
  }
  const bytes = [];
  for (let index = 0; index + 8 <= bits.length; index += 8) bytes.push(parseInt(bits.slice(index, index + 8), 2));
  return Buffer.from(bytes);
}

function currentApprovalTotp() {
  const key = base32Decode(requiredEnv("ADMIN_APPROVAL_TOTP_SECRET"));
  const algorithm = (process.env.ADMIN_APPROVAL_TOTP_ALGORITHM || "SHA1").toLowerCase().replace("-", "");
  const counter = Math.floor(Date.now() / 1000 / 30);
  const message = Buffer.alloc(8);
  message.writeBigUInt64BE(BigInt(counter));
  const digest = crypto.createHmac(algorithm, key).update(message).digest();
  const offset = digest[digest.length - 1] & 15;
  return String((digest.readUInt32BE(offset) & 0x7fffffff) % 1000000).padStart(6, "0");
}

const browser = await chromium.launch({ headless: process.env.ADMIN_SCAN_HEADED !== "false" });
const context = await browser.newContext({ ignoreHTTPSErrors: true, viewport: { width: 1600, height: 1000 }, locale: "en-US" });
const page = await context.newPage();
page.on("request", request => requestActions.set(request, action));
page.on("response", async response => {
  const request = response.request();
  if (!["xhr", "fetch"].includes(request.resourceType())) return;
  let url;
  try { url = new URL(response.url()); } catch { return; }
  if (url.origin !== origin || !["/admin/member/detail", "/admin/member/deposit/multiple/update", "/admin/member/deposit/multiple/log"].includes(url.pathname)) return;
  let decoded = null;
  let bodyFields = [];
  try {
    const raw = request.postDataBuffer();
    if (raw?.length) {
      const type = (request.headers()["content-type"] || "").toLowerCase();
      const body = type.includes("json") ? JSON.parse(raw.toString("utf8")) : decodeCbor(new Uint8Array(raw));
      if (body && typeof body === "object" && !Array.isArray(body)) bodyFields = Object.keys(body).sort();
    }
  } catch {}
  try { decoded = decodeCbor(new Uint8Array(await response.body())); } catch {}
  const eventAction = requestActions.get(request) || action;
  const event = {
    action: eventAction, method: request.method(), path: url.pathname,
    query_fields: [...url.searchParams.keys()].filter(key => key !== "t").sort(), body_fields: bodyFields,
    http_status: response.status(), business_status: decoded?.status ?? null,
    business_message: safeMessage(decoded?.message ?? decoded?.msg ?? decoded?.error),
    response_top_keys: decoded && typeof decoded === "object" ? Object.keys(decoded).sort() : [],
    response_safe_scalars: decoded && typeof decoded === "object" ? Object.fromEntries(Object.entries(decoded).filter(([key, value]) => key !== "data" && key !== "d" && ["string", "number", "boolean"].includes(typeof value)).map(([key, value]) => [key, typeof value === "string" ? safeMessage(value) : value])) : {},
    response_keys: decoded?.data && typeof decoded.data === "object" ? Object.keys(decoded.data).sort() : [],
    response_values_persisted: false,
  };
  network.push(event);
  if (url.pathname === "/admin/member/detail" && decoded?.data) {
    states.push({ action: eventAction, deposit_multiple: decoded.data.deposit_multiple, deposit_multiple_type: decoded.data.deposit_multiple_type, platform_deposit_multiple: decoded.data.platform_deposit_multiple });
  }
});

async function quiet() {
  let last = network.length;
  let stable = Date.now();
  for (let index = 0; index < 100; index += 1) {
    await page.waitForTimeout(100);
    if (last !== network.length) { last = network.length; stable = Date.now(); }
    else if (Date.now() - stable > 800) return;
  }
}

async function login() {
  await page.goto(baseUrl, { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.getByPlaceholder(/请输入用户名|user\s*name|email/i).fill(requiredEnv("ADMIN_EMAIL"));
  await page.getByPlaceholder(/请输入密码|password/i).fill(requiredEnv("ADMIN_PASSWORD"));
  await page.getByRole("button", { name: /登\s*录|log\s*in/i }).click();
  const code = page.getByPlaceholder(/谷歌验证|google.*(?:code|verification|authenticator)/i);
  await code.waitFor({ state: "visible", timeout: 10000 });
  await code.fill(requiredEnv("ADMIN_GOOGLE_CODE"));
  await page.getByRole("button", { name: /确\s*定|confirm|ok/i }).click();
  await page.waitForURL(url => !url.pathname.startsWith("/user/login"), { timeout: 20000 });
}

async function rateItem() {
  const item = page.locator(".ant-descriptions-item").filter({ hasText: /General recharge rate|一般充值倍率|通用充值倍率/i }).first();
  await item.waitFor({ state: "visible", timeout: 10000 });
  return item;
}

async function openEdit() {
  const item = await rateItem();
  let edit = item.locator('[data-icon="edit"],.anticon-edit').first();
  if (!await edit.count()) edit = item.locator("button,a,[role=button]").first();
  const targetControl = edit.locator("xpath=ancestor-or-self::button[1] | ancestor-or-self::a[1] | ancestor-or-self::*[@role='button'][1]").first();
  if (await targetControl.count()) await targetControl.click(); else await edit.click();
  const modal = page.locator(".ant-modal:visible").last();
  await modal.waitFor({ state: "visible", timeout: 8000 });
  return modal;
}

async function selectOption(modal, label) {
  await modal.locator(".ant-select:visible").first().click();
  await page.locator(".ant-select-dropdown:visible .ant-select-item-option").filter({ hasText: new RegExp(`^\\s*${label}\\s*$`, "i") }).click();
}

async function submitCustom() {
  action = "open_edit_for_custom";
  const modal = await openEdit();
  await selectOption(modal, "Custom");
  await modal.getByPlaceholder(/custom recharge rate/i).fill(process.env.CUSTOM_RECHARGE_RATE || "1.0");
  await modal.locator("textarea").fill("FAT interface discovery reversible custom-rate check");
  await modal.getByPlaceholder(/google.*verification code/i).fill(currentApprovalTotp());
  action = "submit_custom_rate";
  await modal.getByRole("button", { name: /^OK$/i }).click();
  await modal.waitFor({ state: "hidden", timeout: 12000 });
  await quiet();
}

async function submitRestore() {
  action = "open_edit_for_restore";
  const modal = await openEdit();
  await selectOption(modal, "Platform Configuration");
  await modal.locator("textarea").fill("FAT interface discovery restore platform configuration");
  await modal.getByPlaceholder(/google.*verification code/i).fill(currentApprovalTotp());
  action = "submit_restore_platform_rate";
  await modal.getByRole("button", { name: /^OK$/i }).click();
  await modal.waitFor({ state: "hidden", timeout: 12000 });
  await quiet();
}

async function reloadDetail(nextAction) {
  action = nextAction;
  const detailResponse = page.waitForResponse(response => new URL(response.url()).pathname === "/admin/member/detail", { timeout: 15000 });
  await page.reload({ waitUntil: "domcontentloaded", timeout: 25000 });
  await detailResponse;
  await quiet();
}

try {
  await login();
  action = "baseline_member_detail";
  const baselineResponse = page.waitForResponse(response => new URL(response.url()).pathname === "/admin/member/detail", { timeout: 15000 });
  await page.goto(new URL(`/member-center/detail/${target.uid}`, baseUrl).toString(), { waitUntil: "domcontentloaded", timeout: 25000 });
  await baselineResponse;
  await quiet();
  const baseline = states.at(-1);
  if (!baseline) throw new Error("member detail baseline unavailable");
  let customState;
  let writes = 0;
  let executionMode = "platform_to_custom_to_platform";
  if (Number(baseline.deposit_multiple_type) === 1) {
    await submitCustom();
    writes += 1;
    await reloadDetail("verify_custom_member_detail");
    customState = states.at(-1);
    if (Number(customState?.deposit_multiple_type) !== 2) throw new Error(`custom rate did not persist: ${JSON.stringify(customState)}`);
  } else if (Number(baseline.deposit_multiple_type) === 2 && Number(baseline.deposit_multiple) === Number(process.env.CUSTOM_RECHARGE_RATE || "1.0")) {
    executionMode = "recover_existing_current_run_custom_to_platform";
    customState = baseline;
  } else {
    throw new Error(`refusing unexpected recharge-rate baseline: ${JSON.stringify(baseline)}`);
  }

  await submitRestore();
  writes += 1;
  await reloadDetail("verify_restored_member_detail");
  const restoredState = states.at(-1);
  if (Number(restoredState?.deposit_multiple_type) !== 1) throw new Error(`platform rate restore did not persist: ${JSON.stringify(restoredState)}`);

  action = "verify_operation_records";
  const item = await rateItem();
  const recordsButton = item.getByRole("button", { name: /operating record|操作记录/i }).first();
  if (await recordsButton.count()) await recordsButton.click(); else await item.getByText(/operating record|操作记录/i).first().click();
  const recordsModal = page.locator(".ant-modal:visible").last();
  await recordsModal.waitFor({ state: "visible", timeout: 8000 });
  await quiet();
  const logRows = await recordsModal.locator("tbody tr").count();

  fs.writeFileSync(output, `${JSON.stringify({
    captured_at: new Date().toISOString(), environment: "FAT", target_ref: target.target_ref,
    page_route: "/member-center/detail/{uid}", endpoint: "/admin/member/deposit/multiple/update",
    execution_mode: executionMode,
    before: baseline, after_custom: customState, after_restore: restoredState,
    restored_to_original_platform_mode: Number(restoredState.deposit_multiple_type) === 1,
    operation_log_rows: logRows, writes, raw_phone_or_uid_persisted: false, network,
  }, null, 2)}\n`);
  console.log(JSON.stringify({ target_ref: target.target_ref, execution_mode: executionMode, before: baseline, after_custom: customState, after_restore: restoredState, restored_to_original_platform_mode: Number(restoredState.deposit_multiple_type) === 1, operation_log_rows: logRows, update_events: network.filter(event => event.path.endsWith("/update")), writes }));
} catch (error) {
  const modal = page.locator(".ant-modal:visible").last();
  const diagnostic = {
    captured_at: new Date().toISOString(), environment: "FAT", target_ref: target.target_ref,
    page_route: "/member-center/detail/{uid}", failed_action: action,
    error: String(error?.message || error).split("\n")[0], states,
    visible_modal_text: await modal.count() ? (await modal.innerText()).replace(/(?:\+?63|0)9\d{9}|\b\d{7,}\b/g, "<redacted>").replace(/\s+/g, " ").trim().slice(0, 1200) : "",
    validation_errors: await page.locator(".ant-form-item-explain-error:visible").allInnerTexts(),
    notifications: await page.locator(".ant-message-notice:visible,.ant-notification-notice:visible").allInnerTexts(),
    network, writes_confirmed: network.filter(event => event.path === "/admin/member/deposit/multiple/update" && event.business_status === true).length,
    raw_phone_or_uid_persisted: false,
  };
  fs.writeFileSync(output, `${JSON.stringify(diagnostic, null, 2)}\n`);
  console.error(JSON.stringify(diagnostic));
  throw error;
} finally {
  await browser.close();
}
