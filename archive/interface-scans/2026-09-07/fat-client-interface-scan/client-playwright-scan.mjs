import fs from "node:fs";
import path from "node:path";
import { chromium, devices } from "playwright";
import { ClientAppPage } from "../ui/elements/client-app.page.mjs";
import { loadEnv, requiredEnv } from "../ui/framework/env.mjs";
import { decodeCbor } from "../ui/framework/cbor-decoder.mjs";
import { loadJson } from "../ui/framework/data-loader.mjs";

loadEnv(process.env.ENV_FILE || ".env.fat");

const OUTPUT_DIR = path.resolve("fat-client-interface-scan/results");
const NETWORK_OUT = path.join(OUTPUT_DIR, "fat-client-network.json");
const PROGRESS_OUT = path.join(OUTPUT_DIR, "fat-client-page-progress.json");
const CLIENT_DEVICE = devices["Pixel 7"];
const BASE_URL = process.env.CLIENT_BASE_URL || process.env.API_URL || "https://client-fat.filbet2025.com";
const BASE_HOST = new URL(BASE_URL).hostname;
const ASSET_RE = /\.(?:js|css|png|jpe?g|webp|gif|svg|ico|woff2?|ttf|map)(?:$|\?)/i;
const SECRET_FIELD_RE = /^(?:t|token|authorization|cookie|password|pwd|otp|code|phone|mobile|uid|player_?id|session(?:_id)?|device(?:_id)?)$/i;

fs.mkdirSync(OUTPUT_DIR, { recursive: true });

function safeText(value, limit = 160) {
  return String(value || "")
    .replace(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi, "<redacted-email>")
    .replace(/(?:\+?63|0)?9\d{9}/g, "<redacted-phone>")
    .replace(/[₱$]\s*[\d,]+(?:\.\d{1,2})?/g, "<redacted-amount>")
    .replace(/\b\d{6,}\b/g, "<redacted-number>")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, limit);
}

function decodePayload(buffer) {
  if (!buffer?.length) return null;
  try { return decodeCbor(buffer); } catch {}
  try { return JSON.parse(buffer.toString("utf8")); } catch {}
  try {
    const params = new URLSearchParams(buffer.toString("utf8"));
    if ([...params.keys()].length) return Object.fromEntries([...params.keys()].map((key) => [key, null]));
  } catch {}
  return null;
}

function valueShape(value, depth = 0) {
  if (depth > 2) return typeof value;
  if (Array.isArray(value)) return { type: "array", item: value.length ? valueShape(value[0], depth + 1) : "unknown" };
  if (value && typeof value === "object") {
    return {
      type: "object",
      fields: Object.keys(value).filter((key) => !SECRET_FIELD_RE.test(key)).sort().slice(0, 60),
    };
  }
  return value === null ? "null" : typeof value;
}

function businessStatus(value) {
  if (!value || typeof value !== "object") return "UNAVAILABLE";
  if (typeof value.status === "boolean") return String(value.status);
  if (typeof value.success === "boolean") return String(value.success);
  if (typeof value.code === "number" || typeof value.code === "string") return `code:${safeText(value.code, 40)}`;
  return "UNAVAILABLE";
}

function normalizedPath(rawPath) {
  return String(rawPath || "/")
    .replace(/[0-9a-f]{8}-[0-9a-f-]{27,}/gi, "{uuid}")
    .replace(/\/\d{6,}(?=\/|$)/g, "/{id}");
}

function requestFieldNames(request) {
  const decoded = decodePayload(request.postDataBuffer());
  if (decoded && typeof decoded === "object" && !Array.isArray(decoded)) return Object.keys(decoded).sort();
  return [];
}

function parameterSources(queryFields, bodyFields, authRequired) {
  const sources = [];
  if (queryFields.length) sources.push(`query:${queryFields.join("|")}<-page/filter/pagination/default`);
  if (bodyFields.length) sources.push(`body:${bodyFields.join("|")}<-form/current-record/default`);
  if (authRequired) sources.push("header:t<-authenticated-session");
  return sources;
}

function isThirdParty(hostname) {
  return hostname !== BASE_HOST && !hostname.endsWith(".filbet2025.com");
}

function endpointClassification(record) {
  if (record.thirdParty) return "THIRD_PARTY";
  if (record.httpStatus >= 400 || record.businessStatus === "false") return "ACTIVE_FAILED";
  return "ACTIVE";
}

async function settle(page, ms = 900) {
  await page.waitForLoadState("domcontentloaded", { timeout: 5000 }).catch(() => {});
  await page.waitForTimeout(ms);
}

