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
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("http://localhost:3000", { waitUntil: "networkidle" });
  const card = () =>
    page.getByRole("region", { name: "Local weather & storage", exact: true });
  await card().getByText("Air temperature", { exact: true }).waitFor();
  const live = await card().innerText();
  assert.match(live, /Weather updated:/);
  assert.match(live, /Weather data by Open-Meteo/);
  assert.match(live, /21 Sep 2025/);
  const recommendation = await page.locator(".advice-money").innerText();
  assert.match(recommendation, /₹1,089/);
  assert.match(await page.locator(".advice-gain").innerText(), /₹35/);
  await card().screenshot({ path: "test-results/weather-card-desktop.png" });

  // Controlled provider failures and partial values must never alter engine advice.
  let mode = "zero";
  let calls = 0;
  await page.route(/\/weather\?/, async (route) => {
    calls++;
    const village = new URL(route.request().url()).searchParams.get("village");
    if (mode === "error")
      return route.fulfill({
        status: 503,
        contentType: "application/json",
        body: '{"error":"Weather service unavailable"}',
      });
    if (mode === "offline") return route.abort();
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        village,
        available: true,
        time: "2026-10-03T09:15",
        temperature_c: mode === "partial" ? null : 0,
        relative_humidity_pct: 0,
        attribution: "Weather data by Open-Meteo.com",
        label: "context only",
      }),
    });
  });
  await card()
    .getByRole("button", { name: "Refresh weather", exact: true })
    .click();
  await card().getByText("0°C", { exact: true }).waitFor();
  assert.match(await card().innerText(), /0%/);
  assert.equal(
    calls,
    1,
    "One weather request per refresh; no duplicate AdviceCard request",
  );
  mode = "partial";
  await card()
    .getByRole("button", { name: "Refresh weather", exact: true })
    .click();
  await card().getByText("Not enough data", { exact: true }).waitFor();
  assert.equal(await page.locator(".advice-money").innerText(), recommendation);
  mode = "error";
  await card()
    .getByRole("button", { name: "Refresh weather", exact: true })
    .click();
  await card().getByText("Weather unavailable", { exact: true }).waitFor();
  assert.equal(await page.locator(".advice-money").innerText(), recommendation);
  await card().screenshot({
    path: "test-results/weather-card-unavailable.png",
  });
  mode = "offline";
  await card()
    .getByRole("button", { name: "Refresh weather", exact: true })
    .click();
  await card().getByText("Weather unavailable", { exact: true }).waitFor();
  mode = "zero";
  await card()
    .getByRole("button", { name: "Refresh weather", exact: true })
    .click();
  await card().getByText("0°C", { exact: true }).waitFor();
  await page.locator("#village").selectOption("Lasalgaon");
  await card().getByText("Lasalgaon", { exact: true }).waitFor();
  await card().getByText("0°C", { exact: true }).waitFor();
  await page.locator("#freshness").selectOption("false");
  await card()
    .getByText(/Not cured: check drying/)
    .waitFor();
  await page.locator("#crop").selectOption("tomato");
  await page.locator("#freshness").selectOption("2");
  await card()
    .getByText(/Picked 3\+ days ago: prioritise inspection/)
    .waitFor();
  await page.locator("#crop").selectOption("soybean");
  await page.locator("#freshness").selectOption("true");
  await card()
    .getByText(/Fully dried: keep moisture out/)
    .waitFor();
  await page.getByRole("button", { name: "मराठी", exact: true }).click();
  await page
    .getByRole("region", { name: "स्थानिक हवामान आणि साठवण" })
    .waitFor();
  await page.getByRole("button", { name: "हिंदी", exact: true }).click();
  await page.getByRole("region", { name: "स्थानीय मौसम और भंडारण" }).waitFor();
  await page.getByRole("button", { name: "EN", exact: true }).click();
  await card().waitFor();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(250);
  assert.ok(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  );
  await card().screenshot({ path: "test-results/weather-card-mobile.png" });
  await page.unroute(/\/weather\?/);
  await page.locator("#village").selectOption("Niphad");
  await page.locator("#crop").selectOption("onion");
  await page.locator("#freshness").selectOption("true");
  await card().getByText("Air temperature", { exact: true }).waitFor();
  await card()
    .getByText(/Cured and ventilated: maintain airflow/)
    .waitFor();
  await page.setViewportSize({ width: 1366, height: 768 });
  await card().screenshot({ path: "test-results/weather-card-desktop.png" });
  assert.deepEqual(errors, []);
  const report = {
    liveWeatherCard: live,
    checks: [
      "real provider data",
      "recommendation unchanged",
      "zero values",
      "missing temperature",
      "HTTP failure",
      "offline and recovery",
      "village change",
      "all crop conditions",
      "English Marathi Hindi",
      "mobile overflow",
    ],
    errors,
  };
  fs.writeFileSync(
    "test-results/weather-verification.json",
    JSON.stringify(report, null, 2),
  );
  console.log(JSON.stringify(report, null, 2));
  await browser.close();
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
