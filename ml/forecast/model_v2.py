"""Version 2: monthly refit, trailing self-check, trailing widening.

- Refit on the 1st of each month (REFITS) on rows whose target date is before the refit date, i.e. from
  prices before it. A forecast at origin t uses the latest refit on or before t.
- At each as_of_date D, per (crop, mandi, h): origins t with D - 90 <= t and t + h <= D, targets from prices
  on or before D. Pass = >= MIN_ROWS rows and MAE(mid) / MAE(same as today) < RATIO_MAX; else fallback.
- Widening per (crop, h) on the same window: if coverage < COVERAGE_MIN, widen both ends by the 80th
  percentile of max(low - actual, actual - high). Applies to model rows only.
Features and model settings are v1's (features.py, model.py). Rebuilds the fallback first (baseline.py).
Writes data/forecast_table.csv, data/forecast_history.csv, data/selfcheck.csv, data/selfcheck_history.csv.
Run from the repo root: venv/bin/python ml/forecast/model_v2.py

  --as-of-date YYYY-MM-DD   move the demo's "today": set splits.json as_of_date and rewrite only
                            data/forecast_table.csv, data/selfcheck.csv and that date's rows in
                            data/selfcheck_history.csv, from prices on or before that date.
                            forecast_history.csv is untouched.
"""
import argparse
import json
import runpy
import subprocess
import sys

import lightgbm as lgb
import numpy as np
import pandas as pd

from features import FEATURES, HORIZONS, build, load_prices
from model import CROPS, PARAMS, QUANTILES, ROUNDS, scale

# ponytail: placeholders until config.yaml (ML 2) exists.
REFITS = pd.date_range("2025-05-01", "2025-11-01", freq="MS")
WINDOW_DAYS = 90
MIN_ROWS = 15
RATIO_MAX = 0.95
COVERAGE_MIN = 0.70
WIDEN_QUANTILE = 0.8
SC_COLS = ["crop", "mandi", "horizon_days", "model_mae", "same_as_today_mae", "ratio", "rows", "passed"]
DAY = pd.Timedelta(days=1)


def predictions(prices, crop):
    """Model low/mid/high for every origin t from the first refit to the last price date."""
    end = prices.date.max()
    rows = build(prices, crop, end)  # features at t use prices on or before t
    cats = sorted(rows.mandi.unique())
    rows["mandi"] = pd.Categorical(rows.mandi, categories=cats)
    refits = [r for r in REFITS if r <= end]
    out = []
    for r, nxt in zip(refits, refits[1:] + [end + DAY]):
        train = build(prices[prices.date < r], crop, r - DAY).dropna(subset=["target"])
        train["mandi"] = pd.Categorical(train.mandi, categories=cats)
        models = [lgb.train({**PARAMS, "alpha": q}, lgb.Dataset(train[FEATURES], train.target / scale(train)), ROUNDS)
                  for q in QUANTILES]
        o = rows[(rows.t >= r) & (rows.t < nxt)]
        band = np.sort(np.column_stack([m.predict(o[FEATURES]) for m in models]) * scale(o)[:, None], axis=1)
        out.append(pd.DataFrame({"mandi": o.mandi.astype(str), "t": o.t, "h": o.h, "same_as_today": o.same_as_today,
                                 "low": band[:, 0], "mid": band[:, 1], "high": band[:, 2]}))
    return pd.concat(out, ignore_index=True)


def trailing(prices, crop, preds, d):
    """Self-check per (mandi, h) and widening per h at as_of_date d, using prices on or before d only."""
    tgt = build(prices[prices.date <= d], crop, d)[["mandi", "t", "h", "target"]].dropna(subset=["target"])
    w = preds[(preds.t >= d - WINDOW_DAYS * DAY) & (preds.t + preds.h * DAY <= d)].merge(tgt, on=["mandi", "t", "h"])
    w = w.assign(err_mid=(w.mid - w.target).abs(), err_same=(w.same_as_today - w.target).abs(),
                 gap=np.maximum(w.low - w.target, w.target - w.high))
    grid = pd.MultiIndex.from_product([sorted(preds.mandi.unique()), HORIZONS], names=["mandi", "h"])
    sc = (w.groupby(["mandi", "h"]).agg(model_mae=("err_mid", "mean"), same_as_today_mae=("err_same", "mean"),
                                        rows=("err_mid", "size"))
          .reindex(grid).reset_index())
    sc["rows"] = sc.rows.fillna(0).astype(int)
    sc["ratio"] = sc.model_mae / sc.same_as_today_mae
    sc["passed"] = (sc.rows >= MIN_ROWS) & (sc.ratio < RATIO_MAX)
    cov = w.groupby("h").agg(coverage=("gap", lambda g: (g <= 0).mean()),
                             q=("gap", lambda g: g.quantile(WIDEN_QUANTILE)))
    widen = cov.q.where(cov.coverage < COVERAGE_MIN, 0.0)
    return sc, widen


