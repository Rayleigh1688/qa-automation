import { handleConfiguredModals, clickFirstByText, clickConfiguredTarget } from "../framework/ui-actions.mjs";

export class ClientAppPage {
  constructor(page, { modalConfig = {}, pageConfig = {} } = {}) {
    this.page = page;
    this.modalConfig = modalConfig;
    this.pageConfig = pageConfig;
    this.warnings = [];
  }

  warn(message, detail = {}) {
    this.warnings.push({ message, detail, ts: Date.now() });
  }

  async waitForClientSettle(label = "page") {
    await this.page.waitForLoadState("domcontentloaded", { timeout: 5000 }).catch(() => {
      this.warn(`${label} domcontentloaded exceeded 5s`);
    });
    await this.page.waitForLoadState("networkidle", { timeout: 5000 }).catch(() => {
      this.warn(`${label} networkidle exceeded 5s`);
    });
  }

  async gotoHome() {
    await this.page.goto("/", { waitUntil: "domcontentloaded" });
    await this.waitForClientSettle("home");
    await this.handleModals({ timeout: 5000 });
  }

  async clickFirst(labels, timeout = 3000) {
    const result = await clickFirstByText(this.page, labels, { timeout });
    return result.text;
  }

  async openLogin() {
    await this.gotoHome();
    await this.prepareGuestHome();

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
    await this.useOtherAccountIfRemembered(phone);
    await this.chooseOtpMode();

    await this.fillPhone(phone);
    await this.requestOtp();
    await this.fillOtp(otp);

    await this.acceptLoginTerms();
    const clicked = await this.submitLogin();
    if (await this.acceptLoginConfirmation()) {
      await this.acceptLoginTerms();
      await this.submitLogin().catch(() => {});
    }
    await this.waitForLoggedIn(15_000);
    await this.ensureNotFoundPageRecovered();
    await this.handlePostLoginOverlays();
    return clicked;
  }

  async loginWithPassword(phone, password) {
    await this.openLogin();
    await this.useOtherAccountIfRemembered(phone);

    const passwordMode = this.page.getByRole("button", { name: /^Password$/i }).first();
    if (await passwordMode.isVisible({ timeout: 5000 }).catch(() => false)) {
      await passwordMode.click({ timeout: 3000 });
    }

    await this.fillPhone(phone);
    const passwordInput = this.page.locator('input[type="password"]:visible').first();
    await passwordInput.waitFor({ state: "visible", timeout: 8000 });
    await passwordInput.fill(password);
    await this.acceptLoginTerms();
    const clicked = await this.submitLogin();
    if (await this.acceptLoginConfirmation()) {
      await this.acceptLoginTerms();
      await this.submitLogin().catch(() => {});
    }
    await this.waitForLoggedIn(15_000);
    await this.ensureNotFoundPageRecovered();
    await this.handlePostLoginOverlays();
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
    const phoneInput = this.page.locator('input[type="tel"], input[placeholder*="Phone"], input[placeholder*="900"]').first();
    await phoneInput.waitFor({ state: "visible", timeout: 8000 });
    await phoneInput.click({ force: true }).catch(() => {});
    await phoneInput.fill(phone);
  }

  async requestOtp() {
    const getCode = this.page.getByRole("button", { name: /^Get Code$|^Send$|^发送$|^获取$/i }).first();
    if (await getCode.isVisible({ timeout: 5000 }).catch(() => false)) {
      await getCode.click({ timeout: 3000 }).catch(() => {});
    }
  }

  async fillOtp(otp) {
    await this.page.waitForFunction(() => document.querySelectorAll("input").length >= 2, null, { timeout: 5000 }).catch(() => {});
    const inputs = this.page.locator("input:visible");
    const count = await inputs.count();
    const candidates = [];

    for (let index = 0; index < count; index += 1) {
      const input = inputs.nth(index);
      const meta = await input.evaluate((element) => ({
        type: element.getAttribute("type") || "",
        placeholder: element.getAttribute("placeholder") || "",
        value: element.value || "",
        autocomplete: element.getAttribute("autocomplete") || "",
      })).catch(() => null);
      if (!meta) continue;
      if (/tel|password/i.test(meta.type)) continue;
      if (/phone|password/i.test(meta.placeholder)) continue;
      candidates.push(input);
    }

    if (candidates.length >= String(otp).length) {
      for (let index = 0; index < String(otp).length; index += 1) {
        await candidates[index].fill(String(otp)[index]).catch(async () => {
          await candidates[index].click({ force: true });
          await this.page.keyboard.type(String(otp)[index]);
        });
      }
      return;
    }

    const target = candidates.at(-1) || (count >= 2 ? inputs.nth(count - 1) : null);
    if (!target) throw new Error("OTP input not found");
    await target.fill(String(otp)).catch(async () => {
      await target.click({ force: true });
      await this.page.keyboard.type(String(otp));
    });
  }

