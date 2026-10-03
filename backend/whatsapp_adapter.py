"""
SahiDaam WhatsApp adapter. All three options are free:

  WA_PROVIDER=webjs      (default) Node bridge in whatsapp-bridge/ posts to /wa-bridge.
                         Text + voice, any phone can message. Unofficial: use a spare SIM.
  WA_PROVIDER=360dialog  360dialog sandbox (no Facebook login; text only; your own phone only)
  WA_PROVIDER=meta       Meta WhatsApp Cloud API (needs developers.facebook.com)

Mounted by backend/main.py (app.include_router(whatsapp_adapter.router)); env comes from backend/.env.
Replies come from the backend's conversation.handle_message, keyed by the sender's WhatsApp ID.
Voice notes: downloaded, sent as Ogg to Groq whisper-large-v3 (speech.transcribe), then the same path.

Env vars for 360dialog:
    D360_API_KEY        the key 360dialog sends you after you WhatsApp "START" to +55 11 4673-3492
Env vars for meta:
    WA_TOKEN, WA_PHONE_NUMBER_ID, WA_VERIFY_TOKEN, optional WA_APP_SECRET, WA_API_VERSION
Optional for webjs:
    WA_BRIDGE_SECRET    if set, the bridge must send the same value (set it in both places)
Either 360dialog or meta:
    WA_DRY_RUN=1        log replies instead of sending them (saves the sandbox's 200-message quota)

Needs: pip install fastapi httpx
"""

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import os

import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import PlainTextResponse

from . import conversation, replies, speech

log = logging.getLogger("whatsapp")

PROVIDER = os.getenv("WA_PROVIDER", "webjs").lower()
DRY_RUN = os.getenv("WA_DRY_RUN") == "1"
GRAPH = f"https://graph.facebook.com/{os.getenv('WA_API_VERSION', 'v23.0')}"

D360_BASE = "https://waba-sandbox.360dialog.io/v1"
if PROVIDER == "360dialog":
    SEND_URL = f"{D360_BASE}/messages"
    AUTH = {"D360-API-KEY": os.environ["D360_API_KEY"]}
    VERIFY_TOKEN = ""
    APP_SECRET = None
elif PROVIDER == "meta":
    SEND_URL = f"{GRAPH}/{os.environ['WA_PHONE_NUMBER_ID']}/messages"
    AUTH = {"Authorization": f"Bearer {os.environ['WA_TOKEN']}"}
    VERIFY_TOKEN = os.environ["WA_VERIFY_TOKEN"]
    APP_SECRET = os.getenv("WA_APP_SECRET")
else:  # webjs: replies go back through the Node bridge, nothing to configure here
    SEND_URL, AUTH, VERIFY_TOKEN, APP_SECRET = None, {}, "", None

# Bilingual fallbacks (have a native speaker check these, same as §4 replies)
MSG_UNSUPPORTED = "कृपया मजकूर किंवा व्हॉइस नोट पाठवा. / कृपया टेक्स्ट या वॉइस नोट भेजें।"
MSG_ERROR = "माफ करा, काहीतरी चूक झाली. पुन्हा प्रयत्न करा. / माफ़ कीजिए, कुछ गड़बड़ हुई। फिर से भेजें।"

router = APIRouter()
_seen_ids: set[str] = set()  # providers retry webhooks; dedupe on message id


# Whisper hint for crop, unit and village names; no language is forced.
VOICE_HINT = "कांदा, टोमॅटो, सोयाबीन, क्विंटल, निफाड, सिन्नर, लासलगाव, पिंपळगाव"


def handle_message(user_id: str, text: str) -> str:
    """Thin wrapper: the backend's conversation (parser, state, templates), keyed on user_id."""
    return conversation.handle_message(user_id, text)["reply"]


def handle_voice(user_id: str, audio: bytes) -> str:
    """Ogg voice note -> Groq transcript -> the same conversation path as text."""
    try:
        text = speech.transcribe(audio, "voice.ogg", "audio/ogg", auto_language=True, prompt=VOICE_HINT)
    except speech.SpeechError as exc:
        log.error("voice note from %s not transcribed: %s", user_id[-4:], exc)
        return replies.VOICE_FAILED
    return conversation.handle_message(user_id, text, is_voice=True)["reply"]


# --- Meta's one-time webhook verification (not used by 360dialog)
@router.get("/webhook")
def verify(request: Request):
    p = request.query_params
    if VERIFY_TOKEN and p.get("hub.mode") == "subscribe" and p.get("hub.verify_token") == VERIFY_TOKEN:
        return PlainTextResponse(p.get("hub.challenge", ""))
    raise HTTPException(status_code=403, detail="verify token mismatch")


