import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";
import { loadEnv, requiredEnv } from "../ui/framework/env.mjs";
import { decodeCbor } from "../ui/framework/cbor-decoder.mjs";

loadEnv(process.env.ENV_FILE || ".env.fat");

const baseUrl = requiredEnv("ADMIN_URL");
const origin = new URL(baseUrl).origin;
const outDir = path.resolve("fat-admin-interface-scan/results");
fs.mkdirSync(outDir, { recursive: true });

const sanitize = (value) => String(value || "")
  .replace(/\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi, "<redacted-email>")
  .replace(/(?<!\d)(?:\+?63|0)9\d{9}(?!\d)/g, "<redacted-phone>")
  .trim();

const browser = await chromium.launch({ headless: process.env.ADMIN_SCAN_HEADED === "false" });
const context = await browser.newContext({
  ignoreHTTPSErrors: true,
  viewport: { width: 1440, height: 1000 },
  locale: "en-US",
});
const page = await context.newPage();
const permissionCalls = [];
let adminToken = "";

page.on("response", async (response) => {
  const url = new URL(response.url());
  if (url.origin !== origin) return;
  let decoded = null;
  try { decoded = decodeCbor(new Uint8Array(await response.body())); } catch { /* structure remains unavailable */ }
  if (url.pathname === "/admin/login" && decoded?.status === true && typeof decoded?.data === "string") {
    adminToken = decoded.data;
  }
  if (url.pathname !== "/admin/priv/list") return;
  permissionCalls.push({
    method: response.request().method(),
    path: url.pathname,
    query_fields: [...url.searchParams.keys()].sort(),
    pid: sanitize(url.searchParams.get("pid") || ""),
    http_status: response.status(),
    business_status: decoded?.status ?? null,
    data: Array.isArray(decoded?.data) ? decoded.data.map((item) => ({
      id: sanitize(item.id), pid: sanitize(item.pid), name: sanitize(item.name),
      route_name: sanitize(item.routeName), module: sanitize(item.module),
      sort_level: sanitize(item.sortlevel), state: item.state, flag: item.flag,
      is_button_permission: Boolean(item.is_button_permission),
    })) : [],
  });
});

async function login() {
  await page.goto(baseUrl, { waitUntil: "domcontentloaded", timeout: 30_000 });
  await page.getByPlaceholder(/请输入用户名|user\s*name|email/i).fill(requiredEnv("ADMIN_EMAIL"));
  await page.getByPlaceholder(/请输入密码|password/i).fill(requiredEnv("ADMIN_PASSWORD"));
  await page.getByRole("button", { name: /登\s*录|log\s*in/i }).click();
  const verification = page.getByPlaceholder(/谷歌验证|google.*(?:code|verification|authenticator)/i);
  await verification.waitFor({ state: "visible", timeout: 10_000 });
  await verification.fill(requiredEnv("ADMIN_GOOGLE_CODE"));
  await page.getByRole("button", { name: /确\s*定|confirm|ok/i }).click();
  await page.waitForURL((url) => !url.pathname.startsWith("/user/login"), { timeout: 20_000 });
  await page.waitForTimeout(2_000);
}

async function fetchPermissionChildren(pid) {
  if (!adminToken) throw new Error("Admin token was not captured in memory from the successful login response");
  const url = new URL("/admin/priv/list", baseUrl);
  url.searchParams.set("pid", String(pid));
  const response = await context.request.get(url.toString(), {
    headers: { t: adminToken, lang: "en", "client-id": "123" },
    ignoreHTTPSErrors: true,
  });
  let decoded = null;
  try { decoded = decodeCbor(new Uint8Array(await response.body())); } catch { /* recorded below */ }
  const call = {
    method: "GET", path: url.pathname, query_fields: ["pid"], pid: sanitize(pid),
    http_status: response.status(), business_status: decoded?.status ?? null,
    data: Array.isArray(decoded?.data) ? decoded.data.map((item) => ({
      id: sanitize(item.id), pid: sanitize(item.pid), name: sanitize(item.name),
      route_name: sanitize(item.routeName), module: sanitize(item.module),
      sort_level: sanitize(item.sortlevel), state: item.state, flag: item.flag,
      is_button_permission: Boolean(item.is_button_permission),
    })) : [],
  };
  permissionCalls.push(call);
  return call.data;
}

async function menuItemSnapshot(index) {
  const items = page.locator(".ant-layout-sider .ant-menu-item, aside .ant-menu-item");
  if (index >= await items.count()) return null;
  return items.nth(index).evaluate((node) => {
    const parents = [];
    let current = node.parentElement?.closest(".ant-menu-submenu");
    while (current) {
      const title = current.querySelector(":scope > .ant-menu-submenu-title");
      if (title?.textContent?.trim()) parents.unshift(title.textContent.trim());
      current = current.parentElement?.closest(".ant-menu-submenu");
    }
    const anchor = node.querySelector("a[href]");
    return {
      text: node.textContent?.trim() || "",
      parents,
      href: anchor?.getAttribute("href") || "",
      absolute_href: anchor?.href || "",
      data_menu_id: node.getAttribute("data-menu-id") || "",
      title: node.getAttribute("title") || "",
    };
  });
}

await login();

