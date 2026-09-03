import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";
import { loadEnv, requiredEnv } from "../ui/framework/env.mjs";
import { decodeCbor } from "../ui/framework/cbor-decoder.mjs";

loadEnv(process.env.ENV_FILE || ".env.fat");

const baseUrl = requiredEnv("ADMIN_URL");
const origin = new URL(baseUrl).origin;
const outDir = path.resolve("fat-admin-interface-scan/results");
const inventoryPath = path.join(outDir, "fat-admin-explicit-actions.json");
const actionRisk = process.env.ADMIN_ACTION_RISK || "READ_INTERACTION";
const artifactSlug = process.env.ADMIN_ACTION_ARTIFACT || "read";
const resultPath = path.join(outDir, `fat-admin-explicit-${artifactSlug}-actions.json`);
const progressPath = path.join(outDir, `fat-admin-explicit-${artifactSlug}-actions-progress.json`);
const inventory = JSON.parse(fs.readFileSync(inventoryPath, "utf8"));
const actions = inventory.actions.filter((item) => item.risk === actionRisk);

const sanitize = (value) => String(value ?? "")
  .replace(/\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi, "<redacted-email>")
  .replace(/(?<!\d)(?:\+?63|0)9\d{9}(?!\d)/g, "<redacted-phone>")
  .replace(/(?<!\d)\d{6,}(?!\d)/g, "<redacted-numeric-id>")
  .trim();

const normalizePath = (value) => value
  .replace(/\/[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}(?=\/|$)/g, "/{uuid}")
  .replace(/\/\d{6,}(?=\/|$)/g, "/{id}");

const browser = await chromium.launch({ headless: process.env.ADMIN_SCAN_HEADED === "false" });
const context = await browser.newContext({
  acceptDownloads: true, ignoreHTTPSErrors: true,
  viewport: { width: 1440, height: 1000 }, locale: "en-US",
});
const page = await context.newPage();
const network = [];
const executions = [];
let current = { route: "login", type: "login", name: "login flow" };
let fatalError = null;

page.on("response", async (response) => {
  const request = response.request();
  if (!["xhr", "fetch"].includes(request.resourceType())) return;
  let url;
  try { url = new URL(response.url()); } catch { return; }
  if (url.origin !== origin) return;
  const event = {
    page_route: current.route, control_type: current.type, action_name: current.name,
    method: request.method(), path: normalizePath(url.pathname),
    query_fields: [...url.searchParams.keys()].sort(), body_fields: [],
    header_fields: Object.keys(request.headers()).filter((name) => !["cookie", "authorization"].includes(name.toLowerCase())).sort(),
    http_status: response.status(), business_status: null,
    response_data_type: "unknown", response_data_keys: [],
  };
  network.push(event);
  try {
    const raw = request.postDataBuffer();
    if (raw?.length) {
      const contentType = (request.headers()["content-type"] || "").toLowerCase();
      const decoded = contentType.includes("json") ? JSON.parse(raw.toString("utf8")) : decodeCbor(new Uint8Array(raw));
      if (decoded && typeof decoded === "object" && !Array.isArray(decoded)) event.body_fields = Object.keys(decoded).sort();
    }
  } catch { /* no values are persisted */ }
  try {
    const decoded = decodeCbor(new Uint8Array(await response.body()));
    if (decoded && typeof decoded === "object" && !Array.isArray(decoded)) {
      event.business_status = decoded.status ?? null;
      const data = decoded.data;
      event.response_data_type = data === null ? "null" : Array.isArray(data) ? "list" : typeof data;
      if (data && typeof data === "object" && !Array.isArray(data)) event.response_data_keys = Object.keys(data).sort();
    }
  } catch { /* response structure remains unknown */ }
});

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
  await page.waitForTimeout(1_000);
}

