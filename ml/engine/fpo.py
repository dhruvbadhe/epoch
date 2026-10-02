"""Rule-based FPO allocator (ML2_ENGINE.md, sections 7–8).

Ranking assumes full trucks; final groups pay for their actual whole trips.
All eligibility and money-in-hand calculations are shared with Advice.
Returned totals compare only placed produce. This is not an optimal plan.
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from fractions import Fraction

if __package__:
    from . import api
else:
    import api


def _weight(value, label, *, positive=False):
    number = api._nonnegative(value, label)
    if positive and number == 0:
        raise ValueError(f"{label} must be positive")
    return Fraction(str(value))


def _quantity(value):
    return int(value) if value.denominator == 1 else float(value)


def _centre(value, config, data_dir, distances):
    value = config["fpo"]["collection_centre"] if value is None else value
    if isinstance(value, str):
        value = {"name": value}
    if not isinstance(value, Mapping) or not value.get("name"):
        raise ValueError("set fpo.collection_centre or pass a named collection_centre")
    centre = dict(value)
    if distances is not None and centre["name"] in distances:
        return centre
    if centre.get("lat") is None or centre.get("lon") is None:
        villages = api._optional_csv("villages.csv", data_dir=data_dir) or ()
        row = next((row for row in villages if row["village"] == centre["name"]), None)
        if row is None:
            raise ValueError("collection_centre needs lat and lon, or a known village name")
        centre.update(lat=row["lat"], lon=row["lon"])
    centre["lat"] = api._number(centre["lat"], "collection centre lat")
    centre["lon"] = api._number(centre["lon"], "collection centre lon")
    return centre


@dataclass
class _Lot:
    index: int
    member: str
    crop: str
    quantity: Fraction
    village: str
    deadline: int | None
    hold_limit: int
    options: list
    baseline: dict | None = None
    hold_gate_note: str | None = None

    @property
    def priority(self):
        return (math.inf if self.deadline is None else self.deadline, self.hold_limit, self.index)


@dataclass(frozen=True)
class _Placement:
    lot: _Lot
    option: api._Option
    quantity: Fraction
    moved_for_cap: bool


def _allocate(lots, cap, blocked):
    used = defaultdict(Fraction)
    placements, unplaced = [], []
    for lot in sorted(lots, key=lambda lot: lot.priority):
        remaining = lot.quantity
        options = [option for option in lot.options if option.mandi not in blocked]
        for rank, option in enumerate(options):
            key = (option.mandi, option.day)
            room = max(Fraction(), cap - used[key])
            quantity = min(remaining, room)
            if quantity > 0:
                placements.append(_Placement(lot, option, quantity, rank > 0))
                used[key] += quantity
                remaining -= quantity
            if remaining == 0:
                break
        if remaining > 0:
            reason = ("every mandi for this crop is unavailable" if not options
                      else "no mandi with room before its hold limit")
            unplaced.append({"member": lot.member, "quantity_qtl": _quantity(remaining), "reason": reason})
    return placements, unplaced


def _shares(cost, weights):
    """Largest-remainder rounding keeps whole-rupee shares equal to cost."""
    total = sum(weights, Fraction())
    quotas = [cost * weight / total for weight in weights]
    shares = [math.floor(quota) for quota in quotas]
    order = sorted(range(len(weights)), key=lambda index: quotas[index] - shares[index], reverse=True)
    for index in order[:cost - sum(shares)]:
        shares[index] += 1
    return shares


def _reason(placement, affected):
    if placement.lot.index in affected:
        return "moved: mandi unavailable"
    if placement.moved_for_cap:
        return "moved: mandi cap reached"
    if placement.lot.deadline is not None:
        unit = "day" if placement.lot.deadline == 1 else "days"
        return f"needs cash in {placement.lot.deadline} {unit}"
    return "best net"


def fpo_plan(lots, blocked_mandis=(), mandi_cap_qtl_per_day=None,
             collection_centre=None, overrides=None, *, as_of_date=None,
             forecast=None, data_dir=None, distances=None) -> dict:
    """Place urgent lots first; an unavailable crop does not fail other lots.

    The original allocation, including its caps, identifies lots displaced
    by blocked mandis. Actual assignments use only non-blocked mandis and
    each lot's own Advice baseline. Totals reconcile with returned assignments;
    they are None when no quantity is placed. The shared measured-record gate
    removes all hold options for suppressed crops. This function writes no files.
    """
    config = api._config(overrides)
    settings = config["fpo"]
    cap = _weight(settings["mandi_cap_qtl_per_day"] if mandi_cap_qtl_per_day is None else mandi_cap_qtl_per_day, "mandi-day cap")
    capacity = _weight(settings["truck_capacity_qtl"], "truck capacity", positive=True)
    fixed = api._nonnegative(settings["truck_fixed_cost"], "truck fixed cost")
    per_km = api._nonnegative(settings["truck_per_km"], "truck cost per km")
    first_mile = api._nonnegative(settings["first_mile_per_qtl"], "first-mile cost")
    centre = _centre(collection_centre, config, data_dir, distances)
    forecast = api._forecast_table(forecast, data_dir=data_dir)
    blocked = set(blocked_mandis)

    def trip_cost(distance):
        return fixed + distance * per_km

    def full_truck_transport(distance):
        return trip_cost(distance) / float(capacity) + first_mile

    prepared, eligible, unplaced, dates = [], [], [], set()
    for index, row in enumerate(lots):
        if not isinstance(row, Mapping) or any(key not in row for key in ("member", "crop", "quantity_qtl", "village")):
            raise ValueError("each lot needs member, crop, quantity_qtl and village")
        quantity = _weight(row["quantity_qtl"], "lot quantity_qtl", positive=True)
        crop, member, village = row["crop"], row["member"], row["village"]
        try:
            options, hold_limit, reference_date = api._options(
                crop, centre, row.get("lot_condition"), row.get("cash_needed_in_days"), (),
                config, as_of_date, forecast, data_dir=data_dir, distances=distances,
                transport_for_distance=full_truck_transport,
            )
            deadline = (None if row.get("cash_needed_in_days") is None else
                        api._days(row["cash_needed_in_days"], "cash_needed_in_days"))
            ranked = api._ranked_options(options)
            record = api._suppressed_hold_record(crop, config, data_dir=data_dir)
            gate_note = None
            if record is not None:
                gate_note = f"holds suppressed: {api._hold_record_text(record)}"
                ranked = [option for option in ranked if option.day == 0]
            lot = _Lot(index, member, crop, quantity, village, deadline, hold_limit, ranked, hold_gate_note=gate_note)
            prepared.append(lot)
            dates.add(reference_date)
            advice = api.advise(
                crop, float(quantity), village, lot_condition=row.get("lot_condition"),
                cash_needed_in_days=row.get("cash_needed_in_days"), blocked_mandis=blocked,
                overrides=overrides, as_of_date=reference_date, forecast=forecast,
                data_dir=data_dir, distances=distances,
            )
            lot.baseline = advice["baseline_today"]
            eligible.append(lot)
        except ValueError as error:
            reason = str(error)
            if reason == f"no tradable, unblocked mandis for {crop}":
                reason = "every mandi for this crop is unavailable"
            elif prepared and prepared[-1].index == index:
                prepared.pop()  # An invalid lot must not consume counterfactual room.
            unplaced.append({"member": member, "quantity_qtl": _quantity(quantity), "reason": reason})
    if len(dates) > 1:
        raise ValueError("all FPO lots must use the same as_of_date")
    if dates:
        reference_date = next(iter(dates))
    else:
        reference_date = api._date(as_of_date, "as_of_date") if as_of_date is not None else None
        if reference_date is None:
            forecast_dates = {api._date(row["as_of_date"], "as_of_date") for row in forecast}
            if len(forecast_dates) == 1:
                reference_date = next(iter(forecast_dates))

    original, _ = _allocate(prepared, cap, set()) if blocked else ([], [])
    affected = {placement.lot.index for placement in original if placement.option.mandi in blocked}
    placements, leftovers = _allocate(eligible, cap, blocked)
    unplaced.extend(leftovers)
    groups = defaultdict(list)
    for index, placement in enumerate(placements):
        groups[(placement.option.mandi, placement.option.day)].append(index)
    trucks, truck_shares = [], {}
    for (mandi, day), indices in sorted(groups.items()):
        weights = [placements[index].quantity for index in indices]
        group_quantity = sum(weights, Fraction())
        trips = math.ceil(group_quantity / capacity)
        cost = round(trips * trip_cost(placements[indices[0]].option.distance))
        trucks.append({"mandi": mandi, "sell_day": day, "quantity_qtl": _quantity(group_quantity), "trips": trips, "cost": cost})
        truck_shares.update(zip(indices, _shares(cost, weights)))
    assignments = []
    baseline_values = []
    for index, placement in enumerate(placements):
        lot, option, quantity = placement.lot, placement.option, float(placement.quantity)
        truck_share = truck_shares[index]
        net = quantity * option.net_for_price(option.mid, transport=first_mile) - truck_share
        reason = _reason(placement, affected)
        if reason == "best net" and lot.hold_limit < config["hold_limit_days"][lot.crop]["default"]:
            reason = "short hold limit"
        if lot.hold_gate_note:
            reason += f"; {lot.hold_gate_note}"
        assignments.append({
            "member": lot.member, "crop": lot.crop, "quantity_qtl": _quantity(placement.quantity),
            "mandi": option.mandi, "sell_day": option.day, "price": round(option.mid),
            "first_mile": round(first_mile), "truck_share": truck_share, "storage": round(option.storage),
            "net_total": round(net), "net_per_qtl": round(net / quantity),
            "baseline_today": dict(lot.baseline), "reason": reason,
            "origin": f"via {centre['name']}, shared truck",
        })
        baseline_values.append(quantity * lot.baseline["net"])
    total_net = sum(row["net_total"] for row in assignments) if assignments else None
    baseline_total = round(math.fsum(baseline_values)) if assignments else None
    placed_quantity = sum((placement.quantity for placement in placements), Fraction())
    unplaced_quantity = sum((_weight(row["quantity_qtl"], "unplaced quantity") for row in unplaced), Fraction())
    return {
        "collection_centre": centre["name"], "assignments": assignments, "trucks": trucks,
        "total_net": total_net, "baseline_total": baseline_total,
        "gain_vs_baseline": total_net - baseline_total if assignments else None,
        "placed_qtl": _quantity(placed_quantity), "unplaced_qtl": _quantity(unplaced_quantity),
        "unplaced": unplaced, "prices_as_of": reference_date.isoformat() if reference_date else None,
        "assumptions_default": not bool(overrides),
    }
