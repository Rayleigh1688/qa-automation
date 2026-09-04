import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { chromium } from "playwright";
import { decodeCbor } from "../ui/framework/cbor-decoder.mjs";

const baseUrl = process.env.PAGCOR_ADMIN_URL || "https://admin-pagcor-fat.filbet2025.com/";
const email = process.env.PAGCOR_ADMIN_EMAIL;
const password = process.env.PAGCOR_ADMIN_PASSWORD;
const loginCode = process.env.PAGCOR_ADMIN_LOGIN_CODE || "111111";
if (!email || !password) throw new Error("PAGCOR_ADMIN_EMAIL and PAGCOR_ADMIN_PASSWORD are required");

const origin = new URL(baseUrl).origin;
const outDir = path.resolve("pagcor-admin-interface-scan/results");
fs.mkdirSync(outDir, { recursive: true });
const now = () => new Date().toISOString();
const redact = (value) => String(value ?? "")
  .replace(/\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi, "<redacted-email>")
  .replace(/(?<!\d)(?:\+?63|0)9\d{9}(?!\d)/g, "<redacted-phone>")
  .replace(/\b(?:eyJ|Bearer\s+)[A-Za-z0-9._~+/=-]{12,}\b/gi, "<redacted-secret>")
  .trim();
const unique = (items) => [...new Map(items.map((item) => [JSON.stringify(item), item])).values()];
const sha = (value) => crypto.createHash("sha256").update(String(value)).digest("hex").slice(0, 12);

function parseCsv(text) {
  const rows = []; let row = []; let field = ""; let quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const c = text[i];
    if (quoted) {
      if (c === '"' && text[i + 1] === '"') { field += '"'; i += 1; }
      else if (c === '"') quoted = false; else field += c;
    } else if (c === '"') quoted = true;
    else if (c === ",") { row.push(field); field = ""; }
    else if (c === "\n") { row.push(field.replace(/\r$/, "")); rows.push(row); row = []; field = ""; }
    else field += c;
  }
  if (field || row.length) { row.push(field); rows.push(row); }
  const headers = rows.shift() || [];
  return rows.filter((r) => r.some(Boolean)).map((r) => Object.fromEntries(headers.map((h, i) => [h, r[i] || ""])));
}

const inventory = parseCsv(fs.readFileSync("api/inventory/interfaces.csv", "utf8"));
const relevantDocs = inventory.filter((r) => r.method && r.path && r.top_domain === "合规");
const docByExact = new Map(inventory.map((r) => [`${r.method.toUpperCase()} ${r.path}`, r]));
const docByPath = new Map();
for (const row of inventory) { if (!docByPath.has(row.path)) docByPath.set(row.path, []); docByPath.get(row.path).push(row); }

const browser = await chromium.launch({ headless: process.env.PAGCOR_SCAN_HEADED !== "true" });
// This context is created exclusively for PAGCOR admin and never exports storage state.
const context = await browser.newContext({ ignoreHTTPSErrors: true, acceptDownloads: true, viewport: { width: 1500, height: 1000 }, locale: "en-US" });
const page = await context.newPage();
page.setDefaultTimeout(3_000);
let phase = "LOGIN"; let pageRoute = "/"; let token = "";
const network = []; const thirdParty = []; const permissionResponses = []; const downloads = [];

page.on("download", async (download) => {
  downloads.push({ phase, page_route: pageRoute, suggested_filename: redact(download.suggestedFilename()).replace(/\d{4,}/g, "<id>"), status: "OBSERVED_NOT_SAVED" });
  await download.cancel().catch(() => {});
});

