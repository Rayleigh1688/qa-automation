import fs from "node:fs";
import path from "node:path";
import { chromium, devices } from "playwright";
import { ClientAppPage } from "../ui/elements/client-app.page.mjs";
import { loadEnv, requiredEnv } from "../ui/framework/env.mjs";
import { loadJson } from "../ui/framework/data-loader.mjs";
import { decodeCbor } from "../ui/framework/cbor-decoder.mjs";

loadEnv(process.env.ENV_FILE || ".env.fat");

const BASE_URL = process.env.CLIENT_BASE_URL || process.env.API_URL || "https://client-fat.filbet2025.com";
const OUTPUT_DIR = path.resolve("fat-client-interface-scan/results");
const RAW_OUT = path.join(OUTPUT_DIR, "long-range-network.json");
const PROGRESS_OUT = path.join(OUTPUT_DIR, "long-range-progress.json");
const TIMEZONE = "Asia/Manila";
const PAGE_SIZE_EXPECTATION = 10;
const RANGE_CANDIDATES = [
  { id: "7d", days: 7, match: /(?:last\s*)?7\s*days?|week/i },
  { id: "30d", days: 30, match: /(?:last\s*)?30\s*days?|1\s*month/i },
  { id: "90d", days: 90, match: /(?:last\s*)?90\s*days?|3\s*months?/i },
  { id: "365d", days: 365, match: /(?:last\s*)?365\s*days?|1\s*year/i },
  { id: "max", days: null, match: /all\s*time|maximum|max\s*range/i },
];
const TARGETS = [
  { page: "Transaction / Deposit", route: "/transaction-record/transaction/deposit", endpoint: "/finance/deposit/list", method: "GET" },
  { page: "Transaction / Withdraw", route: "/transaction-record/transaction/withdraw", endpoint: "/finance/withdraw/list", method: "GET" },
  { page: "Bet History", route: "/bet-record", endpoint: "/member/game/bet/list", method: "GET" },
  { page: "Bonus", route: "/transaction-record/bonus", endpoint: "/promo/blindbox/transaction/bonus", method: "GET" },
];

fs.mkdirSync(OUTPUT_DIR, { recursive: true });

function safeText(value, limit = 200) {
  return String(value || "")
    .replace(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi, "<redacted-email>")
    .replace(/(?:\+?63|0)?9\d{9}/g, "<redacted-phone>")
    .replace(/[₱$]\s*[\d,]+(?:\.\d{1,2})?/g, "<redacted-amount>")
    .replace(/\b\d{6,}\b/g, "<redacted-number>")
    .replace(/\s+/g, " ").trim().slice(0, limit);
}

function decode(buffer) {
  if (!buffer?.length) return null;
  try { return decodeCbor(buffer); } catch {}
  try { return JSON.parse(buffer.toString("utf8")); } catch {}
  return null;
}

function describeResponse(decoded) {
  const data = decoded?.data;
  const keys = data && typeof data === "object" && !Array.isArray(data) ? Object.keys(data).sort() : [];
  const arrays = [];
  const visit = (value, at, depth = 0) => {
    if (depth > 3 || value == null) return;
    if (Array.isArray(value)) { arrays.push({ path: at, count: value.length }); return; }
    if (typeof value === "object") for (const [key, child] of Object.entries(value)) visit(child, at ? `${at}.${key}` : key, depth + 1);
  };
  visit(data, "data");
  const recordCount = Math.max(0, ...arrays.map((item) => item.count));
  const totalCandidates = [data?.t, data?.total, data?.count, decoded?.total].filter((value) => Number.isFinite(Number(value))).map(Number);
  return {
    businessStatus: typeof decoded?.status === "boolean" ? decoded.status : null,
    responseStructure: { topLevelKeys: decoded && typeof decoded === "object" ? Object.keys(decoded).sort() : [], dataType: Array.isArray(data) ? "array" : data === null ? "null" : typeof data, dataKeys: keys, arrayPaths: arrays.map((item) => item.path) },
    recordCount,
    totalCount: totalCandidates.length ? Math.max(...totalCandidates) : null,
    nonEmpty: recordCount > 0,
  };
}

async function login(page, app) {
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(900);
  await app.handleModals({ timeout: 3000 });
  const login = page.getByRole("button", { name: /Register \/ Login|^Login$/i }).first();
  await login.click();
  await app.waitForLoginForm();
  await page.getByRole("button", { name: /^Password$/i }).first().click().catch(() => {});
  await app.fillPhone(requiredEnv("CLIENT_PHONE"));
  await page.locator('input[type="password"]:visible').first().fill(requiredEnv("CLIENT_PASSWORD"));
  await app.acceptLoginTerms();
  await app.submitLogin();
  if (await app.acceptLoginConfirmation()) {
    await app.acceptLoginTerms();
    await app.submitLogin();
  }
  await app.waitForLoggedIn(15_000);
}

