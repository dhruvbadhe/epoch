const { chromium } = require("@playwright/test");
(async () => {
  const browser = await chromium.launch({
    executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
    headless: true,
  });
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1100 },
  });
  page.on("pageerror", (error) => console.log("PAGE ERROR:", error.message));
  page.on("console", (message) => {
    if (message.type() === "error")
      console.log("CONSOLE ERROR:", message.text());
  });
  page.on("requestfailed", (request) =>
    console.log("FAILED:", request.url(), request.failure()?.errorText),
  );
  const response = await page.goto("http://localhost:3000", {
    waitUntil: "networkidle",
  });
  await page.waitForTimeout(1500);
  console.log("STATUS:", response.status());
  console.log("HEADING:", await page.locator(".action-line").ariaSnapshot());
  console.log("CONTENT:", await page.locator("body").innerText());
  await page.screenshot({
    path: "test-results/production-inspection.png",
    fullPage: true,
  });
  await browser.close();
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