function assertRoute(page, target) {
  const actual = new URL(page.url());
  const expected = new URL(target, BASE_URL);
  if (actual.pathname !== expected.pathname) {
    throw new Error(`route mismatch: expected ${expected.pathname}, got ${actual.pathname}`);
  }
  for (const [key, value] of expected.searchParams) {
    if (actual.searchParams.get(key) !== value) throw new Error(`route query mismatch: expected ${key}=${value}`);
  }
}

async function controls(page) {
  return page.locator("button:visible, a:visible, input:visible, [role=button]:visible, [role=tab]:visible").evaluateAll((nodes) =>
    nodes.slice(0, 140).map((node) => ({
      tag: node.tagName.toLowerCase(),
      type: node.getAttribute("type") || node.getAttribute("role") || "",
      name: node.getAttribute("aria-label") || node.getAttribute("placeholder") || node.innerText || "",
      href: node instanceof HTMLAnchorElement ? node.getAttribute("href") || "" : "",
      disabled: Boolean(node.disabled || node.getAttribute("aria-disabled") === "true"),
    })),
  ).then((items) => items.map((item) => ({ ...item, name: safeText(item.name), href: safeText(item.href, 240) }))).catch(() => []);
}

async function clickText(page, labels, { exact = false } = {}) {
  for (const label of labels) {
    const matcher = label instanceof RegExp ? label : new RegExp(exact ? `^${String(label).replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}$` : String(label).replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "i");
    const candidates = [page.getByRole("button", { name: matcher }).first(), page.getByRole("link", { name: matcher }).first(), page.getByRole("tab", { name: matcher }).first(), page.getByText(matcher, { exact }).first()];
    for (const candidate of candidates) {
      if (!(await candidate.isVisible({ timeout: 700 }).catch(() => false))) continue;
      await candidate.click({ timeout: 2500 }).catch(async () => candidate.evaluate((el) => el.click()));
      return safeText(label instanceof RegExp ? label.source : label);
    }
  }
  return "";
}

async function requiredClick(page, labels, options = {}) {
  const clicked = await clickText(page, labels, options);
  if (!clicked) throw new Error(`control not found: ${labels.map(String).join(" | ")}`);
  return clicked;
}

async function loginWithPassword(page, app) {
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await settle(page);
  await requiredClick(page, ["Register / Login", "Login"]);
  await app.waitForLoginForm();
  await clickText(page, ["Password"]);
  await app.fillPhone(requiredEnv("CLIENT_PHONE"));
  const passwordInput = page.locator('input[type="password"]:visible').first();
  await passwordInput.waitFor({ state: "visible", timeout: 8000 });
  await passwordInput.fill(requiredEnv("CLIENT_PASSWORD"));
  await app.acceptLoginTerms();
  await app.submitLogin();
  if (await app.acceptLoginConfirmation()) {
    await app.acceptLoginTerms();
    await app.submitLogin().catch(() => {});
  }
  await app.waitForLoggedIn(15_000);
  return "Login";
}

async function requestLoginCode(page, app) {
  await app.fillPhone(requiredEnv("CLIENT_PHONE"));
  const button = page.getByRole("button", { name: /^Get Code$/i }).first();
  if (!(await button.isVisible({ timeout: 2000 }).catch(() => false))) throw new Error("Get Code control not found");
  await button.click({ force: true });
  return "Get Code";
}

