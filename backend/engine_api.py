"""Bridge to ML 2's engine (ml/engine/api.py): advise() and fpo_plan().

Until a function exists there, its answer comes from the example JSON in backend/fake, adjusted
just enough that the hold limit, cash deadline and blocked mandis can be exercised end to end.

ENGINE_MODE in .env: auto (default) = real when available, else fake; real = never fall back
(use this for the demo); fake = always the example JSON.
"""
from __future__ import annotations

import importlib
import inspect
import logging
import os
import sys

from . import data_loader

log = logging.getLogger("sellsmart.engine")

FAKE_NOTE = "Example data: the decision engine is not connected yet"

_module = None
_import_error: str | None = None
_tried = False


class EngineUnavailable(Exception):
    """The real engine is required (ENGINE_MODE=real) or was called, and can't be used."""


def _mode() -> str:
    return os.getenv("ENGINE_MODE", "auto").strip().lower()


def _load_module():
    global _module, _import_error, _tried
    if not _tried:
        _tried = True
        if str(data_loader.ROOT) not in sys.path:
            sys.path.insert(0, str(data_loader.ROOT))
        try:
            _module = importlib.import_module("ml.engine.api")
        except ModuleNotFoundError as exc:
            _import_error = f"{type(exc).__name__}: {exc}"
            log.warning("ml.engine.api not found (%s); serving example data", exc)
        except Exception as exc:                     # the engine exists but is broken
            _import_error = f"{type(exc).__name__}: {exc}"
            log.exception("ml.engine.api failed to import; serving example data")
    return _module


def _real(name: str):
    """The engine's function, or None when the fake should answer."""
    mode = _mode()
    if mode == "fake":
        return None
    fn = getattr(_load_module(), name, None)
    if callable(fn):
        return fn
    if mode == "real":
        raise EngineUnavailable(f"ml.engine.api.{name}() is not available"
                                + (f" ({_import_error})" if _import_error else ""))
    return None


def using_fake(name: str = "advise") -> bool:
    try:
        return _real(name) is None
    except EngineUnavailable:
        return False


def status() -> dict:
    def one(name):
        try:
            return "fake" if _real(name) is None else "real"
        except EngineUnavailable:
            return "unavailable"

    return {"mode": _mode(), "advise": one("advise"), "fpo_plan": one("fpo_plan"),
            "import_error": _import_error}


def _call(fn, kwargs: dict):
    """Call an engine function with the arguments it declares.

    Accepts fn(**kwargs), fn(request_dict), or a named-argument signature. An argument that
    carries a real value but that the engine doesn't take is a contract mismatch: fail loudly
    instead of quietly giving advice that ignores it.
    """
    params = inspect.signature(fn).parameters
    if any(p.kind is p.VAR_KEYWORD for p in params.values()):
        return fn(**kwargs)
    if len(params) == 1 and next(iter(params)) not in kwargs:
        return fn(dict(kwargs))
    ignored = [k for k, v in kwargs.items() if k not in params and v not in (None, [], {})]
    if ignored:
        raise EngineUnavailable(f"ml.engine.api.{fn.__name__}() does not accept {', '.join(ignored)}; "
                                "its arguments must match docs/api_contract.md")
    return fn(**{k: v for k, v in kwargs.items() if k in params})


# ---------- advise --------------------------------------------------------

def advise(crop: str, quantity_qtl: float, village: str, lot_condition=None,
           cash_needed_in_days: int | None = None, blocked_mandis: list[str] | None = None,
           overrides: dict | None = None) -> dict:
    """The engine's answer in the /advise response shape, without storage_tip and message."""
    kwargs = {"crop": crop, "quantity_qtl": quantity_qtl, "village": village,
              "lot_condition": lot_condition, "cash_needed_in_days": cash_needed_in_days,
              "blocked_mandis": list(blocked_mandis or []), "overrides": overrides or None}
    fn = _real("advise")
    return _call(fn, kwargs) if fn else _fake_advise(**kwargs)


