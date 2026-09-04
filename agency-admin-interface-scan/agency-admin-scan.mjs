import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { execFileSync } from "node:child_process";
import { chromium } from "playwright";
import { decodeCbor } from "../ui/framework/cbor-decoder.mjs";

const baseUrl = process.env.AGENCY_ADMIN_URL || "https://admin-agency-fat.filbet2025.com/";
const origin = new URL(baseUrl).origin;
const email = process.env.AGENCY_ADMIN_EMAIL;
const password = process.env.AGENCY_ADMIN_PASSWORD;
if (!email || !password) throw new Error("AGENCY_ADMIN_EMAIL and AGENCY_ADMIN_PASSWORD are required");
const outDir = path.resolve("agency-admin-interface-scan/results");
fs.mkdirSync(outDir, { recursive: true });

const sanitize = (value) => String(value ?? "")
  .replace(/\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi, "<redacted-email>")
  .replace(/(?<!\d)(?:\+?63|0)9\d{9}(?!\d)/g, "<redacted-phone>")
  .replace(/\bfilbet_[A-Z0-9]+\b/gi, "<redacted-account>")
  .replace(/(?<!\d)\d{6,}(?!\d)/g, "<redacted-numeric-id>")
  .replace(/[A-F0-9]{24,}/gi, "<redacted-secret-like>")
  .trim();
const safeText = (value) => sanitize(value).slice(0, 160);

function currentTotp() {
  const qr = path.resolve("agency-admin-QR.png");
  const raw = execFileSync("zbarimg", ["--quiet", "--raw", qr], { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }).trim();
  const parsed = new URL(raw);
  if (parsed.protocol !== "otpauth:" || parsed.hostname !== "totp") throw new Error("QR is not an otpauth TOTP URI");
  const secretText = (parsed.searchParams.get("secret") || "").toUpperCase().replace(/=+$/, "");
  if (!secretText) throw new Error("TOTP secret is missing");
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  let bits = "";
  for (const char of secretText) {
    const value = alphabet.indexOf(char);
    if (value < 0) throw new Error("Unsupported Base32 character");
    bits += value.toString(2).padStart(5, "0");
  }
  const bytes = [];
  for (let i = 0; i + 8 <= bits.length; i += 8) bytes.push(parseInt(bits.slice(i, i + 8), 2));
  const algorithm = (parsed.searchParams.get("algorithm") || "SHA1").toLowerCase().replace("sha", "sha");
  const digits = Number(parsed.searchParams.get("digits") || 6);
  const period = Number(parsed.searchParams.get("period") || 30);
  const counter = BigInt(Math.floor(Date.now() / 1000 / period));
  const message = Buffer.alloc(8); message.writeBigUInt64BE(counter);
  const digest = crypto.createHmac(algorithm, Buffer.from(bytes)).update(message).digest();
  const offset = digest[digest.length - 1] & 15;
  const binary = ((digest[offset] & 127) << 24) | ((digest[offset + 1] & 255) << 16) | ((digest[offset + 2] & 255) << 8) | (digest[offset + 3] & 255);
  return String(binary % (10 ** digits)).padStart(digits, "0");
}

const browser = await chromium.launch({ headless: process.env.AGENCY_SCAN_HEADED !== "true" });
const context = await browser.newContext({ ignoreHTTPSErrors: true, acceptDownloads: true, viewport: { width: 1440, height: 1000 }, locale: "en-US" });
const page = await context.newPage();
let currentRoute = "login";
let currentAction = "login flow";
const network = [];
const loginEvidence = [];

