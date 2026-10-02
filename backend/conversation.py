"""One handler for every channel: handle_message(sender, text) -> {"reply", "state", "parsed"}.

At most three questions, each asked only when it can change the answer:
  awaiting_confirm    echo-back (always for voice; for text only if something was guessed or missing)
  awaiting_freshness  only if the advice with the default hold limit is a hold
  awaiting_cash       only if a 3-day deadline would change the action, mandi or day
then the advice (state "done") and the conversation resets.
"""
from __future__ import annotations

import logging
import threading

from . import advice, data_loader, parser, querylog, replies, state

log = logging.getLogger("sellsmart.conversation")

CONFIRM, FRESHNESS, CASH, DONE = "awaiting_confirm", "awaiting_freshness", "awaiting_cash", "done"

_lock = threading.Lock()       # one message at a time; conversation memory is a plain dict


def handle_message(sender: str, text: str, is_voice: bool = False) -> dict:
    text = (text or "").strip()
    with _lock:
        result = _route(sender, text, is_voice)
    querylog.append(sender, ("🎤 " if is_voice else "") + text, result["reply"])
    return result


# ---------- routing -------------------------------------------------------

def _route(sender: str, text: str, is_voice: bool) -> dict:
    p = parser.parse(text)
    s = state.get(sender)
    if s is None or parser.is_new_request(p):           # nothing open, timed out, or a new crop message
        return _start(sender, p, is_voice)
    if s["state"] == CONFIRM:
        return _on_confirm(sender, s, text, p, is_voice)
    if s["state"] == FRESHNESS:
        understood, value = parser.freshness_answer(s["crop"], text)
        if not understood:
            return _again(sender, s)
        s["lot_condition"], s["freshness_done"] = value, True
        return _advance(sender, s)
    understood, days = parser.cash_answer(text)
    if not understood:
        return _again(sender, s)
    s["cash_known"], s["cash_days"] = True, days
    return _advance(sender, s)


def _start(sender: str, p: parser.Parsed, is_voice: bool) -> dict:
    state.clear(sender)
    has_quantity = p.qty_value is not None and p.qty_unit is not None    # a bare number isn't a request
    if p.crop is None and p.village is None and not has_quantity:
        return _reply(replies.help_message(p.lang, _example_village()), DONE, None)
    s = {"state": None, "pending": None, "question": None, "lang": p.lang,
         "crop": p.crop, "qty_value": p.qty_value, "qty_unit": p.qty_unit,
         "village": p.village, "village_guessed": bool(p.village) and not p.village_exact,
         "candidates": p.village_candidates, "voice": is_voice, "confirmed": False,
         "cash_known": p.cash_known, "cash_days": p.cash_days,
         "lot_condition": None, "freshness_done": False}
    return _collect(sender, s)


# ---------- step 1: what was said ------------------------------------------

def _collect(sender: str, s: dict) -> dict:
    """Ask for whatever is missing or unclear; once the request is settled, move on to the advice."""
    lang, qtl = s["lang"], _quantity(s)
    missing = []
    if s["crop"] is None:
        missing.append("crop")
    if s["qty_value"] is None or (s["crop"] and qtl is None):   # None qtl: no weight for that unit and crop
        s["qty_value"] = s["qty_unit"] = None
        missing.append("quantity")
    if s["village"] is None and not s["candidates"]:
        missing.append("village")
    if missing:
        return _ask(sender, s, CONFIRM, "missing", replies.ask_missing(missing, lang))

    echo = replies.echo(s["crop"], s["qty_value"], s["qty_unit"], qtl, lang)
    if s["village"] is None:                                    # a name was given but didn't match
        return _ask(sender, s, CONFIRM, "village", replies.village_options(echo, s["candidates"], lang))
    guessed = s["village_guessed"] or parser.unit_guessed(s["qty_unit"])
    if not s["confirmed"] and (s["voice"] or guessed):
        return _ask(sender, s, CONFIRM, "yesno", replies.confirm(echo, s["village"], lang))
    return _advance(sender, s)


