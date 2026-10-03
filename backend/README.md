# Backend: run it and connect WhatsApp (360dialog sandbox)

All commands run from the repo root on the Mac. Keys live in `backend/.env` (git-ignored):
`WA_PROVIDER=360dialog`, `D360_API_KEY`, `GROQ_API_KEY`, `ENGINE_MODE=real`. Never paste a key into a command.

## Restart everything before the demo

1. Backend (one worker, no reload, or conversation memory is lost). Frees port 8000 first, keeps running
   after the terminal closes, logs to `backend.log`:

       lsof -ti tcp:8000 | xargs kill 2>/dev/null
       nohup .venv/bin/python -m uvicorn backend.main:app --port 8000 > backend.log 2>&1 &
       grep "Application startup complete" backend.log

2. Tunnel (the URL changes on every restart):

       pkill -f "cloudflared tunnel" 2>/dev/null
       nohup cloudflared tunnel --url http://localhost:8000 > tunnel.log 2>&1 &
       sleep 5; grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' tunnel.log | head -1

3. Register the tunnel with 360dialog (replace `<tunnel>` with the host printed in step 2). The key is read
   from `backend/.env` into the environment of a subshell, never typed or printed:

       ( set -a; . backend/.env; set +a
         curl -s -X POST https://waba-sandbox.360dialog.io/v1/configs/webhook \
           -H "D360-API-KEY: $D360_API_KEY" -H "Content-Type: application/json" \
           -d '{"url": "https://<tunnel>.trycloudflare.com/webhook"}' )

   Expected answer: `{"url":"https://<tunnel>.trycloudflare.com/webhook","headers":null}`

4. Check: `curl -s localhost:8000/health` shows `"advise": "real"`; recent messages and replies are at
   `curl -s localhost:8000/queries`.

## Local test without WhatsApp

Stop the server on port 8000 first; the test starts its own and sends nothing:

    .venv/bin/python backend/tests/test_whatsapp_local.py

The sandbox replies only to the phone that sent START and has a cap of about 200 messages.

## SQLite store (inspection and query log)

`data/sellsmart.db` (git-ignored) holds copies of `prices_mh.csv`, `mandis.csv`, `villages.csv`,
`forecast_table.csv` (tables `prices`, `mandis`, `villages`, `forecasts`), the backtest ladder
(`backtest_results`), and one `queries` row per `/advise` call and per completed WhatsApp conversation
(sender masked to its last four digits). The engine never reads it. It is built at startup if missing;
rebuild with `.venv/bin/python -m backend.db` (the queries log is kept).

Row counts per table:

    sqlite3 -header -column data/sellsmart.db "SELECT 'prices' AS tbl, COUNT(*) AS n FROM prices
      UNION ALL SELECT 'mandis', COUNT(*) FROM mandis UNION ALL SELECT 'villages', COUNT(*) FROM villages
      UNION ALL SELECT 'forecasts', COUNT(*) FROM forecasts
      UNION ALL SELECT 'backtest_results', COUNT(*) FROM backtest_results
      UNION ALL SELECT 'queries', COUNT(*) FROM queries;"

Onion prices by mandi on the day before the as-of date:

    sqlite3 -header -column data/sellsmart.db "SELECT mandi, modal_price, min_price, max_price FROM prices
      WHERE crop = 'onion' AND date = date((SELECT MAX(as_of_date) FROM forecasts), '-1 day')
      ORDER BY modal_price DESC;"

The last five farmer queries:

    sqlite3 -header -column data/sellsmart.db "SELECT timestamp, channel, sender, language, crop, quantity_qtl,
      village, action, mandi, net_per_qtl, gain_vs_baseline, hold_suppressed
      FROM queries ORDER BY id DESC LIMIT 5;"

The four-policy ladder per crop:

    sqlite3 -header -column data/sellsmart.db "SELECT crop, policy, avg_net FROM backtest_results
      ORDER BY crop, position;"

## Supabase copy (browse the data in Supabase's Table Editor)

`SUPABASE_DB_URL` in `backend/.env` is the project's **Connect → Connection String → URI → Session pooler**
link with the database password in place of `[YOUR-PASSWORD]` (no brackets). Then, from the repo root:

    .venv/bin/python -m backend.supabase_load

It drops and reloads 14 tables (prices, mandis, villages, forecasts, forecast_history, selfcheck,
selfcheck_history, coverage, selfcheck_v1, coverage_v1, splits, backtest_summary, backtest_results, queries),
turns on row-level security, and prints each table's row count next to its source file. It is a snapshot:
re-run it to copy new farmer queries from `data/sellsmart.db`. The engine never reads Supabase.
