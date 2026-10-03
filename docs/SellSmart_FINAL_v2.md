# SahiDaam — FINAL build spec (rev 2)

**Team Byte Me · EPOCH 1.0 · PS1 · locked 12:15 AM, 3 October · rev 2**

This file replaces rev 1, the earlier context file and the blueprint wherever they disagree. Formulas, data sources and git rules not repeated here stay as in `SahiDaam_Project_Context.md`. **No more scope changes after this.** Rev 2 only tightens definitions and rules; it adds no features. Coding ends 10:00 AM.

**Pitch:** SahiDaam tells a farmer where and when to sell for the most money in hand, how sure we are, and what to check before the crop leaves, on WhatsApp, in Marathi or Hindi. FPOs get a dashboard that plans the whole group's produce.

---

## 0. What changed in rev 2 (read this first if you read rev 1)

| # | Change | Why | Where | Owner |
|---|---|---|---|---|
| 1 | Two named comparisons: `baseline_today` (nearest mandi today) for the rupee gain; `best_today` (best net today) for the hold test, break-even and hold success rate | A hold to a far mandi was getting credit for the distance, not the waiting | §5, §8, §9 | ML 2 |
| 2 | Hold rule checks hold options in order and takes the first that passes, instead of only the top one | A safe 7-day hold was being thrown away when a risky 21-day hold ranked first | §5 | ML 2 |
| 3 | Self-check per crop, mandi **and horizon**; pass only if ratio < 0.95 with enough rows | "Same as today" is hardest to beat at 1–3 days; a pooled check let weak short horizons through | §5, §7 | ML 1 |
| 4 | Missing-day rules for features, target, baseline and backtest | Mandis skip days; deciding this at 2 AM costs the checkpoint | §7, §8 | ML 1 |
| 5 | FPO trucks leave from one collection centre; first-mile cost added; FPO numbers labelled | Trip distance had no origin | §6 | ML 2 |
| 6 | Evidence tab labelled "at default assumptions"; banner if the drawer was edited | The drawer changes Advice but not the precomputed backtest | §8, §10 | Frontend |
| 7 | Parser: Devanagari digits, bags / crates / tonnes / kg, fuzzy village match | Farmers won't type "20 quintal" | §4 | Backend |
| 8 | Quantiles sorted per row; optional range widening on validation | Separate fits can cross; GBM ranges usually cover less than they claim | §7 | ML 1 |
| 9 | Persistence-band forecast table ships first, in the final schema | Unblocks engine, API and frontend before LightGBM is ready | §7, §12 | ML 1 |
| 10 | Judge Q&A prep; backtest cases called "simulated cases", no significance claims | Cases overlap, so they aren't independent | §14, §15 | All |

---

## 1. Decisions on every idea

| Idea | Decision | What we actually build |
|---|---|---|
| 1. Demand-driven routing ("real-time consumer demand") | **Keep, reworded** | We have no demand data. We have arrivals (supply) and prices. Build a **glut flag**: a mandi is marked "heavy arrivals" when recent arrivals are well above its normal. Never say "real-time demand". |
| 2. Spoilage prevention advice | **Keep, small** | One short storage tip per crop, added to the reply only when the advice is "hold". A static table, no model. |
| 3. Waste recovery / upcycling | **Cut** | Outside the problem statement (where and when to sell). One line under future scope. |
| 4. Flood / disaster re-routing from news | **Keep, simplified** | Operator ticks "mandi unavailable (flood, strike, closure)" on the dashboard; the engine drops that mandi and re-plans. News scraping is future scope. Stretch: a rain-forecast hint from Open-Meteo. |
| 5. Ask the farmer how fresh the produce is | **Keep** | One crop-specific question on WhatsApp sets how long that lot can be held. Replaces the fixed per-crop hold limit. |
| 6. Easy-to-read WhatsApp replies | **Keep, text only** | Short lines, bold, a few icons. Image cards and voice replies are stretch items. |
| 7. Assign a farmer to grow a niche vegetable / "control demand" | **Cut** | It's a different problem (what to grow, not where to sell), we have no data for it, and "controlling demand" is an overclaim: few growers doesn't mean there are buyers. Don't pitch it. |
| Timed "confirm before dispatch" workflow (blueprint) | **Shrunk** | A display-only line on the advice card: "Go only if price is above ₹X. Check before you send the crop." No clock, cutoffs, locks or new endpoint. |
| "7 in 10 chance" odds | **Replaced** | Show the range, plus a measured figure from the backtest: "last season our hold advice beat the best sell-today option X% of the time". |
| Cash need | **"By when" only** | Not "how much". No lot splitting for cash. |