page.on("response", async (response) => {
  const request = response.request();
  if (!["xhr", "fetch"].includes(request.resourceType())) return;
  let url; try { url = new URL(response.url()); } catch { return; }
  if (url.origin !== origin) return;
  const event = { route: currentRoute, action: currentAction, method: request.method(), path: url.pathname,
    query_fields: [...url.searchParams.keys()].sort(), body_fields: [], http_status: response.status(), business_status: null,
    response_data_type: "unknown", response_data_keys: [] };
  try {
    const raw = request.postDataBuffer();
    if (raw?.length) {
      const type = (request.headers()["content-type"] || "").toLowerCase();
      const body = type.includes("json") ? JSON.parse(raw.toString("utf8")) : decodeCbor(new Uint8Array(raw));
      if (body && typeof body === "object" && !Array.isArray(body)) event.body_fields = Object.keys(body).sort();
    }
  } catch {}
  try {
    const decoded = decodeCbor(new Uint8Array(await response.body()));
    if (decoded && typeof decoded === "object" && !Array.isArray(decoded)) {
      event.business_status = decoded.status ?? null;
      const data = decoded.data;
      event.response_data_type = data === null ? "null" : Array.isArray(data) ? "list" : typeof data;
      if (data && typeof data === "object" && !Array.isArray(data)) event.response_data_keys = Object.keys(data).sort();
    }
  } catch {}
  network.push(event);
  if (currentRoute === "login") loginEvidence.push(event);
});

async function login() {
  await page.goto(baseUrl, { waitUntil: "domcontentloaded", timeout: 30000 });
  const user = page.getByPlaceholder(/user\s*name|email|用户名|账号/i).first();
  const pass = page.getByPlaceholder(/password|密码/i).first();
  await user.waitFor({ state: "visible", timeout: 15000 });
  await user.fill(email); await pass.fill(password);
  await page.getByRole("button", { name: /log\s*in|登录/i }).first().click();
  const dialog = page.locator(".ant-modal:visible,[role=dialog]:visible").last();
  await dialog.waitFor({ state: "visible", timeout: 10000 });
  let otp = dialog.locator("input:visible").last();
  if (!await otp.isVisible().catch(() => false)) otp = page.locator("input:visible").filter({ hasNot: page.locator("[type=password]") }).last();
  await otp.fill(currentTotp());
  let confirm = dialog.getByRole("button", { name: /confirm|ok|确定|提交|verify/i }).last();
  if (!await confirm.isVisible().catch(() => false)) confirm = dialog.locator("button.ant-btn-primary:visible").last();
  await confirm.click();
  await page.waitForURL((url) => url.origin === origin && !/login/i.test(url.pathname), { timeout: 25000 });
  await page.waitForTimeout(2000);
  const body = safeText(await page.locator("body").innerText());
  const menus = await page.locator(".ant-layout-sider .ant-menu-item, aside .ant-menu-item").count();
  const loginPost = loginEvidence.find((x) => x.method === "POST" && x.path === "/backend/agency/login" && x.http_status === 200 && x.business_status === true);
  const meDetail = loginEvidence.find((x) => x.method === "GET" && x.path === "/backend/agency/me/detail" && x.http_status === 200 && x.business_status === true);
  if (page.url().startsWith(origin) === false || /login/i.test(new URL(page.url()).pathname) || menus === 0 || !loginPost || !meDetail) throw new Error("Login success gate failed: required login/me evidence missing");
  return { success: true, origin: new URL(page.url()).origin, pathname: new URL(page.url()).pathname, title: safeText(await page.title()), rendered_menu_items: menus,
    required_request_evidence: ["POST /backend/agency/login:200:true", "GET /backend/agency/me/detail:200:true"],
    identity_or_permission_evidence: network.filter((x) => /(?:me|priv|permission|profile|detail)/i.test(x.path)).map((x) => `${x.method} ${x.path}:${x.http_status}:${x.business_status}`).slice(0, 10), body_shell_present: body.length > 0 };
}

