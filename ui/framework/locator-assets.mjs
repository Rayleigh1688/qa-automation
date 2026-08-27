function textPreview(value, max = 120) {
  return String(value || "").replace(/\s+/g, " ").trim().slice(0, max);
}

export async function collectLocatorAssets(page, { max = 300 } = {}) {
  return page.evaluate((limit) => {
    const cssEscape = window.CSS?.escape || ((value) => String(value).replace(/["\\]/g, "\\$&"));
    const textPreview = (value, max = 120) => String(value || "").replace(/\s+/g, " ").trim().slice(0, max);
    const isVisible = (el) => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
    const selectorFor = (el) => {
      const testId = el.getAttribute("data-testid") || el.getAttribute("data-test-id");
      if (testId) return `[data-testid="${cssEscape(testId)}"]`;
      const id = el.getAttribute("id");
      if (id) return `#${cssEscape(id)}`;
      const name = el.getAttribute("name");
      if (name) return `${el.tagName.toLowerCase()}[name="${cssEscape(name)}"]`;
      const placeholder = el.getAttribute("placeholder");
      if (placeholder) return `${el.tagName.toLowerCase()}[placeholder="${cssEscape(placeholder)}"]`;
      const role = el.getAttribute("role");
      const text = textPreview(el.innerText || el.textContent, 40);
      if (role && text) return `[role="${cssEscape(role)}"]:has-text("${cssEscape(text)}")`;
      if (text && ["BUTTON", "A"].includes(el.tagName)) return `${el.tagName.toLowerCase()}:has-text("${cssEscape(text)}")`;
      return el.tagName.toLowerCase();
    };

    const candidates = Array.from(
      document.querySelectorAll(
        [
          "button",
          "a",
          "input",
          "select",
          "textarea",
          "[role=\"button\"]",
          "[role=\"tab\"]",
          "[role=\"link\"]",
          "[data-testid]",
          "[data-test-id]"
        ].join(","),
      ),
    );

    return candidates
      .filter(isVisible)
      .slice(0, limit)
      .map((el, index) => {
        const rect = el.getBoundingClientRect();
        return {
          index,
          tag: el.tagName.toLowerCase(),
          role: el.getAttribute("role") || "",
          text: textPreview(el.innerText || el.textContent),
          ariaLabel: el.getAttribute("aria-label") || "",
          placeholder: el.getAttribute("placeholder") || "",
          name: el.getAttribute("name") || "",
          type: el.getAttribute("type") || "",
          href: el.getAttribute("href") || "",
          testId: el.getAttribute("data-testid") || el.getAttribute("data-test-id") || "",
          enabled: !el.disabled && el.getAttribute("aria-disabled") !== "true",
          selectorHint: selectorFor(el),
          box: {
            x: Math.round(rect.x),
            y: Math.round(rect.y),
            width: Math.round(rect.width),
            height: Math.round(rect.height)
          }
        };
      });
  }, max);
}

export async function pageSnapshot(page, name, extra = {}) {
  const text = await page.locator("body").innerText({ timeout: 8000 }).catch(() => "");
  const assets = await collectLocatorAssets(page);
  return {
    name,
    url: page.url(),
    title: await page.title().catch(() => ""),
    text: textPreview(text, 4000),
    locatorCount: assets.length,
    locators: assets,
    ...extra,
  };
}
