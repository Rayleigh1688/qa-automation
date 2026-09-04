import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";
import { chromium, devices } from "@playwright/test";
import { ClientAppPage } from "../elements/client-app.page.mjs";
import { loadJson } from "../framework/data-loader.mjs";
import { loadEnv, requiredEnv } from "../framework/env.mjs";
import { p0StorageStatePath } from "../framework/auth-state.mjs";
import { decodeCbor } from "../framework/cbor-decoder.mjs";

const resolvedOtpCodes = new Map();

function resolveAdminSmsOtp(otpId) {
  if (resolvedOtpCodes.has(otpId)) return resolvedOtpCodes.get(otpId);
  const code = execFileSync(
    "python3",
    ["scripts/admin-sms-otp.py", "--env", process.env.ENV_FILE || ".env.fat", "--otp-id", otpId],
    {
      cwd: process.cwd(),
      env: { ...process.env, ENV_FILE_PRECEDENCE: "shell" },
      encoding: "utf8",
      stdio: ["ignore", "pipe", "pipe"],
    },
  ).trim();
  if (!/^\d{6}$/.test(code)) throw new Error("admin SMS OTP lookup returned an invalid code");
  resolvedOtpCodes.set(otpId, code);
  return code;
}

export default async function clientP0AuthSetup(config) {
  loadEnv();
  fs.mkdirSync(path.dirname(p0StorageStatePath), { recursive: true });

  const projectUse = config.projects[0]?.use || {};
  const configuredBaseUrl = requiredEnv("CLIENT_BASE_URL");
  if (new URL(projectUse.baseURL).origin !== new URL(configuredBaseUrl).origin) {
    throw new Error("Playwright baseURL does not match CLIENT_BASE_URL for the selected environment");
  }
  const browser = await chromium.launch({
    channel: process.env.PLAYWRIGHT_CHANNEL || undefined,
  });
  const contextOptions = {
    ...devices["Pixel 7"],
    viewport: { width: 412, height: 915 },
    baseURL: projectUse.baseURL,
    ignoreHTTPSErrors: true,
  };
  let context;
  const authNetwork = [];

  try {
    const reused = false;
    context = await browser.newContext(contextOptions);
    const page = context.pages()[0] || await context.newPage();
    const authMode = (process.env.CLIENT_AUTH_MODE || "password").toLowerCase();
    const otpSource = (process.env.CLIENT_OTP_SOURCE || "fixed").toLowerCase();
    page.on("response", async (response) => {
      const url = response.url();
      if (!/filbet\.zone|\/member\/|\/finance\//i.test(url)) return;
      const record = {
        method: response.request().method(),
        status: response.status(),
        url: url.replace(/^https?:\/\/[^/]+/i, ""),
      };
      authNetwork.push(record);
      if (!/\/member\/(?:v2\/login|otp\/login\/v2)(?:\?|$)/.test(url)) return;
      try {
        if (/\/member\/otp\/login\/v2(?:\?|$)/.test(url)) {
          const requestBytes = response.request().postDataBuffer();
          if (requestBytes) {
            let requestBody;
            try {
              requestBody = decodeCbor(requestBytes);
            } catch {
              requestBody = JSON.parse(requestBytes.toString("utf8"));
            }
            const submittedOtpId = String(requestBody?.otp_id || "");
            const submittedCode = String(requestBody?.code || "");
            record.otpRequest = {
              fields: requestBody && typeof requestBody === "object" ? Object.keys(requestBody).sort() : [],
              otpIdKnown: resolvedOtpCodes.has(submittedOtpId),
              codeLength: submittedCode.length,
              codeIsDigits: /^\d+$/.test(submittedCode),
              codeMatchesResolvedOtp: resolvedOtpCodes.get(submittedOtpId) === submittedCode,
            };
          }
        }
        const decoded = decodeCbor(await response.body());
        record.businessStatus = decoded?.status;
        record.message = typeof decoded?.msg === "string"
          ? decoded.msg.slice(0, 300)
          : typeof decoded?.message === "string" ? decoded.message.slice(0, 300) : "";
        record.dataType = decoded?.data === null ? "null" : typeof decoded?.data;
        if (decoded?.status === false && typeof decoded?.data === "string") {
          record.businessError = decoded.data.slice(0, 300);
        } else {
          record.tokenPresent = typeof decoded?.data === "string" && decoded.data.length > 0;
        }
      } catch {
        record.businessBodyDecoded = false;
      }
    });
    const app = new ClientAppPage(page, {
      pageConfig: loadJson("ui/data/client-pages.json"),
      modalConfig: loadJson("ui/data/client-modals.json"),
    });
    try {
      if (authMode === "password") {
        await app.loginWithPassword(requiredEnv("CLIENT_PHONE"), requiredEnv("CLIENT_PASSWORD"));
      } else {
        const otp = otpSource === "admin_sms"
          ? resolveAdminSmsOtp
          : requiredEnv("CLIENT_OTP");
        await app.loginWithOtp(requiredEnv("CLIENT_PHONE"), otp);
      }
      await context.storageState({ path: p0StorageStatePath });
    } catch (error) {
      const diagnosticPath = path.resolve("ui/results/client-p0-auth-failure.json");
      const screenshotPath = path.resolve("ui/results/client-p0-auth-failure.png");
      await page.screenshot({ path: screenshotPath, fullPage: false }).catch(() => {});
      const diagnostic = {
        createdAt: new Date().toISOString(),
        error: String(error?.message || error),
        pageUrl: page.url().replace(/^https?:\/\/[^/]+/i, ""),
        visibleText: (await page.locator("body").innerText().catch(() => "")).slice(0, 2000),
        warnings: app.warnings,
        authNetwork,
        screenshotPath: path.relative(process.cwd(), screenshotPath),
      };
      fs.writeFileSync(diagnosticPath, JSON.stringify(diagnostic, null, 2));
      throw error;
    }

    const state = {
      createdAt: new Date().toISOString(),
      pageUrl: page.url().replace(/^https?:\/\/[^/]+/i, ""),
      storageStatePath: path.relative(process.cwd(), p0StorageStatePath),
      accountLane: "readonly_mature_account",
      authMode,
      reused,
    };
    fs.writeFileSync(
      path.resolve("ui/results/client-p0-auth-session.json"),
      JSON.stringify(state, null, 2),
    );
  } finally {
    await context?.close();
    await browser.close();
  }
}
