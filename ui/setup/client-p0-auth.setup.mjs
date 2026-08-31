import fs from "node:fs";
import path from "node:path";
import { chromium, devices } from "@playwright/test";
import { ClientAppPage } from "../elements/client-app.page.mjs";
import { loadJson } from "../framework/data-loader.mjs";
import { loadEnv, requiredEnv } from "../framework/env.mjs";
import { p0StorageStatePath } from "../framework/auth-state.mjs";

export default async function clientP0AuthSetup(config) {
  loadEnv();
  fs.mkdirSync(path.dirname(p0StorageStatePath), { recursive: true });

  const projectUse = config.projects[0]?.use || {};
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

  try {
    let reused = false;
    if (fs.existsSync(p0StorageStatePath)) {
      context = await browser.newContext({ ...contextOptions, storageState: p0StorageStatePath });
      const existingPage = await context.newPage();
      const existingApp = new ClientAppPage(existingPage, {
        pageConfig: loadJson("ui/data/client-pages.json"),
        modalConfig: loadJson("ui/data/client-modals.json"),
      });
      await existingApp.gotoHome();
      reused = await existingApp.waitForLoggedIn(5000).then(() => true).catch(() => false);
      if (!reused) {
        await context.close();
        context = undefined;
      }
    }

    context ||= await browser.newContext(contextOptions);
    const page = context.pages()[0] || await context.newPage();
    const app = new ClientAppPage(page, {
      pageConfig: loadJson("ui/data/client-pages.json"),
      modalConfig: loadJson("ui/data/client-modals.json"),
    });
    const authMode = (process.env.CLIENT_AUTH_MODE || "password").toLowerCase();
    if (!reused) {
      if (authMode === "password") {
        await app.loginWithPassword(requiredEnv("CLIENT_PHONE"), requiredEnv("CLIENT_PASSWORD"));
      } else {
        await app.loginWithOtp(requiredEnv("CLIENT_PHONE"), requiredEnv("CLIENT_OTP"));
      }
      await context.storageState({ path: p0StorageStatePath });
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
