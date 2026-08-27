function textMatcher(text) {
  return new RegExp(String(text).replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "i");
}

export async function clickFirstBySelector(page, selectors = [], { timeout = 2500, force = false } = {}) {
  for (const selector of selectors) {
    const locator = page.locator(selector).first();
    if (await locator.isVisible({ timeout }).catch(() => false)) {
      try {
        await locator.click({ timeout, force });
        return { clicked: true, selector };
      } catch {
        continue;
      }
    }
  }
  return { clicked: false, selector: "" };
}

export async function clickFirstByText(page, texts = [], { timeout = 2500, force = false } = {}) {
  for (const text of texts) {
    const matcher = text instanceof RegExp ? text : textMatcher(text);
    const locators = [
      page.getByRole("button", { name: matcher }),
      page.getByRole("link", { name: matcher }),
      page.locator(`button:has-text("${String(text).replace(/"/g, '\\"')}")`).first(),
      page.locator(`a:has-text("${String(text).replace(/"/g, '\\"')}")`).first(),
      page.locator(`[role="button"]:has-text("${String(text).replace(/"/g, '\\"')}")`).first(),
    ];
    for (const locator of locators) {
      if (await locator.isVisible({ timeout }).catch(() => false)) {
        try {
          await locator.click({ timeout, force });
          return { clicked: true, text: String(text) };
        } catch {
          continue;
        }
      }
    }

    if (!(text instanceof RegExp)) {
      const clicked = await page.evaluate((targetText) => {
        const candidates = Array.from(document.querySelectorAll("button, a, [role='button'], [role='link'], div, span"));
        const target = candidates.find((element) => {
          const text = element.innerText?.trim();
          if (text !== targetText) return false;
          const rect = element.getBoundingClientRect();
          return rect.width > 0 && rect.height > 0 && rect.bottom >= 0 && rect.top <= window.innerHeight;
        });
        if (!target) return false;
        target.click();
        return true;
      }, String(text)).catch(() => false);
      if (clicked) return { clicked: true, text: String(text), mode: "dom_text" };
    }
  }
  return { clicked: false, text: "" };
}

export async function clickConfiguredTarget(page, target = {}, options = {}) {
  const bySelector = await clickFirstBySelector(page, target.selectors || [], options);
  if (bySelector.clicked) return { ...bySelector, mode: "selector", value: bySelector.selector };

  const byText = await clickFirstByText(page, target.texts || [], options);
  if (byText.clicked) return { ...byText, mode: "text", value: byText.text };

  return { clicked: false, mode: "", value: "" };
}

async function waitForModalText(page, modalConfig = {}, timeout = 3000) {
  const texts = (modalConfig.modals || []).flatMap((modal) => modal.detectText || []);
  if (!texts.length || timeout <= 0) return "";
  await page.waitForFunction(
    (candidates) => candidates.some((text) => document.body.innerText.includes(text)),
    texts,
    { timeout },
  ).catch(() => {});
  return page.locator("body").innerText({ timeout: 2000 }).catch(() => "");
}

export async function handleConfiguredModals(page, modalConfig = {}, { timeout = 3000 } = {}) {
  const handled = [];
  const bodyText = await waitForModalText(page, modalConfig, timeout);
  for (const modal of modalConfig.modals || []) {
    const shown = (modal.detectText || []).some((text) => bodyText.includes(text));
    if (!shown) continue;

    let checked = false;
    if (modal.name === "responsible_gaming_pagcor") {
      const box = await page.evaluate(() => {
        const modalRoot = document.querySelector('[data-family-name="pagcor"]');
        if (!modalRoot) return null;
        const agreeText = Array.from(modalRoot.querySelectorAll("div")).find((element) =>
          element.innerText?.trim().startsWith("I agree to all"),
        );
        const row = agreeText;
        if (!row) return null;
        const rect = row.getBoundingClientRect();
        return {
          x: rect.x + Math.min(24, rect.width / 4),
          y: rect.y + rect.height / 2,
          width: rect.width,
          height: rect.height,
        };
      }).catch(() => false);
      if (box && box.width > 0 && box.height > 0) {
        await page.mouse.click(box.x, box.y);
        checked = true;
      }
    }

    for (const selector of modal.accept?.checkboxSelectors || []) {
      const locator = page.locator(selector).last();
      if ((await locator.count().catch(() => 0)) > 0) {
        await locator.check({ force: true }).catch(async () => {
          await locator.evaluate((element) => {
            element.checked = true;
            element.dispatchEvent(new Event("input", { bubbles: true }));
            element.dispatchEvent(new Event("change", { bubbles: true }));
            element.click();
          }).catch(() => {});
        });
        await locator.evaluate((element) => {
          if (!element.checked) element.checked = true;
          element.dispatchEvent(new Event("input", { bubbles: true }));
          element.dispatchEvent(new Event("change", { bubbles: true }));
        }).catch(() => {});
        checked = true;
        break;
      }
    }

    if (!checked && !(modal.accept?.checkboxSelectors || []).length) {
      for (const text of modal.accept?.checkboxTexts || []) {
        const matcher = textMatcher(text);
        const label = page.getByText(matcher).last();
        if (await label.isVisible({ timeout: 1000 }).catch(() => false)) {
          await label.click({ force: true }).catch(() => {});
          checked = true;
          break;
        }
      }
    }

    let accepted = false;
    for (const text of modal.accept?.buttonTexts || []) {
      const button = page.getByRole("button", { name: textMatcher(text) }).first();
      await button.waitFor({ state: "visible", timeout: 1500 }).catch(() => {});
      await page.waitForTimeout(500);
      if (await button.isEnabled().catch(() => false)) {
        try {
          await button.click({ timeout: 3000 });
          accepted = true;
        } catch {
          accepted = await button.evaluate((element) => {
            element.click();
            return true;
          }).catch(() => false);
        }
        break;
      }
    }

    handled.push({ name: modal.name, accepted });
    await page.waitForTimeout(800);
  }
  return handled;
}

export async function openConfiguredEntry(page, pageConfig, modalConfig = {}) {
  const entry = pageConfig.entry || {};
  const paths = entry.paths || (entry.path ? [entry.path] : []);
  if (paths.length) {
    const openedPaths = [];
    for (const candidatePath of paths) {
      await page.goto(candidatePath, { waitUntil: "domcontentloaded" });
      await page.waitForTimeout(1500);
      await handleConfiguredModals(page, modalConfig);
      openedPaths.push({ path: candidatePath, url: page.url() });
    }
    return { mode: "path", value: paths.at(-1), clicked: false, paths: openedPaths };
  }

  if (entry.path) {
    await page.goto(entry.path, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(1500);
    await handleConfiguredModals(page, modalConfig);
    return { mode: "path", value: entry.path, clicked: false };
  }

  await handleConfiguredModals(page, modalConfig);
  const preResults = [];
  for (const preEntry of entry.preEntry || []) {
    const preResult = await clickConfiguredTarget(page, preEntry, { timeout: 2500, force: Boolean(preEntry.force) });
    preResults.push(preResult);
    await page.waitForTimeout(preEntry.waitMs || 800);
    await handleConfiguredModals(page, modalConfig);
  }

  const result = await clickConfiguredTarget(page, entry, { timeout: 2500, force: Boolean(entry.force) });
  await page.waitForTimeout(1500);
  await handleConfiguredModals(page, modalConfig);
  return { mode: result.mode, value: result.value, clicked: result.clicked, preResults };
}
