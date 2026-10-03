"""Simulated 360dialog webhooks against localhost:8000/webhook. Sends nothing to WhatsApp or Groq.

Starts the backend in-process on port 8000 (stop any other server on 8000 first) with the adapter's
send_text, voice download and transcription mocked.
Run from the repo root: .venv/bin/python backend/tests/test_whatsapp_local.py
"""
import os
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ["WA_DRY_RUN"] = "1"  # second guard: even unmocked, the adapter would only log replies

import httpx  # noqa: E402
import uvicorn  # noqa: E402

from backend import main, speech, whatsapp_adapter as wa  # noqa: E402

URL = "http://localhost:8000/webhook"
sent: list[tuple[str, str]] = []
heard: list[dict] = []


async def fake_send(to, body, by_user_id=False):
    sent.append((to, body))


async def fake_download(media_id):
    return b"OggS fake voice note"


def fake_transcribe(audio, *args, **kwargs):
    heard.append({"bytes": audio, **kwargs})
    return "20 क्विंटल कांदा, निफाड"


wa.send_text, wa.download_voice_note, speech.transcribe = fake_send, fake_download, fake_transcribe


def event(sender, message_id, **content):
    """A 360dialog (Cloud API shape) incoming-message webhook."""
    message = {"from": sender, "id": message_id, "timestamp": "1758412800", **content}
    return {"object": "whatsapp_business_account", "entry": [{"id": "waba", "changes": [{"field": "messages", "value": {
        "messaging_product": "whatsapp", "contacts": [{"wa_id": sender, "profile": {"name": "Test"}}],
        "messages": [message]}}]}]}


def status_event(message_id):
    return {"object": "whatsapp_business_account", "entry": [{"id": "waba", "changes": [{"field": "messages", "value": {
        "messaging_product": "whatsapp", "statuses": [{"id": message_id, "status": "delivered",
                                                       "recipient_id": "919800000009"}]}}]}]}


def post(payload, expect_replies=1):
    """POST the webhook; return the replies sent because of it (background work, so wait for them)."""
    before = len(sent)
    r = httpx.post(URL, json=payload, timeout=10)
    assert r.status_code == 200, r.text
    deadline = time.time() + 15
    while time.time() < deadline and len(sent) < before + expect_replies:
        time.sleep(0.05)
    time.sleep(0.5)  # anything extra (a second reply) would arrive now
    return [body for _, body in sent[before:]]


results = []


def case(name, ok, replies):
    results.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {name}")
    for body in replies:
        print("      " + body.replace("\n", "\n      "))


def text(sender, mid, body, expect_replies=1):
    return post(event(sender, mid, type="text", text={"body": body}), expect_replies)


server = uvicorn.Server(uvicorn.Config(main.app, host="127.0.0.1", port=8000, log_level="warning"))
threading.Thread(target=server.run, daemon=True).start()
while not server.started:
    time.sleep(0.05)

try:
    r = text("919800000001", "wamid.1", "20 क्विंटल कांदा, निफाड")
    case("1. Devanagari text -> advice (Pimpalgaon, 1,089, +35, hold-suppressed note)",
         len(r) == 1 and all(s in r[0] for s in ("पिंपळगाव", "₹1,089", "₹35", "124 पैकी फक्त 40")), r)

    r = text("919800000002", "wamid.dup", "20 क्विंटल कांदा, निफाड") + \
        text("919800000002", "wamid.dup", "20 क्विंटल कांदा, निफाड", expect_replies=0)
    case("2. same message ID twice -> one reply", len(r) == 1, r)

    r = post(status_event("wamid.1"), expect_replies=0)
    case("3. status event -> no reply", r == [], r)

    r = text("919800000004", "wamid.4", "20 क्विंटल कांदा, अटलांटिस")
    case("4. unknown village -> asks which village", len(r) == 1 and "गाव" in r[0] and wa.MSG_ERROR not in r[0], r)

    r = text("919800000005", "wamid.5", "10 qtl mango, Niphad")
    case("5. unsupported crop -> says which crops are covered",
         len(r) == 1 and "सोयाबीन" in r[0] and wa.MSG_ERROR not in r[0], r)

    r = text("919800000006", "wamid.6", "zzqx blorp 42 !!")
    case("6. nonsense -> help or a question, not an error", len(r) == 1 and wa.MSG_ERROR not in r[0], r)

    r = post(event("919800000007", "wamid.7", type="audio", audio={"id": "media-7", "mime_type": "audio/ogg; codecs=opus"}))
    sent_ok = len(r) == 1 and "20 क्विंटल कांदा" in r[0]
    hint_ok = heard and heard[-1].get("auto_language") is True and heard[-1].get("prompt") == wa.VOICE_HINT \
        and heard[-1]["bytes"] == b"OggS fake voice note"
    r += text("919800000007", "wamid.7b", "1")
    case("7. voice note (download + Groq mocked) -> echo, then '1' -> same advice as case 1",
         bool(sent_ok and hint_ok and len(r) == 2 and "₹1,089" in r[1]), r)
finally:
    server.should_exit = True

print(f"\n{sum(results)} of {len(results)} passed")
sys.exit(0 if all(results) else 1)