---

## 2. Final feature list

### Required by the problem statement
| # | Feature |
|---|---|
| R1 | Money-in-hand comparison across mandis: forecast price minus transport, from the farmer's village |
| R2 | Sell now or hold, weighing price gain against spoilage and storage, per crop |
| R3 | Price range plus high / medium / low confidence |
| R4 | WhatsApp text and voice in Marathi / Hindi, short reply in the same language |
| R5 | Rupee backtest vs selling at the nearest mandi on harvest day |
| R6 | FPO dashboard to plan bulk produce across mandis |

Scope: Maharashtra; onion, tomato, soybean; 10–15 mandis (each crop only at mandis that trade it).

### What makes us different (build in this order)
| # | Feature | Seen by |
|---|---|---|
| A | **Cash deadline:** "need money by when?" removes later selling days. Same crop, different farmer, different advice. | Farmer, FPO |
| B | **Freshness-aware holding:** one question sets this lot's hold limit. | Farmer, FPO |
| C | **Honest forecast:** range, a self-check against "price stays the same" at every horizon, and no hold advice where the model fails it. | Both |
| D | **Rupee proof with losses:** average and median gain, how often the advice lost, worst loss, strategy ladder. | FPO, judges |
| E | **Disruption re-route:** mark a mandi unavailable and the plan changes for every affected lot. | FPO |
| F | **Farmer-friendly reply:** short formatted message, break-even condition, storage tip when holding. | Farmer |
| G | **Glut flag** (only if the data has arrivals). | Both |

### FPO plan
Urgent members first, a cap per mandi per day (an entered assumption), shared trucks from one collection centre with cost split by weight, unplaced lots shown with a reason.

### Stretch, only after the 6:30 AM freeze items work
Image card on WhatsApp, voice reply, rain-forecast hint.

### Future scope (say it, don't build it)
News-based disruption detection, waste upcycling guidance, crop planning from supply gaps, buyer offers and payment tracking, official WhatsApp Business deployment, MSP procurement as a selling option, season-aware onion hold limits (rabi vs kharif), a full village gazetteer.

---

## 3. Architecture

```
 FARMER (phone)                                 FPO OPERATOR (laptop)
 WhatsApp text / voice, Marathi or Hindi        Next.js dashboard: Advice · FPO Plan · Evidence
        │                                              │
  WhatsApp adapter (whichever integration works)       │
        │ POST /message                                │ POST /advise, /fpo/plan · GET /forecast, /backtest
        ▼                                              ▼
 ┌────────────────────────── FastAPI backend ──────────────────────────┐
 │ voice → text → parser → conversation state → reply builder + tips   │
 └──────────────┬──────────────────────────────┬───────────────────────┘
                ▼                              ▼
      Decision engine                    FPO allocator
      money in hand per mandi and day    lots → mandis and days
      vs best_today, baseline_today      from the collection centre
      hold limit from freshness          urgent first, mandi cap,
      cash deadline, blocked mandis      shared trucks, blocked mandis
      break-even, flags
                │
                ▼
      Forecast table (precomputed)       Backtest results (precomputed,
      low / likely / high                at default assumptions)
      at 1, 2, 3, 7, 14, 21 days         rupee gain, losses, ladder,
      + self-check flag per horizon      coverage, self-check, hold success
                │
      prices_mh.csv · mandi, village and collection-centre coordinates · config.yaml · tips table
```

Nothing is trained or fetched live during the demo. Every screen and reply shows "prices as of {date}". Backtest and Evidence numbers always use the default assumptions in `config.yaml`; edits in the assumptions drawer change live advice and the FPO plan only.

---

## 4. WhatsApp conversation

At most three short questions. Each is asked only when it can change the answer.

| Step | Bot | When |
|---|---|---|
| 1 | Echo-back: "20 क्विंटल कांदा, निफाड. बरोबर? 1) हो 2) नाही" | Always for voice notes; for text only if something was unclear, or a unit or village was guessed |
| 2 | Freshness question (below) | Only if the best option without it would be a hold |
| 3 | "पैसे कधीपर्यंत हवेत? 1) 2–3 दिवसांत 2) या आठवड्यात 3) घाई नाही" | Only if a 3-day deadline would change the advice |
| 4 | The advice | Always |

