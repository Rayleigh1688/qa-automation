import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";
import { loadEnv, requiredEnv } from "../ui/framework/env.mjs";

loadEnv(process.env.ENV_FILE || ".env.fat");
const target = JSON.parse(fs.readFileSync(process.env.MEMBER_TARGET_FILE || "/tmp/fat-member-lane-kyc_reject.json", "utf8"));
if (target.environment !== "FAT" || target.target_ref !== "FAT-KYC-REJECT-01") throw new Error("unexpected FAT target");
const baseUrl = requiredEnv("ADMIN_URL");
const output = path.resolve("fat-admin-interface-scan/results/record-flow-member-kyc-reject-credit-dynamic-fields.json");
const scrub = value => String(value || "").replace(/(?:\+?63|0)9\d{9}|\b\d{7,}\b/g, "<redacted>").replace(/\s+/g, " ").trim().slice(0, 300);
const browser = await chromium.launch({ headless: process.env.ADMIN_SCAN_HEADED !== "false" });
const context = await browser.newContext({ ignoreHTTPSErrors: true, viewport: { width: 1600, height: 1000 }, locale: "en-US" });
const page = await context.newPage();

try {
  await page.goto(baseUrl, { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.getByPlaceholder(/请输入用户名|user\s*name|email/i).fill(requiredEnv("ADMIN_EMAIL"));
  await page.getByPlaceholder(/请输入密码|password/i).fill(requiredEnv("ADMIN_PASSWORD"));
  await page.getByRole("button", { name: /登\s*录|log\s*in/i }).click();
  const loginCode = page.getByPlaceholder(/谷歌验证|google.*(?:code|verification|authenticator)/i); await loginCode.waitFor({ state: "visible", timeout: 10000 }); await loginCode.fill(requiredEnv("ADMIN_GOOGLE_CODE"));
  await page.getByRole("button", { name: /确\s*定|confirm|ok/i }).click(); await page.waitForURL(url => !url.pathname.startsWith("/user/login"), { timeout: 20000 });
  await page.goto(new URL(`/member-center/detail/${target.uid}`, baseUrl).toString(), { waitUntil: "domcontentloaded", timeout: 25000 });
  const button = page.locator("button:visible").filter({ hasText: /^(?:Credit or Debit|上下分)$/i }).last(); await button.waitFor({ state: "visible", timeout: 12000 }); await button.click();
  const modal = page.locator(".ant-modal:visible").last(); await modal.waitFor({ state: "visible", timeout: 8000 });
  await modal.getByText(/^(?:Credit Top.?up|上分)$/i, { exact: true }).click();
  const restrictionItem = modal.locator(".ant-form-item:visible").filter({ hasText: /Turnover Venue\/Game Restrictions|流水.*(?:场馆|游戏)/i }).first();
  await restrictionItem.waitFor({ state: "visible", timeout: 5000 });
  const treeSelect = restrictionItem.locator(".ant-tree-select").first();
  await page.waitForFunction(element => !/loading/i.test(element.innerText), await treeSelect.elementHandle(), { timeout: 15000 }).catch(() => {});
  await treeSelect.click(); await page.waitForTimeout(500);
  const treeOptions = (await page.locator(".ant-select-dropdown:visible .ant-select-tree-treenode:visible").allInnerTexts()).map(scrub).filter(Boolean);
  const fields = await modal.locator(".ant-form-item:visible").evaluateAll(items => items.map((item, index) => ({
    index, label: item.querySelector(".ant-form-item-label")?.innerText.replace(/\s+/g, " ").trim() || "", required: Boolean(item.querySelector(".ant-form-item-required")),
    controls: [...item.querySelectorAll("input,textarea,button,[role=button],.ant-select,.ant-tree-select")].map(element => ({ tag: element.tagName.toLowerCase(), type: element.getAttribute("type") || "", role: element.getAttribute("role") || "", placeholder: element.getAttribute("placeholder") || "", class_names: [...element.classList].filter(name => /select|tree|cascader|input|button/.test(name)).slice(0, 6), text: element.matches("input,textarea") ? "" : element.innerText.replace(/\s+/g, " ").trim().slice(0, 80), disabled: Boolean(element.disabled) })).slice(0, 20),
  })));
  const candidateLabels = fields.filter(field => /turnover|game|venue|platform|流水|游戏|场馆/i.test(field.label));
  fs.writeFileSync(output, `${JSON.stringify({ captured_at: new Date().toISOString(), environment: "FAT", target_ref: target.target_ref, uid_ref: "FAT-UID-KYC-REJECT-01", page_route: "/member-center/detail/{uid}", operation: "Credit Top-up dynamic required fields", fields, candidate_labels: candidateLabels, tree_options: treeOptions, submitted: false, writes: 0, raw_phone_or_uid_persisted: false, secrets_persisted: false }, null, 2)}\n`);
  console.log(JSON.stringify({ fields: fields.map(field => ({ label: scrub(field.label), required: field.required, controls: field.controls.map(control => ({ tag: control.tag, type: control.type, role: control.role, placeholder: scrub(control.placeholder), class_names: control.class_names, text: scrub(control.text), disabled: control.disabled })) })), candidates: candidateLabels.map(field => field.label), tree_options: treeOptions, writes: 0 }));
} finally { await browser.close(); }
