"""Adapter for the official WhatsApp Cloud API. It only moves messages; all logic is in
conversation.handle_message. Used only if the WHATSAPP_* keys are set in .env.

Meta calls GET /whatsapp/webhook once to verify the URL, then POST /whatsapp/webhook per event.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from collections import deque

import httpx
from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import PlainTextResponse

from .. import conversation, data_loader, querylog, replies, speech
from ..errors import ApiError

log = logging.getLogger("sellsmart.whatsapp")

router = APIRouter(prefix="/whatsapp")

GRAPH_URL = "https://graph.facebook.com"
TIMEOUT_SECONDS = 30
_handled: deque = deque(maxlen=1000)        # message ids already answered (Meta retries deliveries)
_transport: httpx.BaseTransport | None = None   # swapped for a mock in the self-test


def _env(name: str) -> str:
    return os.getenv(name, "").strip()


def _digits(number: str) -> str:
    return "".join(c for c in str(number) if c.isdigit())


def _allowed(sender: str) -> bool:
    """Reply only to the team's test numbers."""
    return _digits(sender) in {_digits(n) for n in _env("WHATSAPP_ALLOWED_NUMBERS").split(",") if _digits(n)}


def _client() -> httpx.Client:
    return httpx.Client(transport=_transport, timeout=TIMEOUT_SECONDS,
                        headers={"Authorization": f"Bearer {_env('WHATSAPP_TOKEN')}"})


def _graph(path: str) -> str:
    return f"{GRAPH_URL}/{_env('WHATSAPP_GRAPH_VERSION') or 'v21.0'}/{path}"


def signature_ok(body: bytes, header: str | None) -> bool:
    """X-Hub-Signature-256 is 'sha256=' + HMAC-SHA256 of the raw body with the app secret."""
    secret = _env("WHATSAPP_APP_SECRET")
    if not secret or not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(header[len("sha256="):].encode(), expected.encode())


@router.get("/webhook")
def verify(request: Request):
    query, token = request.query_params, _env("WHATSAPP_VERIFY_TOKEN")
    if token and query.get("hub.mode") == "subscribe" and hmac.compare_digest(
            query.get("hub.verify_token", "").encode(), token.encode()):
        return PlainTextResponse(query.get("hub.challenge", ""))
    raise ApiError("Webhook verification failed", status=403)


@router.post("/webhook")
async def receive(request: Request, background: BackgroundTasks):
    body = await request.body()
    if not signature_ok(body, request.headers.get("x-hub-signature-256")):
        raise ApiError("Bad webhook signature", status=403)
    try:
        payload = json.loads(body)
    except ValueError:
        raise ApiError("Request body is not valid JSON") from None
    for incoming in _messages(payload):
        background.add_task(_answer, incoming)      # reply after the 200, so Meta doesn't retry
    return {"status": "ok"}


def _messages(payload: dict) -> list[dict]:
    """New text and voice messages from allowed senders. Statuses, groups and repeats are skipped."""
    found = []
    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            for incoming in (change.get("value") or {}).get("messages") or []:
                message_id, sender = incoming.get("id"), incoming.get("from")
                if not message_id or not sender or message_id in _handled:
                    continue
                _handled.append(message_id)
                if incoming.get("type") in ("text", "audio") and _allowed(sender):
                    found.append(incoming)
    return found


def _answer(incoming: dict) -> None:
    sender = incoming["from"]
    try:
        if incoming["type"] == "text":
            reply = conversation.handle_message(sender, incoming["text"]["body"])["reply"]
        else:
            try:
                audio, mime = _download(incoming["audio"]["id"])
                text = speech.transcribe(audio, "voice.ogg", mime)
            except (speech.SpeechError, httpx.HTTPError) as exc:
                log.error("voice note not transcribed: %s", exc)
                querylog.append(sender, "🎤 (not understood)", replies.VOICE_FAILED)
                reply = replies.VOICE_FAILED
            else:
                reply = conversation.handle_message(sender, text, is_voice=True)["reply"]
        _send(sender, reply)
    except Exception:
        log.exception("could not answer WhatsApp message %s", incoming.get("id"))


def _download(media_id: str) -> tuple[bytes, str]:
    with _client() as client:
        meta = client.get(_graph(media_id))
        meta.raise_for_status()
        media = client.get(meta.json()["url"])
        media.raise_for_status()
        return media.content, meta.json().get("mime_type") or "audio/ogg"


