"use client";

import { useEffect, useState } from "react";
import { getAdvice, getForecast, getMandis } from "@/lib/api";
import { useResource } from "@/lib/useResource";
import { dateLabel, rupees } from "@/lib/format";
import type { ApiResult, Crop } from "@/lib/types";
import { HarvestIntro } from "./HarvestIntro";
import { ErrorState, Loading, SourceNote } from "./ui";

export function InfoTab({
  onStatus,
}: {
  onStatus: (result: ApiResult<unknown>) => void;
}) {
  const [crop, setCrop] = useState<Crop>("onion");
  const resource = useResource(crop, async () => {
    const [advice, markets] = await Promise.all([
      getAdvice({
        crop,
        quantity_qtl: 20,
        village: "Niphad",
        lot_condition: null,
        cash_needed_in_days: null,
        blocked_mandis: [],
        overrides: null,
        lang: "en",
      }),
      getMandis(),
    ]);
    const forecasts = await Promise.all(
      markets.data
        .filter((m) => m.crops.includes(crop))
        .map(async (m) => ({
          mandi: m.mandi,
          result: await getForecast(crop, m.mandi),
        })),
    );
    return {
      data: {
        advice: advice.data,
        forecasts,
        prices_as_of: advice.data.prices_as_of,
      },
      mock: advice.mock || markets.mock || forecasts.some((f) => f.result.mock),
      fallback: advice.fallback,
    };
  });
  useEffect(() => {
    if (resource.result) onStatus(resource.result);
  }, [resource.result, onStatus]);
  if (resource.loading) return <Loading text="Loading market context…" />;
  if (resource.error)
    return <ErrorState error={resource.error} retry={resource.reload} />;
  if (!resource.result) return null;
  const { advice, forecasts } = resource.result.data;
  const asOf = advice.prices_as_of;
  const day = (offset: number) => {
    const date = new Date(asOf + "T12:00:00Z");
    date.setUTCDate(date.getUTCDate() + offset);
    return date.toISOString().slice(0, 10);
  };
  const yesterday = day(-1);
  const previous = forecasts
    .map((f) => ({
      mandi: f.mandi,
      price:
        f.result.data.history.find((h) => h.date === yesterday)?.price ?? null,
    }))
    .sort((a, b) => (b.price ?? -Infinity) - (a.price ?? -Infinity));
  const history =
    forecasts.find((f) => f.mandi === advice.mandi)?.result.data.history ?? [];
  const timeline = Array.from({ length: 7 }, (_, i) => {
    const date = day(i - 7);
    const row = history.find((h) => h.date === date);
    return {
      name: dateLabel(date),
      title: `${dateLabel(date)} · ${advice.mandi}`,
      copy: row
        ? `${rupees(row.price)} per quintal reported for ${crop}. Gross market price; transport, storage and spoilage are not deducted.`
        : "No reported price for this day. No value has been estimated or carried forward.",
    };
  });
  const today = advice.options
    .filter((o) => o.sell_day === 0)
    .sort((a, b) => b.net_per_qtl - a.net_per_qtl);
  return (
    <div className="tab-content">
      <div className="evidence-intro">
        <div>
          <strong>Market context for a 20-quintal lot from Niphad</strong>
          <p>
            Default transport, storage and spoilage assumptions. Net rankings
            change with the lot and origin.
          </p>
        </div>
        <select
          aria-label="Info crop"
          value={crop}
          onChange={(e) => setCrop(e.target.value as Crop)}
        >
          <option value="onion">Onion</option>
          <option value="tomato">Tomato</option>
          <option value="soybean">Soybean</option>
        </select>
      </div>
      <SourceNote result={resource.result} />
      <div className="stat-grid three">
        <div className="stat-card accent">
          <span>Best net mandi today</span>
          <strong>{advice.best_today.mandi}</strong>
          <small>
            {rupees(advice.best_today.net)} / quintal · {dateLabel(asOf)}
          </small>
        </div>
        <div className="stat-card">
          <span>Gain over nearest mandi</span>
          <strong>{rupees(advice.gain_from_mandi)}</strong>
          <small>From mandi choice · estimated per quintal</small>
        </div>
        <div className="stat-card">
          <span>Previous day’s highest reported price</span>
          <strong>
            {previous[0]?.price != null
              ? rupees(previous[0].price)
              : "Not enough data"}
          </strong>
          <small>
            {previous[0]?.price != null
              ? previous[0].mandi
              : "No reported price"}{" "}
            · {dateLabel(yesterday)} · gross / quintal
          </small>
        </div>
      </div>
      <section className="panel">
        <div className="section-heading">
          <div>
            <span className="eyebrow">Market comparison</span>
            <h2>Today’s net options and previous-day prices</h2>
          </div>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Mandi</th>
                <th>Net today / quintal</th>
                <th>Previous day gross / quintal</th>
              </tr>
            </thead>
            <tbody>
              {today.map((o) => (
                <tr key={o.mandi}>
                  <td>{o.mandi}</td>
                  <td>{rupees(o.net_per_qtl)}</td>
                  <td>
                    {rupees(
                      previous.find((p) => p.mandi === o.mandi)?.price ?? null,
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="tiny">
          Prices as of {dateLabel(asOf)}. Previous-day values are reported gross
          prices, not net profit. Collection totals and realised profits are not
          supplied by the API.
        </p>
      </section>
      <HarvestIntro key={crop} timeline={timeline} />
      <section className="panel">
        <div className="section-heading">
          <h2>Seven-day reported price record</h2>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Date and market</th>
                <th>Reported observation</th>
              </tr>
            </thead>
            <tbody>
              {timeline.map((row) => (
                <tr key={row.name}>
                  <td>{row.title}</td>
                  <td>{row.copy}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