async function openDateMenu(page) {
  const buttons = page.locator("button:visible");
  const count = await buttons.count();
  for (let index = 0; index < count; index += 1) {
    const button = buttons.nth(index);
    const name = safeText(await button.innerText().catch(() => ""));
    if (!/today|days?|week|month|year|all\s*time/i.test(name)) continue;
    await button.click();
    await page.waitForTimeout(350);
    return name;
  }
  throw new Error("date range control not found");
}

async function dateOptions(page) {
  const candidates = await page.locator('button:visible, [role="option"]:visible, [role="menuitem"]:visible, li:visible').evaluateAll((nodes) =>
    nodes.map((node) => ({ text: node.innerText || node.getAttribute("aria-label") || "", disabled: Boolean(node.disabled || node.getAttribute("aria-disabled") === "true") })),
  );
  const unique = new Map();
  for (const item of candidates) {
    const text = safeText(item.text);
    if (!text || !/today|days?|week|month|year|all\s*time|maximum|max\s*range/i.test(text)) continue;
    if (!unique.has(text)) unique.set(text, { text, disabled: item.disabled });
  }
  return [...unique.values()];
}

async function chooseOption(page, optionText) {
  const matcher = new RegExp(`^${optionText.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}$`, "i");
  const candidates = [page.getByRole("option", { name: matcher }).first(), page.getByRole("button", { name: matcher }).first(), page.getByRole("menuitem", { name: matcher }).first(), page.getByText(matcher, { exact: true }).last()];
  for (const candidate of candidates) {
    if (!(await candidate.isVisible({ timeout: 500 }).catch(() => false))) continue;
    await candidate.click({ timeout: 2500 });
    return true;
  }
  return false;
}

async function waitForEndpoint(page, target, action, timeout = 7000) {
  const response = await page.waitForResponse((candidate) => {
    try {
      const url = new URL(candidate.url());
      return candidate.request().method() === target.method && url.pathname === target.endpoint;
    } catch { return false; }
  }, { timeout });
  const url = new URL(response.url());
  const query = {};
  for (const key of ["time_flag", "page", "page_size", "start_time", "end_time"]) {
    if (url.searchParams.has(key)) query[key] = url.searchParams.get(key);
  }
  const decoded = await response.body().then(decode).catch(() => null);
  return {
    page: target.page, pageRoute: target.route, action,
    method: target.method, normalizedPath: target.endpoint,
    timeParameters: query, timeUnit: "time_flag interpreted from selected UI day-range label",
    timezone: TIMEZONE, httpStatus: response.status(), ...describeResponse(decoded),
    classification: response.status() >= 400 || decoded?.status === false ? "ACTIVE_FAILED" : "ACTIVE",
    auth: "authenticated client session (t header); values not stored",
    sideEffect: "none; historical list query", ts: new Date().toISOString(),
  };
}

async function samplePageTwo(page, target, prior) {
  if (!prior.nonEmpty) return { attempted: false, reason: "first page is empty" };
  if (prior.totalCount != null && prior.totalCount <= PAGE_SIZE_EXPECTATION) return { attempted: false, reason: "no second page required: total does not exceed page size" };
  const responsePromise = page.waitForResponse((candidate) => {
    try {
      const url = new URL(candidate.url());
      return url.pathname === target.endpoint && url.searchParams.get("page") === "2";
    } catch { return false; }
  }, { timeout: 5000 }).catch(() => null);
  let interaction = "";
  const pageTwo = page.getByRole("button", { name: /^2$/ }).first();
  const pageTwoLink = page.getByRole("link", { name: /^2$/ }).first();
  const next = page.locator('button[aria-label*="next" i]:visible, a[aria-label*="next" i]:visible, button[title*="next" i]:visible').first();
  if (await pageTwo.isVisible({ timeout: 500 }).catch(() => false)) {
    await pageTwo.click(); interaction = "page 2 button";
  } else if (await pageTwoLink.isVisible({ timeout: 500 }).catch(() => false)) {
    await pageTwoLink.click(); interaction = "page 2 link";
  } else if (await next.isVisible({ timeout: 500 }).catch(() => false)) {
    await next.click(); interaction = "Next control";
  } else {
    const scrolled = await page.evaluate(() => {
      const candidates = [document.scrollingElement, ...document.querySelectorAll("div,main,section")].filter(Boolean);
      const target = candidates.find((node) => {
        const style = getComputedStyle(node);
        return node.scrollHeight > node.clientHeight + 20 && /auto|scroll/.test(style.overflowY);
      });
      if (!target) return false;
      target.scrollTop = target.scrollHeight;
      return true;
    });
    if (scrolled) {
      interaction = "scroll internal list container";
    } else {
      for (let pass = 0; pass < 8; pass += 1) {
        await page.mouse.wheel(0, 900);
        await page.waitForTimeout(180);
      }
      interaction = "progressive viewport wheel scroll";
    }
  }
  const response = await responsePromise;
  if (!response) return { attempted: true, captured: false, method: interaction, reason: "no page=2 request emitted" };
  const url = new URL(response.url());
  const decoded = await response.body().then(decode).catch(() => null);
  return { attempted: true, captured: true, method: interaction, page: url.searchParams.get("page"), pageSize: url.searchParams.get("page_size"), httpStatus: response.status(), ...describeResponse(decoded) };
}