const pages = [
  { id: "home_guest", menu: "Home", page: "Home (guest)", route: "/", auth: false },
  { id: "sidebar_guest", menu: "Sidebar", page: "Sidebar (guest)", route: "/", auth: false, action: async (page) => requiredClick(page, ["Menu"]) },
  { id: "login", menu: "Authentication", page: "Login", route: "/", auth: false, action: async (page) => requiredClick(page, ["Register / Login", "Login"]) },
  { id: "register", menu: "Authentication", page: "Register", route: "/", auth: false, action: async (page) => { await requiredClick(page, ["Register / Login", "Login"]); await settle(page, 300); return requiredClick(page, ["Register here", "Register"]); } },
  { id: "home", menu: "Home", page: "Home", route: "/", auth: true },
  { id: "sidebar", menu: "Sidebar", page: "Sidebar", route: "/", auth: true, action: async (page) => requiredClick(page, ["Menu"]) },
  { id: "my", menu: "My", page: "My", route: "/my", auth: true },
  { id: "rewards", menu: "Rewards", page: "Rewards", route: "/welfare", auth: true },
  { id: "free_spins", menu: "Rewards", page: "My Free Spins", route: "/welfare", auth: true, action: async (page) => requiredClick(page, ["My Free Spin", "Free Spin"]) },
  { id: "earn_filcoins", menu: "Filcoins", page: "Earn Filcoins", route: "/s-points-v2", auth: true },
  { id: "filcoins_mall", menu: "Filcoins", page: "Filcoins Mall", route: "/s-points-v2", auth: true, action: async (page) => requiredClick(page, ["Filcoins Mall", "Mall"]) },
  { id: "game", menu: "Game", page: "Game", route: "/s-game-category-v2/gameType/3", auth: true },
  { id: "vip", menu: "VIP", page: "VIP Center", route: "/my", auth: true, action: async (page) => requiredClick(page, ["VIP Center"], { exact: true }) },
  { id: "deposit", menu: "My", page: "Deposit", route: "/my?action=deposit", auth: true },
  { id: "withdraw", menu: "My", page: "Withdraw", route: "/my?action=withdraw", auth: true },
  { id: "transaction", menu: "My", page: "Transaction", route: "/my", auth: true, action: async (page) => requiredClick(page, ["Transaction"]) },
  { id: "bet_history", menu: "My", page: "Bet History", route: "/my", auth: true, action: async (page) => requiredClick(page, ["Bet History"]) },
  { id: "bonus", menu: "My", page: "Bonus", route: "/my", auth: true, action: async (page) => requiredClick(page, ["Bonus"]) },
  { id: "account", menu: "My", page: "Account", route: "/my", auth: true, action: async (page) => requiredClick(page, ["Account"]) },
];

const browser = await chromium.launch({ headless: process.env.HEADED !== "true", channel: process.env.PLAYWRIGHT_CHANNEL || undefined });
const context = await browser.newContext({ ...CLIENT_DEVICE, viewport: { width: 412, height: 915 }, baseURL: BASE_URL, ignoreHTTPSErrors: true, locale: "en-US" });
const page = await context.newPage();
page.setDefaultTimeout(4000);
page.setDefaultNavigationTimeout(8000);
const app = new ClientAppPage(page, { pageConfig: loadJson("ui/data/client-pages.json"), modalConfig: loadJson("ui/data/client-modals.json") });
const network = [];
const progress = [];
let currentAction = { id: "bootstrap", menu: "System", page: "Browser", action: "browser initialization", controlType: "system", startedAt: Date.now() };
const requestMeta = new WeakMap();

context.on("request", (request) => {
  if (ASSET_RE.test(request.url())) return;
  if (!["xhr", "fetch"].includes(request.resourceType())) return;
  let parsed;
  try { parsed = new URL(request.url()); } catch { return; }
  const queryFields = [...parsed.searchParams.keys()].sort();
  const bodyFields = requestFieldNames(request).filter((field) => !SECRET_FIELD_RE.test(field));
  const authRequired = Object.keys(request.headers()).some((key) => /^t$|authorization/i.test(key));
  const item = {
    id: network.length + 1,
    ts: Date.now(),
    actionId: currentAction.id,
    menu: currentAction.menu,
    page: currentAction.page,
    pageRoute: currentAction.route || "",
    controlType: currentAction.controlType,
    action: currentAction.action,
    method: request.method(),
    origin: parsed.origin,
    path: parsed.pathname,
    normalizedPath: normalizedPath(parsed.pathname),
    queryFields,
    bodyFields,
    parameterSources: parameterSources(queryFields, bodyFields, authRequired),
    authRequired,
    thirdParty: isThirdParty(parsed.hostname),
    resourceType: request.resourceType(),
    httpStatus: 0,
    businessStatus: "UNAVAILABLE",
    responseShape: null,
    error: "",
  };
  network.push(item);
  requestMeta.set(request, item);
});

context.on("response", async (response) => {
  const item = requestMeta.get(response.request());
  if (!item) return;
  item.httpStatus = response.status();
  const type = response.headers()["content-type"] || "";
  if (/json|cbor|octet-stream|text/i.test(type)) {
    const decoded = await response.body().then(decodePayload).catch(() => null);
    item.businessStatus = businessStatus(decoded);
    item.responseShape = valueShape(decoded);
  }
  item.classification = endpointClassification(item);
});

context.on("requestfailed", (request) => {
  const item = requestMeta.get(request);
  if (!item) return;
  item.error = safeText(request.failure()?.errorText || "request failed");
  item.classification = item.thirdParty ? "THIRD_PARTY" : "ACTIVE_FAILED";
});

