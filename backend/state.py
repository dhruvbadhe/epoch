"""Per-sender conversation memory: a plain in-memory dict.

It lives in this process only, so run one worker and no auto-reload during the demo.
"""
from __future__ import annotations

import time

# The spec: an open question times out after 30 minutes.
TIMEOUT_SECONDS = 30 * 60

_sessions: dict[str, dict] = {}


def get(sender: str, now: float | None = None) -> dict | None:
    """The sender's open conversation, or None if there is none or it has timed out."""
    session = _sessions.get(sender)
    if session is None:
        return None
    if (now if now is not None else time.time()) - session["updated_at"] > TIMEOUT_SECONDS:
        del _sessions[sender]
        return None
    return session


def save(sender: str, session: dict, now: float | None = None) -> None:
    session["updated_at"] = now if now is not None else time.time()
    _sessions[sender] = session


def clear(sender: str) -> None:
    _sessions.pop(sender, None)


def _selftest():
    save("t1", {"state": "awaiting_confirm"}, now=1000)
    assert get("t1", now=1000 + TIMEOUT_SECONDS)["state"] == "awaiting_confirm"
    assert get("t1", now=1001 + TIMEOUT_SECONDS) is None and "t1" not in _sessions
    save("t2", {"state": "awaiting_cash"})
    clear("t2")
    clear("t2")
    assert get("t2") is None
    print("state ok")


if __name__ == "__main__":
    _selftest()
