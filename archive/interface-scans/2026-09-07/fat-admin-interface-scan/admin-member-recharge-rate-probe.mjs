import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";
import { loadEnv, requiredEnv } from "../ui/framework/env.mjs";
import { decodeCbor } from "../ui/framework/cbor-decoder.mjs";

loadEnv(process.env.ENV_FILE || ".env.fat");
const target = JSON.parse(fs.readFileSync(process.env.MEMBER_TARGET_FILE || "/tmp/fat-member-lane-kyc_reject.json", "utf8"));
if (target.environment !== "FAT" || target.target_ref !== "FAT-KYC-REJECT-01") throw new Error("unexpected approved FAT target");

const baseUrl = requiredEnv("ADMIN_URL");
const origin = new URL(baseUrl).origin;
const output = path.resolve("fat-admin-interface-scan/results/record-flow-member-recharge-rate-controls.json");
const network = [];
const requestActions = new WeakMap();
let action = "login";

const scrub = value => String(value || "")
  .replace(/\b(?:\d{1,3}\.){3}\d{1,3}\b/g, "<redacted-ip>")
  .replace(/(?:\+?63|0)9\d{9}|\b\d{7,}\b/g, "<redacted>")
  .replace(/\s+/g, " ").trim().slice(0, 800);

function profile(data) {
  const value = Array.isArray(data) ? data : data && typeof data === "object"
    ? (Array.isArray(data.d) ? data.d : Array.isArray(data.list) ? data.list : data)
    : data;
  if (Array.isArray(value)) {
    const sample = value.find(item => item && typeof item === "object");
    return { type: "list", count: value.length, item_keys: sample ? Object.keys(sample).sort() : [] };
  }
  if (value && typeof value === "object") return { type: "object", keys: Object.keys(value).sort() };
  return { type: value === null ? "null" : typeof value };
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
  if (url.origin !== origin) return;
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
  network.push({
    action: requestActions.get(request) || action,
    method: request.method(),
    path: url.pathname,
    query_fields: [...url.searchParams.keys()].filter(key => key !== "t").sort(),
    body_fields: bodyFields,
    http_status: response.status(),
    business_status: decoded?.status ?? null,
    response_profile: profile(decoded?.data),
    response_values_persisted: false,
  });
});

async function quiet() {
  let last = network.length;
  let stable = Date.now();
  for (let index = 0; index < 80; index += 1) {
    await page.waitForTimeout(100);
    if (last !== network.length) { last = network.length; stable = Date.now(); }
    else if (Date.now() - stable > 700) return;
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

async function modalSnapshot(modal) {
  return {
    title: scrub(await modal.locator(".ant-modal-title").first().innerText().catch(() => "")),
    fields: await modal.locator(".ant-form-item").evaluateAll(items => items.map((item, index) => ({
      index,
      label: (item.querySelector(".ant-form-item-label")?.innerText || "").replace(/\s+/g, " ").trim(),
      required: Boolean(item.querySelector(".ant-form-item-required")),
      controls: [...item.querySelectorAll("input,textarea")].map(element => ({
        type: element.getAttribute("type") || element.tagName.toLowerCase(),
        placeholder: element.getAttribute("placeholder") || "",
        disabled: element.disabled,
      })),
    }))),
    select_texts: (await modal.locator(".ant-select:visible").allInnerTexts()).map(scrub),
    buttons: (await modal.locator("button:visible").allInnerTexts()).map(scrub).filter(Boolean),
  };
}

try {
  await login();
  action = "open_member_detail";
  await page.goto(new URL(`/member-center/detail/${target.uid}`, baseUrl).toString(), { waitUntil: "domcontentloaded", timeout: 25000 });
  await quiet();

  const rateItem = page.locator(".ant-descriptions-item").filter({ hasText: /General recharge rate|一般充值倍率|通用充值倍率/i }).first();
  await rateItem.waitFor({ state: "visible", timeout: 10000 });
  const rateContext = {
    text: scrub(await rateItem.innerText()),
    clickable_count: await rateItem.locator("button,a,[role=button]").count(),
    edit_icon_count: await rateItem.locator('[data-icon="edit"],.anticon-edit').count(),
  };

  action = "open_recharge_rate_edit";
  let edit = rateItem.locator('[data-icon="edit"],.anticon-edit').first();
  if (!await edit.count()) edit = rateItem.locator("button,a,[role=button]").first();
  const editTarget = edit.locator("xpath=ancestor-or-self::button[1] | ancestor-or-self::a[1] | ancestor-or-self::*[@role='button'][1]").first();
  if (await editTarget.count()) await editTarget.click(); else await edit.click();
  const editModal = page.locator(".ant-modal:visible").last();
  await editModal.waitFor({ state: "visible", timeout: 8000 });
  await quiet();
  const editForm = await modalSnapshot(editModal);
  editForm.select_options = [];
  const selects = editModal.locator(".ant-select:visible");
  for (let index = 0; index < await selects.count(); index += 1) {
    action = `expand_recharge_rate_select:${index}`;
    await selects.nth(index).click();
    await page.waitForTimeout(350);
    editForm.select_options.push((await page.locator(".ant-select-dropdown:visible .ant-select-item-option").allInnerTexts()).map(scrub));
    await page.keyboard.press("Escape");
  }
  if (await selects.count()) {
    action = "select_recharge_rate_custom_without_submit";
    await selects.first().click();
    await page.locator(".ant-select-dropdown:visible .ant-select-item-option").filter({ hasText: /^\s*Custom\s*$/ }).click();
    await page.waitForTimeout(250);
    editForm.custom_mode = await modalSnapshot(editModal);
  }
  await page.keyboard.press("Escape");

  action = "open_recharge_rate_operation_records";
  const recordsButton = rateItem.getByRole("button", { name: /operating record|操作记录/i }).first();
  if (await recordsButton.count()) await recordsButton.click();
  else await rateItem.getByText(/operating record|操作记录/i).first().click();
  const recordsModal = page.locator(".ant-modal:visible").last();
  await recordsModal.waitFor({ state: "visible", timeout: 8000 });
  await quiet();
  const records = {
    title: scrub(await recordsModal.locator(".ant-modal-title").first().innerText().catch(() => "")),
    columns: (await recordsModal.locator("th").allInnerTexts()).map(scrub).filter(Boolean),
    empty: /No data|暂无数据/i.test(await recordsModal.innerText()),
  };

  const relevantNetwork = network.filter(event => event.action.includes("recharge_rate"));
  fs.writeFileSync(output, `${JSON.stringify({
    captured_at: new Date().toISOString(), environment: "FAT", target_ref: target.target_ref,
    page_route: "/member-center/detail/{uid}", rate_context: rateContext, edit_form: editForm,
    operation_records: records, submitted: false, writes: 0, raw_phone_or_uid_persisted: false,
    network: relevantNetwork,
  }, null, 2)}\n`);
  console.log(JSON.stringify({ target_ref: target.target_ref, rate_context: rateContext, edit_form: editForm, operation_records: records, endpoints: relevantNetwork.map(({ action: eventAction, method, path, query_fields, body_fields, http_status, business_status }) => ({ action: eventAction, method, path, query_fields, body_fields, http_status, business_status })), writes: 0 }));
} finally {
  await browser.close();
}
