# SahiDaam — team rules and workspace

**Team Byte Me · EPOCH 1.0 · PS1 "Where and When to Sell" · coding ends 10:00 AM, 3 October**

**The product in two lines:** a farmer sends crop, quantity and village on WhatsApp (text or voice, Marathi or Hindi) and gets one answer: where and when to sell for the most money in hand. FPO operators use a web dashboard (Advice, FPO Plan, Evidence) built on the same engine.

**Scope:** Maharashtra; onion, tomato, soybean; 10–15 mandis. Nothing is trained or fetched live during the demo. Every screen and reply shows "prices as of {date}".

Full spec: `docs/SellSmart_FINAL_v2.md`. Each person also has their own file: `ML1_FORECAST.md`, `ML2_ENGINE.md`, `BACKEND.md`, `FRONTEND.md`.

## Who does what, with which AI
| Role | Folder | AI | Use the strong model for | Use the lighter model for |
|---|---|---|---|---|
| Backend and integrator | `/backend` | Claude (Claude Code) | Wiring, WhatsApp flow, bugs across parts | Routine edits |
| ML 2: engine, FPO, backtest | `/ml/engine` | Claude (Claude Code) | Decision rules, backtest | Small fixes |
| Frontend | `/frontend` | ChatGPT (Codex if available) | First build of each tab | Styling and tweaks |
| ML 1: data and forecast | `/ml/forecast` | ChatGPT | Feature and split logic | Cleaning scripts |

Fill in names: Backend ______ · ML 2 ______ · Frontend ______ · ML 1 ______

## Repo layout
```
/backend          Backend only (includes /backend/whatsapp)
/frontend         Frontend only
/ml/forecast      ML 1 only
/ml/engine        ML 2 only
/data             one owner per file (table below)
/docs             spec + API contract (Backend owns the contract)
config.yaml       ML 2 owns
requirements.txt  Backend owns; ask in the group chat to add a line
CLAUDE.md, AGENTS.md, .gitignore, README.md   Backend owns
```

## Handoff files
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

## Names everyone uses (code, API and UI)
- `baseline_today`: money in hand at the nearest mandi to the village, selling today. Used for the "gain" shown to the farmer, the backtest and the FPO comparison.
- `best_today`: the highest money in hand over all allowed mandis, selling today. Used for the hold test, the break-even price and the hold success rate.
- `uses_baseline`: the model failed its self-check there, so no hold advice.

## Git: how you push
One-time setup:
```bash
git config pull.rebase true
git config rebase.autoStash true
```
Every 30 minutes, or whenever something works:
```bash
git status                      # only your files should be listed
git add <your folder>/
git commit -m "<area>: <what changed>"
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
7. At each checkpoint, when the full flow works, the integrator runs `git tag ok-0230 && git push --tags`. If `main` breaks later, go back to the last tag.

## `.gitignore` (integrator adds this first)
```
node_modules/
.next/
__pycache__/
venv/
.env
*.ipynb
.ipynb_checkpoints/
.wwebjs_auth/
data/raw/
```

## `CLAUDE.md` and `AGENTS.md` (same text in both, at the repo root)
```
Project: SahiDaam. Full spec: docs/SellSmart_FINAL_v2.md. API: docs/api_contract.md.
You work in ONE folder only, named in the first prompt. Never create or edit files outside it.
Read-only inputs: everything under data/ that you don't own, and config.yaml.
Use the exact names from the spec: baseline_today, best_today, uses_baseline.
All assumptions come from config.yaml. Never hardcode a rate, limit or threshold.
Never commit secrets. Keys come from .env.
After each change, run it and show the output. Keep one small self-test per module.
A metric that hasn't been measured is null, never 0.
```

## Checkpoints
| Time | Team checkpoint |
|---|---|
| 2:30 AM | One crop works end to end: real data → forecast → engine → API → Advice tab, and WhatsApp text in and out |
| 3:00 – 4:00 AM | Break |
| 5:30 AM | Three crops, FPO Plan tab, backtest running, voice note end to end |
| 6:30 AM | **Feature freeze** |
| 8:00 – 9:45 AM | Backup recording, slides, rehearsals, final push |

## Making the AI limits last
- One session per task. Long sessions cost more per message.
- Point the tool at a section of your role file; don't paste the whole spec each time.
- Batch requests: several functions and their self-test in one message.
- Check usage at each checkpoint. If an account runs out, pair with a teammate until it resets.
- Read what the AI writes before you commit it. Judges may ask any of you how a piece works.
