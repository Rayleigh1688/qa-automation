import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { chromium } from "playwright";
import { loadEnv, requiredEnv } from "../ui/framework/env.mjs";
import { decodeCbor } from "../ui/framework/cbor-decoder.mjs";

loadEnv(process.env.ENV_FILE || ".env.fat");
const targetPath = process.env.MEMBER_TARGET_FILE || "/tmp/fat-record-flow-target.json";
const target = JSON.parse(fs.readFileSync(targetPath, "utf8"));
const expectedTargetRef = process.env.MEMBER_TARGET_REF || "KYC-RUN-B9CA6D6A0704";
const uidRef = process.env.MEMBER_UID_REF || "UID-REF-26913CC85458";
if (target.environment !== "FAT" || target.target_ref !== expectedTargetRef) throw new Error("unexpected target");
const baseUrl = requiredEnv("ADMIN_URL"), origin = new URL(baseUrl).origin;
const probeOnly = process.env.MEMBER_LIMITATION_PROBE_ONLY === "true";
const limitationLabel = process.env.MEMBER_LIMITATION_LABEL || "Deposit";
const outputSlug = limitationLabel.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
const output = path.resolve(process.env.MEMBER_LIMITATION_OUTPUT || `fat-admin-interface-scan/results/record-flow-member-limitation-${outputSlug}-${probeOnly ? "probe" : "flow"}.json`);
const network = []; let action = "login";
const scrub = (value) => String(value || "").replace(/(?:\+?63|0)9\d{9}|\b\d{7,}\b/g, "<redacted>").replace(/\s+/g, " ").trim().slice(0, 240);
const browser = await chromium.launch({ headless: process.env.ADMIN_SCAN_HEADED === "false" });
const context = await browser.newContext({ ignoreHTTPSErrors: true, viewport: { width: 1440, height: 1000 }, locale: "en-US" });
const page = await context.newPage();

page.on("response", async (response) => {
  const request = response.request(); if (!["xhr", "fetch"].includes(request.resourceType())) return;
  let url; try { url = new URL(response.url()); } catch { return; } if (url.origin !== origin) return;
  let decoded = null, bodyFields = [];
  try { const raw = request.postDataBuffer(); if (raw?.length) { const type = (request.headers()["content-type"] || "").toLowerCase();
    const body = type.includes("json") ? JSON.parse(raw.toString("utf8")) : decodeCbor(new Uint8Array(raw));
    if (body && typeof body === "object" && !Array.isArray(body)) bodyFields = Object.keys(body).sort(); } } catch {}
  try { decoded = decodeCbor(new Uint8Array(await response.body())); } catch {}
  const data = decoded?.data;
  network.push({ action, method: request.method(), path: url.pathname.replace(/\/\d{4,}(?=\/|$)/g, "/{id}"),
    query_fields: [...url.searchParams.keys()].sort(), body_fields: bodyFields, http_status: response.status(),
    business_status: decoded?.status ?? null, response_type: Array.isArray(data) ? "list" : data === null ? "null" : typeof data,
    response_keys: data && typeof data === "object" && !Array.isArray(data) ? Object.keys(data).sort() : [], response_values_persisted: false });
});
async function quiet() { let last=network.length, stable=Date.now(); for(let i=0;i<60;i++){await page.waitForTimeout(100);if(last!==network.length){last=network.length;stable=Date.now();}else if(Date.now()-stable>700)return;} }
async function login() {
  await page.goto(baseUrl,{waitUntil:"domcontentloaded",timeout:30000});
  await page.getByPlaceholder(/请输入用户名|user\s*name|email/i).fill(requiredEnv("ADMIN_EMAIL"));
  await page.getByPlaceholder(/请输入密码|password/i).fill(requiredEnv("ADMIN_PASSWORD")); await page.getByRole("button",{name:/登\s*录|log\s*in/i}).click();
  const code=page.getByPlaceholder(/谷歌验证|google.*(?:code|verification|authenticator)/i);await code.waitFor({state:"visible",timeout:10000});await code.fill(requiredEnv("ADMIN_GOOGLE_CODE"));
  await page.getByRole("button",{name:/确\s*定|confirm|ok/i}).click();await page.waitForURL((url)=>!url.pathname.startsWith("/user/login"),{timeout:20000});
}
async function enterTarget() {
  await page.goto(new URL("/member-center/list",baseUrl).toString(),{waitUntil:"domcontentloaded",timeout:25000});await quiet();
  const phoneItem=page.locator(".ant-form-item").filter({has:page.locator(".ant-form-item-label",{hasText:/^\s*Phone Number\s*$/i})}).first();
  await phoneItem.locator("input").first().fill(String(target.phone));action="target_query";await page.locator("button").filter({hasText:/^\s*Query\s*$/i}).first().click();await quiet();
  const row=page.locator(".ant-table-tbody tr:not(.ant-table-measure-row):visible").filter({hasText:String(target.phone)}).first();await row.waitFor({state:"visible",timeout:15000});
  await row.getByRole("button",{name:"View Details",exact:true}).click();await page.waitForURL((url)=>url.pathname.endsWith(`/member-center/detail/${target.uid}`),{timeout:15000});await quiet();
  const tab=page.locator(".ant-layout-content .ant-tabs-tab").filter({hasText:/^\s*Function Limitation\s*$/}).last();action="limitation_baseline";await tab.click();await quiet();
}
async function rowFor(panel,label) { const rows=panel.locator("tr:visible");for(let index=0;index<await rows.count();index+=1){const row=rows.nth(index);if(scrub(await row.innerText()).toLowerCase().startsWith(label.toLowerCase()))return row;}return null; }

