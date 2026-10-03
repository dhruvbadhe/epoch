"use client";
import { useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  CheckCircle2,
  Download,
  MapPin,
  Plus,
  Route,
  Trash2,
  Truck,
  UsersRound,
} from "lucide-react";
import { getPlan } from "@/lib/api";
import { NOT_ENOUGH } from "@/lib/format";
import { engineDemoLots, sampleCentre } from "@/lib/demo";
import { useResource } from "@/lib/useResource";
import { cropLabel, rupees, sellDay, signedRupees } from "@/lib/format";
import type {
  ApiResult,
  Config,
  Crop,
  Lot,
  Mandi,
  Overrides,
  Plan,
  PlanRequest,
  Village,
} from "@/lib/types";
import {
  downloadCsv,
  Empty,
  ErrorState,
  FreshnessSelect,
  Loading,
  SourceBadge,
  SourceNote,
} from "./ui";
export function FpoPlanTab({
  mandis,
  villages,
  config,
  overrides,
  onStatus,
}: {
  mandis: Mandi[];
  villages: Village[];
  config: Config;
  overrides: Overrides;
  onStatus: (result: ApiResult<unknown>) => void;
}) {
  const [lots, setLots] = useState<Lot[]>(structuredClone(engineDemoLots));
  const [blocked, setBlocked] = useState<string[]>([]);
  const [planned, setPlanned] = useState<PlanRequest | null>(null);
  const [dirty, setDirty] = useState(true);
  const [moved, setMoved] = useState<string[]>([]);
  const previous = useRef<Plan | null>(null);
  const { result, loading, error, reload } = useResource(
    JSON.stringify(planned),
    () => getPlan(planned!),
    planned !== null,
  );
  useEffect(() => {
    if (result) {
      onStatus(result);
      const before = previous.current;
      setMoved(
        before
          ? result.data.assignments
              .filter(
                (a) =>
                  !before.assignments.some(
                    (b) =>
                      b.member === a.member &&
                      b.mandi === a.mandi &&
                      b.sell_day === a.sell_day &&
                      b.quantity_qtl === a.quantity_qtl,
                  ),
              )
              .map((a) => a.member)
          : [],
      );
      previous.current = result.data;
    }
  }, [result, onStatus]);
  useEffect(() => {
    if (planned) {
      setPlanned((v) => (v ? { ...v, overrides } : v));
    }
  }, [overrides]); // Recalculate an existing plan after applying assumptions.
  const patchLot = (index: number, patch: Partial<Lot>) => {
    setLots((items) =>
      items.map((lot, i) => (i === index ? { ...lot, ...patch } : lot)),
    );
    setDirty(true);
  };
  const valid =
    lots.length > 0 &&
    lots.every(
      (l) =>
        l.member.trim() &&
        Number.isFinite(l.quantity_qtl) &&
        l.quantity_qtl > 0 &&
        villages.some((v) => v.village === l.village),
    ) &&
    new Set(lots.map((l) => l.member.trim())).size === lots.length;
  const plan = (newBlocked = blocked) => {
    setPlanned({
      lots: structuredClone(lots),
      blocked_mandis: newBlocked,
      mandi_cap_qtl_per_day: null,
      collection_centre: config.fpo.collection_centre.name || sampleCentre,
      overrides,
    });
    setDirty(false);
  };
  // The same lots with nothing blocked, to headline what a closure costs.
  const openRequest =
    planned && planned.blocked_mandis.length
      ? { ...planned, blocked_mandis: [] }
      : null;
  const openResource = useResource(
    JSON.stringify(openRequest),
    () => getPlan(openRequest!),
    openRequest !== null,
  );
  const openTotal = openResource.result?.data.total_net;
  const centre = config.fpo.collection_centre.name || sampleCentre;
  const data = result?.data;
  return (
    <div className="tab-content">
      <div className="plan-intro">
        <div>
          <span className="icon-tile">
            <UsersRound size={23} />
          </span>
          <div>
            <strong>Better together.</strong>
            <p>
              Plan the group’s harvest, with shared transport and individual
              constraints.
            </p>
          </div>
        </div>
        <span className="centre-pill">
          <MapPin size={15} />
          Collection centre <b>{data?.collection_centre ?? centre}</b>
        </span>
      </div>
      <section className="panel">
        <div className="section-heading">
          <div>
            <span className="eyebrow">THE GROUP’S HARVEST</span>
            <h2>
              Member lots <span className="count-badge">{lots.length}</span>
            </h2>
          </div>
          <button
            className="button secondary"
            onClick={() => {
              setLots(
                structuredClone(engineDemoLots).map((l) => ({
                  ...l,
                  village: villages.some((v) => v.village === l.village)
                    ? l.village
                    : (villages[0]?.village ?? l.village),
                })),
              );
              setDirty(true);
            }}
          >
            Load sample lots
          </button>
        </div>
        <div className="table-scroll editable-lots">
          <table>
            <thead>
              <tr>
                <th>Member</th>
                <th>Crop</th>
                <th>Quantity · qtl</th>
                <th>Village</th>
                <th>Lot condition</th>
                <th>Cash needed</th>
                <th>
                  <span className="sr-only">Remove</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {lots.map((lot, i) => (
                <tr key={i}>
                  <td>
                    <input
                      aria-label={`Member ${i + 1} name`}
                      value={lot.member}
                      onChange={(e) => patchLot(i, { member: e.target.value })}
                    />
                  </td>
                  <td>
                    <select
                      aria-label={`Member ${i + 1} crop`}
                      value={lot.crop}
                      onChange={(e) =>
                        patchLot(i, {
                          crop: e.target.value as Crop,
                          lot_condition: null,
                        })
                      }
                    >
                      <option value="onion">Onion</option>
                      <option value="tomato">Tomato</option>
                      <option value="soybean">Soybean</option>
                    </select>
                  </td>
                  <td>
                    <input
                      aria-label={`Member ${i + 1} quantity`}
                      type="number"
                      min="0"
                      step="any"
                      value={lot.quantity_qtl || ""}
                      onChange={(e) =>
                        patchLot(i, { quantity_qtl: Number(e.target.value) })
                      }
                    />
                  </td>
                  <td>
                    <select
                      aria-label={`Member ${i + 1} village`}
                      value={lot.village}
                      onChange={(e) => patchLot(i, { village: e.target.value })}
                    >
                      {villages.map((v) => (
                        <option key={v.village}>{v.village}</option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <FreshnessSelect
                      id={`lot-condition-${i}`}
                      crop={lot.crop}
                      value={lot.lot_condition}
                      onChange={(v) => patchLot(i, { lot_condition: v })}
                    />
                  </td>
                  <td>
                    <select
                      aria-label={`Member ${i + 1} cash deadline`}
                      value={lot.cash_needed_in_days ?? ""}
                      onChange={(e) =>
                        patchLot(i, {
                          cash_needed_in_days: e.target.value
                            ? (Number(e.target.value) as 3 | 7)
                            : null,
                        })
                      }
                    >
                      <option value="">No hurry</option>
                      <option value="7">This week</option>
                      <option value="3">In 2–3 days</option>
                    </select>
                  </td>
                  <td>
                    <button
                      className="icon-button danger"
                      aria-label={`Remove member ${i + 1}`}
                      onClick={() => {
                        setLots((items) => items.filter((_, j) => i !== j));
                        setDirty(true);
                      }}
                    >
                      <Trash2 size={15} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="lots-footer">
          <button
            className="button subtle"
            onClick={() => {
              setLots((v) => [
                ...v,
                {
                  member: `Member ${v.length + 1}`,
                  crop: "onion",
                  quantity_qtl: 10,
                  village: villages[0]?.village ?? "Niphad",
                  lot_condition: null,
                  cash_needed_in_days: null,
                },
              ]);
              setDirty(true);
            }}
          >
            <Plus size={15} />
            Add member
          </button>
          <span className="tiny">
            {lots
              .reduce((s, l) => s + (l.quantity_qtl || 0), 0)
              .toLocaleString("en-IN")}{" "}
            quintals across {lots.length} members
          </span>
        </div>
      </section>
      <section className="panel disruptions">
        <div className="section-heading">
          <div>
            <span className="eyebrow">ADAPT TO THE DAY</span>
            <h2>Mark a mandi unavailable</h2>
          </div>
          <span className="tiny">
            Flood, strike, or closure · operator reported
          </span>
        </div>
        <div className="mandi-checkboxes">
          {mandis.map((m) => (
            <label
              className={blocked.includes(m.mandi) ? "blocked" : ""}
              key={m.mandi}
            >
              <input
                type="checkbox"
                checked={blocked.includes(m.mandi)}
                onChange={(e) => {
                  const next = e.target.checked
                    ? [...blocked, m.mandi]
                    : blocked.filter((v) => v !== m.mandi);
                  setBlocked(next);
                  if (planned && valid) plan(next);
                }}
              />
              {m.mandi}
            </label>
          ))}
        </div>
        <div className="plan-actions">
          <span className="tiny">
            {!valid
              ? "Use unique member names, valid villages, and positive quantities."
              : dirty
                ? "Ready to compare routes and shared truck costs."
                : "Change a closure to automatically re-plan."}
          </span>
          <button
            className="button primary"
            disabled={!valid || loading}
            onClick={() => plan()}
          >
            <Route size={16} />
            {loading ? "Planning…" : "Build the plan"}
            <ArrowRight size={16} />
          </button>
        </div>
      </section>
      {dirty && data && (
        <div className="notice warning">
          Member lots have changed. Build the plan again to update these
          results.
        </div>
      )}
      {loading && <Loading text="Planning the group’s harvest…" />}
      {error && <ErrorState error={error} retry={reload} />}
      {!planned && (
        <div className="plan-placeholder">
          <Route size={28} />
          <h3>A route for every member.</h3>
          <p>Add your lots, mark any closures, and build a collective plan.</p>
        </div>
      )}
      {data && !loading && (
        <>
          <SourceNote result={result} />
          {planned?.blocked_mandis.length && openTotal !== undefined ? (
            <div className="notice warning" role="status">
              <strong>
                Blocking {planned.blocked_mandis.join(", ")} changes FPO money
                in hand by {signedRupees(data.total_net - openTotal)} against
                the open plan ({rupees(openTotal)} → {rupees(data.total_net)}).
              </strong>
            </div>
          ) : null}
          <p className="tiny">
            Placed {data.placed_qtl ?? NOT_ENOUGH} qtl · Unplaced{" "}
            {data.unplaced_qtl ?? NOT_ENOUGH} qtl · Moved lots show their reason
            in the table below.
          </p>
          <div className="stat-grid three">
            <div className="stat-card">
              <span>FPO money in hand</span>
              <strong>{rupees(data.total_net)}</strong>
              <small>via {data.collection_centre}, shared truck</small>
            </div>
            <div className="stat-card">
              <span>Nearest-today baseline</span>
              <strong>{rupees(data.baseline_total)}</strong>
              <small>Everyone sells at their nearest mandi today</small>
            </div>
            <div className="stat-card accent">
              <span>Difference against baseline</span>
              <strong>{signedRupees(data.gain_vs_baseline)}</strong>
              <small>
                {data.unplaced.length
                  ? "Includes unplaced lots with zero sale proceeds"
                  : "After transport, spoilage, storage, and fees"}
              </small>
            </div>
          </div>
          {data.unplaced.length > 0 && (
            <div className="notice warning unplaced">
              <strong>
                {data.unplaced.length} unplaced{" "}
                {data.unplaced.length === 1 ? "lot" : "lots"}
              </strong>
              {data.unplaced.map((lot, i) => (
                <p key={i}>
                  {lot.member} · {lot.quantity_qtl} quintals — {lot.reason}
                </p>
              ))}
            </div>
          )}
          <section className="panel">
            <div className="section-heading">
              <div>
                <span className="eyebrow">THE COLLECTIVE PLAN</span>
                <h2>Where each lot goes</h2>
              </div>
              <button
                className="button subtle"
                onClick={() =>
                  downloadCsv(
                    "sellsmart-fpo-plan.csv",
                    [
                      "Member",
                      "Crop",
                      "Quantity qtl",
                      "Mandi",
                      "Sell day",
                      "Reason",
                      "Truck share INR",
                      "Net total INR",
                      "Net INR/qtl",
                      "Baseline INR/qtl",
                      "Origin",
                      "Prices as of",
                    ],
                    data.assignments.map((a) => [
                      a.member,
                      a.crop,
                      a.quantity_qtl,
                      a.mandi,
                      a.sell_day,
                      a.reason,
                      a.truck_share,
                      a.net_total,
                      a.net_per_qtl,
                      a.baseline_today.net,
                      a.origin,
                      data.prices_as_of,
                    ]),
                  )
                }
              >
                <Download size={15} />
                Export plan
              </button>
            </div>
            {moved.length > 0 && (
              <p className="reroute-note">
                <CheckCircle2 size={15} />
                {new Set(moved).size} member routes changed. Updated rows are
                highlighted.
              </p>
            )}
            {data.assignments.length ? (
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Member / crop</th>
                      <th>Quantity</th>
                      <th>Destination / day</th>
                      <th>Reason</th>
                      <th>Truck share</th>
                      <th>Nearest today</th>
                      <th className="numeric">Money in hand</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.assignments.map((a, i) => (
                      <tr
                        className={moved.includes(a.member) ? "moved-row" : ""}
                        key={`${a.member}-${a.mandi}-${a.sell_day}-${i}`}
                      >
                        <td>
                          <strong>{a.member}</strong>
                          <small>{cropLabel(a.crop)}</small>
                        </td>
                        <td>{a.quantity_qtl} qtl</td>
                        <td>
                          <strong>{a.mandi}</strong>
                          <small>{sellDay(a.sell_day)}</small>
                        </td>
                        <td className="reason-cell">{a.reason}</td>
                        <td>{rupees(a.truck_share)}</td>
                        <td>
                          {rupees(a.baseline_today.net)}/qtl
                          <small>{a.baseline_today.mandi}</small>
                        </td>
                        <td className="numeric">
                          <strong>{rupees(a.net_total)}</strong>
                          <small>
                            {rupees(a.net_per_qtl)}/qtl · {a.origin}
                          </small>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <Empty
                title="No lots could be placed"
                text="Review the unplaced reasons above, or make another mandi available."
              />
            )}
          </section>
          <section className="panel">
            <div className="section-heading">
              <div>
                <span className="eyebrow">SHARE THE JOURNEY</span>
                <h2>
                  <Truck size={20} />
                  Truck schedule
                </h2>
              </div>
              <SourceBadge mock={result!.mock} />
            </div>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Destination</th>
                    <th>Departure</th>
                    <th>Load</th>
                    <th>Trips</th>
                    <th className="numeric">Shared cost</th>
                  </tr>
                </thead>
                <tbody>
                  {data.trucks.map((t) => (
                    <tr key={`${t.mandi}:${t.sell_day}`}>
                      <td>
                        <strong>{t.mandi}</strong>
                      </td>
                      <td>{sellDay(t.sell_day)}</td>
                      <td>{t.quantity_qtl} quintals</td>
                      <td>{t.trips}</td>
                      <td className="numeric">{rupees(t.cost)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="table-footer">
              <span>
                Rule-based allocation · cash deadlines and freshness first
              </span>
              <span>Prices as of {data.prices_as_of}</span>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
