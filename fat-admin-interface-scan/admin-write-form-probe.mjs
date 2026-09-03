import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";
import { loadEnv, requiredEnv } from "../ui/framework/env.mjs";
import { decodeCbor } from "../ui/framework/cbor-decoder.mjs";

loadEnv(process.env.ENV_FILE || ".env.fat");
const baseUrl = requiredEnv("ADMIN_URL"), origin = new URL(baseUrl).origin;
const cases = [
  { page: "Material Management", route: "/operations/material-management", action: "Add" },
  { page: "Marquee Management", route: "/operations/marquee-management", action: "Add Marquee" },
  { page: "Channel Management", route: "/promo-marketing/channels", action: "Add" },
  { page: "Recharge Template", route: "/operations/recharge-template", action: "Add Template" },
  { page: "Role Configuration", route: "/system/role", action: "Add New" },
  { page: "Whitelist", route: "/whitelist/list", action: "Add IP Pool" },
];
const sanitize = (value) => String(value ?? "").replace(/\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi,"<redacted-email>").replace(/(?<!\d)(?:\+?63|0)9\d{9}(?!\d)/g,"<redacted-phone>").replace(/(?<!\d)\d{6,}(?!\d)/g,"<redacted-numeric-id>").trim();
const browser = await chromium.launch({ headless: process.env.ADMIN_SCAN_HEADED === "false" });
const context = await browser.newContext({ ignoreHTTPSErrors: true, viewport: { width: 1440, height: 1000 }, locale: "en-US" });
const page = await context.newPage(), network = [], probes = [];
let current = "login";
page.on("response", async (response) => {
  const req=response.request(); if(!["xhr","fetch"].includes(req.resourceType()))return;
  const url=new URL(response.url()); if(url.origin!==origin)return;
  let business=null,keys=[]; try{const d=decodeCbor(new Uint8Array(await response.body()));business=d?.status??null;keys=d?.data&&typeof d.data==="object"&&!Array.isArray(d.data)?Object.keys(d.data).sort():[];}catch{}
  network.push({action:current,method:req.method(),path:url.pathname.replace(/\/\d{6,}(?=\/|$)/g,"/{id}"),query_fields:[...url.searchParams.keys()].sort(),http_status:response.status(),business_status:business,response_data_keys:keys});
});
async function login(){await page.goto(baseUrl,{waitUntil:"domcontentloaded"});await page.getByPlaceholder(/请输入用户名|user\s*name|email/i).fill(requiredEnv("ADMIN_EMAIL"));await page.getByPlaceholder(/请输入密码|password/i).fill(requiredEnv("ADMIN_PASSWORD"));await page.getByRole("button",{name:/登\s*录|log\s*in/i}).click();const v=page.getByPlaceholder(/谷歌验证|google.*(?:code|verification|authenticator)/i);await v.waitFor({state:"visible"});await v.fill(requiredEnv("ADMIN_GOOGLE_CODE"));await page.getByRole("button",{name:/确\s*定|confirm|ok/i}).click();await page.waitForURL(u=>!u.pathname.startsWith("/user/login"));}
await login();
for(const item of cases){
  current=`prepare ${item.page}`;await page.goto(new URL(item.route,baseUrl).toString(),{waitUntil:"domcontentloaded"});await page.waitForTimeout(1500);
  let button=page.getByRole("button",{name:item.action,exact:true}).first();let status="OPENED",error="";
  if(!await button.isVisible().catch(()=>false)){
    const escaped=item.action.replace(/[.*+?^${}()|[\]\\]/g,"\\$&");
    button=page.locator("button").filter({hasText:new RegExp(`^\\s*${escaped}\\s*$`)}).first();
  }
  try{if(!await button.isVisible())status="SKIPPED";else{current=`${item.page} :: ${item.action}`;await button.click({timeout:3000});await page.waitForTimeout(700);}}catch(e){status="ERROR";error=sanitize(e);}
  const dialog=page.locator("[role='dialog']:visible, .ant-modal:visible, .ant-drawer:visible").last();
  const controls=await dialog.count()?await dialog.evaluate(node=>({
    text:(node.querySelector(".ant-modal-title,.ant-drawer-title")?.textContent||"").trim(),
    inputs:Array.from(node.querySelectorAll("input,textarea")).map(x=>({type:x.type||x.tagName.toLowerCase(),name:x.name||"",placeholder:x.placeholder||""})),
    selects:Array.from(node.querySelectorAll(".ant-select")).map(x=>(x.textContent||"").trim()),
    buttons:Array.from(node.querySelectorAll("button")).map(x=>(x.innerText||x.textContent||"").trim()).filter(Boolean),
    labels:Array.from(node.querySelectorAll("label,.ant-form-item-label")).map(x=>(x.textContent||"").trim()).filter(Boolean),
  })):{};
  probes.push({page:item.page,route:item.route,action:item.action,status,controls:JSON.parse(JSON.stringify(controls),(k,v)=>typeof v==="string"?sanitize(v):v),error});
  console.log(`[probe] ${item.page} ${status} fields=${controls.inputs?.length||0} selects=${controls.selects?.length||0}`);
}
fs.writeFileSync(path.resolve("fat-admin-interface-scan/results/fat-admin-write-form-probes.json"),JSON.stringify({captured_at:new Date().toISOString(),environment:"FAT",probes,network},null,2)+"\n");
await browser.close();
