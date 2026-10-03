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