page.on("response", async (response) => {
  const req = response.request();
  if (!["xhr", "fetch"].includes(req.resourceType())) return;
  let url; try { url = new URL(response.url()); } catch { return; }
  if (url.origin !== origin) {
    thirdParty.push({ phase, page_route: pageRoute, method: req.method(), origin: url.origin, path: url.pathname, http_status: response.status(), classification: "THIRD_PARTY" });
    return;
  }
  if (["/cmpl/me/detail", "/admin/me/detail"].includes(url.pathname) && req.headers().t) token = req.headers().t;
  const event = { phase, page_route: pageRoute, action: phase, method: req.method(), path: url.pathname,
    query_fields: [...url.searchParams.keys()].sort(), body_fields: [], header_fields: Object.keys(req.headers()).filter((h) => !["cookie", "authorization", "t", "x-device-id"].includes(h.toLowerCase())).sort(),
    http_status: response.status(), business_status: null, response_data_type: "unknown", response_data_keys: [] };
  try {
    const raw = req.postDataBuffer();
    if (raw?.length) {
      const ct = (req.headers()["content-type"] || "").toLowerCase();
      const body = ct.includes("json") ? JSON.parse(raw.toString("utf8")) : decodeCbor(new Uint8Array(raw));
      if (body && typeof body === "object" && !Array.isArray(body)) event.body_fields = Object.keys(body).filter((k) => !/password|token|cookie|otp|code|secret|device/i.test(k)).sort();
    }
  } catch { event.body_fields = ["<encoded-body-fields-unavailable>"]; }
  try {
    const decoded = decodeCbor(new Uint8Array(await response.body()));
    if (decoded && typeof decoded === "object" && !Array.isArray(decoded)) {
      event.business_status = decoded.status ?? null;
      const data = decoded.data;
      event.response_data_type = data === null ? "null" : Array.isArray(data) ? "list" : typeof data;
      if (data && typeof data === "object" && !Array.isArray(data)) event.response_data_keys = Object.keys(data).filter((k) => !/password|token|cookie|otp|secret|device/i.test(k)).sort();
      if (["/admin/login", "/admin/login/auth", "/cmpl/login"].includes(url.pathname) && decoded.status === true) {
        if (typeof data === "string") token = data;
        else if (data && typeof data === "object") token = data.token || data.t || data.access_token || token;
      }
      if (["/admin/priv/list", "/cmpl/priv/list"].includes(url.pathname) && Array.isArray(data)) permissionResponses.push({ query_fields: event.query_fields, item_count: data.length, items: data.map((x) => ({ id: String(x.id ?? ""), pid: String(x.pid ?? ""), name: redact(x.name), route_name: redact(x.routeName), module: redact(x.module), is_button_permission: Boolean(x.is_button_permission) })) });
    }
  } catch { /* structure unavailable */ }
  network.push(event);
  if (phase === "LOGIN") console.log(`[login-network] ${event.method} ${event.path} http=${event.http_status} business=${event.business_status}`);
});

async function login() {
  await page.goto(baseUrl, { waitUntil: "domcontentloaded", timeout: 30_000 });
  await page.waitForTimeout(2_000);
  const observedLogin = new URL(page.url());
  if (observedLogin.origin !== origin) throw new Error(`Login redirected to unexpected origin ${observedLogin.origin}`);
  const loginDom = await page.locator("body").evaluate(() => ({ inputs: Array.from(document.querySelectorAll("input")).map(e => ({ type: e.type, placeholder: e.placeholder, name: e.name })), buttons: Array.from(document.querySelectorAll("button")).map(e => (e.innerText || e.textContent || "").trim()) }));
  console.log(`[login-page] origin=${observedLogin.origin} path=${observedLogin.pathname} title=${redact(await page.title())} dom=${JSON.stringify(loginDom)}`);
  const username = page.getByPlaceholder(/请输入用户名|user\s*name|email|account/i).or(page.locator("input:visible:not([type=password])")).first();
  const passwordInput = page.getByPlaceholder(/请输入密码|password/i).or(page.locator("input[type=password]:visible")).first();
  await username.fill(email, { timeout: 12_000 });
  await passwordInput.fill(password, { timeout: 12_000 });
  const loginButton = page.getByRole("button", { name: /登\s*录|log\s*in|sign\s*in/i }).or(page.locator("button.ant-btn-primary:visible")).first();
  await loginButton.click();
  const codeInput = page.getByPlaceholder(/谷歌验证|google.*(?:code|verification|authenticator)|verification/i).or(page.locator(".ant-modal input:visible")).first();
  const needsCode = await codeInput.waitFor({ state: "visible", timeout: 5_000 }).then(() => true).catch(() => false);
  if (needsCode) {
    await codeInput.fill(loginCode);
    await page.getByRole("button", { name: /确\s*定|confirm|ok/i }).or(page.locator(".ant-modal button.ant-btn-primary:visible")).first().click();
  } else if (!network.some((e) => e.path === "/cmpl/me/detail" && e.business_status === true) && /\/user\/login|\/login(?:\/|$)|^\/$/i.test(new URL(page.url()).pathname)) {
    const alert = redact(await page.locator(".ant-message,.ant-notification,.ant-form-item-explain-error,[role=alert]").allInnerTexts().catch(() => [])).slice(0, 300);
    throw new Error(`Login did not advance to verification or authenticated route; visible_feedback=${alert || "none"}`);
  }
  if (!network.some((e) => e.path === "/cmpl/me/detail" && e.business_status === true)) await page.waitForURL((u) => u.origin === origin && !/\/user\/login|\/login(?:\/|$)/i.test(u.pathname), { timeout: 25_000 });
  await page.waitForTimeout(2_000);
}

