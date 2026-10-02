/** Fixture-driven UI simulator. These values are illustrative, never measured results. */
import configFixture from "@/mock/config.json";
import adviceFixture from "@/mock/advise.json";
import forecastFixture from "@/mock/forecast.json";
import planFixture from "@/mock/fpo_plan.json";
import mandiFixture from "@/mock/mandis.json";
import villageFixture from "@/mock/villages.json";
import markets from "@/mock/market-fixtures.json";
import type {
  Advice,
  AdviceRequest,
  Config,
  Crop,
  Forecast,
  Lot,
  Mandi,
  MandiOption,
  Overrides,
  Plan,
  PlanRequest,
} from "./types";
import { rupees } from "./format";
export const defaultConfig = configFixture as Config;
export const sampleLots = markets.sample_lots as Lot[];
export function mergeConfig(overrides: Overrides): Config {
  const merge = (
    base: Record<string, unknown>,
    patch: Record<string, unknown>,
  ): Record<string, unknown> => {
    const result = { ...base };
    for (const [key, value] of Object.entries(patch)) {
      if (value === undefined) continue;
      result[key] =
        value && typeof value === "object" && !Array.isArray(value)
          ? merge(
              (base[key] ?? {}) as Record<string, unknown>,
              value as Record<string, unknown>,
            )
          : value;
    }
    return result;
  };
  return merge(
    structuredClone(defaultConfig) as unknown as Record<string, unknown>,
    (overrides ?? {}) as Record<string, unknown>,
  ) as unknown as Config;
}
export function holdLimit(
  crop: Crop,
  condition: Lot["lot_condition"],
  config: Config,
): number {
  const rule = config.hold_limit_days[crop];
  if (condition === null) return rule.default;
  if (crop === "tomato")
    return (
      config.hold_limit_days.tomato.answers[Number(condition)] ?? rule.default
    );
  return (
    config.hold_limit_days[crop].answers[String(condition)] ?? rule.default
  );
}
function km(
  a: { lat: number; lon: number },
  b: { lat: number; lon: number },
  factor: number,
) {
  const rad = Math.PI / 180;
  const value =
    Math.sin(((b.lat - a.lat) * rad) / 2) ** 2 +
    Math.cos(a.lat * rad) *
      Math.cos(b.lat * rad) *
      Math.sin(((b.lon - a.lon) * rad) / 2) ** 2;
  return Math.round(
    6371 * 2 * Math.atan2(Math.sqrt(value), Math.sqrt(1 - value)) * factor,
  );
}
export function demoForecast(crop: Crop, mandi: string): Forecast {
  const price = (markets[crop] as Record<string, number>)[mandi];
  if (!price) throw new Error("No demo prices for this crop and mandi.");
  return {
    crop,
    mandi,
    prices_as_of: forecastFixture.prices_as_of,
    history: forecastFixture.history.map((row) => ({
      date: row.date,
      price: Math.round((row.price * price) / 1760),
    })),
    forecast: forecastFixture.forecast.map((row, i) => ({
      ...row,
      price_mid: Math.round(price * markets.forecast_multipliers[crop][i]),
      price_low: Math.round(
        price *
          (markets.forecast_multipliers[crop][i] -
            markets.forecast_spreads[crop][i]),
      ),
      price_high: Math.round(
        price *
          (markets.forecast_multipliers[crop][i] +
            markets.forecast_spreads[crop][i]),
      ),
      uses_baseline: markets.baseline_horizons.includes(row.horizon_days),
    })),
  };
}
function allOptions(
  request: AdviceRequest,
  config: Config,
  shared = false,
  origin?: { lat: number; lon: number },
): MandiOption[] {
  const village =
    origin ?? villageFixture.find((v) => v.village === request.village);
  if (!village) throw new Error("This village is not covered by the demo.");
  const limit = Math.min(
    holdLimit(request.crop, request.lot_condition, config),
    request.cash_needed_in_days ?? Infinity,
  );
  return (mandiFixture as Mandi[])
    .filter(
      (m) =>
        m.crops.includes(request.crop) &&
        !request.blocked_mandis.includes(m.mandi),
    )
    .flatMap((m) => {
      const distance = km(village, m, config.transport.road_factor);
      const transport = shared
        ? (config.fpo.truck_fixed_cost + distance * config.fpo.truck_per_km) /
            config.fpo.truck_capacity_qtl +
          config.fpo.first_mile_per_qtl
        : distance * config.transport.rate_per_km_per_qtl +
          config.transport.loading_per_qtl;
      const today = (markets[request.crop] as Record<string, number>)[m.mandi];
      const forecast = demoForecast(request.crop, m.mandi);
      const rows = [
        {
          horizon_days: 0,
          price_low: today,
          price_mid: today,
          price_high: today,
          uses_baseline: false,
        },
        ...forecast.forecast.filter(
          (row) =>
            config.horizons.includes(row.horizon_days) &&
            row.horizon_days <= limit &&
            !row.uses_baseline,
        ),
      ];
      return rows.map((row) => {
        const sellable =
          (1 - config.spoilage_per_day[request.crop]) ** row.horizon_days;
        const cost =
          transport +
          row.horizon_days * config.storage_cost_per_qtl_per_day[request.crop] +
          config.fees_per_qtl;
        const flags: MandiOption["flags"] = [];
        if (markets.stale_mandis.includes(m.mandi)) flags.push("stale");
        if (markets.glut_mandis.includes(m.mandi)) flags.push("glut");
        return {
          mandi: m.mandi,
          distance_km: distance,
          sell_day: row.horizon_days,
          price_low: row.price_low,
          price_mid: row.price_mid,
          price_high: row.price_high,
          transport_per_qtl: Math.round(transport),
          net_low: Math.round(row.price_low * sellable - cost),
          net_per_qtl: Math.round(row.price_mid * sellable - cost),
          net_high: Math.round(row.price_high * sellable - cost),
          flags,
        };
      });
    });
}
function message(
  advice: Advice,
  lang: AdviceRequest["lang"],
  crop: Crop,
): string {
  const amount = `${rupees(advice.net_per_qtl)}${advice.action === "hold" ? ` (${rupees(advice.net_low)}–${rupees(advice.net_high)})` : ""}`;
  const icon = advice.action === "hold" ? "🟢" : "🔴";
  if (lang === "mr")
    return `${icon} *${advice.days ? `${advice.days} दिवस थांबा` : "आज विका"} → ${advice.mandi}*\n💰 हातात अंदाजे ${amount}/क्विंटल\n📈 आज ${advice.baseline_today.mandi} बाजारापेक्षा ${rupees(advice.gain_vs_baseline)} जास्त${advice.break_even_price ? `\n⚠️ भाव ${rupees(advice.break_even_price)} च्या वर असेल तरच जा. निघण्यापूर्वी खात्री करा.` : ""}${advice.storage_tip ? `\n🌱 ${markets.storage_tips_mr[crop]}` : ""}\n🗓 ${advice.prices_as_of} च्या भावांनुसार · खात्री: ${advice.confidence === "high" ? "उच्च" : advice.confidence === "medium" ? "मध्यम" : "कमी"}`;
  if (lang === "hi")
    return `${icon} *${advice.days ? `${advice.days} दिन रुकें` : "आज बेचें"} → ${advice.mandi}*\n💰 हाथ में लगभग ${amount}/क्विंटल\n📈 आज ${advice.baseline_today.mandi} से ${rupees(advice.gain_vs_baseline)} अधिक${advice.break_even_price ? `\n⚠️ भाव ${rupees(advice.break_even_price)} से ऊपर हो तभी जाएं। भेजने से पहले जांचें।` : ""}${advice.storage_tip ? `\n🌱 ${markets.storage_tips_hi[crop]}` : ""}\n🗓 ${advice.prices_as_of} के भाव · भरोसा: ${advice.confidence === "high" ? "उच्च" : advice.confidence === "medium" ? "मध्यम" : "कम"}`;
  return `${icon} *${advice.days ? `Hold ${advice.days} days` : "Sell today"} → ${advice.mandi}*\n💰 Estimated ${amount}/quintal in hand\n📈 ${rupees(advice.gain_vs_baseline)} more than ${advice.baseline_today.mandi} today${advice.break_even_price ? `\n⚠️ Go only if the price is above ${rupees(advice.break_even_price)}. Check before dispatch.` : ""}${advice.storage_tip ? `\n🌱 ${advice.storage_tip}` : ""}\n🗓 Prices as of ${advice.prices_as_of} · ${advice.confidence} confidence`;
}
export function demoAdvice(request: AdviceRequest): Advice {
  if (!Number.isFinite(request.quantity_qtl) || request.quantity_qtl <= 0)
    throw new Error("Enter a quantity greater than zero.");
  const config = mergeConfig(request.overrides);
  const options = allOptions(request, config).sort(
    (a, b) => b.net_per_qtl - a.net_per_qtl,
  );
  const today = options.filter((o) => o.sell_day === 0);
  if (!today.length)
    throw new Error(
      "No available mandi trades this crop. Make a mandi available to continue.",
    );
  const nearest = [...today].sort((a, b) => a.distance_km - b.distance_km)[0];
  const best = today[0];
  const chosen =
    options.find(
      (o) =>
        o.sell_day > 0 &&
        o.net_per_qtl - best.net_per_qtl >= config.hold_rule.min_gain_per_qtl &&
        best.net_per_qtl - o.net_low <= config.hold_rule.max_downside_per_qtl,
    ) ?? best;
  const sellable =
    (1 - config.spoilage_per_day[request.crop]) ** chosen.sell_day;
  const storage =
    chosen.sell_day * config.storage_cost_per_qtl_per_day[request.crop];
  const confidenceOption = chosen.sell_day
    ? chosen
    : options.find((option) => option.sell_day > 0);
  const advice: Advice = {
    ...(adviceFixture as Advice),
    action: chosen.sell_day ? "hold" : "sell_now",
    days: chosen.sell_day,
    mandi: chosen.mandi,
    net_per_qtl: chosen.net_per_qtl,
    net_low: chosen.net_low,
    net_high: chosen.net_high,
    baseline_today: { mandi: nearest.mandi, net: nearest.net_per_qtl },
    best_today: { mandi: best.mandi, net: best.net_per_qtl },
    gain_vs_baseline: chosen.net_per_qtl - nearest.net_per_qtl,
    gain_from_mandi: best.net_per_qtl - nearest.net_per_qtl,
    gain_from_waiting: chosen.net_per_qtl - best.net_per_qtl,
    confidence:
      !confidenceOption || confidenceOption.flags.includes("stale")
        ? "low"
        : (confidenceOption.price_high - confidenceOption.price_low) /
              confidenceOption.price_mid <=
            config.confidence.narrow_range_pct
          ? "high"
          : "medium",
    break_even_price: chosen.sell_day
      ? Math.ceil(
          (best.net_per_qtl +
            chosen.transport_per_qtl +
            storage +
            config.fees_per_qtl) /
            sellable,
        )
      : null,
    hold_limit_days: holdLimit(request.crop, request.lot_condition, config),
    hold_success_rate: null,
    uses_baseline: false,
    assumptions_default:
      !request.overrides || Object.keys(request.overrides).length === 0,
    why: {
      price: chosen.price_mid,
      spoilage_loss:
        chosen.price_mid -
        chosen.transport_per_qtl -
        storage -
        config.fees_per_qtl -
        chosen.net_per_qtl,
      transport: chosen.transport_per_qtl,
      storage,
      fees: config.fees_per_qtl,
    },
    options,
    notes: [
      "Illustrative demo prices and forecast ranges; not measured model performance.",
    ],
    storage_tip: chosen.sell_day
      ? (request.lang === "mr"
          ? markets.storage_tips_mr
          : request.lang === "hi"
            ? markets.storage_tips_hi
            : markets.storage_tips)[request.crop]
      : null,
  };
  advice.message = message(advice, request.lang, request.crop);
  return advice;
}
export function demoPlan(request: PlanRequest): Plan {
  const config = mergeConfig(request.overrides);
  const centre = request.collection_centre ?? config.fpo.collection_centre;
  if (centre.lat === null || centre.lon === null)
    throw new Error("Set the collection centre coordinates before planning.");
  const cap = request.mandi_cap_qtl_per_day ?? config.fpo.mandi_cap_qtl_per_day;
  const result: Plan = {
    ...(structuredClone(planFixture) as Plan),
    collection_centre: centre.name,
    assumptions_default:
      !request.overrides || !Object.keys(request.overrides).length,
  };
  const groups = new Map<
    string,
    {
      option: MandiOption;
      rows: {
        lot: Lot;
        quantity: number;
        baseline: Advice["baseline_today"];
      }[];
      quantity: number;
    }
  >();
  const lots = [...request.lots].sort(
    (a, b) =>
      (a.cash_needed_in_days ?? Infinity) -
        (b.cash_needed_in_days ?? Infinity) ||
      holdLimit(a.crop, a.lot_condition, config) -
        holdLimit(b.crop, b.lot_condition, config),
  );
  for (const lot of lots) {
    const input: AdviceRequest = {
      ...lot,
      blocked_mandis: request.blocked_mandis,
      overrides: request.overrides,
      lang: "en",
    };
    let advice: Advice;
    try {
      advice = demoAdvice(input);
    } catch (error) {
      result.unplaced.push({
        member: lot.member,
        quantity_qtl: lot.quantity_qtl,
        reason: (error as Error).message,
      });
      continue;
    }
    result.baseline_total += advice.baseline_today.net * lot.quantity_qtl;
    let remaining = lot.quantity_qtl;
    const options = allOptions(input, config, true, {
      lat: centre.lat,
      lon: centre.lon,
    }).sort((a, b) => b.net_per_qtl - a.net_per_qtl);
    const bestToday = options.find((o) => o.sell_day === 0)!;
    const allowed = options.filter(
      (o) =>
        o.sell_day === 0 ||
        (o.net_per_qtl - bestToday.net_per_qtl >=
          config.hold_rule.min_gain_per_qtl &&
          bestToday.net_per_qtl - o.net_low <=
            config.hold_rule.max_downside_per_qtl),
    );
    for (const option of allowed) {
      const key = `${option.mandi}:${option.sell_day}`;
      const group = groups.get(key) ?? { option, rows: [], quantity: 0 };
      const quantity = Math.min(remaining, Math.max(0, cap - group.quantity));
      if (quantity <= 0) continue;
      group.rows.push({ lot, quantity, baseline: advice.baseline_today });
      group.quantity += quantity;
      groups.set(key, group);
      remaining -= quantity;
      if (remaining <= 0) break;
    }
    if (remaining > 0)
      result.unplaced.push({
        member: lot.member,
        quantity_qtl: remaining,
        reason:
          "No mandi with room before this lot's hold limit or cash deadline.",
      });
  }
  for (const group of groups.values()) {
    const { option, quantity } = group;
    const trips = Math.ceil(quantity / config.fpo.truck_capacity_qtl);
    const cost = Math.round(
      trips *
        (config.fpo.truck_fixed_cost +
          option.distance_km * config.fpo.truck_per_km),
    );
    result.trucks.push({
      mandi: option.mandi,
      sell_day: option.sell_day,
      quantity_qtl: quantity,
      trips,
      cost,
    });
    let allocated = 0;
    group.rows.forEach(({ lot, quantity: q, baseline }, index) => {
      const truck_share =
        index === group.rows.length - 1
          ? cost - allocated
          : Math.round((cost * q) / quantity);
      allocated += truck_share;
      const storage =
        config.storage_cost_per_qtl_per_day[lot.crop] * option.sell_day;
      const cropPrice = option.sell_day
        ? demoForecast(lot.crop, option.mandi).forecast.find(
            (f) => f.horizon_days === option.sell_day,
          )!.price_mid
        : (markets[lot.crop] as Record<string, number>)[option.mandi];
      const net_total = Math.round(
        q *
          (cropPrice *
            (1 - config.spoilage_per_day[lot.crop]) ** option.sell_day -
            config.fpo.first_mile_per_qtl -
            storage -
            config.fees_per_qtl) -
          truck_share,
      );
      result.assignments.push({
        member: lot.member,
        crop: lot.crop,
        quantity_qtl: q,
        mandi: option.mandi,
        sell_day: option.sell_day,
        price: cropPrice,
        first_mile: config.fpo.first_mile_per_qtl,
        truck_share,
        storage,
        net_total,
        net_per_qtl: Math.round(net_total / q),
        baseline_today: baseline,
        reason: lot.cash_needed_in_days
          ? `Needs cash in ${lot.cash_needed_in_days} days`
          : holdLimit(lot.crop, lot.lot_condition, config) === 0
            ? "Freshness requires selling today"
            : option.sell_day
              ? "Waiting clears the gain and downside checks"
              : "Best available sell-today option",
        origin: `via ${centre.name}, shared truck`,
      });
      result.total_net += net_total;
    });
  }
  result.baseline_total = Math.round(result.baseline_total);
  result.gain_vs_baseline = result.total_net - result.baseline_total;
  return result;
}
