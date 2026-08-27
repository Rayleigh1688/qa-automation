import fs from "node:fs";
import path from "node:path";
import { test } from "@playwright/test";
import { loadJson } from "../framework/data-loader.mjs";
import { loadEnv } from "../framework/env.mjs";
import { pageSnapshot } from "../framework/locator-assets.mjs";
import { attachNetworkRecorder } from "../framework/network-recorder.mjs";
import { handleConfiguredModals, openConfiguredEntry } from "../framework/ui-actions.mjs";

loadEnv();

function writeMarkdown(outFile, result) {
  const lines = [
    "# 客户端 UI 定位资产扫描",
    "",
    `- 扫描时间：${result.scannedAt}`,
    `- Base URL：${result.baseURL}`,
    "- 目标：按页面沉淀 Playwright 可用定位资产，优先用于后续数据驱动 UI 自动化和接口链路补全。",
    "",
    "## 页面汇总",
    "",
    "| 页面 | URL | 定位资产数 | 入口 |",
    "|---|---|---:|---|",
  ];

  for (const page of result.pages) {
    lines.push(`| ${page.name} | \`${page.url}\` | ${page.locatorCount} | ${page.opened?.mode || "path"}:${page.opened?.value || ""} |`);
  }

  lines.push("", "## 页面定位资产", "");
  for (const page of result.pages) {
    lines.push(`### ${page.name}`, "", "| 类型 | 文案/占位 | role | selector hint | enabled |", "|---|---|---|---|---:|");
    for (const item of page.locators.slice(0, 80)) {
      const label = item.text || item.placeholder || item.ariaLabel || item.name || item.href;
      lines.push(
        `| ${item.tag}${item.type ? `:${item.type}` : ""} | ${String(label || "").replace(/\|/g, "\\|")} | ${item.role || ""} | \`${String(item.selectorHint || "").replace(/`/g, "\\`")}\` | ${item.enabled} |`,
      );
    }
    lines.push("");
  }

  lines.push("## 捕获接口", "", "| Method | HTTP | URL |", "|---|---:|---|");
  const apiRows = result.network
    .filter((item) => item.kind === "response" && /\/(member|finance|game|activity|promotion|bonus|filcoin)\//i.test(item.url))
    .map((item) => `| ${item.method} | ${item.status} | \`${item.url}\` |`)
    .filter((line, index, arr) => arr.indexOf(line) === index)
    .slice(0, 160);
  lines.push(...apiRows);
  lines.push("", "## 原始结果", "", "- JSON：`ui/results/client-locator-inventory.json`");

  fs.mkdirSync(path.dirname(outFile), { recursive: true });
  fs.writeFileSync(outFile, lines.join("\n"));
}

test.describe("Client UI locator inventory", () => {
  test("scan configured client pages", async ({ page }, testInfo) => {
    const pageConfig = loadJson("ui/data/client-pages.json");
    const modalConfig = loadJson("ui/data/client-modals.json");
    const network = attachNetworkRecorder(page);
    const snapshots = [];

    await page.goto(pageConfig.basePath || "/", { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(2500);
    await handleConfiguredModals(page, modalConfig);

    for (const item of pageConfig.pages) {
      const opened = await openConfiguredEntry(page, item, modalConfig);
      await page.waitForTimeout(1200);
      snapshots.push(await pageSnapshot(page, item.id, { id: item.id, name: item.name, auth: item.auth, opened }));
    }

    const result = {
      scannedAt: new Date().toISOString(),
      baseURL: testInfo.project.use.baseURL,
      pages: snapshots,
      network,
    };

    const jsonOut = path.resolve("ui/results/client-locator-inventory.json");
    const mdOut = path.resolve("ui/reports/client-locator-inventory.md");
    fs.mkdirSync(path.dirname(jsonOut), { recursive: true });
    fs.writeFileSync(jsonOut, JSON.stringify(result, null, 2));
    writeMarkdown(mdOut, result);

    await testInfo.attach("client-locator-inventory", {
      body: JSON.stringify(result, null, 2),
      contentType: "application/json",
    });
  });
});
