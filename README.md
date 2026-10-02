# SellSmart

**Team Byte Me · EPOCH 1.0 · PS1 "Sell Smart"**

A farmer sends crop, quantity and village on WhatsApp (text or voice, Marathi or Hindi) and gets one answer: where and when to sell for the most money in hand. FPO operators use a web dashboard (Advice, FPO Plan, Evidence) built on the same engine.

Scope: Maharashtra; onion, tomato, soybean; 10–15 mandis. Nothing is trained or fetched live during the demo. Every screen and reply shows "prices as of {date}".

| Read | For |
|---|---|
| `docs/SellSmart_FINAL_v2.md` | The full spec |
| `docs/api_contract.md` | The API shapes and `config.yaml` assumptions |
| `docs/00_TEAM_RULES.md` | Who owns what, handoff files, git rules, checkpoints |
| `docs/BACKEND.md` | The backend role file |

## Run the backend
Python 3.10 or newer, from the repo root:
```bash
pip install -r requirements.txt
```
```bash
python -m uvicorn backend.main:app --port 8000
```
Use `python -m uvicorn`, not bare `uvicorn`: on Windows pip often installs the `uvicorn` launcher into a folder that isn't on PATH ("uvicorn is not recognized"). Stop it with Ctrl+C.

No `--reload` and one worker during the demo, or WhatsApp conversation memory is lost. Interactive API docs: http://localhost:8000/docs

Check everything (no network, keys or engine needed):
```bash
python -m backend.selftest
```

## What is real and what is example data
```bash
curl http://localhost:8000/health
```
The backend starts with nothing but this repo. Each part switches from example data to the real thing as soon as its owner commits it; no backend change is needed.

| Part | Until it exists | Real once this is committed | Owner |
|---|---|---|---|
| Decision engine | example JSON from `backend/fake/` | `ml/engine/api.py` with `advise()` | ML 2 |
| FPO allocator | example JSON | `fpo_plan()` in the same file | ML 2 |
| Assumptions | `backend/fake/config.yaml` (the contract copy) | `config.yaml` | ML 2 |
| Mandi list | two example mandis | `data/mandis.csv` | ML 1 |
| `/forecast` | example JSON | `data/forecast_table.csv` (+ `data/prices_mh.csv` for history) | ML 1 |
| `/backtest` | example JSON, every metric `null` | `data/backtest.json` (+ `data/selfcheck.csv`, `data/coverage.csv`) | ML 2, ML 1 |

Data files are re-read when they change on disk. A new or changed `ml/engine/api.py` needs a backend restart.

While the engine is example data, `/advise` returns the header `X-SellSmart-Engine: fake` and the WhatsApp reply ends with a 🧪 line. **For the demo set `ENGINE_MODE=real` in `.env`** so the backend can never quietly fall back to example numbers.

### What the engine functions must look like (ML 2)
The backend calls them with keyword arguments and passes the result through unchanged, adding only `storage_tip` and `message`:
```python
def advise(crop, quantity_qtl, village, lot_condition=None, cash_needed_in_days=None,
           blocked_mandis=None, overrides=None) -> dict      # the /advise response in docs/api_contract.md

def fpo_plan(lots, blocked_mandis=None, mandi_cap_qtl_per_day=None, collection_centre=None,
             overrides=None) -> dict                         # the /fpo/plan response
```
`village` is the `village` column of `data/villages.csv`. `collection_centre` is `None` (use `config.yaml`) or `{"name", "lat", "lon"}`. Raise `ValueError("readable message")` for bad input; it becomes an HTTP 400.

## Keys
```bash
cp .env.example .env
```
Fill in `.env`; it is never committed.

## WhatsApp
Use ONE integration. Both only move messages: message in → `handle_message` → reply out.

**QR-linked bridge** (`backend/whatsapp/bridge`, Node 20.12 or newer). Put the team's test numbers in `ALLOWED_NUMBERS` in `.env` (digits with country code, e.g. `919812345678`), start the backend, then:
```bash
cd backend/whatsapp/bridge && npm install && npm start
```
Scan the QR once from WhatsApp → Linked devices. It ignores groups, status updates and its own messages, and replies only to `ALLOWED_NUMBERS`. Check the bridge's message handling without WhatsApp (backend running):
```bash
node backend/whatsapp/bridge/selftest.js
```

**Official Cloud API** (`backend/whatsapp/cloud_api.py`): set the `WHATSAPP_*` keys in `.env` and point Meta's webhook at `https://<public-url>/whatsapp/webhook`. The signature of every delivery is verified.

In the pitch, say which one it is: "The prototype uses a linked-device bridge to WhatsApp; a real deployment would use the official WhatsApp Business API."

## Voice notes
Set one speech-to-text key in `.env` (`SARVAM_API_KEY`, `GROQ_API_KEY` or `OPENAI_API_KEY`) and `STT_LANGUAGE` (`mr` or `hi`). Nothing runs locally, so no ffmpeg is needed. Test with a real recording that has a number and a village name in it:
```bash
curl -F sender=919812345678 -F audio=@voice.ogg http://localhost:8000/message
```

## Try the conversation without WhatsApp
```bash
curl -X POST http://localhost:8000/message -H "Content-Type: application/json" -d "{\"sender\": \"919812345678\", \"text\": \"20 poti kanda Niphad\"}"
```
Then send `1`, `1`, `3` with the same sender to walk through confirm → freshness → cash → advice.

## Before the demo
- A Marathi and a Hindi speaker read every template in `backend/replies.py` and `backend/tips.py`.
- Storage tips are general guidance: check them against an agricultural source.
- `data/villages.csv` coordinates were checked against OpenStreetMap on 3 October 2026; spot-check a few on a map.
- `ENGINE_MODE=real` in `.env`, and `GET /health` shows no `fake`.
- Keep a screen recording of a working WhatsApp exchange as the backup.
