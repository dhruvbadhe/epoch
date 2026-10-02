# ML 2 — decision engine, FPO allocator, backtest

**Team Byte Me · EPOCH 1.0 · PS1 "Sell Smart" · coding ends 10:00 AM, 3 October**

**The product in two lines:** a farmer sends crop, quantity and village on WhatsApp (text or voice, Marathi or Hindi) and gets one answer: where and when to sell for the most money in hand. FPO operators use a web dashboard (Advice, FPO Plan, Evidence) built on the same engine.

**Scope:** Maharashtra; onion, tomato, soybean; 10–15 mandis. Nothing is trained or fetched live during the demo. Every screen and reply shows "prices as of {date}".

**You own:** `/ml/engine`, `config.yaml`, `data/backtest.json`.
**AI:** Claude (Claude Code). Use the strong model for the rules and the backtest.
**Your code is where every number comes from.** WhatsApp, the dashboard and the backtest all call the same `advise()`.

## Your tasks, in order
| # | By | Task | Output |
|---|---|---|---|
| 1 | 1:45 AM | `config.yaml`; `advise()` passing the worked example below | `ml/engine/api.py`, `ml/engine/selftest.py` |
| 2 | 2:30 AM | `advise()` on ML 1's real `forecast_table.csv` | Backend can import it |
| 3 | 5:00 AM | Backtest on `forecast_history.csv` | `data/backtest.json` |
| 4 | 6:15 AM | `fpo_plan()` | Backend can import it |

Until ML 1's files exist, build against a small fake forecast table in the same schema.

## 1. Functions Backend imports
```python
# ml/engine/api.py
def advise(crop, quantity_qtl, village, lot_condition=None, cash_needed_in_days=None,
           blocked_mandis=(), overrides=None, as_of_date=None, forecast=None) -> dict: ...
def fpo_plan(lots, blocked_mandis=(), mandi_cap_qtl_per_day=None,
             collection_centre=None, overrides=None) -> dict: ...
```
- They return the response dicts shown in section 7, without `message` and `storage_tip` (Backend adds those).
- `as_of_date` and `forecast` let the backtest call `advise()` on a past date with a slice of `forecast_history.csv`. Left as None, they mean the live `forecast_table.csv`.
- Load the CSVs and `config.yaml` once, not on every call.
- Raise `ValueError("readable message")` for an unknown crop or village. Never return a half-filled dict.

## 2. Money in hand
For each allowed option (mandi m, sell after d days):
```
sellable   = (1 − spoilage_per_day[crop]) ^ d
distance   = haversine(village, m) × transport.road_factor
transport  = distance × transport.rate_per_km_per_qtl + transport.loading_per_qtl
storage    = storage_cost_per_qtl_per_day[crop] × d
net(m, d)  = price(m, d) × sellable − transport − storage − fees_per_qtl
```
- All values are ₹ per **harvested** quintal. Round only when building the output.
- `price(m, 0)` is the horizon 0 row of the forecast table (the last reported price). Mark the option `stale` if `last_price_date` is more than `confidence.stale_days` before `as_of_date`.
- For d > 0, compute `net_low`, `net_mid`, `net_high` from `price_low`, `price_mid`, `price_high`.

## 3. Two comparisons
| Name | Definition | Used for |
|---|---|---|
| `baseline_today` | Net at the mandi nearest to the village that trades this crop and isn't blocked, d = 0 | The gain shown to the farmer, the backtest, the FPO comparison |
| `best_today` | Highest net over all allowed mandis at d = 0 | The hold test, the break-even price, the hold success rate |

## 4. Allowed options
- d in {0} ∪ `horizons`, and d ≤ this lot's hold limit. The hold limit comes from `hold_limit_days[crop]`: the `answers` entry for `lot_condition`, or `default` when `lot_condition` is None.
- d ≤ `cash_needed_in_days`, if given.
- m trades this crop (per `mandis.csv`) and isn't in `blocked_mandis`.
- For d > 0: the forecast row has `uses_baseline = false`.

## 5. Choosing
1. Compute `baseline_today` and `best_today`.
2. Go through the hold options (d > 0) from highest `net_mid` down. Take the first that passes both:
   - `net_mid − best_today ≥ hold_rule.min_gain_per_qtl`
   - `best_today − net_low ≤ hold_rule.max_downside_per_qtl`
