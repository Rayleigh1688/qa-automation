import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { chromium, devices } from "playwright";
import { ClientAppPage } from "../ui/elements/client-app.page.mjs";
import { loadEnv } from "../ui/framework/env.mjs";
import { decodeCbor } from "../ui/framework/cbor-decoder.mjs";
import { loadJson } from "../ui/framework/data-loader.mjs";

loadEnv(process.env.ENV_FILE || ".env.fat");
const runtimeDir = path.resolve(process.env.KYC_RUNTIME_DIR || "api/results/provisioning/kyc-record-flow");
const allocation = JSON.parse(fs.readFileSync(path.join(runtimeDir, "member-bootstrap-summary.json"), "utf8"));
const phone = String(allocation.phone || "");
const password = process.env.REGISTER_PASSWORD || "";
if (!phone || !password) throw new Error("allocated KYC phone and REGISTER_PASSWORD are required");
const targetRef = process.env.KYC_TARGET_REF || `KYC-RUN-${crypto.createHash("sha256").update(`fat-kyc-record-flow-v1|${phone}`).digest("hex").slice(0, 12).toUpperCase()}`;
const baseURL = process.env.CLIENT_BASE_URL || process.env.API_URL;
const origin = new URL(baseURL).origin;
const out = path.resolve(process.env.KYC_OUTPUT || "fat-admin-interface-scan/results/record-flow-kyc-client-ui.json");
const resubmitMode = process.env.KYC_RESUBMIT === "true";
const network = [];
let action = "login";
let rawUid = "";

function safe(value) {
  return String(value ?? "")
    .replace(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi, "<redacted-email>")
    .replace(/(?:\+?63|0)?9\d{9}/g, "<redacted-phone>")
    .replace(/\b\d{6,}\b/g, "<redacted-number>")
    .replace(/\s+/g, " ").trim();
}

function decode(buffer) {
  if (!buffer?.length) return null;
  try { return decodeCbor(new Uint8Array(buffer)); } catch {}
  try { return JSON.parse(Buffer.from(buffer).toString("utf8")); } catch {}
  return null;
}

function shape(value) {
  const data = value?.data;
  return {
    top_level_keys: value && typeof value === "object" ? Object.keys(value).sort() : [],
    data_type: Array.isArray(data) ? "list" : data === null ? "null" : typeof data,
    data_keys: data && typeof data === "object" && !Array.isArray(data) ? Object.keys(data).sort() : [],
    kyc_status: Number.isInteger(data?.kyc_status) ? data.kyc_status : undefined,
  };
}

function controls(page) {
  return page.locator("input:visible,textarea:visible,select:visible,button:visible,[role=button]:visible,[role=combobox]:visible,[class*=picker]:visible").evaluateAll((nodes) => nodes.slice(0, 180).map((node, index) => ({
    index,
    tag: node.tagName.toLowerCase(),
    type: node.getAttribute("type") || node.getAttribute("role") || "",
    placeholder: node.getAttribute("placeholder") || "",
    text: (node.innerText || node.textContent || "").trim(),
    accept: node.getAttribute("accept") || "",
    class_name: typeof node.className === "string" ? node.className : "",
    disabled: Boolean(node.disabled || node.getAttribute("aria-disabled") === "true"),
  }))).then((items) => items.map((item) => ({ ...item, placeholder: safe(item.placeholder), text: safe(item.text) })));
}

const browser = await chromium.launch({ headless: process.env.HEADED !== "true", channel: process.env.PLAYWRIGHT_CHANNEL || undefined });
const context = await browser.newContext({ ...devices["Pixel 7"], viewport: { width: 412, height: 915 }, baseURL, ignoreHTTPSErrors: true, locale: "en-US" });
const page = await context.newPage();
const app = new ClientAppPage(page, { pageConfig: loadJson("ui/data/client-pages.json"), modalConfig: loadJson("ui/data/client-modals.json") });

page.on("response", async (response) => {
  const req = response.request();
  if (!["xhr", "fetch"].includes(req.resourceType())) return;
  const url = new URL(response.url());
  if (url.origin !== origin) return;
  const requestBody = decode(req.postDataBuffer());
  let responseBody = null;
  try { responseBody = decode(await response.body()); } catch {}
  if (url.pathname === "/member/detail" && responseBody?.status === true && responseBody?.data?.uid) {
    rawUid = String(responseBody.data.uid);
  }
  network.push({
    action,
    method: req.method(),
    path: url.pathname,
    query_fields: [...url.searchParams.keys()].filter((key) => key !== "t").sort(),
    body_fields: requestBody && typeof requestBody === "object" && !Array.isArray(requestBody) ? Object.keys(requestBody).sort() : [],
    http_status: response.status(),
    business_status: typeof responseBody?.status === "boolean" ? responseBody.status : null,
    response_shape: shape(responseBody),
  });
});

