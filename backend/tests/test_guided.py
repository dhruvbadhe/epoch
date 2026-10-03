"""Guided WhatsApp flow, through handle_message directly (no WhatsApp).
Run from the repo root: .venv/bin/python backend/tests/test_guided.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend import conversation, replies  # noqa: E402

ok = []


def check(name, cond, detail=""):
    ok.append(bool(cond))
    print(f"{'PASS' if cond else 'FAIL'}  {name}" + (f"\n      {detail}" if detail else ""))


def chat(sender, *texts):
    return [conversation.handle_message(sender, t) for t in texts]


def pick(reply, village):
    """The menu number for a village, read from the list we were shown."""
    return next(line.split(")")[0] for line in reply.splitlines() if village in line)


one = conversation.handle_message("g-one", "20 qtl onion Niphad")["reply"]
one_lines = one.splitlines()
check("one-message path unchanged (onion 20 qtl Niphad -> advice at once)",
      one.startswith("🔴 *Sell today → Pimpalgaon*") and "₹1,089" in one and "₹35" in one and "won 40 of 124" in one,
      one_lines[0])

for lang, number, village_name, cured, no_rush in [("mr", "1", "निफाड", "1", "3"), ("hi", "2", "निफाड", "1", "3"),
                                                    ("en", "3", "Niphad", "1", "3")]:
    s = f"g-run-{lang}"
    r = chat(s, "hi", number, "1", "20", "2")
    r += chat(s, pick(r[-1]["reply"], village_name), cured, no_rush, "1")
    final = r[-1]["reply"]
    numbers = all(x in final for x in ("₹1,089", "₹35")) and ("पिंपळगाव" in final or "Pimpalgaon" in final)
    note = ("124 पैकी फक्त 40" in final) or ("124 में से सिर्फ़ 40" in final) or ("won 40 of 124" in final)
    used = replies.guided("used_same", lang) in final
    check(f"full guided run in {lang} -> sell today, Pimpalgaon, 1,089, +35, note, answers line",
          r[-1]["state"] == "done" and numbers and note and used and r[0]["reply"] == replies.LANG_MENU,
          final.splitlines()[0])

r = chat("g-crop", "hello", "3", "mango")
check("unsupported crop -> covered crops, then the crop menu again",
      "onion, tomato and soybean" in r[-1]["reply"] and r[-1]["reply"].endswith(replies.crop_menu("en")),
      r[-1]["reply"].splitlines()[0])

r = chat("g-unit", "hello", "3", "1", "500")
check("missing unit -> asks kg or quintal", r[-1]["reply"] == replies.guided("unit_q", "en", value="500"),
      r[-1]["reply"].splitlines()[0])
r += chat("g-unit", "1")
check("500 + kg -> 5 quintal, then the village list", r[-1]["reply"].startswith(replies.guided("village_q", "en")))

r = chat("g-zero", "hello", "3", "1", "0 quintal")
check("zero quantity rejected", r[-1]["reply"].startswith(replies.guided("qty_bad", "en")))

r = chat("g-village", "hello", "3", "1", "20 quintal", "Atlantis")
check("unknown village -> says so and shows the list again",
      r[-1]["reply"].startswith(replies.guided("village_unknown", "en")), r[-1]["reply"].splitlines()[0])

r = chat("g-restart", "hello", "2", "1", "restart")
check("restart mid-flow -> language menu, chosen language forgotten",
      r[-1]["reply"] == replies.LANG_MENU and "g-restart" not in conversation._chosen_lang)
r = chat("g-restart2", "hello", "1", "1", "पुन्हा")
check("'पुन्हा' restarts too", r[-1]["reply"] == replies.LANG_MENU)

r = chat("g-edit", "hello", "3", "2", "20 quintal")
r += chat("g-edit", pick(r[-1]["reply"], "Manchar") if "Manchar" in r[-1]["reply"] else "Manchar", "1", "3", "2")
check("summary 2 (edit) -> crop menu in the same language", r[-1]["reply"] == replies.crop_menu("en"),
      r[-1]["reply"].splitlines()[0])

r = chat("g-soy", "hello", "3", "3", "50 quintal")
r += chat("g-soy", "1")
check("soybean skips freshness -> cash question", r[-1]["state"] == "awaiting_cash", r[-1]["reply"].splitlines()[0])

print(f"\n{sum(ok)} of {len(ok)} passed")
sys.exit(0 if all(ok) else 1)
