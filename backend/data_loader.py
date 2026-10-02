"""Loads config.yaml and the handoff files under data/.

Every file is parsed once and cached; it is re-read only when it changes on disk, so ML 1 or
ML 2 can replace a file without the server restarting (a restart loses conversation memory).
Files that don't exist yet fall back to backend/fake where a fake exists, else to None.
"""
from __future__ import annotations

import contextlib
import csv
import functools
import json
import logging
import shutil
import tempfile
from datetime import date, timedelta
from pathlib import Path

import yaml

log = logging.getLogger("sellsmart.data")

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CONFIG = ROOT / "config.yaml"
FAKE = Path(__file__).resolve().parent / "fake"

CROPS = ("onion", "tomato", "soybean")

# Every config.yaml key the backend itself reads (the engine reads the rest).
CONFIG_KEYS = [("hold_limit_days", crop) for crop in CROPS] + [
    ("units", "bag_kg"), ("units", "crate_kg"), ("parser", "village_match_threshold"), ("horizons",)]

_cache: dict[Path, tuple[float, object]] = {}


def _load(path: Path, parse):
    """Parsed contents of path, or None if it doesn't exist. Keeps the last good copy if a re-read fails."""
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return None
    hit = _cache.get(path)
    if hit and hit[0] == mtime:
        return hit[1]
    try:
        value = parse(path)
    except Exception as exc:  # half-written or malformed file
        log.error("could not read %s: %s", path, exc)
        if hit:
            return hit[1]
        raise
    _cache[path] = (mtime, value)
    return value


# ---------- small parsers -------------------------------------------------

def _read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [{k.strip(): (v or "").strip() for k, v in row.items() if isinstance(k, str)}
                for row in csv.DictReader(f)]


def _read_json(path: Path):
    with path.open(encoding="utf-8-sig") as f:
        return json.load(f)


def _read_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8-sig") as f:
        return yaml.safe_load(f) or {}


