import { defineConfig, devices } from "@playwright/test";

const clientDevice = process.env.CLIENT_BROWSER_PROFILE === "desktop"
  ? devices["Desktop Chrome"]
  : devices["Pixel 7"];

export default defineConfig({
  globalSetup: process.env.CLIENT_REUSE_P0_AUTH === "true"
    ? "./ui/setup/client-p0-auth.setup.mjs"
    : undefined,
  testDir: "./ui/cases",
  timeout: 120_000,
  expect: {
    timeout: 10_000,
  },
  fullyParallel: false,
  workers: process.env.CLIENT_REUSE_P0_AUTH === "true" ? 1 : undefined,
  retries: process.env.CI ? 1 : 0,
  reporter: [
    ["list"],
    ["html", { outputFolder: "playwright-report", open: "never" }],
    ["json", { outputFile: "ui/results/ui-playwright-result.json" }],
  ],
  use: {
    baseURL: process.env.CLIENT_BASE_URL || process.env.API_URL || "https://client-fat.filbet2025.com",
    ignoreHTTPSErrors: true,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    actionTimeout: 15_000,
    navigationTimeout: 45_000,
  },
  projects: [
    {
      name: "client-mobile-chromium",
      use: {
        ...clientDevice,
        viewport: process.env.CLIENT_BROWSER_PROFILE === "desktop"
          ? { width: 1365, height: 900 }
          : { width: 412, height: 915 },
        channel: process.env.PLAYWRIGHT_CHANNEL || undefined,
      },
    },
  ],
});
