import fs from "node:fs";
import path from "node:path";
import { devices, expect, test } from "@playwright/test";
import { ClientAppPage } from "../elements/client-app.page.mjs";
import { loadJson } from "../framework/data-loader.mjs";
import { loadEnv, requiredEnv } from "../framework/env.mjs";
import { pageSnapshot } from "../framework/locator-assets.mjs";
import { attachNetworkRecorder, summarizeNetworkRecords } from "../framework/network-recorder.mjs";
import { clickFirstByText, openConfiguredEntry } from "../framework/ui-actions.mjs";

loadEnv();

const DISCOVERY_HOST_PATTERN = /filbet|pwa|game|luck|jili|spribe|pg|cq9|bng|neurorestorativeals|playpoint|cloudfront/i;
const CLIENT_DEVICE = devices["Pixel 7"];
const CLIENT_VIEWPORT = { width: 412, height: 915 };

test.use({ trace: "off", screenshot: "off", video: "off" });

function baseURL(testInfo) {
  return (
    process.env.CLIENT_BASE_URL ||
    process.env.API_URL ||
    testInfo.project.use.baseURL ||
    "https://client-fat.filbet2025.com"
  );
}

function compactEndpoint(item) {
  const origin = String(item.origin || "").replace(/^https?:\/\//i, "");
  return `${origin}${item.path || ""}`;
}

async function waitForPageSettle(page, app, waitMs = 1800) {
  await page.waitForLoadState("domcontentloaded", { timeout: 5000 }).catch(() => {
    app.warn("step domcontentloaded exceeded 5s");
  });
  await page.waitForLoadState("networkidle", { timeout: 5000 }).catch(() => {
    app.warn("step networkidle exceeded 5s");
  });
  await page.waitForTimeout(waitMs);
  await app.handleModals({ timeout: 1500 }).catch(() => {});
}

async function captureStep(page, app, steps, step, action) {
  const startedAt = Date.now();
  let status = "ok";
  let error = "";
  let clicked = null;
  const id = typeof step === "string" ? step : step.id;

  try {
    clicked = await action();
    await waitForPageSettle(page, app);
  } catch (err) {
    status = "error";
    error = err?.message || String(err);
  }

  steps.push({
    id,
    name: typeof step === "string" ? "" : step.name || "",
    notes: typeof step === "string" ? "" : step.notes || "",
    status,
    error,
    clicked,
    url: page.url(),
    startedAt,
    finishedAt: Date.now(),
    snapshot: await pageSnapshot(page, id).catch((err) => ({
      pageId: id,
      error: err?.message || String(err),
      text: "",
      locatorCount: 0,
    })),
  });
}

async function openPreferredSurface(page, surface) {
  const paths = surface.entry?.paths || (surface.entry?.path ? [surface.entry.path] : []);
  if (paths.length) {
    await page.goto(paths[0], { waitUntil: "domcontentloaded" });
    return { mode: "path", value: paths[0], clicked: false };
  }
  return openConfiguredEntry(page, surface, {});
}

function endpointsDuringStep(summary, step) {
  return summary.filter((item) => item.firstTs <= step.finishedAt && item.lastTs >= step.startedAt);
}

function writeDiscoveryReport(result) {
  const lines = [
    "# 客户端 P0 Network 发现报告",
    "",
    `- 扫描时间: ${result.scannedAt}`,
    `- Base URL: ${result.baseURL}`,
    `- 客户端设备: ${result.device.name}`,
    `- 固定视口: ${result.viewport.width}x${result.viewport.height}`,
    `- 登录完成: ${result.loginCompleted}`,
    `- 加载/交互警告数: ${result.warnings.length}`,
    `- 探索步骤: ${result.steps.length}`,
    `- 原始 Network 事件数: ${result.network.length}`,
    `- 候选 endpoint 数: ${result.summary.length}`,
    `- HAR: \`${result.artifacts.har}\``,
    `- Trace: \`${result.artifacts.trace}\``,
    "",
    "## 探索步骤",
    "",
    "| 步骤 | 状态 | 当前 URL | 定位资产数 | 点击 |",
    "|---|---|---|---:|---|",
  ];

  for (const step of result.steps) {
    lines.push(
      `| ${step.name || step.id} | ${step.status} | \`${step.url.replace(/^https?:\/\/[^/]+/i, "")}\` | ${step.snapshot.locatorCount || 0} | ${step.clicked?.text || step.clicked?.value || ""} |`,
    );
  }

  const notedSteps = result.steps.filter((step) => step.notes);
  if (notedSteps.length) {
    lines.push("", "## 入口说明", "");
    for (const step of notedSteps) {
      lines.push(`- ${step.name || step.id}: ${step.notes}`);
    }
  }

  if (result.warnings.length) {
    lines.push("", "## 警告", "");
    for (const warning of result.warnings) {
      lines.push(`- ${warning.message}`);
    }
  }

  lines.push("", "## 候选接口", "");
  lines.push("| Method | HTTP | Endpoint | Query | Body 字段 | Response 字段 | 次数 |");
  lines.push("|---|---|---|---|---|---|---:|");
  for (const item of result.summary) {
    lines.push(
      `| ${item.method} | ${item.statuses.join(",")} | \`${compactEndpoint(item)}\` | ${item.queryKeys.join(", ")} | ${item.postDataFields.join(", ")} | ${item.responseFields.join(", ")} | ${item.responseCount || item.requestCount} |`,
    );
  }

  lines.push("", "## 按步骤归类", "");
  for (const step of result.steps) {
    lines.push(`### ${step.id}`);
    const stepEndpoints = endpointsDuringStep(result.summary, step).slice(0, 30);
    if (!stepEndpoints.length) {
      lines.push("", "- 未捕获到业务候选接口。", "");
      continue;
    }
    lines.push("");
    for (const item of stepEndpoints) {
      lines.push(`- ${item.method} ${item.statuses.join(",")} \`${compactEndpoint(item)}\``);
    }
    lines.push("");
  }

  lines.push("## 需要人工协助判断", "");
  if (!result.loginCompleted) {
    lines.push("- 当前执行未完成客户端登录；请优先确认测试账号是否被短信频控、OTP 是否仍有效、登录弹层是否需要新的勾选/确认操作。");
  }
  lines.push("- 若充值、提现、KYC 入口未能自动打开，请业务同学指出当前页面的真实入口文案或可点击区域。");
  lines.push("- 若某个接口需要进入第三方页面、上传资料或真实资金动作，先只保留捕获证据，不默认纳入 CI。");
  lines.push("- 只有确认稳定契约后，才把 endpoint 回填到 `api/p0/interface-shortlist.csv` 和后续 runner。");

  const reportOut = path.resolve("ui/reports/client-network-discovery-report.md");
  fs.mkdirSync(path.dirname(reportOut), { recursive: true });
  fs.writeFileSync(reportOut, lines.join("\n"));
  return reportOut;
}

test.describe("Client P0 network discovery", () => {
  test.setTimeout(180_000);

  test("capture sanitized network while exploring client P0 surfaces", async ({ browser }, testInfo) => {
    const pageConfig = loadJson("ui/data/client-pages.json");
    const modalConfig = loadJson("ui/data/client-modals.json");
    const discoveryConfig = loadJson("ui/data/client-network-discovery.json");
    const viewport = CLIENT_VIEWPORT;
    const artifactDir = path.resolve("ui/results");
    fs.mkdirSync(artifactDir, { recursive: true });

    const context = await browser.newContext({
      ...CLIENT_DEVICE,
      viewport,
      baseURL: baseURL(testInfo),
      ignoreHTTPSErrors: true,
      recordHar: {
        path: path.join(artifactDir, "client-network-discovery.har"),
        content: "omit",
      },
    });
    await context.tracing.start({ screenshots: true, snapshots: true, sources: false });

    const page = await context.newPage();
    page.setDefaultTimeout(5000);
    page.setDefaultNavigationTimeout(5000);
    const network = attachNetworkRecorder(context, { hostPattern: DISCOVERY_HOST_PATTERN });
    const app = new ClientAppPage(page, { pageConfig, modalConfig });
    const steps = [];
    let loginCompleted = false;

    await captureStep(page, app, steps, "login", async () => {
      await app.loginWithPassword(requiredEnv("CLIENT_PHONE"), requiredEnv("CLIENT_PASSWORD"));
      return { text: "Login" };
    });
    const bodyTextAfterLogin = await page.locator("body").innerText({ timeout: 5000 }).catch(() => "");
    loginCompleted = !bodyTextAfterLogin.includes("Register / Login") && !bodyTextAfterLogin.includes("No account yet?");

    if (loginCompleted) {
      const surfacePages = (pageConfig.pages || []).filter((item) => item.id !== "login_register");
      for (const surface of surfacePages) {
        await captureStep(page, app, steps, `surface_${surface.id}`, async () => {
          if (surface.id === "home") {
            await page.goto("/", { waitUntil: "domcontentloaded" });
            return { text: "home" };
          }
          return openPreferredSurface(page, surface);
        });
      }

      for (const target of discoveryConfig.financeEntrypoints || []) {
        await captureStep(page, app, steps, { ...target, id: `entry_${target.id}` }, async () => {
          if (target.basePath) await page.goto(target.basePath, { waitUntil: "domcontentloaded" });
          await waitForPageSettle(page, app, 600);
          await app.ensureNotFoundPageRecovered();
          return clickFirstByText(page, target.texts, { timeout: 2500, force: false });
        });
      }
    }

    const tracePath = path.join(artifactDir, "client-network-discovery-trace.zip");
    await context.tracing.stop({ path: tracePath });
    await context.close();

    const summary = summarizeNetworkRecords(network);
    const result = {
      scannedAt: new Date().toISOString(),
      baseURL: baseURL(testInfo),
      device: {
        name: "Pixel 7",
      },
      viewport,
      loginCompleted,
      warnings: app.warnings,
      steps,
      summary,
      network,
      artifacts: {
        har: "ui/results/client-network-discovery.har",
        trace: "ui/results/client-network-discovery-trace.zip",
      },
    };

    const jsonOut = path.join(artifactDir, "client-network-discovery.json");
    fs.writeFileSync(jsonOut, JSON.stringify(result, null, 2));
    const reportOut = writeDiscoveryReport(result);

    await testInfo.attach("client-network-discovery", {
      path: jsonOut,
      contentType: "application/json",
    });
    await testInfo.attach("client-network-discovery-report", {
      path: reportOut,
      contentType: "text/markdown",
    });

    expect(loginCompleted, "client login must complete before member-only network discovery").toBeTruthy();
    expect(summary.some((item) => /\/member\//i.test(item.path))).toBeTruthy();
  });
});
