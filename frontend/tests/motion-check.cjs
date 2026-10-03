const { chromium } = require("@playwright/test");
const assert = require("node:assert/strict");
(async () => {
  const browser = await chromium.launch({
    executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
    headless: true,
  });
  const page = await browser.newPage({
    viewport: { width: 1366, height: 768 },
  });
  await page.goto("http://localhost:3000", { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "Info", exact: true }).click();
  const story = page.locator(".harvest-intro");
  await story.waitFor();
  const bounds = await story.boundingBox();
  const storyTop = bounds.y + (await page.evaluate(() => scrollY));
  for (const [fraction, chapter] of [
    [0, 0],
    [0.5, 3],
    [1, 6],
  ]) {
    await page.evaluate(
      ({ top, height, fraction }) =>
        window.scrollTo({
          top: top - 88 + (height - innerHeight + 88) * fraction,
          behavior: "instant",
        }),
      { top: storyTop, height: bounds.height, fraction },
    );
    await page.waitForTimeout(200);
    assert.equal(Number(await story.getAttribute("data-chapter")), chapter);
    await page.screenshot({
      path: "test-results/info-growth-" + chapter + ".png",
    });
  }
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.waitForTimeout(200);
  assert.equal(Number(await story.getAttribute("data-chapter")), 6);
  await browser.close();
  console.log("Info seed, sprout, plant and reduced-motion checks passed");
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
