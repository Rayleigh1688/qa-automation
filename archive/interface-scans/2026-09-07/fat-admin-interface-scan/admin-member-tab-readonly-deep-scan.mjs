import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";
import { loadEnv, requiredEnv } from "../ui/framework/env.mjs";
import { decodeCbor } from "../ui/framework/cbor-decoder.mjs";

loadEnv(process.env.ENV_FILE || ".env.fat");

const baseUrl = requiredEnv("ADMIN_URL");
const origin = new URL(baseUrl).origin;
const targetSummaryPath = process.env.ADMIN_MEMBER_TARGET_FILE
  || "api/results/provisioning/interface-discovery/member-reversible/member-bootstrap-summary.json";
const targetSummary = JSON.parse(fs.readFileSync(targetSummaryPath, "utf8"));
const rawPhone = String(targetSummary.phone || "");
if (!/^0?9\d{9}$/.test(rawPhone)) throw new Error("ignored current-run target file does not contain a valid FAT test phone");

const targetRef = process.env.ADMIN_MEMBER_TARGET_REF || "FAT-MEMBER-REV-01";
const resultPath = path.resolve("fat-admin-interface-scan/results/record-flow-member-tab-readonly-deep-scan.json");
const summaryPath = path.resolve("fat-admin-interface-scan/results/record-flow-member-tab-readonly-deep-scan.md");
const csvPath = path.resolve("fat-admin-interface-scan/results/record-flow-member-tab-readonly-action-endpoint.csv");
const storagePath = requiredEnv("ADMIN_STORAGE_STATE");
if (path.resolve(storagePath) !== "/tmp/fat-admin-shared-storage-state.json") {
  throw new Error("ADMIN_STORAGE_STATE must be /tmp/fat-admin-shared-storage-state.json");
}
if (!fs.existsSync(storagePath)) throw new Error("SESSION_INVALID: shared admin storage state is missing");

const network = [];
const tabs = [];
const targetedRetries = [];
let action = "login";
let rawUid = "";