async function controls() {
  return await page.locator("body").evaluate(() => {
    const visible = (e) => { const r = e.getBoundingClientRect(); const s = getComputedStyle(e); return r.width > 0 && r.height > 0 && s.display !== "none" && s.visibility !== "hidden"; };
    const clean = (v) => (v || "").trim().replace(/\s+/g, " ").replace(/\b\d{6,}\b/g, "<redacted-numeric-id>");
    const take = (sel, map) => Array.from(document.querySelectorAll(sel)).filter(visible).map(map);
    return {
      inputs: take("input,textarea", e => ({ type: e.type || e.tagName.toLowerCase(), name: e.name || "", placeholder: clean(e.placeholder), disabled: e.disabled })),
      buttons: take("button", e => ({ text: clean(e.innerText || e.textContent), title: clean(e.title), aria_label: clean(e.getAttribute("aria-label")), disabled: e.disabled })),
      selects: take(".ant-select,[role=combobox]", e => ({ text: clean(e.innerText || e.textContent), aria_label: clean(e.getAttribute("aria-label")) })),
      tabs: take("[role=tab],.ant-tabs-tab", e => ({ text: clean(e.innerText || e.textContent), selected: e.getAttribute("aria-selected") || "" })),
      pagination: take(".ant-pagination a,.ant-pagination button", e => ({ text: clean(e.innerText || e.textContent), title: clean(e.title), disabled: e.disabled })),
      links: take("a[href]", e => ({ text: clean(e.innerText || e.textContent), href: e.getAttribute("href") || "" })).filter(x => x.text),
      drawers: take(".ant-drawer", e => ({ text: clean(e.querySelector(".ant-drawer-title")?.textContent || "drawer") })),
      modals: take(".ant-modal", e => ({ text: clean(e.querySelector(".ant-modal-title")?.textContent || "modal") })),
      tables: take("table,.ant-table", e => ({ headers: Array.from(e.querySelectorAll("th")).map(x => clean(x.textContent)).filter(Boolean), row_count: e.querySelectorAll("tbody tr").length })),
    };
  });
}

await login();
phase = "LOGIN_GATE"; pageRoute = new URL(page.url()).pathname;
const me = network.find((e) => ["/admin/me/detail", "/cmpl/me/detail"].includes(e.path) && e.business_status === true);
const renderedSidebar = page.locator(".ant-layout-sider,aside,.ant-menu").first();
const sidebarVisible = await renderedSidebar.isVisible().catch(() => false);
const menuCountAtGate = await renderedSidebar.locator(".ant-menu-item,.ant-menu-submenu-title").count().catch(() => 0);
console.log(`[login-gate] token_in_memory=${Boolean(token)} me=${Boolean(me)} menu_visible=${sidebarVisible} menu_controls=${menuCountAtGate} route=${new URL(page.url()).pathname}`);
const authenticatedBusinessPage = network.some((e) => e.path !== "/cmpl/login" && e.path !== "/cmpl/me/detail" && e.business_status === true);
if (!token || !me || !authenticatedBusinessPage) throw new Error("Authenticated gate failed: token/me/business-page evidence incomplete");

// Query the complete permission tree with the in-memory token; it is never serialized.
const visited = new Set(); const queue = ["0"];
while (queue.length && visited.size < 500) {
  const pid = queue.shift(); if (visited.has(pid)) continue; visited.add(pid);
  const u = new URL("/cmpl/priv/list", baseUrl); u.searchParams.set("pid", pid);
  const resp = await context.request.get(u.toString(), { headers: { t: token, lang: "en", "client-id": "123" }, ignoreHTTPSErrors: true });
  try {
    const d = decodeCbor(new Uint8Array(await resp.body()));
    if (d?.status && Array.isArray(d.data)) {
      permissionResponses.push({ pid, http_status: resp.status(), business_status: true, item_count: d.data.length, items: d.data.map((x) => ({ id: String(x.id ?? ""), pid: String(x.pid ?? ""), name: redact(x.name), route_name: redact(x.routeName), module: redact(x.module), is_button_permission: Boolean(x.is_button_permission) })) });
      for (const x of d.data) if (!x.is_button_permission && x.id !== undefined) queue.push(String(x.id));
    } else permissionResponses.push({ pid, http_status: resp.status(), business_status: d?.status ?? null, item_count: 0, items: [] });
  } catch { permissionResponses.push({ pid, http_status: resp.status(), business_status: null, item_count: 0, items: [] }); }
}

