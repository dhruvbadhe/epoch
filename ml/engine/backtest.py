"""Test-block backtest at default assumptions (ML2_ENGINE.md, section 9).

Results are "simulated on last season's reported prices, at our default
assumptions". These overlapping observations are simulated cases.

run_backtest(crop) uses the repository's data directory. Supplying data_dir
isolates every handoff input and writes only data_dir/backtest.json, preserving
other crops. No training, forecast generation, or FPO planning happens here.
"""

from __future__ import annotations

import argparse
import json
from bisect import bisect_right
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import timedelta
from statistics import mean, median

if __package__:
    from . import api
else:
    import api

advise = api.advise

_COLUMNS = {
    "forecast_history.csv": api._FORECAST_COLUMNS,
    "prices_mh.csv": ("date", "crop", "mandi", "modal_price", "min_price", "max_price"),
    "villages.csv": ("village", "name_mr", "name_hi", "lat", "lon"),
    "mandis.csv": ("mandi", "lat", "lon", "crops"),
    "coverage.csv": ("crop", "horizon_days", "coverage", "n"),
    "selfcheck.csv": ("crop", "mandi", "horizon_days", "model_mae", "same_as_today_mae", "ratio", "rows", "passed"),
}
_POLICIES = ("nearest_today", "highest_price_today", "best_net_today", "full_advice")


def _table(data_dir, name, *, optional=False):
    path = data_dir / name
    if not path.is_file():
        if optional:
            return ()
        raise ValueError(f"missing backtest input: {path}")
    rows = api._read_csv(path)
    if any(any(column not in row for column in _COLUMNS[name]) for row in rows):
        raise ValueError(f"{name} must use the handoff schema")
    return rows