The farmer replies with a number, by text or voice. A message that already contains the answer ("2 divsat paise have") skips that question.

### Parsing rules
- **Digits:** accept ASCII and Devanagari digits (० १ २ ३ ४ ५ ६ ७ ८ ९). Normalise them before anything else.
- **Yes / no:** हो, होय, हां, हाँ, ho, haan, ha, yes → yes. नाही, नहीं, nahi, nai, no → no.
- **Quantity units:** क्विंटल / quintal / qtl as is; टन / ton / tonne × 10; किलो / kilo / kg ÷ 100. पोती / गोणी / बोरी / bag and क्रेट / कॅरेट / crate convert using `bag_kg` and `crate_kg` per crop in `config.yaml`. No unit given → assume quintals.
- **Village:** fuzzy-match against the fixed village list (Devanagari and Latin spellings both stored). Below `village_match_threshold`, the echo-back offers the top 3 matches as numbered options plus "4) other"; "other" gets a reply that this village isn't covered yet.
- **Any guessed unit or village forces the echo-back**, even for text, and the echo-back shows the converted quantity: "20 पोती कांदा (≈ 10 क्विंटल), निफाड. बरोबर? 1) हो 2) नाही".

### Freshness question → this lot's hold limit (all values are placeholders; ask a mentor)
| Crop | Question | Answer → days this lot can be held |
|---|---|---|
| Tomato | When was it picked? 1) today 2) 1–2 days ago 3) 3+ days ago | 4 / 2 / 0 |
| Onion | Is it dried (cured) and kept in ventilated storage? 1) yes 2) no | 21 / 5 (ask the mentor whether kharif onion needs a lower limit than rabi) |
| Soybean | Is the grain fully dried? 1) yes 2) no | 21 / 3 |

### Reply format (Marathi example; a native speaker must check all wording)
```
🟢 *14 दिवस थांबा → लासलगाव*
💰 हातात अंदाजे ₹1,840/क्विंटल (₹1,650–₹2,010)
📈 आज जवळच्या बाजारापेक्षा ₹180 जास्त
⚠️ भाव ₹1,720 च्या वर असेल तरच जा. निघण्यापूर्वी खात्री करा
🧅 साठवण: कोरड्या, हवेशीर जागी ठेवा; सडलेले कांदे काढून टाका
🗓 30 सप्टें.च्या भावांनुसार · खात्री: मध्यम
```
The 📈 line is the gain against `baseline_today` (nearest mandi today). The ⚠️ line is the break-even against `best_today`. "Sell now" uses 🔴 and drops the storage line. Low confidence adds one line saying the forecast isn't reliable here, so only today's prices were compared. Hindi and English versions follow the same shape.

### Storage tips (general guidance; check against an agricultural source before the pitch)
| Crop | Tip shown with a hold |
|---|---|
| Onion | Keep in a dry, well-ventilated place off the ground; don't pile deep; remove rotting or sprouting bulbs. |
| Tomato | Keep in shade, in crates not sacks; don't stack deep; move it in the cool hours. |
| Soybean | Store only fully dried grain, in clean dry bags, off the floor and away from walls. |

---

## 5. Decision engine

For each allowed option (mandi m, sell after d days):

```
sellable   = (1 − spoilage_per_day[crop]) ^ d
transport  = distance_km × rate_per_km_per_qtl + loading_per_qtl
storage    = storage_cost_per_qtl_per_day[crop] × d
net(m, d)  = price(m, d) × sellable − transport − storage − fees     (₹ per harvested quintal)
```

`price(m, 0)` is the last reported price at m on or before today (not a forecast; flagged `stale` if older than 3 days). For d > 0, compute `net_low`, `net_mid` and `net_high` from `price_low`, `price_mid` and `price_high`.

### Two comparisons (use these exact names in code, API and UI)
| Name | Definition | Used for |
|---|---|---|
| `baseline_today` | Net at the nearest mandi to the village that trades this crop and isn't blocked, d = 0 | The "gain" shown to the farmer, the rupee backtest, the FPO comparison |
| `best_today` | Highest net over all allowed mandis at d = 0 | The hold test, the break-even price, the hold success rate |

