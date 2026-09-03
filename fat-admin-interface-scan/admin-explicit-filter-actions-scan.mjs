import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";
import { loadEnv, requiredEnv } from "../ui/framework/env.mjs";
import { decodeCbor } from "../ui/framework/cbor-decoder.mjs";

loadEnv(process.env.ENV_FILE || ".env.fat");
const baseUrl = requiredEnv("ADMIN_URL");
const origin = new URL(baseUrl).origin;
const outDir = path.resolve("fat-admin-interface-scan/results");
const inventory = JSON.parse(fs.readFileSync(path.join(outDir, "fat-admin-explicit-actions.json"), "utf8"));
const filterActions = inventory.actions.filter((item) => item.risk === "READ_FILTER_OR_FORM_INPUT");
const queryActions = inventory.actions.filter((item) => item.risk === "READ_INTERACTION" && /^(query|search)$/i.test(item.action_name));
const resultPath = path.join(outDir, "fat-admin-explicit-filter-actions.json");
const progressPath = path.join(outDir, "fat-admin-explicit-filter-actions-progress.json");

const sanitize = (value) => String(value ?? "")
  .replace(/\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi, "<redacted-email>")
  .replace(/(?<!\d)(?:\+?63|0)9\d{9}(?!\d)/g, "<redacted-phone>")
  .replace(/(?<!\d)\d{6,}(?!\d)/g, "<redacted-numeric-id>").trim();
const normalizePath = (value) => value.replace(/\/[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}(?=\/|$)/g, "/{uuid}").replace(/\/\d{6,}(?=\/|$)/g, "/{id}");
const escapeRegex = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

const browser = await chromium.launch({ headless: process.env.ADMIN_SCAN_HEADED === "false" });
const context = await browser.newContext({ ignoreHTTPSErrors: true, viewport: { width: 1440, height: 1000 }, locale: "en-US" });
const page = await context.newPage();
const network = [], executions = [];
let current = { route: "login", type: "login", name: "login flow" }, fatalError = null;

