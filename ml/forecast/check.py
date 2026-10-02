"""Self-test before each push (ML1_FORECAST.md section 9).

Run from the repo root: venv/bin/python ml/forecast/check.py
"""
import json

import duckdb

s = json.load(open("data/splits.json"))
con = duckdb.connect()
con.execute("CREATE TABLE p AS SELECT date::DATE AS date, crop, mandi, modal_price FROM 'data/prices_mh.csv'")
con.execute("""CREATE TABLE f AS
               SELECT 'table' AS src, * FROM read_csv('data/forecast_table.csv', types = {'falling': 'BOOLEAN'})
               UNION ALL
               SELECT 'history', * FROM read_csv('data/forecast_history.csv', types = {'falling': 'BOOLEAN'})""")


def check(name, sql):
    bad = con.sql(sql).fetchall()
    assert not bad, f"FAIL {name}: {bad[:5]}"
    print(f"ok  {name}")


check("low <= mid <= high, all positive",
      "SELECT * FROM f WHERE NOT (0 < price_low AND price_low <= price_mid AND price_mid <= price_high)")
check("every forecast has horizons 0, 1, 2, 3, 7, 14, 21 exactly once",
      """SELECT src, as_of_date, crop, mandi FROM f GROUP BY ALL
         HAVING list_sort(list(horizon_days)) != [0, 1, 2, 3, 7, 14, 21]""")
check("forecast_table as_of_date = splits.as_of_date",
      f"SELECT * FROM f WHERE src = 'table' AND as_of_date != DATE '{s['as_of_date']}'")
check("every history as_of_date inside the test block",
      f"""SELECT * FROM f WHERE src = 'history'
          AND as_of_date NOT BETWEEN DATE '{s['test_start']}' AND DATE '{s['test_end']}'""")
check("no last_price_date after its as_of_date", "SELECT * FROM f WHERE last_price_date > as_of_date")
check("no row built from data after its as_of_date (horizon 0 = latest price on or before as_of_date)",
      """SELECT f.src, f.as_of_date, f.crop, f.mandi FROM f
         LEFT JOIN p ON p.crop = f.crop AND p.mandi = f.mandi AND p.date = f.last_price_date
         WHERE f.horizon_days = 0 AND (p.modal_price IS NULL OR p.modal_price != f.price_mid
               OR EXISTS (SELECT 1 FROM p q WHERE q.crop = f.crop AND q.mandi = f.mandi
                          AND q.date > f.last_price_date AND q.date <= f.as_of_date))""")
check("every (crop, mandi) in mandis.csv",
      """SELECT DISTINCT crop, mandi FROM f ANTI JOIN
         (SELECT mandi, unnest(string_split(crops, '|')) AS crop FROM 'data/mandis.csv') USING (crop, mandi)""")
con.execute("CREATE TABLE sch AS SELECT * FROM read_csv('data/selfcheck_history.csv', types = {'passed': 'BOOLEAN'})")
check("uses_baseline = false exactly where the trailing self-check passed at that as_of_date (never at horizon 0)",
      """SELECT f.src, f.as_of_date, f.crop, f.mandi, f.horizon_days FROM f
         LEFT JOIN sch USING (as_of_date, crop, mandi, horizon_days)
         WHERE (NOT f.uses_baseline) != (f.horizon_days > 0 AND coalesce(sch.passed, false))""")
check("selfcheck.csv = selfcheck_history.csv at splits.as_of_date",
      f"""(SELECT * EXCLUDE (as_of_date) FROM sch WHERE as_of_date = DATE '{s['as_of_date']}'
           EXCEPT SELECT * FROM read_csv('data/selfcheck.csv', types = {{'passed': 'BOOLEAN'}}))
          UNION ALL
          (SELECT * FROM read_csv('data/selfcheck.csv', types = {{'passed': 'BOOLEAN'}})
           EXCEPT SELECT * EXCLUDE (as_of_date) FROM sch WHERE as_of_date = DATE '{s['as_of_date']}')""")

# Leak check: rerun version 2 with prices cut at D. Everything written for D must come out identical.
# D = as_of_date, and 2025-08-01 (a refit date and a history date: the edge case).
import pandas as pd  # noqa: E402

from features import load_prices  # noqa: E402
from model_v2 import run  # noqa: E402

prices = load_prices()
for d in [pd.Timestamp(s["as_of_date"]), pd.Timestamp("2025-08-01")]:
    bands, sc, _ = run(prices[prices.date <= d], [d])
    got = bands.sort_values(["crop", "mandi", "horizon_days"]).reset_index(drop=True)
    want = con.sql(f"""SELECT crop, mandi, as_of_date, horizon_days, price_low, price_mid, price_high FROM f
                       WHERE as_of_date = DATE '{d.date()}' AND NOT uses_baseline AND src =
                       (SELECT min(src) FROM f WHERE as_of_date = DATE '{d.date()}')
                       ORDER BY crop, mandi, horizon_days""").df()
    pd.testing.assert_frame_equal(got, want, check_dtype=False)
    sc_want = con.sql(f"SELECT crop, mandi, horizon_days, rows, passed FROM sch WHERE as_of_date = DATE '{d.date()}' "
                      "ORDER BY crop, mandi, horizon_days").df()
    sc_got = sc.sort_values(["crop", "mandi", "horizon_days"])[["crop", "mandi", "horizon_days", "rows", "passed"]]
    pd.testing.assert_frame_equal(sc_got.reset_index(drop=True), sc_want, check_dtype=False)
    print(f"ok  no price after D used at D = {d.date()}: rerun with prices <= D gives identical bands "
          f"({len(got)} model rows) and self-check")
print("all checks passed")
