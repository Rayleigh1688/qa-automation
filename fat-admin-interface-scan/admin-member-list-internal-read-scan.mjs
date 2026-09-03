import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";
import { loadEnv, requiredEnv } from "../ui/framework/env.mjs";
import { decodeCbor } from "../ui/framework/cbor-decoder.mjs";

loadEnv(process.env.ENV_FILE || ".env.fat");
const baseUrl = requiredEnv("ADMIN_URL");
const origin = new URL(baseUrl).origin;
const output = path.resolve("fat-admin-interface-scan/results/member-list-a-internal-read-scan.json");
const storagePath = process.env.ADMIN_STORAGE_STATE;
if (!storagePath) throw new Error("ADMIN_STORAGE_STATE is required; generate one shared FAT admin session before running the A-line scan");
if (!fs.existsSync(storagePath)) throw new Error("ADMIN_STORAGE_STATE does not exist");
const network = [];
const actions = [];
let action = "login";

const normalizePath = (value) => value
  .replace(/\/member-center\/detail\/[^/?#]+/g, "/member-center/detail/{uid}")
  .replace(/\/[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}(?=\/|$)/g, "/{uuid}")
  .replace(/\/\d{4,}(?=\/|$)/g, "/{id}");
const safeText = (value) => {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  if (!text) return "";
  if (/\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/i.test(text)) return "<redacted-dynamic-label>";
  if (/(?:\+?63|0)9\d{9}|\b(?:\d{1,3}\.){3}\d{1,3}\b|\b\d{7,}\b/.test(text)) return "<redacted-dynamic-label>";
  return text.slice(0, 160);
};
const responseSummary = (data) => {
  if (Array.isArray(data)) return { type: "list", keys: [], count: data.length };
  if (data === null) return { type: "null", keys: [], count: 0 };
  if (!data || typeof data !== "object") return { type: typeof data, keys: [], count: null };
  const keys = Object.keys(data).sort();
  const listKey = ["d", "list", "records", "items", "rows"].find((key) => Array.isArray(data[key]));
  return { type: "object", keys, count: listKey ? data[listKey].length : null };
};

function attachNetwork(page) {
  page.on("response", async (response) => {
    const request = response.request();
    if (!["xhr", "fetch"].includes(request.resourceType())) return;
    let url;
    try { url = new URL(response.url()); } catch { return; }
    if (url.origin !== origin) return;
    let bodyFields = [], decoded = null;
    try {
      const raw = request.postDataBuffer();
      if (raw?.length) {
        const type = (request.headers()["content-type"] || "").toLowerCase();
        const body = type.includes("json") ? JSON.parse(raw.toString("utf8")) : decodeCbor(new Uint8Array(raw));
        if (body && typeof body === "object" && !Array.isArray(body)) bodyFields = Object.keys(body).sort();
      }
    } catch {}
    try { decoded = decodeCbor(new Uint8Array(await response.body())); } catch {}
    const summary = responseSummary(decoded?.data);
    network.push({
      action, method: request.method(), path: normalizePath(url.pathname),
      query_fields: [...url.searchParams.keys()].sort(), body_fields: bodyFields,
      http_status: response.status(), business_status: decoded?.status ?? null,
      response_type: summary.type, response_keys: summary.keys, record_count: summary.count,
    });
  });
}

async function quiet(page, ms = 700) {
  let last = network.length, stable = Date.now();
  for (let index = 0; index < 80; index += 1) {
    await page.waitForTimeout(100);
    if (last !== network.length) { last = network.length; stable = Date.now(); }
    else if (Date.now() - stable >= ms) return;
  }
}

async function formInventory(scope) {
  return scope.locator(".ant-form-item:visible").evaluateAll((items) => items.map((item, index) => {
    const clean = (value) => String(value || "").replace(/\s+/g, " ").trim();
    const input = item.querySelector("input:enabled,textarea:enabled");
    const select = item.querySelector(".ant-select:not(.ant-select-disabled)");
    return {
      index,
      label: clean(item.querySelector(".ant-form-item-label")?.innerText),
      input: input ? { type: input.getAttribute("type") || input.tagName.toLowerCase(), placeholder: input.getAttribute("placeholder") || "" } : null,
      select: Boolean(select),
    };
  })).then((items) => items.map((item) => ({ ...item, label: safeText(item.label), input: item.input ? { ...item.input, placeholder: safeText(item.input.placeholder) } : null })));
}

async function visibleOptions(page) {
  const dropdown = page.locator(".ant-select-dropdown:visible").last();
  return (await dropdown.locator(".ant-select-item-option:not(.ant-select-item-option-disabled)").allInnerTexts()).map(safeText).filter(Boolean);
}

async function clickQuery(page, label) {
  const start = network.length;
  action = label;
  await page.locator("button").filter({ hasText: /^\s*Query\s*$/i }).first().click();
  await quiet(page);
  actions.push({ name: label, status: "EXECUTED_READ_ONLY", network_event_indexes: [start, network.length], side_effect: "none" });
}

const browser = await chromium.launch({ headless: process.env.ADMIN_SCAN_HEADED !== "true" });
try {
  const context = await browser.newContext({ ignoreHTTPSErrors: true, viewport: { width: 1440, height: 1000 }, locale: "en-US", storageState: storagePath, acceptDownloads: true });
  const page = await context.newPage();
  page.setDefaultTimeout(5_000);
  attachNetwork(page);
  action = "member_list:initialization from reused storage state";
  await page.goto(new URL("/member-center/list", baseUrl).toString(), { waitUntil: "domcontentloaded", timeout: 30_000 });
  await quiet(page);
  if (new URL(page.url()).pathname.startsWith("/user/login")) throw new Error("ADMIN_STORAGE_STATE is unauthenticated or expired");
  const authEvent = [...network].reverse().find((item) => item.path === "/admin/me/detail");
  if (!authEvent || authEvent.http_status !== 200 || authEvent.business_status !== true) throw new Error("ADMIN_STORAGE_STATE failed /admin/me/detail verification");
  const content = page.locator(".ant-layout-content").first();
  const form = content.locator("form").first();
  const domInventory = {
    form_items: await formInventory(form),
    buttons: (await content.locator("button:visible").allInnerTexts()).map(safeText).filter(Boolean),
    pagination: {
      items: (await content.locator(".ant-pagination-item:visible").allInnerTexts()).map(safeText),
      page_size_text: safeText(await content.locator(".ant-pagination-options:visible").innerText().catch(() => "")),
    },
    row_buttons: [...new Set((await content.locator(".ant-table-tbody tr:not(.ant-table-measure-row):visible").first().locator("button:visible").allInnerTexts()).map(safeText).filter(Boolean))],
  };

  // Capture every select's actual UI enum options without changing member state.
  const selectInventories = [];
  const selectItems = form.locator(".ant-form-item").filter({ has: page.locator(".ant-select:not(.ant-select-disabled)") });
  for (let index = 0; index < await selectItems.count(); index += 1) {
    const item = selectItems.nth(index);
    const label = safeText(await item.locator(".ant-form-item-label").innerText().catch(() => `select_${index}`));
    const select = item.locator(".ant-select").first();
    try {
      await select.click();
      await page.waitForTimeout(150);
      const options = await visibleOptions(page);
      selectInventories.push({ label, status: "OPTIONS_ENUMERATED", options });
      await page.keyboard.press("Escape");
    } catch (error) {
      selectInventories.push({ label, status: "STRICT_LOCATOR_ERROR", options: [], error: String(error).split("\n")[0] });
    }
  }

  // Each text/date filter is submitted independently with a non-matching or valid bounded probe, then Reset.
  const inputItems = form.locator(".ant-form-item").filter({ has: page.locator("input:enabled"), hasNot: page.locator(".ant-select") });
  for (let index = 0; index < await inputItems.count(); index += 1) {
    const item = inputItems.nth(index);
    const label = safeText(await item.locator(".ant-form-item-label").innerText().catch(() => `input_${index}`));
    const inputs = item.locator("input:enabled");
    const inputCount = await inputs.count();
    const start = network.length;
    try {
      if (inputCount >= 2 || /date|time/i.test(label + " " + await inputs.first().getAttribute("placeholder"))) {
        // Date range is already valid on initialization; submit it to prove the field family.
        await clickQuery(page, `member_list:filter:${label || "date_range"}`);
      } else {
        const input = inputs.first();
        const placeholder = await input.getAttribute("placeholder") || "";
        const probe = /ip/i.test(`${label} ${placeholder}`) ? "203.0.113.250"
          : /count|amount|minimum|maximum/i.test(`${label} ${placeholder}`) ? "999999"
          : /uid|id|phone|number/i.test(`${label} ${placeholder}`) ? "999999999999999" : "A_LANE_NO_MATCH";
        await input.fill(probe);
        await clickQuery(page, `member_list:filter:${label || safeText(placeholder) || index}`);
      }
      await page.locator("button").filter({ hasText: /^\s*Reset\s*$/i }).first().click();
      await quiet(page);
    } catch (error) {
      actions.push({ name: `member_list:filter:${label || index}`, status: "STRICT_LOCATOR_OR_VALIDATION_ERROR", network_event_indexes: [start, network.length], side_effect: "none", error: String(error).split("\n")[0] });
    }
  }

  // One representative value for every select family.
  for (let index = 0; index < await selectItems.count(); index += 1) {
    const item = selectItems.nth(index);
    const label = safeText(await item.locator(".ant-form-item-label").innerText().catch(() => `select_${index}`));
    const start = network.length;
    try {
      await item.locator(".ant-select").first().click();
      const dropdown = page.locator(".ant-select-dropdown:visible").last();
      const option = dropdown.locator(".ant-select-item-option:not(.ant-select-item-option-disabled)").filter({ hasNotText: /^\s*All\s*$/i }).first();
      await option.waitFor({ state: "visible", timeout: 3000 });
      const optionName = safeText(await option.innerText());
      await option.click();
      await clickQuery(page, `member_list:filter:${label}:${optionName}`);
      await page.locator("button").filter({ hasText: /^\s*Reset\s*$/i }).first().click();
      await quiet(page);
    } catch (error) {
      await page.keyboard.press("Escape").catch(() => {});
      actions.push({ name: `member_list:filter:${label}`, status: "CURRENT_STATE_NOT_ACTIONABLE", network_event_indexes: [start, network.length], side_effect: "none", error: String(error).split("\n")[0] });
    }
  }

  // Representative two-field combination: first usable text filter plus first usable enum.
  const comboStart = network.length;
  try {
    const textItem = inputItems.filter({ hasNot: page.locator("input[placeholder*='Date'],input[placeholder*='date']") }).first();
    const textInput = textItem.locator("input:enabled").first();
    await textInput.fill("A_LANE_NO_MATCH");
    const enumItem = selectItems.first();
    await enumItem.locator(".ant-select").first().click();
    const dropdown = page.locator(".ant-select-dropdown:visible").last();
    const option = dropdown.locator(".ant-select-item-option:not(.ant-select-item-option-disabled)").filter({ hasNotText: /^\s*All\s*$/i }).first();
    await option.click();
    await clickQuery(page, "member_list:combined_filter:text_plus_enum");
  } catch (error) {
    actions.push({ name: "member_list:combined_filter:text_plus_enum", status: "STRICT_LOCATOR_OR_VALIDATION_ERROR", network_event_indexes: [comboStart, network.length], side_effect: "none", error: String(error).split("\n")[0] });
  }

  // Export only the bounded default date-window result; download content is discarded immediately.
  action = "member_list:prepare bounded current-window Export";
  await page.goto(new URL("/member-center/list", baseUrl).toString(), { waitUntil: "domcontentloaded", timeout: 30_000 });
  await quiet(page);
  const exportStart = network.length;
  action = "member_list:Export bounded current-window result";
  if (process.env.ADMIN_MEMBER_SKIP_EXPORT === "true") {
    actions.push({ name: action, status: "CLICKED_NO_INTERFACE_EVIDENCE", trigger_status: "NOT_OBSERVED", save_confirmation: "NOT_REQUIRED_NOT_ATTEMPTED", network_event_indexes: [exportStart, network.length], side_effect: "none", error: "Prior semantic click produced no captured request/response or download event; not retried per export policy" });
  } else try {
    const downloadPromise = page.waitForEvent("download", { timeout: 7000 }).catch(() => null);
    const exportButton = page.locator("button:visible").filter({ hasText: /^\s*Export\s*$/i }).first();
    await exportButton.scrollIntoViewIfNeeded();
    await exportButton.click({ noWaitAfter: true });
    await quiet(page);
    const download = await downloadPromise;
    if (download) await download.delete();
    actions.push({ name: action, status: download ? "EXECUTED_DOWNLOAD_DISCARDED" : "EXECUTED_NETWORK_ONLY", trigger_status: "TRIGGERED_INTERFACE", save_confirmation: "NOT_REQUIRED_NOT_ATTEMPTED", network_event_indexes: [exportStart, network.length], side_effect: "none; bounded current-window export; no member export retained" });
  } catch (error) {
    actions.push({ name: action, status: "STRICT_LOCATOR_ERROR", network_event_indexes: [exportStart, network.length], side_effect: "none", error: String(error).split("\n")[0] });
  }
  action = "member_list:restore after Export";
  await page.goto(new URL("/member-center/list", baseUrl).toString(), { waitUntil: "domcontentloaded", timeout: 30_000 });
  await quiet(page);

  // Batch query is treated as a read form. It receives an intentionally non-matching synthetic value only.
  const batchStart = network.length;
  action = "member_list:Batch query bounded synthetic no-match";
  let batchForm = null;
  try {
    const batchToggle = page.locator("button").filter({ hasText: /^\s*Batch query\s*$/i }).first();
    await batchToggle.click();
    await page.waitForTimeout(300);
    const overlay = page.locator(".ant-modal:visible,.ant-drawer:visible,[role=dialog]:visible").last();
    const overlayVisible = await overlay.isVisible().catch(() => false);
    const batchScope = overlayVisible ? overlay : content;
    batchForm = {
      presentation: overlayVisible ? "overlay" : "in_page",
      title: safeText(await batchScope.locator(".ant-modal-title,.ant-drawer-title").first().innerText().catch(() => "")),
      form_items: await formInventory(batchScope),
      buttons: (await batchScope.locator("button:visible").allInnerTexts()).map(safeText).filter(Boolean),
    };
    const batchInput = batchScope.locator("textarea:enabled,input:enabled").last();
    if (await batchInput.count()) await batchInput.fill("999999999999999");
    const submit = batchScope.locator("button:visible").filter({ hasText: /^\s*(Apply filter|Query|Search|Confirm|OK)\s*$/i }).last();
    if (await submit.count()) { await submit.click(); await quiet(page); }
    else throw new Error("registered Batch query overlay has no strict read-submit button");
    actions.push({ name: action, status: "EXECUTED_READ_ONLY", network_event_indexes: [batchStart, network.length], side_effect: "none" });
    if (overlayVisible && await overlay.isVisible().catch(() => false)) await page.keyboard.press("Escape");
  } catch (error) {
    actions.push({ name: action, status: "STRICT_LOCATOR_OR_FORM_ERROR", network_event_indexes: [batchStart, network.length], side_effect: "none", error: String(error).split("\n")[0] });
    await page.keyboard.press("Escape").catch(() => {});
  }

  action = "member_list:restore after Batch query";
  await page.goto(new URL("/member-center/list", baseUrl).toString(), { waitUntil: "domcontentloaded", timeout: 30_000 });
  await quiet(page);

  // Pagination: first choose a smaller page size so page 2 exists, then navigate to it.
  const sizeStart = network.length;
  try {
    action = "member_list:pagination:page_size_change";
    const sizeSelect = page.locator(".ant-pagination-options .ant-select:visible").first();
    await sizeSelect.click();
    const sizeDropdown = page.locator(".ant-select-dropdown:visible").last();
    const selected = sizeDropdown.locator(".ant-select-item-option-selected").first();
    const selectedText = await selected.innerText().catch(() => "");
    const tenPerPage = sizeDropdown.locator(".ant-select-item-option:not(.ant-select-item-option-disabled)").filter({ hasText: /^\s*10\s*\/\s*page\s*$/i }).first();
    const different = await tenPerPage.count() ? tenPerPage : sizeDropdown.locator(".ant-select-item-option:not(.ant-select-item-option-disabled)").filter({ hasNotText: new RegExp(`^\\s*${selectedText.replace(/[.*+?^${}()|[\\]\\\\]/g, "\\$&")}\\s*$`) }).first();
    await different.click(); await quiet(page);
    actions.push({ name: action, status: "EXECUTED_READ_ONLY", network_event_indexes: [sizeStart, network.length], side_effect: "none" });
  } catch (error) {
    actions.push({ name: action, status: "CURRENT_STATE_NOT_ACTIONABLE", network_event_indexes: [sizeStart, network.length], side_effect: "none", error: String(error).split("\n")[0] });
  }
  for (const [name, locator] of [
    ["member_list:pagination:page_2", page.locator(".ant-pagination-item").filter({ hasText: /^\s*2\s*$/ }).first()],
    ["member_list:pagination:next", page.locator(".ant-pagination-next:not(.ant-pagination-disabled)").first()],
  ]) {
    const start = network.length;
    try {
      await locator.waitFor({ state: "visible", timeout: 2500 });
      action = name; await locator.click(); await quiet(page);
      actions.push({ name, status: "EXECUTED_READ_ONLY", network_event_indexes: [start, network.length], side_effect: "none" });
      break;
    } catch (error) {
      if (name.endsWith("next")) actions.push({ name: "member_list:pagination:page_2", status: "CURRENT_STATE_NOT_ACTIONABLE", network_event_indexes: [start, network.length], side_effect: "none", error: String(error).split("\n")[0] });
    }
  }

  // Inline read-only entries only. Explicitly do not click write/terminal row controls.
  const rowActionResults = [];
  for (const rowAction of ["XP Growth Log", "View Details"]) {
    action = `member_list:row:${rowAction}`;
    const start = network.length;
    try {
      const row = page.locator(".ant-table-tbody tr:not(.ant-table-measure-row):visible").first();
      const control = row.getByRole("button", { name: rowAction, exact: true }).first();
      await control.waitFor({ state: "visible", timeout: 4000 });
      await control.click(); await quiet(page);
      rowActionResults.push({ action: rowAction, status: "OPENED_READ_ONLY", route_after: normalizePath(new URL(page.url()).pathname), network_event_indexes: [start, network.length] });
      const overlay = page.locator(".ant-modal:visible,.ant-drawer:visible,[role=dialog]:visible").last();
      if (await overlay.isVisible().catch(() => false)) await page.keyboard.press("Escape");
      if (new URL(page.url()).pathname !== "/member-center/list") {
        await page.goBack({ waitUntil: "domcontentloaded" }); await quiet(page);
      }
    } catch (error) {
      rowActionResults.push({ action: rowAction, status: "STRICT_LOCATOR_OR_CURRENT_STATE_ERROR", route_after: normalizePath(new URL(page.url()).pathname), network_event_indexes: [start, network.length], error: String(error).split("\n")[0] });
    }
  }
  for (const blocked of ["Transfer", "Risk Control", "Reset Password", "Convert to Agent", "Unblock"]) {
    rowActionResults.push({ action: blocked, status: "BLOCKED_DATA_SCOPE", reason: "No A-line dedicated write member; control intentionally not clicked" });
  }

  const result = {
    captured_at: new Date().toISOString(), environment: "FAT", lane: "A_member_list_readonly",
    page: "Member List", menu: "Member", route: "/member-center/list",
    dom_inventory: domInventory, select_inventories: selectInventories, batch_form: batchForm,
    actions, row_actions: rowActionResults, network,
    method_drift: { ui_actual: "POST /admin/member/list", documented: "GET /admin/member/list", classification: "MISCLASSIFIED" },
    permissions: "authenticated FAT main-admin session; actual button permissions inherited from /admin/me/detail",
    side_effects: [],
    safety: { writes_executed: 0, raw_uid_persisted: false, raw_phone_persisted: false, export_rows_persisted: false, storage_state_persisted_in_repository: false },
  };
  fs.writeFileSync(output, `${JSON.stringify(result, null, 2)}\n`);
  await context.close();
} finally {
  await browser.close();
}

console.log(JSON.stringify({ output, actions: actions.length, action_statuses: actions.reduce((acc, item) => ({ ...acc, [item.status]: (acc[item.status] || 0) + 1 }), {}), network_events: network.length, writes: 0, side_effects: 0 }));
