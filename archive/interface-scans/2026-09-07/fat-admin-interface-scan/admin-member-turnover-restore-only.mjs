import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";
import { loadEnv, requiredEnv } from "../ui/framework/env.mjs";
import { decodeCbor } from "../ui/framework/cbor-decoder.mjs";

loadEnv(process.env.ENV_FILE || ".env.fat");
const target = JSON.parse(fs.readFileSync("/tmp/fat-member-lane-reversible.json", "utf8"));
if (target.environment !== "FAT" || target.target_ref !== "FAT-MEMBER-REV-01") throw new Error("BLOCKED_DATA_SCOPE: unexpected reversible target");
const storagePath = process.env.ADMIN_STORAGE_STATE || "/tmp/fat-admin-shared-storage-state.json";
if (!fs.existsSync(storagePath)) throw new Error("SESSION_INVALID: shared admin storage state is missing");
const storageState = JSON.parse(fs.readFileSync(storagePath, "utf8"));
const output = path.resolve("fat-admin-interface-scan/results/record-flow-member-reversible-turnover-adjust-flow.json");
const prior = JSON.parse(fs.readFileSync(output, "utf8"));
const initial = JSON.parse(fs.readFileSync(path.resolve("fat-admin-interface-scan/results/record-flow-member-reversible-turnover-submit-control-probe.json"), "utf8"));
if (prior.target_ref !== target.target_ref || prior.add?.business_status !== true || prior.after_add?.left_turnover_count !== 1 || prior.restore !== null) {
  throw new Error("BLOCKED_DATA_SCOPE: current turnover cannot be correlated to the successful add");
}

const baseUrl = requiredEnv("ADMIN_URL"), origin = new URL(baseUrl).origin;
const network = [];
let action = "validate shared session", latestCount = null;
const scrub = (value) => String(value || "").replace(/(?:\+?63|0)9\d{9}|\b\d{7,}\b/g, "<redacted>").replace(/\s+/g, " ").trim().slice(0, 300);
const browser = await chromium.launch({ headless: process.env.ADMIN_SCAN_HEADED !== "true" });
const context = await browser.newContext({ ignoreHTTPSErrors: true, viewport: { width: 1440, height: 1000 }, locale: "zh-CN", storageState });
const page = await context.newPage();

page.on("response", async (response) => {
  const request = response.request();
  if (!["xhr", "fetch"].includes(request.resourceType())) return;
  const url = new URL(response.url());
  if (url.origin !== origin) return;
  let decoded = null, bodyFields = [];
  try {
    const raw = request.postDataBuffer();
    if (raw?.length) {
      const body = (request.headers()["content-type"] || "").includes("json") ? JSON.parse(raw.toString("utf8")) : decodeCbor(new Uint8Array(raw));
      if (body && typeof body === "object" && !Array.isArray(body)) bodyFields = Object.keys(body).sort();
    }
  } catch {}
  try { decoded = decodeCbor(new Uint8Array(await response.body())); } catch {}
  if (url.pathname === "/admin/member/detail" && Number.isInteger(decoded?.data?.left_turnover_count)) latestCount = decoded.data.left_turnover_count;
  network.push({ action, method: request.method(), path: url.pathname, body_fields: bodyFields, http_status: response.status(), business_status: decoded?.status ?? null, response_values_persisted: false });
});

function base32Decode(value) {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567", normalized = value.replace(/\s|=/g, "").toUpperCase();
  let bits = "";
  for (const char of normalized) { const index = alphabet.indexOf(char); if (index < 0) throw new Error("invalid approval TOTP secret"); bits += index.toString(2).padStart(5, "0"); }
  const bytes = [];
  for (let index = 0; index + 8 <= bits.length; index += 8) bytes.push(parseInt(bits.slice(index, index + 8), 2));
  return Buffer.from(bytes);
}

function currentTotp() {
  const key = base32Decode(requiredEnv("ADMIN_APPROVAL_TOTP_SECRET"));
  const algorithm = (process.env.ADMIN_APPROVAL_TOTP_ALGORITHM || "SHA1").toLowerCase().replace("-", "");
  const message = Buffer.alloc(8); message.writeBigUInt64BE(BigInt(Math.floor(Date.now() / 30_000)));
  const digest = crypto.createHmac(algorithm, key).update(message).digest(), offset = digest[digest.length - 1] & 15;
  return String((digest.readUInt32BE(offset) & 0x7fffffff) % 1_000_000).padStart(6, "0");
}

async function openDetail(label) {
  action = label; latestCount = null;
  await page.goto(new URL(`/member-center/detail/${target.uid}`, baseUrl).toString(), { waitUntil: "domcontentloaded", timeout: 25_000 });
  if (new URL(page.url()).pathname.startsWith("/user/login")) throw new Error("SESSION_INVALID: shared admin session redirected to login");
  for (let index = 0; index < 80 && latestCount === null; index += 1) await page.waitForTimeout(100);
  if (latestCount === null) throw new Error("member detail turnover state unavailable");
  return latestCount;
}

