"""First look at the Kaggle mandi prices for Maharashtra (ML1_FORECAST.md section 2).

Run from the repo root: venv/bin/python ml/forecast/first_look.py
"""
import duckdb

RAW = "data/raw/*.parquet"
CROP_MATCH = "(lower(Commodity) LIKE '%onion%' OR lower(Commodity) LIKE '%tomato%' OR lower(Commodity) LIKE '%soya%')"

con = duckdb.connect()
# DuckDB pushes the WHERE into the Parquet scan, so only matching Maharashtra rows are read.
con.execute(f"""
    CREATE TEMP TABLE mh AS
    SELECT Commodity, Market, Variety, Grade, CAST(Arrival_Date AS DATE) AS d
    FROM read_parquet('{RAW}')
    WHERE State = 'Maharashtra' AND {CROP_MATCH}
""")


def show(title, sql):
    print(f"\n=== {title} ===")
    con.sql(sql).show(max_rows=100_000, max_width=200)


show("1. Commodity names containing onion / tomato / soya",
     "SELECT Commodity, count(*) AS rows FROM mh GROUP BY 1 ORDER BY 1")

show("2. Per commodity and market: reported days since 2023-01-01, first and last date (all years)",
     """SELECT Commodity, Market,
               count(DISTINCT d) FILTER (WHERE d >= DATE '2023-01-01') AS days_since_2023,
               min(d) AS first_date, max(d) AS last_date
        FROM mh GROUP BY 1, 2 ORDER BY 1, 3 DESC, 2""")

show("3. Per commodity: Variety and Grade pairs",
     "SELECT Commodity, Variety, Grade, count(*) AS rows FROM mh GROUP BY 1, 2, 3 ORDER BY 1, 4 DESC")

show("4. Last date in the Maharashtra rows (all commodities)",
     f"SELECT max(CAST(Arrival_Date AS DATE)) AS last_date FROM read_parquet('{RAW}') WHERE State = 'Maharashtra'")