def _fake_advise(crop, quantity_qtl, village, lot_condition, cash_needed_in_days,
                 blocked_mandis, overrides) -> dict:
    result = data_loader.fake("advise.json")
    blocked = {m.lower() for m in blocked_mandis}
    limit = data_loader.hold_limit_days(crop, lot_condition)
    last_day = limit if cash_needed_in_days is None else min(limit, cash_needed_in_days)
    options = [o for o in result["options"]
               if o["mandi"].lower() not in blocked and o["sell_day"] <= last_day]
    today = [o for o in options if o["sell_day"] == 0]
    if not today:
        raise ValueError("No mandi is available for this crop")

    baseline = min(today, key=lambda o: o["distance_km"])
    best = max(today, key=lambda o: o["net_per_qtl"])
    result.update(
        options=options, hold_limit_days=limit, assumptions_default=not overrides,
        baseline_today={"mandi": baseline["mandi"], "net": baseline["net_per_qtl"]},
        best_today={"mandi": best["mandi"], "net": best["net_per_qtl"]},
        gain_from_mandi=best["net_per_qtl"] - baseline["net_per_qtl"],
        notes=[FAKE_NOTE])
    if not any(o["sell_day"] > 0 for o in options):          # the example hold isn't allowed
        result.update(
            action="sell_now", days=0, mandi=best["mandi"], net_per_qtl=best["net_per_qtl"],
            net_low=best["net_low"], net_high=best["net_high"],
            gain_vs_baseline=best["net_per_qtl"] - baseline["net_per_qtl"], gain_from_waiting=0,
            break_even_price=None,
            why={"price": best["price_mid"], "spoilage_loss": 0,
                 "transport": best["transport_per_qtl"], "storage": 0, "fees": 0})
    return result


# ---------- FPO plan ------------------------------------------------------

def fpo_plan(lots: list[dict], blocked_mandis: list[str] | None = None,
             mandi_cap_qtl_per_day: float | None = None, collection_centre: dict | None = None,
             overrides: dict | None = None) -> dict:
    kwargs = {"lots": lots, "blocked_mandis": list(blocked_mandis or []),
              "mandi_cap_qtl_per_day": mandi_cap_qtl_per_day,
              "collection_centre": collection_centre, "overrides": overrides or None}
    fn = _real("fpo_plan")
    if fn:
        return _call(fn, kwargs)
    result = data_loader.fake("fpo_plan.json")
    result["assumptions_default"] = not overrides
    return result


@data_loader.with_example_data
def _selftest():
    os.environ["ENGINE_MODE"] = "fake"
    hold = advise("onion", 10, "Niphad")
    assert hold == {**data_loader.fake("advise.json"), "notes": [FAKE_NOTE]}, "must equal the contract example"
    assert advise("onion", 10, "Niphad", overrides={"fees_per_qtl": 5})["assumptions_default"] is False

    sell = advise("onion", 10, "Niphad", cash_needed_in_days=3)
    assert (sell["action"], sell["days"], sell["mandi"], sell["net_per_qtl"]) == ("sell_now", 0, "Pimpalgaon", 1700)
    assert sell["gain_vs_baseline"] == 40 == sell["gain_from_mandi"] and sell["gain_from_waiting"] == 0
    assert sell["break_even_price"] is None and all(o["sell_day"] == 0 for o in sell["options"])
    assert advise("onion", 10, "Niphad", lot_condition=False)["hold_limit_days"] == 5
    assert advise("tomato", 10, "Niphad")["action"] == "sell_now"        # default tomato limit is 4 days

    rerouted = advise("onion", 10, "Niphad", blocked_mandis=["pimpalgaon"])
    assert (rerouted["mandi"], rerouted["gain_vs_baseline"]) == ("Lasalgaon", 0)
    try:
        advise("onion", 10, "Niphad", blocked_mandis=["Pimpalgaon", "Lasalgaon"])
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
    assert fpo_plan([{"member": "A"}])["assignments"][0]["member"] == "A"

    # how the real engine gets called, whatever its signature style
    seen = {}
    def named(crop, quantity_qtl, village, lot_condition=None, cash_needed_in_days=None,
              blocked_mandis=None, overrides=None):
        seen.update(locals())
    args = {"crop": "onion", "quantity_qtl": 5, "village": "Niphad", "lot_condition": True,
            "cash_needed_in_days": 3, "blocked_mandis": [], "overrides": None}
    _call(named, args)
    assert seen["cash_needed_in_days"] == 3 and seen["lot_condition"] is True
    assert _call(lambda request: request, args) == args and _call(lambda **kw: kw, args) == args
    try:
        _call(lambda crop, quantity_qtl, village: None, args)
        raise AssertionError("expected EngineUnavailable")
    except EngineUnavailable as exc:
        assert "lot_condition" in str(exc)
    del os.environ["ENGINE_MODE"]
    print("engine_api ok:", status())


if __name__ == "__main__":
    _selftest()
