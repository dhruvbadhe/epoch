"""GET /market/snapshot: yesterday's reported mandi prices for one crop (the Info tab).

Reported prices only (data/prices_mh.csv), never forecasts. "Yesterday" is the latest reported date before
the as-of date in data/splits.json. With a village, road distance and money in hand per quintal come from
the engine's own functions (ml/engine/api.py), selling on the day of the snapshot.
"""
from __future__ import annotations

from datetime import date, timedelta

from . import data_loader, engine_api

SERIES_DAYS = 7


def _prices(crop: str) -> list[dict]:
    rows = data_loader._load(data_loader.DATA / "prices_mh.csv", data_loader._read_csv) or []
    return [r for r in rows if r.get("crop", "").lower() == crop]


def _num(value):
    n = data_loader._num(value)
    return None if n is None else (int(n) if float(n).is_integer() else n)


def snapshot(crop: str, village: dict | None = None) -> dict:
    as_of = data_loader.as_of_date()
    rows = [r for r in _prices(crop) if r["date"][:10] < as_of]            # nothing on or after the as-of date
    mandis = [m for m in data_loader.mandis() if crop in m["crops"]]
    districts = {m["mandi"]: m.get("district") for m in data_loader._load(
        data_loader.DATA / "mandis.csv", data_loader._read_csv) or []}
    by_mandi: dict[str, dict[str, dict]] = {}
    for r in rows:
        by_mandi.setdefault(r["mandi"], {})[r["date"][:10]] = r
    snapshot_date = max((r["date"][:10] for r in rows), default=None)

    reporting, not_reporting = [], []
    for m in mandis:
        days = by_mandi.get(m["mandi"], {})
        today = days.get(snapshot_date)
        if today is None:
            not_reporting.append({"mandi": m["mandi"], "last_reported_date": max(days, default=None)})
            continue
        earlier = [d for d in days if d < snapshot_date]
        previous = days[max(earlier)] if earlier else None
        modal = _num(today["modal_price"])
        prev_modal = _num(previous["modal_price"]) if previous else None
        reporting.append({
            "mandi": m["mandi"], "district": districts.get(m["mandi"]) or today.get("district"),
            "modal_price": modal, "min_price": _num(today["min_price"]), "max_price": _num(today["max_price"]),
            "previous_date": max(earlier) if earlier else None, "previous_modal_price": prev_modal,
            "change": None if prev_modal is None else modal - prev_modal})
    reporting.sort(key=lambda r: -r["modal_price"])

    highest = reporting[0] if reporting else None
    lowest = reporting[-1] if reporting else None
    dates = ([(date.fromisoformat(snapshot_date) - timedelta(days=i)).isoformat()
              for i in range(SERIES_DAYS - 1, -1, -1)] if snapshot_date else [])
    series = [{"mandi": m["mandi"],
               "points": [{"date": d, "modal_price": _num(by_mandi.get(m["mandi"], {}).get(d, {}).get("modal_price"))}
                          for d in dates]} for m in mandis]

    result = {
        "crop": crop, "prices_as_of": as_of, "snapshot_date": snapshot_date,
        "basis": "Reported mandi prices only (no forecasts). Gross price per quintal.",
        "reporting": reporting,
        "highest_price": {"mandi": highest["mandi"], "modal_price": highest["modal_price"]} if highest else None,
        "lowest_price": {"mandi": lowest["mandi"], "modal_price": lowest["modal_price"]} if lowest else None,
        "spread": highest["modal_price"] - lowest["modal_price"] if highest else None,
        "not_reporting": not_reporting, "series_dates": dates, "series_7d": series,
        "village": None, "money_in_hand": None,
    }
    if village and reporting:
        result["village"] = village["village"]
        result["money_in_hand"] = _money_in_hand(crop, village["village"], reporting)
    return result


def _money_in_hand(crop: str, village: str, reporting: list[dict]) -> dict:
    """Road km and net per quintal from the engine's own distance and cost functions (sell on day 0)."""
    engine = engine_api._load_module()
    config = engine._config(None)
    rows = []
    for r in reporting:
        km = engine.road_distance_km(village, r["mandi"], config=config)
        sellable, transport, storage, fees = engine._costs(crop, 0, km, config)
        net = engine._money_in_hand(r["modal_price"], sellable, transport, storage, fees)
        rows.append({"mandi": r["mandi"], "road_km": round(km, 1), "modal_price": r["modal_price"],
                     "transport_per_qtl": round(transport), "net_per_qtl": round(net)})
    rows.sort(key=lambda x: -x["net_per_qtl"])
    return {"label": f"highest money in hand from {village}", "rows": rows,
            "highest": {"mandi": rows[0]["mandi"], "net_per_qtl": rows[0]["net_per_qtl"]},
            "assumptions": "default transport, storage and spoilage from config.yaml (assumptions)"}
