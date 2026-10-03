"""Reply language: Latin script without Hindi/Marathi markers is English; Devanagari is Marathi or Hindi
by marker words; an explicit choice wins; a bare "1" keeps the conversation's language.
Calls handle_message directly (no WhatsApp). Run from the repo root:
    .venv/bin/python backend/tests/test_language.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend import conversation, parser  # noqa: E402

ok = []


def check(name, cond, detail=""):
    ok.append(bool(cond))
    print(f"{'PASS' if cond else 'FAIL'}  {name}" + (f"\n      {detail}" if detail else ""))


def reply(sender, text):
    return conversation.handle_message(sender, text)["reply"]


r = reply("lang-en", "20 qtl tomato, Manchar")
check("'20 qtl tomato, Manchar' -> English", r.startswith("🔴 *Sell today → Pimpalgaon*") and "₹1,597" in r, r.splitlines()[0])
r = reply("lang-mr", "20 क्विंटल कांदा, निफाड")
check("'20 क्विंटल कांदा, निफाड' -> Marathi", r.startswith("🔴 *आजच विका → पिंपळगाव*") and "₹1,089" in r, r.splitlines()[0])
r = reply("lang-hi", "10 quintal pyaz Yeola")
check("'10 quintal pyaz Yeola' -> Hindi", parser.detect_lang("10 quintal pyaz Yeola") == "hi" and "हाथ में" in r,
      r.splitlines()[0])
check("'20 poti kanda Niphad' (romanised Marathi) -> Marathi", parser.detect_lang("20 poti kanda Niphad") == "mr")
check("'hello' -> guided language menu", reply("lang-hello", "hello").startswith("भाषा निवडा / भाषा चुनें / Choose"))

# a bare "1" answering an English question stays English
first = reply("lang-1", "30 crate tomato Narayangaon")
second = reply("lang-1", "1")
check("bare '1' keeps the conversation's language", first.endswith("Correct? 1) yes 2) no") and "Sell today" in second,
      second.splitlines()[0])

# an explicit choice overrides detection until it is cleared
conversation.choose_lang("lang-pick", "hi")
r = reply("lang-pick", "20 qtl tomato, Manchar")
check("explicit choice (hi) beats detection (en)", "आज ही बेचें" in r, r.splitlines()[0])
conversation.choose_lang("lang-pick", None)
check("cleared choice -> detection again", reply("lang-pick", "20 qtl tomato, Manchar").startswith("🔴 *Sell today"))

print(f"\n{sum(ok)} of {len(ok)} passed")
sys.exit(0 if all(ok) else 1)