async function discoverMenu() {
  const side = page.locator(".ant-layout-sider, aside").first();
  const titles = side.locator(".ant-menu-submenu-title");
  for (let i = 0; i < await titles.count(); i++) {
    if (await titles.nth(i).getAttribute("aria-expanded") !== "true") await titles.nth(i).click({ timeout: 1500 }).catch(() => {});
  }
  await page.waitForTimeout(500);
  const items = side.locator(".ant-menu-item");
  const rows = [];
  for (let i = 0; i < await items.count(); i++) {
    const row = await items.nth(i).evaluate((el) => {
      const parents=[]; let cur=el.parentElement?.closest(".ant-menu-submenu");
      while(cur){ const t=cur.querySelector(":scope > .ant-menu-submenu-title"); if(t?.textContent?.trim()) parents.unshift(t.textContent.trim()); cur=cur.parentElement?.closest(".ant-menu-submenu"); }
      const a=el.querySelector("a[href]"); return { parents, name:(el.textContent||"").trim(), href:a?.getAttribute("href")||"" };
    });
    let route = "";
    if (row.href) route = new URL(row.href, baseUrl).pathname;
    else { const before=page.url(); await items.nth(i).click({ timeout: 2000 }).catch(() => {}); await page.waitForTimeout(250); if(page.url()!==before) route=new URL(page.url()).pathname; }
    rows.push({ order:i+1, menu_path:row.parents.map(safeText), page_name:safeText(row.name), route:safeText(route), route_source:row.href?"anchor_href":route?"semantic_click":"unresolved" });
  }
  const seen=new Set(); return rows.filter((r)=>{const k=`${r.menu_path.join(">")}|${r.page_name}|${r.route}`;if(seen.has(k))return false;seen.add(k);return true;});
}

async function controls() {
  return await page.locator("body").evaluate(() => {
    const visible=(e)=>{const s=getComputedStyle(e),r=e.getBoundingClientRect();return s.display!=="none"&&s.visibility!=="hidden"&&r.width>0&&r.height>0};
    const text=(e)=>(e.innerText||e.textContent||"").trim();
    return {
      inputs:[...document.querySelectorAll("input,textarea")].filter(visible).map(e=>({type:e.getAttribute("type")||e.tagName.toLowerCase(),placeholder:e.getAttribute("placeholder")||"",name:e.getAttribute("name")||"",disabled:!!e.disabled})),
      selects:[...document.querySelectorAll(".ant-select,[role=combobox]")].filter(visible).map(e=>({text:text(e),aria_label:e.getAttribute("aria-label")||""})),
      buttons:[...document.querySelectorAll("button")].filter(visible).map(e=>({text:text(e),title:e.getAttribute("title")||"",aria_label:e.getAttribute("aria-label")||"",disabled:!!e.disabled})),
      tabs:[...document.querySelectorAll("[role=tab],.ant-tabs-tab")].filter(visible).map(e=>({text:text(e),selected:e.getAttribute("aria-selected")||""})),
      pagination:[...document.querySelectorAll(".ant-pagination a,.ant-pagination button")].filter(visible).map(e=>({text:text(e),title:e.getAttribute("title")||"",aria_label:e.getAttribute("aria-label")||""})),
      links:[...document.querySelectorAll("a[href]")].filter(visible).map(e=>({text:text(e),href:e.getAttribute("href")||""})).filter(x=>x.text)
    };
  }).then(o=>Object.fromEntries(Object.entries(o).map(([k,v])=>[k,v.map(x=>Object.fromEntries(Object.entries(x).map(([a,b])=>[a,typeof b==="string"?safeText(b):b])))])));
}

