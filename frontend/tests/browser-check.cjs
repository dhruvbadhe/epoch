const { chromium } = require("@playwright/test");
const fs = require("node:fs");
const path = require("node:path");
(async () => {
  const browser = await chromium.launch({
    executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
    headless: true,
  });
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1100 },
  });
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("http://localhost:3000", { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: /Hold.*14 days/ }).waitFor();
  await page.locator(".forecast-panel .recharts-surface").waitFor();
  await page.screenshot({
    path: "test-results/advice-desktop.png",
    fullPage: true,
  });
  await page.screenshot({
    path: "test-results/advice-preview.png",
    fullPage: false,
  });
  await page.getByRole("button", { name: "Next options page" }).click();
  await page.getByText(/Showing 9–16/).waitFor();
  await page.getByRole("button", { name: "Previous options page" }).click();
  await page.getByRole("checkbox", { name: "Selling today only" }).check();
  await page.getByRole("checkbox", { name: "Selling today only" }).uncheck();
  await page
    .getByRole("textbox", { name: "Search mandis" })
    .fill("does-not-exist");
  await page.getByRole("heading", { name: "No matching options" }).waitFor();
  await page.getByRole("textbox", { name: "Search mandis" }).fill("");
  await page.getByRole("button", { name: "मराठी", exact: true }).click();
  await page.getByRole("heading", { name: /थांबा/ }).waitFor();
  await page.getByRole("button", { name: "EN", exact: true }).click();
  await page.locator("#cash").selectOption("3");
  await page.waitForFunction(
    () =>
      !document.querySelector(".action-line")?.textContent.includes("14 days"),
  );
  await page.locator("#crop").selectOption("tomato");
  await page.locator("#freshness").selectOption("2");
  await page
    .getByRole("heading", { name: "Sell today", exact: true })
    .waitFor();
  await page.locator("#quantity").fill("0");
  await page.getByText("Enter a quantity greater than zero.").waitFor();
  await page.locator("#quantity").fill("15");
  await page
    .getByRole("heading", { name: "Sell today", exact: true })
    .waitFor();
  await page.getByRole("button", { name: "FPO Plan", exact: true }).click();
  await page.getByRole("button", { name: "Build the plan" }).click();
  await page.getByRole("heading", { name: "Where each lot goes" }).waitFor();
  await page.screenshot({
    path: "test-results/fpo-desktop.png",
    fullPage: true,
  });
  const firstMandi = await page
    .locator("div:not([hidden]) > .tab-content")
    .last()
    .locator("table")
    .nth(1)
    .locator("tbody tr")
    .first()
    .locator("td")
    .nth(2)
    .locator("strong")
    .textContent();
  await page
    .locator(".mandi-checkboxes")
    .getByLabel(firstMandi, { exact: true })
    .check();
  await page.getByText(/member routes changed/).waitFor();
  await page.getByRole("button", { name: "Evidence", exact: true }).click();
  await page.getByRole("heading", { name: "The strategy ladder" }).waitFor();
  await page.screenshot({
    path: "test-results/evidence-desktop.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Assumptions", exact: true }).click();
  await page.locator('[id="transport.loading_per_qtl"]').fill("45");
  await page.getByRole("button", { name: "Apply assumptions" }).click();
  await page.getByText(/You’ve changed assumptions/).waitFor();
  await page
    .getByRole("button", { name: "Farmer queries", exact: true })
    .click();
  await page.getByText("…4521", { exact: true }).waitFor();
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: "Advice", exact: true }).click();
  if ((await page.locator("#quantity").inputValue()) !== "15")
    throw new Error("Advice state lost between tabs");
  await page.locator("#crop").selectOption("onion");
  await page.locator("#cash").selectOption("");
  await page.getByRole("heading", { name: /Hold/ }).waitFor();
  await page.locator(".forecast-panel .recharts-surface").waitFor();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(200);
  await page.screenshot({
    path: "test-results/advice-mobile.png",
    fullPage: true,
  });
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > window.innerWidth,
  );
  if (overflow) throw new Error("Mobile page has horizontal overflow");
  await page.getByRole("button", { name: "Toggle navigation" }).click();
  await page.getByRole("button", { name: "FPO Plan", exact: true }).click();
  await page.screenshot({
    path: "test-results/fpo-mobile.png",
    fullPage: true,
  });
  await browser.close();
  if (errors.length) throw new Error(errors.join("\n"));
  console.log(
    "Browser checks passed: all tabs, languages, cash/freshness, quantity validation, pagination/search, closure rerouting, assumptions, queries, state persistence, mobile overflow, and no browser errors.",
  );
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
