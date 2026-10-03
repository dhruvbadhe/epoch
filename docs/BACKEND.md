# Backend — API, WhatsApp, voice, parser, replies (and integrator)

**Team Byte Me · EPOCH 1.0 · PS1 "Where and When to Sell" · coding ends 10:00 AM, 3 October**

**The product in two lines:** a farmer sends crop, quantity and village on WhatsApp (text or voice, Marathi or Hindi) and gets one answer: where and when to sell for the most money in hand. FPO operators use a web dashboard (Advice, FPO Plan, Evidence) built on the same engine.

**Scope:** Maharashtra; onion, tomato, soybean; 10–15 mandis. Nothing is trained or fetched live during the demo. Every screen and reply shows "prices as of {date}".

**You own:** `/backend` (including `/backend/whatsapp`), `docs/api_contract.md`, `data/villages.csv`, `requirements.txt`, `CLAUDE.md`, `AGENTS.md`, `.gitignore`, `README.md`.
**AI:** Claude (Claude Code).
**You're also the integrator:** you tag working versions and chase mismatches between parts.

## Your tasks, in order
| # | By | Task |
|---|---|---|
| 0 | now | `.gitignore`, `CLAUDE.md`, `AGENTS.md`, `docs/api_contract.md`, the four role files in `/docs`. Push. |
| 1 | 1:30 AM | FastAPI app with every endpoint returning the example JSON from the contract; CORS on. Frontend can start. |
| 2 | 2:30 AM | `villages.csv`; `/advise` calling ML 2's real `advise()`; WhatsApp text in → `/message` → reply out. Tag `ok-0230`. |
| 3 | 5:30 AM | Conversation flow (confirm, freshness, cash); voice note → text; parser units, digits and village matching |
| 4 | 6:30 AM | Formatted replies with tips; real `/fpo/plan`, `/backtest`, `/forecast`, `/queries`; input errors |

## 1. Layout
```
/backend
  main.py          FastAPI app and routes only
  engine_api.py    imports ml.engine.api; falls back to fake JSON if it isn't there yet
  parser.py        text → crop, quantity_qtl, village (+ what was guessed)
  state.py         per-sender conversation memory (in-memory dict)
  replies.py       templates → Marathi / Hindi / English text
  tips.py          storage tips per crop and language
  speech.py        audio file → text
  data_loader.py   loads CSVs and config once at startup
  fake/            example JSON per endpoint
  /whatsapp        the adapter for whichever integration works
```
Run: `uvicorn backend.main:app --port 8000` (no auto-reload and one worker during the demo, or conversation memory is lost).

## 2. The API
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

**How `/advise` is built:** call `advise()` from `ml/engine/api.py`, then add `storage_tip` (hold only) and `message` (from `replies.py`). Pass `overrides` straight through. A `ValueError` from the engine becomes a 400 with its message.

## 3. One handler for every channel
```python
def handle_message(sender: str, text: str) -> dict:   # returns {"reply", "state", "parsed"}
```
The WhatsApp adapter and `/message` both call this. The adapter only moves messages; it holds no logic.

## 4. Conversation flow
At most three questions, each only when it can change the answer.

| State | Bot sends | Asked when | Next |
|---|---|---|---|
| start | (parse the message) | | → confirm, or straight on |
| `awaiting_confirm` | "20 पोती कांदा (≈ 10 क्विंटल), निफाड. बरोबर? 1) हो 2) नाही" | Always for voice notes. For text, only if a unit or village was guessed, or something is missing. | yes → next; no → "please send it again" |
| `awaiting_freshness` | The crop's freshness question | Only if `advise()` with the default hold limit says hold | answer → `lot_condition` |
| `awaiting_cash` | "पैसे कधीपर्यंत हवेत? 1) 2–3 दिवसांत 2) या आठवड्यात 3) घाई नाही" | Only if `advise(cash_needed_in_days=3)` gives a different action, mandi or day than no deadline | 1 → 3 days, 2 → 7 days, 3 → none |
| `done` | The advice | Always | reset |

