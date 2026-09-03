import fs from "node:fs";
import { chromium } from "playwright";
import { loadEnv, requiredEnv } from "../ui/framework/env.mjs";
import { decodeCbor } from "../ui/framework/cbor-decoder.mjs";

loadEnv(process.env.ENV_FILE || ".env.fat");
const baseUrl = requiredEnv("ADMIN_URL");
const origin = new URL(baseUrl).origin;
const storagePath = process.env.ADMIN_STORAGE_STATE || "/tmp/fat-admin-shared-storage-state.json";
if (!storagePath.startsWith("/tmp/")) throw new Error("ADMIN_STORAGE_STATE must be an ignored /tmp path");

const browser = await chromium.launch({ headless: process.env.ADMIN_SCAN_HEADED !== "true" });
try {
  const loginContext = await browser.newContext({ ignoreHTTPSErrors: true, viewport: { width: 1440, height: 1000 }, locale: "en-US" });
  const loginPage = await loginContext.newPage();
  await loginPage.goto(baseUrl, { waitUntil: "domcontentloaded", timeout: 30_000 });
  await loginPage.getByPlaceholder(/请输入用户名|user\s*name|email/i).fill(requiredEnv("ADMIN_EMAIL"));
  await loginPage.getByPlaceholder(/请输入密码|password/i).fill(requiredEnv("ADMIN_PASSWORD"));
  await loginPage.getByRole("button", { name: /登\s*录|log\s*in/i }).click();
  const verification = loginPage.getByPlaceholder(/谷歌验证|google.*(?:code|verification|authenticator)/i);
  await verification.waitFor({ state: "visible", timeout: 10_000 });
  await verification.fill(requiredEnv("ADMIN_GOOGLE_CODE"));
  await loginPage.getByRole("button", { name: /确\s*定|confirm|ok/i }).click();
  await loginPage.waitForURL((url) => !url.pathname.startsWith("/user/login"), { timeout: 20_000 });
  await loginContext.storageState({ path: storagePath });
  fs.chmodSync(storagePath, 0o600);
  await loginContext.close();

  let meDetail = null;
  const verifyContext = await browser.newContext({ ignoreHTTPSErrors: true, viewport: { width: 1440, height: 1000 }, locale: "en-US", storageState: storagePath });
  const verifyPage = await verifyContext.newPage();
  verifyPage.on("response", async (response) => {
    let url;
    try { url = new URL(response.url()); } catch { return; }
    if (url.origin !== origin || url.pathname !== "/admin/me/detail") return;
    let decoded = null;
    try { decoded = decodeCbor(new Uint8Array(await response.body())); } catch {}
    meDetail = { http_status: response.status(), business_status: decoded?.status ?? null };
  });
  await verifyPage.goto(new URL("/member-center/list", baseUrl).toString(), { waitUntil: "domcontentloaded", timeout: 30_000 });
  await verifyPage.waitForTimeout(1200);
  const pathname = new URL(verifyPage.url()).pathname;
  if (pathname.startsWith("/user/login")) throw new Error("shared admin storage state verification returned to /user/login");
  if (!meDetail || meDetail.http_status !== 200 || meDetail.business_status !== true) {
    throw new Error("shared admin storage state verification did not receive successful /admin/me/detail");
  }
  await verifyContext.close();
  const stat = fs.statSync(storagePath);
  console.log(JSON.stringify({ storage_state: storagePath, verified_route: "/member-center/list", me_detail_http_status: meDetail.http_status, me_detail_business_status: meDetail.business_status, file_mode: (stat.mode & 0o777).toString(8), sensitive_values_printed: false }));
} finally {
  await browser.close();
}
