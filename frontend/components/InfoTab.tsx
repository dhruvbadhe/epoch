"use client";

import { useEffect, useState } from "react";
import { getSnapshot, getVillages } from "@/lib/api";
import { useResource } from "@/lib/useResource";
import { NOT_ENOUGH, dateLabel, rupees, signedRupees } from "@/lib/format";
import type { ApiResult, Crop } from "@/lib/types";
import { HarvestIntro } from "./HarvestIntro";
import { ErrorState, Loading, SourceBadge, SourceNote } from "./ui";

export function InfoTab({
  onStatus,
}: {
  onStatus: (result: ApiResult<unknown>) => void;
}) {
  const [crop, setCrop] = useState<Crop>("onion");
  const [VILLAGE, setVillage] = useState("Niphad");
  const villages = useResource("villages", getVillages).result?.data ?? [];
  const resource = useResource(`${crop}:${VILLAGE}`, () =>
    getSnapshot(crop, VILLAGE),
  );
  useEffect(() => {
    if (resource.result) onStatus(resource.result);
  }, [resource.result, onStatus]);
  if (resource.loading) return <Loading text="Loading market context…" />;
  if (resource.error)
    return <ErrorState error={resource.error} retry={resource.reload} />;
  if (!resource.result) return null;
  const s = resource.result.data;
  const day = s.snapshot_date ? dateLabel(s.snapshot_date) : NOT_ENOUGH;
  const net = new Map(
    (s.money_in_hand?.rows ?? []).map((r) => [r.mandi, r] as const),
  );
  const top = s.highest_price?.mandi;
  const topSeries = s.series_7d.find((m) => m.mandi === top)?.points ?? [];
  const timeline = topSeries.map((p) => ({
    name: dateLabel(p.date),
    title: `${dateLabel(p.date)} · ${top}`,
    copy:
      p.modal_price !== null
        ? `${rupees(p.modal_price)} per quintal reported for ${crop}. Gross market price; transport, storage and spoilage are not deducted.`
        : "No reported price for this day. No value has been estimated or carried forward.",
  }));
  return (
    <div className="tab-content">
      <div className="evidence-intro">
        <div>
          <strong>
            Reported mandi prices on {day} (the day before prices as of{" "}
            {dateLabel(s.prices_as_of)})
          </strong>
          <p>
            Reported prices only, no forecasts. Money in hand is for a lot from{" "}
            {VILLAGE}, selling that day, at default transport, storage and
            spoilage assumptions.
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
        <select
          aria-label="Info village"
          value={VILLAGE}
          onChange={(e) => setVillage(e.target.value)}
        >
          {(villages.length ? villages : [{ village: VILLAGE }]).map((v) => (
            <option key={v.village} value={v.village}>
              {v.village}
            </option>
          ))}
        </select>
      </div>
      <SourceNote result={resource.result} />
      <div className="stat-grid three">
        <div className="stat-card accent">
          <span>Highest price</span>
          <strong>
            {s.highest_price ? rupees(s.highest_price.modal_price) : NOT_ENOUGH}
          </strong>
          <small>
            {s.highest_price?.mandi ?? "No reported price"} · {day} · gross /
            quintal
          </small>
        </div>
        <div className="stat-card">
          <span>Lowest price · spread</span>
          <strong>
            {s.lowest_price ? rupees(s.lowest_price.modal_price) : NOT_ENOUGH}
          </strong>
          <small>
            {s.lowest_price?.mandi ?? "No reported price"} · spread{" "}
            {s.spread !== null ? rupees(s.spread) : NOT_ENOUGH}
          </small>
        </div>
        <div className="stat-card">
          <span>Highest money in hand from {VILLAGE}</span>
          <strong>
            {s.money_in_hand
              ? rupees(s.money_in_hand.highest.net_per_qtl)
              : NOT_ENOUGH}
          </strong>
          <small>
            {s.money_in_hand?.highest.mandi ?? "No reported price"} · per
            quintal after transport (assumption)
          </small>
        </div>
      </div>
      <section className="panel">
        <div className="section-heading">
          <div>
            <span className="eyebrow">Market comparison</span>
            <h2>Reported prices on {day}</h2>
          </div>
          <SourceBadge mock={resource.result.mock} />
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Mandi</th>
                <th>District</th>
                <th>Modal / quintal</th>
                <th>Min – max</th>
                <th>Change vs previous report</th>
                <th>Road km from {VILLAGE}</th>
                <th>Money in hand / quintal</th>
              </tr>
            </thead>
            <tbody>
              {s.reporting.map((r) => (
                <tr key={r.mandi}>
                  <td>{r.mandi}</td>
                  <td>{r.district ?? "—"}</td>
                  <td>{rupees(r.modal_price)}</td>
                  <td>
                    {rupees(r.min_price)} – {rupees(r.max_price)}
                  </td>
                  <td>
                    {r.change === null
                      ? NOT_ENOUGH
                      : `${signedRupees(r.change)} (vs ${dateLabel(r.previous_date!)})`}
                  </td>
                  <td>{net.get(r.mandi)?.road_km ?? "—"}</td>
                  <td>
                    {net.has(r.mandi)
                      ? rupees(net.get(r.mandi)!.net_per_qtl)
                      : NOT_ENOUGH}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {s.not_reporting.length > 0 && (
          <p className="tiny">
            Did not report on {day}:{" "}
            {s.not_reporting
              .map(
                (m) =>
                  `${m.mandi} (last report ${m.last_reported_date ? dateLabel(m.last_reported_date) : "none"})`,
              )
              .join(", ")}
            .
          </p>
        )}
        <p className="tiny">
          {s.basis} Money in hand uses the engine’s own distance and cost
          functions; transport, storage and spoilage are assumptions.
        </p>
      </section>
      <HarvestIntro key={crop} timeline={timeline} />
      <section className="panel">
        <div className="section-heading">
          <h2>Seven-day reported modal prices</h2>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Mandi</th>
                {s.series_dates.map((d) => (
                  <th key={d}>{dateLabel(d)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {s.series_7d.map((m) => (
                <tr key={m.mandi}>
                  <td>{m.mandi}</td>
                  {m.points.map((p) => (
                    <td key={p.date}>
                      {p.modal_price !== null ? rupees(p.modal_price) : "—"}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="tiny">
          “—” means no price was reported that day; nothing is estimated or
          carried forward.
        </p>
      </section>
    </div>
  );
}