function base32Decode(value) {
  const alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ234567", normalized=value.replace(/\s|=/g,"").toUpperCase(); let bits="";
  for(const char of normalized){const index=alphabet.indexOf(char);if(index<0)throw new Error("invalid approval TOTP secret");bits+=index.toString(2).padStart(5,"0");}
  const bytes=[];for(let i=0;i+8<=bits.length;i+=8)bytes.push(parseInt(bits.slice(i,i+8),2));return Buffer.from(bytes);
}
function currentTotp() {
  const key=base32Decode(requiredEnv("ADMIN_APPROVAL_TOTP_SECRET"));
  const algorithm=(process.env.ADMIN_APPROVAL_TOTP_ALGORITHM||"SHA1").toLowerCase().replace("-","");
  const counter=Math.floor(Date.now()/1000/30), message=Buffer.alloc(8);message.writeBigUInt64BE(BigInt(counter));
  const digest=crypto.createHmac(algorithm,key).update(message).digest(),offset=digest[digest.length-1]&15;
  return String((digest.readUInt32BE(offset)&0x7fffffff)%1000000).padStart(6,"0");
}
async function ensureFreshTotpWindow() {
  const remaining=30-(Math.floor(Date.now()/1000)%30);if(remaining<7)await page.waitForTimeout((remaining+1)*1000);
}
async function submitCurrentModal(reason, actionName) {
  const activeModal=page.locator(".ant-modal:visible,.ant-drawer:visible,[role=dialog]:visible").last();
  await ensureFreshTotpWindow();
  const items=activeModal.locator(".ant-form-item");
  for(let i=0;i<await items.count();i++){
    const item=items.nth(i),label=scrub(await item.locator(".ant-form-item-label").innerText().catch(()=>""));
    const input=item.locator('textarea,input:not([type="radio"]):not([type="checkbox"]):not([type="hidden"]):not([type="file"])').first();if(!await input.isVisible().catch(()=>false))continue;
    await input.fill(/google|verification/i.test(label)?currentTotp():reason);
  }
  const start=network.length;action=actionName;await activeModal.getByRole("button",{name:/^OK$/i,exact:true}).click();await quiet();
  await activeModal.waitFor({state:"hidden",timeout:10000}).catch(()=>{});
  return {network_event_indexes:[start,network.length],events:network.slice(start).map((event)=>({method:event.method,path:event.path,http_status:event.http_status,business_status:event.business_status,body_fields:event.body_fields}))};
}

