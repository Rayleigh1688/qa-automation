import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";
import { decodeCbor } from "../ui/framework/cbor-decoder.mjs";

const baseUrl = process.env.AGENCY_PORTAL_URL || "https://agency-fat.filbet2025.com/user/login";
const expectedOrigin = new URL(baseUrl).origin;
const phone = process.env.AGENCY_PORTAL_PHONE;
const otp = process.env.AGENCY_PORTAL_OTP;
if (!phone || !otp) throw new Error("AGENCY_PORTAL_PHONE and AGENCY_PORTAL_OTP are required at runtime");

const outDir = path.resolve("agency-portal-interface-scan/results");
fs.mkdirSync(outDir, { recursive: true });

const clean = (value) => String(value ?? "")
  .replace(/\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi, "<redacted-email>")
  .replace(/(?<!\d)(?:\+?63|0)?9\d{9}(?!\d)/g, "<redacted-phone>")
  .replace(/(?<!\d)\d{6,}(?!\d)/g, "<redacted-numeric>")
  .replace(/[A-F0-9]{24,}/gi, "<redacted-secret-like>")
  .replace(/\s+/g, " ")
  .trim();
const safeLabel = (value) => clean(value).slice(0, 120);
const normalizePath = (pathname) => pathname
  .replace(/\/\d{5,}(?=\/|$)/g, "/{id}")
  .replace(/\/[0-9a-f]{16,}(?=\/|$)/gi, "/{id}");

const browser = await chromium.launch({ headless: process.env.AGENCY_PORTAL_HEADED !== "true" });
// This context is deliberately created here without storageState and is never exported.
const context = await browser.newContext({
  ignoreHTTPSErrors: true,
  acceptDownloads: true,
  viewport: { width: 1536, height: 960 },
  locale: "en-US",
});
const page = await context.newPage();

let currentRoute = "login";
let currentAction = "login flow";
const network = [];
const loginNetwork = [];

function isFirstParty(url) {
  return url.hostname === new URL(expectedOrigin).hostname || url.hostname.endsWith(".filbet2025.com");
}

async function decodeResponse(response) {
  const bytes = new Uint8Array(await response.body());
  const type = (response.headers()["content-type"] || "").toLowerCase();
  if (type.includes("json")) return JSON.parse(Buffer.from(bytes).toString("utf8"));
  try { return decodeCbor(bytes); } catch {}
  try { return JSON.parse(Buffer.from(bytes).toString("utf8")); } catch {}
  return null;
}

page.on("response", async (response) => {
  const request = response.request();
  if (!["xhr", "fetch"].includes(request.resourceType())) return;
  let url;
  try { url = new URL(response.url()); } catch { return; }
  if (!isFirstParty(url)) return;
  const event = {
    route: currentRoute,
    action: currentAction,
    api_origin: url.origin,
    method: request.method(),
    path: normalizePath(url.pathname),
    query_fields: [...url.searchParams.keys()].sort(),
    body_fields: [],
    http_status: response.status(),
    business_status: null,
    response_data_type: "unknown",
    response_data_keys: [],
    response_list_length: null,
  };
  try {
    const raw = request.postDataBuffer();
    if (raw?.length) {
      const type = (request.headers()["content-type"] || "").toLowerCase();
      let body;
      if (type.includes("json")) body = JSON.parse(raw.toString("utf8"));
      else body = decodeCbor(new Uint8Array(raw));
      if (body && typeof body === "object" && !Array.isArray(body)) event.body_fields = Object.keys(body).sort();
    }
  } catch {}
  try {
    const decoded = await decodeResponse(response);
    if (decoded && typeof decoded === "object" && !Array.isArray(decoded)) {
      event.business_status = typeof decoded.status === "boolean" ? decoded.status : null;
      const data = decoded.data;
      event.response_data_type = data === null ? "null" : Array.isArray(data) ? "list" : typeof data;
      if (Array.isArray(data)) event.response_list_length = data.length;
      if (data && typeof data === "object" && !Array.isArray(data)) event.response_data_keys = Object.keys(data).sort();
    }
  } catch {}
  network.push(event);
  if (currentRoute === "login") loginNetwork.push(event);
});

async function visibleCount(locator) {
  let count = 0;
  for (let i = 0; i < await locator.count(); i++) if (await locator.nth(i).isVisible().catch(() => false)) count++;
  return count;
}

