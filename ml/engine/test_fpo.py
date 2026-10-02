"""Run with ml/engine/.venv/bin/python -B -m ml.engine.test_fpo.

Uses synthetic fixtures only; production data is checked for changes.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
from collections import defaultdict
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

if __package__:
    from . import api
else:
    import api


_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "fpo"
_REQUEST = json.loads((_FIXTURES / "request.json").read_text(encoding="utf-8"))


def _rows(name):
    with (_FIXTURES / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _snapshot(folder):
    if not folder.exists():
        return None
    return {str(path.relative_to(folder)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in folder.rglob("*") if path.is_file()}


def _fraction(value):
    return Fraction(str(value))


def _request(**changes):
    result = deepcopy(_REQUEST)
    result.update(changes)
    return result


def _lot(member, crop="onion", quantity=10, **changes):
    return {"member": member, "crop": crop, "quantity_qtl": quantity, "village": "Niphad", **changes}


def _build(request, data_dir=_FIXTURES):
    return api.fpo_plan(**request, data_dir=data_dir)


def _verify(plan, request, data_dir=_FIXTURES):
    config = api._config(request.get("overrides"))
    settings = config["fpo"]
    cap = request.get("mandi_cap_qtl_per_day")
    cap = settings["mandi_cap_qtl_per_day"] if cap is None else cap
    lots = {lot["member"]: lot for lot in request["lots"]}
    assert len(lots) == len(request["lots"])
    groups, assigned, unplaced = defaultdict(list), defaultdict(Fraction), defaultdict(Fraction)
    traders = {row["mandi"]: row["crops"].split("|") for row in _rows("mandis.csv")}
    forecast = request.get("forecast")
    forecast = _rows("forecast_table.csv") if forecast is None else forecast
    forecast_lookup = {(row["crop"], row["mandi"], int(row["horizon_days"])): row for row in forecast}
    baselines = {}
    for assignment in plan["assignments"]:
        lot = lots[assignment["member"]]
        quantity = _fraction(assignment["quantity_qtl"])
        assert quantity > 0 and assignment["mandi"] not in request.get("blocked_mandis", ())
        assert lot["crop"] in traders[assignment["mandi"]]
        assert assignment["sell_day"] <= api._hold_limit(lot["crop"], lot.get("lot_condition"), config)
        if lot.get("cash_needed_in_days") is not None:
            assert assignment["sell_day"] <= lot["cash_needed_in_days"]
        row = forecast_lookup[(lot["crop"], assignment["mandi"], assignment["sell_day"])]
        assert assignment["sell_day"] == 0 or str(row["uses_baseline"]).lower() == "false"
        if lot["member"] not in baselines:
            advice = api.advise(
                lot["crop"], lot["quantity_qtl"], lot["village"],
                lot_condition=lot.get("lot_condition"), cash_needed_in_days=lot.get("cash_needed_in_days"),
                blocked_mandis=request.get("blocked_mandis", ()), overrides=request.get("overrides"),
                as_of_date=plan["prices_as_of"], forecast=forecast, data_dir=data_dir,
                distances=request.get("distances"),
            )
            baselines[lot["member"]] = advice["baseline_today"]
        assert assignment["baseline_today"] == baselines[lot["member"]]
        assert assignment["origin"] == f"via {plan['collection_centre']}, shared truck"
        groups[(assignment["mandi"], assignment["sell_day"])].append(assignment)
        assigned[lot["member"]] += quantity
    for row in plan["unplaced"]:
        assert row["reason"] and "baseline_today" not in row
        unplaced[row["member"]] += _fraction(row["quantity_qtl"])
    for member, lot in lots.items():
        assert assigned[member] + unplaced[member] == _fraction(lot["quantity_qtl"]), member
    placed_total = sum(assigned.values(), Fraction())
    unplaced_total = sum(unplaced.values(), Fraction())
    assert _fraction(plan["placed_qtl"]) == placed_total
    assert _fraction(plan["unplaced_qtl"]) == unplaced_total
    assert placed_total + unplaced_total == sum((_fraction(lot["quantity_qtl"]) for lot in lots.values()), Fraction())
    assert {(truck["mandi"], truck["sell_day"]) for truck in plan["trucks"]} == set(groups)
    centre = request.get("collection_centre")
    centre = settings["collection_centre"] if centre is None else centre
    if isinstance(centre, str):
        centre = {"name": centre}
    if "lat" not in centre and request.get("distances") is None:
        coords = next(row for row in _rows("villages.csv") if row["village"] == centre["name"])
        centre = {**centre, "lat": coords["lat"], "lon": coords["lon"]}
    mandi_coords = {row["mandi"]: (float(row["lat"]), float(row["lon"])) for row in _rows("mandis.csv")}
    for truck in plan["trucks"]:
        group = groups[(truck["mandi"], truck["sell_day"])]
        quantity = sum((_fraction(row["quantity_qtl"]) for row in group), Fraction())
        assert quantity <= _fraction(cap)
        assert quantity == _fraction(truck["quantity_qtl"])
        assert truck["trips"] == math.ceil(quantity / _fraction(settings["truck_capacity_qtl"]))
        if request.get("distances") is not None:
            distance = request["distances"][centre["name"]][truck["mandi"]]
        else:
            distance = api.haversine((float(centre["lat"]), float(centre["lon"])), mandi_coords[truck["mandi"]], unit=api.Unit.KILOMETERS)
            distance *= config["transport"]["road_factor"]
        assert truck["cost"] == round(truck["trips"] * (settings["truck_fixed_cost"] + distance * settings["truck_per_km"]))
        assert sum(row["truck_share"] for row in group) == truck["cost"]
        for row in group:
            quota = truck["cost"] * _fraction(row["quantity_qtl"]) / quantity
            assert abs(_fraction(row["truck_share"]) - quota) < 1
    if plan["assignments"]:
        assert plan["total_net"] == sum(row["net_total"] for row in plan["assignments"])
        baseline = sum((_fraction(row["quantity_qtl"]) * row["baseline_today"]["net"] for row in plan["assignments"]), Fraction())
        assert plan["baseline_total"] == round(baseline)
        assert plan["gain_vs_baseline"] == plan["total_net"] - plan["baseline_total"]
    else:
        assert plan["total_net"] is plan["baseline_total"] is plan["gain_vs_baseline"] is None
    assert plan["assumptions_default"] == (not bool(request.get("overrides")))
    assert set(plan) == {
        "collection_centre", "assignments", "trucks", "total_net", "baseline_total", "gain_vs_baseline",
        "placed_qtl", "unplaced_qtl", "unplaced", "prices_as_of", "assumptions_default",
    }


def _test_hold_gate():
    request = _request(lots=[_lot("gated onion", quantity=60), _lot("gated tomato", crop="tomato", quantity=40)])
    missing_file_plan = _build(request)
    assert any(row["sell_day"] > 0 for row in missing_file_plan["assignments"] if row["crop"] == "onion")
    with TemporaryDirectory(prefix="fpo-gate-test-", dir=_FIXTURES.parent) as temporary:
        folder = Path(temporary)
        for name in ("forecast_table.csv", "villages.csv", "mandis.csv"):
            shutil.copyfile(_FIXTURES / name, folder / name)
        shutil.copyfile(api._ROOT / "data" / "backtest.json", folder / "backtest.json")
        for blocked in ([], ["Pimpalgaon"]):
            current = {**request, "blocked_mandis": blocked}
            plan = _build(current, data_dir=folder)
            _verify(plan, current, data_dir=folder)
            assert all(row["sell_day"] == 0 for row in plan["assignments"])
            assert all("holds suppressed" in row["reason"] for row in plan["assignments"])
            assert all("won 40 of 124" in row["reason"] for row in plan["assignments"] if row["crop"] == "onion")
    print("PASS FPO hold gate: same real crop records remove all holds, including after a closure; missing file preserves holds")


def main():
    production_before = _snapshot(api._ROOT / "data")
    request = _request()
    with patch.object(api, "_options", wraps=api._options) as shared_options, patch.object(api, "_money_in_hand", wraps=api._money_in_hand) as shared_money:
        plan = _build(request)
    assert shared_options.call_count >= len(request["lots"])
    assert shared_money.call_count > 0
    _verify(plan, request)
    assert [row["member"] for row in plan["assignments"]] == ["A", "B", "B", "E", "D", "C", "C"]
    assert plan["placed_qtl"] == 435 and plan["unplaced_qtl"] == 50
    assert plan["unplaced"] == [{"member": "D", "quantity_qtl": 50, "reason": "no mandi with room before its hold limit"}]
    assert (plan["total_net"], plan["baseline_total"], plan["gain_vs_baseline"]) == (708709, 681050, 27659)
    print("PASS shared option/money code; urgent lots first, then shorter hold limits")
    print("PASS caps and splits: placed=435 qtl, unplaced=50 qtl; every lot reconciles")
    print("PASS truck shares: proportional whole-rupee shares sum exactly to every group's trip cost")
    print("PASS baselines match advise(); totals cover placed quantity only and add up")

    mixed = _request(lots=[_lot("onion", quantity=40, cash_needed_in_days=1), _lot("tomato", crop="tomato", quantity=60, cash_needed_in_days=1)], mandi_cap_qtl_per_day=300)
    mixed_plan = _build(mixed)
    _verify(mixed_plan, mixed)
    assert len(mixed_plan["trucks"]) == 1
    assert mixed_plan["trucks"][0]["quantity_qtl"] == 100
    assert {row["crop"] for row in mixed_plan["assignments"]} == {"onion", "tomato"}
    multi = _request(lots=[_lot("first", quantity=30, cash_needed_in_days=1), _lot("second", quantity=75, cash_needed_in_days=1), _lot("third", quantity=100, cash_needed_in_days=1)], mandi_cap_qtl_per_day=300)
    multi_plan = _build(multi)
    _verify(multi_plan, multi)
    assert len(multi_plan["trucks"]) == 1 and multi_plan["trucks"][0]["trips"] == 3
    fractional = _request(lots=[_lot("fraction A", quantity=0.1, cash_needed_in_days=1), _lot("fraction B", quantity=0.2, cash_needed_in_days=1)], mandi_cap_qtl_per_day=0.15)
    fractional_plan = _build(fractional)
    _verify(fractional_plan, fractional)
    assert fractional_plan["placed_qtl"] == 0.3 and fractional_plan["unplaced_qtl"] == 0
    print("PASS mixed-crop shared trucks, multiple trips and fractional-quantity reconciliation")

    closed = _request(blocked_mandis=["Pimpalgaon"])
    closed_plan = _build(closed)
    _verify(closed_plan, closed)
    affected = {row["member"] for row in plan["assignments"] if row["mandi"] == "Pimpalgaon"}
    for row in closed_plan["assignments"]:
        assert (row["reason"] == "moved: mandi unavailable") == (row["member"] in affected)
    print("PASS blocked mandi receives nothing; closure reasons follow the original capped allocation")

    onion_closed = _request(blocked_mandis=["Lasalgaon", "Pimpalgaon"])
    continuing = _build(onion_closed)
    _verify(continuing, onion_closed)
    assert all(row["crop"] == "tomato" and row["mandi"] == "Nashik" for row in continuing["assignments"])
    onion_members = {lot["member"] for lot in onion_closed["lots"] if lot["crop"] == "onion"}
    assert {row["member"] for row in continuing["unplaced"]} == onion_members
    assert all(row["reason"] == "every mandi for this crop is unavailable" for row in continuing["unplaced"])
    assert continuing["placed_qtl"] == 60 and continuing["unplaced_qtl"] == 425
    tomato_only = _request(lots=[lot for lot in onion_closed["lots"] if lot["crop"] == "tomato"], blocked_mandis=onion_closed["blocked_mandis"])
    tomato_only_plan = _build(tomato_only)
    assert all(continuing[key] == tomato_only_plan[key] for key in ("total_net", "baseline_total", "gain_vs_baseline"))
    try:
        api.advise("onion", 10, "Niphad", blocked_mandis=onion_closed["blocked_mandis"], data_dir=_FIXTURES)
    except ValueError as error:
        assert str(error) == "no tradable, unblocked mandis for onion"
    else:
        raise AssertionError("advise must still reject a crop with every mandi blocked")
    print("PASS every onion mandi blocked: onion unplaced, tomato planned; totals cover only 60 tomato qtl")

    for no_placement in (
        _request(blocked_mandis=["Lasalgaon", "Pimpalgaon", "Nashik"]),
        _request(mandi_cap_qtl_per_day=0),
        _request(lots=[]),
    ):
        empty = _build(no_placement)
        _verify(empty, no_placement)
        assert not empty["assignments"] and not empty["trucks"] and empty["placed_qtl"] == 0
    invalid_lot = _request(lots=[_lot("invalid", crop="wheat", quantity=5), _lot("valid tomato", crop="tomato", quantity=10)])
    invalid_plan = _build(invalid_lot)
    _verify(invalid_plan, invalid_lot)
    assert invalid_plan["unplaced"] == [{"member": "invalid", "quantity_qtl": 5, "reason": "unknown crop: wheat"}]
    print("PASS unavailable/invalid lots stay unplaced; no-placement totals are null")

    overridden = _request(
        lots=[_lot("override", quantity=90)], mandi_cap_qtl_per_day=None, collection_centre=None,
        overrides={
            "fpo": {"collection_centre": {"name": "Depot", "lat": 20, "lon": 74.05},
                    "truck_capacity_qtl": 50, "truck_fixed_cost": 2000, "truck_per_km": 40,
                    "first_mile_per_qtl": 25, "mandi_cap_qtl_per_day": 60},
            "fees_per_qtl": 5, "spoilage_per_day": {"onion": 0.005},
            "storage_cost_per_qtl_per_day": {"onion": 2},
        },
    )
    override_plan = _build(overridden)
    _verify(override_plan, overridden)
    assert override_plan["collection_centre"] == "Depot" and override_plan["assumptions_default"] is False
    assert any(truck["trips"] == 2 for truck in override_plan["trucks"])
    assert all(row["first_mile"] == 25 and row["storage"] == row["sell_day"] * 2 for row in override_plan["assignments"])
    name_only = _request(collection_centre="Niphad")
    assert _build(name_only) == plan
    matrix = {name: {"Lasalgaon": 10, "Pimpalgaon": 20, "Nashik": 30} for name in ("Depot", "Niphad", "Chandori")}
    injected = _request(collection_centre={"name": "Depot"}, distances=matrix)
    injected_plan = _build(injected)
    _verify(injected_plan, injected)
    multiplier_changed = {**injected, "overrides": {"transport": {"road_factor": 99}}}
    bypassed = _build(multiplier_changed)
    assert injected_plan["assignments"] == bypassed["assignments"] and injected_plan["trucks"] == bypassed["trucks"]
    print("PASS configuration overrides, coordinate/name centres and injected road-distance bypass")

    unreliable = _rows("forecast_table.csv")
    row = next(row for row in unreliable if row["crop"] == "tomato" and row["mandi"] == "Pimpalgaon" and row["horizon_days"] == "1")
    row.update(price_low="8000", price_mid="9000", price_high="10000")
    fallback = _request(lots=[_lot("no unreliable hold", crop="tomato", quantity=10)], forecast=unreliable)
    fallback_plan = _build(fallback)
    _verify(fallback_plan, fallback)
    assert all(row["sell_day"] == 0 for row in fallback_plan["assignments"])
    print("PASS failed self-check forecasts cannot create FPO holds")
    _test_hold_gate()
    assert _snapshot(api._ROOT / "data") == production_before
    (_FIXTURES / "sample_plan.json").write_text(json.dumps(plan, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print("PASS production data folder untouched")
    print("All FPO self-tests passed (synthetic fixtures only).")


if __name__ == "__main__":
    main()