def _send(to: str, text: str) -> None:
    with _client() as client:
        response = client.post(_graph(f"{_env('WHATSAPP_PHONE_NUMBER_ID')}/messages"), json={
            "messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text}})
        response.raise_for_status()


@data_loader.with_example_data
def _selftest():
    global _transport
    from fastapi.testclient import TestClient

    from ..main import app

    names = ("WHATSAPP_VERIFY_TOKEN", "WHATSAPP_APP_SECRET", "WHATSAPP_TOKEN", "WHATSAPP_PHONE_NUMBER_ID",
             "WHATSAPP_ALLOWED_NUMBERS", "WHATSAPP_GRAPH_VERSION", "ENGINE_MODE")
    saved = {name: os.environ.get(name) for name in names}
    os.environ.update(WHATSAPP_VERIFY_TOKEN="verify-me", WHATSAPP_APP_SECRET="app-secret",
                      WHATSAPP_TOKEN="token", WHATSAPP_PHONE_NUMBER_ID="555",
                      WHATSAPP_ALLOWED_NUMBERS="+91 98123 44521", WHATSAPP_GRAPH_VERSION="v21.0",
                      ENGINE_MODE="fake")
    real_log, real_recent, real_transcribe = querylog.LOG_PATH, querylog._recent, speech.transcribe
    import tempfile
    from pathlib import Path
    folder = tempfile.TemporaryDirectory()
    querylog.LOG_PATH, querylog._recent = Path(folder.name) / "queries.log", None
    sent = []

    def graph(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer token"
        if request.method == "POST":
            sent.append((str(request.url), json.loads(request.content)))
            return httpx.Response(200, json={"messages": [{"id": "out"}]})
        if request.url.path.endswith("/media-1"):
            return httpx.Response(200, json={"url": "https://media.example/file", "mime_type": "audio/ogg"})
        return httpx.Response(200, content=b"OggS")

    def post(payload, secret="app-secret"):
        body = json.dumps(payload).encode()
        signature = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        return client.post("/whatsapp/webhook", content=body,
                           headers={"X-Hub-Signature-256": signature, "Content-Type": "application/json"})

    def event(message_id, sender, **content):
        return {"entry": [{"changes": [{"value": {"messages": [{"id": message_id, "from": sender, **content}],
                                                  "statuses": [{"id": "x", "status": "read"}]}}]}]}

    _transport, speech.transcribe = httpx.MockTransport(graph), lambda *a, **k: "वीस क्विंटल कांदा निफाड"
    client = TestClient(app)
    try:
        ok = client.get("/whatsapp/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "verify-me",
                                                     "hub.challenge": "12345"})
        assert ok.status_code == 200 and ok.text == "12345"
        assert client.get("/whatsapp/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "wrong",
                                                       "hub.challenge": "1"}).status_code == 403

        text = event("wamid.1", "919812344521", type="text", text={"body": "20 poti kanda Niphad"})
        assert post(text, secret="wrong").status_code == 403 and not sent
        assert post(text).status_code == 200
        assert sent == [("https://graph.facebook.com/v21.0/555/messages",
                         {"messaging_product": "whatsapp", "to": "919812344521", "type": "text",
                          "text": {"body": "20 पोती कांदा (≈ 10 क्विंटल), निफाड. बरोबर? 1) हो 2) नाही"}})]
        post(text)                                                                # Meta retry: same id
        post(event("wamid.2", "919999999999", type="text", text={"body": "20 poti kanda Niphad"}))  # stranger
        post(event("wamid.3", "919812344521", type="image", image={"id": "i"}))   # not text or voice
        assert len(sent) == 1

        post(event("wamid.4", "919812344521", type="audio", audio={"id": "media-1"}))
        assert len(sent) == 2 and sent[1][1]["text"]["body"] == "20 क्विंटल कांदा, निफाड. बरोबर? 1) हो 2) नाही"
    finally:
        _transport, speech.transcribe = None, real_transcribe
        querylog.LOG_PATH, querylog._recent = real_log, real_recent
        folder.cleanup()
        conversation.state.clear("919812344521")
        for name, value in saved.items():
            os.environ.pop(name, None)
            if value is not None:
                os.environ[name] = value
    print("whatsapp cloud_api ok (mocked Graph API; test with the real test number before relying on it)")


if __name__ == "__main__":
    _selftest()