def _num(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _bool(value) -> bool:
    return str(value).strip().lower() in ("true", "1", "yes", "y", "t")


def _day(value) -> str:
    """'2026-08-31 00:00:00' -> '2026-08-31'. Raises ValueError if it isn't an ISO date."""
    text = str(value).strip()[:10]
    date.fromisoformat(text)
    return text


def rupees(value) -> int | None:
    number = _num(value)
    return None if number is None else round(number)


# ---------- config --------------------------------------------------------

def config() -> dict:
    return _load(CONFIG if CONFIG.is_file() else FAKE / "config.yaml", _read_yaml)


def _lookup(source, keys) -> tuple[bool, object]:
    node = source
    for key in keys:
        if not isinstance(node, dict) or key not in node:
            return False, None
        node = node[key]
    return True, node


def cfg(*keys):
    """config value at a nested key; falls back to the contract copy if config.yaml lacks the key."""
    for source in (config(), _load(FAKE / "config.yaml", _read_yaml)):
        found, value = _lookup(source, keys)
        if found:
            return value
    raise KeyError("config.yaml has no " + ".".join(map(str, keys)))


def config_missing_keys() -> list[str]:
    """Keys the backend needs that config.yaml doesn't have (the contract copy is used for them)."""
    return [".".join(keys) for keys in CONFIG_KEYS if not _lookup(config(), keys)[0]]


def hold_limit_days(crop: str, lot_condition) -> int:
    """This lot's hold limit: the freshness answer if given, else the crop default."""
    spec = cfg("hold_limit_days", crop)
    if lot_condition is None:
        return spec["default"]
    answers = spec["answers"]
    if isinstance(answers, list):
        return answers[int(lot_condition)]
    key = bool(lot_condition)
    return answers[key] if key in answers else answers[str(key).lower()]


# ---------- villages and mandis -------------------------------------------

def _parse_villages(path: Path) -> list[dict]:
    rows = []
    for r in _read_csv(path):
        if not r.get("village"):
            continue
        rows.append({"village": r["village"],
                     "name_mr": r.get("name_mr") or r["village"],
                     "name_hi": r.get("name_hi") or r.get("name_mr") or r["village"],
                     "lat": _num(r.get("lat")), "lon": _num(r.get("lon"))})
    return rows


def villages() -> list[dict]:
    return _load(DATA / "villages.csv", _parse_villages) or []


def find_village(name: str) -> dict | None:
    """Exact (case-insensitive) match on any of the three spellings."""
    wanted = str(name).strip().lower()
    for v in villages():
        if wanted in (v["village"].lower(), v["name_mr"], v["name_hi"]):
            return v
    return None


def _parse_mandis(path: Path) -> list[dict]:
    rows = []
    for r in _read_csv(path):
        if not r.get("mandi"):
            continue
        crops = [c.strip().lower() for c in r.get("crops", "").split("|") if c.strip()]
        rows.append({"mandi": r["mandi"], "lat": _num(r.get("lat")), "lon": _num(r.get("lon")),
                     "crops": crops})
    return rows


def mandis() -> list[dict]:
    real = _load(DATA / "mandis.csv", _parse_mandis)
    return real if real is not None else _load(FAKE / "mandis.json", _read_json)


def find_mandi(name: str) -> dict | None:
    wanted = str(name).strip().lower()
    for m in mandis():
        if m["mandi"].lower() == wanted:
            return m
    return None


# ---------- forecast and prices -------------------------------------------

def _parse_forecast(path: Path) -> dict:
    table: dict[tuple[str, str], list[dict]] = {}
    for r in _read_csv(path):
        try:
            row = {"crop": r["crop"].lower(), "mandi": r["mandi"],
                   "as_of_date": _day(r["as_of_date"]),
                   "horizon_days": int(float(r["horizon_days"])),
                   "price_low": rupees(r["price_low"]), "price_mid": rupees(r["price_mid"]),
                   "price_high": rupees(r["price_high"]),
                   "uses_baseline": _bool(r.get("uses_baseline")),
                   "last_price_date": (r.get("last_price_date") or "")[:10] or None,
                   "glut": _bool(r.get("glut"))}
        except (KeyError, ValueError) as exc:
            raise ValueError(f"bad forecast row {r}: {exc}") from exc
        table.setdefault((row["crop"], row["mandi"].lower()), []).append(row)
    for rows in table.values():
        rows.sort(key=lambda x: x["horizon_days"])
    return table


def forecast_table() -> dict | None:
    """{(crop, mandi lower-case): rows sorted by horizon}, or None until ML 1 ships the file."""
    return _load(DATA / "forecast_table.csv", _parse_forecast)


def _parse_prices(path: Path) -> dict:
    series: dict[tuple[str, str], list[tuple[str, int]]] = {}
    skipped = 0
    for r in _read_csv(path):
        try:
            day, price = _day(r["date"]), rupees(r["modal_price"])
            key = (r["crop"].lower(), r["mandi"].lower())
        except (KeyError, ValueError):
            skipped += 1
            continue
        if price is None:
            skipped += 1
            continue
        series.setdefault(key, []).append((day, price))
    for rows in series.values():
        rows.sort()
    if skipped:
        log.warning("%s: skipped %d unreadable rows", path.name, skipped)
    return series


def price_history(crop: str, mandi: str, end: str, days: int) -> list[dict]:
    """Reported prices in the `days` up to and including `end`. Reported days only; no filling."""
    series = _load(DATA / "prices_mh.csv", _parse_prices)
    if not series:
        return []
    start = (date.fromisoformat(end) - timedelta(days=days)).isoformat()
    return [{"date": d, "price": p} for d, p in series.get((crop, mandi.lower()), [])
            if start <= d <= end]


# ---------- evidence ------------------------------------------------------

def as_of_date() -> str | None:
    """The demo's "today" (data/splits.json as_of_date); None makes the engine use the forecast's date."""
    splits = _load(DATA / "splits.json", _read_json)
    return splits.get("as_of_date") if isinstance(splits, dict) else None


def backtest() -> object | None:
    return _load(DATA / "backtest.json", _read_json)


def selfcheck() -> list[dict] | None:
    return _load(DATA / "selfcheck.csv", _read_csv)


def coverage() -> list[dict] | None:
    return _load(DATA / "coverage.csv", _read_csv)


def fake(name: str):
    """A fresh copy of an example file from backend/fake."""
    return json.loads((FAKE / name).read_text(encoding="utf-8"))


def sources() -> dict:
    """Which inputs are real right now. Shown by GET /health for the integrator."""
    def state(path: Path, has_fake: bool) -> str:
        return "real" if path.is_file() else ("fake" if has_fake else "missing")

    return {"config.yaml": state(CONFIG, True),
            "data/villages.csv": state(DATA / "villages.csv", False),
            "data/mandis.csv": state(DATA / "mandis.csv", True),
            "data/forecast_table.csv": state(DATA / "forecast_table.csv", True),
            "data/prices_mh.csv": state(DATA / "prices_mh.csv", False),
            "data/backtest.json": state(DATA / "backtest.json", True),
            "data/selfcheck.csv": state(DATA / "selfcheck.csv", False),
            "data/coverage.csv": state(DATA / "coverage.csv", False)}


@contextlib.contextmanager
def example_data():
    """For self-tests: the contract's example config and data plus the real villages.csv,
    whatever ML 1 and ML 2 have committed. The self-tests assert on the example numbers."""
    global DATA, CONFIG
    saved = DATA, CONFIG
    with tempfile.TemporaryDirectory() as folder:
        shutil.copy(DATA / "villages.csv", folder)
        DATA, CONFIG = Path(folder), Path(folder) / "config.yaml"
        try:
            yield DATA
        finally:
            DATA, CONFIG = saved


def with_example_data(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        with example_data():
            return fn(*args, **kwargs)
    return wrapper


def _selftest():
    # the real files, as they are in the repo right now
    assert 20 <= len(villages()) <= 30, "the spec asks for 20-30 demo villages"
    assert all(v["lat"] and v["lon"] for v in villages()), "every village needs coordinates"
    assert len({v["village"].lower() for v in villages()}) == len(villages()), "duplicate village"
    assert all(set(m["crops"]) <= set(CROPS) for m in mandis()), "unknown crop in the mandi list"
    for keys in CONFIG_KEYS:
        cfg(*keys)                                     # raises if neither config has it
    for crop in CROPS:
        assert isinstance(hold_limit_days(crop, None), int)
    summary = f"{len(villages())} villages, {len(mandis())} mandis, sources={sources()}"
    if config_missing_keys():
        summary += f", config.yaml is missing {config_missing_keys()}"

    with example_data():                               # the contract copy of the assumptions
        assert sources()["config.yaml"] == "fake" and config_missing_keys() == []
        assert cfg("parser", "village_match_threshold") == 0.80
        assert hold_limit_days("tomato", None) == 4 and hold_limit_days("tomato", 2) == 0
        assert hold_limit_days("onion", True) == 21 and hold_limit_days("onion", False) == 5
        assert hold_limit_days("soybean", False) == 3
        assert [m["mandi"] for m in mandis()] == ["Lasalgaon", "Pimpalgaon"]
    assert rupees("1843.6") == 1844 and rupees("") is None
    assert _day("2026-08-31 00:00:00") == "2026-08-31"
    print(f"data_loader ok: {summary}")


if __name__ == "__main__":
    _selftest()
