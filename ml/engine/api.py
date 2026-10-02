"""Money-in-hand advice from the ML 2 specification, sections 2–5.

Dependencies: PyYAML and haversine. Forecasts can be iterables of row dicts
in the handoff CSV schema, or pandas DataFrames. Existing handoff files and
the default config are cached; missing files are never created by the engine.
"""

from __future__ import annotations

import csv
import json
import math
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, replace
from datetime import date
from functools import cache
from pathlib import Path

import yaml
from haversine import Unit, haversine


_ROOT = Path(__file__).resolve().parents[2]
_FORECAST_COLUMNS = (
    "crop", "mandi", "as_of_date", "horizon_days", "price_low", "price_mid",
    "price_high", "uses_baseline", "last_price_date", "falling",
)
_UNRELIABLE_NOTE = "forecast not reliable here; compared today's prices only"


@cache
def _defaults():
    with (_ROOT / "config.yaml").open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _deep_merge(defaults, overrides):
    merged = deepcopy(defaults)
    for key, value in overrides.items():
        if key not in merged:
            raise ValueError(f"unknown config override: {key}")
        if isinstance(merged[key], Mapping):
            if not isinstance(value, Mapping):
                raise ValueError(f"config override {key} must be a mapping")
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def _config(overrides):
    if overrides is None:
        return _defaults()
    if not isinstance(overrides, Mapping):
        raise ValueError("overrides must be a partial copy of config.yaml")
    return _deep_merge(_defaults(), overrides)


@cache
def _read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return tuple(csv.DictReader(handle))


def _data_dir(data_dir=None):
    return (_ROOT / "data") if data_dir is None else Path(data_dir).resolve()


def _optional_csv(name, data_dir=None):
    path = _data_dir(data_dir) / name
    return _read_csv(path) if path.is_file() else None


def _number(value, label):
    try:
        if isinstance(value, bool):
            raise ValueError
        result = float(value)
        if not math.isfinite(result):
            raise ValueError
        return result
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{label} must be a finite number") from error


def _nonnegative(value, label):
    result = _number(value, label)
    if result < 0:
        raise ValueError(f"{label} must not be negative")
    return result


def _days(value, label):
    result = _nonnegative(value, label)
    if not result.is_integer():
        raise ValueError(f"{label} must be a whole number of days")
    return int(result)


def _date(value, label):
    if type(value) is date:
        return value
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} must be a YYYY-MM-DD date") from error


def _boolean(value, label):
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip().lower() in ("true", "false"):
        return value.strip().lower() == "true"
    raise ValueError(f"{label} must be true or false")


def road_distance_km(village, mandi, *, config=None, data_dir=None, distances=None):
    """Reusable distance lookup; supplied distances are already road km.

    With no matrix, read villages.csv and mandis.csv once and calculate the
    haversine distance times the configured road factor. A merged config can
    be passed by other engine callers so their overrides apply consistently.
    """
    origin_name = village.get("name") if isinstance(village, Mapping) else village
    if distances is not None:
        try:
            value = distances[origin_name][mandi]
        except (KeyError, TypeError) as error:
            raise ValueError(f"no distance data for {origin_name} to {mandi}") from error
        return _nonnegative(value, f"distance from {origin_name} to {mandi}")

    mandis = _optional_csv("mandis.csv", data_dir=data_dir)
    if isinstance(village, Mapping):
        origin = village
        if mandis is None:
            raise ValueError(f"no distance data for {origin_name}")
    else:
        villages = _optional_csv("villages.csv", data_dir=data_dir)
        if villages is None or mandis is None:
            raise ValueError(f"no distance data for {origin_name}")
        origin = next((row for row in villages if row["village"] == village), None)
    destination = next((row for row in mandis if row["mandi"] == mandi), None)
    if origin is None:
        raise ValueError(f"unknown village: {origin_name}")
    if destination is None:
        raise ValueError(f"unknown mandi: {mandi}")
    origin_coords = tuple(_number(origin[key], f"{origin_name} {key}") for key in ("lat", "lon"))
    mandi_coords = tuple(_number(destination[key], f"{mandi} {key}") for key in ("lat", "lon"))
    settings = _defaults() if config is None else config
    factor = _nonnegative(settings["transport"]["road_factor"], "transport.road_factor")
    return haversine(origin_coords, mandi_coords, unit=Unit.KILOMETERS) * factor


def _hold_limit(crop, lot_condition, config):
    limits = config["hold_limit_days"][crop]
    if lot_condition is None:
        value = limits["default"]
    elif isinstance(limits["answers"], list):
        answers = limits["answers"]
        if type(lot_condition) is not int or not 0 <= lot_condition < len(answers):
            raise ValueError(f"invalid lot_condition answer index for {crop}")
        value = answers[lot_condition]
    else:
        if type(lot_condition) is not bool or lot_condition not in limits["answers"]:
            raise ValueError(f"lot_condition for {crop} must be true or false")
        value = limits["answers"][lot_condition]
    return _days(value, f"hold limit for {crop}")


