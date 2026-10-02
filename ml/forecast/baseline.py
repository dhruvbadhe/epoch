"""Simple fallback forecast: last price with a band (ML1_FORECAST.md section 4).

Writes data/forecast_table.csv (as_of_date from splits.json) and data/forecast_history.csv
(every 3rd day of the test block). Every row has uses_baseline = true.
Run from the repo root: venv/bin/python ml/forecast/baseline.py [--table-only]
"""
import json
import sys

import duckdb

# ponytail: placeholders from the spec until config.yaml (ML 2) exists; read forecast.* from it then.
HORIZONS = [1, 2, 3, 7, 14, 21]
MIN_REPORTED_DAYS = 500  # forecast.min_reported_days
FALLING_RATIO = 0.90  # forecast.falling_ratio
COLS = "crop, mandi, as_of_date, horizon_days, price_low, price_mid, price_high, uses_baseline, last_price_date, falling"

s = json.load(open("data/splits.json"))
con = duckdb.connect()
con.execute("CREATE TABLE p AS SELECT date::DATE AS date, crop, mandi, modal_price FROM 'data/prices_mh.csv'")
con.execute(f"""CREATE TABLE series AS SELECT crop, mandi FROM p WHERE date <= DATE '{s["train_end"]}'
                GROUP BY crop, mandi HAVING count(*) >= {MIN_REPORTED_DAYS}""")
con.execute(f"CREATE TABLE hz AS SELECT unnest({HORIZONS}) AS h")

# h-day ratios in the train block, t = each reported day. Target per section 3: t+h, else t+h+1,
# else t+h-1 (not for h = 1, where t+h-1 = t). Target must also fall inside the train block.
con.execute(f"""
    CREATE TABLE band AS
    SELECT crop, mandi, h, quantile_cont(ratio, 0.1) AS q10, quantile_cont(ratio, 0.9) AS q90, count(*) AS n
    FROM (SELECT t.crop, t.mandi, h,
                 coalesce(a.modal_price, b.modal_price, CASE WHEN h > 1 THEN c.modal_price END) / t.modal_price AS ratio,
                 coalesce(a.date, b.date, CASE WHEN h > 1 THEN c.date END) AS target_date
          FROM p t JOIN series USING (crop, mandi) CROSS JOIN hz
          LEFT JOIN p a ON a.crop = t.crop AND a.mandi = t.mandi AND a.date = t.date + h
          LEFT JOIN p b ON b.crop = t.crop AND b.mandi = t.mandi AND b.date = t.date + h + 1
          LEFT JOIN p c ON c.crop = t.crop AND c.mandi = t.mandi AND c.date = t.date + h - 1
          WHERE t.date <= DATE '{s["train_end"]}')
    WHERE ratio IS NOT NULL AND target_date <= DATE '{s["train_end"]}'
    GROUP BY crop, mandi, h
""")

con.execute(f"""
    CREATE TABLE dates AS
    SELECT DATE '{s["as_of_date"]}' AS as_of_date, true AS live
    UNION ALL
    SELECT d::DATE, false FROM generate_series(DATE '{s["test_start"]}', DATE '{s["test_end"]}', INTERVAL 3 DAY) g(d)
""")

# State of each series at each as_of_date, using only prices on or before it.
con.execute(f"""
    CREATE TABLE state AS
    SELECT as_of_date, live, crop, mandi,
           any_value(modal_price) FILTER (WHERE rn = 1) AS price,
           max(date) AS last_price_date,
           count(*) FILTER (WHERE date > as_of_date - 10) >= 4
             AND any_value(modal_price) FILTER (WHERE rn = 1) / avg(modal_price) FILTER (WHERE rn <= 7) < {FALLING_RATIO}
             AS falling
    FROM (SELECT a.as_of_date, a.live, p.*,
                 row_number() OVER (PARTITION BY a.as_of_date, a.live, p.crop, p.mandi ORDER BY p.date DESC) AS rn
          FROM dates a JOIN p ON p.date <= a.as_of_date JOIN series USING (crop, mandi))
    WHERE rn <= 10
    GROUP BY ALL
""")

con.execute(f"""
    CREATE TABLE fc AS
    SELECT live, crop, mandi, as_of_date, 0 AS horizon_days, price AS price_low, price AS price_mid,
           price AS price_high, true AS uses_baseline, last_price_date, falling
    FROM state
    UNION ALL
    SELECT live, crop, mandi, as_of_date, h, round(price * q10)::INTEGER, price, round(price * q90)::INTEGER,
           true, last_price_date, falling
    FROM state JOIN band USING (crop, mandi)
""")

outputs = [("data/forecast_table.csv", "true"), ("data/forecast_history.csv", "false")]
for path, live in outputs[:1] if "--table-only" in sys.argv else outputs:
    con.execute(f"COPY (SELECT {COLS} FROM fc WHERE live = {live} ORDER BY as_of_date, crop, mandi, horizon_days) "
                f"TO '{path}' (HEADER)")
    print(f"{path}: {con.sql(f'SELECT count(*) FROM fc WHERE live = {live}').fetchone()[0]} rows")

print(f"series kept (>= {MIN_REPORTED_DAYS} train days): {con.sql('SELECT count(*) FROM series').fetchone()[0]}")
print("history as_of_dates:", con.sql("SELECT count(*), min(as_of_date), max(as_of_date) FROM dates WHERE NOT live").fetchone())
print("ratio samples per (crop, mandi, h): min", con.sql("SELECT min(n) FROM band").fetchone()[0])
print("bands not straddling 1 (q10 > 1 or q90 < 1):", con.sql("SELECT count(*) FROM band WHERE q10 > 1 OR q90 < 1").fetchone()[0])
