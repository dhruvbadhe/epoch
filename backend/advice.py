"""The one path to advice, used by both POST /advise and the WhatsApp conversation.

Because both go through get_advice(), the same inputs give the same numbers on both screens.
"""
from __future__ import annotations

from . import data_loader, engine_api, replies, tips
from .errors import ApiError


# ---------- input checks (shared by /advise and /fpo/plan) -----------------

def resolve_village(name, field: str = "village") -> dict:
    village = data_loader.find_village(name) if isinstance(name, str) else None
    if village is None:
        raise ApiError(f"Unknown village '{name}'. Use a name from GET /villages", field)
    return village


def check_lot_condition(crop: str, lot_condition, field: str = "lot_condition"):
    """tomato: answer index; onion, soybean: true | false; null = not asked."""
    if lot_condition is None:
        return None
    answers = data_loader.cfg("hold_limit_days", crop, "answers")
    if isinstance(answers, list):
        valid = isinstance(lot_condition, int) and not isinstance(lot_condition, bool) \
            and 0 <= lot_condition < len(answers)
        if not valid:
            indexes = ", ".join(str(i) for i in range(len(answers)))
            raise ApiError(f"lot_condition for {crop} must be one of {indexes}, or null", field)
    elif not isinstance(lot_condition, bool):
        raise ApiError(f"lot_condition for {crop} must be true or false, or null", field)
    return lot_condition


def check_blocked(blocked, field: str = "blocked_mandis") -> list[str]:
    names = []
    for name in blocked or []:
        mandi = data_loader.find_mandi(name)
        if mandi is None:
            raise ApiError(f"Unknown mandi '{name}'. Use a name from GET /mandis", field)
        names.append(mandi["mandi"])
    return names


# ---------- advice --------------------------------------------------------

def _backtest_hold_rate(crop: str):
    data = data_loader.backtest()
    entry = data.get(crop) if isinstance(data, dict) else None
    return entry.get("hold_success_rate") if isinstance(entry, dict) else None


def get_advice(crop: str, quantity_qtl: float, village: str, lot_condition=None,
               cash_needed_in_days: int | None = None, blocked_mandis: list[str] | None = None,
               overrides: dict | None = None, lang: str = "mr", as_of_date: str | None = None) -> dict:
    """The engine's advice plus storage_tip (hold only) and the formatted message."""
    result = dict(engine_api.advise(
        crop=crop, quantity_qtl=quantity_qtl, village=village, lot_condition=lot_condition,
        cash_needed_in_days=cash_needed_in_days, blocked_mandis=blocked_mandis, overrides=overrides,
        as_of_date=as_of_date))
    if result.get("hold_success_rate") is None:
        result["hold_success_rate"] = _backtest_hold_rate(crop)
    result["storage_tip"] = tips.storage_tip(crop, lang) if result.get("action") == "hold" else None
    result["message"] = replies.advice_message(result, lang, result["storage_tip"],
                                               example_data=engine_api.using_fake("advise"))
    return result


@data_loader.with_example_data
def _selftest():
    import os

    os.environ["ENGINE_MODE"] = "fake"
    assert resolve_village("niphad")["village"] == "Niphad" == resolve_village("निफाड")["village"]
    for bad in ("Atlantis", None, 7):
        try:
            resolve_village(bad)
            raise AssertionError("expected ApiError")
        except ApiError as exc:
            assert exc.field == "village" and exc.status == 400
    assert check_lot_condition("tomato", 2) == 2 and check_lot_condition("onion", False) is False
    for crop, bad in (("tomato", True), ("tomato", 3), ("onion", 1), ("soybean", "yes")):
        try:
            check_lot_condition(crop, bad)
            raise AssertionError(f"expected ApiError for {crop} {bad!r}")
        except ApiError as exc:
            assert exc.field == "lot_condition"
    assert check_blocked(["lasalgaon"]) == ["Lasalgaon"]

    hold = get_advice("onion", 10, "Niphad", lang="mr")
    assert hold["action"] == "hold" and hold["storage_tip"] == tips.storage_tip("onion", "mr")
    assert hold["message"].startswith("🟢 *14 दिवस थांबा → पिंपळगाव*")
    sell = get_advice("onion", 10, "Niphad", cash_needed_in_days=3, lang="hi")
    assert sell["storage_tip"] is None and sell["message"].startswith("🔴 *आज ही बेचें → पिंपळगाव*")
    del os.environ["ENGINE_MODE"]
    print("advice ok")


if __name__ == "__main__":
    _selftest()
