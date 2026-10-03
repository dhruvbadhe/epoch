const { chromium } = require("@playwright/test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
(async () => {
  const browser = await chromium.launch({
    executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
    headless: true,
  });
  const page = await browser.newPage({
    viewport: { width: 1366, height: 768 },
    reducedMotion: "reduce",
  });
  const errors = [],
    requests = new Set();
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("request", (r) => {
    if (r.url().startsWith("http://localhost:8000"))
      requests.add(new URL(r.url()).pathname);
  });
  const screenshot = async (name) => {
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(300);
    await page.screenshot({
      path: `test-results/live-${name}.png`,
      fullPage: true,
    });
  };
  await page.goto("http://localhost:3000", { waitUntil: "networkidle" });
  await page
    .getByRole("heading", { name: "Sell today", exact: true })
    .waitFor();
  assert.equal(await page.locator("#quantity").inputValue(), "20");
  const card = await page.locator(".advice-card").innerText();
  assert.match(card, /₹1,089/);
  assert.match(card, /\+₹35/);
  assert.match(card, /Pimpalgaon/);
  assert.match(card, /40 of 124/);
  assert.equal(await page.getByText("Mock data", { exact: true }).count(), 0);
  assert.equal(await page.locator(".harvest-intro").count(), 0);
  assert.equal(
    await page.getByText("Before you dispatch", { exact: true }).count(),
    0,
  );
  assert.equal(
    await page.getByText("Heavy arrivals", { exact: true }).count(),
    0,
  );
  assert.ok((await page.locator(".advice-money").boundingBox()).y < 768);
  await screenshot("advice");
  await page.getByRole("button", { name: "FPO Plan", exact: true }).click();
  await page
    .getByRole("button", { name: "Build the plan", exact: true })
    .click();
  await page.getByText("FPO money in hand", { exact: true }).waitFor();
  await page.getByRole("checkbox", { name: "Pimpalgaon", exact: true }).check();
  await page.getByText(/Blocking Pimpalgaon changes FPO money/).waitFor();
  assert.ok(await page.locator(".reason-cell").count());
  await screenshot("fpo");
  await page.getByRole("button", { name: "Evidence", exact: true }).click();
  for (const crop of ["onion", "tomato", "soybean"]) {
    await page.getByLabel("Evidence crop").selectOption(crop);
    await page.waitForTimeout(700);
    await page
      .getByText("Holds won / lost / unscored", { exact: true })
      .waitFor();
    if (crop === "tomato")
      assert.match(
        await page.locator(".validation-panel").innerText(),
        /not enough data/,
      );
  }
  await page.getByLabel("Evidence crop").selectOption("onion");
  await page.waitForTimeout(600);
  await screenshot("evidence");
  await page.getByRole("button", { name: "Info", exact: true }).click();
  await page
    .getByRole("heading", {
      name: "Today’s net options and previous-day prices",
    })
    .waitFor();
  assert.equal(await page.locator(".growth-controls button").count(), 7);
  await screenshot("info");
  for (const endpoint of [
    "/advise",
    "/fpo/plan",
    "/backtest",
    "/mandis",
    "/villages",
    "/config",
  ])
    assert.ok(requests.has(endpoint), endpoint);
  assert.deepEqual(errors, []);
  await page.getByRole("button", { name: "Advice", exact: true }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(700);
  assert.ok(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  );
  await page.screenshot({
    path: "test-results/live-mobile.png",
    fullPage: true,
  });
  const offline = await browser.newPage();
  await offline.route("http://localhost:8000/**", (r) => r.abort());
  await offline.goto("http://localhost:3000", { waitUntil: "networkidle" });
  await offline.getByText("Mock data", { exact: true }).first().waitFor();
  const report = {
    onion: {
      action: "sell_now",
      mandi: "Pimpalgaon",
      net: 1089,
      gain: 35,
      date: "2025-09-21",
    },
    endpoints: [...requests],
    errors,
    checks: [
      "laptop above-fold advice",
      "FPO closure and reasons",
      "all evidence crops and null metric",
      "Info history",
      "mobile overflow",
      "offline badge",
    ],
  };
  fs.writeFileSync(
    "test-results/live-verification.json",
    JSON.stringify(report, null, 2),
  );
  console.log(JSON.stringify(report, null, 2));
  await browser.close();
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
