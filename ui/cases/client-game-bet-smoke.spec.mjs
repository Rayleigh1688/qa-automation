import fs from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";
import { ClientAppPage } from "../elements/client-app.page.mjs";
import { loadJson } from "../framework/data-loader.mjs";
import { loadEnv, requiredEnv } from "../framework/env.mjs";
import { attachNetworkRecorder } from "../framework/network-recorder.mjs";
import { p0StorageStatePath, reuseP0Auth } from "../framework/auth-state.mjs";

loadEnv();

const storageStatePath = reuseP0Auth
  ? p0StorageStatePath
  : path.resolve(process.env.CLIENT_STORAGE_STATE_PATH || "ui/results/client-fund-flow-storage-state.json");
if (reuseP0Auth || (process.env.CLIENT_REUSE_STORAGE_STATE === "true" && fs.existsSync(storageStatePath))) {
  test.use({ storageState: storageStatePath });
}

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

function compactDiagnostic(value = "") {
  return String(value)
    .replace(/https?:\/\/[^\s"']+/gi, (url) => safeFrameUrl(url))
    .replace(/((?:token|ssoKey|authorization|session_id|player_id|uid))=?[^\s&,"']*/gi, "$1=<redacted>")
    .slice(0, 1200);
}

function attachRuntimeDiagnostics(page) {
  const diagnostics = [];
  const push = (kind, text, extra = {}) => diagnostics.push({
    kind,
    text: compactDiagnostic(text),
    ts: Date.now(),
    ...extra,
  });
  page.on("console", (message) => {
    if (["error", "warning"].includes(message.type())) {
      const location = message.location();
      push(`console.${message.type()}`, message.text(), {
        source: location.url ? safeFrameUrl(location.url) : "",
        line: location.lineNumber,
        column: location.columnNumber,
      });
    }
  });
  page.on("pageerror", (error) => push("pageerror", error.stack || error.message));
  page.on("requestfailed", (request) => push("requestfailed", request.failure()?.errorText || "unknown", {
    method: request.method(),
    url: safeFrameUrl(request.url()),
  }));
  page.on("websocket", (socket) => {
    const socketUrl = safeFrameUrl(socket.url());
    push("websocket.open", socketUrl);
    socket.on("socketerror", (error) => push("websocket.error", error, { url: socketUrl }));
    socket.on("close", () => push("websocket.close", socketUrl));
  });
  return diagnostics;
}

function selectGame(config) {
  const id = process.env.CLIENT_GAME_ID || "lucky_penny";
  const game = (config.games || []).find((item) => item.id === id);
  if (!game) throw new Error(`game config not found: ${id}`);
  return game;
}

async function activatePoint(page, x, y) {
  if (process.env.CLIENT_GAME_INPUT !== "mouse") {
    await page.touchscreen.tap(x, y);
    return;
  }
  await page.mouse.click(x, y);
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
    `- 计划/完成点击: ${result.spinCount}/${result.completedSpinCount}`,
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
    const viewport = game.viewport || gameConfig.viewport || page.viewportSize() || { width: 412, height: 915 };
    if (JSON.stringify(page.viewportSize()) !== JSON.stringify(viewport)) {
      await page.setViewportSize(viewport);
    }
    const network = attachNetworkRecorder(page, { hostPattern: /filbet|pwa|game|luck|jili|spribe|pg|cq9|bng|neurorestorativeals|playpoint|cloudfront/i });
    const runtimeDiagnostics = attachRuntimeDiagnostics(page);
    const app = new ClientAppPage(page, { pageConfig, modalConfig });

    await app.gotoHome();
    const alreadyLoggedIn = !(await page.locator("body").innerText()).includes("Register / Login");
    if (!alreadyLoggedIn) {
      const authDiagnostics = await page.evaluate(() => ({
        localStorageKeyCount: Object.keys(localStorage).length,
        hasAccessTokenKey: Object.keys(localStorage).some((key) => key.includes("api_access_token")),
        hasLoggedInAccountKey: Object.keys(localStorage).some((key) => key.includes("logged_in_account")),
        hasEncodedAccessTokenKey: Object.keys(localStorage).some((key) => {
          try {
            return atob(key).includes("api_access_token");
          } catch {
            return false;
          }
        }),
      }));
      console.log(`game auth diagnostics=${JSON.stringify(authDiagnostics)}`);
      await app.loginWithPassword(requiredEnv("CLIENT_PHONE"), requiredEnv("CLIENT_PASSWORD"));
    }
    await expect(page.locator("body")).not.toContainText("Register / Login");
    await page.context().storageState({ path: storageStatePath });

    expect(page.viewportSize()).toEqual(viewport);
    await page.goto(process.env.CLIENT_GAME_PAGE_PATH || game.path, { waitUntil: "domcontentloaded" });
    await page.waitForLoadState("networkidle", { timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(Number(process.env.CLIENT_GAME_READY_WAIT_MS || game.readyWaitMs || 25_000));

    if (game.startTap) {
      await activatePoint(page,
        Math.round(viewport.width * game.startTap.xRatio),
        Math.round(viewport.height * game.startTap.yRatio),
      );
      await page.waitForTimeout(Number(process.env.CLIENT_GAME_POST_START_WAIT_MS || game.postStartWaitMs || 3000));
    }

    if (game.dismissOverlayTap) {
      await activatePoint(page,
        Math.round(viewport.width * game.dismissOverlayTap.xRatio),
        Math.round(viewport.height * game.dismissOverlayTap.yRatio),
      );
      await page.waitForTimeout(500);
    }

    const requestedBetAmount = String(process.env.CLIENT_GAME_BET_AMOUNT || "");
    const betOption = requestedBetAmount ? game.betOptions?.[requestedBetAmount] : null;
    const configuredBetButtonClicks = requestedBetAmount
      ? game.betButtonClicksByAmount?.[requestedBetAmount]
      : undefined;
    const betButtonClicks = Math.max(0, Number(
      process.env.CLIENT_GAME_BET_BUTTON_CLICKS
      ?? configuredBetButtonClicks
      ?? 0,
    ));
    const betButtonPoint = game.betButton
      ? {
          x: Math.round(viewport.width * game.betButton.xRatio),
          y: Math.round(viewport.height * game.betButton.yRatio),
        }
      : null;
    const betButtonHitTargets = betButtonPoint
      ? await page.evaluate(({ x, y }) => document.elementsFromPoint(x, y).slice(0, 8).map((element) => ({
          tag: element.tagName,
          id: element.id,
          className: String(element.className || ""),
          text: String(element.textContent || "").trim().slice(0, 80),
        })), betButtonPoint)
      : [];
    if (requestedBetAmount && !betOption && configuredBetButtonClicks === undefined) {
      throw new Error(`bet option is not configured: ${requestedBetAmount}`);
    }
    if (game.betButton && betOption) {
      await activatePoint(page,
        Math.round(viewport.width * game.betButton.xRatio),
        Math.round(viewport.height * game.betButton.yRatio),
      );
      await page.waitForTimeout(500);
      await activatePoint(page,
        Math.round(viewport.width * betOption.xRatio),
        Math.round(viewport.height * betOption.yRatio),
      );
      await page.waitForTimeout(500);
    }
    if (game.betButton) {
      for (let index = 0; index < betButtonClicks; index += 1) {
        await activatePoint(page,
          Math.round(viewport.width * game.betButton.xRatio),
          Math.round(viewport.height * game.betButton.yRatio),
        );
        await page.waitForTimeout(500);
      }
    }

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
    const spinCount = Math.max(1, Number(process.env.CLIENT_GAME_SPIN_COUNT || 1));
    let completedSpinCount = 0;
    const clickStartedAt = Date.now();
    if (executeBet) {
      for (let index = 0; index < spinCount; index += 1) {
        await activatePoint(page, clickPoint.x, clickPoint.y);
        completedSpinCount += 1;
        await page.waitForTimeout(Number(process.env.CLIENT_GAME_POST_CLICK_WAIT_MS || game.postClickWaitMs || 8000));
      }
    }
    await page.screenshot({ path: afterScreenshot, fullPage: false });

    const frames = page.frames().map((frame) => frame.url()).filter(Boolean);
    const frameDiagnostics = [];
    for (const frame of page.frames()) {
      const canvases = frame.locator("canvas");
      const canvasBoxes = [];
      for (let index = 0; index < Math.min(await canvases.count(), 8); index += 1) {
        canvasBoxes.push(await canvases.nth(index).boundingBox());
      }
      frameDiagnostics.push({
        url: safeFrameUrl(frame.url()),
        canvasBoxes,
        viewport: await frame.locator("body").evaluate((body) => ({
          width: body.clientWidth,
          height: body.clientHeight,
          scrollWidth: body.scrollWidth,
          scrollHeight: body.scrollHeight,
        })).catch(() => null),
      });
    }
    const afterClickGameRequestCount = network.filter(
      (item) => item.kind === "request" && item.ts >= clickStartedAt && /\/process\/|spin|bet|wager|round|play/i.test(`${item.url} ${item.postData || ""}`),
    ).length;
    const afterClickBetTotals = network
      .filter((item) => item.kind === "request" && item.ts >= clickStartedAt && item.url.includes("/process/"))
      .map((item) => {
        const match = String(item.postData || "").match(/"total_bet"\s*:\s*([0-9.]+)/);
        if (match) return Number(match[1]);
        try {
          return Number(JSON.parse(item.postData || "{}").total_bet);
        } catch {
          return Number.NaN;
        }
      })
      .filter(Number.isFinite);

    const result = {
      scannedAt: new Date().toISOString(),
      game,
      pageUrl: page.url(),
      executeBet,
      betButtonClicks,
      requestedBetAmount,
      betButtonPoint,
      betButtonHitTargets,
      spinCount,
      completedSpinCount,
      clickPoint,
      frames,
      frameDiagnostics,
      afterClickGameRequestCount,
      afterClickBetTotals,
      screenshots: {
        before: beforeScreenshot,
        after: afterScreenshot,
      },
      network,
      runtimeDiagnostics,
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
    if (executeBet) {
      if (game.networkEvidenceRequired !== false) {
        expect(afterClickGameRequestCount).toBeGreaterThan(0);
      }
      if (requestedBetAmount && game.assertRequestedBetAmount !== false) {
        expect(afterClickBetTotals).toContain(Number(requestedBetAmount));
      }
    }
  });
});
