import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";
import { loadEnv, requiredEnv } from "../ui/framework/env.mjs";
import { decodeCbor } from "../ui/framework/cbor-decoder.mjs";

loadEnv(process.env.ENV_FILE || ".env.fat");
const targetPath = process.env.MEMBER_TARGET_FILE || "/tmp/fat-member-lane-reversible.json";
const target = JSON.parse(fs.readFileSync(targetPath, "utf8"));
if (target.environment !== "FAT" || target.target_ref !== "FAT-MEMBER-REV-01") throw new Error("unexpected reversible target");
const output = path.resolve("fat-admin-interface-scan/results/record-flow-member-risk-control-flow.json");
const baseUrl = requiredEnv("ADMIN_URL"), origin = new URL(baseUrl).origin;
let prior = null;
try {
  const saved = JSON.parse(fs.readFileSync(output, "utf8"));
  if (saved.target_ref === target.target_ref && saved.unrestored_side_effects === 1) prior = saved;
} catch {}
const network = prior?.network || []; let action = "login";
let report = prior || {
  captured_at: new Date().toISOString(), environment: "FAT", target_ref: target.target_ref,
  uid_ref: "FAT-UID-REV-01", before: null, block: null, after_block: null,
  restore: null, restored: null, unrestored_side_effects: null,
  raw_phone_or_uid_persisted: false, network,
};
function checkpoint() {
  report.captured_at = new Date().toISOString();
  fs.writeFileSync(output, `${JSON.stringify(report, null, 2)}\n`);
}
const browser = await chromium.launch({ headless: process.env.ADMIN_SCAN_HEADED === "false" });
const context = await browser.newContext({ ignoreHTTPSErrors: true, viewport: { width: 1440, height: 1000 }, locale: "en-US" });
const page = await context.newPage();