async function login() {
  await page.goto(baseUrl, { waitUntil: "domcontentloaded", timeout: 30_000 });
  await page.waitForTimeout(800);
  const loginUrl = new URL(page.url());
  const loginDom = await page.locator("body").evaluate(() => ({
    input_types: [...document.querySelectorAll("input")].filter((e) => {
      const r=e.getBoundingClientRect(),s=getComputedStyle(e);return r.width>0&&r.height>0&&s.visibility!=="hidden";
    }).map((e) => e.type || "text"),
    input_placeholders: [...document.querySelectorAll("input")].map((e) => e.placeholder || "").filter(Boolean),
    button_labels: [...document.querySelectorAll("button")].map((e) => (e.innerText || e.textContent || "").trim()).filter(Boolean),
  }));
  const codeTab = page.getByText(/^Code Login$/i).first();
  if (await codeTab.isVisible().catch(() => false)) await codeTab.click();
  const inputs = page.locator("input:visible");
  const phoneInput = page.getByPlaceholder(/phone number|mobile|手机号/i).first();
  await phoneInput.waitFor({ state: "visible", timeout: 15_000 });
  await phoneInput.fill(phone);

  const getCode = page.getByRole("button", { name: /get\s*code|send\s*code|获取验证码|发送验证码/i }).first();
  let getCodeClicked = false;
  if (await getCode.isVisible().catch(() => false) && !await getCode.isDisabled().catch(() => true)) {
    currentAction = "request login code";
    await getCode.click();
    getCodeClicked = true;
    await page.waitForTimeout(700);
  }
  currentAction = "submit code login";
  let codeInput = page.getByPlaceholder(/verification code|otp|验证码/i).first();
  if (!await codeInput.isVisible().catch(() => false)) codeInput = inputs.nth(1);
  await codeInput.fill(otp);
  await page.getByRole("button", { name: /^log\s*in$|^login$|^登录$/i }).last().click();
  await page.waitForURL((url) => url.origin === expectedOrigin && !/\/user\/login\/?$/i.test(url.pathname), { timeout: 25_000 });
  await page.waitForTimeout(1800);
  const authenticatedUrl = new URL(page.url());
  const navigation = page.locator("aside:visible,nav:visible,.ant-layout-sider:visible,.sidebar:visible,.menu:visible");
  const navVisible = await visibleCount(navigation) > 0;
  const profileEvidence = network.filter((e) => /\/(?:agency\/profile|profile|me|detail|permission|priv)(?:\/|$)/i.test(e.path));
  const successfulLogin = loginNetwork.some((e) => /\/agency\/(?:otp|pwd)\/login$/i.test(e.path) && e.http_status >= 200 && e.http_status < 300 && e.business_status !== false);
  const successfulProfile = profileEvidence.some((e) => e.http_status >= 200 && e.http_status < 300 && e.business_status !== false);
  if (authenticatedUrl.origin !== expectedOrigin || /\/user\/login/i.test(authenticatedUrl.pathname) || !successfulLogin || !successfulProfile) {
    throw new Error("Login success gate failed: route/login/profile evidence incomplete");
  }
  return {
    success: true,
    login_origin: loginUrl.origin,
    login_path: loginUrl.pathname,
    authenticated_origin: authenticatedUrl.origin,
    authenticated_path: normalizePath(authenticatedUrl.pathname),
    title: safeLabel(await page.title()),
    get_code_clicked: getCodeClicked,
    login_request_success: successfulLogin,
    profile_request_success: successfulProfile,
    profile_evidence: profileEvidence.map((e) => `${e.method} ${e.path}:${e.http_status}:${e.business_status}`).slice(0, 10),
    navigation_shell_visible: navVisible,
    login_dom: {
      input_types: loginDom.input_types,
      input_placeholders: loginDom.input_placeholders.map(safeLabel),
      button_labels: loginDom.button_labels.map(safeLabel),
    },
  };
}

async function expandMenus() {
  const toggles = page.locator(".ant-menu-submenu-title:visible,[aria-haspopup=menu]:visible,.menu-item-has-children:visible");
  for (let i = 0; i < Math.min(await toggles.count(), 30); i++) {
    const item = toggles.nth(i);
    const expanded = await item.getAttribute("aria-expanded");
    if (expanded !== "true") await item.click({ timeout: 1200 }).catch(() => {});
  }
  await page.waitForTimeout(350);
}

