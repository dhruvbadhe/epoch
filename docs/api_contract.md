# SahiDaam — API contract

Owner: Backend. Save as `docs/api_contract.md`. Don't change a shape without telling Frontend and ML 2.

Base URL in development: `http://localhost:8000`. CORS is open to `http://localhost:3000`.

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

### POST /message  (called by the WhatsApp adapter)
Request: `{ "sender": "9198xxxxxxx", "text": "20 poti kanda Niphad" }`, or a multipart upload with `sender` and an `audio` file.
Response: `{ "reply": "...", "state": "awaiting_confirm", "parsed": {"crop": "onion", "quantity_qtl": 10, "village": "Niphad"} }`
`state` is one of `awaiting_confirm`, `awaiting_freshness`, `awaiting_cash`, `done`.

### GET /forecast?crop=onion&mandi=Lasalgaon
```json
{ "crop": "onion", "mandi": "Lasalgaon", "prices_as_of": "2026-08-31",
  "history": [ {"date": "2026-08-01", "price": 1650} ],
  "forecast": [ {"horizon_days": 7, "date": "2026-09-07", "price_low": 1600, "price_mid": 1750,
                 "price_high": 1900, "uses_baseline": false} ] }
```

### GET /queries
`[ {"time": "2026-10-03T02:10:00+05:30", "sender": "…4521", "text": "...", "reply": "..."} ]` (last 20; sender masked)

### GET /mandis · GET /villages · GET /config
`[ {"mandi": "Lasalgaon", "lat": 0, "lon": 0, "crops": ["onion"]} ]` · `[ {"village": "Niphad", "name_mr": "निफाड", "lat": 0, "lon": 0} ]` · the `config.yaml` contents as JSON.

### Errors
Any bad input returns HTTP 400 with `{ "error": "short readable message", "field": "village" }`. Never a stack trace.

### How the backend implements this (nothing above changed; these only fill gaps)
- **Errors:** `field` is `null` when no single field is at fault (bad JSON, or a `ValueError` raised by the engine). A field inside a list uses a dotted path: `"lots.0.village"`. Other statuses use the same body: 404 / 405 for a wrong path or method, 500 for a server bug, 503 when the engine is required but missing.
- **`X-SellSmart-Engine` response header** on `/advise` and `/fpo/plan`: `real` or `fake`. While it is `fake`, the numbers are the examples in this file, `notes` carries `"Example data: the decision engine is not connected yet"`, and `message` ends with a 🧪 line.
- **`GET /health`** (new, for the integrator): `{ "status": "ok", "engine": {"mode", "advise", "fpo_plan", "import_error"}, "data": {file: "real" | "fake" | "missing"}, "config_missing_keys": ["parser.village_match_threshold"], "speech_to_text": "sarvam" | "groq" | "openai" | null }`. `config_missing_keys` lists keys the backend needs that `config.yaml` lacks; the copy in this file is used for those.
- **`/advise`:** `village` is a name from `GET /villages` (any of its three spellings, any case). `lot_condition` is checked per crop: tomato takes 0 | 1 | 2 only, onion and soybean take `true` | `false` only. `blocked_mandis` must be names from `GET /mandis`. `cash_needed_in_days` is 3 or 7 from our own screens; any whole number ≥ 0 is passed to the engine. `hold_success_rate` is filled from `data/backtest.json` when the engine leaves it null.
- **`/fpo/plan`:** `collection_centre` is `null`, a village name from `GET /villages`, or `{ "name", "lat", "lon" }`. The engine always receives `null` or the `{name, lat, lon}` shape used in `config.yaml`.
- **`/message`:** for an audio upload the response also has `"transcript"` (the text that was heard, or `null` if speech-to-text failed; the `reply` then asks the farmer to type it).
- **`/queries`:** newest first.
- **`/villages`:** each row also has `name_hi`. **`/mandis`:** optional `?crop=onion` filter. **`/forecast`:** optional `&days=60` for how much history to return; `forecast` holds horizons 1–21 only (today's price is the last `history` point).
- **`/config`:** YAML `true` / `false` keys become the strings `"true"` / `"false"` (JSON keys must be strings): `hold_limit_days.onion.answers = {"true": 21, "false": 5}`.
- **`/backtest`:** a crop that hasn't been backtested returns the same shape with every metric `null`. `selfcheck` and `coverage` come from ML 1's `data/selfcheck.csv` and `data/coverage.csv` when `backtest.json` doesn't carry them.

## Assumptions (`config.yaml`, also returned by GET /config)
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
