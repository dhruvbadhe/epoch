# SahiDaam (सही दाम)

**EPOCH 1.0 · PS1 "Where and When to Sell" · Team Byte Me:** Dhruv Badhe (Team Leader), Aarana Chaurasia, Vedant Khedekar, Vidit Jain

A farmer sends crop, quantity and village on WhatsApp (text or voice, Marathi, Hindi or English) and gets one answer: where and when to sell for the most money in hand, with the numbers behind it. FPO operators use a web dashboard (Advice, FPO Plan, Evidence, Info) built on the same engine. Scope: Maharashtra; onion, tomato and soybean; 14 mandis; 26 villages. Every screen and reply shows "prices as of 2025-09-21"; nothing is trained or fetched live during the demo.

## What it does, against each requirement

| Requirement | What SahiDaam does |
|---|---|
| R1 Money in hand across mandis | Price at each mandi minus transport (road km from the farmer's village), spoilage, storage and fees, ranked per quintal; compared with the nearest mandi (`baseline_today`). |
| R2 Sell now or hold | Holds only when the forecast gain beats selling today by a margin and the downside is limited, within the lot's freshness and cash deadline. A hold gate turns holding off for a crop whose measured hold record is poor. |
| R3 Range and confidence | Low–mid–high range from quantile models, a self-check against "price stays the same" at every horizon, and high / medium / low confidence. |
| R4 WhatsApp in Marathi / Hindi | 360dialog sandbox; text and voice (Groq whisper-large-v3); one-message path or a guided step-by-step flow; reply in the farmer's language; a price-offer check after the advice. |
| R5 Rupee backtest | Simulated cases over the test block, against selling at the nearest mandi; gains and losses both shown. |
| R6 FPO dashboard | Bulk plan across mandis: urgent lots first, a per-mandi cap, shared trucks; block a mandi and every affected lot is re-routed with a reason. |

## Architecture

```
WhatsApp bot (360dialog webhook)      FPO dashboard (Next.js, :3000)
            \                               /
             FastAPI backend (:8000): parser, conversation, replies,
             /advise /fpo/plan /backtest /forecast /market/snapshot /message
                              |
             decision engine (ml/engine): money in hand, hold rule,
             hold gate, FPO allocator
                              |
             forecast and trust layer (ml/forecast): quantile LightGBM,
             trailing self-check, fallback bands, coverage
                              |
             data: prices_mh.csv, mandis.csv, villages.csv, forecast tables,
             config.yaml (assumptions), backtest.json

offline: backtest (ml/engine/backtest.py) replays the test block -> data/backtest.json
```

## Repository

| Path | What |
|---|---|
| `backend/` | FastAPI app, WhatsApp adapter, parser, conversation and reply templates, SQLite query log, tests |
| `frontend/` | Next.js dashboard: Advice, FPO Plan, Evidence, Info |
| `ml/forecast/` | Data cleaning, features, quantile models, self-check, evaluation |
| `ml/engine/` | Decision engine, FPO allocator, backtest |
| `data/` | Handoff files read by the engine and backend |
| `docs/` | Spec, API contract, pitch numbers |
| `config.yaml` | Every assumption (transport, spoilage, storage, hold limits, hold rule) |

## How ML is used, and how rules are used

- **ML (forecast only):** LightGBM quantile models (10th / 50th / 90th percentile) per crop give a price range 1–21 days ahead. The model is used at a mandi and horizon only where it beats "price stays the same" on a trailing self-check; elsewhere a simple fallback band is shown and no hold advice is given.
- **Rules (every decision):** money in hand, the hold rule, the cash deadline, freshness limits, the hold gate and the FPO allocation are fixed formulas on `config.yaml` assumptions. Why: the decision has to be explainable to a farmer, and every number has to be traceable. No language model writes any number.

## Results (simulated cases, default assumptions)

Test block 2025-08-01 to 2025-11-04 (`data/backtest.json`).

| Crop | Nearest mandi today | Highest price today | Best net today | With hold rule (before the gate) | Gain from mandi choice | Gain from holding | Avg / median gain | Holds won / lost / unscored | Cases scored / excluded |
|---|---|---|---|---|---|---|---|---|---|
| onion | ₹1000 | ₹1015 | ₹1069 | ₹1058 | ₹69 | ₹-11 | ₹58 / ₹15 | 40 / 84 / 0 | 707 / 125 |
| tomato | ₹1574 | ₹1763 | ₹1798 | ₹1798 | ₹224 | ₹0 | ₹224 / ₹52 | 0 / 0 / 0 | 739 / 93 |
| soybean | ₹3789 | ₹3750 | ₹3825 | ₹3826 | ₹36 | ₹1 | ₹37 / ₹0 | 7 / 1 / 13 | 649 / 183 |

Per quintal. Exclusions are cases with no recent price at the nearest or chosen mandi, or no real price to score against. Full sources and percentages: `docs/pitch_numbers.md`.

## Info tab and `/market/snapshot`

`GET /market/snapshot?crop=onion&village=Niphad` returns the previous day's **reported** prices (never forecasts) for every mandi that trades the crop: modal, min and max, change from its previous report, the highest and lowest price and the spread, mandis that did not report with their last report date, a 7-day series, and with a village the road distance and money in hand per quintal from the engine's own functions. The Info tab shows it; it falls back to demo data only when the backend is unreachable, with a badge.

## Honest limitations

- Forecast vs "same as today" on the test block, onion: ratio 1.207 (below 1 = better), coverage 0.715 (`ml/forecast/summary.json`).
- Forecast vs "same as today" on the test block, tomato: ratio 1.027 (below 1 = better), coverage 0.781 (`ml/forecast/summary.json`).
- Forecast vs "same as today" on the test block, soybean: ratio 1.037 (below 1 = better), coverage 0.756 (`ml/forecast/summary.json`).
- Hold advice is suppressed by the hold gate for all three crops with the current record (onion holds won 40 of 124).
- Forecast v2 and the hold gate were both designed after seeing test-block results, so their test numbers are not an untouched holdout.
- Transport, storage, spoilage and fees are assumptions in `config.yaml`, not measured costs.
- The backtest uses simulated farmer cases (villages × dates), not real farmer outcomes; cases overlap.
- Freshness is a guidance-based lookup of the configured hold limits, not a calibrated model.
- Three crops and 14 mandis in Maharashtra only.

## Tech stack

Python 3.11, FastAPI, pandas, LightGBM, DuckDB (data preparation), haversine; Next.js, React, Recharts; 360dialog WhatsApp sandbox, Groq whisper-large-v3, cloudflared; SQLite query log; optional Supabase copy.

## Run it

```bash
# once
python3.11 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt
cp .env.example backend/.env        # fill in WA_PROVIDER, D360_API_KEY, GROQ_API_KEY; ENGINE_MODE=real
cd frontend && pnpm install && cp .env.example .env.local && cd ..

# backend (repo root)
.venv/bin/python -m uvicorn backend.main:app --port 8000

# dashboard
cd frontend && pnpm dev            # http://localhost:3000
```

WhatsApp (tunnel and webhook registration): see `backend/README.md`.

Self-tests:

```bash
.venv/bin/python ml/engine/selftest.py && .venv/bin/python ml/engine/test_backtest.py && .venv/bin/python ml/engine/test_fpo.py
.venv/bin/python -m backend.selftest
for t in language guided offer db market freshness; do .venv/bin/python backend/tests/test_$t.py; done
.venv/bin/python backend/tests/test_whatsapp_local.py   # stop the server on :8000 first
cd frontend && pnpm test
```

## Demo script

1. **WhatsApp:** send `20 क्विंटल कांदा, निफाड` → sell today at Pimpalgaon, with the note that a 7-day hold was not advised because past holds rarely paid off. Then send `1200 per quintal` for the offer check.
2. **Guided flow:** send `hi` → language → crop → quantity → village → freshness → cash → summary → advice.
3. **Advice tab:** onion, 20 qtl, Niphad: the same mandi and numbers, the selling-window estimate and its reasons.
4. **FPO Plan:** build the plan for six lots; block Pimpalgaon and show the change in total net and the moved lots.
5. **Evidence:** the ladder per crop, the hold record and the losses next to the gains.
6. **Info:** yesterday's reported prices, highest price, spread, and highest money in hand from Niphad.