def _forecast_table(forecast, data_dir=None):
    if forecast is None:
        forecast = _optional_csv("forecast_table.csv", data_dir=data_dir)
        if forecast is None:
            raise ValueError("no forecast data; pass forecast or provide data/forecast_table.csv")
    if hasattr(forecast, "to_dict"):
        forecast = forecast.to_dict(orient="records")
    try:
        rows = list(forecast)
    except TypeError as error:
        raise ValueError("forecast must be a table of rows in the handoff schema") from error
    for row in rows:
        if not isinstance(row, Mapping) or any(key not in row for key in _FORECAST_COLUMNS):
            raise ValueError("forecast rows must contain every column in the handoff schema")
    return rows


def _forecast_rows(forecast, crop, as_of_date, data_dir=None):
    rows = _forecast_table(forecast, data_dir=data_dir)
    crop_rows = [row for row in rows if row["crop"] == crop]
    if not crop_rows:
        raise ValueError(f"no forecast data for {crop}")
    dates = {_date(row["as_of_date"], "as_of_date") for row in crop_rows}
    if as_of_date is None:
        if len(dates) != 1:
            raise ValueError("forecast has multiple as_of_date values; pass as_of_date")
        reference_date = next(iter(dates))
    else:
        reference_date = _date(as_of_date, "as_of_date")
    selected = [row for row in crop_rows if _date(row["as_of_date"], "as_of_date") == reference_date]
    if not selected:
        raise ValueError(f"no forecast data for {crop} on {reference_date}")
    return selected, reference_date


@dataclass(frozen=True)
class _Option:
    mandi: str
    day: int
    distance: float
    low: float
    mid: float
    high: float
    uses_baseline: bool
    flags: tuple[str, ...]
    sellable: float
    transport: float
    storage: float
    fees: float

    @property
    def net_low(self):
        return self.net_for_price(self.low)

    @property
    def net_mid(self):
        return self.net_for_price(self.mid)

    @property
    def net_high(self):
        return self.net_for_price(self.high)

    def net_for_price(self, price, *, transport=None):
        return _money_in_hand(
            price, self.sellable, self.transport if transport is None else transport,
            self.storage, self.fees,
        )

    def confidence(self, config):
        if self.uses_baseline or "stale" in self.flags:
            return "low"
        width = (self.high - self.low) / self.mid if self.mid else math.inf
        return "high" if width <= config["confidence"]["narrow_range_pct"] else "medium"

    def output(self):
        return {
            "mandi": self.mandi, "distance_km": self.distance, "sell_day": self.day,
            "price_low": round(self.low), "price_mid": round(self.mid), "price_high": round(self.high),
            "transport_per_qtl": round(self.transport), "net_low": round(self.net_low),
            "net_per_qtl": round(self.net_mid), "net_high": round(self.net_high), "flags": list(self.flags),
        }


def _option(row, distance, crop, config, reference_date):
    day = _days(row["horizon_days"], "horizon_days")
    low, mid, high = (_number(row[key], key) for key in ("price_low", "price_mid", "price_high"))
    if not low <= mid <= high:
        raise ValueError(f"unsorted forecast prices for {row['mandi']} at day {day}")
    if day == 0 and not low == mid == high:
        raise ValueError(f"horizon 0 prices must match for {row['mandi']}")
    last_report = _date(row["last_price_date"], "last_price_date")
    if last_report > reference_date:
        raise ValueError("last_price_date must not be after as_of_date")
    flags = []
    if (reference_date - last_report).days > config["confidence"]["stale_days"]:
        flags.append("stale")
    if _boolean(row["falling"], "falling"):
        flags.append("falling")
    return _Option(
        row["mandi"], day, distance, low, mid, high, _boolean(row["uses_baseline"], "uses_baseline"),
        tuple(flags), *_costs(crop, day, distance, config),
    )


def _costs(crop, day, distance, config):
    """Shared sellable weight and costs for Advice, FPO and the backtest."""
    spoilage = _nonnegative(config["spoilage_per_day"][crop], f"spoilage_per_day.{crop}")
    if spoilage >= 1:
        raise ValueError(f"spoilage_per_day.{crop} must be less than one")
    transport = config["transport"]
    rate = _nonnegative(transport["rate_per_km_per_qtl"], "transport.rate_per_km_per_qtl")
    loading = _nonnegative(transport["loading_per_qtl"], "transport.loading_per_qtl")
    storage = _nonnegative(config["storage_cost_per_qtl_per_day"][crop], f"storage cost for {crop}")
    fees = _nonnegative(config["fees_per_qtl"], "fees_per_qtl")
    return (1 - spoilage) ** day, distance * rate + loading, storage * day, fees