3. One passes → the advice is that hold. None passes → sell today at `best_today`'s mandi.
4. If there were no hold options at all because every forecast row failed the self-check, sell today at `best_today`'s mandi, set confidence to low, and add the note `"forecast not reliable here; compared today's prices only"`.
5. `gain_vs_baseline` = advice net − `baseline_today`. `gain_from_mandi` = `best_today − baseline_today`. `gain_from_waiting` = advice net − `best_today` (0 for sell-today advice).
6. `break_even_price` (hold only) = `(best_today + transport + storage + fees) ÷ sellable` for the chosen mandi and day.
7. **Confidence**, for the chosen (crop, mandi, horizon):
   - high: `uses_baseline` is false, the last report is ≤ `stale_days` old, and (high − low) ÷ mid ≤ `narrow_range_pct`
   - low: `uses_baseline` is true, or the last report is older than `stale_days`
   - medium: everything else
   - For sell-today advice, use the rule for the best rejected hold option, or low if there was none.
8. `options` in the output: every allowed (mandi, day) with its numbers and flags (`stale`, `glut`), sorted by `net_per_qtl` high to low. `why` is the breakdown for the chosen option: `price` (mid), `spoilage_loss` = price × (1 − sellable), `transport`, `storage`, `fees`.
9. `hold_success_rate`: read from `data/backtest.json` for that crop if the file exists, else None.

## 6. Worked example (make this your first self-test)
Made-up inputs: onion, 10 quintals, config defaults. Road distances given directly: Lasalgaon 10 km (nearest), Pimpalgaon 20 km. Today's prices: Lasalgaon 1700, Pimpalgaon 1760. Pimpalgaon at 14 days: low 1800, mid 2000, high 2200, `uses_baseline = false`. No other hold options.

| Step | Value |
|---|---|
| Transport | Lasalgaon 10 × 2 + 20 = 40; Pimpalgaon 20 × 2 + 20 = 60 |
| `baseline_today` | 1700 − 40 = **1660** (Lasalgaon) |
| `best_today` | 1760 − 60 = **1700** (Pimpalgaon) |
| sellable at 14 days | 0.997 ^ 14 = 0.95881 |
| `net_mid` | 2000 × 0.95881 − 60 − 14 = **1844** |
| `net_low`, `net_high` | **1652**, **2035** |
| Hold test | 1844 − 1700 = 144 ≥ 50 ✓; 1700 − 1652 = 48 ≤ 100 ✓ → hold 14 days at Pimpalgaon |
| Gains | vs baseline **184**; from mandi **40**; from waiting **144** |
| `break_even_price` | (1700 + 60 + 14) ÷ 0.95881 = **1850** |
| `why` | price 2000, spoilage_loss 82, transport 60, storage 14, fees 0 |

Then test the flips: `cash_needed_in_days = 3` → sell today at Pimpalgaon (1700). `blocked_mandis = ["Pimpalgaon"]` → sell today at Lasalgaon (1660). Onion with `lot_condition = False` (hold limit 5) → sell today at Pimpalgaon.

