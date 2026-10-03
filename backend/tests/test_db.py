"""SQLite store: tables exist with the files' row counts, and one /advise call adds exactly one query row.
Uses a temporary database, never data/sellsmart.db. Run from the repo root:
    .venv/bin/python backend/tests/test_db.py
"""
import csv
import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ["SELLSMART_DB"] = str(Path(tempfile.mkdtemp()) / "test.db")

from fastapi.testclient import TestClient  # noqa: E402

from backend import db  # noqa: E402
from backend.main import app  # noqa: E402  (startup builds the missing database)


def csv_rows(name):
    with (ROOT / "data" / name).open(encoding="utf-8-sig", newline="") as f:
        return sum(1 for _ in csv.reader(f)) - 1


expected = {table: csv_rows(name) for table, name in db.TABLES.items()}
expected["backtest_results"] = sum(len(e["ladder"]) for e in json.loads((ROOT / "data" / "backtest.json").read_text()).values())


def count(table):
    with sqlite3.connect(db.path()) as con:
        return con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


assert db.path().is_file(), "startup did not build the database"
for table, n in expected.items():
    assert count(table) == n, (table, count(table), n)
    print(f"ok  {table}: {n} rows")

before = count("queries")
r = TestClient(app).post("/advise", json={"crop": "onion", "quantity_qtl": 20, "village": "Niphad", "lang": "en"})
assert r.status_code == 200, r.text
assert count("queries") == before + 1, (before, count("queries"))
with sqlite3.connect(db.path()) as con:
    row = con.execute("SELECT channel, sender, crop, quantity_qtl, village, action, mandi, net_per_qtl, "
                      "gain_vs_baseline, hold_suppressed FROM queries ORDER BY id DESC LIMIT 1").fetchone()
assert row == ("api", None, "onion", 20.0, "Niphad", "sell_now", "Pimpalgaon", 1089, 35, 1), row
print(f"ok  one /advise call -> exactly one queries row: {row}")

db.log_query("whatsapp", "919812344521", "mr", "onion", 20, "Niphad", {"action": "sell_now"})
with sqlite3.connect(db.path()) as con:
    assert con.execute("SELECT sender FROM queries ORDER BY id DESC LIMIT 1").fetchone()[0] == "…4521"
print("ok  sender masked to its last four digits")

os.environ["SELLSMART_DB"] = "/nonexistent-dir/x.db"            # a logging failure must not raise
db.log_query("api", None, "en", "onion", 1, "Niphad", {})
print("ok  a logging failure is swallowed")
print("all db checks passed")