- A reply of "1", "2" or "3" (ASCII or Devanagari digit, text or voice) answers the open question.
- If the first message already says when money is needed (a money word such as पैसे, पैसा, cash, urgent, लगेच, तातडीने next to आज, उद्या, "2 दिवस", "या आठवड्यात"), set the deadline and skip that question.
- State times out after 30 minutes; a new crop message restarts it.

**Freshness questions** (the answer index or yes/no becomes `lot_condition`):
| Crop | Question | Answers |
|---|---|---|
| Tomato | When was it picked? 1) today 2) 1–2 days ago 3) 3+ days ago | `lot_condition` = 0, 1 or 2 |
| Onion | Is it dried (cured) and kept in ventilated storage? 1) yes 2) no | true / false |
| Soybean | Is the grain fully dried? 1) yes 2) no | true / false |

## 5. Parser
- **Digits:** convert Devanagari digits (० १ २ ३ ४ ५ ६ ७ ८ ९) to ASCII first.
- **Number words:** a small table for the common ones in Marathi and Hindi (एक/दोन/तीन/चार/पाच/दहा/वीस/पन्नास/शंभर; एक/दो/तीन/चार/पाँच/दस/बीस/पचास/सौ), because speech-to-text often writes numbers as words.
- **Crop:** कांदा, कांदे, प्याज, kanda, pyaz, onion → onion. टोमॅटो, टमाटर, tamatar, tomato → tomato. सोयाबीन, soyabean, soybean → soybean.
- **Units:** क्विंटल / quintal / qtl as is. टन / ton / tonne × 10. किलो / kilo / kg ÷ 100. पोती / गोणी / बोरी / bag and क्रेट / कॅरेट / crate use `units.bag_kg` and `units.crate_kg` for that crop. No unit → assume quintals and mark it as guessed.
- **Village:** fuzzy-match (Python `difflib`) against both spellings in `villages.csv`. Below `parser.village_match_threshold`, the confirm message offers the top 3 as "1) … 2) … 3) … 4) other"; "other" replies that the village isn't covered yet.
- **Yes / no:** हो, होय, हां, हाँ, ho, haan, ha, yes → yes. नाही, नहीं, nahi, nai, no → no.
- Anything guessed forces the confirm step, and the confirm message shows the converted quantity.
- A crop outside our three → reply with the three supported crops. A missing quantity → ask for it.

## 6. Replies
Marathi, hold:
```
🟢 *{days} दिवस थांबा → {mandi}*
💰 हातात अंदाजे ₹{net}/क्विंटल (₹{low}–₹{high})
📈 आज जवळच्या बाजारापेक्षा ₹{gain} जास्त
⚠️ भाव ₹{breakeven} च्या वर असेल तरच जा. निघण्यापूर्वी खात्री करा
📦 साठवण: {tip}
🗓 {date} च्या भावांनुसार · खात्री: {confidence}
```
Marathi, sell now:
```
🔴 *आजच विका → {mandi}*
💰 हातात अंदाजे ₹{net}/क्विंटल
📈 आज जवळच्या बाजारापेक्षा ₹{gain} जास्त
🗓 {date} च्या भावांनुसार · खात्री: {confidence}
```
Hindi, hold:
```
🟢 *{days} दिन रुकें → {mandi}*
💰 हाथ में लगभग ₹{net}/क्विंटल (₹{low}–₹{high})
📈 आज पास की मंडी से ₹{gain} ज़्यादा
⚠️ भाव ₹{breakeven} से ऊपर हो तभी जाएँ. निकलने से पहले पक्का करें
📦 भंडारण: {tip}
🗓 {date} के भाव के अनुसार · भरोसा: {confidence}
```
Hindi, sell now:
```
🔴 *आज ही बेचें → {mandi}*
💰 हाथ में लगभग ₹{net}/क्विंटल
📈 आज पास की मंडी से ₹{gain} ज़्यादा
🗓 {date} के भाव के अनुसार · भरोसा: {confidence}
```
- `{gain}` is `gain_vs_baseline`; `{breakeven}` is `break_even_price`; `{net}`, `{low}`, `{high}` are `net_per_qtl`, `net_low`, `net_high`.
- If `gain_vs_baseline` is 0, replace the 📈 line with "जवळचा बाजारच सर्वोत्तम आहे" / "पास की मंडी ही सबसे अच्छी है".
- If confidence is low because the forecast failed its check, add: "ℹ️ येथे अंदाज विश्वासार्ह नाही; फक्त आजच्या भावांची तुलना केली" / "ℹ️ यहाँ अनुमान भरोसेमंद नहीं; सिर्फ़ आज के भाव की तुलना की".
- If `hold_success_rate` isn't null, add to hold replies: "मागील हंगामात थांबण्याचा सल्ला {pct}% वेळा फायद्याचा ठरला" / "पिछले सीज़न में रुकने की सलाह {pct}% बार फ़ायदेमंद रही".
- Confidence words: high जास्त / ज़्यादा, medium मध्यम, low कमी / कम.
- English templates in the same shape, for judges.
- Numbers always come from the engine. No language model writes the reply.
- **A Marathi and a Hindi speaker must read every template before the demo.**

