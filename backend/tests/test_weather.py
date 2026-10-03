"""Weather (display only): success, failure -> unavailable, cache, and /advise untouched. Open-Meteo is mocked.
Run from the repo root: .venv/bin/python backend/tests/test_weather.py
"""
import os
import sys
import tempfile
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ["SELLSMART_DB"] = str(Path(tempfile.mkdtemp()) / "test.db")   # not the demo database

from fastapi.testclient import TestClient  # noqa: E402

from backend import advice, weather  # noqa: E402
from backend.main import app  # noqa: E402

calls = []


def ok(request):
    calls.append(request)
    return httpx.Response(200, json={"current": {"time": "2025-09-21T09:00", "temperature_2m": 27.4,
                                                 "relative_humidity_2m": 68}})


niphad = advice.resolve_village("Niphad")
weather._cache.clear()
r = weather.current(niphad, client=httpx.Client(transport=httpx.MockTransport(ok)))
assert r["available"] and (r["temperature_c"], r["relative_humidity_pct"]) == (27.4, 68), r
assert r["label"] == "context only; it does not change the estimate" and r["attribution"] == "Weather data by Open-Meteo.com"
assert "latitude=20.0797" in str(calls[0].url)                       # the village's own coordinates
weather.current(niphad, client=httpx.Client(transport=httpx.MockTransport(ok)))
assert len(calls) == 1, "second call should come from the cache"
print("ok  current weather, labelled, with attribution; second call cached")

weather._cache.clear()
down = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(503)))
assert weather.current(niphad, client=down)["available"] is False
slow = httpx.Client(transport=httpx.MockTransport(lambda req: (_ for _ in ()).throw(httpx.ReadTimeout("slow"))))
assert weather.current(niphad, client=slow)["available"] is False
print("ok  failure and timeout -> available: false (shown as 'weather unavailable')")

client = TestClient(app)
a = client.post("/advise", json={"crop": "onion", "quantity_qtl": 20, "village": "Niphad"}).json()
assert "weather" not in a and (a["mandi"], a["net_per_qtl"], a["gain_vs_baseline"]) == ("Pimpalgaon", 1089, 35)
assert client.get("/weather", params={"village": "Atlantis"}).status_code == 400
print("ok  /advise has no weather and its numbers are unchanged")
print("all weather checks passed")
