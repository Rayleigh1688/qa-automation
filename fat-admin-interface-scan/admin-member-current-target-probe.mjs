import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";
import { loadEnv, requiredEnv } from "../ui/framework/env.mjs";
import { decodeCbor } from "../ui/framework/cbor-decoder.mjs";

loadEnv(process.env.ENV_FILE || ".env.fat");
const target = JSON.parse(fs.readFileSync("/tmp/fat-record-flow-target.json", "utf8"));
if (target.environment !== "FAT") throw new Error("target environment is not FAT");
const expectedRef = "KYC-RUN-B9CA6D6A0704";
if (target.target_ref !== expectedRef) throw new Error("unexpected current-run target_ref");
const uidRef = "UID-REF-26913CC85458";
const rawUid = String(target.uid), rawPhone = String(target.phone);
const baseUrl = requiredEnv("ADMIN_URL"), origin = new URL(baseUrl).origin;
const output = path.resolve("fat-admin-interface-scan/results/record-flow-member-current-target.json");
const network = [], state = {};
let action = "login";

const normalizePath = (value) => value.replace(/\/member-center\/detail\/[^/?#]+/g, "/member-center/detail/{uid}").replace(/\/\d{4,}(?=\/|$)/g, "/{id}");
const safeDom = (value) => String(value || "").replace(/\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi, "<redacted>")
  .replace(/(?:\+?63|0)9\d{9}/g, "<redacted>").replace(/\b\d{7,}\b/g, "<redacted>").replace(/\s+/g, " ").trim().slice(0, 200);
const safeState = (value) => {
  if (value === null || ["boolean", "number"].includes(typeof value)) return value;
  if (typeof value === "string" && /^[A-Za-z_-]{1,32}$/.test(value)) return value;
  return "<redacted-or-present>";
};
const stateFields = {
  "/admin/member/detail": ["status", "block_state", "banned_state", "risk_level", "risk_tag", "is_agent", "deposit_multiple", "deposit_multiple_type", "platform_deposit_multiple", "vip_level", "vip_manual_level", "left_turnover", "left_turnover_count", "has_login_password", "balance", "available_balance", "withdrawable_balance", "tokens_balance", "locked"],
  "/admin/kyc/detail": ["kyc_status", "status", "blacklist_status", "review_times", "ocr_status"],
  "/admin/finance/member/wallet": ["balance", "locked", "withdrawable"],
};
const browser = await chromium.launch({ headless: process.env.ADMIN_SCAN_HEADED === "false" });
const context = await browser.newContext({ ignoreHTTPSErrors: true, viewport: { width: 1440, height: 1000 }, locale: "en-US" });
const page = await context.newPage();

page.on("response", async (response) => {
  const request = response.request(); if (!["xhr", "fetch"].includes(request.resourceType())) return;
  let url; try { url = new URL(response.url()); } catch { return; } if (url.origin !== origin) return;
  let decoded = null, bodyFields = [];
  try {
    const raw = request.postDataBuffer(); if (raw?.length) {
      const type = (request.headers()["content-type"] || "").toLowerCase();
      const body = type.includes("json") ? JSON.parse(raw.toString("utf8")) : decodeCbor(new Uint8Array(raw));
      if (body && typeof body === "object" && !Array.isArray(body)) bodyFields = Object.keys(body).sort();
    }
  } catch {}
  try { decoded = decodeCbor(new Uint8Array(await response.body())); } catch {}
  const data = decoded?.data;
  const responseKeys = data && typeof data === "object" && !Array.isArray(data) ? Object.keys(data).sort() : [];
  if (stateFields[url.pathname] && data && typeof data === "object") {
    state[url.pathname] = Object.fromEntries(stateFields[url.pathname].filter((key) => key in data).map((key) => [key, safeState(data[key])]));
    if (url.pathname === "/admin/member/detail") state[url.pathname].has_parent_uid = Boolean(data.parent_uid);
  }
  network.push({ action, method: request.method(), path: normalizePath(url.pathname), query_fields: [...url.searchParams.keys()].sort(),
    body_fields: bodyFields, http_status: response.status(), business_status: decoded?.status ?? null,
    response_type: Array.isArray(data) ? "list" : data === null ? "null" : typeof data, response_keys: responseKeys,
    target_value_persisted: false });
});

async function quiet() {
  let last = network.length, stable = Date.now();
  for (let i = 0; i < 60; i += 1) { await page.waitForTimeout(100); if (last !== network.length) { last = network.length; stable = Date.now(); } else if (Date.now() - stable > 700) return; }
}
async function login() {
  await page.goto(baseUrl, { waitUntil: "domcontentloaded", timeout: 30_000 });
  await page.getByPlaceholder(/请输入用户名|user\s*name|email/i).fill(requiredEnv("ADMIN_EMAIL"));
  await page.getByPlaceholder(/请输入密码|password/i).fill(requiredEnv("ADMIN_PASSWORD"));
  await page.getByRole("button", { name: /登\s*录|log\s*in/i }).click();
  const verification = page.getByPlaceholder(/谷歌验证|google.*(?:code|verification|authenticator)/i);
  await verification.waitFor({ state: "visible", timeout: 10_000 }); await verification.fill(requiredEnv("ADMIN_GOOGLE_CODE"));
  await page.getByRole("button", { name: /确\s*定|confirm|ok/i }).click();
  await page.waitForURL((url) => !url.pathname.startsWith("/user/login"), { timeout: 20_000 });
}

await login();
action = "current_target:list query by Phone Number";
await page.goto(new URL("/member-center/list", baseUrl).toString(), { waitUntil: "domcontentloaded", timeout: 25_000 }); await quiet();
const phoneItem = page.locator(".ant-form-item").filter({ has: page.locator(".ant-form-item-label", { hasText: /^\s*Phone Number\s*$/i }) }).first();
const phoneInput = phoneItem.locator("input").first(); await phoneInput.waitFor({ state: "visible", timeout: 10_000 }); await phoneInput.fill(rawPhone);
const query = page.locator("button").filter({ hasText: /^\s*Query\s*$/i }).first(); await query.click(); await quiet();
const matchedRow = page.locator(".ant-table-tbody tr:not(.ant-table-measure-row):visible").filter({ hasText: rawPhone }).first();
await matchedRow.waitFor({ state: "visible", timeout: 15_000 });
const rowMatchVerified = (await matchedRow.innerText()).includes(rawPhone);
action = "current_target:list matched row View Details";
await matchedRow.getByRole("button", { name: "View Details", exact: true }).click();
await page.waitForURL((url) => /\/member-center\/detail\//.test(url.pathname), { timeout: 15_000 }); await quiet();
const routeUidVerified = new URL(page.url()).pathname.endsWith(`/${rawUid}`);
if (!rowMatchVerified || !routeUidVerified) throw new Error("current target row/detail UID correlation failed");

action = "current_target:Function Limitation baseline";
const limitationTab = page.locator(".ant-layout-content .ant-tabs-tab").filter({ hasText: /^\s*Function Limitation\s*$/ }).last();
await limitationTab.click(); await quiet();
const limitationPanel = page.locator(".ant-tabs-tabpane-active:visible").last();
const limitationRows = (await limitationPanel.locator("tr:visible").allInnerTexts()).map(safeDom);
const limitationButtons = await limitationPanel.locator("button:visible").evaluateAll((buttons) => buttons.map((button, index) => ({
  index, text: button.innerText.replace(/\s+/g, " ").trim(), disabled: button.disabled,
  row_text: button.closest("tr")?.innerText.replace(/\s+/g, " ").trim() || "",
})));

const stableWriteControls = ["+ Lock", "Risk Control", "Credit or Debit", "流水要求调整", "changed", "Manual Adjust VIP", "Clear Turnover Requirement", "Risk Control Adjustment", "Token Top-Up and Withdrawal"];
const visibleButtons = await page.locator(".ant-layout-content button:visible").allTextContents();
const currentVisiblePrerequisites = stableWriteControls.filter((name) => visibleButtons.some((text) => text.replace(/\s+/g, " ").trim() === name));

const result = { captured_at: new Date().toISOString(), environment: "FAT", phase: "current_target_readonly_prerequisite",
  target_ref: expectedRef, uid_ref: uidRef, source_file_mode: "0600", raw_uid_persisted: false, raw_phone_persisted: false,
  list_query: { route: "/member-center/list", field: "Phone Number", row_match_verified: rowMatchVerified, response_values_persisted: false },
  detail: { route: "/member-center/detail/{uid}", route_uid_verified: routeUidVerified, state,
    limitation_rows: limitationRows, limitation_buttons: limitationButtons.map((button) => ({ ...button, text: safeDom(button.text), row_text: safeDom(button.row_text) })) },
  visible_reversible_prerequisite_controls: currentVisiblePrerequisites,
  network, writes_executed: 0, side_effects: [], kyc_phase_guard: "pre-submission; no member state-changing control clicked" };
fs.writeFileSync(output, JSON.stringify(result, null, 2) + "\n");
await browser.close();
console.log(JSON.stringify({ target_ref: expectedRef, uid_ref: uidRef, list_match: rowMatchVerified, route_uid_match: routeUidVerified,
  state_endpoints: Object.keys(state), network_events: network.length, writes: 0, side_effects: 0 }));