### Allowed options
- d in {0, 1, 2, 3, 7, 14, 21}, and d ≤ this lot's hold limit (from the freshness answer; crop default if not asked).
- d ≤ cash deadline, if given.
- m not in the blocked list, and m trades this crop.
- For d > 0: the self-check passed for (crop, m, d). See §7.

### Choosing
1. Compute `baseline_today` and `best_today`.
2. Go through the hold options (d > 0) from highest `net_mid` down. Take the first one that passes both tests:
   - `net_mid − best_today ≥ min_gain_per_qtl`, and
   - `best_today − net_low ≤ max_downside_per_qtl`.
3. If one passes, the advice is that hold. If none passes, the advice is sell today at `best_today`'s mandi.
4. If no hold option survived the self-check at any mandi, the advice is sell today at `best_today`'s mandi, confidence = low, and the reply adds the "forecast isn't reliable here" line.
5. Gain shown to the farmer = advice net − `baseline_today`. The "why" breakdown splits it into **from choosing the mandi** (`best_today − baseline_today`) and **from waiting** (advice net − `best_today`; zero for sell-today advice).
6. Confidence = the §7 rule for the chosen (crop, mandi, horizon). For sell-today advice, use the rule for the best rejected hold option, or low if there was none.

### Also return
- `break_even_price` (hold advice only): the price at the chosen mandi and day below which selling at `best_today` is better. `= (best_today + transport + storage + fees) ÷ sellable` with per-quintal fees; if fees are a % of price, solve `net(m, d) = best_today` for the price instead.
- Flags per mandi: `stale` (last price older than 3 days), `glut` (recent arrivals well above normal), `blocked`.
- `hold_success_rate` from the backtest, if available, for the reply and the card.
- The "why" breakdown: price, spoilage loss, transport, storage, fees, and the mandi / waiting split.

All transport, spoilage, storage, hold-limit, unit and first-mile numbers live in `config.yaml`, are **placeholders until a mentor gives real figures**, and are shown on screen as assumptions.

### `config.yaml` keys added in rev 2
```yaml
# every number here is a placeholder until a mentor confirms it
fpo:
  collection_centre: {name: "", lat: null, lon: null}
  first_mile_per_qtl: null          # member's cost to bring the lot to the centre
units:
  bag_kg:   {onion: 50, tomato: 20, soybean: 50}
  crate_kg: {tomato: 20}
forecast:
  target_match_window_days: 1
  min_reported_days: null           # set after the first look at the data
  selfcheck_ratio_max: 0.95
  selfcheck_min_rows: 20
  coverage_widen_below: 0.70
confidence:
  stale_days: 3
  narrow_range_pct: 0.15            # range width ÷ mid
parser:
  village_match_threshold: 0.80
```

---

## 6. FPO allocator (rule-based, not an optimiser)

**Origin:** all FPO lots ship from one collection centre (`fpo.collection_centre`). Members bring their lot there, which costs `first_mile_per_qtl`.

1. For each lot, get its allowed options from the engine with origin = collection centre and transport = full-truck cost per quintal (trip cost ÷ truck capacity) + `first_mile_per_qtl`, best first. The ranking assumes full trucks; step 4 computes the real cost.
2. Order lots: soonest cash deadline, then shortest hold limit.
3. Give each lot its best option that still has room under the mandi-day cap; send any remainder to its next-best option.
4. Group by (mandi, day). Trips = quantity ÷ truck capacity, rounded up. Trip cost = fixed + distance (collection centre → mandi) × per-km rate. Split each trip's cost by weight.
5. Each member's money in hand = quantity × (price × sellable − `first_mile_per_qtl` − storage − fees) − truck share.
6. Compare with: every lot sold at its own `baseline_today` (nearest mandi to its own village, today, its own transport). This is the same number the Advice tab shows as the baseline.
7. Any lot that can't be placed is listed with the reason.

"Mark mandi unavailable" re-runs the same steps with that mandi removed.

**Expected difference, not a bug:** a lot's money in hand on FPO Plan won't match the Advice tab for the same crop and village, because FPO uses the collection centre, first-mile cost and shared trucks while Advice uses the village and the per-quintal rate. The baseline does match. Label the FPO column "via {collection centre}, shared truck".

---

## 7. ML: forecast

