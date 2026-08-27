import fs from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";
import { loadEnv, requiredEnv } from "../framework/env.mjs";
import { attachNetworkRecorder } from "../framework/network-recorder.mjs";
import { loadJson } from "../framework/data-loader.mjs";
import { ClientAppPage } from "../elements/client-app.page.mjs";

loadEnv();

async function openLogin(page) {
  const app = new ClientAppPage(page, {
    pageConfig: loadJson("ui/data/client-pages.json"),
    modalConfig: loadJson("ui/data/client-modals.json"),
  });
  await app.openLogin();
  return app;
}

async function visibleState(page) {
  return {
    url: page.url(),
    text: (await page.locator("body").innerText({ timeout: 8000 }).catch(() => "")).slice(0, 3000),
  };
}

test.describe("Client login P0", () => {
  test("positive: OTP login succeeds", async ({ page }, testInfo) => {
    const network = attachNetworkRecorder(page);
    const app = await openLogin(page);
    await app.chooseOtpMode();
    await app.fillPhone(requiredEnv("CLIENT_PHONE"));
    await app.requestOtp();
    const visibleInputs = page.locator("input:visible");
    const inputCount = await visibleInputs.count();
    if (inputCount >= 2) await visibleInputs.nth(inputCount - 1).fill(requiredEnv("CLIENT_OTP"));
    await app.acceptLoginTerms();
    const login = page.getByRole("button", { name: /^Login$/i }).first();
    if (await login.isEnabled().catch(() => false)) await login.click();
    await page.waitForTimeout(5000);

    const state = await visibleState(page);
    const result = { name: "positive_otp_login", state, network };
    const out = path.resolve("ui/results/client-login-positive.json");
    fs.mkdirSync(path.dirname(out), { recursive: true });
    fs.writeFileSync(out, JSON.stringify(result, null, 2));
    await testInfo.attach("client-login-positive", { body: JSON.stringify(result, null, 2), contentType: "application/json" });

    expect(state.url).not.toMatch(/\/login|\/user\/login/);
    expect(network.some((item) => item.kind === "response" && /\/member\/(login|detail|v2\/index|index)/.test(item.url))).toBeTruthy();
  });

  test("negative: empty phone does not login", async ({ page }) => {
    const app = await openLogin(page);
    await app.chooseOtpMode();
    const login = page.getByRole("button", { name: /^Login$/i }).first();
    expect(await login.isEnabled().catch(() => false)).toBeFalsy();
  });

  test("negative: invalid phone keeps user in guest state", async ({ page }, testInfo) => {
    const network = attachNetworkRecorder(page);
    const app = await openLogin(page);
    await app.chooseOtpMode();
    await app.fillPhone(process.env.CLIENT_INVALID_PHONE || "123");

    const login = page.getByRole("button", { name: /^Login$/i }).first();
    if (await login.isEnabled().catch(() => false)) {
      await login.click();
      await page.waitForTimeout(2500);
    }

    const state = await visibleState(page);
    const result = { name: "negative_invalid_phone", state, network };
    const out = path.resolve("ui/results/client-login-negative.json");
    fs.mkdirSync(path.dirname(out), { recursive: true });
    fs.writeFileSync(out, JSON.stringify(result, null, 2));
    await testInfo.attach("client-login-negative", { body: JSON.stringify(result, null, 2), contentType: "application/json" });

    expect(state.text).toContain("Register / Login");
    expect(network.some((item) => item.kind === "response" && /\/member\/detail|\/finance\/wallet/.test(item.url))).toBeFalsy();
  });
});
