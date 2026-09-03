import fs from "node:fs";
import path from "node:path";
import { chromium, devices } from "playwright";
import { ClientAppPage } from "../ui/elements/client-app.page.mjs";
import { loadEnv } from "../ui/framework/env.mjs";
import { decodeCbor } from "../ui/framework/cbor-decoder.mjs";
import { loadJson } from "../ui/framework/data-loader.mjs";

loadEnv(process.env.ENV_FILE || ".env.fat");
const target = JSON.parse(fs.readFileSync("/tmp/fat-record-flow-target.json", "utf8"));
if (target.environment !== "FAT" || target.target_ref !== "KYC-RUN-B9CA6D6A0704") throw new Error("unexpected KYC target");
const baseURL = process.env.CLIENT_BASE_URL || process.env.API_URL;
const origin = new URL(baseURL).origin;
const observations = [];
const browser = await chromium.launch({ headless: process.env.HEADED !== "true" });
const context = await browser.newContext({ ...devices["Pixel 7"], viewport: { width: 412, height: 915 }, baseURL, ignoreHTTPSErrors: true, locale: "en-US" });
const page = await context.newPage();
const app = new ClientAppPage(page, { pageConfig: loadJson("ui/data/client-pages.json"), modalConfig: loadJson("ui/data/client-modals.json") });

page.on("response", async (response) => {
  const url = new URL(response.url());
  if (url.origin !== origin || !["/member/detail", "/member/kyc/detail"].includes(url.pathname)) return;
  let decoded = null;
  try { decoded = decodeCbor(new Uint8Array(await response.body())); } catch {}
  observations.push({
    method: response.request().method(), path: url.pathname, http_status: response.status(), business_status: decoded?.status ?? null,
    response_shape: { top_level_keys: decoded && typeof decoded === "object" ? Object.keys(decoded).sort() : [], data_type: decoded?.data === null ? "null" : typeof decoded?.data, data_keys: decoded?.data && typeof decoded.data === "object" ? Object.keys(decoded.data).sort() : [] },
    kyc_status: Number.isInteger(decoded?.data?.kyc_status) ? decoded.data.kyc_status : null,
  });
});

await app.loginWithPassword(String(target.phone), process.env.REGISTER_PASSWORD || "");
await page.goto("/s-kyc-v2", { waitUntil: "domcontentloaded" });
await page.waitForTimeout(1800);
const statuses = observations.map((item) => item.kyc_status).filter(Number.isInteger);
const approved = statuses.includes(5);
const result = { captured_at: new Date().toISOString(), environment: "FAT", target_ref: target.target_ref, uid_ref: "UID-REF-26913CC85458", action: "post-approval client status refresh", expected_kyc_status: 5, observed_kyc_statuses: [...new Set(statuses)], approved, observations };
fs.writeFileSync(path.resolve("fat-admin-interface-scan/results/record-flow-kyc-after-status.json"), JSON.stringify(result, null, 2) + "\n");
await browser.close();
console.log(JSON.stringify({ target_ref: target.target_ref, observed_kyc_statuses: result.observed_kyc_statuses, approved }));
if (!approved) process.exitCode = 1;