let restore = null, afterRestore = null, error = "", submitEvidence = null;
try {
  const before = await openDetail("validate recovery before");
  if (before !== 1) throw new Error(`BLOCKED_DATA_SCOPE: recovery expected count=1, observed=${before}`);
  await page.getByRole("button", { name: "流水要求调整", exact: true }).click();
  const modal = page.locator(".ant-modal:visible").last(); await modal.waitFor({ state: "visible", timeout: 8_000 });
  await modal.locator(".ant-radio-wrapper").filter({ hasText: /^\s*扣除\s*$/ }).click();
  const gameInput = modal.locator(".ant-form-item").filter({ hasText: /流水游戏限制/ }).locator('input[type="search"]');
  if (await gameInput.count() !== 1 || !await gameInput.isDisabled()) throw new Error("STRICT_LOCATOR_PROBLEM: subtract game field is not uniquely disabled");
  const amountLabel = modal.locator(".ant-form-item-label").filter({ hasText: /^\s*(?:调整金额|Adjustment Amount)\s*$/i });
  if (await amountLabel.count() !== 1) throw new Error("STRICT_LOCATOR_PROBLEM: subtract amount label is not unique");
  const amount = amountLabel.locator("xpath=ancestor::*[contains(concat(' ', normalize-space(@class), ' '), ' ant-form-item ')][1]").locator("input:not([disabled])"); if (await amount.count() !== 1) throw new Error("STRICT_LOCATOR_PROBLEM: subtract amount control is not unique"); await amount.fill("1");
  const fields = modal.locator(".ant-form-item"); let codeLength = 0, reasonLength = 0;
  for (let index = 0; index < await fields.count(); index += 1) {
    const item = fields.nth(index), label = scrub(await item.locator(".ant-form-item-label").innerText().catch(() => ""));
    const input = item.locator('textarea,input:not([type=radio]):not([type=checkbox]):not([type=hidden]):not([type=file]):not([disabled])').first();
    if (!await input.isVisible().catch(() => false)) continue;
    if (/Google(?: Verification Code|验证码)/i.test(label)) { const remaining = 30 - Math.floor(Date.now() / 1000) % 30; if (remaining < 7) await page.waitForTimeout((remaining + 1) * 1000); const code = currentTotp(); await input.fill(code); codeLength = code.length; }
    else if (/(?:Adjustment Reason|调整理由)/i.test(label)) { const reason = "FAT reversible turnover restore"; await input.fill(reason); reasonLength = reason.length; }
  }
  const submit = modal.locator(".ant-modal-footer .ant-btn-primary:visible");
  if (await submit.count() !== 1) throw new Error("STRICT_LOCATOR_PROBLEM: subtract submit control is not unique");
  const submitType = (await submit.getAttribute("type") || "").toLowerCase(), submitText = (await submit.innerText()).replace(/\s+/g, "").toLowerCase();
  if (submitType !== "button" || !["确定", "ok", "confirm"].includes(submitText)) throw new Error("STRICT_LOCATOR_PROBLEM: unexpected subtract submit control");
  action = "turnover subtract one restore";
  const responsePromise = page.waitForResponse((response) => response.request().method() === "POST" && new URL(response.url()).pathname === "/admin/finance/turnover/sub", { timeout: 15_000 }).catch(() => null);
  await submit.click(); const response = await responsePromise;
  if (!response) { const errors = (await modal.locator(".ant-form-item-explain-error:visible").allInnerTexts()).map(scrub); throw new Error(`subtract sent no write request; validation=${errors.join(" | ") || "none"}`); }
  let decoded = null; try { decoded = decodeCbor(new Uint8Array(await response.body())); } catch {}
  restore = { method: "POST", path: "/admin/finance/turnover/sub", http_status: response.status(), business_status: decoded?.status ?? null, body_fields: network.findLast((item) => item.path === "/admin/finance/turnover/sub")?.body_fields || [] };
  submitEvidence = { amount_filled: true, game_field_disabled: true, totp_length: codeLength, reason_length: reasonLength, request_observed: true };
  if (restore.http_status >= 400 || restore.business_status !== true) throw Object.assign(new Error("turnover subtract business failure"), { write_event: restore });
  await page.waitForTimeout(1_200); afterRestore = await openDetail("verify recovery after sub");
  if (afterRestore !== 0) { await page.waitForTimeout(12_000); afterRestore = await openDetail("delayed verify recovery after sub"); }
  if (afterRestore !== 0) throw new Error(`turnover restore did not return to zero; observed=${afterRestore}`);
} catch (caught) { error = scrub(caught?.message || caught); }

const restored = Boolean(restore?.business_status === true && afterRestore === 0);
const result = { captured_at: new Date().toISOString(), environment: "FAT", target_ref: target.target_ref, uid_ref: "FAT-UID-REV-01", page_route: "/member-center/detail/{uid}", operation: "Turnover requirement adjustment minimal reversible closure", before: initial.before, add: prior.add, after_add: prior.after_add, restore, after_restore: afterRestore === null ? null : { left_turnover_count: afterRestore }, restored, recovery_from_prior_run: true, error, writes: Number(Boolean(prior.add)) + Number(Boolean(restore)), side_effects: restored ? ["temporary all-games turnover requirement +1; restored by -1"] : ["current-run turnover +1 still awaiting recovery"], submit_evidence: [prior.submit_evidence?.find((item) => item.action === "turnover add one"), submitEvidence].filter(Boolean), raw_phone_or_uid_persisted: false, network };
fs.writeFileSync(output, JSON.stringify(result, null, 2) + "\n");
await browser.close();
console.log(JSON.stringify({ target_ref: target.target_ref, restore, after_restore: result.after_restore, restored, error, writes: result.writes }));
if (error || !restored) process.exitCode = 1;
