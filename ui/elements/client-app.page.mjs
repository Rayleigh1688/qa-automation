import { handleConfiguredModals, clickFirstByText, clickConfiguredTarget } from "../framework/ui-actions.mjs";

export class ClientAppPage {
  constructor(page, { modalConfig = {}, pageConfig = {} } = {}) {
    this.page = page;
    this.modalConfig = modalConfig;
    this.pageConfig = pageConfig;
  }

  async gotoHome() {
    await this.page.goto("/", { waitUntil: "domcontentloaded" });
    await this.page.waitForLoadState("networkidle", { timeout: 12_000 }).catch(() => {});
    await this.handleModals({ timeout: 8000 });
  }

  async clickFirst(labels, timeout = 3000) {
    const result = await clickFirstByText(this.page, labels, { timeout });
    return result.text;
  }

  async openLogin() {
    await this.gotoHome();

    const clickedEntry = await this.clickFirst(["Register / Login", "Login", "Register"], 3000);
    await this.waitForLoginForm();
    return clickedEntry || "home_login_entry";
  }

  async hasLoginForm() {
    const phoneInput = this.page.locator('input[type="tel"], input[placeholder*="900"]').first();
    if (await phoneInput.isVisible({ timeout: 1500 }).catch(() => false)) return true;
    return this.page.getByRole("button", { name: /SMS OTP/i }).first().isVisible({ timeout: 1500 }).catch(() => false);
  }

  async waitForLoginForm(timeout = 10_000) {
    const found = await this.page.waitForFunction(
      () =>
        Array.from(document.querySelectorAll("input")).some((element) => {
          const rect = element.getBoundingClientRect();
          const placeholder = element.getAttribute("placeholder") || "";
          return rect.width > 0 && rect.height > 0 && (element.type === "tel" || placeholder.includes("900"));
        }) || document.body.innerText.includes("SMS OTP"),
      null,
      { timeout },
    ).then(() => true).catch(() => false);
    if (!found) throw new Error("login form not found from home entry");
  }

  async handleModals(options = {}) {
    return handleConfiguredModals(this.page, this.modalConfig, options);
  }

  async loginWithOtp(phone, otp) {
    await this.openLogin();
    await this.chooseOtpMode();

    await this.fillPhone(phone);
    await this.requestOtp();
    await this.page.waitForFunction(() => document.querySelectorAll("input").length >= 2, null, { timeout: 5000 }).catch(() => {});

    const refreshedCount = await this.page.locator("input:visible").count();
    if (refreshedCount >= 2) {
      await this.page.locator("input:visible").nth(refreshedCount - 1).fill(otp);
    }

    await this.acceptLoginTerms();
    const clicked = await this.submitLogin();
    await this.waitForLoggedIn(15_000);
    await this.ensureNotFoundPageRecovered();
    return clicked;
  }

  async submitLogin() {
    const buttons = this.page.getByRole("button", { name: /^Login$/i });
    for (let index = (await buttons.count()) - 1; index >= 0; index -= 1) {
      const button = buttons.nth(index);
      if (!(await button.isVisible({ timeout: 1000 }).catch(() => false))) continue;
      if (!(await button.isEnabled().catch(() => false))) continue;
      await button.click({ timeout: 3000 }).catch(async () => {
        await button.evaluate((element) => element.click()).catch(() => {});
      });
      return "Login";
    }

    const clicked = await this.page.evaluate(() => {
      const candidates = Array.from(document.querySelectorAll("button, [role='button']"));
      const target = candidates
        .filter((element) => element.innerText?.trim() === "Login")
        .map((element) => ({ element, rect: element.getBoundingClientRect() }))
        .filter(({ rect }) => rect.width > 0 && rect.height > 0)
        .sort((a, b) => b.rect.width * b.rect.height - a.rect.width * a.rect.height)[0]?.element;
      if (!target) return false;
      target.click();
      return true;
    }).catch(() => false);
    if (!clicked) throw new Error("login submit button not found");
    return "Login";
  }

