"""Freshness lookup: the window equals config.yaml hold_limit_days for every crop and answer, and /advise numbers
are unchanged by the new field. Run from the repo root: .venv/bin/python backend/tests/test_freshness.py
"""
import os
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ["SELLSMART_DB"] = str(Path(tempfile.mkdtemp()) / "test.db")   # not the demo database

from fastapi.testclient import TestClient  # noqa: E402

from backend import advice, freshness  # noqa: E402
from backend.main import app  # noqa: E402

limits = yaml.safe_load((ROOT / "config.yaml").read_text())["hold_limit_days"]
cases = [("tomato", None, limits["tomato"]["default"])] + \
    [("tomato", i, v) for i, v in enumerate(limits["tomato"]["answers"])] + \
    [(c, None, limits[c]["default"]) for c in ("onion", "soybean")] + \
    [(c, a, v) for c in ("onion", "soybean") for a, v in limits[c]["answers"].items()]
for crop, answer, expected in cases:
    for lang in ("en", "mr", "hi"):
        f = freshness.estimate(crop, answer, lang)
        assert f["estimated_window_days"] == expected, (crop, answer, f["estimated_window_days"], expected)
        assert f["basis"] == "Based on general post-harvest guidance; local accuracy not evaluated"
        assert 1 <= len(f["reasons"]) <= 2 and f["missing"] and len(f["references"]) == 5
print(f"ok  window = config.yaml hold_limit_days for {len(cases)} crop/answer cases in 3 languages")

client = TestClient(app)
for crop, village, lot in [("onion", "Niphad", None), ("onion", "Niphad", False), ("tomato", "Manchar", 1),
                           ("soybean", "Niphad", True)]:
    body = {"crop": crop, "quantity_qtl": 20, "village": village, "lot_condition": lot, "lang": "en"}
    got = client.post("/advise", json=body).json()
    fresh = got.pop("freshness")
    same = advice.get_advice(crop, 20, village, lot_condition=lot, lang="en")      # the path without the field
    assert got == same, (crop, lot)
    assert fresh["estimated_window_days"] == got["hold_limit_days"], (fresh, got["hold_limit_days"])
a = client.post("/advise", json={"crop": "onion", "quantity_qtl": 20, "village": "Niphad"}).json()
assert (a["action"], a["mandi"], a["net_per_qtl"], a["gain_vs_baseline"]) == ("sell_now", "Pimpalgaon", 1089, 35)
print("ok  /advise is unchanged apart from the new 'freshness' field (onion 1089 / +35)")
print("all freshness checks passed")
