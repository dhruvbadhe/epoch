"""Synthetic fixture self-test; run with the engine's local Python:

ml/engine/.venv/bin/python -B -m ml.engine.test_backtest

All writes, including temporary variations, stay under ml/engine. Synthetic
fixture outcomes are not evidence about performance on real market data.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
from datetime import date, timedelta
from pathlib import Path
from statistics import mean, median
from tempfile import TemporaryDirectory
from unittest.mock import patch

if __package__:
    from . import api, backtest
else:
    import api
    import backtest


_FIXTURES = Path(__file__).resolve().parent / "fixtures"
_FIELDS = {
    "crop", "assumptions", "test_period", "cases_tested", "cases_excluded_by_reason",
    "avg_gain_per_qtl", "median_gain_per_qtl", "loss_share", "worst_loss_per_qtl",
    "hold_cases", "hold_success_rate", "ladder", "coverage", "selfcheck",
    "forecast_period", "forecast_dates", "villages_tested", "cases_attempted",
    "decision_counts", "hold_record", "gain_split",
}


def _rows(name, folder=_FIXTURES):
    with (folder / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _snapshot(folder):
    if not folder.exists():
        return None
    return {
        str(path.relative_to(folder)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in folder.rglob("*") if path.is_file()
    }


def _run_recorded(crop, folder):
    decisions = {}

    def record(*args, **kwargs):
        decision = api.advise(*args, **kwargs)
        decisions[(kwargs["as_of_date"], args[2])] = decision
        return decision

    with patch.object(backtest, "advise", side_effect=record) as calls:
        result = backtest.run_backtest(crop, data_dir=folder)
    return result, decisions, calls.call_args_list


def _test_fixtures():
    for name, columns in backtest._COLUMNS.items():
        with (_FIXTURES / name).open(encoding="utf-8", newline="") as handle:
            assert tuple(csv.DictReader(handle).fieldnames) == tuple(columns), name
    splits = json.loads((_FIXTURES / "splits.json").read_text(encoding="utf-8"))
    assert set(splits) == {"train_end", "val_start", "val_end", "test_start", "test_end", "as_of_date"}
    assert len(_rows("villages.csv")) == 2
    assert len(_rows("mandis.csv")) == 2
    price_dates = sorted({date.fromisoformat(row["date"]) for row in _rows("prices_mh.csv")})
    assert len(price_dates) == 40
    assert (price_dates[-1] - price_dates[0]).days == 39
    forecast_dates = sorted({date.fromisoformat(row["as_of_date"]) for row in _rows("forecast_history.csv")})
    assert all((later - earlier).days == 3 for earlier, later in zip(forecast_dates, forecast_dates[1:]))
    print("PASS fixtures: exact handoff schemas, 2 mandis, 2 villages, 40 days, forecasts every 3rd day")


def _test_slices(result, decisions, calls):
    forecasts = _rows("forecast_history.csv")
    expected_dates = {"2026-07-01", "2026-07-04", "2026-07-07", "2026-07-10", "2026-07-13", "2026-07-16", "2026-07-19"}
    expected_pairs = {(as_of, village) for as_of in expected_dates for village in ("Niphad", "Chandori")}
    pairs = []
    for call in calls:
        crop, quantity, village = call.args
        as_of = call.kwargs["as_of_date"]
        pairs.append((as_of, village))
        assert crop == "onion" and quantity == 1
        assert call.kwargs["lot_condition"] is None and call.kwargs["overrides"] is None
        assert call.kwargs["apply_hold_gate"] is False
        assert call.kwargs["data_dir"] == _FIXTURES
        assert call.kwargs["forecast"] == [row for row in forecasts if row["crop"] == crop and row["as_of_date"] == as_of]
        assert {row["as_of_date"] for row in call.kwargs["forecast"]} == {as_of}
    assert len(pairs) == len(set(pairs)) == 14
    assert set(pairs) == expected_pairs
    assert set(decisions) == expected_pairs
    assert result["test_period"] == {"start": "2026-07-01", "end": "2026-07-19"}
    print("PASS decisions: advise called once for each of 14 date/village pairs, using only that date's slice with apply_hold_gate=False")


def _test_lookups():
    config = api._config(None)
    stale = config["confidence"]["stale_days"]
    window = config["forecast"]["target_match_window_days"]
    prices = backtest._Prices(_rows("prices_mh.csv"), "onion")
    assert prices.today("Lasalgaon", date(2026, 7, 13), stale) == 1733
    assert prices.today("Lasalgaon", date(2026, 7, 15), stale) == 1733  # Exactly 3 days old.
    assert prices.today("Lasalgaon", date(2026, 7, 16), stale) is None
    assert prices.today("Pimpalgaon", date(2026, 7, 19), stale) is None
    assert prices.today("Pimpalgaon", date(2026, 6, 27), stale) is None
    assert prices.held("Pimpalgaon", date(2026, 7, 1), 14, window) == 1720  # Exact target.
    assert prices.held("Pimpalgaon", date(2026, 7, 7), 14, window) == 1900  # Next beats previous.
    assert prices.held("Pimpalgaon", date(2026, 7, 13), 14, window) == 1870  # Previous when next is absent.
    assert prices.held("Pimpalgaon", date(2026, 7, 4), 1, window) is None  # Today exists, but is forbidden.
    assert prices.held("Pimpalgaon", date(2026, 7, 5), 1, window) == 1778  # One-day hold allows next.
    print("PASS real-price lookup: today never looks ahead; hold fallback order and 1-day exception")


def _manual_outcomes():
    config = api._config(None)
    village_coords = {row["village"]: (float(row["lat"]), float(row["lon"])) for row in _rows("villages.csv")}
    mandi_coords = {row["mandi"]: (float(row["lat"]), float(row["lon"])) for row in _rows("mandis.csv")}
    prices = {(row["date"], row["mandi"]): float(row["modal_price"]) for row in _rows("prices_mh.csv") if row["crop"] == "onion"}
    # Expected valid decisions and the independently identified report dates.
    outcomes = {
        "2026-07-01": (14, "2026-07-15", "2026-07-01"),
        "2026-07-07": (14, "2026-07-22", "2026-07-07"),
        "2026-07-10": (0, "2026-07-10", "2026-07-10"),
        "2026-07-13": (14, "2026-07-26", "2026-07-12"),
        "2026-07-19": (0, "2026-07-19", "2026-07-19"),
    }
    cases = []
    for village, origin in village_coords.items():
        costs = {
            mandi: api.haversine(origin, coords, unit=api.Unit.KILOMETERS)
            * config["transport"]["road_factor"] * config["transport"]["rate_per_km_per_qtl"]
            + config["transport"]["loading_per_qtl"]
            for mandi, coords in mandi_coords.items()
        }
        for as_of, (days, sale_report, baseline_report) in outcomes.items():
            baseline = prices[(baseline_report, "Lasalgaon")] - costs["Lasalgaon"] - config["fees_per_qtl"]
            sale_mandi = "Lasalgaon" if as_of == "2026-07-19" else "Pimpalgaon"
            # July 19's Pimpalgaon report is stale; the fresh baseline is the
            # only market available for today's comparison.
            highest_today = baseline if as_of == "2026-07-19" else prices[(as_of, "Pimpalgaon")] - costs["Pimpalgaon"] - config["fees_per_qtl"]
            best = max(baseline, highest_today)
            sale_net = prices[(sale_report, sale_mandi)] * (1 - config["spoilage_per_day"]["onion"]) ** days
            sale_net -= costs[sale_mandi] + config["storage_cost_per_qtl_per_day"]["onion"] * days + config["fees_per_qtl"]
            cases.append({
                "as_of": as_of, "village": village, "days": days,
                "gain": sale_net - baseline, "held": days > 0,
                "beats_best": sale_net > best, "beats_baseline": sale_net > baseline,
                "policies": {
                    "nearest_today": baseline, "highest_price_today": highest_today,
                    "best_net_today": best, "full_advice": sale_net,
                },
            })
    return cases


def _test_metrics(result, decisions):
    expected = _manual_outcomes()
    gains = [case["gain"] for case in expected]
    holds = [case for case in expected if case["held"]]
    for case in expected:
        choice = decisions[(case["as_of"], case["village"])]
        assert (choice["days"], choice["mandi"]) == (case["days"], "Lasalgaon" if case["as_of"] == "2026-07-19" else "Pimpalgaon")
    assert result["cases_tested"] == 10
    assert result["cases_excluded_by_reason"] == {
        "missing real price": 2,
        "no recent price at baseline mandi": 2,
    }
    assert result["avg_gain_per_qtl"] == round(mean(gains))
    assert result["median_gain_per_qtl"] == round(median(gains))
    assert result["worst_loss_per_qtl"] == round(min(gains)) < 0
    assert result["loss_share"] == sum(gain < 0 for gain in gains) / len(gains) == 0.2
    assert len(holds) == 6
    assert result["hold_cases"] == 8  # Two additional July 16 holds lack a baseline, but both win.
    assert result["decision_counts"] == {"sell_now": 4, "hold": 10}
    assert result["hold_record"] == {"won": 4, "lost": 4, "unscored": 2}
    assert result["cases_attempted"] == 14
    assert result["forecast_dates"] == 7 and result["villages_tested"] == 2
    assert result["forecast_period"] == result["test_period"]
    assert math.isclose(result["hold_success_rate"], 0.5)
    assert result["hold_success_rate"] != sum(case["beats_baseline"] for case in holds) / len(holds)
    assert result["gain_split"] == {
        "from_mandi_choice": round(mean(case["policies"]["best_net_today"] - case["policies"]["nearest_today"] for case in expected)),
        "from_holding": round(mean(case["policies"]["full_advice"] - case["policies"]["best_net_today"] for case in expected)),
    }
    assert [row["policy"] for row in result["ladder"]] == ["nearest_today", "highest_price_today", "best_net_today", "full_advice"]
    for row in result["ladder"]:
        assert row["avg_net"] == round(mean(case["policies"][row["policy"]] for case in expected))
    assert set(result) == _FIELDS
    assert result["assumptions"] == "default"
    assert result["coverage"] == [
        {"horizon_days": 1, "coverage": 0.5, "n": 4},
        {"horizon_days": 14, "coverage": 0.8, "n": 10},
    ]
    assert len(result["selfcheck"]) == 12
    assert {"mandi": "Pimpalgaon", "horizon_days": 14, "ratio": 0.8, "rows": 20, "passed": True} in result["selfcheck"]
    print("PASS exclusions: 10 gain cases; missing hold price=2, stale baseline=2; stale alternative remains scoreable")
    print("PASS gains/losses: compared with real nearest-today net, using unrounded calculations")
    print("PASS ladder: four policies evaluated on the same included cases")
    print("PASS hold_success_rate: 4/8 beat real fresh best_today; baseline-missing holds remain scoreable")
    print("PASS output shape and copied coverage/selfcheck")


def _test_changed_actual_prices(original, decisions):
    with TemporaryDirectory(prefix="backtest-test-", dir=_FIXTURES.parent) as temporary:
        folder = Path(temporary)
        for name in (*backtest._COLUMNS, "splits.json"):
            shutil.copyfile(_FIXTURES / name, folder / name)
        rows = _rows("prices_mh.csv", folder)
        for row in rows:
            change = row["crop"] == "onion" and (row["date"], row["mandi"]) in {
                ("2026-07-01", "Lasalgaon"), ("2026-07-07", "Pimpalgaon"),
            }
            if change:
                for key in ("modal_price", "min_price", "max_price"):
                    row[key] = str(float(row[key]) + 300)
        with (folder / "prices_mh.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=backtest._COLUMNS["prices_mh.csv"], lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        altered, altered_decisions, calls = _run_recorded("onion", folder)
        assert len(calls) == 14
        assert {key: (value["action"], value["days"], value["mandi"]) for key, value in altered_decisions.items()} == {
            key: (value["action"], value["days"], value["mandi"]) for key, value in decisions.items()
        }
        assert altered["cases_tested"] == original["cases_tested"]
        assert altered["cases_excluded_by_reason"] == original["cases_excluded_by_reason"]
        assert altered["avg_gain_per_qtl"] == original["avg_gain_per_qtl"] - 60
        assert altered["hold_success_rate"] == 0.25
    print("PASS changed actual prices: decisions stay locked; real baseline and real best_today change metrics")


def _test_zero_cases_and_preservation(onion):
    tomato = backtest.run_backtest("tomato", data_dir=_FIXTURES)
    assert tomato["cases_tested"] == 14 and tomato["hold_cases"] == 0
    assert tomato["hold_success_rate"] is None
    assert tomato["avg_gain_per_qtl"] == tomato["median_gain_per_qtl"] == tomato["worst_loss_per_qtl"] == 0
    assert tomato["loss_share"] == 0.0
    tomato_ladder = {row["policy"]: row["avg_net"] for row in tomato["ladder"]}
    assert tomato_ladder["best_net_today"] > tomato_ladder["highest_price_today"]
    assert tomato["coverage"] == [{"horizon_days": 1, "coverage": None, "n": 0}]
    with patch.object(backtest, "advise", wraps=api.advise) as calls:
        empty = backtest.run_backtest("soybean", data_dir=_FIXTURES)
    assert calls.call_count == 0
    assert empty["cases_tested"] == empty["hold_cases"] == 0
    assert empty["cases_excluded_by_reason"] == {}
    for key in ("avg_gain_per_qtl", "median_gain_per_qtl", "loss_share", "worst_loss_per_qtl", "hold_success_rate"):
        assert empty[key] is None
    assert all(row["avg_net"] is None for row in empty["ladder"])
    assert empty["gain_split"] == {"from_mandi_choice": None, "from_holding": None}
    assert empty["decision_counts"] == {"sell_now": 0, "hold": 0}
    assert empty["hold_record"] == {"won": 0, "lost": 0, "unscored": 0}
    saved = json.loads((_FIXTURES / "backtest.json").read_text(encoding="utf-8"))
    assert saved["onion"] == onion and saved["tomato"] == tomato and saved["soybean"] == empty
    assert set(saved) == {"onion", "tomato", "soybean"}
    assert all(set(value) == _FIELDS for value in saved.values())
    print("PASS zero-case metrics=null; measured no-loss metrics=0; no-hold success rate=null")
    print("PASS backtest.json keyed by crop, preserving results for other crops")


def _test_fresh_mandi_scoring():
    config = api._config(None)
    as_of = date(2026, 7, 1)
    stale = config["confidence"]["stale_days"]
    rows = [
        {"crop": "onion", "mandi": "Lasalgaon", "date": as_of.isoformat(), "modal_price": 1000},
        {"crop": "onion", "mandi": "Pimpalgaon", "date": as_of.isoformat(), "modal_price": 1100},
        {"crop": "onion", "mandi": "Pimpalgaon", "date": (as_of + timedelta(days=7)).isoformat(), "modal_price": 1300},
        {"crop": "onion", "mandi": "Stale", "date": (as_of - timedelta(days=stale + 1)).isoformat(), "modal_price": 9999},
    ]
    prices = backtest._Prices(rows, "onion")
    decision = {"days": 7, "mandi": "Pimpalgaon"}
    case, reason = backtest._evaluate(decision, "onion", as_of, {"Lasalgaon": 0, "Pimpalgaon": 0, "Stale": 100}, prices, config)
    assert reason is None and case.held and case.hold_succeeded
    assert case.policy_nets["best_net_today"] == case.policy_nets["highest_price_today"] == 1080
    assert case.policy_nets["nearest_today"] == 980
    # A stale nearest market prevents the gain measurement, not the hold score.
    case, reason = backtest._evaluate(decision, "onion", as_of, {"Lasalgaon": 10, "Pimpalgaon": 20, "Stale": 0}, prices, config)
    assert reason == "no recent price at baseline mandi" and case.gain is None
    assert case.held and case.hold_succeeded
    no_fresh, reason = backtest._evaluate(decision, "onion", as_of, {"Stale": 0}, prices, config)
    assert no_fresh is None and reason == "no recent price at best mandi"
    no_sale, reason = backtest._evaluate({"days": 14, "mandi": "Pimpalgaon"}, "onion", as_of, {"Lasalgaon": 0, "Pimpalgaon": 0}, prices, config)
    assert no_sale is None and reason == "missing real price"
    print("PASS fresh-mandi regression: stale alternative excluded; hold unscored only without fresh today or realized hold price")


def main():
    production_before = _snapshot(api._ROOT / "data")
    _test_fixtures()
    result, decisions, calls = _run_recorded("onion", _FIXTURES)
    _test_slices(result, decisions, calls)
    _test_lookups()
    _test_fresh_mandi_scoring()
    _test_metrics(result, decisions)
    _test_changed_actual_prices(result, decisions)
    _test_zero_cases_and_preservation(result)
    assert _snapshot(api._ROOT / "data") == production_before
    print("PASS production data folder untouched")
    print("All backtest self-tests passed (synthetic fixtures only).")


if __name__ == "__main__":
    main()
