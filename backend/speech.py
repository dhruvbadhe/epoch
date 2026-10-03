"""Voice note -> text, through a hosted speech-to-text service (nothing runs locally).

The provider is chosen by whichever key is in .env, first match wins:
  SARVAM_API_KEY  -> Sarvam (built for Indian languages)
  GROQ_API_KEY    -> Whisper large-v3 on Groq
  OPENAI_API_KEY  -> Whisper on OpenAI
STT_LANGUAGE is the language the farmer speaks: mr (default) or hi.
"""
from __future__ import annotations

import logging
import os

import httpx

from . import data_loader, replies

log = logging.getLogger("sellsmart.speech")

TIMEOUT_SECONDS = 60
_WHISPER = {"groq": ("https://api.groq.com/openai/v1", "whisper-large-v3"),
            "openai": ("https://api.openai.com/v1", "whisper-1")}
_SARVAM_URL, _SARVAM_MODEL = "https://api.sarvam.ai/speech-to-text", "saarika:v2.5"


class SpeechError(Exception):
    """The voice note could not be turned into text."""


def provider() -> str | None:
    for name in ("sarvam", "groq", "openai"):
        if os.getenv(f"{name.upper()}_API_KEY", "").strip():
            return name
    return None


def _language() -> str:
    language = os.getenv("STT_LANGUAGE", "mr").strip().lower()
    return language if language in ("mr", "hi") else "mr"


def _vocabulary(language: str) -> str:
    """Words we expect to hear; Whisper spells them better when it has seen them in the prompt."""
    words = [replies.CROP[c][language] for c in data_loader.CROPS]
    words += [replies.UNIT[u][language] for u in ("quintal", "bag", "crate", "ton", "kg")]
    words += [v["name_" + language] for v in data_loader.villages()]
    return ", ".join(dict.fromkeys(words))


def transcribe(audio: bytes, filename: str = "voice.ogg", content_type: str = "audio/ogg",
               client: httpx.Client | None = None, *, auto_language: bool = False,
               prompt: str | None = None) -> str:
    """The spoken text. Raises SpeechError if no provider is configured or the service fails.

    auto_language: let Whisper detect the language instead of sending STT_LANGUAGE.
    prompt: replaces the default vocabulary hint sent to Whisper."""
    name = provider()
    if name is None:
        raise SpeechError("no speech-to-text key in .env (SARVAM_API_KEY, GROQ_API_KEY or OPENAI_API_KEY)")
    if not audio:
        raise SpeechError("empty audio file")
    key = os.environ[f"{name.upper()}_API_KEY"].strip()
    language, model = _language(), os.getenv("STT_MODEL", "").strip()
    mime = (content_type or "").split(";")[0].strip()              # 'audio/ogg; codecs=opus' -> 'audio/ogg'
    if not mime.startswith("audio/"):
        mime = "audio/ogg"                                         # WhatsApp voice notes are Ogg Opus
    files = {"file": (filename or "voice.ogg", audio, mime)}

    if name == "sarvam":
        url, headers = _SARVAM_URL, {"api-subscription-key": key}
        data = {"model": model or _SARVAM_MODEL, "language_code": f"{language}-IN"}
        field = "transcript"
    else:
        base, default_model = _WHISPER[name]
        url, headers = f"{base}/audio/transcriptions", {"Authorization": f"Bearer {key}"}
        data = {"model": model or default_model, "response_format": "json",
                "temperature": "0", "prompt": prompt or _vocabulary(language)}
        if not auto_language:
            data["language"] = language
        field = "text"

    own_client = client is None
    client = client or httpx.Client(timeout=TIMEOUT_SECONDS)
    try:
        response = client.post(url, headers=headers, data=data, files=files)
        response.raise_for_status()
        text = (response.json().get(field) or "").strip()
    except httpx.HTTPStatusError as exc:
        raise SpeechError(f"{name} returned HTTP {exc.response.status_code}: {exc.response.text[:200]}") from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise SpeechError(f"{name} request failed: {type(exc).__name__}: {exc}") from exc
    finally:
        if own_client:
            client.close()
    if not text:
        raise SpeechError(f"{name} returned no text")
    log.info("transcribed %d bytes with %s: %r", len(audio), name, text)
    return text


def _selftest():
    saved = {k: os.environ.pop(k, None) for k in
             ("SARVAM_API_KEY", "GROQ_API_KEY", "OPENAI_API_KEY", "STT_LANGUAGE", "STT_MODEL")}
    seen = {}

    def service(request: httpx.Request) -> httpx.Response:
        seen.update(url=str(request.url), headers=request.headers, body=request.content)
        if "sarvam" in request.url.host:
            return httpx.Response(200, json={"transcript": " वीस पोती कांदा निफाड "})
        if request.headers["authorization"] == "Bearer bad":
            return httpx.Response(401, text="invalid key")
        return httpx.Response(200, json={"text": "बीस बोरी प्याज निफाड"})

    try:
        assert provider() is None
        try:
            transcribe(b"x")
            raise AssertionError("expected SpeechError")
        except SpeechError:
            pass
        with httpx.Client(transport=httpx.MockTransport(service)) as client:
            os.environ["GROQ_API_KEY"], os.environ["STT_LANGUAGE"] = "k", "hi"
            assert transcribe(b"OggS", "note.ogg", "audio/ogg; codecs=opus", client) == "बीस बोरी प्याज निफाड"
            assert seen["url"] == "https://api.groq.com/openai/v1/audio/transcriptions"
            assert b"whisper-large-v3" in seen["body"] and b'name="language"\r\n\r\nhi' in seen["body"]
            assert b"Content-Type: audio/ogg\r\n" in seen["body"]
            assert "निफाड".encode() in seen["body"], "village names should be in the prompt"

            os.environ["GROQ_API_KEY"] = "bad"
            try:
                transcribe(b"OggS", client=client)
                raise AssertionError("expected SpeechError")
            except SpeechError as exc:
                assert "401" in str(exc)

            os.environ["SARVAM_API_KEY"], os.environ["STT_LANGUAGE"] = "s", "mr"   # Sarvam wins when both are set
            assert provider() == "sarvam" and transcribe(b"OggS", client=client) == "वीस पोती कांदा निफाड"
            assert seen["url"] == _SARVAM_URL and seen["headers"]["api-subscription-key"] == "s"
            assert b"mr-IN" in seen["body"] and b"saarika:v2.5" in seen["body"]
    finally:
        for key, value in saved.items():
            os.environ.pop(key, None)
            if value is not None:
                os.environ[key] = value
    print("speech ok (request shapes only; test with a real voice note and a real key)")


if __name__ == "__main__":
    _selftest()