async function runAction(def, actionName, controlType, fn) {
  currentAction = { id: `${def.id}__${actionName.toLowerCase().replace(/[^a-z0-9]+/g, "_")}`, menu: def.menu, page: def.page, route: def.route, action: actionName, controlType, startedAt: Date.now() };
  const networkStart = network.length;
  let status = "COMPLETED";
  let error = "";
  let outcome = "";
  try {
    outcome = safeText(await fn());
    await settle(page);
  } catch (err) {
    status = "FAILED";
    error = safeText(err?.message || err, 300);
  }
  const finishedAt = Date.now();
  progress.push({ ...currentAction, status, error, outcome, url: safeText(page.url(), 300), controls: await controls(page), requestCount: network.length - networkStart, finishedAt });
  fs.writeFileSync(NETWORK_OUT, JSON.stringify({ scannedAt: new Date().toISOString(), environment: "FAT", baseHost: BASE_HOST, records: network }, null, 2));
  fs.writeFileSync(PROGRESS_OUT, JSON.stringify({ scannedAt: new Date().toISOString(), environment: "FAT", pages: progress }, null, 2));
}

async function recordBlocked(def, actionName, controlType, reason) {
  const now = Date.now();
  progress.push({
    id: `${def.id}__${actionName.toLowerCase().replace(/[^a-z0-9]+/g, "_")}`,
    menu: def.menu, page: def.page, route: def.route, action: actionName, controlType,
    startedAt: now, finishedAt: now, status: "BLOCKED_DATA_SCOPE", error: reason,
    outcome: "not executed", url: safeText(page.url(), 300), controls: [], requestCount: 0,
  });
  fs.writeFileSync(PROGRESS_OUT, JSON.stringify({ scannedAt: new Date().toISOString(), environment: "FAT", pages: progress }, null, 2));
}

