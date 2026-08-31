import fs from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";
import { ClientAppPage } from "../elements/client-app.page.mjs";
import { loadJson } from "../framework/data-loader.mjs";
import { loadEnv, requiredEnv } from "../framework/env.mjs";
import { attachNetworkRecorder } from "../framework/network-recorder.mjs";
import { p0StorageStatePath, reuseP0Auth } from "../framework/auth-state.mjs";

loadEnv();

const p0Results = [];
const p0ResultDir = path.resolve("ui/results/client-p0-positive-negative-cases");

function compactUrl(value = "") {
  return String(value)
    .replace(/^https?:\/\/[^/]+/i, "")
    .replace(/([?&](?:payload|token|key|authenticity_url|history_url|session_id|player_id|uid)=)[^&]+/gi, "$1<redacted>");
}

function createApp(page) {
  return new ClientAppPage(page, {
    pageConfig: loadJson("ui/data/client-pages.json"),
    modalConfig: loadJson("ui/data/client-modals.json"),
  });
}

async function visibleState(page) {
  return {
    url: page.url(),
    text: (await page.locator("body").innerText({ timeout: 8000 }).catch(() => "")).slice(0, 3000),
    frames: page.frames().map((frame) => frame.url()).filter(Boolean),
  };
}

function hasMemberSuccess(network) {
  return network.some(
    (item) => item.kind === "response" && item.status >= 200 && item.status < 300 && /\/(member\/detail|finance\/wallet)/.test(item.url),
  );
}

function hasLoginSuccess(network) {
  return network.some((item) => item.kind === "response" && item.status >= 200 && item.status < 300 && /\/member\/otp\/login\/v2/.test(item.url));
}

function looksLoggedIn(state) {
  return !state.text.includes("Register / Login") && /Balance|Deposit|Withdraw|KYC|Member Account|UID|VIP|₱/.test(state.text);
}

function isRestrictedAccount(state) {
  return /mobile number has been restricted|account has been restricted|contact customer support/i.test(state.text || "");
}

async function writeResult(testInfo, result) {
  p0Results.push(result);
  fs.mkdirSync(p0ResultDir, { recursive: true });
  fs.writeFileSync(path.join(p0ResultDir, `${result.name}.json`), JSON.stringify(result, null, 2));
  await testInfo.attach(result.name, {
    body: JSON.stringify(result, null, 2),
    contentType: "application/json",
  });
}

async function loginWithOtpOrSkip(page, testInfo, network, app) {
  try {
    await app.gotoHome();
    const current = await visibleState(page);
    if (looksLoggedIn(current) || hasMemberSuccess(network)) return;
    await app.loginWithOtp(requiredEnv("CLIENT_PHONE"), requiredEnv("CLIENT_OTP"));
    return;
  } catch (error) {
    const state = await visibleState(page);
    const stillOnLoginForm = await app.hasLoginForm().catch(() => false);
    const loginDidNotSucceed = !looksLoggedIn(state) && !hasLoginSuccess(network);
    if (isRestrictedAccount(state) || (stillOnLoginForm && loginDidNotSucceed)) {
      await writeResult(testInfo, {
        name: testInfo.title.replace(/[^a-z0-9]+/gi, "_").toLowerCase(),
        status: "blocked",
        note: "测试账号当前无法登录，无法继续验证登录后页面",
        state,
        network,
      });
      test.skip(true, "CLIENT_PHONE cannot login in FAT");
    }
    throw error;
  }
}

