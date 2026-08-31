import fs from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";
import { ClientAppPage } from "../elements/client-app.page.mjs";
import { loadJson } from "../framework/data-loader.mjs";
import { loadEnv, requiredEnv } from "../framework/env.mjs";
import { pageSnapshot } from "../framework/locator-assets.mjs";
import { attachNetworkRecorder } from "../framework/network-recorder.mjs";
import { p0StorageStatePath, reuseP0Auth } from "../framework/auth-state.mjs";

loadEnv();
if (reuseP0Auth) test.use({ storageState: p0StorageStatePath });

function compactUrl(value = "") {
  return String(value).replace(/^https?:\/\/[^/]+/i, "");
}

function writeMainFlowReport(result) {
  const lines = [
    "# 客户端 P0 主流程 UI 扫描报告",
    "",
    `- 扫描时间: ${result.scannedAt}`,
    `- Base URL: ${result.baseURL}`,
    `- 页面数: ${result.surfaces.length}`,
    `- Network 响应数: ${result.network.filter((item) => item.kind === "response").length}`,
    "",
    "## 页面扫描",
    "",
    "| 模块 | 最终 URL | 定位资产数 | 入口方式 | 备注 |",
    "|---|---|---:|---|---|",
  ];

  for (const surface of result.surfaces) {
    const note = surface.snapshot.text.includes("Register / Login") ? "疑似未登录态或壳页面" : "";
    lines.push(
      `| ${surface.name || surface.id} | \`${compactUrl(surface.url)}\` | ${surface.snapshot.locatorCount} | ${surface.opened.mode}:${surface.opened.value || ""} | ${note} |`,
    );
  }

  const importantResponses = result.network
    .filter((item) => item.kind === "response" && /\/(member|finance|game|wallet|withdraw|deposit|bonus|activity)\//i.test(item.url))
    .slice(0, 80);

  lines.push("", "## 关键接口响应", "");
  lines.push("| Status | URL |");
  lines.push("|---:|---|");
  for (const item of importantResponses) {
    lines.push(`| ${item.status || ""} | \`${compactUrl(item.url)}\` |`);
  }

  lines.push("", "## 下一步判断", "");
  lines.push("- 登录后的首页、钱包、My 页可作为接口自动化的前置状态来源。");
  lines.push("- 充值、提现、投注需要在页面扫描基础上继续补入口点击和 Network 捕获，避免只按接口文档猜参数。");
  lines.push("- 活动、运营位只保留扫描资产，不纳入稳定 P0 断言。");

  const reportOut = path.resolve("ui/reports/client-main-flow-ui-report.md");
  fs.mkdirSync(path.dirname(reportOut), { recursive: true });
  fs.writeFileSync(reportOut, lines.join("\n"));
  return reportOut;
}

test.describe("P0 client main flow UI scan", () => {
  test("login and scan wallet/deposit/withdraw/betting surfaces", async ({ page }, testInfo) => {
    const phone = requiredEnv("CLIENT_PHONE");
    const otp = requiredEnv("CLIENT_OTP");
    const pageConfig = loadJson("ui/data/client-pages.json");
    const modalConfig = loadJson("ui/data/client-modals.json");
    const network = attachNetworkRecorder(page);
    const app = new ClientAppPage(page, { pageConfig, modalConfig });

    await app.gotoHome();
    const initialBodyText = await page.locator("body").innerText();
    if (initialBodyText.includes("Register / Login")) {
      await app.loginWithOtp(phone, otp);
    }

    const bodyText = await page.locator("body").innerText();
    expect(bodyText).not.toContain("Register / Login");

    const surfaces = [];
    for (const surface of await app.openMainFlowSurfaces()) {
      surfaces.push({
        ...surface,
        snapshot: await pageSnapshot(page, surface.id),
      });
    }
    const result = {
      scannedAt: new Date().toISOString(),
      baseURL: testInfo.project.use.baseURL,
      surfaces,
      network,
    };

    const out = path.resolve("ui/results/client-main-flow-ui.json");
    fs.mkdirSync(path.dirname(out), { recursive: true });
    fs.writeFileSync(out, JSON.stringify(result, null, 2));
    const reportOut = writeMainFlowReport(result);

    await testInfo.attach("client-main-flow-ui", {
      body: JSON.stringify(result, null, 2),
      contentType: "application/json",
    });
    await testInfo.attach("client-main-flow-ui-report", {
      path: reportOut,
      contentType: "text/markdown",
    });

    expect(network.some((item) => item.kind === "response" && /\/member\//.test(item.url))).toBeTruthy();
    expect(network.some((item) => item.kind === "response" && /\/finance\//.test(item.url))).toBeTruthy();
    expect(surfaces.some((surface) => surface.snapshot.text.includes("Page not found"))).toBeFalsy();
  });
});
