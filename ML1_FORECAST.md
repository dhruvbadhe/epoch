# ML 1 — data and price forecast (rev 2)

**Team Byte Me · EPOCH 1.0 · PS1 "Sell Smart" · coding ends 10:00 AM, 3 October**

**The product in two lines:** a farmer sends crop, quantity and village on WhatsApp (text or voice, Marathi or Hindi) and gets one answer: where and when to sell for the most money in hand. FPO operators use a web dashboard (Advice, FPO Plan, Evidence) built on the same engine.

**Scope:** Maharashtra; onion, tomato, soybean; 10–15 mandis. Nothing is trained or fetched live during the demo. Every screen and reply shows "prices as of {date}".

**You own:** `/ml/forecast`, and these files in `/data`: `prices_mh.csv`, `mandis.csv`, `splits.json`, `forecast_table.csv`, `forecast_history.csv`, `selfcheck.csv`, `coverage.csv`.
**AI:** ChatGPT.
**Everyone else is blocked on your first two tasks, so ship those before anything else.**

**Changed in this revision:** the dataset is confirmed (Kaggle, schema below); it has no arrivals, so the arrivals features and the "heavy arrivals" flag are gone; a **"price falling" flag** replaces it (column `falling`).

---

## 0. How the product uses your files

Your job is to produce six small files. Every feature below reads them; nobody calls your code directly.

