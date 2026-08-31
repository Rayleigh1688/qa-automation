import fs from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";
import { ClientAppPage } from "../elements/client-app.page.mjs";
import { loadJson } from "../framework/data-loader.mjs";
import { loadEnv, requiredEnv } from "../framework/env.mjs";
import { attachNetworkRecorder } from "../framework/network-recorder.mjs";

loadEnv();

function compactUrl(value = "") {
  return String(value)
    .replace(/^https?:\/\/[^/]+/i, "")
    .replace(/([?&](?:token|key|authenticity_url|history_url|session_id|player_id|uid)=)[^&]+/gi, "$1<redacted>");
}

function safeFrameUrl(value = "") {
  const url = String(value);
  if (!url.includes("?")) return url;
  const [base] = url.split("?");
  return `${base}?<redacted>`;
}

function selectGame(config) {
  const id = process.env.CLIENT_GAME_ID || "lucky_penny";
  const game = (config.games || []).find((item) => item.id === id);
  if (!game) throw new Error(`game config not found: ${id}`);
  return game;
}

function businessNetworkRows(network) {
  return network
    .filter((item) => item.kind === "response" && /\/(game|wallet|finance|bet|order|record|launch|enter|process)\//i.test(item.url))
    .map((item) => `| ${item.method} | ${item.status} | \`${compactUrl(item.url)}\` |`)
    .filter((line, index, rows) => rows.indexOf(line) === index)
    .slice(0, 120);
}

function writeReport(result) {
  const lines = [
    "# 客户端游戏投注冒烟报告",
    "",
    `- 扫描时间: ${result.scannedAt}`,
    `- 游戏: ${result.game.name} (${result.game.id})`,
    `- 游戏页: \`${compactUrl(result.pageUrl)}\``,
    `- 执行真实点击: ${result.executeBet}`,
    `- 点击前等待: ${result.game.readyWaitMs}ms`,
    `- 点击后等待: ${result.game.postClickWaitMs}ms`,
    `- 点击位置: ${JSON.stringify(result.clickPoint)}`,
    `- Frame 数: ${result.frames.length}`,
    `- 点击后新增疑似游戏请求数: ${result.afterClickGameRequestCount}`,
    `- 点击前截图: \`${result.screenshots.before}\``,
    `- 点击后截图: \`${result.screenshots.after}\``,
    "",
    "## Frame",
    "",
    ...result.frames.map((frame) => `- \`${safeFrameUrl(frame)}\``),
    "",
    "## 关键接口",
    "",
    "| Method | HTTP | URL |",
    "|---|---:|---|",
    ...businessNetworkRows(result.network),
    "",
    "## 结论",
    "",
  ];

  if (!result.executeBet) {
    lines.push("- 未执行真实点击；设置 `EXECUTE_BET=true` 后才会点击游戏内 Spin/Bet 区域。");
  } else if (result.afterClickGameRequestCount > 0) {
    lines.push("- 已点击游戏内 Spin/Bet 区域，并捕获到点击后的第三方游戏请求。最终账变以钱包余额或投注记录接口为准。");
  } else {
    lines.push("- 已点击游戏内 Spin/Bet 区域，但未捕获到明确的点击后游戏请求，需要结合截图或投注记录继续判断。");
  }

  const out = path.resolve("ui/reports/client-game-bet-smoke-report.md");
  fs.mkdirSync(path.dirname(out), { recursive: true });
  fs.writeFileSync(out, lines.join("\n"));
  return out;
}

test.describe("Client game bet smoke", () => {
  test("launch configured game and click spin area when enabled", async ({ page }, testInfo) => {
    const pageConfig = loadJson("ui/data/client-pages.json");
    const modalConfig = loadJson("ui/data/client-modals.json");
    const gameConfig = loadJson("ui/data/client-game-actions.json");
    const game = selectGame(gameConfig);
    const viewport = gameConfig.viewport || page.viewportSize() || { width: 412, height: 915 };
    const network = attachNetworkRecorder(page, { hostPattern: /filbet|pwa|game|luck|jili|spribe|pg|cq9|bng|neurorestorativeals|playpoint|cloudfront/i });
    const app = new ClientAppPage(page, { pageConfig, modalConfig });

    await app.loginWithOtp(requiredEnv("CLIENT_PHONE"), requiredEnv("CLIENT_OTP"));
    await expect(page.locator("body")).not.toContainText("Register / Login");

    expect(page.viewportSize()).toEqual(viewport);
    await page.goto(process.env.CLIENT_GAME_PAGE_PATH || game.path, { waitUntil: "domcontentloaded" });
    await page.waitForLoadState("networkidle", { timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(Number(process.env.CLIENT_GAME_READY_WAIT_MS || game.readyWaitMs || 25_000));

    const screenshotDir = path.resolve("ui/results/screenshots");
    fs.mkdirSync(screenshotDir, { recursive: true });
    const beforeScreenshot = path.join(screenshotDir, `${game.id}-before-spin.png`);
    const afterScreenshot = path.join(screenshotDir, `${game.id}-after-spin.png`);
    await page.screenshot({ path: beforeScreenshot, fullPage: false });

    const clickPoint = {
      x: Math.round(viewport.width * game.spinButton.xRatio),
      y: Math.round(viewport.height * game.spinButton.yRatio),
    };
    const executeBet = process.env.EXECUTE_BET === "true";
    const clickStartedAt = Date.now();
    if (executeBet) {
      await page.mouse.click(clickPoint.x, clickPoint.y);
      await page.waitForTimeout(Number(process.env.CLIENT_GAME_POST_CLICK_WAIT_MS || game.postClickWaitMs || 8000));
    }
    await page.screenshot({ path: afterScreenshot, fullPage: false });

    const frames = page.frames().map((frame) => frame.url()).filter(Boolean);
    const afterClickGameRequestCount = network.filter(
      (item) => item.kind === "request" && item.ts >= clickStartedAt && /\/process\/|spin|bet|wager|round|play/i.test(`${item.url} ${item.postData || ""}`),
    ).length;

    const result = {
      scannedAt: new Date().toISOString(),
      game,
      pageUrl: page.url(),
      executeBet,
      clickPoint,
      frames,
      afterClickGameRequestCount,
      screenshots: {
        before: beforeScreenshot,
        after: afterScreenshot,
      },
      network,
    };

    const jsonOut = path.resolve("ui/results/client-game-bet-smoke.json");
    fs.mkdirSync(path.dirname(jsonOut), { recursive: true });
    fs.writeFileSync(jsonOut, JSON.stringify(result, null, 2));
    const reportOut = writeReport(result);

    await testInfo.attach("client-game-bet-smoke", {
      body: JSON.stringify(result, null, 2),
      contentType: "application/json",
    });
    await testInfo.attach("client-game-bet-smoke-report", {
      path: reportOut,
      contentType: "text/markdown",
    });

    expect(page.url()).toContain("/s-game-page/");
    for (const expected of game.expectedFrameText || []) {
      expect(frames.some((frame) => frame.includes(expected))).toBeTruthy();
    }
    if (executeBet) expect(afterClickGameRequestCount).toBeGreaterThan(0);
  });
});