async function waitForNetworkQuiet(quietMs = 700, maxMs = 5_000) {
  const started = Date.now();
  let stableSince = Date.now();
  let previous = network.length;
  while (Date.now() - started < maxMs) {
    await page.waitForTimeout(100);
    if (network.length !== previous) {
      previous = network.length;
      stableSince = Date.now();
    } else if (Date.now() - stableSince >= quietMs) {
      return;
    }
  }
}

function checkpoint() {
  const capturedAt = new Date().toISOString();
  fs.writeFileSync(resultPath, `${JSON.stringify({
    captured_at: capturedAt, environment: "FAT", phase: actionRisk,
    source_inventory: "fat-admin-explicit-actions.json", actions_planned: actions.length,
    executions, network, fatal_error: fatalError,
  }, null, 2)}\n`);
  fs.writeFileSync(progressPath, `${JSON.stringify({
    updated_at: capturedAt, completed_actions: executions.length, total_actions: actions.length,
    clicked: executions.filter((item) => item.status === "CLICKED").length,
    skipped: executions.filter((item) => item.status === "SKIPPED_NOT_ACTIONABLE").length,
    errors: executions.filter((item) => item.status === "ERROR").length,
    raw_network_events: network.length,
    unique_method_paths: new Set(network.map((item) => `${item.method} ${item.path}`)).size,
    fatal_error: fatalError,
  }, null, 2)}\n`);
}

function actionLocator(action) {
  const selector = JSON.parse(action.selector_strategy);
  if (selector.role) return page.getByRole(selector.role, { name: selector.name, exact: selector.exact }).nth(Number(action.selector_ordinal || 0));
  const expected = selector.visible_text || selector.accessible_name || "";
  const escaped = expected.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return page.locator(selector.locator).filter({ hasText: new RegExp(`^\\s*${escaped}\\s*$`) }).nth(Number(action.selector_ordinal || 0));
}

try {
  await login();
  console.log(`[login] success actions=${actions.length}`);
  for (let index = 0; index < actions.length; index += 1) {
    const action = actions[index];
    current = { route: action.page_route, type: "page_initialization", name: `prepare ${action.action_name}` };
    let status = "CLICKED";
    let error = "";
    let matchedCount = 0;
    let actionEvents = [];
    try {
      await page.goto(new URL(action.page_route, baseUrl).toString(), { waitUntil: "domcontentloaded", timeout: 20_000 });
      await waitForNetworkQuiet();
      const locator = actionLocator(action);
      matchedCount = await locator.count();
      if (!matchedCount || !await locator.isVisible().catch(() => false) || !await locator.isEnabled().catch(() => false)) {
        status = "SKIPPED_NOT_ACTIONABLE";
      } else {
        const start = network.length;
        current = { route: action.page_route, type: action.control_type, name: action.action_name };
        await locator.click({ timeout: 3_000 });
        await page.waitForTimeout(900);
        actionEvents = network.slice(start);
      }
    } catch (caught) {
      status = "ERROR";
      error = sanitize(caught);
    }
    executions.push({
      order: index + 1, top_menu: action.top_menu, page_name: action.page_name,
      page_route: action.page_route, control_type: action.control_type,
      action_name: action.action_name, selector_strategy: action.selector_strategy,
      matched_count: matchedCount, status, request_count: actionEvents.length,
      endpoint_keys: [...new Set(actionEvents.map((item) => `${item.method} ${item.path}`))], error,
    });
    checkpoint();
    console.log(`[${index + 1}/${actions.length}] ${action.page_name} :: ${action.action_name} status=${status} requests=${actionEvents.length}`);
  }
} catch (caught) {
  fatalError = sanitize(caught);
  checkpoint();
  console.error(`[fatal] ${fatalError}`);
}

checkpoint();
await browser.close();
console.log(`[summary] actions=${executions.length}/${actions.length} clicked=${executions.filter((item) => item.status === "CLICKED").length} requests=${network.length} fatal=${fatalError ? "yes" : "no"}`);
if (fatalError) process.exitCode = 1;