# --- Incoming events. Return 200 immediately; do the slow work in the background.
@router.post("/webhook")
async def receive(request: Request, background: BackgroundTasks):
    raw = await request.body()

    if APP_SECRET:
        expected = "sha256=" + hmac.new(APP_SECRET.encode(), raw, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(request.headers.get("X-Hub-Signature-256", ""), expected):
            raise HTTPException(status_code=403, detail="bad signature")

    data = json.loads(raw or b"{}")
    # Cloud API shape (entry/changes/value) or the older top-level shape ({"messages": [...]})
    values = [change.get("value", {}) for entry in data.get("entry", []) for change in entry.get("changes", [])]
    values += [data] if "messages" in data else []
    for value in values:
        # value["statuses"] (sent / delivered / read) arrive here too; ignore them
        for msg in value.get("messages", []):
            if msg["id"] in _seen_ids:
                continue
            if len(_seen_ids) > 5000:
                _seen_ids.clear()
            _seen_ids.add(msg["id"])
            background.add_task(process_message, msg)
    return {"ok": True}


async def process_message(msg: dict) -> None:
    # 360dialog identifies you by "from_user_id" instead of "from" if your number wasn't shared
    by_user_id = "from" not in msg
    user = msg.get("from") or msg.get("from_user_id")
    try:
        kind = msg.get("type")
        if kind == "text":
            reply = await asyncio.to_thread(handle_message, user, msg["text"]["body"])
        elif kind in ("audio", "voice"):  # WhatsApp voice notes arrive as type "audio" (OGG/Opus)
            media = msg[kind]
            log.info("voice note %s: fields %s", msg.get("id"), sorted(media))
            audio = await download_voice_note(media)
            reply = await asyncio.to_thread(handle_voice, user, audio)
        else:
            reply = MSG_UNSUPPORTED
        await send_text(user, reply, by_user_id)
    except Exception:
        log.exception("failed to handle message %s", msg.get("id"))
        await send_text(user, MSG_ERROR, by_user_id)


async def download_voice_note(media: dict) -> bytes:
    """The voice note's bytes (Ogg/Opus, sent to speech-to-text as it is).

    A direct "url" in the webhook is used first. Otherwise 360dialog: GET /v1/media/{id} (bytes, or JSON with
    a download url); Meta: GET /{id} -> short-lived URL (5 min) -> bytes."""
    media_id = media["id"]
    async with httpx.AsyncClient(timeout=30) as client:
        if media.get("url"):
            direct = await client.get(media["url"], headers=AUTH)
            log.info("voice note download from webhook url (%s): HTTP %s", httpx.URL(media["url"]).host,
                     direct.status_code)
            if direct.status_code == 200:
                return direct.content
        first = await client.get(f"{D360_BASE}/media/{media_id}" if PROVIDER == "360dialog" else f"{GRAPH}/{media_id}",
                                 headers=AUTH)
        first.raise_for_status()
        if not first.headers.get("content-type", "").startswith("application/json"):
            return first.content
        audio = await client.get(first.json()["url"], headers=AUTH)  # the key is required here too
        audio.raise_for_status()
    return audio.content


async def send_text(to: str, body: str, by_user_id: bool = False) -> None:
    payload = {"messaging_product": "whatsapp", "type": "text", "text": {"body": body[:4096]}}
    if by_user_id:
        payload["recipient"] = to
    else:
        payload.update(recipient_type="individual", to=to)

    if DRY_RUN:
        log.warning("[dry run] reply to %s:\n%s", to, body)
        return
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(SEND_URL, headers=AUTH, json=payload)
    if r.status_code >= 400:
        log.error("send failed %s: %s", r.status_code, r.text)


# --- whatsapp-web.js bridge (WA_PROVIDER=webjs). Runs on the same machine; no tunnel needed.
@router.post("/wa-bridge")
async def wa_bridge(request: Request):
    secret = os.getenv("WA_BRIDGE_SECRET")
    if secret and request.headers.get("X-Bridge-Secret") != secret:
        raise HTTPException(status_code=403, detail="bad bridge secret")
    data = await request.json()
    user = data["user"]
    try:
        if data.get("audio_b64"):
            reply = await asyncio.to_thread(handle_voice, user, base64.b64decode(data["audio_b64"]))
        elif data.get("text"):
            reply = await asyncio.to_thread(handle_message, user, data["text"])
        else:
            reply = MSG_UNSUPPORTED
    except Exception:
        log.exception("bridge message from %s failed", user)
        reply = MSG_ERROR
    return {"reply": reply}
