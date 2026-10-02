"""Feature rows for the quantile model (ML1_FORECAST.md sections 3 and 5).

One row per (mandi, calendar day t, horizon h). Every feature uses prices on or before t only.
Self-test (leak check): venv/bin/python ml/forecast/features.py
"""
import numpy as np
import pandas as pd

HORIZONS = [1, 2, 3, 7, 14, 21]
FEATURES = ["mandi", "h", "same_as_today", "lag1", "lag3", "lag7", "lag14", "avg7", "avg30", "spread7",
            "price_to_avg7", "today_range", "days_since_last_report", "week", "doy_sin", "doy_cos"]


def load_prices(path="data/prices_mh.csv"):
    return pd.read_csv(path, parse_dates=["date"])


def build(prices, crop, end):
    """Rows for every day from each mandi's first report to `end`. `target` / `target_date` follow
    section 3: t+h, else t+h+1, else t+h-1 (h = 1: only t+2); NaN when none is reported."""
    out = []
    for mandi, g in prices[prices.crop == crop].groupby("mandi"):
        g = g.set_index("date").sort_index()
        days = pd.date_range(g.index.min(), end, name="t")
        p = g.modal_price.reindex(days).astype(float)  # NaN on days with no report
        last = p.ffill()  # last reported price on or before each day
        last_date = pd.Series(days.where(p.notna()), index=days).ffill()
        f = pd.DataFrame({
            "mandi": mandi,
            "same_as_today": last,
            "last_price_date": last_date,
            **{f"lag{k}": last.shift(k) for k in (1, 3, 7, 14)},
            # Rolling over the calendar window; NaN days are skipped, so these use reported days only.
            "avg7": p.rolling(7, min_periods=1).mean(),
            "avg30": p.rolling(30, min_periods=1).mean(),
            "spread7": p.rolling(7, min_periods=1).max() - p.rolling(7, min_periods=1).min(),
            "today_range": ((g.max_price - g.min_price) / g.modal_price).reindex(days).ffill(),
            "days_since_last_report": (days.to_series() - last_date).dt.days,
            "week": days.isocalendar().week.astype(int).to_numpy(),
            "doy_sin": np.sin(2 * np.pi * days.dayofyear / 365.25),
            "doy_cos": np.cos(2 * np.pi * days.dayofyear / 365.25),
        }, index=days)
        f["price_to_avg7"] = f.same_as_today / f.avg7
        for h in HORIZONS:
            offsets = [h, h + 1] + ([h - 1] if h > 1 else [])
            target = pd.Series(np.nan, index=days)
            target_date = pd.Series(pd.NaT, index=days)
            for o in reversed(offsets):  # first offset in the list wins
                y = p.shift(-o)
                target = y.where(y.notna(), target)
                target_date = target_date.mask(y.notna(), days.to_series() + pd.Timedelta(days=o))
            out.append(f.assign(h=h, target=target, target_date=target_date))
    rows = pd.concat(out).reset_index()
    return rows[rows.same_as_today.notna()].reset_index(drop=True)


if __name__ == "__main__":
    prices = load_prices()
    cut = pd.Timestamp("2024-06-15")
    full = build(prices, "onion", prices.date.max())
    trunc = build(prices[prices.date <= cut], "onion", cut)
    cols = ["mandi", "t", "h"] + [c for c in FEATURES if c not in ("mandi", "h")] + ["last_price_date"]
    a = full[full.t <= cut][cols].reset_index(drop=True)
    b = trunc[cols].reset_index(drop=True)
    pd.testing.assert_frame_equal(a, b)
    # Target rule spot checks.
    r = full.dropna(subset=["target"])
    off = (r.target_date - r.t).dt.days
    assert ((off >= r.h - 1) & (off <= r.h + 1)).all() and off[r.h == 1].isin([1, 2]).all()
    print(f"features ok: {len(full)} rows, features on or before t identical with data cut at {cut.date()}")