def _on_confirm(sender: str, s: dict, text: str, p: parser.Parsed, is_voice: bool) -> dict:
    lang = s["lang"]
    if s["pending"] == "yesno":
        picked = parser.choice(text, 2)
        answer = (picked == 1) if picked else parser.yes_no(text)
        if answer is True:
            s["confirmed"] = True
            return _advance(sender, s)
        if answer is False:
            state.clear(sender)
            return _reply(replies.resend(lang, _example_village()), DONE, None)
        if _merge(s, p, is_voice, overwrite=True):              # a correction such as "30 poti"
            return _collect(sender, s)
        return _again(sender, s)

    if s["pending"] == "village":
        count = len(s["candidates"])
        picked = parser.choice(text, count + 1)
        if picked and picked <= count:                          # the echo was shown with the options
            s.update(village=s["candidates"][picked - 1], village_guessed=False, candidates=[],
                     confirmed=True)
            return _collect(sender, s)
        if picked == count + 1 or parser.is_other(text):
            state.clear(sender)
            return _reply(replies.not_covered(lang), DONE, s)

    if _merge(s, p, is_voice, overwrite=False):
        return _collect(sender, s)
    return _again(sender, s)


def _merge(s: dict, p: parser.Parsed, is_voice: bool, overwrite: bool) -> bool:
    """Fold a follow-up message into the open request. True if it changed anything."""
    changed = False
    if p.crop and p.crop != s["crop"] and (overwrite or s["crop"] is None):
        s["crop"], changed = p.crop, True
    if p.qty_value is not None and (overwrite or s["qty_value"] is None):
        s["qty_value"], s["qty_unit"], changed = p.qty_value, p.qty_unit, True
    if p.village and (overwrite or s["village"] is None):
        s.update(village=p.village, village_guessed=not p.village_exact, candidates=[])
        changed = True
    elif p.village_candidates and s["village"] is None:
        s["candidates"], changed = p.village_candidates, True
    if p.cash_known and not s["cash_known"]:
        s["cash_known"], s["cash_days"] = True, p.cash_days
    if changed:
        s["confirmed"] = False
        s["voice"] = s["voice"] or is_voice
    return changed


# ---------- steps 2-4: freshness, cash, advice ------------------------------

def _advance(sender: str, s: dict) -> dict:
    lang, seen = s["lang"], {}

    def advise(lot_condition, cash_days):
        key = (lot_condition, cash_days)
        if key not in seen:
            seen[key] = advice.get_advice(s["crop"], _quantity(s), s["village"]["village"],
                                          lot_condition=lot_condition,
                                          cash_needed_in_days=cash_days, lang=lang)
        return seen[key]

    def decision(a):
        return a.get("action"), a.get("mandi"), a.get("days")

    try:
        if not s["freshness_done"]:
            if advise(None, s["cash_days"])["action"] == "hold":
                return _ask(sender, s, FRESHNESS, None, replies.freshness_question(s["crop"], lang))
            s["freshness_done"] = True
        if not s["cash_known"]:
            no_deadline = advise(s["lot_condition"], None)
            if decision(no_deadline) != decision(advise(s["lot_condition"], parser.CASH_SOON)):
                return _ask(sender, s, CASH, None, replies.cash_question(lang))
            final = no_deadline
        else:
            final = advise(s["lot_condition"], s["cash_days"])
    except Exception as exc:        # engine ValueError, engine missing, bad data: the farmer still gets a reply
        log.exception("advice failed for %s: %s", _parsed(s), exc)
        state.clear(sender)
        return _reply(replies.error(lang), DONE, s)
    state.clear(sender)
    return _reply(final["message"], DONE, s)


# ---------- helpers -------------------------------------------------------

def _quantity(s: dict) -> float | None:
    if s["crop"] is None or s["qty_value"] is None:
        return None
    return parser.to_quintals(s["crop"], s["qty_value"], s["qty_unit"])


def _parsed(s: dict | None) -> dict:
    if s is None:
        return {"crop": None, "quantity_qtl": None, "village": None}
    return {"crop": s["crop"], "quantity_qtl": _quantity(s),
            "village": s["village"]["village"] if s["village"] else None}