## 7. Output shapes
### POST /advise
Request:
```json
{ "crop": "onion",                 // "onion" | "tomato" | "soybean"
  "quantity_qtl": 10,
  "village": "Niphad",
  "lot_condition": null,           // tomato: 0 | 1 | 2 (answer index); onion, soybean: true | false; null = not asked
  "cash_needed_in_days": null,     // 3, 7 or null
  "blocked_mandis": [],
  "overrides": null,
  "lang": "mr" }                   // "mr" | "hi" | "en"
```
Response (the numbers are a made-up example, but they are consistent with the formulas):
```json
{ "action": "hold",                // "hold" | "sell_now"
  "days": 14,
  "mandi": "Pimpalgaon",
  "net_per_qtl": 1844, "net_low": 1652, "net_high": 2035,
  "baseline_today": {"mandi": "Lasalgaon", "net": 1660},
  "best_today": {"mandi": "Pimpalgaon", "net": 1700},
  "gain_vs_baseline": 184,
  "gain_from_mandi": 40,
  "gain_from_waiting": 144,
  "confidence": "medium",          // "high" | "medium" | "low"
  "break_even_price": 1850,        // null for sell_now
  "hold_limit_days": 21,
  "hold_success_rate": null,       // 0-1, or null until the backtest exists
  "prices_as_of": "2026-08-31",
  "uses_baseline": false,
  "assumptions_default": true,
  "why": {"price": 2000, "spoilage_loss": 82, "transport": 60, "storage": 14, "fees": 0},
  "options": [
    { "mandi": "Pimpalgaon", "distance_km": 20, "sell_day": 14,
      "price_low": 1800, "price_mid": 2000, "price_high": 2200,
      "transport_per_qtl": 60, "net_low": 1652, "net_per_qtl": 1844, "net_high": 2035,
      "flags": [] },
    { "mandi": "Pimpalgaon", "distance_km": 20, "sell_day": 0,
      "price_low": 1760, "price_mid": 1760, "price_high": 1760,
      "transport_per_qtl": 60, "net_low": 1700, "net_per_qtl": 1700, "net_high": 1700,
      "flags": [] },
    { "mandi": "Lasalgaon", "distance_km": 10, "sell_day": 0,
      "price_low": 1700, "price_mid": 1700, "price_high": 1700,
      "transport_per_qtl": 40, "net_low": 1660, "net_per_qtl": 1660, "net_high": 1660,
      "flags": ["stale"] }          // "stale" | "glut"
  ],
  "notes": [],
  "storage_tip": "Keep in a dry, well-ventilated place...",   // added by Backend; null for sell_now
  "message": "🟢 *14 दिवस थांबा → ..."                          // added by Backend
}
```
All money values are ₹ per **harvested** quintal, rounded to whole rupees.

### POST /fpo/plan
Request:
```json
{ "lots": [ { "member": "A", "crop": "onion", "quantity_qtl": 40, "village": "Niphad",
              "lot_condition": true, "cash_needed_in_days": 3 } ],
  "blocked_mandis": [],
  "mandi_cap_qtl_per_day": null,     // null = config default
  "collection_centre": null,         // null = config default
  "overrides": null }
```
Response:
```json
{ "collection_centre": "Niphad",
  "assignments": [
    { "member": "A", "crop": "onion", "quantity_qtl": 40, "mandi": "Pimpalgaon", "sell_day": 0,
      "price": 1760, "first_mile": 15, "truck_share": 884, "storage": 0,
      "net_total": 68916, "net_per_qtl": 1723,
      "baseline_today": {"mandi": "Lasalgaon", "net": 1660},
      "reason": "needs cash in 3 days",
      "origin": "via Niphad, shared truck" } ],
  "trucks": [ { "mandi": "Pimpalgaon", "sell_day": 0, "quantity_qtl": 95, "trips": 1, "cost": 2100 } ],
  "total_net": 0, "baseline_total": 0, "gain_vs_baseline": 0,
  "unplaced": [ { "member": "D", "quantity_qtl": 20, "reason": "no mandi with room before its hold limit" } ],
  "prices_as_of": "2026-08-31", "assumptions_default": true }
```
A lot split across two mandis appears as two assignment rows with the same `member`.

### GET /backtest?crop=onion
```json
{ "crop": "onion", "assumptions": "default",
  "test_period": {"start": "2026-06-01", "end": "2026-08-31"},
  "cases_tested": 0, "cases_excluded_by_reason": {"missing real price": 0},
  "avg_gain_per_qtl": null, "median_gain_per_qtl": null,
  "loss_share": null, "worst_loss_per_qtl": null,
  "hold_cases": 0, "hold_success_rate": null,
  "ladder": [ {"policy": "nearest_today", "avg_net": null},
              {"policy": "highest_price_today", "avg_net": null},
              {"policy": "best_net_today", "avg_net": null},
              {"policy": "full_advice", "avg_net": null} ],
  "coverage": [ {"horizon_days": 7, "coverage": null, "n": 0} ],
  "selfcheck": [ {"mandi": "Lasalgaon", "horizon_days": 7, "ratio": null, "rows": 0, "passed": false} ] }
```
A metric that hasn't been measured is `null`, never 0. The UI shows "not evaluated" for null.