const steps = [];
async function step(name, fn) {
  action = name;
  const start = network.length;
  try {
    await fn();
    await page.waitForTimeout(800);
    const overlay_structure = name.includes("birth date") ? await page.evaluate(() => {
      const button = [...document.querySelectorAll("button")].find((node) => (node.textContent || "").trim() === "Confirm" && node.getBoundingClientRect().width > 0);
      let root = button;
      for (let index = 0; root?.parentElement && index < 4; index += 1) root = root.parentElement;
      return root ? [...root.querySelectorAll("*")].slice(0, 160).map((node) => ({ tag: node.tagName.toLowerCase(), class_name: typeof node.className === "string" ? node.className : "", text: (node.children.length ? "" : node.textContent || "").trim().slice(0, 80) })).filter((item) => item.class_name || item.text) : [];
    }) : undefined;
    steps.push({ name, status: "COMPLETED", route: `${new URL(page.url()).pathname}${new URL(page.url()).search}`, controls: await controls(page), overlay_structure, network_indexes: Array.from({ length: network.length - start }, (_, i) => start + i) });
  } catch (error) {
    steps.push({ name, status: "FAILED", route: `${new URL(page.url()).pathname}${new URL(page.url()).search}`, controls: await controls(page).catch(() => []), network_indexes: Array.from({ length: network.length - start }, (_, i) => start + i), error: safe(error?.message || error) });
    throw error;
  }
}

async function choosePicker(placeholder, optionPattern) {
  const input = page.locator(`input[placeholder="${placeholder}"]`).first();
  await input.evaluate((node) => (node.closest("[role=button],.van-field,.nut-cell,.adm-list-item") || node.parentElement || node).click());
  const option = page.getByRole("button", { name: optionPattern }).first();
  await option.click({ timeout: 5000 });
  await page.getByRole("button", { name: /^Confirm$/i }).last().click({ timeout: 5000 });
  await page.waitForTimeout(300);
}