async function discoverMenu() {
  await expandMenus();
  const candidates = page.locator("aside a[href]:visible,nav a[href]:visible,.ant-menu a[href]:visible,.sidebar a[href]:visible");
  const rows = [];
  for (let i = 0; i < await candidates.count(); i++) {
    const raw = await candidates.nth(i).evaluate((el) => {
      const item = el.closest("li,.ant-menu-item,.menu-item") || el;
      const parents=[];
      let current=item.parentElement?.closest(".ant-menu-submenu,li.menu-item-has-children");
      while(current){
        const title=current.querySelector(":scope > .ant-menu-submenu-title,:scope > a,:scope > .menu-title");
        if(title?.textContent?.trim()) parents.unshift(title.textContent.trim());
        current=current.parentElement?.closest(".ant-menu-submenu,li.menu-item-has-children");
      }
      return { label:(item.innerText||el.textContent||"").trim(), href:el.getAttribute("href")||"", parents };
    });
    let target;
    try { target = new URL(raw.href, page.url()); } catch { continue; }
    if (target.origin !== expectedOrigin || /logout|login/i.test(target.pathname)) continue;
    rows.push({
      order: rows.length + 1,
      menu_path: raw.parents.map(safeLabel),
      page_name: safeLabel(raw.label),
      route: normalizePath(target.pathname),
      route_source: "rendered_anchor_href",
    });
  }
  const bundleRoutes = [
    { page_name:"Data Overview", route:"/", labels:/^(Data Overview|Dashboard|Home|首页看板)$/i },
    { page_name:"Member List", route:"/a-member-list", labels:/^(Member List|会员列表)$/i },
    { page_name:"Betting Record", route:"/betting-record", labels:/^(Betting Record|投注记录)$/i },
    { page_name:"Commission Report", route:"/commission-report", labels:/^(Commission Report|佣金报表)$/i },
    { page_name:"Commission Rule", route:"/commission-rule", labels:/^(Commission Rule|佣金规则)$/i },
  ];
  for (const item of bundleRoutes) {
    const visibleInDom = await page.getByText(item.labels,{exact:true}).first().isVisible().catch(()=>false);
    if (!rows.some((r)=>r.route===item.route)) rows.push({
      order:rows.length+1,menu_path:[],page_name:item.page_name,route:item.route,
      route_source:visibleInDom?"bundle_route_plus_rendered_exact_label":"bundle_candidate_pending_dynamic_route_gate",
    });
  }
  if (!rows.some((r) => r.route === normalizePath(new URL(page.url()).pathname))) {
    rows.unshift({ order: 1, menu_path: [], page_name: "Authenticated landing page", route: normalizePath(new URL(page.url()).pathname), route_source: "post_login_route" });
  }
  const seen = new Set();
  return rows.filter((r) => {
    const key = `${r.page_name}|${r.route}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  }).map((r,i) => ({...r,order:i+1}));
}

async function captureControls() {
  const raw = await page.locator("body").evaluate(() => {
    const visible=(e)=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return r.width>0&&r.height>0&&s.visibility!=="hidden"&&s.display!=="none"};
    const label=(e)=>(e.getAttribute("aria-label")||e.getAttribute("title")||e.innerText||e.textContent||"").trim();
    return {
      inputs:[...document.querySelectorAll("input,textarea")].filter(visible).map(e=>({type:e.type||e.tagName.toLowerCase(),placeholder:e.placeholder||"",name:e.name||"",disabled:Boolean(e.disabled)})),
      selects:[...document.querySelectorAll("select,[role=combobox],.ant-select")].filter(visible).map(e=>({label:label(e),disabled:e.getAttribute("aria-disabled")==="true"})),
      buttons:[...document.querySelectorAll("button,[role=button]")].filter(visible).map(e=>({label:label(e),disabled:Boolean(e.disabled)||e.getAttribute("aria-disabled")==="true"})),
      tabs:[...document.querySelectorAll("[role=tab],.ant-tabs-tab")].filter(visible).map(e=>({label:label(e),selected:e.getAttribute("aria-selected")||""})),
      pagination:[...document.querySelectorAll(".ant-pagination a,.ant-pagination button,[aria-label*=page i]")].filter(visible).map(e=>({label:label(e),disabled:Boolean(e.disabled)})),
      overlays:[...document.querySelectorAll("[role=dialog],.ant-modal,.ant-drawer,.ant-dropdown")].filter(visible).map(e=>({type:e.getAttribute("role")||e.className||e.tagName.toLowerCase()})),
    };
  });
  return Object.fromEntries(Object.entries(raw).map(([kind,items]) => [kind, items.map((item) => Object.fromEntries(Object.entries(item).map(([k,v]) => [k, typeof v === "string" ? safeLabel(v) : v])))]));
}

const actions = [];
async function recordAction(route, kind, name, fn, options={}) {
  const start = network.length;
  currentAction = `${kind}: ${name}`;
  const beforeUrl = normalizePath(new URL(page.url()).pathname);
  const beforeOverlayCount = await page.locator("[role=dialog]:visible,.ant-modal:visible,.ant-drawer:visible,.ant-dropdown:visible").count();
  let status = "CLICKED";
  let error = "";
  let downloadObserved = false;
  try {
    const downloadPromise = options.download ? page.waitForEvent("download", { timeout: 2500 }).then(() => true).catch(() => false) : Promise.resolve(false);
    await fn();
    await page.waitForTimeout(options.wait ?? 700);
    downloadObserved = await downloadPromise;
  } catch (e) {
    status = "INTERACTION_ERROR";
    error = safeLabel(e?.message || e);
  }
  const afterUrl = normalizePath(new URL(page.url()).pathname);
  const afterOverlayCount = await page.locator("[role=dialog]:visible,.ant-modal:visible,.ant-drawer:visible,.ant-dropdown:visible").count();
  actions.push({ route, action_type:kind, action_name:safeLabel(name), status, before_route:beforeUrl, after_route:afterUrl,
    before_overlay_count:beforeOverlayCount, after_overlay_count:afterOverlayCount, download_observed:downloadObserved,
    network_events:network.slice(start), side_effect:"none observed; read/navigation/local UI interaction", error });
  return { status, beforeUrl, afterUrl };
}

async function restoreRoute(route) {
  await page.keyboard.press("Escape").catch(() => {});
  const current = normalizePath(new URL(page.url()).pathname);
  if (current !== route) {
    currentAction = "restore scanned route";
    await page.goto(new URL(route, expectedOrigin).toString(), { waitUntil:"domcontentloaded", timeout:20_000 }).catch(() => {});
    await page.waitForTimeout(600);
  }
}

async function safeActions(route) {
  const buttonKinds = [
    ["query", /^(query|search|search\s*\/\s*query|查询|搜索)$/i, false],
    ["reset", /^(reset|重置)$/i, false],
    ["detail", /^(detail|details|view|查看|详情)$/i, false],
    ["export", /^(export|download|导出|下载)$/i, true],
  ];
  for (const [kind, regex, download] of buttonKinds) {
    const matches = page.getByRole("button", { name:regex });
    for (let i=0; i<Math.min(await matches.count(), kind === "detail" ? 2 : 1); i++) {
      const button=matches.nth(i);
      if (!await button.isVisible().catch(()=>false) || await button.isDisabled().catch(()=>true)) continue;
      await recordAction(route,kind,kind,()=>button.click({timeout:2500}),{download});
      await restoreRoute(route);
    }
  }

  const tabs = page.locator("[role=tab]:visible,.ant-tabs-tab:visible");
  for (let i=0; i<Math.min(await tabs.count(),12); i++) {
    const tab=tabs.nth(i);
    if (await tab.getAttribute("aria-selected") === "true") continue;
    const name=safeLabel(await tab.innerText().catch(()=>"tab"));
    await recordAction(route,"tab",name,()=>tab.click({timeout:2200}));
    await restoreRoute(route);
  }

  const selects=page.locator("select:visible,[role=combobox]:visible,.ant-select:visible");
  for(let i=0;i<Math.min(await selects.count(),8);i++){
    const select=selects.nth(i);
    if(await select.getAttribute("aria-disabled")==="true")continue;
    await recordAction(route,"filter_open",`filter ${i+1}`,async()=>{await select.click({timeout:2000});await page.waitForTimeout(250);await page.keyboard.press("Escape")},{wait:200});
  }

  const next=page.locator(".ant-pagination-next:not(.ant-pagination-disabled) button,.ant-pagination-next:not(.ant-pagination-disabled) a,button[aria-label='Next Page']:not([disabled])").first();
  if(await next.isVisible().catch(()=>false)){
    await recordAction(route,"pagination","next page",()=>next.click({timeout:2200}));
    const prev=page.locator(".ant-pagination-prev:not(.ant-pagination-disabled) button,.ant-pagination-prev:not(.ant-pagination-disabled) a,button[aria-label='Previous Page']:not([disabled])").first();
    if(await prev.isVisible().catch(()=>false)) await recordAction(route,"pagination_restore","previous page",()=>prev.click({timeout:2200}));
    await restoreRoute(route);
  }

  const overflows=page.locator("button[aria-label*='more' i]:visible,button[title*='more' i]:visible,.ant-dropdown-trigger:visible");
  for(let i=0;i<Math.min(await overflows.count(),3);i++){
    const item=overflows.nth(i);
    await recordAction(route,"overflow_open",`overflow ${i+1}`,()=>item.click({timeout:2000}));
    await page.keyboard.press("Escape").catch(()=>{});
  }
}

let fatalError = "";
let loginGate = {};
let menu = [];
const pages = [];
try {
  loginGate = await login();
  console.log(`[login-gate] PASS origin=${loginGate.authenticated_origin} route=${loginGate.authenticated_path} profile=${loginGate.profile_request_success}`);
  currentRoute = loginGate.authenticated_path;
  currentAction = "authenticated menu discovery";
  menu = await discoverMenu();
  console.log(`[menu] rendered=${menu.length} routes=${new Set(menu.map((x)=>x.route)).size}`);
  for (let i=0;i<menu.length;i++) {
    const item=menu[i];
    currentRoute=item.route;
    currentAction="page initialization";
    const start=network.length;
    let error="";
    try {
      await page.goto(new URL(item.route,expectedOrigin).toString(),{waitUntil:"domcontentloaded",timeout:20_000});
      await page.waitForTimeout(1000);
    } catch(e) { error=safeLabel(e?.message||e); }
    const finalUrl=new URL(page.url());
    if(finalUrl.origin!==expectedOrigin || normalizePath(finalUrl.pathname)!==item.route || /\/user\/login/i.test(finalUrl.pathname)) {
      error=error||"authenticated route gate did not retain requested route";
    } else if (item.route_source.includes("bundle_candidate")) {
      item.route_source="bundle_candidate_plus_authenticated_path_and_network_gate";
    }
    const controls=await captureControls().catch(()=>({inputs:[],selects:[],buttons:[],tabs:[],pagination:[],overlays:[]}));
    pages.push({order:i+1,menu_path:item.menu_path,page_name:item.page_name,route:item.route,final_origin:finalUrl.origin,final_route:normalizePath(finalUrl.pathname),title:safeLabel(await page.title()),controls,initialization_events:network.slice(start),error});
    if(finalUrl.origin===expectedOrigin && !/\/user\/login/i.test(finalUrl.pathname)) await safeActions(item.route);
    console.log(`[${i+1}/${menu.length}] route=${item.route} controls=${Object.values(controls).reduce((n,x)=>n+x.length,0)} init=${network.length-start}${error?" ERROR":""}`);
  }
} catch(e) {
  fatalError=safeLabel(e?.message||e);
  console.error(`[fatal] ${fatalError}`);
}

const result={captured_at:new Date().toISOString(),environment:"FAT",surface:"agency_portal",base_origin:expectedOrigin,
  context_policy:"fresh dedicated Playwright browser context; no storage state/token reuse or export",
  credential_retention:"runtime input only; phone and OTP omitted from artifacts",login_gate:loginGate,login_network:loginNetwork,menu,pages,actions,network,fatal_error:fatalError};
fs.writeFileSync(path.join(outDir,"agency-portal-live-scan.json"),JSON.stringify(result,null,2)+"\n",{mode:0o600});
await context.close();
await browser.close();
console.log(`[summary] pages=${pages.length} actions=${actions.length} events=${network.length} unique=${new Set(network.map((e)=>`${e.method} ${e.path}`)).size} fatal=${fatalError?"yes":"no"}`);
if(fatalError)process.exitCode=1;