def _reply(text: str, new_state: str, s: dict | None) -> dict:
    return {"reply": text, "state": new_state, "parsed": _parsed(s)}


def _ask(sender: str, s: dict, new_state: str, pending: str | None, question: str) -> dict:
    s.update(state=new_state, pending=pending, question=question)
    state.save(sender, s)
    return _reply(question, new_state, s)


def _again(sender: str, s: dict) -> dict:
    """The answer wasn't understood: repeat the open question."""
    state.save(sender, s)
    numbered = s["pending"] != "missing"
    text = replies.pick_number(s["question"], s["lang"]) if numbered else s["question"]
    return _reply(text, s["state"], s)


def _example_village() -> dict | None:
    villages = data_loader.villages()
    return villages[0] if villages else None


@data_loader.with_example_data
def _selftest():
    import os
    import tempfile
    from pathlib import Path

    os.environ["ENGINE_MODE"] = "fake"
    real_log, real_recent = querylog.LOG_PATH, querylog._recent
    folder = tempfile.TemporaryDirectory()
    querylog.LOG_PATH, querylog._recent = Path(folder.name) / "queries.log", None
    counter = iter(range(10_000))

    def chat(*messages, voice_first=False, sender=None):
        """Send messages from a fresh sender; return the list of results."""
        sender = sender or f"9100000{next(counter):05d}"
        return [handle_message(sender, m, is_voice=(voice_first and i == 0))
                for i, m in enumerate(messages)]

    try:
        # the contract example: bags -> echo-back -> freshness -> cash -> advice
        r = chat("20 poti kanda Niphad", "1", "हो", "3")
        assert r[0] == {"reply": "20 पोती कांदा (≈ 10 क्विंटल), निफाड. बरोबर? 1) हो 2) नाही",
                        "state": CONFIRM,
                        "parsed": {"crop": "onion", "quantity_qtl": 10, "village": "Niphad"}}, r[0]
        assert r[1]["state"] == FRESHNESS and r[1]["reply"] == replies.freshness_question("onion", "mr")
        assert r[2]["state"] == CASH and r[2]["reply"] == replies.cash_question("mr")
        assert r[3]["state"] == DONE and r[3]["reply"].startswith("🟢 *14 दिवस थांबा → पिंपळगाव*")
        assert r[3]["reply"] == advice.get_advice("onion", 10, "Niphad", lot_condition=True)["message"]

        # nothing guessed: no echo-back; needing cash in 2-3 days flips the advice to sell now
        r = chat("२० क्विंटल कांदा निफाड", "१", "१")
        assert [x["state"] for x in r] == [FRESHNESS, CASH, DONE]
        assert r[2]["reply"].startswith("🔴 *आजच विका → पिंपळगाव*")

        # the deadline is already in the first message: no cash question, and no hold to ask freshness about
        r = chat("20 quintal kanda Niphad 2 divsat paise have")
        assert r[0]["state"] == DONE and r[0]["reply"].startswith("🔴"), r[0]

        # uncured onion can't be held 14 days, so the answer is sell now and cash can't change it
        r = chat("20 क्विंटल कांदा निफाड", "नाही")
        assert [x["state"] for x in r] == [FRESHNESS, DONE] and r[1]["reply"].startswith("🔴")

        # tomato in crates: echo-back only (default limit rules out the hold, so nothing else to ask)
        r = chat("30 crate tomato Narayangaon", "ho")
        assert r[0]["reply"] == "30 क्रेट टोमॅटो (≈ 6 क्विंटल), नारायणगाव. बरोबर? 1) हो 2) नाही"
        assert r[1]["state"] == DONE and r[1]["parsed"]["quantity_qtl"] == 6

        # voice notes always get the echo-back, even when nothing was guessed
        r = chat("वीस क्विंटल कांदा निफाड", "एक", voice_first=True)
        assert r[0]["reply"] == "20 क्विंटल कांदा, निफाड. बरोबर? 1) हो 2) नाही" and r[1]["state"] == FRESHNESS
        assert querylog.recent()[1]["text"] == "🎤 वीस क्विंटल कांदा निफाड"

        # Hindi in, Hindi out; a fuzzy village is confirmed
        r = chat("10 quintal pyaz Nifad", "haan")
        assert r[0]["reply"] == "10 क्विंटल प्याज, निफाड. सही है? 1) हाँ 2) नहीं"
        assert r[1]["reply"] == replies.freshness_question("onion", "hi")

        # a village we don't know: top 3 + other
        r = chat("20 quintal kanda Pune", "4")
        assert r[0]["state"] == CONFIRM and r[0]["reply"].splitlines()[-1] == "4) इतर"
        assert r[1] == {"reply": replies.not_covered("mr"), "state": DONE,
                        "parsed": {"crop": "onion", "quantity_qtl": 20, "village": None}}
        r = chat("20 quintal kanda Pune", "2")
        assert r[1]["state"] == FRESHNESS and r[1]["parsed"]["village"] is not None
        r = chat("20 quintal kanda Pune", "Yeola")
        assert r[1]["state"] == FRESHNESS and r[1]["parsed"]["village"] == "Yeola"

        # missing pieces are asked for, then merged
        r = chat("kanda Niphad", "20", "ho")
        assert r[0]["state"] == CONFIRM and r[0]["reply"] == replies.ask_missing(["quantity"], "mr")
        assert r[1]["reply"] == "20 क्विंटल कांदा, निफाड. बरोबर? 1) हो 2) नाही" and r[2]["state"] == FRESHNESS
        r = chat("20 quintal gahu Niphad", "kanda")              # a crop outside our three
        assert "कांदा, टोमॅटो आणि सोयाबीन" in r[0]["reply"] and r[1]["state"] == FRESHNESS
        r = chat("30 crate kanda Niphad", "15 quintal")          # no crate weight for onion
        assert r[0]["reply"] == replies.ask_missing(["quantity"], "mr") and r[1]["state"] == FRESHNESS

        # no -> send again; a correction instead of yes/no is taken; nonsense repeats the question
        r = chat("20 poti kanda Niphad", "nahi")
        assert r[1]["state"] == DONE and r[1]["reply"] == replies.resend("mr", _example_village())
        r = chat("20 poti kanda Niphad", "30 poti")
        assert r[1]["reply"].startswith("30 पोती कांदा (≈ 15 क्विंटल), निफाड")
        r = chat("20 poti kanda Niphad", "kay?", "1", "maybe", "2")
        assert r[1]["state"] == CONFIRM and r[1]["reply"].endswith(r[0]["reply"]) and r[1]["reply"] != r[0]["reply"]
        assert r[3]["state"] == FRESHNESS and r[3]["reply"].endswith(r[2]["reply"]) and r[4]["state"] == DONE

        # greetings get help; a new crop message restarts; an open question times out after 30 minutes
        assert chat("hello")[0] == {"reply": replies.help_message("en", _example_village()), "state": DONE,
                                    "parsed": {"crop": None, "quantity_qtl": None, "village": None}}
        r = chat("20 poti kanda Niphad", "5 ton soyabean Ausa")
        assert r[1]["parsed"] == {"crop": "soybean", "quantity_qtl": 50, "village": "Ausa"}
        chat("20 poti kanda Niphad", sender="timeout-test")
        state._sessions["timeout-test"]["updated_at"] -= state.TIMEOUT_SECONDS + 1
        late = chat("1", sender="timeout-test")[0]                       # the "1" is no longer an answer
        assert late["state"] == DONE and late["reply"] == replies.help_message("mr", _example_village())

        log_lines = querylog.recent()
        assert log_lines[0]["sender"].startswith("…") and len(log_lines) == querylog.KEEP
    finally:
        querylog.LOG_PATH, querylog._recent = real_log, real_recent
        folder.cleanup()
        del os.environ["ENGINE_MODE"]
    print("conversation ok")


if __name__ == "__main__":
    _selftest()
