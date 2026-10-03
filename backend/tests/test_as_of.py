"""/advise for a past date: the engine answers from that day's leak-checked row in forecast_history.csv.
Run from the repo root: .venv/bin/python backend/tests/test_as_of.py
"""
import csv
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ["SELLSMART_DB"] = str(Path(tempfile.mkdtemp()) / "test.db")   # not the demo database

from fastapi.testclient import TestClient  # noqa: E402

from backend.main import app  # noqa: E402
from ml.engine import api as engine  # noqa: E402

client = TestClient(app)
dates = client.get("/as-of-dates").json()
history = sorted({r["as_of_date"] for r in csv.DictReader(open(ROOT / "data" / "forecast_history.csv"))})
assert dates["default"] == "2025-09-21" and set(history) <= set(dates["dates"]), dates
rows = list(csv.DictReader(open(ROOT / "data" / "forecast_history.csv")))


def advise(**extra):
    body = {"crop": "onion", "quantity_qtl": 20, "village": "Niphad", "lang": "en", **extra}
    return client.post("/advise", json=body)


demo = advise().json()
assert (demo["mandi"], demo["net_per_qtl"], demo["gain_vs_baseline"]) == ("Pimpalgaon", 1089, 35)  # unchanged
for d in [history[0], "2025-08-10", history[-1]]:
    got = advise(as_of_date=d).json()
    want = engine.advise("onion", 20, "Niphad", as_of_date=d, forecast=rows)          # the engine itself
    assert got["prices_as_of"] == d and all(got[k] == want[k] for k in
                                            ("action", "mandi", "days", "net_per_qtl", "gain_vs_baseline")), d
    assert got["gain_from_mandi"] + got["gain_from_waiting"] == got["gain_vs_baseline"]
assert advise(as_of_date="2024-01-01").status_code == 400
print(f"as-of dates ok: {len(dates['dates'])} dates; past dates match the engine; demo date unchanged (1089 / +35)")
