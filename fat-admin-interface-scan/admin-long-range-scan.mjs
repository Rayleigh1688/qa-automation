import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";
import { loadEnv, requiredEnv } from "../ui/framework/env.mjs";
import { decodeCbor } from "../ui/framework/cbor-decoder.mjs";

loadEnv(process.env.ENV_FILE || ".env.fat");
const baseUrl = requiredEnv("ADMIN_URL");
const origin = new URL(baseUrl).origin;
const outDir = path.resolve("fat-admin-interface-scan/results");
const init = JSON.parse(fs.readFileSync(path.join(outDir, "fat-admin-page-initialization.json"), "utf8"));
const runLabel = sanitizeRunLabel(process.env.ADMIN_LONG_RANGE_RUN_LABEL || "admin");
const output = path.join(outDir, `long-range-${runLabel}-results.json`);
const progress = path.join(outDir, `long-range-${runLabel}-progress.json`);

function sanitizeRunLabel(value) { return String(value).replace(/[^a-z0-9_-]/gi, "-"); }

const excludedRoutes = new Set(["/home", "/operations/client-config", "/operations/ops-tools"]);
const priorityRoutes = new Set([
  "/kyc", "/logs/list", "/member-center/list", "/member-management/vip-rewards",
  "/member-management/inviter-transfer-records", "/agency-management/agency-statistical",
  "/report-management/game-reports/list", "/report-management/game-types-report/list",
  "/report-management/game-platform-report/list", "/report-management/member-daily-stats",
  "/report-management/member-daily-game-stats", "/payment/recharge-orders/list",
  "/payment/withdraw-orders/list", "/payment/betting-slip/list", "/payment/transaction-orders",
  "/payment/recharge-card-orders/list", "/operations/daily-reports",
  "/operations/activity-expenditure-audit", "/risk-control/dw-audit",
  "/risk-control/up-down-score", "/risk-control/temporary-restriction-list", "/risk-control/risk-logs",
  "/promo-marketing/statistical-reports", "/promo-marketing/first-deposit-daily-active",
  "/game/bet-orders", "/gamev2/freespin-import-logs", "/system/sms-otp", "/system/order-monitor",
]);
const requestedRoutes = new Set((process.env.ADMIN_LONG_RANGE_ROUTES || "").split(",").map((value) => value.trim()).filter(Boolean));
const candidates = init.pages.filter((item) => {
  if (excludedRoutes.has(item.route)) return false;
  if (!priorityRoutes.has(item.route)) return false;
  if (requestedRoutes.size && !requestedRoutes.has(item.route)) return false;
  const placeholders = item.controls?.inputs?.map((input) => input.placeholder || "") || [];
  const hasStart = placeholders.some((value) => /start\s*(date|time)/i.test(value));
  const hasEnd = placeholders.some((value) => /end\s*(date|time)/i.test(value));
  const hasQuery = item.controls?.buttons?.some((button) => /^(query|search|查\s*询|搜索)$/i.test((button.text || "").trim()));
  return hasStart && hasEnd && hasQuery;
});

const sanitize = (value) => String(value ?? "")
  .replace(/\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi, "<redacted-email>")
  .replace(/(?<!\d)(?:\+?63|0)9\d{9}(?!\d)/g, "<redacted-phone>")
  .replace(/(?<!\d)\d{9,}(?!\d)/g, "<redacted-member-id>").trim();