def _json(path):
    try:
        with path.open(encoding="utf-8") as handle:
            result = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read backtest JSON input: {path}") from error
    if not isinstance(result, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return result


class _Prices:
    """Index actual reported prices; never forward-fill a realized sale."""

    def __init__(self, rows, crop):
        self.values = defaultdict(dict)
        for row in rows:
            if row["crop"] != crop:
                continue
            reported = api._date(row["date"], "price date")
            series = self.values[row["mandi"]]
            if reported in series:
                raise ValueError(f"duplicate real price for {crop} at {row['mandi']} on {reported}")
            series[reported] = api._number(row["modal_price"], "modal_price")
        self.dates = {mandi: sorted(series) for mandi, series in self.values.items()}

    def today(self, mandi, as_of_date, stale_days):
        dates = self.dates.get(mandi, ())
        position = bisect_right(dates, as_of_date) - 1
        if position < 0:
            return None
        reported = dates[position]
        if (as_of_date - reported).days > stale_days:
            return None
        return self.values[mandi][reported]

    def held(self, mandi, as_of_date, days, match_window):
        target = as_of_date + timedelta(days=days)
        series = self.values.get(mandi, {})
        if target in series:
            return series[target]
        # Next day first, then previous. A one-day hold cannot use the
        # previous day: it would reuse a price known when deciding to hold.
        for offset in range(1, match_window + 1):
            reported = target + timedelta(days=offset)
            if reported in series:
                return series[reported]
        if days != 1:
            for offset in range(1, match_window + 1):
                reported = target - timedelta(days=offset)
                if reported in series:
                    return series[reported]
        return None


def _real_net(price, crop, days, distance, config):
    sellable, transport, storage, fees = api._costs(crop, days, distance, config)
    return api._money_in_hand(price, sellable, transport, storage, fees)


@dataclass(frozen=True)
class _Case:
    gain: float | None
    policy_nets: dict[str, float | None]
    held: bool
    hold_succeeded: bool


def _evaluate(decision, crop, as_of_date, distances, prices, config):
    baseline_mandi = min(distances, key=lambda mandi: (distances[mandi], mandi))
    stale_days = api._days(config["confidence"]["stale_days"], "confidence.stale_days")
    today_prices = {}
    for mandi in distances:
        price = prices.today(mandi, as_of_date, stale_days)
        if price is not None:
            today_prices[mandi] = price
    if not today_prices:
        return None, "no recent price at best mandi"
    today_nets = {
        mandi: _real_net(price, crop, 0, distances[mandi], config)
        for mandi, price in today_prices.items()
    }
    best_today_net = max(today_nets.values())
    highest_price_mandi = max(today_prices, key=today_prices.get)
    days, mandi = decision["days"], decision["mandi"]
    holding = days > 0
    if holding:
        match_window = api._days(config["forecast"]["target_match_window_days"], "forecast.target_match_window_days")
        real_price = prices.held(mandi, as_of_date, days, match_window)
        if real_price is None:
            return None, "missing real price"
        advice_net = _real_net(real_price, crop, days, distances[mandi], config)
    else:
        if mandi not in today_nets:
            return None, "no recent price at chosen mandi"
        advice_net = today_nets[mandi]
    baseline_net = today_nets.get(baseline_mandi)
    # Missing baseline coverage prevents gain/ladder measurement, but a hold
    # can still be scored against the best fresh mandi available today.
    return _Case(
        advice_net - baseline_net if baseline_net is not None else None,
        {
            "nearest_today": baseline_net,
            "highest_price_today": today_nets[highest_price_mandi],
            "best_net_today": best_today_net,
            "full_advice": advice_net,
        },
        holding,
        holding and advice_net > best_today_net,
    ), "no recent price at baseline mandi" if baseline_net is None else None


def _nullable_number(value, label):
    return None if value.strip().lower() in ("", "null", "none") else api._number(value, label)


def _evidence(crop, data_dir):
    coverage = [
        {
            "horizon_days": api._days(row["horizon_days"], "coverage horizon_days"),
            "coverage": _nullable_number(row["coverage"], "coverage"),
            "n": api._days(row["n"], "coverage n"),
        }
        for row in _table(data_dir, "coverage.csv", optional=True) if row["crop"] == crop
    ]
    selfcheck = [
        {
            "mandi": row["mandi"], "horizon_days": api._days(row["horizon_days"], "selfcheck horizon_days"),
            "ratio": _nullable_number(row["ratio"], "selfcheck ratio"),
            "rows": api._days(row["rows"], "selfcheck rows"),
            "passed": api._boolean(row["passed"], "selfcheck passed"),
        }
        for row in _table(data_dir, "selfcheck.csv", optional=True) if row["crop"] == crop
    ]
    return coverage, selfcheck


def run_backtest(crop, data_dir=None) -> dict:
    """Evaluate every in-test (as_of_date, listed village) once and save it.

    Only the current date's forecast slice reaches advise(), with default
    freshness and costs. Decisions are locked before looking up realized
    outcomes. All four ladder policies use the same included simulated cases.
    Monetary metrics are rounded only when constructing the output; measured
    zero counts remain zero, and metrics with no eligible cases are None.
    Hold records use every measurable hold, including those without a fresh
    baseline; gains and ladder policies require that baseline.
    """
    config = api._config(None)
    if crop not in config["spoilage_per_day"]:
        raise ValueError(f"unknown crop: {crop}")
    data_dir = api._data_dir(data_dir)
    forecasts = _table(data_dir, "forecast_history.csv")
    price_rows = _table(data_dir, "prices_mh.csv")
    villages = _table(data_dir, "villages.csv")
    mandis = _table(data_dir, "mandis.csv")
    splits = _json(data_dir / "splits.json")
    try:
        test_start = api._date(splits["test_start"], "test_start")
        test_end = api._date(splits["test_end"], "test_end")
    except KeyError as error:
        raise ValueError("splits.json must contain test_start and test_end") from error
    if test_start > test_end:
        raise ValueError("test_start must not be after test_end")
    village_names = [row["village"] for row in villages]
    if len(village_names) != len(set(village_names)):
        raise ValueError("villages.csv contains duplicate village names")
    tradable = sorted(row["mandi"] for row in mandis if crop in row["crops"].split("|"))
    if len(tradable) != len(set(tradable)):
        raise ValueError("mandis.csv contains duplicate mandi names for this crop")
    slices = defaultdict(list)
    for row in forecasts:
        if row["crop"] == crop:
            as_of_date = api._date(row["as_of_date"], "forecast as_of_date")
            if test_start <= as_of_date <= test_end:
                slices[as_of_date].append(row)
    if slices and not tradable:
        raise ValueError(f"no tradable mandis for {crop}")
    distances = {
        village: {
            mandi: api.road_distance_km(village, mandi, config=config, data_dir=data_dir)
            for mandi in tradable
        }
        for village in village_names
    }
    prices = _Prices(price_rows, crop)
    cases, holds = [], []
    excluded = Counter()
    decision_counts = Counter(sell_now=0, hold=0)
    hold_record = {"won": 0, "lost": 0, "unscored": 0}
    for as_of_date, forecast_slice in sorted(slices.items()):
        for village in village_names:
            decision = advise(
                crop, 1, village, lot_condition=None, overrides=None,
                as_of_date=as_of_date.isoformat(), forecast=forecast_slice,
                data_dir=data_dir, apply_hold_gate=False, distances=distances,
            )
            decision_counts[decision["action"]] += 1
            case, reason = _evaluate(decision, crop, as_of_date, distances[village], prices, config)
            if decision["days"] > 0:
                if case is None:
                    hold_record["unscored"] += 1
                else:
                    holds.append(case)
                    hold_record["won" if case.hold_succeeded else "lost"] += 1
            if reason is not None:
                excluded[reason] += 1
            else:
                cases.append(case)
    gains = [case.gain for case in cases]
    mandi_gains = [case.policy_nets["best_net_today"] - case.policy_nets["nearest_today"] for case in cases]
    holding_gains = [case.policy_nets["full_advice"] - case.policy_nets["best_net_today"] for case in cases]
    coverage, selfcheck = _evidence(crop, data_dir)
    result = {
        "crop": crop, "assumptions": "default",
        "test_period": {"start": test_start.isoformat(), "end": test_end.isoformat()},
        "forecast_period": {"start": min(slices).isoformat(), "end": max(slices).isoformat()} if slices else None,
        "forecast_dates": len(slices), "villages_tested": len(village_names) if slices else 0,
        "cases_attempted": sum(decision_counts.values()),
        "cases_tested": len(cases), "cases_excluded_by_reason": dict(sorted(excluded.items())),
        "decision_counts": dict(decision_counts), "hold_record": hold_record,
        "gain_split": {
            "from_mandi_choice": round(mean(mandi_gains)) if cases else None,
            "from_holding": round(mean(holding_gains)) if cases else None,
        },
        "avg_gain_per_qtl": round(mean(gains)) if gains else None,
        "median_gain_per_qtl": round(median(gains)) if gains else None,
        "loss_share": sum(gain < 0 for gain in gains) / len(gains) if gains else None,
        "worst_loss_per_qtl": round(min(0, min(gains))) if gains else None,
        "hold_cases": len(holds),
        "hold_success_rate": sum(case.hold_succeeded for case in holds) / len(holds) if holds else None,
        "ladder": [
            {"policy": policy, "avg_net": round(mean(case.policy_nets[policy] for case in cases)) if cases else None}
            for policy in _POLICIES
        ],
        "coverage": coverage, "selfcheck": selfcheck,
    }
    output_path = data_dir / "backtest.json"
    results = _json(output_path) if output_path.is_file() else {}
    results[crop] = result
    output_path.write_text(json.dumps(results, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    api._read_backtest.cache_clear()
    return result


def main():
    parser = argparse.ArgumentParser(description="Simulated cases at default assumptions.")
    parser.add_argument("crop", choices=tuple(api._config(None)["spoilage_per_day"]))
    parser.add_argument("--data-dir", default=None, help="Input/output folder; defaults to repository data/.")
    arguments = parser.parse_args()
    result = run_backtest(arguments.crop, data_dir=arguments.data_dir)
    print("simulated on last season's reported prices, at our default assumptions")
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
