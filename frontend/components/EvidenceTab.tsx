"use client";
import { useEffect, useState } from "react";
import { BarChart3, FlaskConical, Info, ShieldCheck } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getBacktest } from "@/lib/api";
import { useResource } from "@/lib/useResource";
import {
  NOT_ENOUGH,
  dateLabel,
  metric,
  percentage,
  rupees,
} from "@/lib/format";
import type { ApiResult, Config, Crop, Overrides } from "@/lib/types";
import { Empty, ErrorState, Loading, SourceBadge, SourceNote } from "./ui";
const policies: Record<string, string> = {
  nearest_today: "Nearest today",
  highest_price_today: "Highest price today",
  best_net_today: "Best net today",
  full_advice: "With hold rule (before the gate)",
};
export function EvidenceTab({
  overrides,
  config,
  onStatus,
}: {
  overrides: Overrides;
  config: Config;
  onStatus: (result: ApiResult<unknown>) => void;
}) {
  const [crop, setCrop] = useState<Crop>("onion");
  const { result, loading, error, reload } = useResource(crop, () =>
    getBacktest(crop),
  );
  useEffect(() => {
    if (result) onStatus(result);
  }, [result, onStatus]);
  const data = result?.data;
  return (
    <div className="tab-content">
      <div className="evidence-intro">
        <FlaskConical size={23} />
        <div>
          <strong>
            Simulated on last season’s reported prices, at default assumptions.
          </strong>
          <p>
            See the gains, the losses, and where the forecast earns our trust.
          </p>
        </div>
        <select
          aria-label="Evidence crop"
          value={crop}
          onChange={(e) => setCrop(e.target.value as Crop)}
        >
          <option value="onion">🧅 Onion</option>
          <option value="tomato">🍅 Tomato</option>
          <option value="soybean">🌱 Soybean</option>
        </select>
      </div>
      {overrides && (
        <div className="notice warning">
          <Info size={17} />
          You’ve changed assumptions. Advice and FPO Plan use your values; these
          numbers use the defaults.
        </div>
      )}
      {loading ? (
        <Loading text="Loading the backtest results…" />
      ) : error ? (
        <ErrorState error={error} retry={reload} />
      ) : (
        data && (
          <>
            <SourceNote result={result} />
            {result?.mock && (
              <div className="notice">
                <Info size={17} />
                The backtest hasn’t been measured in this demo. Metrics remain
                “Not enough data” until the backend provides results.
              </div>
            )}
            <div className="stat-grid">
              <div className="stat-card accent">
                <span>Average gain / quintal</span>
                <strong
                  className={
                    data.avg_gain_per_qtl === null ? "not-evaluated" : ""
                  }
                >
                  {metric(data.avg_gain_per_qtl)}
                </strong>
                <small>Against nearest-today baseline</small>
              </div>
              <div className="stat-card">
                <span>Median gain / quintal</span>
                <strong
                  className={
                    data.median_gain_per_qtl === null ? "not-evaluated" : ""
                  }
                >
                  {metric(data.median_gain_per_qtl)}
                </strong>
                <small>The middle simulated outcome</small>
              </div>
              <div className="stat-card">
                <span>Advice that lost money</span>
                <strong
                  className={data.loss_share === null ? "not-evaluated" : ""}
                >
                  {percentage(data.loss_share)}
                </strong>
                <small>Share that did worse than nearest today</small>
              </div>
              <div className="stat-card">
                <span>Worst loss / quintal</span>
                <strong
                  className={
                    data.worst_loss_per_qtl === null ? "not-evaluated" : ""
                  }
                >
                  {metric(data.worst_loss_per_qtl)}
                </strong>
                <small>The downside deserves to be visible</small>
              </div>
            </div>
            <div className="evidence-grid">
              <section className="panel ladder-panel">
                <div className="section-heading">
                  <div>
                    <span className="eyebrow">WHAT ADDS VALUE?</span>
                    <h2>The strategy ladder</h2>
                  </div>
                  <BarChart3 size={20} />
                </div>
                <p className="muted">
                  Average money in hand per harvested quintal.
                </p>
                {data.ladder.some((l) => l.avg_net !== null) ? (
                  <div className="chart-container">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={data.ladder
                          .filter((l) => l.avg_net !== null)
                          .map((l) => ({
                            ...l,
                            label: policies[l.policy] ?? l.policy,
                          }))}
                        margin={{ left: 0, right: 8, top: 16, bottom: 0 }}
                      >
                        <CartesianGrid vertical={false} stroke="#e8ece5" />
                        <XAxis
                          dataKey="label"
                          tick={{ fontSize: 11 }}
                          axisLine={false}
                          tickLine={false}
                        />
                        <YAxis
                          tickFormatter={(v) => rupees(v)}
                          width={65}
                          tick={{ fontSize: 11 }}
                          axisLine={false}
                          tickLine={false}
                        />
                        <Tooltip
                          formatter={(v) => [rupees(Number(v)), "Average net"]}
                        />
                        <Bar
                          dataKey="avg_net"
                          fill="#24734f"
                          radius={[5, 5, 0, 0]}
                          isAnimationActive={false}
                        >
                          <LabelList
                            dataKey="avg_net"
                            position="top"
                            formatter={(v) => rupees(Number(v))}
                            style={{ fontSize: 11 }}
                          />
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <div className="ladder-empty">
                    {data.ladder.map((l, i) => (
                      <div key={l.policy}>
                        <span className="step-number">0{i + 1}</span>
                        <strong>{policies[l.policy] ?? l.policy}</strong>
                        <span className="ladder-placeholder" />
                        <span className="tiny">Not enough data</span>
                      </div>
                    ))}
                  </div>
                )}
                <p className="tiny">
                  Nearest mandi → price comparison → transport accounted for →
                  holding considered.
                </p>
              </section>
              <section className="panel validation-panel">
                <span className="eyebrow">THE TEST SET</span>
                <h2>How much evidence?</h2>
                <div className="validation-row">
                  <span>Simulated cases tested</span>
                  <strong>{data.cases_tested.toLocaleString("en-IN")}</strong>
                </div>
                <div className="validation-row">
                  <span>Cases excluded</span>
                  <strong>
                    {Object.values(data.cases_excluded_by_reason)
                      .reduce((s, n) => s + n, 0)
                      .toLocaleString("en-IN")}
                  </strong>
                </div>
                {Object.entries(data.cases_excluded_by_reason).map(
                  ([reason, count]) => (
                    <div className="tiny exclusion" key={reason}>
                      {reason}: {count}
                    </div>
                  ),
                )}
                <div className="validation-row">
                  <span>Hold cases</span>
                  <strong>{data.hold_cases}</strong>
                </div>
                <div className="validation-row">
                  <span>Hold success rate</span>
                  <strong className="small-metric">
                    {percentage(data.hold_success_rate)}
                  </strong>
                </div>
                <div className="validation-row">
                  <span>Holds won / lost / unscored</span>
                  <strong>
                    {data.hold_record
                      ? `${data.hold_record.won} / ${data.hold_record.lost} / ${data.hold_record.unscored}`
                      : NOT_ENOUGH}
                  </strong>
                </div>
                <div className="validation-row">
                  <span>Gain from mandi choice</span>
                  <strong>{metric(data.gain_split?.from_mandi_choice)}</strong>
                </div>
                <div className="validation-row">
                  <span>Gain from holding</span>
                  <strong>{metric(data.gain_split?.from_holding)}</strong>
                </div>
                <p className="tiny">
                  Hold success compares against the best sell-today option,
                  including transport. Losses count the same as wins.
                </p>
                <div className="test-period">
                  <span>Test period</span>
                  <strong>
                    {dateLabel(data.test_period.start)} –{" "}
                    {dateLabel(data.test_period.end)}
                  </strong>
                </div>
                <p className="tiny">
                  Cases overlap and are not independent. No significance claims.
                </p>
              </section>
            </div>
            <div className="evidence-grid">
              <section className="panel">
                <div className="section-heading">
                  <div>
                    <span className="eyebrow">CHECK THE RANGE</span>
                    <h2>Forecast coverage</h2>
                  </div>
                </div>
                {data.coverage.length ? (
                  <div className="table-scroll">
                    <table>
                      <thead>
                        <tr>
                          <th>Horizon</th>
                          <th>Actual price inside range</th>
                          <th className="numeric">Test rows</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.coverage.map((c) => (
                          <tr key={c.horizon_days}>
                            <td>Day {c.horizon_days}</td>
                            <td>{percentage(c.coverage)}</td>
                            <td className="numeric">{c.n}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <Empty
                    title="Coverage not available"
                    text="The backend has not supplied forecast coverage yet."
                  />
                )}
              </section>
              <section className="panel confidence-panel">
                <div className="section-heading">
                  <div>
                    <span className="eyebrow">NO HIDDEN SCORE</span>
                    <h2>
                      <ShieldCheck size={20} />
                      The confidence rule
                    </h2>
                  </div>
                </div>
                <div className="confidence-rule">
                  <span className="badge green">High</span>
                  <p>
                    Self-check passed, last report ≤{" "}
                    {config.confidence.stale_days} days old, range width ÷ mid ≤{" "}
                    {Math.round(config.confidence.narrow_range_pct * 100)}%.
                  </p>
                </div>
                <div className="confidence-rule">
                  <span className="badge amber">Medium</span>
                  <p>
                    Self-check passed and prices are recent, but the range is
                    wider.
                  </p>
                </div>
                <div className="confidence-rule">
                  <span className="badge red">Low</span>
                  <p>
                    Self-check failed, or the last report is more than{" "}
                    {config.confidence.stale_days} days old.
                  </p>
                </div>
                <div className="notice compact">
                  A failed horizon uses the baseline range and gives no hold
                  advice.
                </div>
              </section>
            </div>
            <section className="panel">
              <div className="section-heading">
                <div>
                  <span className="eyebrow">
                    MODEL VS. “PRICE STAYS THE SAME”
                  </span>
                  <h2>A self-check at every horizon</h2>
                </div>
                <SourceBadge mock={result!.mock} />
              </div>
              <p className="muted">
                Ratio below {config.forecast.selfcheck_ratio_max} means the
                model beat “price stays the same”; at least{" "}
                {config.forecast.selfcheck_min_rows} validation rows are also
                required.
              </p>
              {data.selfcheck.length ? (
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Mandi</th>
                        <th>Horizon</th>
                        <th>MAE ratio</th>
                        <th>Validation rows</th>
                        <th className="numeric">Result</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.selfcheck.map((s) => (
                        <tr key={`${s.mandi}:${s.horizon_days}`}>
                          <td>
                            <strong>{s.mandi}</strong>
                          </td>
                          <td>Day {s.horizon_days}</td>
                          <td>
                            {s.ratio === null
                              ? "Not enough data"
                              : s.ratio.toFixed(3)}
                          </td>
                          <td>{s.rows}</td>
                          <td className="numeric">
                            <span
                              className={`badge ${s.ratio === null ? "" : s.passed ? "green" : "red"}`}
                            >
                              {s.ratio === null
                                ? "Not enough data"
                                : s.passed
                                  ? "Passed"
                                  : "Failed"}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <Empty
                  title="Self-check results not available"
                  text="Each crop, mandi, and horizon will be evaluated separately."
                />
              )}
              <div className="table-footer">
                <span>Default assumptions · {data.assumptions}</span>
                <span>
                  Prices as of{" "}
                  {data.prices_as_of
                    ? dateLabel(data.prices_as_of)
                    : NOT_ENOUGH}
                </span>
              </div>
            </section>
          </>
        )
      )}
    </div>
  );
}
