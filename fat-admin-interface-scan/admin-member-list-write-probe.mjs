import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";
import { loadEnv, requiredEnv } from "../ui/framework/env.mjs";
import { decodeCbor } from "../ui/framework/cbor-decoder.mjs";

loadEnv(process.env.ENV_FILE || ".env.fat");
const laneKey = process.env.MEMBER_LANE || "reversible";
const actionName = process.env.MEMBER_ROW_ACTION || "Risk Control";
const targetPath = process.env.MEMBER_TARGET_FILE || `/tmp/fat-member-lane-${laneKey}.json`;
const target = JSON.parse(fs.readFileSync(targetPath, "utf8"));
if (target.environment !== "FAT" || target.lane !== laneKey) throw new Error("unexpected FAT member lane target");

const slug = actionName.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
const output = path.resolve(`fat-admin-interface-scan/results/record-flow-member-${laneKey}-${slug}-probe.json`);
const baseUrl = requiredEnv("ADMIN_URL");
const origin = new URL(baseUrl).origin;
const network = [];
let action = "login";
const scrub = (value) => String(value || "")
  .replace(/\b(?:\d{1,3}\.){3}\d{1,3}\b/g, "<redacted-ip>")
  .replace(/(?:\+?63|0)9\d{9}|\b\d{7,}\b/g, "<redacted>")
  .replace(/\s+/g, " ").trim().slice(0, 300);

const browser = await chromium.launch({ headless: process.env.ADMIN_SCAN_HEADED === "false" });
const context = await browser.newContext({
  ignoreHTTPSErrors: true,
  viewport: { width: 1440, height: 1000 },
  locale: "en-US",
});
const page = await context.newPage();

page.on("response", async (response) => {
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
    action,
    method: request.method(),
    path: url.pathname,
    body_fields: bodyFields,
    http_status: response.status(),
    business_status: decoded?.status ?? null,
    response_values_persisted: false,
  });
});

async function quiet() {
  let last = network.length;
  let stable = Date.now();
  for (let index = 0; index < 60; index += 1) {
    await page.waitForTimeout(100);
    if (last !== network.length) { last = network.length; stable = Date.now(); }
    else if (Date.now() - stable > 700) return;
  }
}

async function login() {
  await page.goto(baseUrl, { waitUntil: "domcontentloaded", timeout: 30_000 });
  await page.getByPlaceholder(/请输入用户名|user\s*name|email/i).fill(requiredEnv("ADMIN_EMAIL"));
  await page.getByPlaceholder(/请输入密码|password/i).fill(requiredEnv("ADMIN_PASSWORD"));
  await page.getByRole("button", { name: /登\s*录|log\s*in/i }).click();
  const verification = page.getByPlaceholder(/谷歌验证|google.*(?:code|verification|authenticator)/i);
  await verification.waitFor({ state: "visible", timeout: 10_000 });
  await verification.fill(requiredEnv("ADMIN_GOOGLE_CODE"));
  await page.getByRole("button", { name: /确\s*定|confirm|ok/i }).click();
  await page.waitForURL((url) => !url.pathname.startsWith("/user/login"), { timeout: 20_000 });
}

try {
  await login();
  await page.goto(new URL("/member-center/list", baseUrl).toString(), { waitUntil: "domcontentloaded", timeout: 25_000 });
  await quiet();
  const phoneItem = page.locator(".ant-form-item").filter({
    has: page.locator(".ant-form-item-label", { hasText: /^\s*Phone Number\s*$/i }),
  }).first();
  await phoneItem.locator("input").first().fill(String(target.phone));
  action = `${slug}:query target`;
  await page.locator("button").filter({ hasText: /^\s*Query\s*$/i }).first().click();
  await quiet();
  const row = page.locator(".ant-table-tbody tr:not(.ant-table-measure-row):visible")
    .filter({ hasText: String(target.phone) }).first();
  await row.waitFor({ state: "visible", timeout: 15_000 });
  const control = row.getByRole("button", { name: actionName, exact: true }).first();
  const availableButtons = (await row.locator("button:visible").allInnerTexts()).map(scrub);
  const controlPresent = await control.count() > 0;
  const disabled = controlPresent ? await control.isDisabled() : null;
  let form = null;
  if (controlPresent && !disabled) {
    action = `${slug}:open form`;
    await control.click();
    await page.waitForTimeout(500);
    const overlay = page.locator(".ant-modal:visible,.ant-drawer:visible,[role=dialog]:visible").last();
    await overlay.waitFor({ state: "visible", timeout: 8_000 });
    form = {
      title: scrub(await overlay.locator(".ant-modal-title,.ant-drawer-title").first().innerText().catch(() => "")),
      text_head: scrub((await overlay.innerText()).slice(0, 700)),
      fields: await overlay.locator(".ant-form-item").evaluateAll((items) => items.map((item, index) => ({
        index,
        label: item.querySelector(".ant-form-item-label")?.innerText.replace(/\s+/g, " ").trim() || "",
        required: Boolean(item.querySelector(".ant-form-item-required")),
        controls: [...item.querySelectorAll("input,textarea")].map((element) => ({
          type: element.getAttribute("type") || element.tagName.toLowerCase(),
          placeholder: element.getAttribute("placeholder") || "",
          disabled: element.disabled,
        })),
      }))),
      radio_labels: (await overlay.locator(".ant-radio-wrapper:visible").allInnerTexts()).map(scrub),
      select_texts: (await overlay.locator(".ant-select:visible").allInnerTexts()).map(scrub),
      buttons: (await overlay.locator("button:visible").allInnerTexts()).map(scrub),
    };
    await page.keyboard.press("Escape");
    await page.waitForTimeout(300);
  }
  fs.writeFileSync(output, `${JSON.stringify({
    captured_at: new Date().toISOString(),
    environment: "FAT",
    lane: laneKey,
    target_ref: target.target_ref,
    action_name: actionName,
    control_present: controlPresent,
    control_disabled: disabled,
    available_buttons: availableButtons,
    form,
    submitted: false,
    writes: 0,
    side_effects: [],
    raw_phone_or_uid_persisted: false,
    network,
  }, null, 2)}\n`);
  console.log(JSON.stringify({ lane: laneKey, target_ref: target.target_ref, action_name: actionName, present: controlPresent, disabled, available_buttons: availableButtons, fields: form?.fields.length ?? 0, radios: form?.radio_labels ?? [], buttons: form?.buttons ?? [], writes: 0 }));
} finally {
  await browser.close();
}