  async acceptLoginTerms() {
    const checkbox = this.page.locator('input[type="checkbox"]:visible').last();
    if (await checkbox.isVisible({ timeout: 1000 }).catch(() => false)) {
      await checkbox.check({ force: true }).catch(async () => {
        await checkbox.evaluate((element) => {
          element.checked = true;
          element.dispatchEvent(new Event("input", { bubbles: true }));
          element.dispatchEvent(new Event("change", { bubbles: true }));
          element.click();
        }).catch(() => {});
      });
      await this.page.waitForTimeout(300);
      return;
    }

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

  async prepareGuestHome() {
    await this.handleModals({ timeout: 5000 });
    await this.closeActivityPopups({ maxPasses: 2 });
    await this.closeDownloadBanner();
  }

  async useOtherAccountIfRemembered(phone) {
    const bodyText = await this.page.locator("body").innerText({ timeout: 1500 }).catch(() => "");
    if (!/Welcome Back|Other Accounts/i.test(bodyText)) return false;

    const normalizedPhone = String(phone).replace(/\D/g, "");
    const visiblePhone = bodyText.replace(/\D/g, "");
    if (normalizedPhone && visiblePhone.includes(normalizedPhone.slice(-8)) && bodyText.includes("SMS OTP")) return false;

    const result = await clickFirstByText(this.page, ["Other Accounts", "Other Account"], { timeout: 3000 });
    if (result.clicked) {
      await this.page.waitForTimeout(800);
      return true;
    }
    this.warn("remembered account dialog shown but Other Accounts was not clicked");
    return false;
  }

  async handlePostLoginOverlays() {
    await this.handleConfiguredClientOverlay("post_login_notice");
    await this.handleConfiguredClientOverlay("activity_popup");
    await this.handleConfiguredClientOverlay("download_app_banner");
    await this.closeActivityFloat();
  }

  async closeBasicAccountKycGate() {
    const marker = this.page.getByText(/Your current account type is a basic account/i).first();
    if (!(await marker.isVisible({ timeout: 5000 }).catch(() => false))) return false;

    const semantic = this.page.getByRole("button", { name: /^(Close|X|×)$/i }).first();
    if (await semantic.isVisible({ timeout: 1000 }).catch(() => false)) {
      await semantic.click({ timeout: 3000 });
      await marker.waitFor({ state: "hidden", timeout: 5000 }).catch(() => {});
      return true;
    }

    const clicked = await this.page.evaluate(() => {
      const viewport = { width: window.innerWidth, height: window.innerHeight };
      const candidates = Array.from(document.querySelectorAll("button, [role='button'], svg, div, span"));
      const target = candidates
        .map((element) => ({
          element,
          rect: element.getBoundingClientRect(),
          text: element.innerText?.trim() || element.getAttribute("aria-label") || "",
        }))
        .filter(({ rect }) => rect.width > 0 && rect.height > 0)
        .filter(({ rect }) => rect.left > viewport.width * 0.68 && rect.top < viewport.height * 0.2)
        .filter(({ text, rect }) => /^(×|X|Close)$/i.test(text) || (rect.width <= 56 && rect.height <= 56))
        .sort((a, b) => b.rect.right - a.rect.right || a.rect.top - b.rect.top)[0]?.element;
      if (!target) return false;
      target.click();
      return true;
    }).catch(() => false);
    if (clicked) await marker.waitFor({ state: "hidden", timeout: 5000 }).catch(() => {});
    return clicked;
  }

  async handleConfiguredClientOverlay(name) {
    const overlay = (this.modalConfig.clientOverlays || []).find((item) => item.name === name);
    if (!overlay) return false;
    let handled = false;
    const passes = overlay.maxPasses || 1;
    for (let pass = 0; pass < passes; pass += 1) {
      const bodyText = await this.page.locator("body").innerText({ timeout: 1500 }).catch(() => "");
      if (!(overlay.detectText || []).some((text) => bodyText.includes(text))) break;

      for (const text of overlay.buttonTexts || []) {
        const result = await clickFirstByText(this.page, [text], { timeout: 3000 });
        if (result.clicked) {
          handled = true;
          await this.page.waitForTimeout(800);
          break;
        }
      }

      if (overlay.close && name === "download_app_banner") {
        handled = (await this.closeDownloadBanner()) || handled;
      } else if (overlay.close) {
        handled = (await this.closeActivityPopups({ maxPasses: 1 })) || handled;
      }

      if (!handled) {
        this.warn(`overlay ${name} detected but not handled`);
        break;
      }
    }
    return handled;
  }

  async acceptNotice() {
    const result = await clickFirstByText(this.page, ["Agree"], { timeout: 5000 });
    if (result.clicked) {
      await this.page.waitForTimeout(800);
      return true;
    }
    return false;
  }

  async closeActivityPopups({ maxPasses = 2 } = {}) {
    let closed = 0;
    for (let pass = 0; pass < maxPasses; pass += 1) {
      const didClose = await this.clickVisibleCloseButton({ preferCenterPopup: true });
      if (!didClose) break;
      closed += 1;
      await this.page.waitForTimeout(800);
    }
    return closed;
  }

  async closeDownloadBanner() {
    const bannerVisible = await this.page.getByText(/Download Filbet APP/i).first().isVisible({ timeout: 1500 }).catch(() => false);
    if (!bannerVisible) return false;

    await this.closeActivityFloat();
    const clicked = await this.page.evaluate(() => {
      const bannerText = Array.from(document.querySelectorAll("div")).find((element) =>
        /Download Filbet APP/i.test(element.innerText || ""),
      );
      if (!bannerText) return false;
      const root = bannerText.closest("div") || bannerText;
      const buttons = Array.from(document.querySelectorAll("button, [role='button'], svg, div, span"));
      const close = buttons
        .map((element) => ({ element, rect: element.getBoundingClientRect(), text: element.innerText?.trim() || "" }))
        .filter(({ rect }) => rect.width > 0 && rect.height > 0)
        .filter(({ rect, text }) => text === "×" || text === "X" || (rect.right > root.getBoundingClientRect().right - 90 && rect.top < root.getBoundingClientRect().top + 90))
        .sort((a, b) => b.rect.right - a.rect.right)[0];
      if (!close) return false;
      close.element.click();
      return true;
    }).catch(() => false);
    if (!clicked) this.warn("download app banner shown but close button was not clicked");
    await this.page.waitForTimeout(500);
    return clicked;
  }

  async closeActivityFloat() {
    const clicked = await this.page.evaluate(() => {
      const candidates = Array.from(document.querySelectorAll("button, [role='button'], svg, div, span"));
      const closers = candidates
        .map((element) => {
          const rect = element.getBoundingClientRect();
          return { element, rect, text: element.innerText?.trim() || element.getAttribute("aria-label") || "" };
        })
        .filter(({ rect }) => rect.width > 0 && rect.height > 0 && rect.right > window.innerWidth - 120 && rect.bottom > window.innerHeight - 280)
        .filter(({ text, rect }) => /^(×|X|Close)$/i.test(text) || (rect.width <= 40 && rect.height <= 40));
      const target = closers.sort((a, b) => a.rect.top - b.rect.top)[0]?.element;
      if (!target) return false;
      target.click();
      return true;
    }).catch(() => false);
    if (clicked) await this.page.waitForTimeout(500);
    return clicked;
  }

  async clickVisibleCloseButton({ preferCenterPopup = false } = {}) {
    return this.page.evaluate((centerOnly) => {
      const viewport = { width: window.innerWidth, height: window.innerHeight };
      const candidates = Array.from(document.querySelectorAll("button, [role='button'], svg, div, span"));
      const closers = candidates
        .map((element) => {
          const rect = element.getBoundingClientRect();
          return { element, rect, text: element.innerText?.trim() || element.getAttribute("aria-label") || "" };
        })
        .filter(({ rect }) => rect.width > 0 && rect.height > 0)
        .filter(({ rect }) => !centerOnly || (rect.left > viewport.width * 0.2 && rect.right < viewport.width * 0.9))
        .filter(({ text, rect }) => /^(×|X|Close)$/i.test(text) || (rect.width <= 48 && rect.height <= 48 && rect.top < viewport.height * 0.85))
        .sort((a, b) => b.rect.top - a.rect.top);
      const target = closers[0]?.element;
      if (!target) return false;
      target.click();
      return true;
    }, preferCenterPopup).catch(() => false);
  }

  async acceptLoginConfirmation() {
    const bodyText = await this.page.locator("body").innerText({ timeout: 1500 }).catch(() => "");
    if (!bodyText.includes("Agree and Continue")) return false;

    const button = this.page.getByRole("button", { name: /Agree and Continue/i }).first();
    if (await button.isVisible({ timeout: 2500 }).catch(() => false)) {
      await button.click({ timeout: 3000 }).catch(async () => {
        await button.evaluate((element) => element.click()).catch(() => {});
      });
      await this.page.waitForTimeout(800);
      return true;
    }

    return this.page.evaluate(() => {
      const target = Array.from(document.querySelectorAll("button, [role='button'], div")).find(
        (element) => element.innerText?.trim() === "Agree and Continue",
      );
      if (!target) return false;
      target.click();
      return true;
    }).catch(() => false);
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
