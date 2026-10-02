import { strict as assert } from "node:assert";
import { test } from "node:test";
import {
  demoAdvice,
  demoPlan,
  holdLimit,
  mergeConfig,
  sampleLots,
} from "../lib/demo";
import {
  ApiError,
  getAdvice,
  getBacktest,
  getConfig,
  getForecast,
  getMandis,
  getQueries,
  getVillages,
} from "../lib/api";
import type { AdviceRequest, PlanRequest } from "../lib/types";
const request: AdviceRequest = {
  crop: "onion",
  quantity_qtl: 10,
  village: "Niphad",
  lot_condition: null,
  cash_needed_in_days: null,
  blocked_mandis: [],
  overrides: null,
  lang: "en",
};
const planRequest: PlanRequest = {
  lots: sampleLots,
  blocked_mandis: [],
  mandi_cap_qtl_per_day: null,
  collection_centre: null,
  overrides: null,
};
test("advice respects cash and freshness, and gain components reconcile", () => {
  const hold = demoAdvice(request);
  assert.equal(hold.action, "hold");
  assert.equal(hold.days, 14);
  const cash = demoAdvice({ ...request, cash_needed_in_days: 3 });
  assert.ok(cash.days <= 3);
  const oldTomato = demoAdvice({
    ...request,
    crop: "tomato",
    lot_condition: 2,
  });
  assert.equal(oldTomato.action, "sell_now");
  assert.equal(oldTomato.days, 0);
  assert.equal(oldTomato.break_even_price, null);
  assert.equal(oldTomato.confidence, "low");
  for (const advice of [hold, cash, oldTomato]) {
    assert.equal(
      advice.gain_from_mandi + advice.gain_from_waiting,
      advice.gain_vs_baseline,
    );
    assert.equal(
      advice.why.price -
        advice.why.spoilage_loss -
        advice.why.transport -
        advice.why.storage -
        advice.why.fees,
      advice.net_per_qtl,
    );
    assert.ok(
      advice.net_low <= advice.net_per_qtl &&
        advice.net_per_qtl <= advice.net_high,
    );
    assert.equal(advice.hold_success_rate, null);
  }
});
test("language, merged assumptions, and blocked markets change the response", () => {
  assert.match(demoAdvice({ ...request, lang: "mr" }).message, /दिवस/);
  assert.match(demoAdvice({ ...request, lang: "hi" }).message, /हाथ/);
  const defaultAdvice = demoAdvice(request);
  const custom = demoAdvice({
    ...request,
    overrides: { transport: { loading_per_qtl: 500 } },
  });
  assert.equal(custom.assumptions_default, false);
  assert.ok(custom.net_per_qtl < defaultAdvice.net_per_qtl);
  assert.equal(holdLimit("tomato", 2, mergeConfig(null)), 0);
  assert.equal(
    mergeConfig({ transport: { loading_per_qtl: 30 } }).transport
      .rate_per_km_per_qtl,
    2,
  );
  const blocked = demoAdvice({
    ...request,
    blocked_mandis: [defaultAdvice.mandi],
  });
  assert.notEqual(blocked.mandi, defaultAdvice.mandi);
  assert.ok(blocked.options.every((o) => o.mandi !== defaultAdvice.mandi));
});
test("FPO costs, capacity, quantity conservation and baselines reconcile", () => {
  const plan = demoPlan(planRequest);
  assert.equal(plan.unplaced.length, 0);
  assert.equal(
    plan.total_net,
    plan.assignments.reduce((s, a) => s + a.net_total, 0),
  );
  assert.equal(plan.gain_vs_baseline, plan.total_net - plan.baseline_total);
  for (const lot of sampleLots) {
    const assignments = plan.assignments.filter((a) => a.member === lot.member);
    assert.equal(
      assignments.reduce((s, a) => s + a.quantity_qtl, 0),
      lot.quantity_qtl,
    );
    assert.ok(
      assignments.every(
        (a) =>
          a.sell_day <=
            holdLimit(lot.crop, lot.lot_condition, mergeConfig(null)) &&
          (!lot.cash_needed_in_days || a.sell_day <= lot.cash_needed_in_days),
      ),
    );
    const advice = demoAdvice({ ...request, ...lot });
    assert.ok(
      assignments.every(
        (a) => a.baseline_today.net === advice.baseline_today.net,
      ),
    );
  }
  for (const truck of plan.trucks) {
    assert.equal(
      truck.cost,
      plan.assignments
        .filter((a) => a.mandi === truck.mandi && a.sell_day === truck.sell_day)
        .reduce((s, a) => s + a.truck_share, 0),
    );
    assert.ok(
      truck.quantity_qtl <= mergeConfig(null).fpo.mandi_cap_qtl_per_day,
    );
  }
  const closed = plan.assignments[0].mandi;
  const reroute = demoPlan({ ...planRequest, blocked_mandis: [closed] });
  assert.ok(reroute.assignments.every((a) => a.mandi !== closed));
  const capped = demoPlan({ ...planRequest, mandi_cap_qtl_per_day: 5 });
  for (const truck of capped.trucks) assert.ok(truck.quantity_qtl <= 5);
  assert.equal(
    capped.assignments.reduce((s, a) => s + a.quantity_qtl, 0) +
      capped.unplaced.reduce((s, a) => s + a.quantity_qtl, 0),
    sampleLots.reduce((s, l) => s + l.quantity_qtl, 0),
  );
});
test("mock endpoint shapes and null evidence remain contract-compatible", async () => {
  const [advice, backtest, forecast, mandis, villages, config, queries] =
    await Promise.all([
      getAdvice(request),
      getBacktest("tomato"),
      getForecast("soybean", "Pimpalgaon"),
      getMandis(),
      getVillages(),
      getConfig(),
      getQueries(),
    ]);
  assert.equal(advice.mock, true);
  assert.equal(backtest.data.crop, "tomato");
  assert.equal(backtest.data.avg_gain_per_qtl, null);
  assert.equal(backtest.data.hold_success_rate, null);
  assert.ok(backtest.data.ladder.every((l) => l.avg_net === null));
  assert.ok(
    forecast.data.forecast.every(
      (f) => f.price_low <= f.price_mid && f.price_mid <= f.price_high,
    ),
  );
  assert.ok(mandis.data.length >= 10);
  assert.ok(villages.data.length >= 20);
  assert.ok(config.data.fpo.truck_capacity_qtl > 0);
  assert.ok(queries.data.every((q) => q.sender.startsWith("…")));
});