try {
  for (const def of pages.filter((item) => !item.auth)) {
    await runAction(def, "page initialization", "page", async () => { await page.goto(def.route, { waitUntil: "domcontentloaded" }); await settle(page); assertRoute(page, def.route); return "opened"; });
    if (def.action) await runAction(def, "primary navigation/action", "button", () => def.action(page, app));
    if (def.id === "login") {
      await runAction(def, "switch Password tab", "tab", () => requiredClick(page, ["Password"]));
      await runAction(def, "switch SMS OTP tab", "tab", () => requiredClick(page, ["SMS OTP"]));
      await runAction(def, "request SMS code", "button", () => requestLoginCode(page, app));
    }
  }

  const loginDef = { id: "login_success", menu: "Authentication", page: "Login", route: "/", auth: false };
  await runAction(loginDef, "password login", "submit", () => loginWithPassword(page, app));

  for (const def of pages.filter((item) => item.auth)) {
    await runAction(def, "page initialization", "page", async () => { await page.goto(def.route, { waitUntil: "domcontentloaded" }); await settle(page); assertRoute(page, def.route); return "opened"; });
    if (def.action) await runAction(def, "primary navigation/action", "button", () => def.action(page, app));

    if (def.id === "home") {
      await runAction(def, "open Daily Rewards", "button", () => requiredClick(page, ["Daily Rewards"], { exact: true }));
      await runAction(def, "refresh balance", "button", async () => {
        await page.goto("/", { waitUntil: "domcontentloaded" }); await settle(page);
        const button = page.getByRole("button", { name: /₱/ }).first();
        if (!(await button.isVisible({ timeout: 2000 }).catch(() => false))) throw new Error("balance refresh control not found");
        await button.click(); return "balance button";
      });
      await recordBlocked(def, "favorite first game", "button", "would change existing member favorites; no game record created by this scan");
    }
    if (def.id === "my") {
      await runAction(def, "refresh balance", "button", () => requiredClick(page, ["Refresh balance"], { exact: true }));
      await recordBlocked(def, "copy member ID", "button", "clipboard/member identifier is deliberately not captured in repository evidence");
      await recordBlocked(def, "affiliate application", "card", "would mutate existing member state; no affiliate record created by this scan");
    }

    if (def.id === "rewards") {
      for (const tab of ["All", "Newcomer", "Daily"]) await runAction(def, `select ${tab} tab`, "tab", () => requiredClick(page, [tab], { exact: true }));
      await runAction(def, "open Lucky 7 rules", "button", () => requiredClick(page, ["Lucky 7 rules"], { exact: true }));
      await recordBlocked(def, "Check In", "button", "would change the existing member's reward state; no member created by this scan");
    }
    if (def.id === "free_spins") {
      for (const tab of ["Available", "In Use", "Ended"]) await runAction(def, `select ${tab} tab`, "tab", () => requiredClick(page, [tab], { exact: true }));
      await runAction(def, "start first free-spin game", "button", async () => {
        await page.goto("/my-free-spins", { waitUntil: "domcontentloaded" }); await settle(page);
        return requiredClick(page, ["Start Game"], { exact: true });
      });
    }
    if (def.id === "earn_filcoins") {
      const goCount = await page.getByRole("button", { name: /^Go$/i }).count();
      for (let index = 0; index < goCount; index += 1) {
        if (index === 8) {
          await recordBlocked(def, "daily task Go 9", "button", "previous discovery proved this emits /promo/task/daily/claim; existing member reward state is not scan-owned");
          continue;
        }
        await runAction(def, `daily task Go ${index + 1}`, "button", async () => {
          await page.goto("/s-points-v2", { waitUntil: "domcontentloaded" }); await settle(page);
          const button = page.getByRole("button", { name: /^Go$/i }).nth(index);
          if (!(await button.isVisible({ timeout: 2000 }).catch(() => false))) throw new Error(`Go button ${index + 1} not found`);
          await button.click(); return `Go ${index + 1}`;
        });
      }
    }
    if (def.id === "filcoins_mall") {
      await runAction(def, "select Popular sort", "filter", () => requiredClick(page, ["Popular"], { exact: true }));
      await runAction(def, "select All Filcoins range", "filter", () => requiredClick(page, ["All Filcoins"], { exact: true }));
      await recordBlocked(def, "redeem first product", "button", "would consume existing member Filcoins; no balance created by this scan");
    }
    if (def.id === "game") {
      for (const tab of ["Slot", "Live", "Table", "Arcade", "Lottery"]) await runAction(def, `select ${tab} tab`, "tab", () => requiredClick(page, [tab], { exact: true }));
      await runAction(def, "open Sort By", "filter", () => requiredClick(page, ["Sort By", "Popular"]));
      for (const option of ["Newest", "A-Z", "Z-A", "Popular"]) await runAction(def, `sort ${option}`, "filter", () => requiredClick(page, [option], { exact: true }));
      await runAction(def, "open Providers", "filter", () => requiredClick(page, ["Providers", "Provider"]));
      await runAction(def, "reset Providers", "button", () => requiredClick(page, ["Reset"], { exact: true }));
      await runAction(def, "confirm Providers", "button", () => requiredClick(page, ["Confirm"], { exact: true }));
      await runAction(def, "scroll/load more", "pagination", async () => { await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight)); return "scrolled"; });
    }
    if (def.id === "transaction") {
      for (const tab of ["Deposit", "Withdraw", "Adjustment", "All"]) await runAction(def, `select ${tab} tab`, "tab", () => requiredClick(page, [tab], { exact: true }));
      await runAction(def, "open All Status filter", "filter", () => requiredClick(page, ["All Status"], { exact: true }));
      await runAction(def, "open Today filter", "filter", () => requiredClick(page, ["Today"], { exact: true }));
    }
    if (def.id === "deposit") {
      await recordBlocked(def, "Deposit now", "submit", "no deposit order created by this scan; submitting would mutate an existing account without a scan-owned order chain");
    }
    if (def.id === "withdraw") {
      await recordBlocked(def, "Withdraw Now", "submit", "no scan-owned funds/order chain; submitting would mutate an existing account");
    }
    if (def.id === "account") {
      await recordBlocked(def, "add withdrawal account", "button", "would add an account to an existing member; no member created by this scan");
    }
  }
} finally {
  await settle(page, 400).catch(() => {});
  fs.writeFileSync(NETWORK_OUT, JSON.stringify({ scannedAt: new Date().toISOString(), environment: "FAT", baseHost: BASE_HOST, records: network }, null, 2));
  fs.writeFileSync(PROGRESS_OUT, JSON.stringify({ scannedAt: new Date().toISOString(), environment: "FAT", pages: progress }, null, 2));
  await context.close().catch(() => {});
  await browser.close().catch(() => {});
}

console.log(JSON.stringify({ pages: new Set(progress.map((item) => item.page)).size, actions: progress.length, requests: network.length, endpoints: new Set(network.map((item) => `${item.method} ${item.origin}${item.normalizedPath}`)).size, failedActions: progress.filter((item) => item.status === "FAILED").length }));