- **Target:** modal price at the same mandi 1, 2, 3, 7, 14 and 21 days ahead.
- **Model:** LightGBM or XGBoost, quantile objective, three fits (10th, 50th, 90th percentile). One pooled model per crop with mandi and horizon as features. **Sort the three predictions in every row** so low ≤ mid ≤ high.
- **Features:** price 1, 3, 7, 14 days back; 7- and 30-day average; 7-day spread; arrivals 1 and 7 days back (if available); `days_since_last_report`; week of year; sine and cosine of day-of-year; mandi; horizon.
- **Three time blocks, in order:** train → validation → test, with a 21-day gap between blocks. Pick the model and the fallback on validation. Touch the test block only for the final numbers.

### Missing days
- Use reported days only. Never forward-fill into the target. Drop rows where the modal price is 0 or outside that day's [min, max].
- Lag features use the last reported price on or before the lag date. Averages and spread use the reported days inside the window.
- Target at horizon h: the modal price on day t + h. If missing, use the nearer of t + h − 1 and t + h + 1 (the later one on a tie). If neither exists, drop the row. The backtest uses the same rule.
- "Same as today" = the last reported price on or before t. This is the same number the engine uses for `price(m, 0)`.
- Keep a (crop, mandi) series only if it has at least `min_reported_days` reported days in the train block. A dropped mandi doesn't appear for that crop.

### Baselines
- "Same as today" and "same week last year".
- **Persistence band:** mid = last reported price; low / high = last price × the 10th / 90th percentile of past h-day price changes for that crop and mandi in the train block. Used (a) as the first table ML 1 ships and (b) for any (crop, mandi, horizon) that fails the self-check, so a range is still shown.

### Self-check, per crop, mandi and horizon
- Ratio = MAE of `price_mid` ÷ MAE of "same as today", on validation.
- **Pass** = ratio < 0.95 and at least 20 validation rows.
- Fail → that (crop, mandi, horizon) uses the persistence band, `uses_baseline = true`, and gives no hold advice at that horizon. Other horizons at the same mandi are unaffected.

### Range widening (optional; first item in the cut order)
If validation coverage of the 10th–90th range is below 70%, widen per crop and horizon: on validation, take score = max(low − actual, actual − high), and widen both ends by the 80th percentile of that score. Report test coverage after widening.

### Report on test
Error vs both baselines per horizon, and how often the real price fell inside the range, per horizon.

### Confidence label
Fix the rule before looking at test results, and show it on the Evidence tab. Thresholds live in `config.yaml`.
- **High:** self-check passed at that horizon, last report ≤ 3 days old, and range width ÷ mid ≤ `narrow_range_pct`.
- **Low:** self-check failed at that horizon, or last report > 3 days old.
- **Medium:** everything else.

### Output table
`crop, mandi, as_of_date, horizon_days, price_low, price_mid, price_high, uses_baseline, last_price_date`

`uses_baseline` is set per row, so per horizon.

### Ship order
1. Persistence-band table in this exact schema (every row `uses_baseline = true`). Hand it to ML 2 and Backend immediately.
2. The LightGBM table replaces it in place: same file name, same columns.

---

## 8. Backtest

On the test block only, for each crop, at the default assumptions:
1. Step through harvest dates (every 3rd day) and 5–10 villages.
2. On each date, forecast and decide using only data up to that date. Lock the decision.
3. Look up the real price at the chosen mandi on the chosen day (same ±1-day rule as the target) and compute the real net with the same cost assumptions.
4. Compare with the real `baseline_today` (nearest mandi on harvest day). For hold advice, also compare with the real `best_today`.
5. If any needed real price is missing, record the case as excluded, with the reason.

**Report:**
- Average and median gain per quintal against `baseline_today`.
- Share of cases that did worse, and the worst loss.
- The ladder: nearest today (`baseline_today`) → highest price today → best net today (`best_today`) → full advice.
- **Hold success rate:** share of hold advice whose real net beat the real `best_today`.
- Self-check table per crop, mandi and horizon; range coverage per horizon.
- Simulated cases tested and excluded, with exclusion reasons.

**Wording:** "simulated on last season's reported prices, at our default assumptions". Cases overlap (every 3rd day, horizons up to 21 days), so they aren't independent: call them "simulated cases" and make no significance claims.

---

## 9. API changes from the earlier contract

