"""Demo-date shortlist from the v2 history files (read-only).

Per test-block as_of_date: onion pairs passing the trailing check at 7 or 14 days, tomato pairs passing at
1-3 days, and whether a passing onion row at 7 or 14 days has price_mid >= 1.08 x today's price. Then the
5 such dates with the highest mid / today (best row per date), with the real price that followed.
Run from the repo root: venv/bin/python ml/forecast/demo_dates.py
"""
import pandas as pd

from features import build, load_prices

HOLD_MIN = 1.08

fc = pd.read_csv("data/forecast_history.csv", parse_dates=["as_of_date"])
sch = pd.read_csv("data/selfcheck_history.csv", parse_dates=["as_of_date"])
sch = sch[sch.as_of_date.isin(fc.as_of_date)]
prices = load_prices()
real = build(prices, "onion", prices.date.max())[["mandi", "t", "h", "target"]]

today = fc[fc.horizon_days == 0][["crop", "mandi", "as_of_date", "price_mid"]].rename(columns={"price_mid": "today"})
on = (fc[(fc.crop == "onion") & fc.horizon_days.isin([7, 14]) & ~fc.uses_baseline]
      .merge(today, on=["crop", "mandi", "as_of_date"])
      .merge(real, left_on=["mandi", "as_of_date", "horizon_days"], right_on=["mandi", "t", "h"], how="left"))
hold = on[on.price_mid >= HOLD_MIN * on.today].assign(mid_over_today=lambda d: d.price_mid / d.today)

per_date = pd.DataFrame({
    "onion_pass_7_14": sch[(sch.crop == "onion") & sch.horizon_days.isin([7, 14])].groupby("as_of_date").passed.sum(),
    "tomato_pass_1_3": sch[(sch.crop == "tomato") & sch.horizon_days.isin([1, 2, 3])].groupby("as_of_date").passed.sum(),
}).astype(int)
per_date["onion_hold_row"] = per_date.index.isin(hold.as_of_date)
print("=== Per test-block as_of_date (onion: 14 pairs at 7/14 days; tomato: 15 pairs at 1-3 days) ===")
print(per_date.reset_index().assign(as_of_date=lambda d: d.as_of_date.dt.strftime("%Y-%m-%d")).to_string(index=False))

best = hold.sort_values("mid_over_today", ascending=False).drop_duplicates("as_of_date").head(5)
best = best.assign(outcome=["unknown" if pd.isna(r) else "rose" if r > t else "fell" if r < t else "flat"
                            for r, t in zip(best.target, best.today)])
print(f"\n=== {per_date.onion_hold_row.sum()} dates have a passing onion 7/14-day row with mid >= {HOLD_MIN} x today; "
      "top 5 (best row per date) ===")
print(best[["as_of_date", "mandi", "horizon_days", "today", "price_low", "price_mid", "price_high", "target", "outcome"]]
      .rename(columns={"horizon_days": "h", "target": "real_price"})
      .assign(as_of_date=lambda d: d.as_of_date.dt.strftime("%Y-%m-%d")).to_string(index=False))