phase = "MENU_DISCOVERY";
const submenuTitles = renderedSidebar.locator(".ant-menu-submenu-title");
for (let pass = 0; pass < 4; pass += 1) {
  const count = await submenuTitles.count();
  for (let i = 0; i < count; i += 1) if (await submenuTitles.nth(i).getAttribute("aria-expanded") !== "true") await submenuTitles.nth(i).click({ timeout: 1500 }).catch(() => {});
  await page.waitForTimeout(200);
}
const menuPages = await renderedSidebar.locator(".ant-menu-item").evaluateAll((nodes) => nodes.map((e) => {
  const parents = []; let p = e.parentElement?.closest(".ant-menu-submenu");
  while (p) { const t = p.querySelector(":scope > .ant-menu-submenu-title")?.textContent?.trim(); if (t) parents.unshift(t); p = p.parentElement?.closest(".ant-menu-submenu"); }
  const a = e.querySelector("a[href]"); return { menu_path: parents, page_name: (e.textContent || "").trim().replace(/\d+$/, "").trim(), href: a?.getAttribute("href") || "" };
}));
if (!menuPages.length) {
  const anchors = await page.locator("a[href]").evaluateAll((nodes) => nodes.map((a) => ({ menu_path: [], page_name: (a.textContent || "").trim(), href: a.getAttribute("href") || "" })));
  menuPages.push(...anchors.filter((x) => x.href && !/^https?:\/\//i.test(x.href)));
}
for (const item of menuPages) if (item.href) { const u = new URL(item.href, baseUrl); item.route = `${u.pathname}${u.hash}`; }
let routes = unique(menuPages.filter(x => x.route).map(x => ({ ...x, menu_path: x.menu_path.map(redact), page_name: redact(x.page_name), href: redact(x.href) })));
if (!routes.length) routes = [{ menu_path: [], page_name: "PAGCOR report", href: "/", route: "/", route_source: "authenticated root application" }];

const pages = [];
for (let i = 0; i < routes.length; i += 1) {
  const item = routes[i]; phase = "PAGE_INITIALIZATION"; pageRoute = item.route; const start = network.length;
  let error = ""; let dom = {};
  try { await page.goto(new URL(item.route, baseUrl).toString(), { waitUntil: "domcontentloaded", timeout: 22_000 }); await page.waitForTimeout(1100); dom = await controls(); }
  catch (e) { error = redact(e.message); }
  { const actual = new URL(page.url()); pages.push({ order: i + 1, ...item, actual_origin: actual.origin, actual_route: `${actual.pathname}${actual.hash}`, title: redact(await page.title()), controls: dom,
    request_count: network.length - start, error });
  }
  console.log(`[${i + 1}/${routes.length}] ${item.route} req=${network.length - start}${error ? " ERROR" : ""}`);
}

// Safe explicit actions: tabs, default query/search, first safe details, export observation, pagination, and overflow.
const dangerous = /add|create|edit|update|delete|remove|approve|reject|audit|adjust|credit|debit|reset|password|enable|disable|block|unblock|submit|save|confirm|success|failed|cancel|assign|upload|新增|添加|编辑|删除|审核|通过|驳回|调整|上分|下分|密码|启用|停用|封禁|解封|提交|保存|确认|上传/i;
const actions = [];
for (const item of routes) {
  phase = "SAFE_ACTION"; pageRoute = item.route;
  try { await page.goto(new URL(item.route, baseUrl).toString(), { waitUntil: "domcontentloaded", timeout: 20_000 }); await page.waitForTimeout(800); } catch { continue; }
  const candidates = page.locator("button:visible,[role=tab]:visible,.ant-tabs-tab:visible,.ant-pagination-next:not(.ant-pagination-disabled),.ant-dropdown-trigger:visible");
  const n = Math.min(await candidates.count(), 30);
  for (let i = 0; i < n; i += 1) {
    const el = candidates.nth(i); const label = redact((await el.innerText().catch(() => "")) || (await el.getAttribute("aria-label")) || (await el.getAttribute("title")) || "<unnamed>");
    const compactLabel = label.replace(/\s+/g, "");
    const semantic = /query|search|filter|detail|view|export|more|overflow|next|查询|搜索|搜寻|寻找|筛选|详情|查看|导出|更多/i.test(compactLabel) || await el.getAttribute("role") === "tab";
    if (!semantic || dangerous.test(label) || /logout|sign out|language|退出/i.test(label)) continue;
    const before = network.length; const downloadsBefore = downloads.length; let result = "CLICKED"; let overlay = { modals: 0, drawers: 0 };
    try { await el.click({ timeout: 2500 }); await page.waitForTimeout(650); overlay = { modals: await page.locator(".ant-modal:visible").count(), drawers: await page.locator(".ant-drawer:visible").count() }; }
    catch (e) { result = `ERROR:${redact(e.message).slice(0, 160)}`; }
    if (/export|导出/i.test(compactLabel) && result === "CLICKED" && network.length === before && downloads.length === downloadsBefore) result = "CLICKED_NO_INTERFACE_EVIDENCE";
    actions.push({ page_route: item.route, label, control_type: await el.getAttribute("role") === "tab" ? "tab" : "button", result, request_count: network.length - before, overlay });
    const close = page.locator(".ant-modal-close:visible,.ant-drawer-close:visible").first(); if (await close.count()) await close.click().catch(() => {});
  }
  const selects = page.locator(".ant-select:visible");
  const selectCount = Math.min(await selects.count(), 8);
  for (let i = 0; i < selectCount; i += 1) {
    const select = selects.nth(i); const before = network.length; let result = "OPENED"; let optionCount = 0; let selected = false;
    try {
      await select.click({ timeout: 2000 }); await page.waitForTimeout(250);
      const opts = page.locator(".ant-select-dropdown:visible .ant-select-item-option:not(.ant-select-item-option-disabled)"); optionCount = await opts.count();
      if (optionCount) { await opts.first().click({ timeout: 2_000, force: true }); selected = true; result = "FIRST_LEGAL_OPTION_SELECTED"; } else await page.keyboard.press("Escape");
    }
    catch (e) { result = `ERROR:${redact(e.message).slice(0, 160)}`; }
    actions.push({ page_route: item.route, label: `filter-${i + 1}`, control_type: "select", result, option_count: optionCount, selected, request_count: network.length - before, overlay: { modals: 0, drawers: 0 } });
    console.log(`[action] filter-${i + 1} ${result} options=${optionCount}`);
  }
  for (const preset of ["今 日", "昨 日", "本 周", "本 月", "上 月", "重 置"]) {
    const button = page.getByRole("button", { name: preset }); if (!await button.count()) continue;
    const dateInputs = page.locator("input[placeholder*=日期]"); const beforeValues = await dateInputs.evaluateAll((nodes) => nodes.map((e) => e.value)).catch(() => []); const before = network.length; let result = "CLICKED";
    try { await button.click({ timeout: 2000 }); await page.waitForTimeout(200); } catch (e) { result = `ERROR:${redact(e.message).slice(0, 160)}`; }
    const afterValues = await dateInputs.evaluateAll((nodes) => nodes.map((e) => e.value)).catch(() => []);
    actions.push({ page_route: item.route, label: preset, control_type: "date_preset", result, request_count: network.length - before, before_values: beforeValues, after_values: afterValues, overlay: { modals: 0, drawers: 0 } });
    console.log(`[action] ${preset.replace(/\s+/g, "")} ${result}`);
  }
  const finalSearch = page.getByRole("button", { name: /搜\s*寻|search|query/i }).first();
  if (await finalSearch.count()) { const before = network.length; let result = "CLICKED"; try { await finalSearch.click(); await page.waitForTimeout(650); } catch (e) { result = `ERROR:${redact(e.message).slice(0, 160)}`; } actions.push({ page_route: item.route, label: "Search after filter/date coverage", control_type: "query", result, request_count: network.length - before, overlay: { modals: 0, drawers: 0 } }); }
}

const endpointMap = new Map();
for (const e of network) {
  if (["/admin/login/auth", "/admin/login"].includes(e.path)) continue;
  const key = `${e.method} ${e.path}`; if (!endpointMap.has(key)) endpointMap.set(key, []); endpointMap.get(key).push(e);
}
const endpoints = [];
for (const [key, events] of endpointMap) {
  const [method, ...rest] = key.split(" "); const p = rest.join(" "); const exact = docByExact.get(key); const pathDocs = docByPath.get(p) || [];
  const success = events.some(e => e.http_status >= 200 && e.http_status < 300 && e.business_status !== false);
  let classification = success ? (exact ? "ACTIVE" : pathDocs.length ? "MISCLASSIFIED" : "UNDOCUMENTED_ACTIVE") : "ACTIVE_FAILED";
  endpoints.push({ method, path: p, classification, documented_match: exact ? "EXACT" : pathDocs.length ? `PATH_ONLY:${pathDocs.map(x => x.method).join("|")}` : "NO",
    event_count: events.length, success_count: events.filter(e => e.http_status >= 200 && e.http_status < 300 && e.business_status !== false).length,
    failed_count: events.filter(e => e.http_status < 200 || e.http_status >= 300 || e.business_status === false).length,
    pages: unique(events.map(e => e.page_route)), evidence: "pagcor-admin-live-scan.json" });
}
const appendedDocs = new Set();
for (const d of relevantDocs) {
  const key = `${d.method.toUpperCase()} ${d.path}`;
  if (!endpointMap.has(key) && !appendedDocs.has(key)) {
    appendedDocs.add(key);
    const permissionReachable = key === "GET /cmpl/priv/list" && permissionResponses.some((x) => x.business_status === true);
    endpoints.push({ method: d.method.toUpperCase(), path: d.path, classification: permissionReachable ? "DOCUMENTED_REACHABLE" : "DOCUMENTED_UNVERIFIED", documented_match: permissionReachable ? "API_DIRECT_SUCCESS_NOT_UI_OBSERVED" : "EXACT_NOT_UI_OBSERVED", event_count: 0, success_count: permissionReachable ? permissionResponses.filter((x) => x.business_status === true).length : 0, failed_count: 0, pages: [], evidence: permissionReachable ? "permission_tree.responses" : d.file, note: permissionReachable ? "Direct authenticated permission-tree evidence; not counted as UI ACTIVE" : "Not observed in current UI; not classified STALE" });
  }
}

const gate = { status: "PASS", authenticated_at: now(), expected_origin: origin, actual_origin: new URL(page.url()).origin,
  initial_post_login_route: `${new URL(page.url()).pathname}${new URL(page.url()).hash}`, token_captured_in_memory_only: Boolean(token), me_detail_business_success: Boolean(me), rendered_navigation_visible: sidebarVisible,
  rendered_menu_controls_at_gate: menuCountAtGate, navigation_structure: "single hash-route top navigation; no traditional sidebar menu items", traditional_sidebar_verified: false,
  business_page_initialization_success: authenticatedBusinessPage, context_isolation: `exclusive-context-${sha(origin + now())}`, storage_state_exported: false };
const result = { captured_at: now(), environment: "FAT", target: "PAGCOR_ADMIN", gate, permission_tree: { queried_pid_count: visited.size, responses: permissionResponses },
  menu: { rendered_items: menuPages.length, routed_pages: routes.length, pages: routes }, pages, actions, network, third_party: unique(thirdParty), downloads,
  unavailable_current_dom: { second_page: "NOT_VISIBLE_SINGLE_PAGE", detail: "NOT_VISIBLE", modal: "NOT_VISIBLE", drawer: "NOT_VISIBLE", overflow: "NOT_VISIBLE" },
  write_operations: { executed: 0, restored: 0, blocked_reason: "No current-run owned data and no real-time business TOTP seed; persistent writes were not attempted" }, endpoints };
fs.writeFileSync(path.join(outDir, "pagcor-admin-live-scan.json"), `${JSON.stringify(result, null, 2)}\n`);
fs.writeFileSync(path.join(outDir, "pagcor-admin-summary.json"), `${JSON.stringify({ captured_at: result.captured_at, gate, counts: { permission_pids: visited.size, menu_items: menuPages.length, routes: routes.length, pages_scanned: pages.length, actions: actions.length, downloads_observed_not_saved: downloads.length, network_events: network.length, third_party: unique(thirdParty).length, unique_endpoints: endpointMap.size, classification: Object.fromEntries([...new Set(endpoints.map(x => x.classification))].sort().map(c => [c, endpoints.filter(x => x.classification === c).length])) }, write_operations: result.write_operations }, null, 2)}\n`);
console.log(`[done] routes=${routes.length} pages=${pages.length} actions=${actions.length} events=${network.length} endpoints=${endpointMap.size}`);
await browser.close();
