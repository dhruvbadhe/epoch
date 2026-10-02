"""Query log: every WhatsApp exchange appended to backend/queries.log as JSON lines (not committed).

The sender is masked before it is written, so no full phone number is kept on disk.
"""
from __future__ import annotations

import json
import logging
import threading
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path

log = logging.getLogger("sellsmart.queries")

LOG_PATH = Path(__file__).resolve().parent / "queries.log"
KEEP = 20
IST = timezone(timedelta(hours=5, minutes=30))

_lock = threading.Lock()
_recent: deque | None = None


def mask(sender: str) -> str:
    """'919812344521' -> '…4521'."""
    digits = "".join(c for c in str(sender) if c.isdigit()) or str(sender)
    return "…" + digits[-4:]


def _load() -> deque:
    recent: deque = deque(maxlen=KEEP)
    try:
        with LOG_PATH.open(encoding="utf-8") as f:
            for line in f:
                try:
                    recent.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        pass
    return recent


def append(sender: str, text: str, reply: str) -> None:
    global _recent
    entry = {"time": datetime.now(IST).isoformat(timespec="seconds"), "sender": mask(sender),
             "text": text, "reply": reply}
    with _lock:
        if _recent is None:
            _recent = _load()
        _recent.append(entry)
        try:
            with LOG_PATH.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError as exc:                      # the reply still goes out
            log.error("could not write %s: %s", LOG_PATH, exc)


def recent() -> list[dict]:
    """The last 20 exchanges, newest first."""
    global _recent
    with _lock:
        if _recent is None:
            _recent = _load()
        return list(reversed(_recent))


def _selftest():
    global LOG_PATH, _recent
    import tempfile

    assert mask("919812344521") == "…4521" and mask("919812344521@c.us") == "…4521"
    real_path, real_recent = LOG_PATH, _recent
    with tempfile.TemporaryDirectory() as folder:
        LOG_PATH, _recent = Path(folder) / "queries.log", None
        try:
            for i in range(KEEP + 5):
                append("919812344521", f"q{i}", f"r{i}")
            got = recent()
            assert len(got) == KEEP and got[0]["text"] == f"q{KEEP + 4}" and got[0]["sender"] == "…4521"
            assert got[0]["time"].endswith("+05:30")
            _recent = None                           # a restart re-reads the file
            assert [e["text"] for e in recent()] == [e["text"] for e in got]
            assert "9198" not in LOG_PATH.read_text(encoding="utf-8")
        finally:
            LOG_PATH, _recent = real_path, real_recent
    print("querylog ok")


if __name__ == "__main__":
    _selftest()
