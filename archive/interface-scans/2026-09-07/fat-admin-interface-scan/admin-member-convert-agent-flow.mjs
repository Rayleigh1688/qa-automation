import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";
import { loadEnv, requiredEnv } from "../ui/framework/env.mjs";
import { decodeCbor } from "../ui/framework/cbor-decoder.mjs";

loadEnv(process.env.ENV_FILE || ".env.fat");
const target = JSON.parse(fs.readFileSync(process.env.MEMBER_TARGET_FILE || "/tmp/fat-member-lane-terminal.json", "utf8"));
if (target.environment !== "FAT" || target.target_ref !== "FAT-MEMBER-END-01") throw new Error("unexpected terminal target");
const output = path.resolve("fat-admin-interface-scan/results/record-flow-member-convert-agent.json");
const baseUrl = requiredEnv("ADMIN_URL"), origin = new URL(baseUrl).origin;
const network = []; let action = "login";
const browser = await chromium.launch({ headless: process.env.ADMIN_SCAN_HEADED === "false" });
const context = await browser.newContext({ ignoreHTTPSErrors: true, viewport: { width: 1440, height: 1000 }, locale: "en-US" });
const page = await context.newPage();

page.on("response", async response => {
  const request=response.request(); if(!["xhr","fetch"].includes(request.resourceType()))return;
  let url; try{url=new URL(response.url());}catch{return;} if(url.origin!==origin)return;
  let decoded=null,bodyFields=[]; try{const raw=request.postDataBuffer();if(raw?.length){const type=(request.headers()["content-type"]||"").toLowerCase();const body=type.includes("json")?JSON.parse(raw.toString("utf8")):decodeCbor(new Uint8Array(raw));if(body&&typeof body==="object"&&!Array.isArray(body))bodyFields=Object.keys(body).sort();}}catch{}
  try{decoded=decodeCbor(new Uint8Array(await response.body()));}catch{}
  network.push({action,method:request.method(),path:url.pathname,body_fields:bodyFields,http_status:response.status(),business_status:decoded?.status??null,response_values_persisted:false});
});
async function quiet(){let last=network.length,stable=Date.now();for(let i=0;i<60;i+=1){await page.waitForTimeout(100);if(last!==network.length){last=network.length;stable=Date.now();}else if(Date.now()-stable>700)return;}}
function base32Decode(value){const alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ234567",normalized=value.replace(/\s|=/g,"").toUpperCase();let bits="";for(const char of normalized){const index=alphabet.indexOf(char);if(index<0)throw new Error("invalid approval TOTP secret");bits+=index.toString(2).padStart(5,"0");}const bytes=[];for(let i=0;i+8<=bits.length;i+=8)bytes.push(parseInt(bits.slice(i,i+8),2));return Buffer.from(bytes);}
function currentTotp(){const key=base32Decode(requiredEnv("ADMIN_APPROVAL_TOTP_SECRET"));const algorithm=(process.env.ADMIN_APPROVAL_TOTP_ALGORITHM||"SHA1").toLowerCase().replace("-","");const counter=Math.floor(Date.now()/1000/30),message=Buffer.alloc(8);message.writeBigUInt64BE(BigInt(counter));const digest=crypto.createHmac(algorithm,key).update(message).digest(),offset=digest[digest.length-1]&15;return String((digest.readUInt32BE(offset)&0x7fffffff)%1000000).padStart(6,"0");}
async function freshTotp(){const remaining=30-(Math.floor(Date.now()/1000)%30);if(remaining<7)await page.waitForTimeout((remaining+1)*1000);return currentTotp();}
async function login(){await page.goto(baseUrl,{waitUntil:"domcontentloaded",timeout:30000});await page.getByPlaceholder(/请输入用户名|user\s*name|email/i).fill(requiredEnv("ADMIN_EMAIL"));await page.getByPlaceholder(/请输入密码|password/i).fill(requiredEnv("ADMIN_PASSWORD"));await page.getByRole("button",{name:/登\s*录|log\s*in/i}).click();const code=page.getByPlaceholder(/谷歌验证|google.*(?:code|verification|authenticator)/i);await code.waitFor({state:"visible",timeout:10000});await code.fill(requiredEnv("ADMIN_GOOGLE_CODE"));await page.getByRole("button",{name:/确\s*定|confirm|ok/i}).click();await page.waitForURL(url=>!url.pathname.startsWith("/user/login"),{timeout:20000});}
async function queryRow(){await page.goto(new URL("/member-center/list",baseUrl).toString(),{waitUntil:"domcontentloaded",timeout:25000});await quiet();const item=page.locator(".ant-form-item").filter({has:page.locator(".ant-form-item-label",{hasText:/^\s*Phone Number\s*$/i})}).first();await item.locator("input").first().fill(String(target.phone));action="query_target";await page.locator("button").filter({hasText:/^\s*Query\s*$/i}).first().click();await quiet();const row=page.locator(".ant-table-tbody tr:not(.ant-table-measure-row):visible").filter({hasText:String(target.phone)}).first();await row.waitFor({state:"visible",timeout:15000});return row;}

try {
  await login(); let row=await queryRow();
  const control=row.getByRole("button",{name:"Convert to Agent",exact:true}).first();
  const before={is_agent:false,convert_control_present:await control.count()>0};
  if(!before.convert_control_present||await control.isDisabled())throw new Error("Convert to Agent is unavailable");
  action="open_convert_to_agent"; await control.click();
  const modal=page.locator(".ant-modal:visible,.ant-drawer:visible,[role=dialog]:visible").last(); await modal.waitFor({state:"visible",timeout:8000});
  const verification=modal.getByPlaceholder(/Google Verification Code/i).first(); await verification.fill(await freshTotp());
  const beforeNetwork=network.length; action="convert_to_agent"; await modal.getByRole("button",{name:/Submit Operation/i}).click(); await quiet();
  const events=network.slice(beforeNetwork),write=events.find(event=>!["GET","HEAD","OPTIONS"].includes(event.method));
  const submitted={method:write?.method||null,path:write?.path||null,body_fields:write?.body_fields||[],http_status:write?.http_status??null,business_status:write?.business_status??null};
  if(!write||write.http_status>=400||write.business_status!==true)throw new Error("Convert to Agent did not return a successful write");
  await page.waitForTimeout(2500); row=await queryRow();
  const after={convert_control_present:await row.getByRole("button",{name:"Convert to Agent",exact:true}).count()>0};
  fs.writeFileSync(output,`${JSON.stringify({captured_at:new Date().toISOString(),environment:"FAT",target_ref:target.target_ref,uid_ref:"FAT-UID-END-01",before,submitted,after,side_effect:"member converted to agent; terminal test lane",raw_phone_or_uid_persisted:false,network},null,2)}\n`);
  console.log(JSON.stringify({target_ref:target.target_ref,path:submitted.path,fields:submitted.body_fields,http_status:submitted.http_status,business_status:submitted.business_status,convert_control_present_after:after.convert_control_present}));
} finally { await browser.close(); }