**Storage tips** (general guidance; check against an agricultural source before the pitch, then translate):
| Crop | Tip |
|---|---|
| Onion | Keep in a dry, well-ventilated place off the ground; don't pile deep; remove rotting or sprouting bulbs. |
| Tomato | Keep in shade, in crates not sacks; don't stack deep; move it in the cool hours. |
| Soybean | Store only fully dried grain, in clean dry bags, off the floor and away from walls. |

## 7. WhatsApp and voice
- Use whichever integration is already working (the official Cloud API test number, or the QR-linked Node bridge). Don't switch again.
- The adapter: message in → `handle_message` (or POST `/message`) → send the reply. Ignore group chats, status updates and the bot's own messages. Reply only to the team's test numbers. Skip a message ID you've already handled.
- Voice: download the audio, send it to the speech-to-text service with the language set to Marathi or Hindi, then treat the transcript as text. Test with a real recording that has a number and a village name **before 2:30 AM**; this is the riskiest required piece.
- If the official API is used, verify the webhook signature. Keys and tokens live in `.env`; commit only `.env.example`.
- Keep a screen recording of a working exchange as the backup for judging.
- In the pitch, say which integration it is. A real deployment would use the official WhatsApp Business API.

## 8. `villages.csv`
`village, name_mr, name_hi, lat, lon` for 20–30 villages near the chosen mandis. Take coordinates from a map by hand; don't trust coordinates an AI tool writes without checking them.

## 9. Logging
Append each query and reply to `backend/queries.log` (JSON lines; not committed). `GET /queries` returns the last 20 with the sender masked to its last 4 digits.

## 10. Assumptions (`config.yaml`, owned by ML 2; you only read it)
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

## 12. Integrator checks at each checkpoint
- The same inputs give the same number on WhatsApp and on the Advice tab.
- The FPO Plan baseline per lot equals the Advice tab's `baseline_today`. FPO money in hand differs by design (collection centre, shared truck).
- Then: `git tag ok-0230 && git push --tags` (use the time in the tag).

## Git: how you push
One-time setup:
```bash
git config pull.rebase true
git config rebase.autoStash true
```
Every 30 minutes, or whenever something works:
```bash
git status                      # only your files should be listed
git add backend/ docs/ data/villages.csv requirements.txt CLAUDE.md AGENTS.md .gitignore README.md
git commit -m "backend: <what changed>"
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
> Read `docs/BACKEND.md`. I own only `/backend` and the root files listed there. Build task 1 only: `backend/main.py` with every endpoint in section 2 returning the example JSON from that section (stored under `backend/fake/`), CORS open to `http://localhost:3000`, and a 400 error shape for bad input. Run it and show `curl` output for `/advise` and `/backtest`. Don't build the parser or WhatsApp yet.