let terminal = "PROBE_ONLY";
try {
  await step("password login for this-run member", async () => app.loginWithPassword(phone, password));
  await step("open KYC form", async () => {
    await page.goto("/s-kyc-v2", { waitUntil: "domcontentloaded" });
    await page.waitForURL((url) => url.pathname === "/s-kyc-v2", { timeout: 12_000 });
  });
  await step("confirm KYC upgrade", async () => {
    if (resubmitMode) {
      const reverify = page.getByRole("button", { name: /^Re-KYC verification$/i }).first();
      await reverify.click({ timeout: 5000 });
      await page.waitForTimeout(700);
      const verify = page.getByRole("button", { name: /^Verify Now$/i }).first();
      if (await verify.isVisible({ timeout: 1000 }).catch(() => false)) await verify.click();
      await page.waitForFunction(() => /Upload Identification|Front Side of ID|Personal Information/i.test(document.body.innerText || ""), null, { timeout: 10_000 });
      return;
    }
    const clicked = await page.evaluate(() => {
      const node = [...document.querySelectorAll("button,[role=button]")].find((item) => (item.textContent || "").trim() === "Verify Now");
      if (!node) return false;
      node.click();
      return true;
    });
    if (!clicked) throw new Error("Verify Now DOM control unavailable");
    await page.waitForTimeout(700);
    await page.evaluate(() => {
      const node = [...document.querySelectorAll("button,[role=button]")].find((item) => (item.textContent || "").trim() === "Verify Now");
      node?.click();
    });
    await page.waitForFunction(() => /Upload Identification|Front Side of ID|Personal Information/i.test(document.body.innerText || ""), null, { timeout: 10_000 });
  });
  await step("open ID type selector", async () => {
    const input = page.locator('input[placeholder="Select your ID type"]').first();
    await input.evaluate((node) => (node.closest("[role=button],.van-field,.nut-cell,.adm-list-item") || node.parentElement || node).click());
    await page.waitForTimeout(500);
  });
  await step("select National ID and upload controlled files", async () => {
    await page.getByRole("button", { name: /^National ID$/i }).click({ timeout: 3000 });
    await page.getByRole("button", { name: /^Confirm$/i }).click({ timeout: 3000 });
    const imagePath = path.resolve(process.env.KYC_IMAGE || "21000000008072.webp");
    const files = page.locator('input[type="file"]');
    const count = await files.count();
    if (count < 3) throw new Error(`expected 3 KYC file inputs, found ${count}`);
    for (let index = 0; index < 3; index += 1) {
      await files.nth(index).setInputFiles(imagePath);
      await page.waitForTimeout(900);
    }
  });
  await step("continue from identity uploads", async () => {
    await page.getByRole("button", { name: /^Next$/i }).click({ timeout: 5000 });
    await page.waitForFunction(() => /Permanent Address|Current Address|Nearest Branch/i.test(document.body.innerText || ""), null, { timeout: 10_000 });
  });
  await step("fill controlled address and employment fields", async () => {
    await page.locator('textarea[placeholder="Enter your permanent address"]').fill("FAT Test Address, Manila");
    await choosePicker("Select your nearest branch", /2040 Taft Ave|Pasay/i);
    await choosePicker("Select your nature of work", /Employed.*Permanent|Contractual/i);
    await choosePicker("Select your source of income", /Employment Income/i);
  });
  await step("continue from address form", async () => {
    await page.getByRole("button", { name: /^Next$/i }).click({ timeout: 5000 });
    await page.waitForFunction(() => /First Name|Last Name|Date of Birth|Nationality/i.test(document.body.innerText || ""), null, { timeout: 10_000 });
  });
  await step("fill controlled personal fields and open birth date", async () => {
    await page.locator('input[placeholder="Enter your first name"]').fill("FatKyc");
    await page.locator('input[placeholder="Enter your middle name"]').fill("Record");
    await page.locator('input[placeholder="Enter your last name"]').fill("Flow");
    await page.getByRole("button", { name: /^Male$/i }).click({ timeout: 3000 });
    await page.locator('input[placeholder="Enter province"]').fill("Manila");
    const date = page.locator('input[placeholder="Select Date"]').first();
    await date.evaluate((node) => (node.closest("[role=button],.van-field,.nut-cell,.adm-list-item") || node.parentElement || node).click());
    await page.waitForTimeout(500);
  });
  await step("confirm picker default legal adult birth date", async () => {
    await page.getByRole("button", { name: /^Confirm$/i }).last().click({ timeout: 3000 });
  });
  await step("select controlled nationality", async () => {
    const input = page.locator('input[placeholder="Select your nationality"]').first();
    await input.evaluate((node) => (node.closest("[role=button],.van-field,.nut-cell,.adm-list-item") || node.parentElement || node).click());
    const selected = await page.evaluate(() => {
      const node = [...document.querySelectorAll("button")].find((item) => (item.textContent || "").trim() === "Philippines");
      node?.click();
      return Boolean(node);
    });
    if (!selected) throw new Error("Philippines nationality option unavailable");
    const confirm = page.getByRole("button", { name: /^Confirm$/i }).last();
    if (await confirm.isVisible({ timeout: 800 }).catch(() => false)) await confirm.click({ timeout: 3000 });
  });
  await step("continue to KYC review", async () => {
    await page.getByRole("button", { name: /^Next$/i }).click({ timeout: 5000 });
    await page.waitForFunction(() => /Check Your Information|Submit/i.test(document.body.innerText || ""), null, { timeout: 10_000 });
  });
  await step("submit this-run KYC record", async () => {
    const responsePromise = page.waitForResponse((response) => {
      const candidate = new URL(response.url()).pathname;
      return response.request().method() === "POST" && /^\/member\/kyc\/(?:v2\/)?insert$/.test(candidate);
    }, { timeout: 20_000 });
    await page.getByRole("button", { name: /^Submit$/i }).click({ timeout: 5000 });
    const response = await responsePromise;
    const decoded = decode(await response.body());
    if (response.status() >= 400 || decoded?.status !== true) throw new Error(`KYC submit failed http=${response.status()} business=${String(decoded?.status)}`);
    await page.waitForFunction(() => /KYC successful|Return to Homepage/i.test(document.body.innerText || ""), null, { timeout: 15_000 });
    terminal = "SUBMITTED_PENDING";
  });
  await step("refresh submitted KYC status", async () => {
    await page.reload({ waitUntil: "domcontentloaded" });
    await page.waitForTimeout(1200);
  });
} catch (error) {
  terminal = "BLOCKED_PRECONDITION";
} finally {
  const uidRef = rawUid ? `UID-REF-${crypto.createHash("sha256").update(`fat-kyc-record-flow-uid-v1|${rawUid}`).digest("hex").slice(0, 12).toUpperCase()}` : "UNAVAILABLE";
  if (rawUid) {
    const tmpTarget = process.env.KYC_TARGET_FILE || "/tmp/fat-record-flow-target.json";
    fs.writeFileSync(tmpTarget, JSON.stringify({ environment: "FAT", target_ref: targetRef, uid: rawUid, phone, query_fields: ["uid", "phone"] }, null, 2) + "\n", { mode: 0o600 });
    fs.chmodSync(tmpTarget, 0o600);
  }
  fs.writeFileSync(out, JSON.stringify({ captured_at: new Date().toISOString(), environment: "FAT", target_ref: targetRef, uid_ref: uidRef, data_scope: "THIS_RUN_CREATED", terminal, steps, network }, null, 2) + "\n");
  await browser.close();
}
console.log(JSON.stringify({ target_ref: targetRef, terminal, steps: steps.map(({ name, status, route }) => ({ name, status, route })), requests: network.length }));
