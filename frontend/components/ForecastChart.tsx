"use client";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getForecast } from "@/lib/api";
import { useResource } from "@/lib/useResource";
import { dateLabel, rupees } from "@/lib/format";
import type { Crop, Forecast } from "@/lib/types";
import { Empty, ErrorState, Loading, SourceBadge, SourceNote } from "./ui";
export function ForecastChart({ crop, mandi }: { crop: Crop; mandi: string }) {
  const { result, loading, error, reload } = useResource(
    `${crop}:${mandi}`,
    () => getForecast(crop, mandi),
  );
  return (
    <section className="panel forecast-panel">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Price forecast</span>
          <h2>
            A range, not a promise{" "}
            <span className="heading-detail">/ {mandi}</span>
          </h2>
        </div>
        {result && <SourceBadge mock={result.mock} />}
      </div>
      {loading ? (
        <Loading text="Loading the price outlook…" />
      ) : error ? (
        <ErrorState error={error} retry={reload} />
      ) : (
        result && (
          <>
            <SourceNote result={result} />
            <Chart data={result.data} />
            <p className="tiny">
              Prices as of {dateLabel(result.data.prices_as_of)} · ₹ per quintal
              · Dashed forecast segments use the baseline.
            </p>
          </>
        )
      )}
    </section>
  );
}
function Chart({ data }: { data: Forecast }) {
  if (!data.history.length && !data.forecast.length)
    return (
      <Empty
        title="No price history yet"
        text="Reported prices will appear here when the forecast data is ready."
      />
    );
  const last = data.history.at(-1);
  const rows = [
    ...data.history.map((row) => ({
      date: row.date,
      reported: row.price,
      mid: row.date === data.prices_as_of ? row.price : undefined,
      band: undefined as [number, number] | undefined,
      forecastValue: undefined as number | undefined,
      baselineValue: undefined as number | undefined,
    })),
    ...data.forecast.map((row, i, all) => ({
      date: row.date,
      reported: undefined,
      mid: row.price_mid,
      band: [row.price_low, row.price_high] as [number, number],
      forecastValue:
        !row.uses_baseline || !all[i + 1]?.uses_baseline
          ? row.price_mid
          : undefined,
      baselineValue:
        row.uses_baseline || (i > 0 && all[i - 1].uses_baseline)
          ? row.price_mid
          : undefined,
    })),
  ];
  if (last) {
    const match = rows.find((row) => row.date === last.date);
    if (match) {
      match.forecastValue = data.forecast[0]?.uses_baseline
        ? undefined
        : last.price;
      match.baselineValue = data.forecast[0]?.uses_baseline
        ? last.price
        : undefined;
    }
  }
  return (
    <>
      <div className="chart-legend">
        <span>
          <i className="legend-line reported" />
          Reported price
        </span>
        <span>
          <i className="legend-line" />
          Forecast
        </span>
        <span>
          <i className="legend-band" />
          Low–high range
        </span>
      </div>
      <div
        className="chart-container"
        role="img"
        aria-label={`Reported and forecast prices for ${data.crop} at ${data.mandi}. The shaded band shows the forecast range.`}
      >
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            data={rows}
            margin={{ top: 12, right: 12, bottom: 2, left: 0 }}
          >
            <defs>
              <linearGradient id="rangeFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#77b18e" stopOpacity={0.27} />
                <stop offset="100%" stopColor="#77b18e" stopOpacity={0.06} />
              </linearGradient>
            </defs>
            <CartesianGrid
              stroke="#e9ece6"
              strokeDasharray="3 5"
              vertical={false}
            />
            <XAxis
              dataKey="date"
              tickFormatter={(v) =>
                new Date(v + "T12:00:00").toLocaleDateString("en-IN", {
                  day: "numeric",
                  month: "short",
                })
              }
              minTickGap={36}
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 11, fill: "#889084" }}
              dy={10}
            />
            <YAxis
              domain={["auto", "auto"]}
              tickFormatter={(v) => rupees(v)}
              width={60}
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 11, fill: "#889084" }}
            />
            <Tooltip
              labelFormatter={(v) => dateLabel(String(v))}
              formatter={(v, name) => [
                Array.isArray(v)
                  ? `${rupees(Number(v[0]))} – ${rupees(Number(v[1]))}`
                  : rupees(Number(v)),
                name,
              ]}
              contentStyle={{
                borderRadius: 10,
                border: "1px solid #e1e7dc",
                fontSize: 12,
              }}
            />
            <Area
              type="linear"
              dataKey="band"
              name="Forecast range"
              stroke="none"
              fill="url(#rangeFill)"
              isAnimationActive={false}
            />
            <Line
              type="linear"
              dataKey="reported"
              name="Reported price"
              stroke="#8d9b8b"
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
            <Line
              type="linear"
              dataKey="forecastValue"
              name="Forecast"
              stroke="#23714f"
              strokeWidth={2.5}
              dot={false}
              isAnimationActive={false}
            />
            <Line
              type="linear"
              dataKey="baselineValue"
              name="Baseline forecast"
              stroke="#23714f"
              strokeDasharray="4 4"
              strokeWidth={2.5}
              dot={false}
              isAnimationActive={false}
            />
            <ReferenceLine
              x={data.prices_as_of}
              stroke="#acb6a6"
              strokeDasharray="4 4"
              label={{
                value: "AS OF",
                position: "insideTopLeft",
                fill: "#8b9484",
                fontSize: 9,
              }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </>
  );
}
