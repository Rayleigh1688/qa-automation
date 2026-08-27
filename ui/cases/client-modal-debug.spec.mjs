import fs from "node:fs";
import path from "node:path";
import { test } from "@playwright/test";
import { loadEnv } from "../framework/env.mjs";

loadEnv();

test("debug responsible gaming modal structure", async ({ page }) => {
  await page.goto("/login", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(2000);
  const result = await page.evaluate(() => {
    const visible = (el) => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
    const modal = document.querySelector('[data-family-name="pagcor"]') || document.body;
    return {
      bodyText: document.body.innerText.slice(0, 3000),
      inputs: Array.from(document.querySelectorAll("input")).map((el, index) => ({
        index,
        type: el.type,
        checked: el.checked,
        disabled: el.disabled,
        visible: visible(el),
        outerHTML: el.outerHTML.slice(0, 800),
      })),
      buttons: Array.from(document.querySelectorAll("button")).map((el, index) => ({
        index,
        text: el.innerText,
        disabled: el.disabled,
        ariaDisabled: el.getAttribute("aria-disabled"),
        visible: visible(el),
        outerHTML: el.outerHTML.slice(0, 800),
      })),
      modalHTML: modal.outerHTML.slice(0, 6000),
      agreeTree: (() => {
        const agreeText = Array.from(modal.querySelectorAll("div")).find((element) =>
          element.innerText?.trim().startsWith("I agree to all"),
        );
        const rows = [];
        let current = agreeText;
        for (let depth = 0; current && depth < 5; depth += 1) {
          rows.push({
            depth,
            tag: current.tagName,
            text: current.innerText?.slice(0, 300),
            className: current.className,
            childCount: current.children.length,
            outerHTML: current.outerHTML.slice(0, 1500),
          });
          current = current.parentElement;
        }
        return rows;
      })(),
    };
  });
  const out = path.resolve("ui/results/client-modal-debug.json");
  fs.mkdirSync(path.dirname(out), { recursive: true });
  fs.writeFileSync(out, JSON.stringify(result, null, 2));
  await test.info().attach("client-modal-debug", {
    body: JSON.stringify(result, null, 2),
    contentType: "application/json",
  });
});