await login(); await enterTarget();
const limitationPanel=page.locator(".ant-tabs-tabpane-active:visible").last();
const observedRows=(await limitationPanel.locator("tr:visible").allInnerTexts()).map(scrub);
const limitationRow=await rowFor(limitationPanel,limitationLabel);
if(!limitationRow){
  fs.writeFileSync(output,JSON.stringify({captured_at:new Date().toISOString(),environment:"FAT",target_ref:target.target_ref,uid_ref:uidRef,
    operation:`${limitationLabel} Function Limitation`,status:"ROW_NOT_AVAILABLE",observed_rows:observedRows,writes:0,side_effects:[],network},null,2)+"\n");
  await browser.close();console.log(JSON.stringify({operation:`${limitationLabel} Function Limitation`,status:"ROW_NOT_AVAILABLE",observed_rows:observedRows,writes:0}));process.exit(2);
}
const beforeRow=scrub(await limitationRow.innerText());
if(beforeRow.includes("Forbidden")&&!beforeRow.includes("Allowed")){
  fs.writeFileSync(output,JSON.stringify({captured_at:new Date().toISOString(),environment:"FAT",target_ref:target.target_ref,uid_ref:uidRef,
    operation:`${limitationLabel} Function Limitation`,status:"BASELINE_ALREADY_FORBIDDEN",before_row:beforeRow,writes:0,side_effects:[],network},null,2)+"\n");
  await browser.close();console.log(JSON.stringify({operation:`${limitationLabel} Function Limitation`,status:"BASELINE_ALREADY_FORBIDDEN",before_row:beforeRow,writes:0}));process.exit(0);
}
action=`${outputSlug}_limitation_open_lock_form`;await limitationRow.getByRole("button",{name:/\+\s*Lock/i}).click();await page.waitForTimeout(500);
const modal=page.locator(".ant-modal:visible,.ant-drawer:visible,[role=dialog]:visible").last();await modal.waitFor({state:"visible",timeout:5000});
const form={
  text_head:scrub((await modal.innerText()).slice(0,400)),
  fields:await modal.locator(".ant-form-item").evaluateAll((items)=>items.map((item,index)=>({index,label:item.querySelector(".ant-form-item-label")?.innerText.replace(/\s+/g," ").trim()||"",required:Boolean(item.querySelector(".ant-form-item-required")),placeholders:[...item.querySelectorAll("input,textarea")].map((el)=>el.getAttribute("placeholder")||"")}))),
  buttons:(await modal.locator("button:visible").allTextContents()).map(scrub),
};
if (probeOnly) {
  await page.keyboard.press("Escape"); await page.waitForTimeout(250);
  fs.writeFileSync(output,JSON.stringify({captured_at:new Date().toISOString(),environment:"FAT",target_ref:target.target_ref,uid_ref:uidRef,
    operation:`${limitationLabel} Function Limitation`,before_row:beforeRow,form,submitted:false,writes:0,side_effects:[],network},null,2)+"\n");
  await browser.close(); console.log(JSON.stringify({probe:true,before_row:beforeRow,fields:form.fields.length,buttons:form.buttons,writes:0})); process.exit(0);
}

const reason=`interface-discovery-reversible-${outputSlug}`;
const lock=await submitCurrentModal(reason,`${outputSlug}_limitation_lock`);
const lockEvent=lock.events.find((event)=>!["GET","HEAD","OPTIONS"].includes(event.method));
if(!lockEvent||lockEvent.http_status>=400||lockEvent.business_status!==true)throw new Error(`${limitationLabel} limitation lock did not return a successful write response`);
await page.waitForTimeout(500);
const lockedRow=await rowFor(limitationPanel,limitationLabel);if(!lockedRow)throw new Error(`${limitationLabel} row disappeared after lock`);const afterLockRow=scrub(await lockedRow.innerText());
const unlock=lockedRow.getByRole("button",{name:/Unlock/i}).first();await unlock.waitFor({state:"visible",timeout:7000});
action="deposit_limitation_open_unlock_form";await unlock.click();
const unlockModal=page.locator(".ant-modal:visible,.ant-drawer:visible,[role=dialog]:visible").last();await unlockModal.waitFor({state:"visible",timeout:5000});
const restore=await submitCurrentModal(reason,`${outputSlug}_limitation_restore`);
const restoreEvent=restore.events.find((event)=>!["GET","HEAD","OPTIONS"].includes(event.method));
if(!restoreEvent||restoreEvent.http_status>=400||restoreEvent.business_status!==true)throw new Error(`${limitationLabel} limitation restore did not return a successful write response`);
await page.waitForTimeout(500);
const restoredLocator=await rowFor(limitationPanel,limitationLabel);if(!restoredLocator)throw new Error(`${limitationLabel} row disappeared after restore`);const restoredRow=scrub(await restoredLocator.innerText());
const restored=restoredRow.includes("Allowed")&&restoredRow.includes("Lock")&&!restoredRow.includes("Unlock");
if(!restored)throw new Error("deposit limitation UI did not return to baseline");
fs.writeFileSync(output,JSON.stringify({captured_at:new Date().toISOString(),environment:"FAT",target_ref:target.target_ref,uid_ref:uidRef,
  operation:`${limitationLabel} Function Limitation`,before_row:beforeRow,lock:{...lock,after_row:afterLockRow},restore:{...restore,restored_row:restoredRow},
  restored,side_effect:`temporary ${limitationLabel} limitation; restored to original Allowed state`,raw_uid_persisted:false,raw_phone_persisted:false,network},null,2)+"\n");
await browser.close();console.log(JSON.stringify({operation:`${limitationLabel} Function Limitation`,lock_path:lockEvent.path,lock_success:true,after_lock:afterLockRow,
  restore_path:restoreEvent.path,restore_success:true,restored_row:restoredRow,restored,writes:2}));