const rootPermissions = await fetchPermissionChildren("0");
for (const permission of rootPermissions) {
  await fetchPermissionChildren(permission.id);
}

const menuPages = [];
const sidebar = page.locator(".ant-layout-sider, aside").first();

async function appendItems(locator) {
  const count = await locator.count();
  for (let index = 0; index < count; index += 1) {
    const node = locator.nth(index);
    const before = await node.evaluate((element) => {
      const parents = [];
      let current = element.parentElement?.closest(".ant-menu-submenu");
      while (current) {
        const title = current.querySelector(":scope > .ant-menu-submenu-title");
        if (title?.textContent?.trim()) parents.unshift(title.textContent.trim());
        current = current.parentElement?.closest(".ant-menu-submenu");
      }
      const anchor = element.querySelector("a[href]");
      const rawLabel = element.textContent?.trim() || "";
      return {
        text: rawLabel.replace(/\d+$/, "").trim(), raw_label: rawLabel, parents,
        href: anchor?.getAttribute("href") || "", title: element.getAttribute("title") || "",
      };
    });
    const hrefPath = before.href ? new URL(before.href, baseUrl).pathname : "";
    menuPages.push({
      order: menuPages.length + 1, menu_path: before.parents.map(sanitize),
      page_name: sanitize(before.text || before.title), anchor_href: sanitize(before.href),
      raw_label: sanitize(before.raw_label),
      route: hrefPath, route_source: hrefPath ? "sidebar anchor href" : "unresolved",
      click_error: "",
    });
  }
}

await appendItems(sidebar.locator(".ant-menu-root > .ant-menu-item"));
const rootSubmenus = sidebar.locator(".ant-menu-root > .ant-menu-submenu");
const rootSubmenuCount = await rootSubmenus.count();
for (let topIndex = 0; topIndex < rootSubmenuCount; topIndex += 1) {
  const rootSubmenu = rootSubmenus.nth(topIndex);
  const title = rootSubmenu.locator(":scope > .ant-menu-submenu-title");
  if (await title.getAttribute("aria-expanded") !== "true") {
    await title.click({ timeout: 3_000 }).catch(() => {});
    await page.waitForTimeout(200);
  }
  const nestedTitles = rootSubmenu.locator(".ant-menu-submenu-title[aria-expanded='false']");
  const nestedCount = await nestedTitles.count();
  for (let nestedIndex = 0; nestedIndex < nestedCount; nestedIndex += 1) {
    await nestedTitles.nth(nestedIndex).click({ timeout: 2_000 }).catch(() => {});
    await page.waitForTimeout(100);
  }
  await appendItems(rootSubmenu.locator(".ant-menu-item"));
}

const deduplicatedPages = [];
const seen = new Set();
for (const item of menuPages) {
  const key = `${item.menu_path.join(" > ")}\u0000${item.page_name}\u0000${item.route}`;
  if (!seen.has(key)) { seen.add(key); deduplicatedPages.push(item); }
}

const result = {
  captured_at: new Date().toISOString(),
  environment: "FAT",
  source: "live /admin/priv/list responses + rendered sidebar DOM",
  permission_calls: permissionCalls,
  rendered_root_submenu_count: rootSubmenuCount,
  permission_root_count: rootPermissions.length,
  rendered_menu_item_count: deduplicatedPages.length,
  menu_pages: deduplicatedPages,
};
fs.writeFileSync(path.join(outDir, "fat-admin-live-menu.json"), `${JSON.stringify(result, null, 2)}\n`);

const csvHeaders = ["order", "top_menu", "menu_path", "page_name", "raw_label", "route", "route_source", "anchor_href", "permission_match", "scan_status", "evidence", "note"];
const escapeCsv = (value) => `"${String(value ?? "").replaceAll('"', '""')}"`;
const permissionItems = permissionCalls.flatMap((call) => call.data);
const csvRows = deduplicatedPages.map((item) => {
  const candidates = permissionItems.filter((permission) => permission.name === item.page_name || permission.route_name === item.page_name);
  return {
    order: item.order,
    top_menu: item.menu_path[0] || item.page_name,
    menu_path: item.menu_path.join(" > "),
    page_name: item.page_name,
    raw_label: item.raw_label,
    route: item.route,
    route_source: item.route_source,
    anchor_href: item.anchor_href,
    permission_match: candidates.map((entry) => `${entry.id}:${entry.name}:${entry.module}`).join(" | "),
    scan_status: item.route_source === "unresolved" ? "ROUTE_UNRESOLVED" : "MENU_DISCOVERED",
    evidence: "fat-admin-live-menu.json rendered sidebar DOM",
    note: item.click_error,
  };
});
fs.writeFileSync(
  path.join(outDir, "fat-admin-live-menu-pages.csv"),
  `${csvHeaders.map(escapeCsv).join(",")}\n${csvRows.map((row) => csvHeaders.map((key) => escapeCsv(row[key])).join(",")).join("\n")}\n`,
);

console.log(`[menu] permission_calls=${permissionCalls.length} permission_items=${permissionItems.length} root_submenus=${rootSubmenuCount} pages=${deduplicatedPages.length} unresolved=${deduplicatedPages.filter((item) => item.route_source === "unresolved").length}`);
await browser.close();
