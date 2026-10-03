"""GET /market/snapshot: reported prices only, from before the as-of date; money in hand matches the engine.
Run from the repo root: .venv/bin/python backend/tests/test_market.py
"""
import csv
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ["SELLSMART_DB"] = str(Path(tempfile.mkdtemp()) / "test.db")   # not the demo database

from fastapi.testclient import TestClient  # noqa: E402

from backend.main import app  # noqa: E402

client = TestClient(app)
as_of = json.loads((ROOT / "data" / "splits.json").read_text())["as_of_date"]
prices = [r for r in csv.DictReader(open(ROOT / "data" / "prices_mh.csv")) if r["crop"] == "onion"]
yesterday = max(r["date"] for r in prices if r["date"] < as_of)

s = client.get("/market/snapshot", params={"crop": "onion", "village": "Niphad"}).json()
assert s["prices_as_of"] == as_of and s["snapshot_date"] == yesterday < as_of, s["snapshot_date"]
day = {r["mandi"]: r for r in prices if r["date"] == yesterday}
assert {r["mandi"] for r in s["reporting"]} == set(day)                    # exactly the mandis that reported
for r in s["reporting"]:                                                   # values straight from the file
    assert (r["modal_price"], r["min_price"], r["max_price"]) == tuple(
        int(float(day[r["mandi"]][k])) for k in ("modal_price", "min_price", "max_price")), r
modal = [r["modal_price"] for r in s["reporting"]]
assert s["highest_price"]["modal_price"] == max(modal) and s["lowest_price"]["modal_price"] == min(modal)
assert s["spread"] == max(modal) - min(modal)
assert all(p["date"] < as_of for m in s["series_7d"] for p in m["points"]) and len(s["series_dates"]) == 7
assert all(r["last_reported_date"] is None or r["last_reported_date"] < yesterday for r in s["not_reporting"])

# money in hand: equal to /advise's sell-today net wherever the engine's latest price is that same day
advice = client.post("/advise", json={"crop": "onion", "quantity_qtl": 20, "village": "Niphad"}).json()
forecast = {r["mandi"]: r for r in csv.DictReader(open(ROOT / "data" / "forecast_table.csv"))
            if r["crop"] == "onion" and r["horizon_days"] == "0"}
engine_net = {o["mandi"]: o["net_per_qtl"] for o in advice["options"] if o["sell_day"] == 0}
mih = s["money_in_hand"]
checked = 0
for row in mih["rows"]:
    if forecast[row["mandi"]]["last_price_date"] == yesterday and row["mandi"] in engine_net:
        assert row["net_per_qtl"] == engine_net[row["mandi"]], (row, engine_net[row["mandi"]])
        checked += 1
assert checked >= 2, checked
assert mih["highest"]["net_per_qtl"] == max(r["net_per_qtl"] for r in mih["rows"])
assert mih["label"] == "highest money in hand from Niphad" and "profitable" not in json.dumps(s).lower()

assert client.get("/market/snapshot", params={"crop": "wheat"}).status_code == 400
assert client.get("/market/snapshot", params={"crop": "onion", "village": "Atlantis"}).status_code == 400
assert client.get("/market/snapshot", params={"crop": "tomato"}).json()["money_in_hand"] is None
# regression: /forecast fills data_loader's cache for prices_mh.csv first (the dashboard order) -> still 200
from backend import data_loader, engine_api, market  # noqa: E402
for crop in ("onion", "tomato", "soybean"):
    client.get("/forecast", params={"crop": crop, "mandi": "Pimpalgaon" if crop != "soybean" else "Akola"})
    for params in ({"crop": crop, "village": "Niphad"}, {"crop": crop}):
        r = client.get("/market/snapshot", params=params)
        assert r.status_code == 200 and r.json()["reporting"], (params, r.status_code)

# a village without coordinates -> snapshot without money in hand, plus a message
nowhere = {**data_loader.find_village("Niphad"), "lat": None, "lon": None, "village": "Nowhere"}
r = market.snapshot("onion", nowhere)
assert r["reporting"] and r["money_in_hand"] is None and r["message"], r["message"]

# no reports on the snapshot date -> empty snapshot with a message, never an error
real_as_of = data_loader.as_of_date
data_loader.as_of_date = lambda: "2000-01-01"
try:
    r = market.snapshot("onion", data_loader.find_village("Niphad"))
    assert r["reporting"] == [] and r["money_in_hand"] is None and r["message"], r
finally:
    data_loader.as_of_date = real_as_of

# a reporting mandi missing from data/mandis.csv -> the engine's distance lookup fails -> no money in hand
engine = engine_api._load_module()
real_distance = engine.road_distance_km
engine.road_distance_km = lambda *a, **k: (_ for _ in ()).throw(ValueError("unknown mandi: Ghost"))
try:
    r = market.snapshot("onion", data_loader.find_village("Niphad"))
    assert r["reporting"] and r["money_in_hand"] is None and "unknown mandi" in r["message"], r["message"]
finally:
    engine.road_distance_km = real_distance

# even an unexpected failure in the snapshot returns 200 with a message
real_snapshot = market.snapshot
market.snapshot = lambda *a, **k: 1 / 0
try:
    r = client.get("/market/snapshot", params={"crop": "onion"})
    assert r.status_code == 200 and r.json()["message"], r.status_code
finally:
    market.snapshot = real_snapshot
print("ok  never 500: after /forecast, no coordinates, no reports, missing mandi, unexpected error")
print(f"market snapshot ok: {yesterday}, {len(s['reporting'])} mandis reported, highest {s['highest_price']}, "
      f"{checked} nets equal to /advise, best from Niphad {mih['highest']}")
