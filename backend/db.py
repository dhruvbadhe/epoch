"""SQLite copy of the handoff files for inspection, plus a log of answered queries (stdlib sqlite3).

The engine never reads this database; it keeps reading data/*.csv and data/backtest.json.
Built at backend startup if missing. Rebuild (keeps the queries log): python3 -m backend.db
SELLSMART_DB overrides the path (the tests use a temporary file).
"""
from __future__ import annotations

import csv
import json
import logging
import os
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import data_loader, querylog

log = logging.getLogger("sellsmart.db")

SOURCES = data_loader.ROOT / "data"          # always the real files, whatever a self-test swaps in
TABLES = {"prices": "prices_mh.csv", "mandis": "mandis.csv", "villages": "villages.csv",
          "forecasts": "forecast_table.csv"}
IST = timezone(timedelta(hours=5, minutes=30))
_lock = threading.Lock()

QUERIES = """CREATE TABLE IF NOT EXISTS queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, channel TEXT, sender TEXT, language TEXT,
    crop TEXT, quantity_qtl REAL, village TEXT, action TEXT, mandi TEXT, net_per_qtl INTEGER,
    gain_vs_baseline INTEGER, hold_suppressed INTEGER)"""


def path() -> Path:
    return Path(os.getenv("SELLSMART_DB") or SOURCES / "sellsmart.db")


def _value(text: str):
    """CSV text -> int, float or text, so SQL sorts and compares numbers as numbers; '' -> NULL."""
    if text == "":
        return None
    for kind in (int, float):
        try:
            return kind(text)
        except ValueError:
            pass
    return text


def build(target: Path | None = None) -> Path:
    """(Re)load the four CSV tables and backtest_results; the queries log is kept."""
    target = target or path()
    with _lock, sqlite3.connect(target) as con:
        for table, name in TABLES.items():
            with (SOURCES / name).open(encoding="utf-8-sig", newline="") as f:
                rows = list(csv.reader(f))
            header, body = rows[0], rows[1:]
            con.execute(f'DROP TABLE IF EXISTS "{table}"')
            columns = ", ".join('"' + c + '"' for c in header)
            con.execute(f'CREATE TABLE "{table}" ({columns})')
            con.executemany(f'INSERT INTO "{table}" VALUES ({", ".join("?" * len(header))})',
                            [[_value(v) for v in r] for r in body])
        con.execute("DROP TABLE IF EXISTS backtest_results")
        con.execute("CREATE TABLE backtest_results (crop TEXT, position INTEGER, policy TEXT, avg_net INTEGER)")
        backtest = json.loads((SOURCES / "backtest.json").read_text(encoding="utf-8"))
        con.executemany("INSERT INTO backtest_results VALUES (?, ?, ?, ?)",
                        [(crop, i, step["policy"], step["avg_net"]) for crop, entry in backtest.items()
                         for i, step in enumerate(entry.get("ladder", []), 1)])
        con.execute(QUERIES)
    return target


def ensure() -> None:
    """Build the database at startup if it isn't there; a failure is logged, never raised."""
    try:
        if not path().is_file():
            log.info("built %s", build())
    except Exception:
        log.exception("could not build %s", path())


def log_query(channel: str, sender: str | None, language: str | None, crop: str | None, quantity_qtl,
              village: str | None, advice: dict) -> None:
    """One row per answered request. Never raises: a logging failure must not break a reply."""
    try:
        row = (datetime.now(IST).isoformat(timespec="seconds"), channel,
               querylog.mask(sender) if sender else None, language, crop, quantity_qtl, village,
               advice.get("action"), advice.get("mandi"), advice.get("net_per_qtl"),
               advice.get("gain_vs_baseline"), int(bool(advice.get("hold_suppressed"))))
        with _lock, sqlite3.connect(path()) as con:
            con.execute(QUERIES)
            con.execute("INSERT INTO queries (timestamp, channel, sender, language, crop, quantity_qtl, "
                        "village, action, mandi, net_per_qtl, gain_vs_baseline, hold_suppressed) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", row)
    except Exception:
        log.exception("could not log the query to %s", path())


if __name__ == "__main__":
    built = build()
    with sqlite3.connect(built) as con:
        for table in [*TABLES, "backtest_results", "queries"]:
            print(f"{table}: {con.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]} rows")
    print(f"rebuilt {built}")