const actions=[];
async function safeActions(route) {
  const candidates = [
    ["query", page.getByRole("button", { name:/^(query|search|查询|搜索)$/i })],
    ["reset", page.getByRole("button", { name:/^(reset|重置)$/i })],
    ["details", page.getByRole("button", { name:/^(details?|view|查看|详情)$/i })],
    ["export", page.getByRole("button", { name:/^(export|导出)$/i })],
    ["overflow", page.locator("button[aria-label*='more' i],button[title*='more' i],.ant-dropdown-trigger button")],
  ];
  for (const [kind, locator] of candidates) {
    const count=Math.min(await locator.count(), kind==="details"?2:1);
    for(let i=0;i<count;i++){
      const item=locator.nth(i); if(!await item.isVisible().catch(()=>false)||await item.isDisabled().catch(()=>true))continue;
      const start=network.length; currentAction=`${kind} control`;
      let status="CLICKED", overlay="", error="", downloadObserved=false;
      try {
        const downloadPromise = kind === "export" ? page.waitForEvent("download", { timeout: 1500 }).then(() => true).catch(() => false) : Promise.resolve(false);
        await item.click({timeout:2500}); await page.waitForTimeout(800);
        downloadObserved = await downloadPromise;
        overlay = safeText(await page.locator(".ant-modal:visible,.ant-drawer:visible,.ant-dropdown:visible").innerText().catch(()=>""));
      }
      catch(e){status="INTERACTION_ERROR";error=safeText(e)}
      actions.push({route,kind,status,overlay_present:Boolean(overlay),overlay_text:overlay,download_observed:downloadObserved,network_events:network.slice(start),error});
      await page.keyboard.press("Escape").catch(()=>{}); await page.waitForTimeout(150);
      if(new URL(page.url()).pathname!==route){ await page.goto(new URL(route,baseUrl).toString(),{waitUntil:"domcontentloaded",timeout:15000}).catch(()=>{}); await page.waitForTimeout(500); }
    }
  }
  const tabs=page.locator("[role=tab],.ant-tabs-tab");
  for(let i=0;i<Math.min(await tabs.count(),8);i++){
    const tab=tabs.nth(i), name=safeText(await tab.innerText().catch(()=>"")); if(!name||await tab.getAttribute("aria-selected")==="true")continue;
    const start=network.length; currentAction=`tab: ${name}`; let status="CLICKED",error="";
    try{await tab.click({timeout:2000});await page.waitForTimeout(600)}catch(e){status="INTERACTION_ERROR";error=safeText(e)}
    actions.push({route,kind:"tab",name,status,network_events:network.slice(start),error});
  }
  const next=page.locator(".ant-pagination-next:not(.ant-pagination-disabled) button,.ant-pagination-next:not(.ant-pagination-disabled) a").first();
  if(await next.isVisible().catch(()=>false)){
    const start=network.length;currentAction="pagination next";let status="CLICKED",error="";
    try{await next.click({timeout:2000});await page.waitForTimeout(700)}catch(e){status="INTERACTION_ERROR";error=safeText(e)}
    actions.push({route,kind:"pagination_next",status,network_events:network.slice(start),error});
    const prev=page.locator(".ant-pagination-prev:not(.ant-pagination-disabled) button,.ant-pagination-prev:not(.ant-pagination-disabled) a").first();
    if(await prev.isVisible().catch(()=>false)){
      const restoreStart=network.length;currentAction="pagination restore previous";let restoreStatus="RESTORED",restoreError="";
      try{await prev.click({timeout:2000});await page.waitForTimeout(700)}catch(e){restoreStatus="INTERACTION_ERROR";restoreError=safeText(e)}
      actions.push({route,kind:"pagination_restore",status:restoreStatus,network_events:network.slice(restoreStart),error:restoreError});
    }
  }

  // Exercise a clearly reversible list filter only on pages that expose an explicit Query/Search action.
  const query = page.getByRole("button", { name:/^(query|search|查询|搜索)$/i }).first();
  const filterInput = page.locator("form input:visible,.ant-form input:visible").filter({ hasNot: page.locator("[type=password]") }).first();
  if(await query.isVisible().catch(()=>false) && await filterInput.isVisible().catch(()=>false) && !await filterInput.isDisabled().catch(()=>true)){
    const original=await filterInput.inputValue().catch(()=>""); const start=network.length; currentAction="reversible text filter query"; let status="CLICKED",error="";
    try{await filterInput.fill("scan-no-match");await query.click({timeout:2000});await page.waitForTimeout(700);await filterInput.fill(original)}catch(e){status="INTERACTION_ERROR";error=safeText(e)}
    actions.push({route,kind:"filter_query",status,before_state:{input_empty:original===""},after_state:{input_restored:await filterInput.inputValue().catch(()=>"")===original},network_events:network.slice(start),error});
    const reset = page.getByRole("button", { name:/^(reset|重置)$/i }).first();
    if(await reset.isVisible().catch(()=>false)){const rs=network.length;currentAction="filter reset";let s="RESTORED",e="";try{await reset.click({timeout:2000});await page.waitForTimeout(500)}catch(x){s="INTERACTION_ERROR";e=safeText(x)}actions.push({route,kind:"filter_reset",status:s,network_events:network.slice(rs),error:e});}
  }

  const safeSelects=page.locator("form .ant-select:visible,.ant-form .ant-select:visible");
  for(let i=0;i<Math.min(await safeSelects.count(),4);i++){
    const select=safeSelects.nth(i);const start=network.length;currentAction="open filter select";let status="OPENED_AND_CLOSED",error="",overlay="";
    try{await select.click({timeout:1500});await page.waitForTimeout(250);overlay=safeText(await page.locator(".ant-select-dropdown:visible").last().innerText().catch(()=>""));await page.keyboard.press("Escape")}catch(e){status="INTERACTION_ERROR";error=safeText(e)}
    actions.push({route,kind:"filter_select_options",status,overlay_present:Boolean(overlay),overlay_text:overlay,network_events:network.slice(start),error});
  }
}