page.on("response", async (response) => {
  const request = response.request();
  if (!["xhr", "fetch"].includes(request.resourceType())) return;
  let url; try { url = new URL(response.url()); } catch { return; }
  if (url.origin !== origin) return;
  const event = {
    page_route: current.route, control_type: current.type, action_name: current.name,
    method: request.method(), path: normalizePath(url.pathname), query_fields: [...url.searchParams.keys()].sort(),
    body_fields: [], header_fields: Object.keys(request.headers()).filter((name) => !["cookie", "authorization"].includes(name.toLowerCase())).sort(),
    http_status: response.status(), business_status: null, response_data_type: "unknown", response_data_keys: [],
  };
  network.push(event);
  try {
    const raw = request.postDataBuffer();
    if (raw?.length) {
      const type = (request.headers()["content-type"] || "").toLowerCase();
      const decoded = type.includes("json") ? JSON.parse(raw.toString("utf8")) : decodeCbor(new Uint8Array(raw));
      if (decoded && typeof decoded === "object" && !Array.isArray(decoded)) event.body_fields = Object.keys(decoded).sort();
    }
  } catch {}
  try {
    const decoded = decodeCbor(new Uint8Array(await response.body()));
    if (decoded && typeof decoded === "object" && !Array.isArray(decoded)) {
      event.business_status = decoded.status ?? null;
      const data = decoded.data;
      event.response_data_type = data === null ? "null" : Array.isArray(data) ? "list" : typeof data;
      if (data && typeof data === "object" && !Array.isArray(data)) event.response_data_keys = Object.keys(data).sort();
    }
  } catch {}
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
}

async function quiet(ms = 700, max = 5_000) {
  const start = Date.now(); let previous = network.length, stable = Date.now();
  while (Date.now() - start < max) {
    await page.waitForTimeout(100);
    if (network.length !== previous) { previous = network.length; stable = Date.now(); }
    else if (Date.now() - stable >= ms) return;
  }
}

function checkpoint() {
  const captured = new Date().toISOString();
  fs.writeFileSync(resultPath, `${JSON.stringify({ captured_at: captured, environment: "FAT", phase: "READ_FILTER_OR_FORM_INPUT", actions_planned: filterActions.length, executions, network, fatal_error: fatalError }, null, 2)}\n`);
  fs.writeFileSync(progressPath, `${JSON.stringify({ updated_at: captured, completed_actions: executions.length, total_actions: filterActions.length, interacted: executions.filter((x) => x.status === "INTERACTED").length, skipped: executions.filter((x) => x.status.startsWith("SKIPPED")).length, errors: executions.filter((x) => x.status === "ERROR").length, action_network_events: network.filter((x) => !["page_initialization", "login"].includes(x.control_type)).length, fatal_error: fatalError }, null, 2)}\n`);
}

async function inFilterContext(locator) {
  return locator.evaluate((node) => {
    const container = node.closest("form, .ant-form, .ant-pro-table-search, .ant-card, .ant-space") || node.parentElement;
    const text = (container?.innerText || "").toLowerCase();
    return /\b(query|search|reset|filter)\b/.test(text) || /查询|搜索|重置|筛选/.test(text);
  }).catch(() => false);
}

function inputValue(action) {
  const name = action.action_name.toLowerCase();
  if (/date|day|month|year/.test(name)) return /end/.test(name) ? "2026-09-03" : "2026-09-01";
  if (/phone|uid|amount|value|page|size|number|count|min|max/.test(name)) return "0";
  return "scan-no-match";
}

try {
  await login();
  const routes = [...new Set(filterActions.map((item) => item.page_route))];
  console.log(`[login] success pages=${routes.length} actions=${filterActions.length}`);
  for (let routeIndex = 0; routeIndex < routes.length; routeIndex += 1) {
    const route = routes[routeIndex];
    const actions = filterActions.filter((item) => item.page_route === route);
    current = { route, type: "page_initialization", name: "prepare filter controls" };
    await page.goto(new URL(route, baseUrl).toString(), { waitUntil: "domcontentloaded", timeout: 20_000 });
    await quiet();
    for (const action of actions) {
      let status = "INTERACTED", error = "", selectedOption = "", requestCount = 0;
      try {
        const selector = JSON.parse(action.selector_strategy);
        let locator;
        if (action.control_type === "input") {
          const name = selector.placeholder_or_name;
          locator = page.getByPlaceholder(name, { exact: true }).first();
          if (!await locator.count()) {
            const escapedName = name.replaceAll("\\", "\\\\").replaceAll('"', '\\"');
            locator = page.locator(`input[name="${escapedName}"], textarea[name="${escapedName}"]`).first();
          }
        } else {
          locator = page.locator(selector.locator).filter({ hasText: new RegExp(`^\\s*${escapeRegex(selector.visible_text || "")}\\s*$`) }).first();
        }
        if (!await locator.count() || !await locator.isVisible().catch(() => false)) status = "SKIPPED_NOT_ACTIONABLE";
        else if (!await inFilterContext(locator)) status = "SKIPPED_NOT_FILTER_CONTEXT";
        else {
          const start = network.length;
          current = { route, type: action.control_type, name: action.action_name };
          if (action.control_type === "input") {
            const type = await locator.getAttribute("type");
            if (type === "file") status = "SKIPPED_FILE_INPUT";
            else await locator.fill(inputValue(action), { timeout: 2_000 });
          } else {
            await locator.click({ timeout: 2_000 });
            const option = page.locator(".ant-select-dropdown:visible .ant-select-item-option:not(.ant-select-item-option-disabled)").first();
            if (await option.count()) {
              selectedOption = sanitize(await option.innerText());
              await option.click({ timeout: 2_000 });
            } else status = "SKIPPED_NO_OPTION";
          }
          await page.waitForTimeout(300);
          requestCount = network.length - start;
        }
      } catch (caught) { status = "ERROR"; error = sanitize(caught); }
      executions.push({ order: executions.length + 1, top_menu: action.top_menu, page_name: action.page_name, page_route: route, control_type: action.control_type, action_name: action.action_name, selector_strategy: action.selector_strategy, status, selected_option: selectedOption, request_count: requestCount, error });
      checkpoint();
    }
    const query = queryActions.find((item) => item.page_route === route);
    if (query) {
      const locator = page.getByRole("button", { name: query.action_name, exact: true }).first();
      if (await locator.isVisible().catch(() => false) && await locator.isEnabled().catch(() => false)) {
        current = { route, type: "filter_submit", name: `Apply registered filters via ${query.action_name}` };
        await locator.click({ timeout: 2_000 }).catch(() => {});
        await page.waitForTimeout(800);
      }
    }
    console.log(`[${routeIndex + 1}/${routes.length}] ${route} actions=${actions.length} interacted=${executions.filter((x) => x.page_route === route && x.status === "INTERACTED").length}`);
  }
} catch (caught) { fatalError = sanitize(caught); checkpoint(); console.error(`[fatal] ${fatalError}`); }

checkpoint();
await browser.close();
console.log(`[summary] actions=${executions.length}/${filterActions.length} interacted=${executions.filter((x) => x.status === "INTERACTED").length} fatal=${fatalError ? "yes" : "no"}`);
if (fatalError) process.exitCode = 1;
