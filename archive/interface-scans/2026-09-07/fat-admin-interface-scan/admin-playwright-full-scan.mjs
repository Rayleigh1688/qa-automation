import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";
import { loadEnv, requiredEnv } from "../ui/framework/env.mjs";
import { decodeCbor } from "../ui/framework/cbor-decoder.mjs";

loadEnv(process.env.ENV_FILE || ".env.fat");

const baseUrl = requiredEnv("ADMIN_URL");
const outDir = path.resolve("fat-admin-interface-scan/results");
fs.mkdirSync(outDir, { recursive: true });
const resultPath = path.join(outDir, "fat-admin-full-scan.json");
const progressPath = path.join(outDir, "fat-admin-page-progress.json");
const resumeRequested = process.env.ADMIN_SCAN_RESUME === "true";
const resumePayload = resumeRequested && fs.existsSync(resultPath)
  ? JSON.parse(fs.readFileSync(resultPath, "utf8"))
  : null;

const routePrefixes = [
  "/home", "/kyc", "/member-center", "/member-management", "/agency-management",
  "/report-management", "/payment", "/operations", "/site-management", "/risk-control",
  "/promo-marketing", "/game", "/gamev2", "/system", "/whitelist", "/logs", "/aggregation",
];

function currentBundleRoutes() {
  const bundlePath = "/tmp/admin-fat-umi.js";
  if (!fs.existsSync(bundlePath)) throw new Error(`${bundlePath} is required; run the static baseline first`);
  const source = fs.readFileSync(bundlePath, "utf8");
  const adminStart = source.indexOf("X9r=()=>[");
  const adminEnd = source.indexOf("],J9r=()=>", adminStart);
  const routeSource = adminStart >= 0 && adminEnd > adminStart ? source.slice(adminStart, adminEnd) : source;
  const routes = [];
  const seen = new Set();
  for (const match of routeSource.matchAll(/path:"(\/[^"?#]+)"/g)) {
    const route = match[1];
    if (!routePrefixes.some((prefix) => route === prefix || route.startsWith(`${prefix}/`))) continue;
    if (route.includes(":")) continue;
    if (!seen.has(route)) { seen.add(route); routes.push(route); }
  }
  return routes;
}

const sanitize = (value) => String(value || "")
  .replace(/\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi, "<redacted-email>")
  .replace(/(?<!\d)(?:\+?63|0)9\d{9}(?!\d)/g, "<redacted-phone>");

function unique(values) {
  return [...new Set(values.map((value) => sanitize(value).trim()).filter(Boolean))];
}

const headed = process.env.ADMIN_SCAN_HEADED !== "false";
const browser = await chromium.launch({ headless: !headed });
const context = await browser.newContext({
  acceptDownloads: true,
  ignoreHTTPSErrors: true,
  viewport: { width: 1440, height: 1000 },
  locale: "en-US",
});
const page = await context.newPage();
const network = Array.isArray(resumePayload?.network) ? resumePayload.network : [];
let currentAction = { type: "page_initialization", name: "page initialization" };

function setAction(type, name) {
  currentAction = { type, name: sanitize(name) };
}

page.on("response", async (response) => {
  const request = response.request();
  if (!["xhr", "fetch"].includes(request.resourceType())) return;
  let url;
  try { url = new URL(response.url()); } catch { return; }
  if (url.origin !== new URL(baseUrl).origin) return;
  const event = {
    page_route: page.__scanRoute || "login",
    control_type: currentAction.type,
    action_name: currentAction.name,
    method: request.method(), path: url.pathname,
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
  } catch { /* field names remain unknown */ }
  try {
    const decoded = decodeCbor(new Uint8Array(await response.body()));
    if (decoded && typeof decoded === "object" && !Array.isArray(decoded)) {
      event.business_status = decoded.status;
      const data = decoded.data;
      event.response_data_type = data === null ? "null" : Array.isArray(data) ? "list" : typeof data;
      if (data && typeof data === "object" && !Array.isArray(data)) event.response_data_keys = Object.keys(data).sort();
    }
  } catch { /* response structure remains unknown */ }
});

async function login() {
  page.__scanRoute = "login";
  setAction("page_initialization", "open login page");
  await page.goto(baseUrl, { waitUntil: "domcontentloaded", timeout: 30_000 });
  await page.getByPlaceholder(/请输入用户名|user\s*name|email/i).fill(requiredEnv("ADMIN_EMAIL"));
  await page.getByPlaceholder(/请输入密码|password/i).fill(requiredEnv("ADMIN_PASSWORD"));
  setAction("button", "login credentials submit");
  await page.getByRole("button", { name: /登\s*录|log\s*in/i }).click();
  const verification = page.getByPlaceholder(/谷歌验证|google.*(?:code|verification|authenticator)/i);
  await verification.waitFor({ state: "visible", timeout: 10_000 });
  await verification.fill(requiredEnv("ADMIN_GOOGLE_CODE"));
  setAction("button", "Google verification confirm");
  await page.getByRole("button", { name: /确\s*定|confirm|ok/i }).click();
  await page.waitForURL((url) => !url.pathname.startsWith("/user/login"), { timeout: 20_000 });
  await page.waitForTimeout(2_000);
}

async function pageControls() {
  const buttonTexts = await page.locator("button:visible").allInnerTexts().catch(() => []);
  const tabTexts = await page.locator(".ant-tabs-tab:visible").allInnerTexts().catch(() => []);
  const headings = await page.locator("h1:visible, h2:visible, h3:visible, .ant-page-header-heading-title:visible").allInnerTexts().catch(() => []);
  const placeholders = await page.locator("input:visible, textarea:visible").evaluateAll((nodes) => nodes.map((node) => node.getAttribute("placeholder") || "")).catch(() => []);
  return {
    headings: unique(headings), buttons: unique(buttonTexts), tabs: unique(tabTexts),
    input_placeholders: unique(placeholders), select_count: await page.locator(".ant-select:visible").count(),
    table_count: await page.locator("table:visible, .ant-table:visible").count(),
  };
}

async function safeInteractions() {
  const actions = [];
  const query = page.getByRole("button", { name: /^(查\s*询|搜\s*索|Search)$/i }).first();
  if (await query.isVisible().catch(() => false) && await query.isEnabled().catch(() => false)) {
    const label = await query.innerText().catch(() => "query");
    setAction("button", label || "query");
    await query.click({ timeout: 3_000 }).catch(() => {});
    await page.waitForTimeout(700);
    actions.push("query");
  }
  const pageTwo = page.locator(".ant-pagination-item-2:visible").first();
  if (await pageTwo.isVisible().catch(() => false)) {
    setAction("pagination", "page 2");
    await pageTwo.click({ timeout: 3_000 }).catch(() => {});
    await page.waitForTimeout(700);
    actions.push("pagination_2");
  }
  const tabs = page.locator(".ant-tabs-tab:visible");
  const tabCount = Math.min(await tabs.count(), 5);
  for (let index = 1; index < tabCount; index += 1) {
    const tab = tabs.nth(index);
    if (await tab.isVisible().catch(() => false)) {
      const label = await tab.innerText().catch(() => `tab ${index + 1}`);
      setAction("tab", label || `tab ${index + 1}`);
      await tab.click({ timeout: 3_000 }).catch(() => {});
      await page.waitForTimeout(500);
      actions.push(`tab_${index + 1}`);
    }
  }
  return actions;
}

const routes = currentBundleRoutes();
const pages = Array.isArray(resumePayload?.pages) ? resumePayload.pages : [];
let fatalError = null;

function writeCheckpoint() {
  const result = { captured_at: new Date().toISOString(), environment: "FAT", headed, routes, pages, network, fatal_error: fatalError };
  fs.writeFileSync(resultPath, `${JSON.stringify(result, null, 2)}\n`);
  fs.writeFileSync(progressPath, `${JSON.stringify({
    updated_at: result.captured_at,
    environment: "FAT",
    completed_pages: pages.length,
    total_pages: routes.length,
    discovered_requests: network.length,
    unique_method_paths: new Set(network.map((event) => `${event.method} ${event.path}`)).size,
    page_errors: pages.filter((item) => item.error).length,
    fatal_error: fatalError,
  }, null, 2)}\n`);
}

try {
  await login();
  console.log(`[login] success ${page.url()}`);
  for (let index = pages.length; index < routes.length; index += 1) {
    const route = routes[index];
    page.__scanRoute = route;
    const networkStart = network.length;
    let error = null;
    let controls = {};
    let actions = [];
    try {
      setAction("page_initialization", `open ${route}`);
      await page.evaluate((nextRoute) => {
        window.history.pushState({}, "", nextRoute);
        window.dispatchEvent(new PopStateEvent("popstate"));
      }, route);
      await page.waitForTimeout(1_500);
      if (!new URL(page.url()).pathname.startsWith(route)) {
        await page.goto(new URL(route, baseUrl).toString(), { waitUntil: "domcontentloaded", timeout: 15_000 });
        await page.waitForTimeout(1_500);
      }
      controls = await pageControls();
      actions = await safeInteractions();
    } catch (caught) {
      error = String(caught);
    }
    await page.waitForTimeout(250);
    const pageEvents = network.slice(networkStart);
    const active = pageEvents.filter((event) => event.http_status >= 200 && event.http_status < 300 && event.business_status !== false).length;
    const failed = pageEvents.length - active;
    pages.push({
      order: index + 1, route, final_url: page.url(), title: await page.title().catch(() => ""),
      controls, actions, request_count: pageEvents.length, active_count: active,
      failed_count: failed, error,
    });
    writeCheckpoint();
    console.log(`[${index + 1}/${routes.length}] ${route} requests=${pageEvents.length} active=${active} failed=${failed}${error ? " ERROR" : ""}`);
  }
} catch (caught) {
  fatalError = String(caught);
  writeCheckpoint();
  console.error(`[fatal] ${fatalError}`);
}

writeCheckpoint();
console.log(`[summary] pages=${pages.length}/${routes.length} requests=${network.length} errors=${pages.filter((item) => item.error).length} fatal=${fatalError ? "yes" : "no"}`);
await browser.close();
if (fatalError) process.exitCode = 1;