const normalizePath = (value) => value.replace(/\/[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}(?=\/|$)/g, "/{uuid}").replace(/\/\d{6,}(?=\/|$)/g, "/{id}");
const formatDate = (date) => {
  const parts = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Manila", year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(date);
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${values.year}-${values.month}-${values.day}`;
};
const endDate = formatDate(new Date());
const ranges = [7, 30, 90, 365].map((days) => {
  const date = new Date(); date.setUTCDate(date.getUTCDate() - days);
  return { label: `${days}d`, start: formatDate(date), end: endDate, days };
});
ranges.push({ label: "page_max_observed", start: "2020-01-01", end: endDate, days: null });

const browser = await chromium.launch({ headless: process.env.ADMIN_SCAN_HEADED === "false" });
const context = await browser.newContext({ ignoreHTTPSErrors: true, viewport: { width: 1440, height: 1000 }, locale: "en-US" });
const page = await context.newPage();
const pages = [];
let currentAttempt = null;

function dataSummary(data) {
  if (Array.isArray(data)) return { type: "list", count: data.length, non_empty: data.length > 0, keys: [] };
  if (data === null) return { type: "null", count: 0, non_empty: false, keys: [] };
  if (!data || typeof data !== "object") return { type: typeof data, count: null, non_empty: Boolean(data), keys: [] };
  const keys = Object.keys(data).sort();
  for (const key of ["d", "list", "records", "items", "rows", "content", "result"]) {
    if (Array.isArray(data[key])) return { type: "object", count: data[key].length, non_empty: data[key].length > 0, keys };
    if (data[key] && typeof data[key] === "object") {
      const nested = dataSummary(data[key]);
      if (nested.count !== null || nested.non_empty) return { type: "object", count: nested.count, non_empty: nested.non_empty, keys };
    }
  }
  for (const key of ["t", "total", "count", "total_count"]) {
    if (typeof data[key] === "number") return { type: "object", count: data[key], non_empty: data[key] > 0, keys };
  }
  return { type: "object", count: null, non_empty: false, keys };
}

function timeUnit(value) {
  if (typeof value === "number") return value >= 1e12 ? "epoch_milliseconds" : value >= 1e9 ? "epoch_seconds" : "numeric_unknown";
  if (typeof value === "string" && /^\d+$/.test(value)) {
    const number = Number(value);
    return number >= 1e12 ? "epoch_milliseconds_string" : number >= 1e9 ? "epoch_seconds_string" : "numeric_string_unknown";
  }
  if (typeof value === "string" && /^\d{4}-\d{2}-\d{2}/.test(value)) return "date_or_datetime_string";
  return typeof value;
}

page.on("response", async (response) => {
  if (!currentAttempt) return;
  const request = response.request();
  if (!["xhr", "fetch"].includes(request.resourceType())) return;
  let url; try { url = new URL(response.url()); } catch { return; }
  if (url.origin !== origin) return;
  let requestFields = [], timeFields = {}, pageSizeFields = {}, requestBodyBytes = 0, requestBodyDecoded = false;
  let requestPayloadFormat = (request.headers()["content-type"] || "unspecified").split(";")[0];
  try {
    const raw = request.postDataBuffer();
    if (raw?.length) {
      requestBodyBytes = raw.length;
      const type = (request.headers()["content-type"] || "").toLowerCase();
      const body = type.includes("json") ? JSON.parse(raw.toString("utf8")) : decodeCbor(new Uint8Array(raw));
      if (body && typeof body === "object" && !Array.isArray(body)) {
        requestBodyDecoded = true;
        requestFields = Object.keys(body).sort();
        for (const [key, value] of Object.entries(body)) {
          if (/start|end|date|time/i.test(key) && ["string", "number"].includes(typeof value)) timeFields[key] = { value, unit: timeUnit(value) };
          if (/page|size|limit/i.test(key) && ["string", "number"].includes(typeof value)) pageSizeFields[key] = value;
        }
      }
    }
  } catch {}
  for (const [key, value] of url.searchParams.entries()) {
    if (/start|end|date|time/i.test(key)) timeFields[key] = { value, unit: timeUnit(value) };
    if (/page|size|limit/i.test(key)) pageSizeFields[key] = value;
  }
  let businessStatus = null, summary = { type: "unknown", count: null, non_empty: false, keys: [] };
  try { const decoded = decodeCbor(new Uint8Array(await response.body())); businessStatus = decoded?.status ?? null; summary = dataSummary(decoded?.data); } catch {}
  currentAttempt.events.push({
    method: request.method(), path: normalizePath(url.pathname), query_fields: [...url.searchParams.keys()].sort(), body_fields: requestFields,
    request_payload_format: requestPayloadFormat, request_body_bytes: requestBodyBytes, request_body_decoded: requestBodyDecoded,
    time_fields: timeFields, page_size_fields: pageSizeFields, http_status: response.status(), business_status: businessStatus,
    response_type: summary.type, response_keys: summary.keys, record_count: summary.count, non_empty: summary.non_empty,
  });
});

async function login() {
  currentAttempt = null;
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

async function quiet() {
  let last = currentAttempt?.events.length || 0, stable = Date.now();
  for (let index = 0; index < 50; index += 1) {
    await page.waitForTimeout(100);
    const size = currentAttempt?.events.length || 0;
    if (size !== last) { last = size; stable = Date.now(); }
    else if (Date.now() - stable >= 700) return;
  }
}

function checkpoint() {
  const now = new Date().toISOString();
  fs.writeFileSync(output, JSON.stringify({ captured_at: now, environment: "FAT", timezone: "Asia/Manila", candidates: candidates.length, pages }, null, 2) + "\n");
  fs.writeFileSync(progress, JSON.stringify({ updated_at: now, completed_pages: pages.length, total_pages: candidates.length, attempts: pages.reduce((sum, item) => sum + item.attempts.length, 0), pages_with_data: pages.filter((item) => item.result === "NON_EMPTY").length, page_errors: pages.filter((item) => item.result === "ERROR").length }, null, 2) + "\n");
}

await login();
for (let pageIndex = 0; pageIndex < candidates.length; pageIndex += 1) {
  const item = candidates[pageIndex];
  const pageResult = { order: pageIndex + 1, top_menu: item.top_menu, page_name: item.page_name, route: item.route, attempts: [], result: "EMPTY_TO_MAX_RANGE", stop_range: "", error: "" };
  try {
    currentAttempt = { events: [] };
    await page.goto(new URL(item.route, baseUrl).toString(), { waitUntil: "domcontentloaded", timeout: 20_000 });
    await quiet();
    const placeholders = item.controls.inputs.map((input) => input.placeholder || "");
    const startPlaceholder = placeholders.find((value) => /start\s*(date|time)/i.test(value));
    const endPlaceholder = placeholders.find((value) => /end\s*(date|time)/i.test(value));
    const queryAction = item.controls.buttons.map((button) => (button.text || "").trim())
      .find((value) => /^(query|search|查\s*询|搜索)$/i.test(value));
    const startInput = page.getByPlaceholder(startPlaceholder, { exact: true }).first();
    const endInput = page.getByPlaceholder(endPlaceholder, { exact: true }).first();
    let button = page.getByRole("button", { name: queryAction, exact: true }).first();
    await startInput.waitFor({ state: "visible", timeout: 12_000 });
    await endInput.waitFor({ state: "visible", timeout: 12_000 });
    try { await button.waitFor({ state: "visible", timeout: 3_000 }); }
    catch {
      button = page.locator("button").filter({ hasText: /^\s*(?:Query|Search|查\s*询|搜索)\s*$/i }).first();
      await button.waitFor({ state: "visible", timeout: 9_000 });
      pageResult.query_selector_fallback = "button exact visible text";
    }
    pageResult.date_control = { start_placeholder: startPlaceholder, end_placeholder: endPlaceholder,
      initial_values: { start: await startInput.inputValue(), end: await endInput.inputValue() } };
    for (const range of ranges) {
      if (!await startInput.isVisible().catch(() => false) || !await endInput.isVisible().catch(() => false)) {
        pageResult.result = "DATE_CONTROL_NOT_ACTIONABLE"; break;
      }
      const startHasTime = pageResult.date_control.initial_values.start.includes(":") || /time/i.test(startPlaceholder);
      const endHasTime = pageResult.date_control.initial_values.end.includes(":") || /time/i.test(endPlaceholder);
      const startValue = startHasTime ? `${range.start} 00:00:00` : range.start;
      const endValue = endHasTime ? `${range.end} 23:59:59` : range.end;
      await startInput.click(); await startInput.press("ControlOrMeta+A"); await startInput.press("Backspace"); await startInput.type(startValue, { delay: 10 });
      await startInput.press("Tab").catch(() => {});
      await endInput.click(); await endInput.press("ControlOrMeta+A"); await endInput.press("Backspace"); await endInput.type(endValue, { delay: 10 });
      await endInput.press("Tab").catch(() => {}); await endInput.press("Escape").catch(() => {});
      try { await button.waitFor({ state: "visible", timeout: 5_000 }); }
      catch { pageResult.result = "QUERY_SELECTOR_NOT_FOUND"; break; }
      const acceptedInputs = { start: await startInput.inputValue(), end: await endInput.inputValue() };
      if (!acceptedInputs.start.startsWith(range.start) || !acceptedInputs.end.startsWith(range.end)
          || acceptedInputs.start.indexOf(range.start) !== acceptedInputs.start.lastIndexOf(range.start)) {
        pageResult.result = "UI_DATE_INPUT_BLOCKED";
        pageResult.stop_range = range.label;
        pageResult.attempts.push({ range: range.label, start: range.start, end: range.end, accepted_inputs: acceptedInputs,
          timezone: "Asia/Manila", events: [], non_empty: false, failed: false, validation: "REJECTED_MISMATCH" });
        break;
      }
      await page.waitForTimeout(700);
      currentAttempt = { events: [] };
      await button.click({ timeout: 3_000 });
      await quiet();
      const events = currentAttempt.events;
      const relevant = events.filter((event) => event.path !== "/admin/me/detail" && event.path !== "/admin/notify/audit/alarm" && event.path !== "/admin/game/search");
      const inspected = relevant;
      if (!inspected.length) {
        pageResult.attempts.push({ range: range.label, start: range.start, end: range.end, accepted_inputs: acceptedInputs,
          timezone: "Asia/Manila", events, non_empty: false, failed: false, validation: "NO_BUSINESS_QUERY_REQUEST" });
        pageResult.result = "NO_QUERY_REQUEST"; pageResult.stop_range = range.label; break;
      }
      const hasFailure = inspected.some((event) => event.http_status < 200 || event.http_status >= 300 || event.business_status === false);
      const hasData = inspected.some((event) => event.business_status !== false && event.non_empty);
      pageResult.attempts.push({ range: range.label, start: range.start, end: range.end, accepted_inputs: acceptedInputs, timezone: "Asia/Manila", events, non_empty: hasData, failed: hasFailure });
      if (hasFailure) { pageResult.result = "ACTIVE_FAILED"; pageResult.stop_range = range.label; break; }
      if (hasData) { pageResult.result = "NON_EMPTY"; pageResult.stop_range = range.label; break; }
    }
  } catch (error) { pageResult.result = "ERROR"; pageResult.error = sanitize(error); }
  pages.push(pageResult); checkpoint();
  console.log(`[${pageIndex + 1}/${candidates.length}] ${item.page_name} result=${pageResult.result} range=${pageResult.stop_range || "max"} attempts=${pageResult.attempts.length}`);
}
currentAttempt = null; checkpoint(); await browser.close();
console.log(`[summary] pages=${pages.length}/${candidates.length} non_empty=${pages.filter((item) => item.result === "NON_EMPTY").length} errors=${pages.filter((item) => item.result === "ERROR").length}`);