def run(prices, dates):
    """Model bands for passing rows and the trailing self-check, at each as_of_date in `dates`."""
    bands, scs, widened = [], [], []
    for crop in CROPS:
        preds = predictions(prices, crop)
        at = preds.set_index(["mandi", "t", "h"])
        for d in dates:
            sc, widen = trailing(prices, crop, preds, d)
            scs.append(sc.assign(crop=crop, as_of_date=d))
            widened += [(d, crop, h, v) for h, v in widen.items() if v > 0]
            ok = sc[sc.passed]
            x = at.loc[pd.MultiIndex.from_arrays([ok.mandi, [d] * len(ok), ok.h])].reset_index()
            wv = x.h.map(widen).fillna(0.0)
            bands.append(pd.DataFrame({
                "crop": crop, "mandi": x.mandi, "as_of_date": d, "horizon_days": x.h,
                "price_low": np.round(x.low - wv).astype(int), "price_mid": np.round(x.mid).astype(int),
                "price_high": np.round(x.high + wv).astype(int)}))
    sc = pd.concat(scs, ignore_index=True).rename(columns={"h": "horizon_days"})
    return pd.concat(bands, ignore_index=True), sc, pd.DataFrame(widened, columns=["as_of_date", "crop", "h", "widen"])


TF = {True: "true", False: "false"}
KEYS = ["crop", "mandi", "as_of_date", "horizon_days"]


def write_forecast(path, bands):
    """Replace the fallback rows in `path` that have a model band; uses_baseline = false there."""
    fc = pd.read_csv(path, parse_dates=["as_of_date"]).merge(bands, on=KEYS, how="left", suffixes=("", "_m"))
    hit = fc.price_mid_m.notna()
    for c in ["price_low", "price_mid", "price_high"]:
        fc.loc[hit, c] = fc.loc[hit, c + "_m"].astype(int)
    fc.loc[hit, "uses_baseline"] = False
    fc = fc.drop(columns=[c for c in fc if c.endswith("_m")])
    fc.assign(as_of_date=fc.as_of_date.dt.strftime("%Y-%m-%d"),
              uses_baseline=fc.uses_baseline.map(TF), falling=fc.falling.map(TF)).to_csv(path, index=False)
    print(f"{path}: {int(hit.sum())} model rows of {int((fc.horizon_days > 0).sum())} forecast rows")


def sc_rows(sc):
    out = sc.round({"model_mae": 1, "same_as_today_mae": 1, "ratio": 3}).assign(passed=sc.passed.map(TF))
    return out.assign(as_of_date=out.as_of_date.dt.strftime("%Y-%m-%d"))[["as_of_date"] + SC_COLS]


def main_all():
    runpy.run_path("ml/forecast/baseline.py")  # fresh fallback rows for everything
    s = {k: pd.Timestamp(v) for k, v in json.load(open("data/splits.json")).items()}
    prices = load_prices()
    paths = ["data/forecast_table.csv", "data/forecast_history.csv"]
    dates = sorted(set().union(*(set(pd.read_csv(p, parse_dates=["as_of_date"]).as_of_date) for p in paths)))

    bands, sc, widened = run(prices, dates)
    for path in paths:
        write_forecast(path, bands)
    out = sc_rows(sc)
    out.to_csv("data/selfcheck_history.csv", index=False)
    out[sc.as_of_date == s["as_of_date"]][SC_COLS].to_csv("data/selfcheck.csv", index=False)

    live = sc[sc.as_of_date == s["as_of_date"]]
    print("passed at as_of_date:", live.groupby("crop").passed.sum().astype(int).to_dict(), "of 42 / 30 / 30")
    print("mean passed per history date:", sc[sc.as_of_date != s["as_of_date"]].groupby(["crop", "as_of_date"])
          .passed.sum().groupby("crop").mean().round(1).to_dict())
    print(f"widened (as_of_date, crop, h): {len(widened)} of {len(dates) * len(CROPS) * len(HORIZONS)}")


def main_as_of(d):
    splits = json.load(open("data/splits.json"))
    if not pd.Timestamp(splits["test_start"]) <= d <= pd.Timestamp(splits["test_end"]):
        sys.exit(f"--as-of-date {d.date()} is outside the test block {splits['test_start']}..{splits['test_end']}")
    old = pd.Timestamp(splits["as_of_date"])
    splits["as_of_date"] = d.strftime("%Y-%m-%d")
    with open("data/splits.json", "w") as f:
        json.dump(splits, f, indent=2)
        f.write("\n")
    subprocess.run([sys.executable, "ml/forecast/baseline.py", "--table-only"], check=True)  # fallback for d

    prices = load_prices()
    bands, sc, widened = run(prices[prices.date <= d], [d])
    write_forecast("data/forecast_table.csv", bands)
    out = sc_rows(sc)
    out[SC_COLS].to_csv("data/selfcheck.csv", index=False)

    # selfcheck_history holds every history date plus the live date: drop the old live date (unless it is
    # also a history date) and this date, then add this date's rows.
    hist_dates = set(pd.read_csv("data/forecast_history.csv").as_of_date)
    sch = pd.read_csv("data/selfcheck_history.csv", dtype=str, keep_default_na=False)
    drop = {d.strftime("%Y-%m-%d")} | ({old.strftime("%Y-%m-%d")} - hist_dates)
    sch = pd.concat([sch[~sch.as_of_date.isin(drop)], out.astype(str).replace("nan", "")])
    sch.sort_values(["as_of_date", "crop", "mandi", "horizon_days"], key=lambda c: c.astype(int) if c.name ==
                    "horizon_days" else c).to_csv("data/selfcheck_history.csv", index=False)

    print(f"as_of_date {old.date()} -> {d.date()}")
    print("passed at as_of_date:", sc.groupby("crop").passed.sum().astype(int).to_dict(), "of 42 / 30 / 30")
    print(f"widened (crop, h): {len(widened)} of {len(CROPS) * len(HORIZONS)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of-date", type=pd.Timestamp)
    args = ap.parse_args()
    main_as_of(args.as_of_date) if args.as_of_date is not None else main_all()
