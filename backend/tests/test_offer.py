"""Offer check after advice, through handle_message directly (no WhatsApp).
Run from the repo root: .venv/bin/python backend/tests/test_offer.py
"""
import math
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ["SELLSMART_DB"] = str(Path(tempfile.mkdtemp()) / "test.db")   # not the demo database

from backend import advice, conversation, replies  # noqa: E402

ok = []


def check(name, cond, detail=""):
    ok.append(bool(cond))
    print(f"{'PASS' if cond else 'FAIL'}  {name}" + (f"\n      {detail}" if detail else ""))


def say(sender, text):
    return conversation.handle_message(sender, text)["reply"]


a = advice.get_advice("onion", 20, "Niphad", lang="en")            # the engine's response for this lot
why, base = a["why"], a["baseline_today"]
sellable = (why["price"] - why["spoilage_loss"]) / why["price"]
costs = why["transport"] + why["storage"] + why["fees"]
break_even = (base["net"] + costs) / sellable                       # offer at which both nets are equal
print(f"engine: {a['mandi']} price {why['price']}, costs {costs}, sellable {sellable:.4f}; "
      f"nearest {base['mandi']} net {base['net']} -> break-even offer ₹{break_even:.0f}/qtl\n")

r = say("offer-1", "20 qtl onion Niphad")
check("advice ends with the offer prompt", r.endswith(replies.offer_prompt("en")), r.splitlines()[-1])

same = say("offer-1", f"{why['price']} per quintal")
check("offer = the engine's own price -> the engine's own net", f"In hand: ₹{a['net_per_qtl']:,}/quintal" in same,
      same.splitlines()[1])

above = math.ceil(break_even) + 100
r = say("offer-1", f"{above} per quintal")
net = round(above * sellable - costs)
diff = (net - base["net"]) * 20
check(f"offer above break-even (₹{above}/qtl) -> still beats the nearest mandi",
      "still beats" in r and f"₹{net:,}/quintal" in r and f"+₹{diff:,}" in r, r.replace("\n", " | "))

below_kg = math.floor(break_even) // 100 - 1                           # a per-kg offer below break-even
r = say("offer-1", f"{below_kg} per kg")
net = round(below_kg * 100 * sellable - costs)
diff = (net - base["net"]) * 20
check(f"offer below break-even ({below_kg} per kg = ₹{below_kg * 100}/qtl) -> nearest mandi is better",
      "nearest mandi (Lasalgaon (Niphad)) is better" in r and f"₹{net:,}/quintal" in r and f"−₹{abs(diff):,}" in r,
      r.replace("\n", " | "))

r = say("offer-2", "2300 per quintal")
check("a price with no advice before it is not treated as an offer", "Based on your quoted price" not in r,
      r.splitlines()[0])

print(f"\n{sum(ok)} of {len(ok)} passed")
sys.exit(0 if all(ok) else 1)
