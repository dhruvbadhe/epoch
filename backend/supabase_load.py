"""Copy every data file (and the local query log) into Supabase Postgres, for browsing in its Table Editor.

A snapshot: tables are dropped and reloaded on each run. The engine never reads Supabase.
Needs SUPABASE_DB_URL (Session pooler URI) in backend/.env and psql on PATH.
Run from the repo root: .venv/bin/python -m backend.supabase_load
"""
from __future__ import annotations

import csv
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CSV_TABLES = {  # Supabase table -> data file
    "prices": "prices_mh.csv", "mandis": "mandis.csv", "villages": "villages.csv",
    "forecasts": "forecast_table.csv", "forecast_history": "forecast_history.csv",
    "selfcheck": "selfcheck.csv", "selfcheck_history": "selfcheck_history.csv", "coverage": "coverage.csv",
    "selfcheck_v1": "selfcheck_v1.csv", "coverage_v1": "coverage_v1.csv",
}


def _type(values: list[str], json_column: bool = False) -> str:
    """Postgres type that fits every non-empty value in a CSV column."""
    if json_column:
        return "jsonb"
    seen = [v for v in values if v != ""]
    if not seen:
        return "text"
    for kind, pattern in (("bigint", r"-?\d+"), ("double precision", r"-?\d+(\.\d+)?([eE]-?\d+)?"),
                          ("date", r"\d{4}-\d{2}-\d{2}"), ("boolean", r"true|false")):
        if all(re.fullmatch(pattern, v) for v in seen):
            return kind
    return "text"


def _read(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    return rows[0], rows[1:]


def _write(path: Path, header: list[str], rows: list[list]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    return path


def _derived(tmp: Path) -> dict[str, tuple[Path, set[str]]]:
    """splits, backtest_summary, backtest_results and queries as CSV files, plus their jsonb columns."""
    out = {}
    splits = json.loads((DATA / "splits.json").read_text(encoding="utf-8"))
    out["splits"] = (_write(tmp / "splits.csv", list(splits), [list(splits.values())]), set())

    backtest = json.loads((DATA / "backtest.json").read_text(encoding="utf-8"))
    keys = list(dict.fromkeys(k for entry in backtest.values() for k in entry))
    nested = {k for entry in backtest.values() for k, v in entry.items() if isinstance(v, (dict, list))}
    rows = [[json.dumps(e.get(k), ensure_ascii=False) if k in nested else ("" if e.get(k) is None else e.get(k))
             for k in keys] for e in backtest.values()]
    out["backtest_summary"] = (_write(tmp / "backtest_summary.csv", keys, rows), nested)
    ladder = [[crop, i, step["policy"], step["avg_net"]] for crop, e in backtest.items()
              for i, step in enumerate(e.get("ladder", []), 1)]
    out["backtest_results"] = (_write(tmp / "backtest_results.csv", ["crop", "position", "policy", "avg_net"],
                                      ladder), set())

    local = Path(os.getenv("SELLSMART_DB") or DATA / "sellsmart.db")
    header = ["timestamp", "channel", "sender", "language", "crop", "quantity_qtl", "village", "action", "mandi",
              "net_per_qtl", "gain_vs_baseline", "hold_suppressed"]
    rows = []
    if local.is_file():
        with sqlite3.connect(local) as con:
            if con.execute("SELECT 1 FROM sqlite_master WHERE name = 'queries'").fetchone():
                rows = [["" if v is None else v for v in r]
                        for r in con.execute(f"SELECT {', '.join(header)} FROM queries ORDER BY id")]
    out["queries"] = (_write(tmp / "queries.csv", header, rows), set())
    return out


def main() -> int:
    load_dotenv(ROOT / "backend" / ".env")
    url = os.getenv("SUPABASE_DB_URL", "").strip()
    psql = shutil.which("psql") or "/Library/PostgreSQL/18/bin/psql"
    if not url:
        print("SUPABASE_DB_URL is not set in backend/.env")
        return 1

    with tempfile.TemporaryDirectory() as folder:
        tmp = Path(folder)
        tables = {name: (DATA / file, set()) for name, file in CSV_TABLES.items()}
        tables.update(_derived(tmp))
        expected, sql = {}, ["\\set ON_ERROR_STOP on"]
        for name, (path, json_columns) in tables.items():
            header, rows = _read(path)
            expected[name] = len(rows)
            columns = [f'"{c}" {_type([r[i] for r in rows], c in json_columns)}' for i, c in enumerate(header)]
            quoted = ", ".join(f'"{c}"' for c in header)
            sql += [f'DROP TABLE IF EXISTS public."{name}";',
                    f'CREATE TABLE public."{name}" (id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, '
                    f'{", ".join(columns)});',
                    f"\\copy public.\"{name}\" ({quoted}) FROM '{path}' WITH (FORMAT csv, HEADER true)",
                    f'ALTER TABLE public."{name}" ENABLE ROW LEVEL SECURITY;']
        script = tmp / "load.sql"
        script.write_text("\n".join(sql) + "\n", encoding="utf-8")
        run = subprocess.run([psql, url, "-X", "-q", "-1", "-f", str(script)], capture_output=True, text=True)
        if run.returncode:
            print("load failed:", run.stderr.replace(url, "<SUPABASE_DB_URL>").strip())
            return 1

    counts = " UNION ALL ".join(f"SELECT '{n}', COUNT(*) FROM public.\"{n}\"" for n in expected)
    run = subprocess.run([psql, url, "-X", "-A", "-t", "-F", "|", "-c", counts], capture_output=True, text=True)
    if run.returncode:
        print("count failed:", run.stderr.replace(url, "<SUPABASE_DB_URL>").strip())
        return 1
    got = dict(line.split("|") for line in run.stdout.split())
    ok = True
    print(f"{'table':<20}{'source rows':>12}{'in Supabase':>13}")
    for name, n in expected.items():
        match = int(got.get(name, -1)) == n
        ok &= match
        print(f"{name:<20}{n:>12}{got.get(name, '?'):>13}  {'ok' if match else 'MISMATCH'}")
    print("all tables match" if ok else "some tables do not match")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
