"""Clean Maharashtra mandi prices (ML1_FORECAST.md section 2).

Writes data/prices_mh.csv, ml/forecast/variety_choice.csv, data/splits.json.
Run from the repo root: venv/bin/python ml/forecast/clean.py
"""
import json

import duckdb

RAW = "data/raw/*.parquet"
DATE_FROM, DATE_TO = "2021-01-01", "2025-11-04"
SPLITS = {
    "train_end": "2025-03-24",
    "val_start": "2025-04-15",
    "val_end": "2025-07-10",
    "test_start": "2025-08-01",
    "test_end": "2025-11-04",
    "as_of_date": "2025-11-03",
}
COMMODITY = {"Onion": "onion", "Tomato": "tomato", "Soyabean": "soybean"}
# Exact dataset spellings (after stripping a trailing " APMC").
MANDIS = {
    "onion": ["Lasalgaon", "Lasalgaon (Vinchur)", "Lasalgaon (Niphad)", "Pimpalgaon", "Nasik", "Pune", "Solapur"],
    "tomato": ["Pune", "Pune (Pimpri)", "Pimpalgaon", "Junnar (Narayangaon)", "Nasik"],
    "soybean": ["Amarawati", "Akola", "Nagpur", "Washim", "Latur"],
}

con = duckdb.connect()
con.execute("CREATE TABLE commodity (Commodity VARCHAR, crop VARCHAR)")
con.executemany("INSERT INTO commodity VALUES (?, ?)", list(COMMODITY.items()))
con.execute("CREATE TABLE keep (crop VARCHAR, mandi VARCHAR)")
con.executemany("INSERT INTO keep VALUES (?, ?)", [(c, m) for c, ms in MANDIS.items() for m in ms])

# Filter while reading. file order (filename, file_row_number) defines "first" below.
con.execute(f"""
    CREATE TABLE base AS
    SELECT k.crop, k.mandi, r.District AS district, r.Variety AS variety, r.Grade AS grade,
           CAST(r.Arrival_Date AS DATE) AS date, r.Modal_Price, r.Min_Price, r.Max_Price,
           r.State, r.Market, r.Commodity, r.Commodity_Code, r.Arrival_Date,
           r.filename, r.file_row_number
    FROM read_parquet('{RAW}', filename = true, file_row_number = true) r
    JOIN commodity c USING (Commodity)
    JOIN keep k ON k.crop = c.crop AND k.mandi = regexp_replace(r.Market, ' APMC$', '')
    WHERE r.State = 'Maharashtra' AND r.Arrival_Date BETWEEN '{DATE_FROM}' AND '{DATE_TO}'
""")

missing = con.sql("SELECT crop, mandi FROM keep ANTI JOIN base USING (crop, mandi)").fetchall()
assert not missing, f"mandis not found in data: {missing}"

# One variety per crop and mandi: the one with the most rows, any grade. Deviation from the spec's
# variety-and-grade pair (team decision): grades were relabelled ~2025-01-27 (FAQ -> Local/Non-FAQ),
# so a fixed pair cuts every series off in January 2025.
con.execute("""
    CREATE TABLE variety_choice AS
    SELECT crop, mandi, variety, grades, n AS rows, total AS mandi_rows
    FROM (SELECT crop, mandi, variety, string_agg(DISTINCT grade, '|' ORDER BY grade) AS grades, count(*) AS n,
                 sum(count(*)) OVER (PARTITION BY crop, mandi) AS total
          FROM base GROUP BY crop, mandi, variety)
    QUALIFY row_number() OVER (PARTITION BY crop, mandi ORDER BY n DESC, variety) = 1
    ORDER BY crop, mandi
""")

con.execute("CREATE TABLE s0 AS SELECT b.* FROM base b JOIN variety_choice v USING (crop, mandi, variety)")
con.execute("""CREATE TABLE s1 AS SELECT * FROM s0
               WHERE Modal_Price > 0 AND Modal_Price BETWEEN Min_Price AND Max_Price""")
con.execute("""CREATE TABLE s2 AS SELECT * FROM s1
               QUALIFY row_number() OVER (PARTITION BY State, District, Market, Commodity, variety, grade,
                   Arrival_Date, Min_Price, Max_Price, Modal_Price, Commodity_Code
                   ORDER BY filename, file_row_number) = 1""")
con.execute("""CREATE TABLE clean AS SELECT * FROM s2
               QUALIFY row_number() OVER (PARTITION BY crop, mandi, date ORDER BY filename, file_row_number) = 1""")

n = {t: con.sql(f"SELECT count(*) FROM {t}").fetchone()[0] for t in ["base", "s0", "s1", "s2", "clean"]}
print("=== Row counts ===")
print(f"read (crops, mandis, {DATE_FROM}..{DATE_TO}): {n['base']}")
print(f"dropped, other variety:                       {n['base'] - n['s0']}")
print(f"dropped, modal 0/missing/outside [min, max]:  {n['s0'] - n['s1']}")
print(f"dropped, exact duplicates:                    {n['s1'] - n['s2']}")
print(f"dropped, 2nd row same crop/mandi/date:        {n['s2'] - n['clean']}")
print(f"kept:                                         {n['clean']}")

con.execute("""
    COPY (SELECT strftime(date, '%Y-%m-%d') AS date, crop, mandi, district, variety, grade,
                 CAST(Modal_Price AS INTEGER) AS modal_price, CAST(Min_Price AS INTEGER) AS min_price,
                 CAST(Max_Price AS INTEGER) AS max_price
          FROM clean ORDER BY crop, mandi, date) TO 'data/prices_mh.csv' (HEADER)
""")
con.execute("COPY variety_choice TO 'ml/forecast/variety_choice.csv' (HEADER)")

s = SPLITS
assert DATE_FROM < s["train_end"] < s["val_start"] <= s["val_end"] < s["test_start"] <= s["as_of_date"] <= s["test_end"]
with open("data/splits.json", "w") as f:
    json.dump(SPLITS, f, indent=2)
    f.write("\n")

# Self-check on what was written.
chk = con.sql("""SELECT count(*) FILTER (WHERE modal_price <= 0 OR modal_price NOT BETWEEN min_price AND max_price),
                        count(*) - count(DISTINCT (crop, mandi, date))
                 FROM 'data/prices_mh.csv'""").fetchone()
assert chk == (0, 0), f"bad prices / duplicate days in prices_mh.csv: {chk}"

print("\n=== Per crop and mandi (reported days per block) ===")
con.sql(f"""
    SELECT crop, mandi, variety, string_agg(DISTINCT grade, '|' ORDER BY grade) AS grades,
           count(*) FILTER (WHERE date <= DATE '{s["train_end"]}') AS train_days,
           count(*) FILTER (WHERE date BETWEEN DATE '{s["val_start"]}' AND DATE '{s["val_end"]}') AS val_days,
           count(*) FILTER (WHERE date BETWEEN DATE '{s["test_start"]}' AND DATE '{s["test_end"]}') AS test_days,
           max(date) AS last_date
    FROM clean GROUP BY crop, mandi, variety ORDER BY crop, mandi
""").show(max_rows=100, max_width=200)