## 8. FPO allocator (rule-based; say so, never call it optimal)
All FPO lots ship from one collection centre (`fpo.collection_centre`). Each member pays `fpo.first_mile_per_qtl` to bring their lot there.

1. For each lot, get its allowed options from the same engine with origin = the collection centre and transport per quintal = (trip cost ÷ `truck_capacity_qtl`) + `first_mile_per_qtl`, where trip cost = `truck_fixed_cost` + road distance × `truck_per_km`. Best first. This ranking assumes full trucks.
2. Order the lots: soonest cash deadline first, then shortest hold limit.
3. Give each lot its best option that still has room under the mandi-day cap. If only part fits, split it and send the rest to its next-best option.
4. Group by (mandi, day). Trips = quantity ÷ truck capacity, rounded up. Split each group's real trip cost across its members by weight. The shares must add up to the trip cost exactly.
5. Member's money in hand = quantity × (price × sellable − first mile − storage − fees) − truck share.
6. Baseline: each lot at its own `baseline_today` (nearest mandi to its own village, today, per-quintal transport rate). This is the same number the Advice tab shows.
7. A lot with no option left goes in `unplaced` with the reason.
8. `reason` per assignment, in plain words: "needs cash in 3 days", "short hold limit", "best net", "moved: mandi cap reached", "moved: mandi unavailable".

FPO money in hand won't equal the Advice tab's figure for the same lot, because the origin and transport differ. That's expected; only the baseline matches.

## 9. Backtest (test block only, default assumptions)
For each crop:
1. Take each `as_of_date` in `forecast_history.csv` (every 3rd day) and 5–10 villages from `villages.csv`.
2. Call `advise()` with that date's forecast slice and default lot condition. Lock the decision.
3. Look up the real price at the chosen mandi on the chosen day in `prices_mh.csv` (if that day is missing, use the next day, else the previous; for a 1-day hold only the next day). Compute the real net with the same costs.
4. Compute the real `baseline_today` (nearest mandi, that date) and, for hold advice, the real `best_today`.
5. If a needed real price is missing, exclude the case and count it under its reason.

Write per crop to `data/backtest.json`: average and median gain against `baseline_today`; `loss_share` (cases below baseline) and `worst_loss_per_qtl`; the ladder (average real net of: nearest today → highest price today → best net today → full advice); `hold_cases` and `hold_success_rate` (share of hold advice whose real net beat the real `best_today`); `cases_tested`; `cases_excluded_by_reason`; plus `coverage` and `selfcheck` copied from ML 1's files.

Wording to use everywhere: "simulated on last season's reported prices, at our default assumptions". The cases overlap, so call them "simulated cases" and make no significance claims.

## 10. `config.yaml` (you own it; every number is a placeholder)
```yaml
# EVERY number here is a placeholder until a mentor confirms it.
transport:
  rate_per_km_per_qtl: 2.0
  loading_per_qtl: 20
  road_factor: 1.3              # straight-line km x this = road km
spoilage_per_day:               # share of weight lost per day held
  onion: 0.003
  tomato: 0.04
  soybean: 0.0005
storage_cost_per_qtl_per_day:
  onion: 1.0
  tomato: 3.0
  soybean: 0.5
fees_per_qtl: 0
hold_limit_days:                # by freshness answer; "default" is used when not asked
  tomato:  {default: 4, answers: [4, 2, 0]}      # picked today / 1-2 days ago / 3+ days ago
  onion:   {default: 21, answers: {true: 21, false: 5}}   # cured and ventilated?
  soybean: {default: 21, answers: {true: 21, false: 3}}   # fully dried?
hold_rule:
  min_gain_per_qtl: 50
  max_downside_per_qtl: 100
horizons: [1, 2, 3, 7, 14, 21]
fpo:
  collection_centre: {name: "", lat: null, lon: null}
  first_mile_per_qtl: 15
  truck_capacity_qtl: 100
  truck_fixed_cost: 1500
  truck_per_km: 30
  mandi_cap_qtl_per_day: 200
units:
  bag_kg:   {onion: 50, tomato: 20, soybean: 50}
  crate_kg: {tomato: 20}
forecast:
  target_match_window_days: 1
  min_reported_days: null       # set after the first look at the data
  selfcheck_ratio_max: 0.95
  selfcheck_min_rows: 20
  coverage_widen_below: 0.70
  glut_ratio: 1.5               # last 3 reported days of arrivals / previous 30
confidence:
  stale_days: 3
  narrow_range_pct: 0.15        # (high - low) / mid
parser:
  village_match_threshold: 0.80
```
`overrides` in an API request is a partial copy of this file (same nesting). The engine deep-merges it over the defaults. `assumptions_default` in the response is true only when `overrides` is empty.