def _money_in_hand(price, sellable, transport, storage, fees):
    return price * sellable - transport - storage - fees


def _options(crop, origin, lot_condition, cash_needed_in_days, blocked_mandis,
             config, as_of_date, forecast, data_dir=None, distances=None,
             transport_for_distance=None):
    """Build unrounded options once using the shared eligibility/cost rules.

    A transport callback changes only the transport cost, allowing FPO to
    rank full-truck options while keeping price, spoilage and storage shared.
    Failed self-check rows remain here for Advice's reliability note.
    """
    if crop not in config["spoilage_per_day"]:
        raise ValueError(f"unknown crop: {crop}")
    hold_limit = _hold_limit(crop, lot_condition, config)
    allowed_days = {0, *(_days(day, "horizons") for day in config["horizons"])}
    allowed_days = {day for day in allowed_days if day <= hold_limit}
    if cash_needed_in_days is not None:
        deadline = _days(cash_needed_in_days, "cash_needed_in_days")
        allowed_days = {day for day in allowed_days if day <= deadline}
    rows, reference_date = _forecast_rows(forecast, crop, as_of_date, data_dir=data_dir)
    metadata = _optional_csv("mandis.csv", data_dir=data_dir)
    tradable = (
        {row["mandi"] for row in metadata if crop in row["crops"].split("|")}
        if metadata is not None else {row["mandi"] for row in rows}
    )
    mandis = tradable - set(blocked_mandis)
    if not mandis:
        raise ValueError(f"no tradable, unblocked mandis for {crop}")
    road_distances = {
        mandi: road_distance_km(origin, mandi, config=config, data_dir=data_dir, distances=distances)
        for mandi in sorted(mandis)
    }
    candidates, seen = [], set()
    for row in rows:
        day = _days(row["horizon_days"], "horizon_days")
        if row["mandi"] not in mandis or day not in allowed_days:
            continue
        key = (row["mandi"], day)
        if key in seen:
            raise ValueError(f"duplicate forecast for {key[0]} at day {day}")
        seen.add(key)
        distance = road_distances[row["mandi"]]
        option = _option(row, distance, crop, config, reference_date)
        if transport_for_distance is not None:
            transport = _nonnegative(transport_for_distance(distance), "transport per quintal")
            option = replace(option, transport=transport)
        candidates.append(option)
    for mandi in sorted(mandis):
        if (mandi, 0) not in seen:
            raise ValueError(f"missing horizon 0 forecast for {crop} at {mandi} on {reference_date}")
    return candidates, hold_limit, reference_date


def _ranked_options(candidates):
    return sorted(
        (option for option in candidates if option.day == 0 or not option.uses_baseline),
        key=lambda option: option.net_mid, reverse=True,
    )


