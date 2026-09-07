import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { chromium } from "playwright";
import { loadEnv, requiredEnv } from "../ui/framework/env.mjs";
import { decodeCbor } from "../ui/framework/cbor-decoder.mjs";

loadEnv(process.env.ENV_FILE || ".env.fat");
const baseUrl=requiredEnv("ADMIN_URL"),origin=new URL(baseUrl).origin,route="/promo-marketing/channels";
const runId=`codex-fat-scan-${new Date().toISOString().slice(0,10).replaceAll("-","")}-${crypto.randomBytes(3).toString("hex")}`;
const updatedName=`${runId}-edited`;
const sanitize=(v)=>String(v??"").replace(/\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi,"<redacted-email>").replace(/(?<!\d)(?:\+?63|0)9\d{9}(?!\d)/g,"<redacted-phone>").replace(/(?<!\d)\d{9,}(?!\d)/g,"<redacted-member-id>").trim();
const browser=await chromium.launch({headless:process.env.ADMIN_SCAN_HEADED==="false"});
const context=await browser.newContext({ignoreHTTPSErrors:true,viewport:{width:1440,height:1000},locale:"en-US"});
const page=await context.newPage(),network=[];
let action="login",createdId="";
page.on("response",async response=>{
 const req=response.request();if(!["xhr","fetch"].includes(req.resourceType()))return;const url=new URL(response.url());if(url.origin!==origin)return;
 let decoded=null,bodyFields=[];try{const raw=req.postDataBuffer();if(raw?.length){const type=(req.headers()["content-type"]||"").toLowerCase();const b=type.includes("json")?JSON.parse(raw.toString()):decodeCbor(new Uint8Array(raw));if(b&&typeof b==="object")bodyFields=Object.keys(b).sort();}}catch{}
 try{decoded=decodeCbor(new Uint8Array(await response.body()));}catch{}
 if(action==="create channel group"&&decoded?.status===true){const d=decoded.data;if(typeof d==="string"||typeof d==="number")createdId=sanitize(d);else if(d&&typeof d==="object")createdId=sanitize(d.id||d.group_id||d.groupId||"");}
 network.push({action,method:req.method(),path:url.pathname.replace(/\/\d{6,}(?=\/|$)/g,"/{id}"),query_fields:[...url.searchParams.keys()].sort(),body_fields:bodyFields,http_status:response.status(),business_status:decoded?.status??null,response_type:Array.isArray(decoded?.data)?"list":typeof decoded?.data,response_keys:decoded?.data&&typeof decoded.data==="object"&&!Array.isArray(decoded.data)?Object.keys(decoded.data).sort():[]});
});
async function login(){await page.goto(baseUrl,{waitUntil:"domcontentloaded"});await page.getByPlaceholder(/请输入用户名|user\s*name|email/i).fill(requiredEnv("ADMIN_EMAIL"));await page.getByPlaceholder(/请输入密码|password/i).fill(requiredEnv("ADMIN_PASSWORD"));await page.getByRole("button",{name:/登\s*录|log\s*in/i}).click();const v=page.getByPlaceholder(/谷歌验证|google.*(?:code|verification|authenticator)/i);await v.waitFor({state:"visible"});await v.fill(requiredEnv("ADMIN_GOOGLE_CODE"));await page.getByRole("button",{name:/确\s*定|confirm|ok/i}).click();await page.waitForURL(u=>!u.pathname.startsWith("/user/login"));}
const result={captured_at:"",environment:"FAT",page:"Channel Management",route,target_type:"promotion group",target_id:"",test_name:runId,before_state:"absent by unique generated name",steps:[],after_state:"",cleanup:"",network};
await login();action="before state";await page.goto(new URL(route,baseUrl).toString(),{waitUntil:"domcontentloaded"});await page.waitForTimeout(1500);
const beforeCount=await page.getByText(runId,{exact:true}).count();result.steps.push({action:"before state",status:beforeCount===0?"PASS_ABSENT":"FAILED_ALREADY_EXISTS",visible_count:beforeCount});
if(beforeCount===0){
 const add=page.getByRole("button",{name:"Add",exact:true}).first();
 if(await add.isVisible().catch(()=>false)){
  action="open create channel group";await add.click();const dialog=page.getByRole("dialog").last();await dialog.waitFor({state:"visible"});
  await dialog.getByPlaceholder("Please enter",{exact:true}).fill(runId);
  action="create channel group";const start=network.length;await dialog.getByRole("button",{name:"Confirm",exact:true}).click();await page.waitForTimeout(1200);
  const events=network.slice(start);const createEvents=events.filter(e=>e.path!=="/admin/game/search");const ok=createEvents.some(e=>e.http_status>=200&&e.http_status<300&&e.business_status!==false);
  result.steps.push({action:"create",status:ok?"PASS":"NO_CREATE_REQUEST",target_id:createdId,endpoint_keys:[...new Set(createEvents.map(e=>`${e.method} ${e.path}`))],ignored_delayed_initialization_events:events.length-createEvents.length});
  if(ok){
   action="verify created state";await page.waitForTimeout(800);const visible=await page.getByText(runId,{exact:true}).count();
   const target=page.getByText(runId,{exact:true}).first();const row=target.locator("xpath=ancestor::tr[1]");const rowText=await row.count()?sanitize(await row.innerText()):"";
   const rowButtons=await row.count()?await row.getByRole("button").allInnerTexts():[];
   result.steps.push({action:"verify create",status:visible?"PASS_VISIBLE":"CREATED_NOT_VISIBLE",visible_count:visible,row_actions:rowButtons.map(sanitize),row_summary:rowText.slice(0,300)});
   if(await row.count()){
    const edit=row.getByRole("button",{name:"Edit",exact:true}).first();
    if(await edit.isVisible().catch(()=>false)){
     action="open edit current-run group";await edit.click();const editDialog=page.getByRole("dialog").last();await editDialog.getByPlaceholder("Please enter",{exact:true}).fill(updatedName);action="edit current-run group";const editStart=network.length;await editDialog.getByRole("button",{name:"Confirm",exact:true}).click();await page.waitForTimeout(1000);const editEvents=network.slice(editStart);result.steps.push({action:"edit",status:editEvents.some(e=>e.business_status!==false&&e.http_status<300)?"PASS":"FAILED",endpoint_keys:[...new Set(editEvents.map(e=>`${e.method} ${e.path}`))]});
    }
    const updatedTarget=page.getByText(updatedName,{exact:true}).first();const updatedRow=updatedTarget.locator("xpath=ancestor::tr[1]");const del=updatedRow.getByRole("button",{name:"Delete",exact:true}).first();
    if(await del.isVisible().catch(()=>false)){
     action="open delete current-run group";await del.click();const confirm=page.getByRole("button",{name:/^(Confirm|OK|Yes)$/i}).last();action="delete current-run group";const deleteStart=network.length;await confirm.click();await page.waitForTimeout(1000);const deleteEvents=network.slice(deleteStart);result.steps.push({action:"delete",status:deleteEvents.some(e=>e.business_status!==false&&e.http_status<300)?"PASS":"FAILED",endpoint_keys:[...new Set(deleteEvents.map(e=>`${e.method} ${e.path}`))]});result.cleanup="delete attempted";
    }else result.cleanup="BLOCKED_DELETE_CONTROL_NOT_FOUND";
   }else result.cleanup="BLOCKED_TARGET_ROW_NOT_FOUND";
  }
 }
}
result.target_id=createdId;result.after_state=await page.getByText(updatedName,{exact:true}).count()?"edited record remains visible":await page.getByText(runId,{exact:true}).count()?"created record remains visible":"target not visible after flow";result.captured_at=new Date().toISOString();
fs.writeFileSync(path.resolve("fat-admin-interface-scan/results/fat-admin-controlled-channel-group-flow.json"),JSON.stringify(result,null,2)+"\n");
console.log(`[flow] ${result.steps.map(x=>`${x.action}:${x.status}`).join(" ")} target_id=${createdId||"not-returned"} cleanup=${result.cleanup}`);
await browser.close();