| Product feature | What it reads from you | How it's used |
|---|---|---|
| Money-in-hand comparison across mandis | The **horizon 0 row** (today's price) per crop and mandi; `mandis.csv` coordinates | The engine subtracts transport from each mandi's price and ranks them |
| Sell now or hold | `price_low`, `price_mid`, `price_high` at 1, 2, 3, 7, 14, 21 days | The engine compares waiting with selling today, after spoilage and storage |
| Price range shown to the farmer | `price_low`, `price_high` | "₹1,650 – ₹2,010" in the WhatsApp reply and on the Advice tab |
| Model self-check ("we only say wait where the model beats a simple guess") | `uses_baseline` per row; `selfcheck.csv` | No hold advice is given for a row with `uses_baseline = true`; the Evidence tab shows the table |
| Confidence label (high / medium / low) | `uses_baseline`, `last_price_date`, range width | Computed by the engine from your columns |
| Old-price warning | `last_price_date` | A mandi whose last price is more than 3 days old gets an "old price" chip |
| "Price falling" warning | `falling` | A chip on the mandi table |
| Freshness-aware holding (tomato can only wait 0–4 days) | The 1, 2 and 3-day horizons | Without these, tomato could never get a hold |
| Cash deadline ("need money in 2–3 days") | The 1, 2 and 3-day horizons | Options later than the deadline are removed |
| Forecast chart on the dashboard | `forecast_table.csv` plus `prices_mh.csv` | Past prices as a line, the forecast as a shaded band |
| Rupee backtest (the proof) | `forecast_history.csv`, `prices_mh.csv`, `splits.json` | ML 2 replays the test block: your forecast at each past date, then the real price |
| Range report card | `coverage.csv` | "The real price fell inside our range X% of the time" |
| FPO plan and "mandi unavailable" re-routing | Same forecast table | The allocator calls the same engine for every lot |

---

## 1. Your tasks, in order

| # | By | Task | Output |
|---|---|---|---|
| 1 | 1:45 AM | First look at the data; clean it; pick the mandis | `prices_mh.csv`, `mandis.csv`, `splits.json` |
| 2 | 2:00 AM | Simple fallback forecast ("last price with a band") for the demo date **and** for every test date | `forecast_table.csv`, `forecast_history.csv` (every row `uses_baseline = true`) |
| 3 | 2:45 AM | Quantile model for onion; self-check | Replace both forecast files in place; `selfcheck.csv` |
| 4 | 5:00 AM | All three crops | Same files |
| 5 | 6:30 AM | Coverage on the test block; `falling` flag; range widening if needed | `coverage.csv`, `falling` column |

Mac setup: `brew install libomp` before installing LightGBM or XGBoost.

---

## 2. The dataset

**Source:** Kaggle, "Daily Market Prices of Commodity India (2001–2026)" (`khandelwalmanas/daily-commodity-prices-india`). Take the Parquet files, and only recent years if it's split. Put downloads in `data/raw/` (not committed).

**Its columns:** `State, District, Market, Commodity, Variety, Grade, Arrival_Date, Min_Price, Max_Price, Modal_Price, Commodity_Code`. Prices are ₹ per quintal. **There is no arrivals quantity.**

| Their column | Our column | Note |
|---|---|---|
| `Arrival_Date` | `date` | The date of the price record |
| `Commodity` | `crop` | Renamed to `onion`, `tomato`, `soybean` |
| `Market` | `mandi` | One clean spelling per mandi |
| `Modal_Price`, `Min_Price`, `Max_Price` | `modal_price`, `min_price`, `max_price` | |

**`data/prices_mh.csv` columns:** `date, crop, mandi, district, variety, grade, modal_price, min_price, max_price`

Fallbacks if this file fails (15-minute limit): Kaggle `ishankat/daily-wholesale-commodity-prices-india-mandis`; then data.gov.in "Variety-wise Daily Market Prices"; then agmarknet.gov.in manual export.

### First look (run before cleaning)
Read with DuckDB or pyarrow and filter while reading; don't load the whole file. For `State` = Maharashtra, print:
1. the distinct `Commodity` names containing "onion", "tomato" or "soya"
2. per commodity and market: reported days since January 2023, first and last date
3. per commodity: varieties and grades with row counts
4. the last date in the Maharashtra rows

### Cleaning rules
- Keep only the plain commodity for each crop (for example "Onion", not "Onion Green"; soybean may be spelt "Soyabean"). Write down the exact names kept.
- **Variety and grade:** a mandi can have several rows per day. For each crop and mandi, keep the single variety-and-grade pair with the most rows. Don't average across them. Save the choice in `ml/forecast/variety_choice.csv`.
- Drop rows where the modal price is 0, missing, or outside that day's [min, max]. Drop exact duplicates. If two rows remain for the same crop, mandi and date, keep the first and count how often it happens.
- Keep missing days missing. Never fill with zero, and never forward-fill.
- Keep a (crop, mandi) series only if it has enough reported days in the train block. Set `forecast.min_reported_days` after the first look and tell ML 2 the value.
- Delete the raw download once `prices_mh.csv` is pushed.

### `mandis.csv`
`mandi, district, lat, lon, crops` (crops separated by `|`). 10–15 mandis in total; each crop only at mandis that passed the rule above. Take coordinates from a map by hand, using the district to find the right place, and check each one. Don't use coordinates an AI tool writes without checking.
Candidates to look for (confirm against the data): onion at Lasalgaon, Pimpalgaon, Nashik, Pune, Solapur; tomato at Pune, Narayangaon, Nashik, Pimpalgaon; soybean at Latur, Akola, Amravati, Washim, Nagpur.

### `splits.json`
`{train_end, val_start, val_end, test_start, test_end, as_of_date}`. Three time blocks in order, train → validation → test, with a 21-day gap between blocks. The test block is the most recent season (about the last 3 months of data); validation is the 2–3 months before it. `as_of_date` is the demo's "today": the last date in the data, unless the team picks a date inside the test block where a real hold example exists.

---

## 3. Missing-day rules (use these everywhere)

- "Same as today" at date t = the last reported price on or before t.
- Lag features use the last reported price on or before the lag date. Averages and spread use the reported days inside the window.
- Target at horizon h = the modal price on day t + h. If that day is missing, use day t + h + 1, else day t + h − 1. **For h = 1, only t + 2 is allowed as the fallback** (t + 0 is today's price and would make the target equal the baseline). If no price is found, drop the row.

---

## 4. Simple fallback forecast (ship this first)

For each crop, mandi and horizon h in {1, 2, 3, 7, 14, 21}:
- mid = last reported price.
- low and high = last price × the 10th and 90th percentile of past h-day price ratios (price at t + h ÷ price at t) for that crop and mandi in the train block.
- Add the **horizon 0 row**: low = mid = high = last reported price.
- `uses_baseline = true` on every row.

Write `forecast_table.csv` for `as_of_date`, and `forecast_history.csv` for every 3rd day of the test block. ML 2's backtest reads the history file, so it has to exist early even in this simple form.

---

## 5. The model

- **Rows:** one per (mandi, date t, horizon h). Target by the rule in section 3.
- **Model:** LightGBM (or XGBoost) with the quantile objective, fitted three times: 10th, 50th and 90th percentile. One pooled model per crop, with mandi and horizon as features.
- **Features, all known at t:**
  - price 1, 3, 7 and 14 days back
  - 7- and 30-day average; 7-day spread (max − min)
  - latest price ÷ 7-day average
  - today's (max − min) ÷ modal, as a sign of an unsettled market
  - `days_since_last_report`
  - week of year; sine and cosine of day-of-year
  - mandi; horizon
  - if time allows: yesterday's price at the 2 nearest mandis for the same crop
- **No arrivals features** (the data has none).
- **Sort the three predictions in every row** so low ≤ mid ≤ high.
- Train on the train block. Choose settings on validation. Touch the test block only for the final numbers.
- For `forecast_history.csv`, predict at each test date using only data up to that date. The model itself can stay as trained on the train block.

---

## 6. Self-check (per crop, mandi and horizon, on validation)

- ratio = MAE of `price_mid` ÷ MAE of "same as today".
- Pass = ratio < `forecast.selfcheck_ratio_max` (0.95) **and** at least `forecast.selfcheck_min_rows` (20) rows.
- Fail → that row keeps the simple fallback values and `uses_baseline = true`. Other horizons at the same mandi aren't affected.
- Write every combination to `selfcheck.csv`: `crop, mandi, horizon_days, model_mae, same_as_today_mae, ratio, rows, passed`.
- Also compute the error of "same week last year" per crop and horizon, for the pitch.

**After this step, tell the team** how many (crop, mandi, horizon) combinations passed, and name one date and mandi in the test block where a 7- or 14-day onion hold passes. The demo needs one real hold example. If none exists, say so at once.

---

## 7. Coverage, the "price falling" flag, widening

- **`coverage.csv`:** on the test block, per crop and horizon: `crop, horizon_days, coverage, n`, where coverage is the share of real prices inside [low, high].
- **`falling`:** true when the latest reported price ÷ the mean of the last 7 reported prices (including the latest) is below `forecast.falling_ratio` (0.90, a placeholder in `config.yaml`). Needs at least 4 reported prices in the last 10 days, otherwise false. Same value on every row of that crop and mandi. In the history file, compute it as of each `as_of_date`.
  It's a price signal only. Nobody may describe it as demand or supply.
- **Optional, cut first if short of time:** if validation coverage is below 70%, widen both ends per crop and horizon by the 80th percentile of max(low − actual, actual − high) on validation, then report test coverage after widening.

---

## 8. Files you hand over

| File | Read by | Columns |
|---|---|---|
| `data/prices_mh.csv` | ML 2, Backend | `date, crop, mandi, district, variety, grade, modal_price, min_price, max_price` |
| `data/mandis.csv` | ML 2, Backend | `mandi, district, lat, lon, crops` |
| `data/splits.json` | ML 2 | `train_end, val_start, val_end, test_start, test_end, as_of_date` |
| `data/forecast_table.csv` | ML 2, Backend | forecast schema below, for `as_of_date` |
| `data/forecast_history.csv` | ML 2 | forecast schema below, one forecast per `as_of_date` (every 3rd day of the test block) |
| `data/selfcheck.csv` | ML 2, Backend | `crop, mandi, horizon_days, model_mae, same_as_today_mae, ratio, rows, passed` |
| `data/coverage.csv` | ML 2, Backend | `crop, horizon_days, coverage, n` |

**Forecast schema (both forecast files):**
`crop, mandi, as_of_date, horizon_days, price_low, price_mid, price_high, uses_baseline, last_price_date, falling`
- `horizon_days` is 0, 1, 2, 3, 7, 14 or 21. The 0 row is today's price.
- `uses_baseline = true`: the model failed the self-check at that horizon, or it's the simple fallback table. A range is shown but no hold advice is given there.
- Dates as `YYYY-MM-DD`. Prices rounded to whole rupees. `true` / `false` in lower case.

Files you read but don't own: `config.yaml` (ML 2), for `forecast.*` thresholds and `horizons`.

---

## 9. Self-test before each push

A script `ml/forecast/check.py` that asserts:
- every forecast row has low ≤ mid ≤ high and all three are positive
- every (crop, mandi) in the table is in `mandis.csv`, and every one has a horizon 0 row and all six other horizons
- every `as_of_date` in the history file is inside the test block
- no forecast row was built from data after its `as_of_date`
- no `last_price_date` is after its `as_of_date`

---

## 10. What to say, and not say, about the forecast

- Say: "a range forecast, checked against 'price stays the same' at every horizon; we show where it fails".
- Don't say: any accuracy number not measured tonight; "predicts demand"; "real-time"; that it can foresee export bans or floods.
- If asked why not an LSTM: daily mandi data is small and gappy; a quantile gradient-boosting model gives ranges cheaply, and what matters is whether it beats the simple baseline.

---

## 11. Git: how you push

One-time setup:
```bash
git config pull.rebase true
git config rebase.autoStash true
```
Every 30 minutes, or whenever something works:
```bash
git status                      # only your files should be listed
git add ml/forecast/ data/prices_mh.csv data/mandis.csv data/splits.json data/forecast_table.csv data/forecast_history.csv data/selfcheck.csv data/coverage.csv
git commit -m "forecast: <what changed>"
git pull
git push
```
Rules:
1. Everyone works on `main`. No branches.
2. Only touch `/ml/forecast` and the data files you own. If you need a change elsewhere, ask the owner.
3. Never `git add .`
4. Don't commit notebooks, `venv`, `.env`, or anything in `data/raw/`.
5. No zips, no code over WhatsApp.

---

## 12. First prompt for your AI

> I'm building the price forecast for a hackathon project. I own only `/ml/forecast` and the data files listed in section 8 of the document below. Read it, then build the "first look" from section 2 only: a script `ml/forecast/first_look.py` that reads the Kaggle Parquet files in `data/raw/` with DuckDB, filters to State = Maharashtra while reading, and prints the four tables listed under "First look". Don't clean or model anything yet. [paste this file]

Second prompt, after you've read the first-look output:

> Now build `ml/forecast/clean.py` following the cleaning rules in section 2, using these commodity names: [names]. Write `data/prices_mh.csv` and `ml/forecast/variety_choice.csv`, and print reported days per crop and mandi in the train block so I can choose the mandis.