test.describe("Client P0 positive and negative UI checkpoints", () => {
  test.afterAll(async () => {
    const persistedResults = fs.existsSync(p0ResultDir)
      ? fs.readdirSync(p0ResultDir)
        .filter((name) => name.endsWith(".json"))
        .map((name) => JSON.parse(fs.readFileSync(path.join(p0ResultDir, name), "utf8")))
      : p0Results;
    const out = path.resolve("ui/results/client-p0-positive-negative.json");
    fs.mkdirSync(path.dirname(out), { recursive: true });
    fs.writeFileSync(out, JSON.stringify({ executedAt: new Date().toISOString(), results: persistedResults }, null, 2));

    const report = [
      "# 客户端 P0 UI 正反例执行报告",
      "",
      `- 执行时间: ${new Date().toISOString()}`,
      `- 用例数: ${persistedResults.length}`,
      "",
      "| 用例 | 结果 | URL | 关键说明 |",
      "|---|---|---|---|",
      ...persistedResults.map((item) => `| ${item.name} | ${item.status} | \`${compactUrl(item.state?.url || "")}\` | ${item.note || ""} |`),
      "",
    ].join("\n");

    const reportOut = path.resolve("ui/reports/client-p0-positive-negative-report.md");
    fs.mkdirSync(path.dirname(reportOut), { recursive: true });
    fs.writeFileSync(reportOut, report);
  });

  test("negative: valid phone without OTP cannot login", async ({ page }, testInfo) => {
    const network = attachNetworkRecorder(page);
    const app = createApp(page);

    await app.openLogin();
    await app.chooseOtpMode();
    await app.fillPhone(process.env.UNVERIFIED_CLIENT_PHONE || requiredEnv("CLIENT_PHONE"));

    const login = page.getByRole("button", { name: /^Login$/i }).first();
    if (await login.isEnabled().catch(() => false)) {
      await login.click({ timeout: 3000 }).catch(() => {});
      await page.waitForTimeout(2500);
    }

    const state = await visibleState(page);
    const result = {
      name: "negative_missing_otp",
      status: looksLoggedIn(state) ? "failed" : "passed",
      note: "手机号已填写但 OTP 为空，应保持未登录态",
      state,
      network,
    };
    await writeResult(testInfo, result);

    expect(looksLoggedIn(state)).toBeFalsy();
    expect(hasLoginSuccess(network)).toBeFalsy();
  });

  test("negative: unchecked login terms cannot login", async ({ page }, testInfo) => {
    const network = attachNetworkRecorder(page);
    const app = createApp(page);

    await app.openLogin();
    await app.chooseOtpMode();
    await app.fillPhone(process.env.UNVERIFIED_CLIENT_PHONE || requiredEnv("CLIENT_PHONE"));
    await app.requestOtp();
    await page.waitForFunction(() => document.querySelectorAll("input").length >= 2, null, { timeout: 5000 }).catch(() => {});

    const visibleInputs = page.locator("input:visible");
    const inputCount = await visibleInputs.count();
    if (inputCount >= 2) await visibleInputs.nth(inputCount - 1).fill(requiredEnv("CLIENT_OTP"));

    const login = page.getByRole("button", { name: /^Login$/i }).first();
    if (await login.isEnabled().catch(() => false)) {
      await login.click({ timeout: 3000 }).catch(() => {});
      await page.waitForTimeout(2500);
    }

    const state = await visibleState(page);
    const result = {
      name: "negative_unchecked_terms",
      status: looksLoggedIn(state) ? "failed" : "passed",
      note: "未勾选登录条款时不能进入会员态",
      state,
      network,
    };
    await writeResult(testInfo, result);

    expect(looksLoggedIn(state)).toBeFalsy();
    expect(hasLoginSuccess(network)).toBeFalsy();
  });

  test("negative: guest direct My does not expose member details", async ({ page }, testInfo) => {
    const app = createApp(page);
    await page.goto("/my", { waitUntil: "domcontentloaded" });
    await page.waitForLoadState("networkidle", { timeout: 12_000 }).catch(() => {});
    await app.handleModals({ timeout: 8000 });

    const state = await visibleState(page);
    const sensitivePattern = /KYC\s+Approved|Member Account|Wallet password|Login password\s+Change|UID\s+\d{8,}/i;
    const result = {
      name: "negative_guest_my",
      status: sensitivePattern.test(state.text) ? "failed" : "passed",
      note: "未登录访问 My 不应暴露会员账号、KYC、钱包等敏感信息",
      state,
    };
    await writeResult(testInfo, result);

    expect(state.text).not.toMatch(sensitivePattern);
  });

  test.describe("authenticated checkpoints", () => {
    if (reuseP0Auth) test.use({ storageState: p0StorageStatePath });

  test("positive: logged-in My exposes wallet and member checkpoints", async ({ page }, testInfo) => {
    const network = attachNetworkRecorder(page);
    const app = createApp(page);

    await loginWithOtpOrSkip(page, testInfo, network, app);
    await page.goto("/my", { waitUntil: "domcontentloaded" });
    await page.waitForLoadState("networkidle", { timeout: 12_000 }).catch(() => {});
    await app.handleModals({ timeout: 3000 });

    const state = await visibleState(page);
    const memberPattern = /Balance|Deposit|Withdraw|KYC|VIP|Wallet|Member Account|UID|Account Center/i;
    const result = {
      name: "positive_logged_in_my_wallet",
      status: memberPattern.test(state.text) || hasMemberSuccess(network) ? "passed" : "failed",
      note: "登录后 My 需要展示会员态、钱包、充值、提现或 KYC 入口",
      state,
      network,
    };
    await writeResult(testInfo, result);

    expect(memberPattern.test(state.text) || hasMemberSuccess(network)).toBeTruthy();
  });

  test("negative: invalid game page does not launch third-party game", async ({ page }, testInfo) => {
    const network = attachNetworkRecorder(page, { hostPattern: /filbet|pwa|game|luck|jili|spribe|pg|cq9|bng|neurorestorativeals|playpoint|cloudfront/i });
    const app = createApp(page);

    await loginWithOtpOrSkip(page, testInfo, network, app);
    await page.goto("/s-game-page/invalid-p0-game-id", { waitUntil: "domcontentloaded" });
    await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => {});
    await page.waitForTimeout(3000);

    const state = await visibleState(page);
    const launchedFrame = state.frames.some((frame) => /bng\.games|neurorestorativeals|playpoint|spribe|jili|cq9/i.test(frame));
    const betRequest = network.some((item) => {
      if (item.kind !== "request") return false;
      const target = new URL(item.url);
      if (target.origin === new URL(page.url()).origin) return false;
      const wageringData = `${target.pathname} ${target.search} ${item.postData || ""}`;
      return /\/process\/|(?:^|[\/?&=_-])(spin|bet|wager|round)(?:[\/?&=_-]|$)/i.test(wageringData);
    });
    const result = {
      name: "negative_invalid_game_page",
      status: launchedFrame || betRequest ? "failed" : "passed",
      note: "无效游戏 ID 不应出现三方游戏 frame 或投注请求",
      state,
      network,
    };
    await writeResult(testInfo, result);

    expect(launchedFrame).toBeFalsy();
    expect(betRequest).toBeFalsy();
  });
  });
});