async function homeChartActions(route) {
  const describe = async (locator) => locator.evaluate((el) => ({
    text: (el.innerText || el.textContent || "").trim(),
    class_name: el.className || "",
    aria_pressed: el.getAttribute("aria-pressed") || "",
    aria_selected: el.getAttribute("aria-selected") || "",
    disabled: Boolean(el.disabled),
    parent_class: el.parentElement?.className || "",
    chart_nodes: document.querySelectorAll("canvas,svg.recharts-surface,.echarts-for-react").length,
  })).then((x) => Object.fromEntries(Object.entries(x).map(([k,v]) => [k, typeof v === "string" ? safeText(v) : v])));
  const line = page.getByRole("button", { name: /^Line Chart Mode$/i }).first();
  const bar = page.getByRole("button", { name: /^Bar Chart Mode$/i }).first();
  if (await line.isVisible().catch(() => false) && await bar.isVisible().catch(() => false)) {
    const initial = { line: await describe(line), bar: await describe(bar) };
    const initiallyLine = /primary|active|selected/i.test(`${initial.line.class_name} ${initial.line.aria_pressed} ${initial.line.aria_selected}`);
    const initiallyBar = /primary|active|selected/i.test(`${initial.bar.class_name} ${initial.bar.aria_pressed} ${initial.bar.aria_selected}`);
    for (const [name, locator] of [["Line Chart Mode", line], ["Bar Chart Mode", bar]]) {
      const before = { line: await describe(line), bar: await describe(bar) };
      const start = network.length; currentAction = `chart mode: ${name}`; let status="CLICKED", error="";
      try { await locator.click({timeout:2000}); await page.waitForTimeout(500); } catch(e) { status="INTERACTION_ERROR"; error=safeText(e); }
      actions.push({route,kind:"chart_mode",name,status,before_state:before,after_state:{line:await describe(line),bar:await describe(bar)},network_events:network.slice(start),error});
    }
    const restore = initiallyBar ? bar : line;
    const restoreName = initiallyBar ? "Bar Chart Mode" : "Line Chart Mode";
    const before = { line: await describe(line), bar: await describe(bar) };
    const start=network.length; currentAction=`restore chart mode: ${restoreName}`; let status="RESTORED",error="";
    try { await restore.click({timeout:2000}); await page.waitForTimeout(500); } catch(e) { status="INTERACTION_ERROR"; error=safeText(e); }
    actions.push({route,kind:"chart_mode_restore",name:restoreName,status,before_state:before,after_state:{line:await describe(line),bar:await describe(bar)},initial_state:initial,initial_active_hint:{line:initiallyLine,bar:initiallyBar},network_events:network.slice(start),error});
  }
  const legend = page.locator("button:visible").filter({ hasText:/On\s*Closed/i }).first();
  if (await legend.isVisible().catch(() => false)) {
    const state=await describe(legend);
    const structure=await legend.evaluate((el)=>({tag:el.tagName.toLowerCase(),role:el.getAttribute("role")||"",class_name:el.className||"",has_input:Boolean(el.querySelector("input")),nearest_chart:Boolean(el.closest("canvas,.echarts-for-react,.recharts-wrapper,[data-chart]")),html_elements:[...el.querySelectorAll("*")].slice(0,8).map(x=>x.tagName.toLowerCase())}));
    actions.push({route,kind:"chart_series_legend",name:"On / Closed",status:"BLOCKED_PREREQUISITE",before_state:state,after_state:state,network_events:[],error:"DOM did not prove this ambiguous combined-label control is a reversible chart series legend; not clicked",dom_structure:structure});
  }
}