## 11. Handoff files
| File | Owner | Read by | What it is |
|---|---|---|---|
| `data/prices_mh.csv` | ML 1 | ML 2, Backend | Clean daily prices: `date, crop, mandi, modal_price, min_price, max_price, arrivals` (₹ per quintal) |
| `data/mandis.csv` | ML 1 | ML 2, Backend | `mandi, lat, lon, crops` (crops separated by `|`). Names match `prices_mh.csv` exactly. |
| `data/splits.json` | ML 1 | ML 2 | `{train_end, val_start, val_end, test_start, test_end, as_of_date}` |
| `data/forecast_table.csv` | ML 1 | ML 2, Backend | The live forecast for the demo date (schema below) |
| `data/forecast_history.csv` | ML 1 | ML 2 | Same schema, one forecast per `as_of_date` across the test block (every 3rd day). The backtest runs on this. |
| `data/selfcheck.csv` | ML 1 | ML 2, Backend | `crop, mandi, horizon_days, model_mae, same_as_today_mae, ratio, rows, passed` |
| `data/coverage.csv` | ML 1 | ML 2, Backend | `crop, horizon_days, coverage, n` (share of test prices inside the low–high range) |
| `data/villages.csv` | Backend | ML 2, Frontend (via API) | `village, name_mr, name_hi, lat, lon` for 20–30 demo villages |
| `config.yaml` | ML 2 | everyone | All assumptions. Placeholders until a mentor confirms. |
| `ml/engine/api.py` | ML 2 | Backend | `advise(...)` and `fpo_plan(...)` |
| `data/backtest.json` | ML 2 | Backend, Frontend (via API) | Backtest results, keyed by crop |
| `docs/api_contract.md` | Backend | Frontend | The API shapes |

**Forecast table schema** (both forecast files):
`crop, mandi, as_of_date, horizon_days, price_low, price_mid, price_high, uses_baseline, last_price_date, glut`
- `horizon_days` is 0, 1, 2, 3, 7, 14 or 21. The **0 row** is today's price: low = mid = high = last reported price on or before `as_of_date`.
- `uses_baseline = true` means the model failed the self-check at that horizon (or it's the simple fallback table): a range is shown but no hold advice is given there.
- `glut` (true/false) is the same on every row of a crop and mandi. Leave it false if there's no arrivals data.

Until a real file exists, its owner commits a fake one at the same path in the same shape.

## Git: how you push
One-time setup:
```bash
git config pull.rebase true
git config rebase.autoStash true
```
Every 30 minutes, or whenever something works:
```bash
git status                      # only your files should be listed
git add ml/engine/ config.yaml data/backtest.json
git commit -m "engine: <what changed>"
git pull
git push
```
Rules:
1. Everyone works on `main`. No branches.
2. Only touch your own folder and the files you own. If you need a change elsewhere, ask the owner.
3. Never `git add .`
4. Don't commit notebooks, `node_modules`, `venv`, `.env`, or raw data downloads.
5. No keys in the repo. Keys live in `.env`.
6. No zips, no code over WhatsApp.

## First prompt for your AI
> Read `docs/ML2_ENGINE.md`. I own only `/ml/engine`, `config.yaml` and `data/backtest.json`. Build task 1 only: `config.yaml` exactly as in section 10, `ml/engine/api.py` with `advise()` following sections 2–5, and `ml/engine/selftest.py` that builds the fake forecast from section 6 and asserts every bold number and all three flips. Run the self-test and show the output. Don't build `fpo_plan` or the backtest yet.