page.on("response", async (response) => {
  const request=response.request(); if(!["xhr","fetch"].includes(request.resourceType()))return;
  let url;try{url=new URL(response.url());}catch{return;}if(url.origin!==origin)return;
  let decoded=null,bodyFields=[];try{const raw=request.postDataBuffer();if(raw?.length){const type=(request.headers()["content-type"]||"").toLowerCase();const body=type.includes("json")?JSON.parse(raw.toString("utf8")):decodeCbor(new Uint8Array(raw));if(body&&typeof body==="object"&&!Array.isArray(body))bodyFields=Object.keys(body).sort();}}catch{}
  try{decoded=decodeCbor(new Uint8Array(await response.body()));}catch{}
  network.push({action,method:request.method(),path:url.pathname,body_fields:bodyFields,http_status:response.status(),business_status:decoded?.status??null,response_values_persisted:false});
});
async function quiet(){let last=network.length,stable=Date.now();for(let i=0;i<60;i+=1){await page.waitForTimeout(100);if(last!==network.length){last=network.length;stable=Date.now();}else if(Date.now()-stable>700)return;}}
function base32Decode(value){const alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ234567",normalized=value.replace(/\s|=/g,"").toUpperCase();let bits="";for(const char of normalized){const index=alphabet.indexOf(char);if(index<0)throw new Error("invalid approval TOTP secret");bits+=index.toString(2).padStart(5,"0");}const bytes=[];for(let i=0;i+8<=bits.length;i+=8)bytes.push(parseInt(bits.slice(i,i+8),2));return Buffer.from(bytes);}
function currentTotp(){const key=base32Decode(requiredEnv("ADMIN_APPROVAL_TOTP_SECRET"));const algorithm=(process.env.ADMIN_APPROVAL_TOTP_ALGORITHM||"SHA1").toLowerCase().replace("-","");const counter=Math.floor(Date.now()/1000/30),message=Buffer.alloc(8);message.writeBigUInt64BE(BigInt(counter));const digest=crypto.createHmac(algorithm,key).update(message).digest(),offset=digest[digest.length-1]&15;return String((digest.readUInt32BE(offset)&0x7fffffff)%1000000).padStart(6,"0");}
async function freshTotp(){const remaining=30-(Math.floor(Date.now()/1000)%30);if(remaining<7)await page.waitForTimeout((remaining+1)*1000);return currentTotp();}
async function login(){await page.goto(baseUrl,{waitUntil:"domcontentloaded",timeout:30000});await page.getByPlaceholder(/请输入用户名|user\s*name|email/i).fill(requiredEnv("ADMIN_EMAIL"));await page.getByPlaceholder(/请输入密码|password/i).fill(requiredEnv("ADMIN_PASSWORD"));await page.getByRole("button",{name:/登\s*录|log\s*in/i}).click();const code=page.getByPlaceholder(/谷歌验证|google.*(?:code|verification|authenticator)/i);await code.waitFor({state:"visible",timeout:10000});await code.fill(requiredEnv("ADMIN_GOOGLE_CODE"));await page.getByRole("button",{name:/确\s*定|confirm|ok/i}).click();await page.waitForURL((url)=>!url.pathname.startsWith("/user/login"),{timeout:20000});}
async function queryRow(){await page.goto(new URL("/member-center/list",baseUrl).toString(),{waitUntil:"domcontentloaded",timeout:25000});await quiet();const item=page.locator(".ant-form-item").filter({has:page.locator(".ant-form-item-label",{hasText:/^\s*Phone Number\s*$/i})}).first();await item.locator("input").first().fill(String(target.phone));action="query_target";await page.locator("button").filter({hasText:/^\s*Query\s*$/i}).first().click();await quiet();const row=page.locator(".ant-table-tbody tr:not(.ant-table-measure-row):visible").filter({hasText:String(target.phone)}).first();await row.waitFor({state:"visible",timeout:15000});return row;}
async function submitModal(actionName,reason){const modal=page.locator(".ant-modal:visible,.ant-drawer:visible,[role=dialog]:visible").last();await modal.waitFor({state:"visible",timeout:7000});const items=modal.locator(".ant-form-item");for(let i=0;i<await items.count();i+=1){const item=items.nth(i),label=(await item.locator(".ant-form-item-label").innerText().catch(()=>"")).replace(/\s+/g," ").trim();const input=item.locator('textarea,input:not([type="radio"]):not([type="checkbox"]):not([type="hidden"])').first();if(!await input.isVisible().catch(()=>false))continue;await input.fill(/google|verification/i.test(label)?await freshTotp():reason);}const before=network.length;action=actionName;const submit=modal.getByRole("button",{name:/Submit Verification|^OK$|Confirm/i}).last();await submit.click();await quiet();await modal.waitFor({state:"hidden",timeout:10000}).catch(()=>{});const events=network.slice(before);const write=events.find((event)=>!["GET","HEAD","OPTIONS"].includes(event.method));if(!write||write.http_status>=400||write.business_status!==true)throw new Error(`${actionName} did not return a successful write`);return {write:{method:write.method,path:write.path,http_status:write.http_status,business_status:write.business_status,body_fields:write.body_fields}};}

try{
  await login();let row=await queryRow();
  const risk=row.getByRole("button",{name:"Risk Control",exact:true}).first(),unrisk=row.getByRole("button",{name:"Unrisk Control",exact:true}).first();
  const before={risk_control_present:await risk.count()>0,unrisk_control_present:await unrisk.count()>0};
  report.before=before; checkpoint();
  let block=null,recoveryFromPriorFailure=false;
  if(before.unrisk_control_present){recoveryFromPriorFailure=true;}
  else{
    if(!before.risk_control_present)throw new Error("neither Risk Control nor Unrisk Control is available");
    action="open_risk_control";await risk.click();
    block=await submitModal("risk_control_block","interface discovery reversible block");
    report.block=block; report.unrestored_side_effects=1; checkpoint();
    const started=Date.now();
    do {
      row=await queryRow();
      if(await row.getByRole("button",{name:"Unrisk Control",exact:true}).count()>0)break;
      await page.waitForTimeout(1500);
    } while(Date.now()-started<30000);
    if(await row.getByRole("button",{name:"Unrisk Control",exact:true}).count()===0)throw new Error("Unrisk Control did not appear after Risk Control");
  }
  const afterBlock={unrisk_control_present:await row.getByRole("button",{name:"Unrisk Control",exact:true}).count()>0};
  report.after_block=afterBlock; checkpoint();
  action="open_unrisk_control";await row.getByRole("button",{name:"Unrisk Control",exact:true}).click();
  const restore=await submitModal("risk_control_restore","interface discovery restore");
  report.restore=restore; checkpoint();
  let restored={risk_control_present:false,unrisk_control_present:true,observed_after_ms:0};
  const started=Date.now();
  while(Date.now()-started<30000){
    row=await queryRow();
    restored={
      risk_control_present:await row.getByRole("button",{name:"Risk Control",exact:true}).count()>0,
      unrisk_control_present:await row.getByRole("button",{name:"Unrisk Control",exact:true}).count()>0,
      observed_after_ms:Date.now()-started,
    };
    if(restored.risk_control_present&&!restored.unrisk_control_present)break;
    await page.waitForTimeout(1500);
  }
  if(!restored.risk_control_present||restored.unrisk_control_present)throw new Error("member did not return to Risk Control baseline");
  report.restored=restored; report.unrestored_side_effects=0; checkpoint();
  console.log(JSON.stringify({target_ref:target.target_ref,recovery_from_prior_failure:recoveryFromPriorFailure,block_path:block?.write.path||null,block_success:block?true:null,restore_path:restore.write.path,restore_success:true,restored:true,writes:block?2:1}));
}finally{await browser.close();}