**POST /advise, request:** add
```json
"lot_condition": null,          // tomato: 0 | 1 | 2 (answer index); onion/soybean: true | false
"cash_needed_in_days": null,
"blocked_mandis": [],
"overrides": null,
"lang": "mr"
```
**POST /advise, response:** add `hold_limit_days`, `storage_tip`, `hold_success_rate`, `prices_as_of`, `uses_baseline`, per-option `flags: ["stale" | "glut"]`, and
```json
"baseline_today": {"mandi": "", "net": 0},
"best_today": {"mandi": "", "net": 0},
"gain_vs_baseline": 0,
"gain_from_mandi": 0,
"gain_from_waiting": 0,
"assumptions_default": true
```
`break_even_price` is now measured against `best_today`. Remove `odds_waiting_wins`. `sell_day` can now be 1, 2 or 3.

**POST /fpo/plan, request:** add `blocked_mandis`, per-lot `lot_condition`, and an optional `collection_centre` (defaults to `config.yaml`).
**POST /fpo/plan, response:** per lot, add `first_mile`, `truck_share` and `origin`; per plan, add `baseline_total` (sum of each lot's `baseline_today`).

**GET /backtest:** add `hold_success_rate`; the `selfcheck` table keyed by crop, mandi and horizon with `ratio`, `rows`, `passed`; `coverage` per horizon; `cases_tested`; `cases_excluded_by_reason`; `assumptions: "default"`.

**POST /message:** state is one of `awaiting_confirm`, `awaiting_freshness`, `awaiting_cash`, `done`. Parsing follows §4.

No `/confirmations`, no `/whatif`. Everything else as before.

---

## 10. Dashboard: three tabs

| Tab | Contents |
|---|---|
| **Advice** | Inputs: crop, quantity, village, freshness, cash-by. Card: action, money in hand with range, gain vs nearest today, confidence, break-even condition, storage tip. Mandi table with stale and glut flags. Forecast chart with the range band. "Why" breakdown, ending with "₹X from choosing the mandi · ₹Y from waiting". |
| **FPO Plan** | Lots table (load a sample of 5–6) and the collection centre. Plan result: destination and day per lot, reason, trucks, each member's money in hand ("via {collection centre}, shared truck") and truck share, baseline per lot (matches Advice), total vs baseline, unplaced lots. Checkboxes to mark a mandi unavailable. |
| **Evidence** | Header: "Simulated on last season's reported prices, at default assumptions." Backtest numbers, strategy ladder chart, losses, hold success rate, range coverage per horizon, self-check table per crop, mandi and horizon, the confidence rule. If the drawer differs from the defaults, a banner: "You've changed assumptions. Advice and FPO Plan use your values; these numbers use the defaults." |

Drawers: assumptions (editable, with "reset to defaults") and recent WhatsApp queries.

---

## 11. Owners

| Area | Owns |
|---|---|
| ML 1, `/ml/forecast` | Data, cleaning, missing-day rules, persistence-band table first, forecast table, per-horizon self-check, coverage, range widening |
| ML 2, `/ml/engine` | Decision engine (`best_today` / `baseline_today`, hold rule), FPO allocator (collection centre, first mile), backtest |
| Backend, `/backend` | API, WhatsApp adapter, voice, parser (digits, units, village match), conversation state, reply builder, tips |
| Frontend, `/frontend` | Three tabs, drawers, language toggle, Evidence assumptions label and banner, FPO labels |

Fill in the names. One integrator merges at each checkpoint.

---

## 12. Rest of the night

| Time | Checkpoint |
|---|---|
| 12:15 – 12:30 AM | Everyone reads sections 0–4. Agree the API changes and the `best_today` / `baseline_today` names. |
| 12:30 – 1:30 AM | Mentor round: one or two people go, the rest keep building. Ask for real transport, spoilage and hold-limit figures; bag and crate weights; a first-mile cost; whether kharif onion needs a lower hold limit; whether the backtest design is fair; how much live WhatsApp matters. **ML 1 ships the persistence-band table in the final schema by 1:30.** |
| 2:30 AM | **One crop works end to end:** real data → forecast (LightGBM or persistence band, whichever is ready) → engine → API → Advice tab, and WhatsApp text in and out. If not, skip features E, F and G. |
| 3:00 – 4:00 AM | Break. |
| 4:00 – 5:30 AM | Three crops. FPO Plan tab with the collection centre. Backtest running. Voice note end to end. Freshness and cash questions on WhatsApp. Parser units and Devanagari digits. |
| 5:30 – 6:30 AM | Evidence tab with the assumptions label. Mark-mandi-unavailable. Formatted reply with tip. Glut flag. Range widening if validation coverage is below 70%. |
| 6:30 AM | **Feature freeze.** |
| 6:30 – 8:00 AM | Fix bugs, labels, empty and error states. Check the same inputs give the same number on WhatsApp and Advice, and the same baseline on FPO Plan. FPO money in hand differs by design; check its label instead of "fixing" it. |
| 8:00 – 9:45 AM | Backup recording, slides, two rehearsals (include the §15 questions), final merge, submit. |

Naps in pairs between 4:30 and 6:30 AM, 45–60 minutes each.

**Cut order if behind:** range widening → glut flag → storage tips → mark-mandi-unavailable → 1–3 day horizons → shared-truck costing → drawers. **Never cut:** three crops, ranges, the backtest, WhatsApp text in Marathi/Hindi, a working FPO Plan tab. Also never skip the §5 definitions or the §7 missing-day rules; they're what make the numbers agree across screens.

---

## 13. Demo (3 minutes)

| Time | Show |
|---|---|
| 0:00 – 0:30 | WhatsApp voice note in Marathi (onion). Echo-back, freshness question, formatted reply with the storage tip. |
| 0:30 – 1:05 | Advice tab on real data: hold advice, range, mandi table, forecast band, "from choosing the mandi / from waiting" split. Switch to tomato picked 2 days ago: sell today. |
| 1:05 – 1:30 | Set "need money in 2–3 days": the advice flips. |
| 1:30 – 2:10 | FPO Plan: five lots from the collection centre, shared trucks, urgent member first. Mark one mandi unavailable (flood): the plan re-routes. |
| 2:10 – 2:50 | Evidence (at default assumptions): rupee gain, how often the advice lost, the ladder, the self-check table by horizon. |
| 2:50 – 3:00 | Limits and closing line. |

**Closing line:** "SahiDaam turns a price forecast into a next step: where to sell, when to sell, and what to check before the crop leaves."

---

## 14. Claims

**Say:** money-in-hand advice; price ranges with a model self-check at every horizon; advice that changes with cash need and freshness; a rupee backtest over simulated cases that shows losses; rule-based FPO planning from a collection centre; operator-marked disruptions.

**Don't say:** real-time demand; controlling or creating demand; predicting floods or reading the news; optimal plan; guaranteed gain; "first"; "statistically significant"; "X farmers would have earned" (say "simulated cases"); any accuracy or gain number we didn't measure tonight. The mandi cap, transport, spoilage, first-mile, unit weights and hold limits are assumptions, the Evidence numbers are at default assumptions, and the storage tips are general guidance.

---

## 15. Judge questions: prepared answers

Fill the brackets with tonight's real numbers before rehearsal.

| Question | Answer |
|---|---|
| Your transport and spoilage numbers are made up. | They're placeholders [or: from our mentor], shown on screen and editable. The ladder shows how much of the gain comes from the mandi choice and how much from waiting, so you can see which assumption matters. |
| Why not just send the farmer to the highest-price mandi? | That's ladder step 2. Once transport is subtracted (step 3), the best mandi often changes: [₹X difference from the ladder]. |
| Onion prices jump on export-policy news. Can you predict that? | No. That's why we show a range, check every horizon against "price stays the same", and give no hold advice where the model fails. Shocks show up in the backtest as losses, and we show those. |
| Kharif onion doesn't keep like rabi onion. | Agreed. The freshness answer sets each lot's hold limit; the numbers are placeholders [or: from our mentor]. Season-aware limits are the next step. |
| What if soybean is below MSP? Why not suggest procurement? | Procurement depends on registration, windows and quotas we can't see, so the prototype compares mandi options only. MSP procurement as an option is future scope. |
| How many cases, and is the result significant? | [N] simulated cases. They overlap, so we don't claim significance. We show the median, how often the advice lost, and the worst loss instead of one average. |
| Why LightGBM and not an LSTM or transformer? | Daily mandi data is small and gappy. A quantile GBM gives ranges cheaply. What matters more is whether it beats "same as today" at each horizon, and we show where it doesn't. |
| What if my village isn't in your list? | The prototype covers a fixed list and the bot offers the closest matches. A full village gazetteer is future scope. |
| How is this different from existing price apps? | They show what prices are, or one forecast. We turn ranges, transport, spoilage, freshness and cash need into one next step with a break-even check, and show how that advice would have done last season. |
| Are you on the official WhatsApp API? | The prototype uses [integration]. Official WhatsApp Business deployment is future scope. |
