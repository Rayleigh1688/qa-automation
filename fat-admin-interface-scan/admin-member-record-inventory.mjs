import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";
import { loadEnv, requiredEnv } from "../ui/framework/env.mjs";
import { decodeCbor } from "../ui/framework/cbor-decoder.mjs";

loadEnv(process.env.ENV_FILE || ".env.fat");
const baseUrl = requiredEnv("ADMIN_URL");
const origin = new URL(baseUrl).origin;
const runLabel = String(process.env.ADMIN_MEMBER_RUN_LABEL || "inventory").replace(/[^a-z0-9_-]/gi, "-");
const out = path.resolve(`fat-admin-interface-scan/results/record-flow-member-${runLabel}.json`);
const network = [];
let action = "login";

const normalizePath = (value) => value
  .replace(/\/member-center\/detail\/[^/?#]+/g, "/member-center/detail/{uid}")
  .replace(/\/[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}(?=\/|$)/g, "/{uuid}")
  .replace(/\/\d{4,}(?=\/|$)/g, "/{id}");
const safeLabel = (value) => {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  if (!text) return "";
  if (/\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/i.test(text)) return "<redacted-dynamic-label>";
  if (/(?:\+?63|0)9\d{9}|\b(?:\d{1,3}\.){3}\d{1,3}\b|\b\d{7,}\b/.test(text)) return "<redacted-dynamic-label>";
  if (/^(?:P\s*)?[\d,.]+$/.test(text)) return "<redacted-dynamic-label>";
  return text.slice(0, 120);
};

function responseSummary(data) {
  if (Array.isArray(data)) return { type: "list", count: data.length, keys: [] };
  if (data === null) return { type: "null", count: 0, keys: [] };
  if (!data || typeof data !== "object") return { type: typeof data, count: null, keys: [] };
  const keys = Object.keys(data).sort();
  for (const key of ["d", "list", "records", "items", "rows"]) {
    if (Array.isArray(data[key])) return { type: "object", count: data[key].length, keys };
  }
  return { type: "object", count: null, keys };
}

const browser = await chromium.launch({ headless: process.env.ADMIN_SCAN_HEADED === "false" });
const context = await browser.newContext({ ignoreHTTPSErrors: true, viewport: { width: 1440, height: 1000 }, locale: "en-US" });
const page = await context.newPage();

page.on("response", async (response) => {
  const request = response.request();
  if (!["xhr", "fetch"].includes(request.resourceType())) return;
  let url; try { url = new URL(response.url()); } catch { return; }
  if (url.origin !== origin) return;
  let bodyFields = [], businessStatus = null, summary = { type: "unknown", count: null, keys: [] };
  try {
    const raw = request.postDataBuffer();
    if (raw?.length) {
      const type = (request.headers()["content-type"] || "").toLowerCase();
      const decoded = type.includes("json") ? JSON.parse(raw.toString("utf8")) : decodeCbor(new Uint8Array(raw));
      if (decoded && typeof decoded === "object" && !Array.isArray(decoded)) bodyFields = Object.keys(decoded).sort();
    }
  } catch {}
  try {
    const decoded = decodeCbor(new Uint8Array(await response.body()));
    businessStatus = decoded?.status ?? null;
    summary = responseSummary(decoded?.data);
  } catch {}
  const headerFields = Object.keys(request.headers()).filter((name) => !["cookie", "authorization"].includes(name.toLowerCase()))
    .map((name) => name.toLowerCase() === "t" ? "<auth-token-header>" : name.toLowerCase() === "x-device-id" ? "<device-id-header>" : name).sort();
  network.push({ action, method: request.method(), path: normalizePath(url.pathname), query_fields: [...url.searchParams.keys()].sort(),
    body_fields: bodyFields, header_fields: headerFields, http_status: response.status(), business_status: businessStatus,
    response_type: summary.type, response_keys: summary.keys, record_count: summary.count });
});

async function quiet(ms = 700) {
  let last = network.length, stable = Date.now();
  for (let i = 0; i < 60; i += 1) {
    await page.waitForTimeout(100);
    if (network.length !== last) { last = network.length; stable = Date.now(); }
    else if (Date.now() - stable >= ms) return;
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

async function controls(scope = page) {
  return await scope.evaluate((root) => {
    const visible = (el) => { const r = el.getBoundingClientRect(); const s = getComputedStyle(el); return r.width > 0 && r.height > 0 && s.visibility !== "hidden" && s.display !== "none"; };
    const clean = (text) => String(text || "").replace(/\s+/g, " ").trim().slice(0, 120);
    const items = (selector, mapper) => [...root.querySelectorAll(selector)].filter(visible).map(mapper);
    return {
      buttons: items("button", (el, index) => ({ index, text: clean(el.innerText), aria_label: el.getAttribute("aria-label") || "", disabled: el.disabled,
        context_label: clean(el.closest(".ant-descriptions-item")?.querySelector(".ant-descriptions-item-label")?.innerText
          || el.closest(".ant-form-item")?.querySelector(".ant-form-item-label")?.innerText || "") })),
      links: items("a[href]", (el, index) => ({ index, text: clean(el.innerText), href: el.getAttribute("href") || "" })),
      inputs: items("input,textarea", (el, index) => ({ index, type: el.getAttribute("type") || el.tagName.toLowerCase(), placeholder: el.getAttribute("placeholder") || "", aria_label: el.getAttribute("aria-label") || "", disabled: el.disabled, required: el.required })),
      tabs: items(".ant-tabs-tab", (el, index) => ({ index, text: clean(el.innerText), selected: el.getAttribute("aria-selected") === "true", classes: el.className })),
      dialogs: items("[role=dialog],.ant-modal,.ant-drawer", (el, index) => ({ index, role: el.getAttribute("role") || "", classes: el.className, text_head: clean(el.innerText).slice(0, 80) })),
      selects: items(".ant-select", (el, index) => ({ index, aria_label: el.getAttribute("aria-label") || "", classes: el.className, disabled: el.classList.contains("ant-select-disabled") })),
      form_items: items(".ant-form-item", (el, index) => ({ index,
        label: clean(el.querySelector(".ant-form-item-label")?.innerText),
        required: Boolean(el.querySelector(".ant-form-item-required")),
        controls: [...el.querySelectorAll("input,textarea,.ant-select")].filter(visible).map((control) => ({
          type: control.getAttribute("type") || (control.tagName === "TEXTAREA" ? "textarea" : control.classList.contains("ant-select") ? "select" : "input"),
          placeholder: control.getAttribute("placeholder") || "", disabled: Boolean(control.disabled || control.classList.contains("ant-select-disabled")),
        })),
      })),
    };
  }).then((result) => ({
    ...result,
    buttons: result.buttons.map((item) => ({ ...item, text: safeLabel(item.text), aria_label: safeLabel(item.aria_label), context_label: safeLabel(item.context_label) })),
    links: result.links.map((item) => ({ ...item, text: safeLabel(item.text), href: normalizePath(item.href) })),
    tabs: result.tabs.map((item) => ({ ...item, text: safeLabel(item.text) })),
    dialogs: result.dialogs.map((item) => ({ ...item, text_head: safeLabel(item.text_head) })),
    form_items: result.form_items.map((item) => ({ ...item, label: safeLabel(item.label) })),
  }));
}

await login();
action = "member_list_initialization";
await page.goto(new URL("/member-center/list", baseUrl).toString(), { waitUntil: "domcontentloaded", timeout: 25_000 });
const firstDataRow = page.locator(".ant-table-tbody tr:not(.ant-table-measure-row):visible").first();
try { await firstDataRow.waitFor({ state: "visible", timeout: 12_000 }); }
catch {
  const format = (date) => {
    const parts = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Manila", year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(date);
    const values = Object.fromEntries(parts.map((part) => [part.type, part.value])); return `${values.year}-${values.month}-${values.day}`;
  };
  const end = new Date(), start = new Date(); start.setUTCDate(start.getUTCDate() - 30);
  const startText = `${format(start)} 00:00:00`, endText = `${format(end)} 23:59:59`;
  const startInput = page.getByPlaceholder(/Start Date/i).first(), endInput = page.getByPlaceholder(/End Date/i).first();
  for (const [input, value] of [[startInput, startText], [endInput, endText]]) {
    await input.click(); await input.press("ControlOrMeta+A"); await input.press("Backspace"); await input.type(value, { delay: 10 }); await input.press("Tab");
  }
  if (!(await startInput.inputValue()).startsWith(format(start)) || !(await endInput.inputValue()).startsWith(format(end))) {
    throw new Error("member list date control rejected validated 30d range");
  }
  action = "member_list:validated 30d Query for readonly row";
  const query = page.locator("button").filter({ hasText: /^\s*Query\s*$/i }).first();
  await query.click(); await quiet();
  await firstDataRow.waitFor({ state: "visible", timeout: 15_000 });
}
await quiet();
const listControls = await controls(page.locator(".ant-layout-content").first());
const firstRowControls = await controls(firstDataRow);

const addMember = page.getByRole("button", { name: "Add Member", exact: true }).first();
let addMemberForm = { status: "CONTROL_NOT_FOUND" };
let addMemberButton = addMember;
if (!await addMemberButton.isVisible().catch(() => false)) {
  addMemberButton = page.locator("button").filter({ hasText: /^\s*Add Member\s*$/i }).first();
}
if (await addMemberButton.isVisible().catch(() => false)) {
  action = "member_list:Add Member open form (no submit)";
  await addMemberButton.click(); await quiet();
  const overlay = page.locator(".ant-modal:visible,.ant-drawer:visible,[role=dialog]:visible").last();
  if (await overlay.isVisible().catch(() => false)) {
    addMemberForm = { status: "OPENED_NOT_SUBMITTED", controls: await controls(overlay) };
    await page.keyboard.press("Escape"); await page.waitForTimeout(300);
  } else addMemberForm = { status: "CLICKED_NO_VISIBLE_FORM" };
}

action = "member_list:View Details readonly existing record";
const viewDetails = firstDataRow.getByRole("button", { name: "View Details", exact: true });
await viewDetails.waitFor({ state: "visible", timeout: 10_000 });
await viewDetails.click();
await page.waitForURL((url) => /\/member-center\/detail\//.test(url.pathname), { timeout: 15_000 });
await quiet();
const detailRoute = normalizePath(new URL(page.url()).pathname);
const detailUrl = page.url();
const detailControls = await controls(page.locator(".ant-layout-content").first());
const tabViews = [];
const requestedTabs = new Set((process.env.ADMIN_MEMBER_TABS || "").split("|").map((value) => value.trim()).filter(Boolean));
const detailTabNames = [...new Set(detailControls.tabs.map((tab) => tab.text)
  .filter((name) => name && !["Member", "Member Detail"].includes(name) && (!requestedTabs.size || requestedTabs.has(name))))];
for (const tabName of detailTabNames) {
  if (tabName !== "Details") {
    action = `member_detail_reset_before_tab:${tabName}`;
    await page.goto(new URL("/member-center/list", baseUrl).toString(), { waitUntil: "domcontentloaded", timeout: 20_000 });
    const resetRow = page.locator(".ant-table-tbody tr:not(.ant-table-measure-row):visible").first();
    await resetRow.waitFor({ state: "visible", timeout: 15_000 });
    await resetRow.getByRole("button", { name: "View Details", exact: true }).click();
    await page.waitForURL((url) => /\/member-center\/detail\//.test(url.pathname), { timeout: 15_000 });
    await quiet();
  }
  const start = network.length;
  action = `member_detail_tab:${tabName}`;
  const escaped = tabName.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const tab = page.locator(".ant-layout-content .ant-tabs-tab").filter({ hasText: new RegExp(`^\\s*${escaped}\\s*$`) }).last();
  try {
    await tab.waitFor({ state: "visible", timeout: 6_000 });
    let selectionMethod = "direct registered tab";
    if (!(await tab.getAttribute("class") || "").includes("ant-tabs-tab-active")) {
      await tab.click(); await page.waitForTimeout(250);
    }
    if (!(await tab.getAttribute("class") || "").includes("ant-tabs-tab-active")) {
      await tab.focus(); await tab.press("Enter"); await page.waitForTimeout(250);
      selectionMethod = "registered tab keyboard activation";
    }
    if (!(await tab.getAttribute("class") || "").includes("ant-tabs-tab-active")) {
      const more = page.locator(".ant-layout-content .ant-tabs-nav-more:visible").last();
      await more.click();
      const overflowItem = page.locator(".ant-tabs-dropdown-menu-item:visible").filter({ hasText: new RegExp(`^\\s*${escaped}\\s*$`) }).last();
      await overflowItem.waitFor({ state: "visible", timeout: 4_000 });
      await overflowItem.click(); selectionMethod = "registered overflow tab item";
    }
    const activeTab = page.locator(".ant-layout-content .ant-tabs-tab-active").filter({ hasText: new RegExp(`^\\s*${escaped}\\s*$`) }).last();
    await activeTab.waitFor({ state: "visible", timeout: 5_000 });
    await quiet();
    const panel = page.locator(".ant-tabs-tabpane-active:visible").last();
    await panel.waitFor({ state: "visible", timeout: 5_000 });
    tabViews.push({ name: tabName, status: "OPENED_READ_ONLY", selection_method: selectionMethod, controls: await controls(panel), network_event_indexes: [start, network.length] });
  } catch (error) {
    const availableTabs = await page.locator(".ant-tabs-tab:visible").allTextContents().catch(() => []);
    tabViews.push({ name: tabName, status: "TAB_NOT_ACTIONABLE", controls: null, network_event_indexes: [start, network.length],
      current_route: normalizePath(new URL(page.url()).pathname), available_tabs: availableTabs.map(safeLabel), error: String(error).split("\n")[0] });
  }
}
const safeDetailActions = [];
if (process.env.ADMIN_MEMBER_SAFE_ACTIONS === "true") {
  const registered = [
    ["Phone Number", "View History"], ["Real Name", "View History"], ["Restricted Status", "Ban Records"],
    ["Balance", "Turnover Details"], ["The remaining purchases are free to rotate", "records"],
    ["General recharge rate", "operating record"], ["Referrer ID", "View History"],
    ["Registration Information", "Login Logs"], ["Member Level", "XP Turnover"],
    ["Available Mall Tokens", "View Token Wallet"], ["Total Top-ups", "View Credit/Debit Records"],
  ];
  for (const [contextLabel, buttonName] of registered) {
    action = `member_detail_reset_before_read_action:${contextLabel}:${buttonName}`;
    await page.goto(new URL("/member-center/list", baseUrl).toString(), { waitUntil: "domcontentloaded", timeout: 20_000 });
    const row = page.locator(".ant-table-tbody tr:not(.ant-table-measure-row):visible").first();
    await row.waitFor({ state: "visible", timeout: 15_000 });
    await row.getByRole("button", { name: "View Details", exact: true }).click();
    await page.waitForURL((url) => /\/member-center\/detail\//.test(url.pathname), { timeout: 15_000 }); await quiet();
    const start = network.length; action = `member_detail_read_action:${contextLabel}:${buttonName}`;
    try {
      const item = page.locator(".ant-descriptions-item").filter({ hasText: contextLabel }).first();
      const button = item.getByRole("button", { name: buttonName, exact: true }).first();
      await button.waitFor({ state: "visible", timeout: 5_000 }); await button.click(); await quiet();
      const overlay = page.locator(".ant-modal:visible,.ant-drawer:visible,[role=dialog]:visible").last();
      const activePanel = page.locator(".ant-tabs-tabpane-active:visible").last();
      const activeTabs = (await page.locator(".ant-layout-content .ant-tabs-tab-active:visible").allTextContents()).map(safeLabel);
      safeDetailActions.push({ context_label: contextLabel, action_name: buttonName, status: "OPENED_READ_ONLY",
        route_after: normalizePath(new URL(page.url()).pathname), active_tabs_after: activeTabs,
        overlay: await overlay.isVisible().catch(() => false) ? await controls(overlay) : null,
        active_panel: await activePanel.isVisible().catch(() => false) ? await controls(activePanel) : null,
        network_event_indexes: [start, network.length] });
      if (await overlay.isVisible().catch(() => false)) { await page.keyboard.press("Escape"); await page.waitForTimeout(250); }
    } catch (error) {
      safeDetailActions.push({ context_label: contextLabel, action_name: buttonName, status: "CONTROL_NOT_ACTIONABLE",
        route_after: normalizePath(new URL(page.url()).pathname), network_event_indexes: [start, network.length], error: String(error).split("\n")[0] });
    }
  }
}

const result = {
  captured_at: new Date().toISOString(), environment: "FAT", phase: "member_record_readonly_inventory",
  target_ref: "existing_readonly_member_1", target_scope: "structure evidence only; no write allowed",
  list: { route: "/member-center/list", controls: listControls, first_row_controls: firstRowControls },
  add_member_form: addMemberForm,
  detail: { route: detailRoute, controls: detailControls, tab_views: tabViews, safe_read_actions: safeDetailActions },
  network,
  side_effects: [],
  safety: { existing_record_write_actions_executed: 0, add_member_submitted: false, raw_uid_persisted: false, member_values_persisted: false },
};
fs.writeFileSync(out, JSON.stringify(result, null, 2) + "\n");
await browser.close();
console.log(JSON.stringify({ list_buttons: listControls.buttons.length, first_row_buttons: firstRowControls.buttons.length,
  add_member: addMemberForm.status, detail_route: detailRoute, detail_tabs: detailControls.tabs.length,
  detail_buttons: detailControls.buttons.length, tab_views_opened: tabViews.filter((tab) => tab.status === "OPENED_READ_ONLY").length,
  tab_views_blocked: tabViews.filter((tab) => tab.status !== "OPENED_READ_ONLY").length,
  safe_read_actions_opened: safeDetailActions.filter((item) => item.status === "OPENED_READ_ONLY").length,
  safe_read_actions_blocked: safeDetailActions.filter((item) => item.status !== "OPENED_READ_ONLY").length,
  network_events: network.length, side_effects: 0 }));