let fatalError=""; let loginGate={}; let menu=[]; const pages=[];
try {
  loginGate=await login(); console.log(`[login] success origin=${loginGate.origin} route=${loginGate.pathname} menus=${loginGate.rendered_menu_items}`);
  menu=await discoverMenu(); loginGate.rendered_menu_items=menu.length; console.log(`[menu] pages=${menu.length} unresolved=${menu.filter(x=>!x.route).length}`);
  fs.writeFileSync(path.join(outDir,"agency-admin-menu-checkpoint.json"),JSON.stringify({login_gate:loginGate,menu},null,2)+"\n",{mode:0o600});
  const routes=menu.filter(x=>x.route);
  for(let i=0;i<routes.length;i++){
    const m=routes[i];currentRoute=m.route;currentAction="page initialization";const start=network.length;let error="";
    try{await page.goto(new URL(m.route,baseUrl).toString(),{waitUntil:"domcontentloaded",timeout:20000});await page.waitForTimeout(1200)}catch(e){error=safeText(e)}
    const actualUrl=new URL(page.url());
    const renderedMenus=await page.locator(".ant-layout-sider .ant-menu-item, aside .ant-menu-item").count().catch(()=>0);
    const authRedirect=actualUrl.origin!==origin || /\/user\/login|\/login/i.test(actualUrl.pathname);
    const routeMismatch=actualUrl.pathname.replace(/\/$/,"")!==m.route.replace(/\/$/,"");
    if(!error && (authRedirect || routeMismatch || renderedMenus===0)) error=`PAGE_GATE_FAILED expected=${safeText(m.route)} actual=${safeText(actualUrl.pathname)} rendered_menu_items=${renderedMenus}`;
    const c=!error ? await controls().catch(()=>({inputs:[],selects:[],buttons:[],tabs:[],pagination:[],links:[]})) : {inputs:[],selects:[],buttons:[],tabs:[],pagination:[],links:[]};
    const pageRecord={order:i+1,menu_path:m.menu_path,page_name:m.page_name,route:m.route,final_origin:actualUrl.origin,final_route:actualUrl.pathname,title:safeText(await page.title()),rendered_menu_items:renderedMenus,scan_status:error?"BLOCKED_PAGE_GATE":"SCANNED",controls:c,initialization_events:network.slice(start),error};
    pages.push(pageRecord);
    if(error){fatalError=error;console.error(`[page-gate] ${i+1}/${routes.length} ${m.page_name} ${error}`);break;}
    await safeActions(m.route);
    if (m.route === "/home") await homeChartActions(m.route);
    const afterUrl=new URL(page.url());
    const afterMenus=await page.locator(".ant-layout-sider .ant-menu-item, aside .ant-menu-item").count().catch(()=>0);
    if(afterUrl.origin!==origin || /\/user\/login|\/login/i.test(afterUrl.pathname) || afterMenus===0){
      pageRecord.scan_status="BLOCKED_AUTH_AFTER_ACTION";pageRecord.error=`POST_ACTION_AUTH_GATE_FAILED actual=${safeText(afterUrl.pathname)} rendered_menu_items=${afterMenus}`;fatalError=pageRecord.error;console.error(`[page-gate] ${i+1}/${routes.length} ${m.page_name} ${pageRecord.error}`);break;
    }
    console.log(`[${i+1}/${routes.length}] ${m.page_name} ${m.route} init=${network.length-start} controls=${Object.values(c).reduce((a,b)=>a+b.length,0)}${error?" ERROR":""}`);
  }
} catch(e){fatalError=safeText(e);console.error(`[fatal] ${fatalError}`)}
const result={captured_at:new Date().toISOString(),environment:"FAT",surface:"agency_admin",base_origin:origin,context_policy:"fresh dedicated Playwright browser context; no storage state/token reuse",login_gate:loginGate,login_network:loginEvidence,menu,pages,actions,network,fatal_error:fatalError};
fs.writeFileSync(path.join(outDir,"agency-admin-live-scan.json"),JSON.stringify(result,null,2)+"\n",{mode:0o600});
await browser.close();
console.log(`[summary] pages=${pages.length} actions=${actions.length} requests=${network.length} unique_endpoints=${new Set(network.map(x=>`${x.method} ${x.path}`)).size} fatal=${fatalError?"yes":"no"}`);
if(fatalError)process.exitCode=1;