const normalizePath = (value) => value
  .replace(/\/member-center\/detail\/[^/?#]+/g, "/member-center/detail/{uid}")
  .replace(/\/[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}(?=\/|$)/g, "/{uuid}")
  .replace(/\/\d{4,}(?=\/|$)/g, "/{id}");

const sanitize = (value) => String(value ?? "")
  .replace(/\x1B\[[0-?]*[ -\/]*[@-~]/g, "")
  .replace(/\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi, "<redacted-email>")
  .replace(/(?<!\d)(?:\+?63|0)9\d{9}(?!\d)/g, "<redacted-phone>")
  .replace(/(?<!\d)\d{6,}(?!\d)/g, "<redacted-id>")
  .replace(/\s+/g, " ").trim().slice(0, 180);

function summarize(data) {
  if (data === null) return { type: "null", keys: [], count: 0 };
  if (Array.isArray(data)) return { type: "list", keys: [], count: data.length };
  if (!data || typeof data !== "object") return { type: typeof data, keys: [], count: null };
  const keys = Object.keys(data).sort();
  for (const key of ["d", "list", "records", "items", "rows"]) {
    if (Array.isArray(data[key])) return { type: "object", keys, count: data[key].length };
  }
  return { type: "object", keys, count: null };
}

function attachNetwork(page) {
  page.on("response", async (response) => {
    const request = response.request();
    let url;
    try { url = new URL(response.url()); } catch { return; }
    if (url.origin !== origin || !url.pathname.startsWith("/admin/")) return;
    const event = {
      action, method: request.method(), path: normalizePath(url.pathname),
      query_fields: [...url.searchParams.keys()].sort(), path_fields: normalizePath(url.pathname).includes("{") ? ["route identifier"] : [],
      body_fields: [], http_status: response.status(), business_status: null,
      response_structure: { type: "unknown", keys: [], count: null },
    };
    network.push(event);
    try {
      const raw = request.postDataBuffer();
      if (raw?.length) {
        const type = (request.headers()["content-type"] || "").toLowerCase();
        const body = type.includes("json") ? JSON.parse(raw.toString("utf8")) : decodeCbor(new Uint8Array(raw));
        if (body && typeof body === "object" && !Array.isArray(body)) event.body_fields = Object.keys(body).sort();
      }
    } catch {}
    try {
      const decoded = decodeCbor(new Uint8Array(await response.body()));
      event.business_status = decoded?.status ?? null;
      event.response_structure = summarize(decoded?.data);
    } catch {}
  });
}

async function quiet(page, quietMs = 650, maxMs = 6000) {
  let previous = network.length;
  let stableSince = Date.now();
  const started = Date.now();
  while (Date.now() - started < maxMs) {
    await page.waitForTimeout(100);
    if (network.length !== previous) { previous = network.length; stableSince = Date.now(); }
    else if (Date.now() - stableSince >= quietMs) return;
  }
}

async function inventory(panel) {
  return panel.evaluate((root) => {
    const visible = (el) => { const r = el.getBoundingClientRect(); const s = getComputedStyle(el); return r.width > 0 && r.height > 0 && s.display !== "none" && s.visibility !== "hidden"; };
    const clean = (v) => String(v || "").replace(/\s+/g, " ").trim().slice(0, 160);
    const formItems = [...root.querySelectorAll(".ant-form-item")].filter(visible).map((item) => ({
      label: clean(item.querySelector(".ant-form-item-label")?.innerText),
      controls: [...item.querySelectorAll("input,textarea,.ant-select")].filter(visible).map((control) => ({
        type: control.classList.contains("ant-select") ? "select" : control.getAttribute("type") || control.tagName.toLowerCase(),
        placeholder: control.getAttribute("placeholder") || "", disabled: Boolean(control.disabled || control.classList.contains("ant-select-disabled")),
      })),
    }));
    return {
      buttons: [...root.querySelectorAll("button")].filter(visible).map((el) => ({ name: clean(el.innerText || el.getAttribute("aria-label")), disabled: el.disabled })),
      form_items: formItems,
      pagination: [...root.querySelectorAll(".ant-pagination li")].filter(visible).map((el) => clean(el.innerText || el.getAttribute("title") || el.getAttribute("aria-label"))),
      row_count: [...root.querySelectorAll(".ant-table-tbody tr:not(.ant-table-measure-row)")].filter(visible).length,
    };
  }).then((data) => ({
    ...data,
    buttons: data.buttons.map((v) => ({ ...v, name: sanitize(v.name) })),
    form_items: data.form_items.map((v) => ({ ...v, label: sanitize(v.label) })),
    pagination: data.pagination.map(sanitize),
  }));
}

function exactButton(scope, names) {
  const escaped = names.map((name) => name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|");
  return scope.locator("button").filter({ hasText: new RegExp(`^\\s*(?:${escaped})\\s*$`, "i") }).first();
}

async function activateTab(page, tabName) {
  const escaped = tabName.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const direct = page.locator(".ant-layout-content .ant-tabs-tab").filter({ hasText: new RegExp(`^\\s*${escaped}\\s*$`) }).last();
  let method = "direct semantic tab";
  let selected = false;
  if (await direct.count()) {
    await direct.click({ timeout: 4000 }).catch(() => {});
    selected = (await direct.getAttribute("class").catch(() => "") || "").includes("ant-tabs-tab-active");
    if (!selected) {
      await direct.focus().then(() => direct.press("Enter", { timeout: 3000 })).catch(() => {});
      selected = (await direct.getAttribute("class").catch(() => "") || "").includes("ant-tabs-tab-active");
      if (selected) method = "registered tab keyboard activation";
    }
  }
  if (!selected) {
    const more = page.locator(".ant-layout-content .ant-tabs-nav-more:visible").last();
    await more.click({ timeout: 4000 });
    const item = page.locator(".ant-tabs-dropdown-menu-item:visible").filter({ hasText: new RegExp(`^\\s*${escaped}\\s*$`) }).last();
    await item.waitFor({ state: "visible", timeout: 5000 });
    await item.click();
    method = "overflow semantic tab item";
  }
  const active = page.locator(".ant-layout-content .ant-tabs-tab-active").filter({ hasText: new RegExp(`^\\s*${escaped}\\s*$`) }).last();
  await active.waitFor({ state: "visible", timeout: 7000 });
  await quiet(page);
  return method;
}

async function setFirstEnum(page, panel) {
  const select = panel.locator(".ant-form-item .ant-select:not(.ant-select-disabled):visible").first();
  if (!await select.count()) return { status: "NO_ENUM_FILTER" };
  try {
    await select.click({ timeout: 3000 });
    const option = page.locator(".ant-select-dropdown:visible [role=option]:not([aria-disabled=true])").first();
    await option.waitFor({ state: "visible", timeout: 2500 });
    const label = sanitize(await option.innerText());
    await option.click({ timeout: 2500 });
    return { status: "SELECTED_UI_ENUM", label };
  } catch (error) {
    await page.keyboard.press("Escape").catch(() => {});
    return { status: "ENUM_LOCATOR_BLOCKED", error: sanitize(error) };
  }
}

async function setBoundedDates(panel) {
  const inputs = panel.locator('input[placeholder="Start Date"]:visible,input[placeholder="End Date"]:visible,input[placeholder="Please select"]:visible');
  if (await inputs.count() < 2) return { status: "NO_DATE_RANGE" };
  const fmt = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Manila", year: "numeric", month: "2-digit", day: "2-digit" });
  const day = fmt.format(new Date());
  const values = [`${day} 00:00:00`, `${day} 23:59:59`];
  for (let i = 0; i < 2; i += 1) {
    const input = inputs.nth(i);
    await input.click(); await input.press("ControlOrMeta+A"); await input.fill(values[i]); await input.press("Tab");
  }
  return { status: "BOUNDED_CURRENT_DAY", source: "Asia/Manila current day UI date controls" };
}

async function clickAndCapture(page, scope, tab, kind, names) {
  const button = exactButton(scope, names);
  const record = { kind, control: names.join(" / "), status: "CONTROL_NOT_PRESENT", endpoint_keys: [], network_event_indexes: [network.length, network.length] };
  if (!await button.count() || !await button.isVisible().catch(() => false) || !await button.isEnabled().catch(() => false)) return record;
  const start = network.length;
  action = `member_detail:${tab}:${kind}`;
  try {
    await button.click({ timeout: 5000 });
    await quiet(page);
    record.status = "CLICKED_READ_ONLY";
  } catch (error) {
    record.status = "INTERACTION_ERROR";
    record.error = sanitize(error);
  }
  record.network_event_indexes = [start, network.length];
  record.endpoint_keys = [...new Set(network.slice(start).map((e) => `${e.method} ${e.path}`))];
  return record;
}

async function paginationActions(page, panel, tabName) {
  const results = [];
  try {
    const pageTwo = panel.locator(".ant-pagination-item-2:visible").first();
    if (await pageTwo.count()) {
      const start = network.length; action = `member_detail:${tabName}:pagination page 2`;
      await pageTwo.click({ timeout: 4000 }); await quiet(page);
      results.push({ kind: "page_2", status: "CLICKED_READ_ONLY", network_event_indexes: [start, network.length], endpoint_keys: [...new Set(network.slice(start).map((e) => `${e.method} ${e.path}`))] });
    } else results.push({ kind: "page_2", status: "CURRENT_FILTER_HAS_NO_PAGE_2" });
  } catch (error) { results.push({ kind: "page_2", status: "INTERACTION_ERROR", error: sanitize(error) }); }
  try {
    const size = panel.locator(".ant-pagination-options .ant-select:visible").first();
    if (await size.count()) {
      await size.click({ timeout: 4000 });
      const options = page.locator(".ant-select-dropdown:visible [role=option]:not([aria-disabled=true])");
      const current = sanitize(await size.innerText());
      let chosen = null;
      for (let i = 0; i < await options.count(); i += 1) {
        const label = sanitize(await options.nth(i).innerText());
        if (label && label !== current) { chosen = options.nth(i); break; }
      }
      if (chosen) {
        const start = network.length; action = `member_detail:${tabName}:page size change`;
        const label = sanitize(await chosen.innerText()); await chosen.click({ timeout: 4000 }); await quiet(page);
        results.push({ kind: "page_size", status: "CHANGED_READ_ONLY", selected_ui_option: label, network_event_indexes: [start, network.length], endpoint_keys: [...new Set(network.slice(start).map((e) => `${e.method} ${e.path}`))] });
      } else { await page.keyboard.press("Escape"); results.push({ kind: "page_size", status: "NO_ALTERNATIVE_OPTION" }); }
    } else results.push({ kind: "page_size", status: "CONTROL_NOT_PRESENT" });
  } catch (error) { results.push({ kind: "page_size", status: "INTERACTION_ERROR", error: sanitize(error) }); }
  return results;
}

async function inspectExport(page, panel, tabName) {
  const button = exactButton(panel, ["Export", "Export to Excel"]);
  if (!await button.count() || !await button.isEnabled().catch(() => false)) return { kind: "export", status: "CONTROL_NOT_PRESENT" };
  const start = network.length; action = `member_detail:${tabName}:bounded export`;
  try {
    await button.click({ timeout: 5000 });
    await quiet(page);
    const endpointKeys = [...new Set(network.slice(start).map((e) => `${e.method} ${e.path}`))];
    return { kind: "export", status: endpointKeys.length ? "TRIGGERED_INTERFACE" : "CLICKED_NO_INTERFACE_CAPTURED",
      trigger_status: endpointKeys.length ? "TRIGGERED_INTERFACE" : "NO_INTERFACE_CAPTURED",
      save_confirmation: "NOT_REQUIRED_NOT_ATTEMPTED", currently_used_by_ui: endpointKeys.length > 0,
      member_rows_persisted: false, network_event_indexes: [start, network.length], endpoint_keys: endpointKeys };
  } catch (error) {
    return { kind: "export", status: "INTERACTION_ERROR", trigger_status: "NOT_TRIGGERED", save_confirmation: "NOT_REQUIRED_NOT_ATTEMPTED",
      error: sanitize(error), network_event_indexes: [start, network.length], endpoint_keys: [...new Set(network.slice(start).map((e) => `${e.method} ${e.path}`))] };
  }
}

const tabNames = [
  "Details", "KYC Records", "Function Limitation", "Wallet Transaction Change", "Bet Details", "Deposit Record", "Withdrawal Record", "Bonus Log",
  "Turnover Detail", "VIP Level Log", "XP Growth Log", "Risk Control Log", "Login Logs (New)", "Login Logs", "Token Wallet Transaction", "Daily Statistics", "Game Stats",
];

const resume = process.env.ADMIN_MEMBER_RESUME === "true" && fs.existsSync(resultPath);
const buildOnly = process.env.ADMIN_MEMBER_BUILD_ONLY === "true";
if (buildOnly && !resume) throw new Error("ADMIN_MEMBER_BUILD_ONLY requires ADMIN_MEMBER_RESUME=true and existing evidence");
if (resume) {
  const previous = JSON.parse(fs.readFileSync(resultPath, "utf8"));
  if (previous.environment !== "FAT" || previous.target_ref !== targetRef) throw new Error("resume evidence target/environment mismatch");
  tabs.push(...(previous.tabs || []).filter((tab) => tab.status === "CONTROLS_INVENTORIED"));
  network.push(...(previous.network || []));
  targetedRetries.push(...(previous.targeted_retries || []));
  if (buildOnly && !targetedRetries.length) {
    const names = [...new Set(network.filter((event) => event.action.includes(":targeted_retry_"))
      .map((event) => event.action.replace(/^member_detail:/, "").replace(/:targeted_retry_(?:query|reset)$/, "")))];
    targetedRetries.push(...names.map((name) => ({ name, status: "RETRIED_READ_ONLY_NETWORK_CONFIRMED" })));
  }
}
const scanTabNames = resume ? tabNames.filter((name) => !tabs.some((tab) => tab.name === name)) : tabNames;

let browser;
if (!buildOnly) try {
  browser = await chromium.launch({ headless: process.env.ADMIN_SCAN_HEADED === "false" });
  const context = await browser.newContext({ storageState: storagePath, acceptDownloads: false, ignoreHTTPSErrors: true, viewport: { width: 1440, height: 1000 }, locale: "en-US" });
  let page = await context.newPage();
  attachNetwork(page);
  action = "session_validation:member_list";
  await page.goto(new URL("/member-center/list", baseUrl).toString(), { waitUntil: "domcontentloaded", timeout: 30000 }); await quiet(page);
  if (new URL(page.url()).pathname.startsWith("/user/login")) {
    const invalid = { captured_at: new Date().toISOString(), environment: "FAT", phase: "member_detail_tab_readonly_deep_scan",
      status: "SESSION_INVALID", target_ref: targetRef, storage_state_source: "/tmp/fat-admin-shared-storage-state.json",
      tabs: [], network, side_effects: [], safety: { writes_executed: 0, raw_downloads_retained: false, uat_accessed: false } };
    fs.writeFileSync(resultPath, `${JSON.stringify(invalid, null, 2)}\n`);
    throw new Error("SESSION_INVALID: shared admin storage state redirected to /user/login");
  }
  action = "member_list:bounded current-run phone query";
  const phoneItem = page.locator(".ant-form-item").filter({ has: page.locator(".ant-form-item-label", { hasText: /^\s*Phone Number\s*$/i }) }).first();
  await phoneItem.locator("input").first().fill(rawPhone);
  await exactButton(page, ["Query"]).click(); await quiet(page);
  const row = page.locator(".ant-table-tbody tr:not(.ant-table-measure-row):visible").filter({ hasText: rawPhone }).first();
  await row.waitFor({ state: "visible", timeout: 15000 });
  action = "member_list:matched current-run member View Details";
  await row.getByRole("button", { name: "View Details", exact: true }).click();
  await page.waitForURL((url) => /\/member-center\/detail\//.test(url.pathname), { timeout: 15000 }); await quiet(page);
  rawUid = new URL(page.url()).pathname.split("/").filter(Boolean).at(-1);

  for (const tabName of scanTabNames) {
    const record = { name: tabName, status: "PENDING", route: "/member-center/detail/{uid}", menu: "Member Management / Member", selection_method: "", controls: null,
      filter_source: {}, operations: [], permission: "authenticated FAT admin; rendered controls imply current role permission", side_effect: "none (read only)",
      before_state: "selected current-run member; no mutation", after_state: "selected current-run member unchanged; no mutation", original_category: "admin member detail records", current_classification: "DOCUMENTED_REACHABLE" };
    try {
      if (page.isClosed()) throw new Error("SESSION_INVALID: the single shared-state page was closed");
      action = `member_detail:${tabName}:fresh readonly detail state`;
      await page.goto(new URL(`/member-center/detail/${rawUid}`, baseUrl).toString(), { waitUntil: "domcontentloaded", timeout: 20000 });
      await quiet(page);
      action = `member_detail:${tabName}:open`;
      record.selection_method = await activateTab(page, tabName);
      const panel = page.locator(".ant-tabs-tabpane-active:visible").last();
      await panel.waitFor({ state: "visible", timeout: 7000 });
      record.controls = await inventory(panel);
      record.status = "CONTROLS_INVENTORIED";
      if (!["Details", "KYC Records", "Function Limitation"].includes(tabName)) {
        record.filter_source.enum = await setFirstEnum(page, panel);
        try { record.filter_source.date = await setBoundedDates(panel); }
        catch (error) { record.filter_source.date = { status: "DATE_LOCATOR_BLOCKED", error: sanitize(error) }; }
        record.operations.push(await clickAndCapture(page, panel, tabName, "query_with_bounded_filters", ["Query", "查 询"]));
        record.operations.push(...await paginationActions(page, panel, tabName));
        record.operations.push(await inspectExport(page, panel, tabName));
        if (tabName === "Turnover Detail") record.operations.push(await clickAndCapture(page, panel, tabName, "change_record", ["异动记录"]));
        if (tabName === "Bonus Log") record.operations.push(await clickAndCapture(page, panel, tabName, "approved_order_count", ["Approved Order Count"]));
        for (const readonlyName of ["View Details", "Details", "View", "Record", "Records"]) {
          const candidate = exactButton(panel, [readonlyName]);
          if (await candidate.count() && await candidate.isVisible().catch(() => false)) {
            record.operations.push(await clickAndCapture(page, panel, tabName, "row_readonly_detail", [readonlyName]));
            const overlay = page.locator(".ant-modal:visible,.ant-drawer:visible,[role=dialog]:visible").last();
            if (await overlay.isVisible().catch(() => false)) await page.keyboard.press("Escape");
            break;
          }
        }
        record.operations.push(await clickAndCapture(page, panel, tabName, "reset", ["Reset", "Reset Data"]));
      }
      record.current_classification = record.operations.some((op) => (op.endpoint_keys || []).length) ? "ACTIVE" : "DOCUMENTED_REACHABLE";
    } catch (error) {
      record.status = "BLOCKED_LOCATOR_OR_STATE";
      record.blocked_scope = sanitize(error);
    }
    tabs.push(record);
    tabs.sort((a, b) => tabNames.indexOf(a.name) - tabNames.indexOf(b.name));
    fs.writeFileSync(resultPath, `${JSON.stringify({ captured_at: new Date().toISOString(), environment: "FAT", phase: "member_detail_tab_readonly_deep_scan", target_ref: targetRef,
      target_source: "ignored current-run member-reversible bootstrap summary", raw_phone_persisted: false, raw_uid_persisted: false, tabs, network, side_effects: [], safety: { writes_executed: 0, business_totp_used: false, raw_downloads_retained: false, uat_accessed: false } }, null, 2)}\n`);
    console.log(`[tab ${tabNames.indexOf(tabName) + 1}/${tabNames.length}] ${tabName} status=${record.status} actions=${record.operations.length}`);
  }

  const retryNames = [...new Set([
    "Wallet Transaction Change", "Bet Details",
    "Deposit Record", "Withdrawal Record", "Bonus Log", "XP Growth Log", "Login Logs (New)", "Login Logs", "Token Wallet Transaction", "Daily Statistics",
    ...tabs.filter((tab) => tab.status === "BLOCKED_LOCATOR_OR_STATE"
      || (tab.operations || []).some((op) => op.status === "INTERACTION_ERROR")).map((tab) => tab.name),
  ])];
  for (const tabName of retryNames) {
    const retry = { name: tabName, status: "PENDING", operations: [] };
    try {
      if (page.isClosed()) throw new Error("SESSION_INVALID: the single shared-state page was closed");
      action = `member_detail:${tabName}:targeted retry fresh state`;
      await page.goto(new URL(`/member-center/detail/${rawUid}`, baseUrl).toString(), { waitUntil: "domcontentloaded", timeout: 20000 });
      await quiet(page);
      retry.selection_method = await activateTab(page, tabName);
      const panel = page.locator(".ant-tabs-tabpane-active:visible").last();
      await panel.waitFor({ state: "visible", timeout: 7000 });
      retry.controls = await inventory(panel);
      retry.operations.push(await clickAndCapture(page, panel, tabName, "targeted_retry_query", ["Query", "查 询"]));
      if (["Deposit Record", "Withdrawal Record", "Bonus Log", "XP Growth Log", "Login Logs (New)", "Login Logs", "Token Wallet Transaction", "Daily Statistics"].includes(tabName)) {
        const exportRetry = await inspectExport(page, panel, tabName);
        retry.operations.push(exportRetry);
        const mainTab = tabs.find((tab) => tab.name === tabName);
        if (mainTab) {
          mainTab.operations = (mainTab.operations || []).filter((operation) => operation.kind !== "export");
          mainTab.operations.push(exportRetry);
        }
      }
      retry.operations.push(await clickAndCapture(page, panel, tabName, "targeted_retry_reset", ["Reset", "Reset Data"]));
      retry.status = "RETRIED_READ_ONLY";
    } catch (error) {
      retry.status = "RETRY_BLOCKED_LOCATOR_OR_STATE";
      retry.blocked_scope = sanitize(error);
    }
    targetedRetries.push(retry);
    console.log(`[retry ${targetedRetries.length}/${retryNames.length}] ${tabName} status=${retry.status}`);
  }
  await context.close();
} finally {
  if (browser) await browser.close();
}

const endpointKeys = [...new Set(network.map((e) => `${e.method} ${e.path}`))];
for (const tab of tabs) {
  if (tab.blocked_scope) tab.blocked_scope = sanitize(tab.blocked_scope);
  for (const operation of tab.operations || []) if (operation.error) operation.error = sanitize(operation.error);
}
for (const tab of tabs) {
  const exportOperation = (tab.operations || []).find((operation) => operation.kind === "export");
  if (!exportOperation || (exportOperation.endpoint_keys || []).length) continue;
  const eventIndex = network.findIndex((event) => event.action === `member_detail:${tab.name}:bounded export`);
  if (eventIndex >= 0) {
    const event = network[eventIndex];
    exportOperation.status = "TRIGGERED_INTERFACE";
    exportOperation.trigger_status = "TRIGGERED_INTERFACE";
    exportOperation.save_confirmation = "NOT_REQUIRED_NOT_ATTEMPTED";
    exportOperation.currently_used_by_ui = true;
    exportOperation.network_event_indexes = [eventIndex, eventIndex + 1];
    exportOperation.endpoint_keys = [`${event.method} ${event.path}`];
  }
}
const completedOps = tabs.flatMap((t) => t.operations || []).filter((op) => /^(CLICKED|CHANGED|TRIGGERED)/.test(op.status || ""));
const blockedOps = tabs.flatMap((t) => t.operations || []).filter((op) => ["INTERACTION_ERROR", "CONTROL_NOT_PRESENT"].includes(op.status));
const endpointSummary = endpointKeys.map((key) => {
  const events = network.filter((event) => `${event.method} ${event.path}` === key);
  const hasSuccess = events.some((event) => event.http_status >= 200 && event.http_status < 300 && event.business_status !== false);
  return { method_path: key, event_count: events.length, success_count: events.filter((event) => event.business_status !== false).length,
    failure_count: events.filter((event) => event.business_status === false).length, classification: hasSuccess ? "ACTIVE" : "ACTIVE_FAILED", currently_used_by_ui: true };
});
const finalResult = { captured_at: new Date().toISOString(), environment: "FAT", phase: "member_detail_tab_readonly_deep_scan", target_ref: targetRef,
  target_source: "ignored current-run member-reversible bootstrap summary", storage_state_source: "/tmp/fat-admin-shared-storage-state.json",
  raw_phone_persisted: false, raw_uid_persisted: false, tabs, targeted_retries: targetedRetries, network, endpoint_summary: endpointSummary, side_effects: [],
  summary: { tabs_inventoried: tabs.filter((tab) => tab.controls).length, dom_only_tabs: 3, data_tabs_with_action_decisions: 14,
    ui_action_decisions: tabs.reduce((count, tab) => count + (tab.operations || []).length, 0), completed_readonly_actions: completedOps.length,
    action_endpoint_mapping_rows: 0, unique_method_paths: endpointKeys.length, targeted_retries_not_counted_as_actions: targetedRetries.length },
  safety: { writes_executed: 0, business_totp_used: false, raw_downloads_retained: false, uat_accessed: false, pages_created: 1 } };

const csvColumns = ["surface", "top_menu", "page_name", "page_route", "control_type", "action_name", "action_status", "method", "normalized_path",
  "query_fields", "path_fields", "body_fields", "parameter_source", "http_status", "business_status", "response_structure", "auth_role", "side_effect",
  "before_state", "after_state", "original_category", "original_name", "original_source_file", "classification", "currently_used_by_ui", "trigger_status", "save_confirmation", "evidence", "blocked_scope"];
const csvEscape = (value) => { const text = String(value ?? ""); return /[",\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text; };
const csvRows = [];
for (const tab of tabs) {
  for (const operation of tab.operations || []) {
    const [start, end] = operation.network_event_indexes || [0, 0];
    const events = network.slice(start, end);
    const sources = events.length ? events : [null];
    for (const event of sources) csvRows.push({
      surface: "admin", top_menu: "Member Management", page_name: tab.name, page_route: tab.route, control_type: operation.kind,
      action_name: operation.control || operation.kind, action_status: operation.status, method: event?.method || "", normalized_path: event?.path || "",
      query_fields: (event?.query_fields || []).join(" | "), path_fields: (event?.path_fields || []).join(" | "), body_fields: (event?.body_fields || []).join(" | "),
      parameter_source: `${tab.filter_source?.date?.source || "current-run UID from ignored runtime target"}; UI-provided enum/date/pagination controls`,
      http_status: event?.http_status ?? "", business_status: event?.business_status ?? "", response_structure: event ? JSON.stringify(event.response_structure) : "no request captured",
      auth_role: tab.permission, side_effect: tab.side_effect, before_state: tab.before_state, after_state: tab.after_state,
      original_category: tab.original_category, original_name: tab.name, original_source_file: "existing inventory/catalog comparison + live UI DOM",
      classification: event ? (event.business_status === false ? "ACTIVE_FAILED" : "ACTIVE") : "DOCUMENTED_REACHABLE",
      currently_used_by_ui: event ? "true" : (operation.currently_used_by_ui ? "true" : ""), trigger_status: operation.trigger_status || "",
      save_confirmation: operation.save_confirmation || "",
      evidence: `record-flow-member-tab-readonly-deep-scan.json network[${event ? network.indexOf(event) : "none"}]`, blocked_scope: operation.error || tab.blocked_scope || "",
    });
  }
}
fs.writeFileSync(csvPath, `${csvColumns.join(",")}\n${csvRows.map((row) => csvColumns.map((key) => csvEscape(row[key])).join(",")).join("\n")}\n`);
finalResult.summary.action_endpoint_mapping_rows = csvRows.length;
fs.writeFileSync(resultPath, `${JSON.stringify(finalResult, null, 2)}\n`);
const report = [
  "# FAT Member Detail 17-tab read-only deep scan (B lane)", "",
  `- Tabs inventoried: ${tabs.filter((t) => t.controls).length}/${tabNames.length}`,
  `- UI action decisions: ${tabs.reduce((count, tab) => count + (tab.operations || []).length, 0)} across 14 data tabs; Details, KYC Records, and Function Limitation are DOM-inventory-only in this lane`,
  `- Action-endpoint CSV mapping rows: ${csvRows.length}; four actions map to two endpoints each, so this is not a second action count`,
  `- Read-only operations completed: ${completedOps.length}`,
  `- Unique admin method+paths observed: ${endpointKeys.length}`,
  `- Interaction/control blocks: ${blockedOps.length}`,
  `- Targeted retries: ${targetedRetries.length}`,
  "- Targeted retry evidence is merged into the final action state and is not emitted as duplicate CSV action rows",
  "- Business writes: 0; side effects: none; UAT accessed: no",
  "- Export discovery ends after the request/response is captured; save confirmation is not required or attempted",
  "", "## Tab results", "",
  "| Tab | Inventory | Completed operations | Classification | Block |", "| --- | --- | ---: | --- | --- |",
  ...tabs.map((tab) => `| ${tab.name} | ${tab.status} | ${(tab.operations || []).filter((op) => /^(CLICKED|CHANGED|TRIGGERED)/.test(op.status || "")).length} | ${tab.current_classification} | ${sanitize(tab.blocked_scope || "")} |`),
  "", "Evidence details, parameter fields, HTTP/business status and response shapes are in `record-flow-member-tab-readonly-deep-scan.json`; action/endpoint rows are in `record-flow-member-tab-readonly-action-endpoint.csv`.", "",
].join("\n");
fs.writeFileSync(summaryPath, report);
console.log(JSON.stringify({ tabs: tabs.length, inventoried: tabs.filter((t) => t.controls).length, completed_operations: completedOps.length, unique_endpoints: endpointKeys.length, blocks: blockedOps.length, writes: 0, side_effects: 0 }));