const browser = await chromium.launch({ headless: process.env.HEADED !== "true", channel: process.env.PLAYWRIGHT_CHANNEL || undefined });
const context = await browser.newContext({ ...devices["Pixel 7"], viewport: { width: 412, height: 915 }, baseURL: BASE_URL, ignoreHTTPSErrors: true, locale: "en-US", timezoneId: TIMEZONE });
const page = await context.newPage();
page.setDefaultTimeout(4000);
page.setDefaultNavigationTimeout(8000);
const app = new ClientAppPage(page, { pageConfig: loadJson("ui/data/client-pages.json"), modalConfig: loadJson("ui/data/client-modals.json") });
const results = [];
const progress = [];

try {
  await login(page, app);
  for (const target of TARGETS) {
    const targetProgress = { page: target.page, route: target.route, endpoint: target.endpoint, status: "RUNNING", availableRangeOptions: [], attempts: [], selectedResult: null, paginationSample: null, error: "" };
    progress.push(targetProgress);
    try {
      const initialPromise = waitForEndpoint(page, target, "page initialization");
      await page.goto(target.route, { waitUntil: "domcontentloaded" });
      const initial = await initialPromise;
      results.push(initial);
      await page.waitForTimeout(600);

      await openDateMenu(page);
      const options = await dateOptions(page);
      targetProgress.availableRangeOptions = options;

      for (const candidate of RANGE_CANDIDATES) {
        const option = options.find((item) => candidate.match.test(item.text) && !item.disabled);
        if (!option) {
          targetProgress.attempts.push({ range: candidate.id, status: "UNSUPPORTED_UI_RANGE" });
          continue;
        }
        const responsePromise = waitForEndpoint(page, target, `select ${option.text}`);
        const clicked = await chooseOption(page, option.text);
        if (!clicked) {
          targetProgress.attempts.push({ range: candidate.id, option: option.text, status: "CONTROL_NOT_CLICKED" });
          continue;
        }
        const record = await responsePromise;
        record.requestedRange = candidate.id;
        record.selectedUiLabel = option.text;
        results.push(record);
        targetProgress.attempts.push({ range: candidate.id, option: option.text, status: "CAPTURED", nonEmpty: record.nonEmpty, recordCount: record.recordCount, totalCount: record.totalCount, timeParameters: record.timeParameters });
        if (record.nonEmpty) {
          targetProgress.selectedResult = { range: candidate.id, option: option.text, recordCount: record.recordCount, totalCount: record.totalCount, timeParameters: record.timeParameters };
          targetProgress.paginationSample = await samplePageTwo(page, target, record);
          break;
        }
        await openDateMenu(page);
      }
      targetProgress.status = targetProgress.selectedResult ? "NON_EMPTY_FOUND" : "NO_NON_EMPTY_SUPPORTED_RANGE";
    } catch (error) {
      targetProgress.status = "FAILED";
      targetProgress.error = safeText(error?.message || error, 400);
    }
    fs.writeFileSync(RAW_OUT, JSON.stringify({ scannedAt: new Date().toISOString(), environment: "FAT", timezone: TIMEZONE, records: results }, null, 2));
    fs.writeFileSync(PROGRESS_OUT, JSON.stringify({ scannedAt: new Date().toISOString(), environment: "FAT", timezone: TIMEZONE, pages: progress }, null, 2));
  }
} finally {
  fs.writeFileSync(RAW_OUT, JSON.stringify({ scannedAt: new Date().toISOString(), environment: "FAT", timezone: TIMEZONE, records: results }, null, 2));
  fs.writeFileSync(PROGRESS_OUT, JSON.stringify({ scannedAt: new Date().toISOString(), environment: "FAT", timezone: TIMEZONE, pages: progress }, null, 2));
  await context.close().catch(() => {});
  await browser.close().catch(() => {});
}

console.log(JSON.stringify({ pages: progress.length, nonEmptyFound: progress.filter((item) => item.status === "NON_EMPTY_FOUND").length, failed: progress.filter((item) => item.status === "FAILED").length, records: results.length }));
