import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";
import { loadEnv, requiredEnv } from "../ui/framework/env.mjs";
import { decodeCbor } from "../ui/framework/cbor-decoder.mjs";

loadEnv(process.env.ENV_FILE || ".env.fat");

const baseUrl = requiredEnv("ADMIN_URL");
const origin = new URL(baseUrl).origin;
const outDir = path.resolve("fat-admin-interface-scan/results");
const menuPath = path.join(outDir, "fat-admin-live-menu.json");
const resultPath = path.join(outDir, "fat-admin-page-initialization.json");
const progressPath = path.join(outDir, "fat-admin-page-initialization-progress.json");
if (!fs.existsSync(menuPath)) throw new Error("Run admin-menu-discovery.mjs first");

const menu = JSON.parse(fs.readFileSync(menuPath, "utf8"));
if ((menu.permission_root_count || 0) < 10 || (menu.menu_pages || []).length <= 3) {
  throw new Error("Live menu completeness gate failed; refusing to scan pages");
}
const routes = menu.menu_pages.filter((item) => item.route && item.route_source !== "unresolved");

const sanitize = (value) => String(value ?? "")
  .replace(/\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi, "<redacted-email>")
  .replace(/(?<!\d)(?:\+?63|0)9\d{9}(?!\d)/g, "<redacted-phone>")
  .replace(/(?<!\d)\d{6,}(?!\d)/g, "<redacted-numeric-id>")
  .trim();

