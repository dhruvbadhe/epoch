"""Read-only views for GET /forecast, /backtest, /mandis, /villages and /config."""
from __future__ import annotations

from datetime import date, timedelta

from . import data_loader
from .errors import ApiError

HISTORY_DAYS = 60     # default span of past prices returned with a forecast


def check_crop(crop, field: str = "crop") -> str:
    if crop not in data_loader.CROPS:
        raise ApiError(f"crop must be one of {', '.join(data_loader.CROPS)}", field)
    return crop


# ---------- GET /forecast -------------------------------------------------

def forecast_view(crop: str, mandi: str, days: int = HISTORY_DAYS) -> dict:
    check_crop(crop)
    table = data_loader.forecast_table()
    if table is None:                                  # ML 1 hasn't shipped the table yet
        known = data_loader.find_mandi(mandi)
        if known is None:
            raise ApiError(f"Unknown mandi '{mandi}'. Use a name from GET /mandis", "mandi")
        return {**data_loader.fake("forecast.json"), "crop": crop, "mandi": known["mandi"]}

    rows = table.get((crop, str(mandi).strip().lower()))
    if not rows:
        raise ApiError(f"No forecast for {crop} at '{mandi}'", "mandi")
    as_of = rows[0]["as_of_date"]
    start = date.fromisoformat(as_of)
    return {
        "crop": crop, "mandi": rows[0]["mandi"], "prices_as_of": as_of,
        "history": data_loader.price_history(crop, rows[0]["mandi"], as_of, days),
        "forecast": [{"horizon_days": r["horizon_days"],
                      "date": (start + timedelta(days=r["horizon_days"])).isoformat(),
                      "price_low": r["price_low"], "price_mid": r["price_mid"],
                      "price_high": r["price_high"], "uses_baseline": r["uses_baseline"]}
                     for r in rows if r["horizon_days"] > 0],   # the 0 row is today's price, already in history
    }


# ---------- GET /backtest -------------------------------------------------

def _not_evaluated(crop: str) -> dict:
    """The backtest shape for a crop that hasn't been run: counts are 0, every metric is null."""
    shape = data_loader.fake("backtest.json")
    shape.update(crop=crop, test_period={"start": None, "end": None},
                 cases_excluded_by_reason={}, coverage=[], selfcheck=[])
    return shape


def _selfcheck_rows(crop: str) -> list[dict]:
    return [{"mandi": r.get("mandi"), "horizon_days": int(float(r["horizon_days"])),
             "ratio": data_loader._num(r.get("ratio")),
             "rows": int(data_loader._num(r.get("rows")) or 0),
             "passed": data_loader._bool(r.get("passed"))}
            for r in data_loader.selfcheck() or [] if r.get("crop", "").lower() == crop]


def _coverage_rows(crop: str) -> list[dict]:
    return [{"horizon_days": int(float(r["horizon_days"])),
             "coverage": data_loader._num(r.get("coverage")),
             "n": int(data_loader._num(r.get("n")) or 0)}
            for r in data_loader.coverage() or [] if r.get("crop", "").lower() == crop]


def backtest_view(crop: str) -> dict:
    check_crop(crop)
    data = data_loader.backtest()
    if data is None:                                   # ML 2 hasn't shipped backtest.json yet
        result = {**data_loader.fake("backtest.json"), "crop": crop}
        if data_loader.selfcheck() is None and data_loader.coverage() is None:
            return result
        result.update(coverage=[], selfcheck=[])       # real tables exist: don't mix in example rows
    else:
        entry = None
        if isinstance(data, dict):
            entry = data.get(crop) or (data if data.get("crop") == crop else None)
        elif isinstance(data, list):
            entry = next((e for e in data if isinstance(e, dict) and e.get("crop") == crop), None)
        result = {**_not_evaluated(crop), **entry} if isinstance(entry, dict) else _not_evaluated(crop)
    # ML 1's tables fill the two evidence lists if the backtest file doesn't carry them
    if not result.get("selfcheck"):
        result["selfcheck"] = _selfcheck_rows(crop)
    if not result.get("coverage"):
        result["coverage"] = _coverage_rows(crop)
    return result


# ---------- GET /mandis, /villages, /config -------------------------------

def mandis_view(crop: str | None = None) -> list[dict]:
    if crop is not None:
        check_crop(crop)
    return [m for m in data_loader.mandis() if crop is None or crop in m["crops"]]


def villages_view() -> list[dict]:
    return data_loader.villages()


def _json_keys(node):
    """YAML allows true/false as keys (hold_limit_days answers); JSON keys must be strings."""
    if isinstance(node, dict):
        return {(str(k).lower() if isinstance(k, bool) else str(k)): _json_keys(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_json_keys(v) for v in node]
    return node


def config_view() -> dict:
    return _json_keys(data_loader.config())


@data_loader.with_example_data
def _selftest():
    assert config_view()["hold_limit_days"]["onion"]["answers"] == {"true": 21, "false": 5}
    assert [m["mandi"] for m in mandis_view("tomato")] == ["Pimpalgaon"]
    assert len(villages_view()) >= 20
    for call in (lambda: backtest_view("wheat"), lambda: mandis_view("wheat"),
                 lambda: forecast_view("onion", "Atlantis")):
        try:
            call()
            raise AssertionError("expected ApiError")
        except ApiError as exc:
            assert exc.field in ("crop", "mandi")
    bt = backtest_view("tomato")
    assert bt["crop"] == "tomato" and bt["avg_gain_per_qtl"] is None
    assert [step["policy"] for step in bt["ladder"]] == ["nearest_today", "highest_price_today",
                                                         "best_net_today", "full_advice"]
    empty = _not_evaluated("soybean")
    assert empty["hold_success_rate"] is None and empty["cases_tested"] == 0 and empty["selfcheck"] == []
    print("lookups ok")


if __name__ == "__main__":
    _selftest()
