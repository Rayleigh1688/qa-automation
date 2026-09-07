import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";
import { loadEnv, requiredEnv } from "../ui/framework/env.mjs";
import { decodeCbor } from "../ui/framework/cbor-decoder.mjs";

loadEnv(process.env.ENV_FILE || ".env.fat");

const laneKey = process.env.MEMBER_LANE || "reversible";
const lanes = {
  reversible: {
    targetRef: "FAT-MEMBER-REV-01",
    uidRef: "FAT-UID-REV-01",
    directory: "member-reversible",
  },
  terminal: {
    targetRef: "FAT-MEMBER-END-01",
    uidRef: "FAT-UID-END-01",
    directory: "member-irreversible",
  },
  kyc_reject: {
    targetRef: "FAT-KYC-REJECT-01",
    uidRef: "FAT-UID-KYC-REJECT-01",
    directory: "kyc-reject-resubmit",
  },
};
const lane = lanes[laneKey];
if (!lane) throw new Error(`unsupported MEMBER_LANE: ${laneKey}`);

const summaryPath = path.resolve(
  "api/results/provisioning/interface-discovery",
  lane.directory,
  "member-bootstrap-summary.json",
);
const summary = JSON.parse(fs.readFileSync(summaryPath, "utf8"));
if (summary.environment_file !== ".env.fat" || summary.status !== "PASS") {
  throw new Error("lane provisioning summary is not a successful FAT result");
}
const rawPhone = String(summary.phone || "");
if (!/^\d{10,12}$/.test(rawPhone)) throw new Error("lane phone is absent or invalid");

const baseUrl = requiredEnv("ADMIN_URL");
const origin = new URL(baseUrl).origin;
const runtimePath = `/tmp/fat-member-lane-${laneKey}.json`;
const outputPath = path.resolve(
  `fat-admin-interface-scan/results/record-flow-member-lane-${laneKey}-baseline.json`,
);
const network = [];
const state = {};
let action = "login";

const stateFields = {
  "/admin/member/detail": [
    "status", "block_state", "banned_state", "risk_level", "is_agent",
    "deposit_multiple", "vip_level", "vip_manual_level", "left_turnover",
    "left_turnover_count", "has_login_password",
  ],
  "/admin/kyc/detail": ["kyc_status", "status", "review_times", "ocr_status"],
  "/admin/finance/member/wallet": ["balance", "locked", "withdrawable"],
};

function safeState(value) {
  if (value === null || ["boolean", "number"].includes(typeof value)) return value;
  if (typeof value === "string" && /^[A-Za-z_-]{1,32}$/.test(value)) return value;
  return "<present>";
}

function responseShape(data) {
  if (!data || typeof data !== "object") return {};
  const sample = Array.isArray(data) ? data.find((item) => item && typeof item === "object") : data;
  if (!sample || typeof sample !== "object") return {};
  return {
    data_keys: Object.keys(sample).sort(),
    nested_keys: Object.fromEntries(Object.entries(sample)
      .filter(([, value]) => value && typeof value === "object")
      .map(([key, value]) => {
        const nested = Array.isArray(value) ? value.find((item) => item && typeof item === "object") : value;
        return [key, nested && typeof nested === "object" ? Object.keys(nested).sort() : []];
      })),
  };
}

const browser = await chromium.launch({
  headless: process.env.ADMIN_SCAN_HEADED === "false",
});
const context = await browser.newContext({
  ignoreHTTPSErrors: true,
  viewport: { width: 1440, height: 1000 },
  locale: "en-US",
});
const page = await context.newPage();

page.on("response", async (response) => {
  const request = response.request();
  if (!["xhr", "fetch"].includes(request.resourceType())) return;
  let url;
  try { url = new URL(response.url()); } catch { return; }
  if (url.origin !== origin) return;
  let decoded = null;
  let bodyFields = [];
  try {
    const raw = request.postDataBuffer();
    if (raw?.length) {
      const type = (request.headers()["content-type"] || "").toLowerCase();
      const body = type.includes("json")
        ? JSON.parse(raw.toString("utf8"))
        : decodeCbor(new Uint8Array(raw));
      if (body && typeof body === "object" && !Array.isArray(body)) {
        bodyFields = Object.keys(body).sort();
      }
    }
  } catch {}
  try { decoded = decodeCbor(new Uint8Array(await response.body())); } catch {}
  const data = decoded?.data;
  if (stateFields[url.pathname] && data && typeof data === "object") {
    state[url.pathname] = Object.fromEntries(
      stateFields[url.pathname]
        .filter((key) => key in data)
        .map((key) => [key, safeState(data[key])]),
    );
  }
  network.push({
    action,
    method: request.method(),
    path: url.pathname,
    query_fields: [...url.searchParams.keys()].sort(),
    body_fields: bodyFields,
    http_status: response.status(),
    business_status: decoded?.status ?? null,
    response_type: Array.isArray(data) ? "list" : data === null ? "null" : typeof data,
    response_shape: responseShape(data),
    response_values_persisted: false,
  });
});

async function quiet() {
  let last = network.length;
  let stableAt = Date.now();
  for (let index = 0; index < 60; index += 1) {
    await page.waitForTimeout(100);
    if (last !== network.length) {
      last = network.length;
      stableAt = Date.now();
    } else if (Date.now() - stableAt > 700) return;
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

try {
  await login();
  action = `${laneKey}:query exact current-run member`;
  await page.goto(new URL("/member-center/list", baseUrl).toString(), {
    waitUntil: "domcontentloaded",
    timeout: 25_000,
  });
  await quiet();
  const phoneItem = page.locator(".ant-form-item").filter({
    has: page.locator(".ant-form-item-label", { hasText: /^\s*Phone Number\s*$/i }),
  }).first();
  await phoneItem.locator("input").first().fill(rawPhone);
  await page.locator("button").filter({ hasText: /^\s*Query\s*$/i }).first().click();
  await quiet();
  const row = page.locator(".ant-table-tbody tr:not(.ant-table-measure-row):visible")
    .filter({ hasText: rawPhone }).first();
  await row.waitFor({ state: "visible", timeout: 15_000 });
  action = `${laneKey}:open View Details`;
  await row.getByRole("button", { name: "View Details", exact: true }).click();
  await page.waitForURL((url) => /\/member-center\/detail\//.test(url.pathname), {
    timeout: 15_000,
  });
  await quiet();
  const rawUid = new URL(page.url()).pathname.split("/").filter(Boolean).at(-1);
  if (!rawUid) throw new Error("detail route did not provide UID");

  fs.writeFileSync(runtimePath, `${JSON.stringify({
    environment: "FAT",
    lane: laneKey,
    target_ref: lane.targetRef,
    uid: rawUid,
    phone: rawPhone,
  }, null, 2)}\n`, { mode: 0o600 });
  fs.chmodSync(runtimePath, 0o600);

  fs.writeFileSync(outputPath, `${JSON.stringify({
    captured_at: new Date().toISOString(),
    environment: "FAT",
    lane: laneKey,
    target_ref: lane.targetRef,
    uid_ref: lane.uidRef,
    list_query_match: true,
    detail_route_uid_observed: true,
    state,
    network,
    writes_executed: 0,
    side_effects: [],
    raw_phone_or_uid_persisted: false,
  }, null, 2)}\n`);
  console.log(JSON.stringify({
    lane: laneKey,
    target_ref: lane.targetRef,
    uid_ref: lane.uidRef,
    list_match: true,
    state_endpoints: Object.keys(state),
    runtime_file_mode: "0600",
  }));
} finally {
  await browser.close();
}
