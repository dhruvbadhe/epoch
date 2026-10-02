"""Quantile LightGBM per crop + self-check (ML1_FORECAST.md sections 5 and 6).

Rebuilds the fallback first (baseline.py), then replaces rows whose (crop, mandi, horizon) passes the
self-check. Writes data/selfcheck.csv, data/forecast_table.csv, data/forecast_history.csv.
Run from the repo root: venv/bin/python ml/forecast/model.py
"""
import json
import runpy

import lightgbm as lgb
import numpy as np
import pandas as pd

from features import FEATURES, build, load_prices

CROPS = ["onion", "tomato", "soybean"]
QUANTILES = [0.1, 0.5, 0.9]
SELFCHECK_RATIO_MAX = 0.95  # forecast.selfcheck_ratio_max (placeholder until config.yaml)
SELFCHECK_MIN_ROWS = 20  # forecast.selfcheck_min_rows
# Learn target / same_as_today rather than the price level, so one pooled model fits every mandi and
# price regime. Chosen on onion validation (24 vs 18 passes); the target is still the section 3 price.
RELATIVE = True
PARAMS = dict(objective="quantile", learning_rate=0.05, num_leaves=15, min_data_in_leaf=100,
              feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=1, seed=0, verbose=-1)
ROUNDS = 300


def scale(d):
    return np.asarray(d.same_as_today if RELATIVE else np.ones(len(d)), dtype=float)


if __name__ == "__main__":
    runpy.run_path("ml/forecast/baseline.py")  # fresh fallback rows for everything

    s = {k: pd.Timestamp(v) for k, v in json.load(open("data/splits.json")).items()}
    prices = load_prices()
    paths = ["data/forecast_table.csv", "data/forecast_history.csv"]
    forecasts = {p: pd.read_csv(p, parse_dates=["as_of_date"]) for p in paths}
    selfchecks = []


    for crop in CROPS:
        rows = build(prices, crop, prices.date.max())
        rows["mandi"] = rows.mandi.astype("category")
        has_target = rows.target.notna()
        train = rows[has_target & (rows.t <= s["train_end"]) & (rows.target_date <= s["train_end"])]
        val = rows[has_target & rows.t.between(s["val_start"], s["val_end"]) & (rows.target_date <= s["val_end"])]
        print(f"\n{crop}: train rows {len(train)}, validation rows {len(val)}")

        models = [lgb.train({**PARAMS, "alpha": q}, lgb.Dataset(train[FEATURES], train.target / scale(train)), ROUNDS)
                  for q in QUANTILES]

        def predict(d):
            """low, mid, high per row, sorted so low <= mid <= high."""
            return np.sort(np.column_stack([m.predict(d[FEATURES]) for m in models]) * scale(d)[:, None], axis=1)

        # Self-check on validation, per mandi and horizon.
        val = val.assign(mid=predict(val)[:, 1])
        sc = (val.assign(err_model=(val.mid - val.target).abs(), err_same=(val.same_as_today - val.target).abs())
              .groupby(["mandi", "h"], observed=True)
              .agg(model_mae=("err_model", "mean"), same_as_today_mae=("err_same", "mean"), rows=("target", "size"))
              .reset_index())
        sc["ratio"] = sc.model_mae / sc.same_as_today_mae
        sc["passed"] = (sc.ratio < SELFCHECK_RATIO_MAX) & (sc.rows >= SELFCHECK_MIN_ROWS)
        sc = sc.assign(crop=crop, mandi=sc.mandi.astype(str)).rename(columns={"h": "horizon_days"})
        selfchecks.append(sc)
        print(f"{crop}: self-check passed {int(sc.passed.sum())} of {len(sc)} (mandi, horizon) pairs")

        # Replace passing rows of this crop in both forecast files with the model's band.
        passed = set(zip(sc.mandi[sc.passed], sc.horizon_days[sc.passed]))
        feat = rows.assign(mandi=rows.mandi.astype(str)).set_index(["mandi", "t", "h"])
        for path, fc in forecasts.items():
            hit = (fc.crop == crop) & [(m, h) in passed for m, h in zip(fc.mandi, fc.horizon_days)]
            x = feat.loc[pd.MultiIndex.from_arrays([fc.mandi[hit], fc.as_of_date[hit], fc.horizon_days[hit]])].reset_index()
            x["mandi"] = pd.Categorical(x.mandi, categories=rows.mandi.cat.categories)
            fc.loc[hit, ["price_low", "price_mid", "price_high"]] = np.round(predict(x)).astype(int)
            fc.loc[hit, "uses_baseline"] = False
            print(f"  {path}: {int(hit.sum())} rows from the model, {int((fc.crop == crop).sum() - hit.sum())} fallback")

    tf = {True: "true", False: "false"}
    sc = pd.concat(selfchecks)[["crop", "mandi", "horizon_days", "model_mae", "same_as_today_mae", "ratio", "rows", "passed"]]
    sc.round({"model_mae": 1, "same_as_today_mae": 1, "ratio": 3}).assign(passed=sc.passed.map(tf)) \
        .to_csv("data/selfcheck.csv", index=False)
    for path, fc in forecasts.items():
        fc.assign(as_of_date=fc.as_of_date.dt.strftime("%Y-%m-%d"),
                  uses_baseline=fc.uses_baseline.map(tf), falling=fc.falling.map(tf)).to_csv(path, index=False)
