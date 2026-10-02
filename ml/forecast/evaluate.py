"""Test-block evaluation (ML1_FORECAST.md section 7) and candidate demo hold dates.

Reads data/forecast_history.csv as delivered (model + fallback rows). The real price is the section 3
target at as_of_date + h. Writes data/coverage.csv. Nothing upstream may be changed because of these numbers.
Run from the repo root: venv/bin/python ml/forecast/evaluate.py [test_table_out.csv]
"""
import json
import sys

import pandas as pd

from features import build, load_prices

s = {k: pd.Timestamp(v) for k, v in json.load(open("data/splits.json")).items()}
prices = load_prices()
real = pd.concat(build(prices, c, prices.date.max()).assign(crop=c) for c in ["onion", "tomato", "soybean"])
real = real[real.target_date <= s["test_end"]][["crop", "mandi", "t", "h", "target"]]

fc = pd.read_csv("data/forecast_history.csv", parse_dates=["as_of_date"])
today = fc[fc.horizon_days == 0][["crop", "mandi", "as_of_date", "price_mid"]].rename(columns={"price_mid": "today"})
fc = (fc[fc.horizon_days > 0].merge(today, on=["crop", "mandi", "as_of_date"])
      .merge(real, left_on=["crop", "mandi", "as_of_date", "horizon_days"], right_on=["crop", "mandi", "t", "h"], how="left"))
ev = fc.dropna(subset=["target"])

cov = (ev.assign(inside=ev.target.between(ev.price_low, ev.price_high))
       .groupby(["crop", "horizon_days"]).agg(coverage=("inside", "mean"), n=("inside", "size")).reset_index())
cov.round({"coverage": 3}).to_csv("data/coverage.csv", index=False)
print("=== data/coverage.csv (test block) ===")
print(cov.round({"coverage": 3}).to_string(index=False))

e = ev.assign(err_mid=(ev.price_mid - ev.target).abs(), err_same=(ev.today - ev.target).abs())
mae = (e.groupby(["crop", "horizon_days"])
       .agg(mid_mae=("err_mid", "mean"), same_as_today_mae=("err_same", "mean"), n=("err_mid", "size"))
       .reset_index())
mae["ratio"] = mae.mid_mae / mae.same_as_today_mae
m = e[~e.uses_baseline]
model_only = (m.groupby(["crop", "horizon_days"])
              .agg(model_rows=("err_mid", "size"), model_mid_mae=("err_mid", "mean"), model_same_mae=("err_same", "mean"))
              .reset_index())
model_only["model_ratio"] = model_only.model_mid_mae / model_only.model_same_mae  # NaN when no model rows
test = mae.merge(model_only, on=["crop", "horizon_days"], how="left").merge(cov, on=["crop", "horizon_days", "n"])
test["model_rows"] = test.model_rows.fillna(0).astype(int)
test = test.round({"mid_mae": 1, "same_as_today_mae": 1, "ratio": 3, "model_mid_mae": 1, "model_same_mae": 1,
                   "model_ratio": 3, "coverage": 3})
print("\n=== MAE on the test block: price_mid vs same as today (all rows; model rows only) ===")
print(test.to_string(index=False))
if len(sys.argv) > 1:
    test.to_csv(sys.argv[1], index=False)
    print(f"test table written to {sys.argv[1]}")

cand = fc[(fc.crop == "onion") & fc.horizon_days.isin([7, 14]) & ~fc.uses_baseline & (fc.price_mid >= 1.08 * fc.today)]
cand = cand.assign(mid_over_today=cand.price_mid / cand.today).sort_values("mid_over_today", ascending=False)
print(f"\n=== Candidate demo holds: onion, h = 7 or 14, model row, mid >= 1.08 x today ({len(cand)} found, top 10) ===")
print(cand.head(10)[["as_of_date", "mandi", "horizon_days", "today", "price_low", "price_mid", "price_high",
                     "target", "mid_over_today"]]
      .rename(columns={"as_of_date": "date", "horizon_days": "h", "target": "real_price"})
      .assign(date=lambda d: d.date.dt.strftime("%Y-%m-%d")).round({"mid_over_today": 3}).to_string(index=False))
