"use client";
import { useEffect, useMemo, useState } from "react";
import {
  ArrowDownUp,
  ArrowUpRight,
  Check,
  ChevronLeft,
  ChevronRight,
  Download,
  Search,
} from "lucide-react";
import type { Advice } from "@/lib/types";
import { rupees, sellDay } from "@/lib/format";
import { downloadCsv, Empty } from "./ui";
export function MandiTable({ advice }: { advice: Advice }) {
  const [search, setSearch] = useState("");
  const [todayOnly, setTodayOnly] = useState(false);
  const [descending, setDescending] = useState(true);
  const [page, setPage] = useState(0);
  const options = useMemo(
    () =>
      advice.options
        .filter(
          (o) =>
            o.mandi.toLowerCase().includes(search.toLowerCase()) &&
            (!todayOnly || o.sell_day === 0),
        )
        .sort((a, b) =>
          descending
            ? b.net_per_qtl - a.net_per_qtl
            : a.net_per_qtl - b.net_per_qtl,
        ),
    [advice.options, search, todayOnly, descending],
  );
  useEffect(() => {
    setPage(0);
  }, [advice.options, search, todayOnly, descending]);
  const pageSize = 8;
  const pageOptions = options.slice(page * pageSize, (page + 1) * pageSize);
  return (
    <section className="panel mandi-panel">
      <div className="section-heading">
        <div>
          <span className="eyebrow">SEE THE ALTERNATIVES</span>
          <h2>A better market, with the costs included.</h2>
        </div>
        <button
          className="button subtle"
          onClick={() =>
            downloadCsv(
              "sellsmart-mandi-options.csv",
              [
                "Mandi",
                "Distance km",
                "Sell day",
                "Price low INR/qtl",
                "Price mid INR/qtl",
                "Price high INR/qtl",
                "Transport INR/qtl",
                "Net INR/harvested qtl",
                "Prices as of",
              ],
              options.map((o) => [
                o.mandi,
                o.distance_km,
                o.sell_day,
                o.price_low,
                o.price_mid,
                o.price_high,
                o.transport_per_qtl,
                o.net_per_qtl,
                advice.prices_as_of,
              ]),
            )
          }
        >
          <Download size={15} />
          Export CSV
        </button>
      </div>
      <div className="table-controls">
        <div className="search-input">
          <Search size={15} />
          <input
            aria-label="Search mandis"
            placeholder="Search a mandi…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={todayOnly}
            onChange={(e) => setTodayOnly(e.target.checked)}
          />
          Selling today only
        </label>
        <span className="tiny">{options.length} options</span>
      </div>
      {options.length ? (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Mandi</th>
                <th>Distance</th>
                <th>Sell on</th>
                <th>
                  {todayOnly ? "Reported price" : "Reported / forecast price"}
                </th>
                <th>Transport (assumption)</th>
                <th className="numeric">
                  <button
                    className="table-sort"
                    onClick={() => setDescending((v) => !v)}
                  >
                    Money in hand <ArrowDownUp size={13} />
                  </button>
                </th>
              </tr>
            </thead>
            <tbody>
              {pageOptions.map((o) => {
                const chosen =
                  o.mandi === advice.mandi && o.sell_day === advice.days;
                return (
                  <tr
                    className={chosen ? "chosen-row" : ""}
                    key={`${o.mandi}-${o.sell_day}`}
                  >
                    <td>
                      <div className="mandi-name">
                        {chosen && (
                          <span className="chosen-check">
                            <Check size={12} />
                          </span>
                        )}
                        <strong>{o.mandi}</strong>
                        {chosen && (
                          <span className="badge green small">Recommended</span>
                        )}
                        {o.mandi === advice.baseline_today.mandi &&
                          o.sell_day === 0 && (
                            <span className="badge small">Nearest</span>
                          )}
                      </div>
                      {o.flags.length > 0 && (
                        <div className="flags">
                          {o.flags.map((flag) => (
                            <span className="flag" key={flag}>
                              {flag === "stale"
                                ? "Old price"
                                : "Heavy arrivals"}
                            </span>
                          ))}
                        </div>
                      )}
                    </td>
                    <td>{o.distance_km} km</td>
                    <td>
                      <span className={o.sell_day ? "day-pill" : ""}>
                        {sellDay(o.sell_day)}
                      </span>
                    </td>
                    <td>
                      {o.price_low === o.price_high
                        ? rupees(o.price_mid)
                        : `${rupees(o.price_low)} – ${rupees(o.price_high)}`}
                      <small>
                        {o.sell_day ? "forecast" : "reported price"}
                      </small>
                    </td>
                    <td>{rupees(o.transport_per_qtl)}</td>
                    <td className="numeric">
                      <strong>{rupees(o.net_per_qtl)}</strong>
                      {chosen && <ArrowUpRight size={15} />}
                      <small>/harvested quintal</small>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <Empty
          title="No matching options"
          text="Try another mandi name or clear the selling-today filter."
        />
      )}
      <div className="table-pagination">
        <span>
          Showing {options.length ? page * pageSize + 1 : 0}–
          {Math.min((page + 1) * pageSize, options.length)} of {options.length}{" "}
          options
        </span>
        <div>
          <button
            className="button secondary"
            aria-label="Previous options page"
            disabled={page === 0}
            onClick={() => setPage((v) => v - 1)}
          >
            <ChevronLeft size={13} />
            Previous
          </button>
          <button
            className="button secondary"
            aria-label="Next options page"
            disabled={(page + 1) * pageSize >= options.length}
            onClick={() => setPage((v) => v + 1)}
          >
            Next
            <ChevronRight size={13} />
          </button>
        </div>
      </div>
      <div className="table-footer">
        <span>
          Nearest-today baseline: {advice.baseline_today.mandi} ·{" "}
          {rupees(advice.baseline_today.net)}/quintal
        </span>
        <span>Prices as of {advice.prices_as_of}</span>
      </div>
    </section>
  );
}