const uniqueObjects = (items) => {
  const seen = new Set();
  return items.filter((item) => {
    const key = JSON.stringify(item);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
};

const browser = await chromium.launch({ headless: process.env.ADMIN_SCAN_HEADED === "false" });
const context = await browser.newContext({
  acceptDownloads: true,
  ignoreHTTPSErrors: true,
  viewport: { width: 1440, height: 1000 },
  locale: "en-US",
});
const page = await context.newPage();
const network = [];
const pages = [];
let currentRoute = "login";
let fatalError = null;

page.on("response", async (response) => {
  const request = response.request();
  if (!["xhr", "fetch"].includes(request.resourceType())) return;
  let url;
  try { url = new URL(response.url()); } catch { return; }
  if (url.origin !== origin) return;
  const event = {
    page_route: currentRoute,
    control_type: "page_initialization",
    action_name: currentRoute === "login" ? "login flow" : "page initialization",
    method: request.method(),
    path: url.pathname,
    query_fields: [...url.searchParams.keys()].sort(),
    body_fields: [],
    header_fields: Object.keys(request.headers()).filter((name) => !["cookie", "authorization"].includes(name.toLowerCase())).sort(),
    http_status: response.status(),
    business_status: null,
    response_data_type: "unknown",
    response_data_keys: [],
  };
  network.push(event);
  try {
    const raw = request.postDataBuffer();
    if (raw?.length) {
      const contentType = (request.headers()["content-type"] || "").toLowerCase();
      const decoded = contentType.includes("json") ? JSON.parse(raw.toString("utf8")) : decodeCbor(new Uint8Array(raw));
      if (decoded && typeof decoded === "object" && !Array.isArray(decoded)) event.body_fields = Object.keys(decoded).sort();
    }
  } catch { /* only field names are retained */ }
  try {
    const decoded = decodeCbor(new Uint8Array(await response.body()));
    if (decoded && typeof decoded === "object" && !Array.isArray(decoded)) {
      event.business_status = decoded.status ?? null;
      const data = decoded.data;
      event.response_data_type = data === null ? "null" : Array.isArray(data) ? "list" : typeof data;
      if (data && typeof data === "object" && !Array.isArray(data)) event.response_data_keys = Object.keys(data).sort();
    }
  } catch { /* response shape remains unknown */ }
});

async function login() {
  currentRoute = "login";
  await page.goto(baseUrl, { waitUntil: "domcontentloaded", timeout: 30_000 });
  await page.getByPlaceholder(/请输入用户名|user\s*name|email/i).fill(requiredEnv("ADMIN_EMAIL"));
  await page.getByPlaceholder(/请输入密码|password/i).fill(requiredEnv("ADMIN_PASSWORD"));
  await page.getByRole("button", { name: /登\s*录|log\s*in/i }).click();
  const verification = page.getByPlaceholder(/谷歌验证|google.*(?:code|verification|authenticator)/i);
  await verification.waitFor({ state: "visible", timeout: 10_000 });
  await verification.fill(requiredEnv("ADMIN_GOOGLE_CODE"));
  await page.getByRole("button", { name: /确\s*定|confirm|ok/i }).click();
  await page.waitForURL((url) => !url.pathname.startsWith("/user/login"), { timeout: 20_000 });
  await page.waitForTimeout(1_500);
}

async function visibleControls() {
  const root = page.locator(".ant-layout-content, main").first();
  const scope = await root.count() ? root : page.locator("body");
  const controls = await scope.evaluate((node) => {
    const visible = (element) => {
      const style = window.getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      return style.visibility !== "hidden" && style.display !== "none" && rect.width > 0 && rect.height > 0;
    };
    const text = (element) => (element.innerText || element.textContent || "").trim();
    const values = (selector, mapper) => Array.from(node.querySelectorAll(selector)).filter(visible).map(mapper);
    return {
      inputs: values("input, textarea", (element) => ({
        type: element.getAttribute("type") || element.tagName.toLowerCase(),
        name: element.getAttribute("name") || "",
        placeholder: element.getAttribute("placeholder") || "",
        aria_label: element.getAttribute("aria-label") || "",
        disabled: Boolean(element.disabled),
      })),
      buttons: values("button", (element) => ({
        text: text(element), aria_label: element.getAttribute("aria-label") || "",
        title: element.getAttribute("title") || "", disabled: Boolean(element.disabled),
      })),
      tabs: values("[role='tab'], .ant-tabs-tab", (element) => ({
        text: text(element), selected: element.getAttribute("aria-selected") || "",
      })),
      selects: values(".ant-select", (element) => ({
        text: text(element), aria_label: element.getAttribute("aria-label") || "",
      })),
      pagination: values(".ant-pagination a, .ant-pagination button", (element) => ({
        text: text(element), aria_label: element.getAttribute("aria-label") || "",
        title: element.getAttribute("title") || "",
      })),
      links: values("a[href]", (element) => ({
        text: text(element), href: element.getAttribute("href") || "",
      })).filter((item) => item.text),
    };
  }).catch(() => ({ inputs: [], buttons: [], tabs: [], selects: [], pagination: [], links: [] }));

  for (const key of Object.keys(controls)) {
    controls[key] = uniqueObjects(controls[key].map((item) => Object.fromEntries(
      Object.entries(item).map(([name, value]) => [name, typeof value === "string" ? sanitize(value) : value]),
    )));
  }
  return controls;
}

function writeCheckpoint() {
  const capturedAt = new Date().toISOString();
  const result = {
    captured_at: capturedAt, environment: "FAT", source_menu: "fat-admin-live-menu.json",
    phase: "PAGE_INITIALIZATION_AND_CONTROL_INVENTORY", routes, pages, network, fatal_error: fatalError,
  };
  fs.writeFileSync(resultPath, `${JSON.stringify(result, null, 2)}\n`);
  fs.writeFileSync(progressPath, `${JSON.stringify({
    updated_at: capturedAt, completed_pages: pages.length, total_pages: routes.length,
    raw_network_events: network.length,
    unique_method_paths: new Set(network.map((item) => `${item.method} ${item.path}`)).size,
    page_errors: pages.filter((item) => item.error).length, fatal_error: fatalError,
  }, null, 2)}\n`);
}

try {
  await login();
  console.log(`[login] success ${page.url()}`);
  for (let index = 0; index < routes.length; index += 1) {
    const menuPage = routes[index];
    currentRoute = menuPage.route;
    const start = network.length;
    let error = "";
    let controls = { inputs: [], buttons: [], tabs: [], selects: [], pagination: [], links: [] };
    try {
      await page.goto(new URL(menuPage.route, baseUrl).toString(), { waitUntil: "domcontentloaded", timeout: 20_000 });
      await page.waitForTimeout(1_500);
      controls = await visibleControls();
    } catch (caught) {
      error = sanitize(caught);
    }
    await page.waitForTimeout(250).catch(() => {});
    const pageEvents = network.slice(start);
    pages.push({
      order: index + 1, top_menu: menuPage.menu_path?.[0] || menuPage.page_name,
      menu_path: menuPage.menu_path || [], page_name: menuPage.page_name,
      route: menuPage.route, final_url: sanitize(page.url()), title: sanitize(await page.title().catch(() => "")),
      controls, request_count: pageEvents.length,
      active_count: pageEvents.filter((item) => item.http_status >= 200 && item.http_status < 300 && item.business_status !== false).length,
      failed_count: pageEvents.filter((item) => item.http_status < 200 || item.http_status >= 300 || item.business_status === false).length,
      error,
    });
    writeCheckpoint();
    console.log(`[${index + 1}/${routes.length}] ${menuPage.page_name} ${menuPage.route} requests=${pageEvents.length} controls=${Object.values(controls).reduce((sum, items) => sum + items.length, 0)}${error ? " ERROR" : ""}`);
  }
} catch (caught) {
  fatalError = sanitize(caught);
  writeCheckpoint();
  console.error(`[fatal] ${fatalError}`);
}

writeCheckpoint();
await browser.close();
console.log(`[summary] pages=${pages.length}/${routes.length} requests=${network.length} errors=${pages.filter((item) => item.error).length} fatal=${fatalError ? "yes" : "no"}`);
if (fatalError) process.exitCode = 1;