@cache
def _read_backtest(path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _hold_success_rate(crop, data_dir=None):
    path = _data_dir(data_dir) / "backtest.json"
    if not path.is_file():
        return None
    return _read_backtest(path).get(crop, {}).get("hold_success_rate")


def _hold_record_text(record):
    counts = record.get("hold_record", {})
    won = _days(counts.get("won", 0), "hold_record.won")
    lost = _days(counts.get("lost", 0), "hold_record.lost")
    return f"won {won} of {won + lost}"


def _suppressed_hold_record(crop, config, data_dir=None):
    """Shared crop-level gate; a missing backtest file leaves holds enabled."""
    path = _data_dir(data_dir) / "backtest.json"
    if not path.is_file():
        return None
    record = _read_backtest(path).get(crop, {})
    counts = record.get("hold_record", {})
    scored = _days(counts.get("won", 0), "hold_record.won") + _days(counts.get("lost", 0), "hold_record.lost")
    gate = config["hold_gate"]
    minimum = _days(gate["min_scored_holds"], "hold_gate.min_scored_holds")
    if scored < minimum:
        return record
    success = _number(record.get("hold_success_rate"), "hold_success_rate")
    minimum_success = _nonnegative(gate["min_success_rate"], "hold_gate.min_success_rate")
    holding_gain = _number(record.get("gain_split", {}).get("from_holding"), "gain_split.from_holding")
    return record if success < minimum_success or holding_gain <= 0 else None


def advise(crop, quantity_qtl, village, lot_condition=None, cash_needed_in_days=None,
           blocked_mandis=(), overrides=None, as_of_date=None, forecast=None, *, data_dir=None, apply_hold_gate=True, distances=None) -> dict:
    """Return the section 7 response, without Backend's message/storage_tip.

    ``distances`` is an optional {village: {mandi: road_km}} matrix; it never
    receives a road-factor multiplier. With no matrix, coordinate handoff
    files are required. Forecast crop/mandi pairs supply crop eligibility
    only while mandis.csv is absent. ``data_dir`` isolates fixture inputs and
    defaults to the repository's data folder. All monetary calculations are per
    harvested quintal, and rounding happens only when building the result.
    The measured-record gate can suppress a hold; apply_hold_gate=False
    preserves the original decision rule for backtest measurement.
    """
    config = _config(overrides)
    if crop not in config["spoilage_per_day"]:
        raise ValueError(f"unknown crop: {crop}")
    if _number(quantity_qtl, "quantity_qtl") <= 0:
        raise ValueError("quantity_qtl must be positive")
    candidates, hold_limit, reference_date = _options(
        crop, village, lot_condition, cash_needed_in_days, blocked_mandis,
        config, as_of_date, forecast, data_dir=data_dir, distances=distances,
    )
    today = [option for option in candidates if option.day == 0]
    baseline_today = min(today, key=lambda option: (option.distance, option.mandi))
    best_today = max(today, key=lambda option: option.net_mid)
    hold_candidates = [option for option in candidates if option.day > 0]
    holds = sorted(
        (option for option in hold_candidates if not option.uses_baseline),
        key=lambda option: option.net_mid, reverse=True,
    )
    min_gain = _nonnegative(config["hold_rule"]["min_gain_per_qtl"], "hold_rule.min_gain_per_qtl")
    max_downside = _nonnegative(config["hold_rule"]["max_downside_per_qtl"], "hold_rule.max_downside_per_qtl")
    chosen = next(
        (option for option in holds if option.net_mid - best_today.net_mid >= min_gain
         and best_today.net_mid - option.net_low <= max_downside),
        best_today,
    )
    holding = chosen.day > 0
    confidence_option = chosen if holding else (holds[0] if holds else None)
    notes = [_UNRELIABLE_NOTE] if hold_candidates and not holds else []
    hold_suppressed = False
    if holding and apply_hold_gate:
        record = _suppressed_hold_record(crop, config, data_dir=data_dir)
        if record is not None:
            extra = round(chosen.net_mid - best_today.net_mid)
            notes.append(f"Hold suppressed: {chosen.day} days at {chosen.mandi}, expected extra Rs {extra} per qtl; {_hold_record_text(record)}.")
            chosen = best_today
            holding = False
            hold_suppressed = True
    break_even = (
        (best_today.net_mid + chosen.transport + chosen.storage + chosen.fees) / chosen.sellable
        if holding else None
    )
    allowed = _ranked_options(candidates)
    return {
        "action": "hold" if holding else "sell_now", "days": chosen.day, "mandi": chosen.mandi,
        "net_per_qtl": round(chosen.net_mid), "net_low": round(chosen.net_low), "net_high": round(chosen.net_high),
        "baseline_today": {"mandi": baseline_today.mandi, "net": round(baseline_today.net_mid)},
        "best_today": {"mandi": best_today.mandi, "net": round(best_today.net_mid)},
        "gain_vs_baseline": round(chosen.net_mid - baseline_today.net_mid),
        "gain_from_mandi": round(best_today.net_mid - baseline_today.net_mid),
        "gain_from_waiting": round(chosen.net_mid - best_today.net_mid) if holding else 0,
        "confidence": confidence_option.confidence(config) if confidence_option else "low",
        "break_even_price": round(break_even) if break_even is not None else None,
        "hold_limit_days": hold_limit, "hold_success_rate": _hold_success_rate(crop, data_dir=data_dir),
        "prices_as_of": reference_date.isoformat(), "uses_baseline": chosen.uses_baseline,
        "assumptions_default": not bool(overrides),
        "why": {
            "price": round(chosen.mid), "spoilage_loss": round(chosen.mid * (1 - chosen.sellable)),
            "transport": round(chosen.transport), "storage": round(chosen.storage), "fees": round(chosen.fees),
        },
        "options": [option.output() for option in allowed], "notes": notes,
        "hold_suppressed": hold_suppressed,
    }


def fpo_plan(lots, blocked_mandis=(), mandi_cap_qtl_per_day=None,
             collection_centre=None, overrides=None, *, as_of_date=None,
             forecast=None, data_dir=None, distances=None) -> dict:
    """Rule-based FPO allocation; fixture arguments leave Backend calls intact."""
    if __package__:
        from .fpo import fpo_plan as build_plan
    else:
        from fpo import fpo_plan as build_plan
    return build_plan(
        lots, blocked_mandis=blocked_mandis, mandi_cap_qtl_per_day=mandi_cap_qtl_per_day,
        collection_centre=collection_centre, overrides=overrides,
        as_of_date=as_of_date, forecast=forecast, data_dir=data_dir, distances=distances,
    )