  async waitForLoggedIn(timeout = 12_000) {
    const loggedIn = await this.page.waitForFunction(
      () => {
        const text = document.body.innerText || "";
        return !text.includes("Register / Login") && /Balance|VIP|Deposit|Withdraw|₱/.test(text);
      },
      null,
      { timeout },
    ).then(() => true).catch(() => false);
    if (!loggedIn) throw new Error("client login did not reach logged-in state");
  }

  async ensureNotFoundPageRecovered() {
    const isNotFound = async () => {
      const text = await this.page.locator("body").innerText({ timeout: 5000 }).catch(() => "");
      return text.includes("Page not found");
    };

    if (!(await isNotFound())) return false;

    const clicked = await this.page.evaluate(() => {
      const candidates = Array.from(document.querySelectorAll("button, a, [role='button']"));
      const target = candidates.find((element) => element.innerText?.trim() === "Back to Home");
      if (!target) return false;
      target.click();
      return true;
    }).catch(() => false);

    if (!clicked) return false;
    await this.page.waitForTimeout(2500);
    await this.handleModals();
    return !(await isNotFound());
  }

  async chooseOtpMode() {
    const otpMode = this.page.getByRole("button", { name: /SMS OTP/i }).first();
    if (await otpMode.isVisible({ timeout: 5000 }).catch(() => false)) {
      await otpMode.click({ timeout: 3000 });
    }
  }

  async fillPhone(phone) {
    const phoneInput = this.page.locator('input[type="tel"], input[placeholder*="900"]').first();
    await phoneInput.waitFor({ state: "visible", timeout: 8000 });
    await phoneInput.fill(phone);
  }

  async requestOtp() {
    const getCode = this.page.getByRole("button", { name: /^Get Code$|^Send$|^发送$|^获取$/i }).first();
    if (await getCode.isVisible({ timeout: 5000 }).catch(() => false)) {
      await getCode.click({ timeout: 3000 }).catch(() => {});
    }
  }

  async acceptLoginTerms() {
    const box = await this.page.waitForFunction(() => {
      const candidates = Array.from(document.querySelectorAll("div")).filter((element) =>
        element.innerText?.trim().startsWith("I agree to the"),
      );
      const row = candidates.find((element) => element.innerText.includes("confirm that I am 21 years old")) || candidates[0];
      if (!row) return false;
      const rect = row.getBoundingClientRect();
      return {
        x: rect.x + Math.min(16, rect.width / 3),
        y: rect.y + rect.height / 2,
        width: rect.width,
        height: rect.height,
      };
    }, null, { timeout: 5000 }).then((handle) => handle.jsonValue()).catch(() => null);
    if (box && box.width > 0 && box.height > 0) {
      await this.page.mouse.click(box.x, box.y);
    }
  }

  async openMainFlowSurfaces() {
    const targets = (this.pageConfig.pages || []).filter((item) => item.id !== "login_register");

    const results = [];
    for (const target of targets) {
      let opened = { mode: "current", value: "", clicked: false };
      const bodyText = await this.page.locator("body").innerText({ timeout: 5000 }).catch(() => "");
      if (bodyText.includes("Page not found")) {
        const recovered = await this.ensureNotFoundPageRecovered();
        if (!recovered) throw new Error(`failed to recover from not found page before scanning ${target.id}`);
      }

      if (target.id === "home") {
        opened = { mode: "current", value: this.page.url(), clicked: false };
      } else {
        opened = await clickConfiguredTarget(this.page, { texts: target.entry?.texts || [] }, { timeout: 2500 });
        if (!opened.clicked) {
          opened = { mode: "nav_text_failed", value: target.entry?.texts?.join("|") || "", clicked: false };
        }
      }
      await this.page.waitForTimeout(2000);
      const recovered = await this.ensureNotFoundPageRecovered();
      if (recovered) opened = { ...opened, recoveredFromNotFound: true };
      results.push({ ...target, opened, url: this.page.url() });
    }
    return results;
  }
}
