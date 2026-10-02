"""Runs every module's self-test, then exercises the API end to end.

    python -m backend.selftest

No network, no keys and no engine needed: example data, a stub engine and temporary data files
stand in. The real queries.log, .env and data/ are not touched.
"""
import json
import os
import sys
import tempfile
import types
from pathlib import Path

for stream in (sys.stdout, sys.stderr):
    stream.reconfigure(encoding="utf-8")        # Devanagari and emoji on a Windows console
os.environ["ENGINE_MODE"] = "fake"

from fastapi.testclient import TestClient  # noqa: E402

from . import (advice, conversation, data_loader, engine_api, lookups, parser, querylog,  # noqa: E402
               replies, speech, state, tips)
from .main import ENGINE_HEADER, app  # noqa: E402
from .whatsapp import cloud_api  # noqa: E402

EXAMPLE = {"crop": "onion", "quantity_qtl": 10, "village": "Niphad", "lot_condition": None,
           "cash_needed_in_days": None, "blocked_mandis": [], "overrides": None, "lang": "mr"}
client = TestClient(app, raise_server_exceptions=False)


def bad(response, field, status=400):
    body = response.json()
    assert response.status_code == status, (response.status_code, body)
    assert set(body) == {"error", "field"} and body["field"] == field and body["error"], body
    assert "Traceback" not in response.text
    return body


def test_advise():
    r = client.post("/advise", json=EXAMPLE)
    body = r.json()
    assert r.status_code == 200 and r.headers[ENGINE_HEADER] == "fake"
    engine_part = {k: v for k, v in body.items() if k not in ("storage_tip", "message", "notes")}
    assert engine_part == {k: v for k, v in data_loader.fake("advise.json").items() if k != "notes"}
    assert body["storage_tip"] == tips.storage_tip("onion", "mr")
    assert body["message"].splitlines()[0] == "🟢 *14 दिवस थांबा → पिंपळगाव*"

    sell = client.post("/advise", json={**EXAMPLE, "cash_needed_in_days": 3, "lang": "en"}).json()
    assert sell["action"] == "sell_now" and sell["storage_tip"] is None and sell["break_even_price"] is None
    assert sell["message"].splitlines()[0] == "🔴 *Sell today → Pimpalgaon*"
    minimal = client.post("/advise", json={"crop": "tomato", "quantity_qtl": "2.5", "village": "निफाड"})
    assert minimal.status_code == 200 and minimal.json()["hold_limit_days"] == 4
    assert client.post("/advise", json={**EXAMPLE, "crop": "tomato", "lot_condition": 2}).json()["hold_limit_days"] == 0
    assert client.post("/advise", json={**EXAMPLE, "overrides": {"fees_per_qtl": 5}}).json()["assumptions_default"] is False
    rerouted = client.post("/advise", json={**EXAMPLE, "blocked_mandis": ["Pimpalgaon"]}).json()
    assert rerouted["mandi"] == "Lasalgaon" and "जवळचा बाजारच सर्वोत्तम आहे" in rerouted["message"]

    bad(client.post("/advise", json={**EXAMPLE, "village": "Atlantis"}), "village")
    bad(client.post("/advise", json={**EXAMPLE, "crop": "wheat"}), "crop")
    bad(client.post("/advise", json={**EXAMPLE, "quantity_qtl": 0}), "quantity_qtl")
    bad(client.post("/advise", json={**EXAMPLE, "quantity_qtl": "lots"}), "quantity_qtl")
    bad(client.post("/advise", json={**EXAMPLE, "lot_condition": 1}), "lot_condition")
    bad(client.post("/advise", json={**EXAMPLE, "crop": "tomato", "lot_condition": True}), "lot_condition")
    bad(client.post("/advise", json={**EXAMPLE, "cash_needed_in_days": -1}), "cash_needed_in_days")
    bad(client.post("/advise", json={**EXAMPLE, "cash_needed_in_days": "soon"}), "cash_needed_in_days")
    bad(client.post("/advise", json={**EXAMPLE, "blocked_mandis": ["Atlantis"]}), "blocked_mandis")
    bad(client.post("/advise", json={**EXAMPLE, "lang": "fr"}), "lang")
    bad(client.post("/advise", json={"crop": "onion", "quantity_qtl": 10}), "village")
    bad(client.post("/advise", content="{not json", headers={"Content-Type": "application/json"}), None)
    # the engine's own ValueError (here: every mandi blocked) is a 400 too
    bad(client.post("/advise", json={**EXAMPLE, "blocked_mandis": ["Pimpalgaon", "Lasalgaon"]}), None)


def test_fpo_plan():
    lot = {"member": "A", "crop": "onion", "quantity_qtl": 40, "village": "Niphad",
           "lot_condition": True, "cash_needed_in_days": 3}
    request = {"lots": [lot], "blocked_mandis": [], "mandi_cap_qtl_per_day": None,
               "collection_centre": None, "overrides": None}
    r = client.post("/fpo/plan", json=request)
    assert r.status_code == 200 and r.json() == data_loader.fake("fpo_plan.json")
    assert client.post("/fpo/plan", json={**request, "collection_centre": "Niphad"}).status_code == 200
    assert client.post("/fpo/plan", json={"lots": [{**lot, "member": 7}]}).status_code == 200
    bad(client.post("/fpo/plan", json={**request, "lots": []}), "lots")
    bad(client.post("/fpo/plan", json={**request, "lots": [{**lot, "village": "Atlantis"}]}), "lots.0.village")
    bad(client.post("/fpo/plan", json={**request, "lots": [lot, {**lot, "crop": "wheat"}]}), "lots.1.crop")
    bad(client.post("/fpo/plan", json={**request, "lots": [{**lot, "lot_condition": 2}]}), "lots.0.lot_condition")
    bad(client.post("/fpo/plan", json={**request, "collection_centre": "Atlantis"}), "collection_centre")
    bad(client.post("/fpo/plan", json={**request, "collection_centre": {"name": "X"}}), "collection_centre")
    bad(client.post("/fpo/plan", json={**request, "mandi_cap_qtl_per_day": 0}), "mandi_cap_qtl_per_day")


def test_lookups():
    assert client.get("/backtest", params={"crop": "onion"}).json() == data_loader.fake("backtest.json")
    assert client.get("/backtest", params={"crop": "soybean"}).json()["crop"] == "soybean"
    bad(client.get("/backtest"), "crop")
    bad(client.get("/backtest", params={"crop": "wheat"}), "crop")

    assert client.get("/forecast", params={"crop": "onion", "mandi": "lasalgaon"}).json() == data_loader.fake("forecast.json")
    bad(client.get("/forecast", params={"crop": "onion", "mandi": "Atlantis"}), "mandi")
    bad(client.get("/forecast", params={"crop": "onion"}), "mandi")

    mandis = client.get("/mandis").json()
    assert set(mandis[0]) == {"mandi", "lat", "lon", "crops"} and isinstance(mandis[0]["crops"], list)
    assert [m["mandi"] for m in client.get("/mandis", params={"crop": "tomato"}).json()] == ["Pimpalgaon"]
    villages = client.get("/villages").json()
    assert 20 <= len(villages) <= 30 and set(villages[0]) == {"village", "name_mr", "name_hi", "lat", "lon"}
    config = client.get("/config").json()
    assert config["hold_rule"] == {"min_gain_per_qtl": 50, "max_downside_per_qtl": 100}
    assert config["hold_limit_days"]["soybean"]["answers"] == {"true": 21, "false": 3}

    health = client.get("/health").json()
    assert health["status"] == "ok" and health["engine"]["advise"] == "fake"
    bad(client.get("/nope"), None, status=404)
    bad(client.put("/advise", json=EXAMPLE), None, status=405)


def test_message_and_queries():
    def send(text, sender="919812344521"):
        r = client.post("/message", json={"sender": sender, "text": text})
        assert r.status_code == 200, r.text
        return r.json()

    first = send("20 poti kanda Niphad")
    assert first == {"reply": "20 पोती कांदा (≈ 10 क्विंटल), निफाड. बरोबर? 1) हो 2) नाही",
                     "state": "awaiting_confirm",
                     "parsed": {"crop": "onion", "quantity_qtl": 10, "village": "Niphad"}}
    assert [send(t)["state"] for t in ("1", "1", "3")] == ["awaiting_freshness", "awaiting_cash", "done"]

    # the same inputs give the same message on WhatsApp and on the Advice tab
    whatsapp = [send(t, "919800000001") for t in ("10 quintal kanda Niphad", "ho", "3")][-1]["reply"]
    assert whatsapp == client.post("/advise", json={**EXAMPLE, "lot_condition": True}).json()["message"]

    bad(client.post("/message", json={"text": "hi"}), "sender")
    bad(client.post("/message", json={"sender": "91", "text": "  "}), "text")
    bad(client.post("/message", json=["x"]), None)
    bad(client.post("/message", content="{", headers={"Content-Type": "application/json"}), None)

    # voice notes: no key -> a polite reply and the open question is kept; with a transcript -> echo-back
    voice = {"audio": ("voice.ogg", b"OggS", "audio/ogg; codecs=opus")}
    send("20 poti kanda Niphad", "919800000002")
    failed = client.post("/message", data={"sender": "919800000002"}, files=voice).json()
    assert failed["reply"] == replies.VOICE_FAILED and failed["transcript"] is None
    assert failed["state"] == "awaiting_confirm"
    real_transcribe, speech.transcribe = speech.transcribe, lambda *a, **k: "वीस क्विंटल टोमॅटो नारायणगाव"
    try:
        heard = client.post("/message", data={"sender": "919800000003"}, files=voice).json()
    finally:
        speech.transcribe = real_transcribe
    assert heard["transcript"] == "वीस क्विंटल टोमॅटो नारायणगाव" and heard["state"] == "awaiting_confirm"
    assert heard["reply"] == "20 क्विंटल टोमॅटो, नारायणगाव. बरोबर? 1) हो 2) नाही"
    bad(client.post("/message", data={"sender": "91"}, files={"x": ("a.txt", b"a")}), "audio")
    bad(client.post("/message", data={"sender": "91"}, files={"audio": ("v.ogg", b"")}), "audio")
    bad(client.post("/message", files=voice), "sender")

    log = client.get("/queries").json()
    assert 0 < len(log) <= 20 and set(log[0]) == {"time", "sender", "text", "reply"}
    assert all(e["sender"].startswith("…") and len(e["sender"]) == 5 for e in log)
    assert log[0]["text"] == "🎤 वीस क्विंटल टोमॅटो नारायणगाव"            # newest first
    assert "9198" not in querylog.LOG_PATH.read_text(encoding="utf-8")


def test_cors_and_500():
    origin = {"Origin": "http://localhost:3000"}
    preflight = client.options("/advise", headers={**origin, "Access-Control-Request-Method": "POST",
                                                   "Access-Control-Request-Headers": "content-type"})
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert client.post("/advise", json=EXAMPLE, headers=origin).headers["access-control-expose-headers"] == ENGINE_HEADER
    assert "access-control-allow-origin" not in client.get("/villages", headers={"Origin": "http://evil.example"}).headers
    assert bad(client.post("/advise", json={**EXAMPLE, "crop": "x"}, headers=origin), "crop")

    real = advice.get_advice
    advice.get_advice = lambda *a, **k: 1 / 0
    try:
        crashed = client.post("/advise", json=EXAMPLE, headers=origin)
    finally:
        advice.get_advice = real
    assert bad(crashed, None, status=500)["error"] == "Internal server error"
    assert crashed.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_real_data_files(folder: Path):
    """The code paths that switch on when ML 1 and ML 2 commit their files."""
    (folder / "mandis.csv").write_text(
        "﻿mandi,lat,lon,crops\nLasalgaon,20.14,74.23,onion|soybean\nPimpalgaon,20.16,73.98,onion|tomato\n",
        encoding="utf-8")
    header = "crop,mandi,as_of_date,horizon_days,price_low,price_mid,price_high,uses_baseline,last_price_date,glut\n"
    rows = ["onion,Lasalgaon,2026-08-31,0,1700,1700,1700,False,2026-08-30,False",
            "onion,Lasalgaon,2026-08-31,7,1600.4,1750.5,1900.6,False,2026-08-30,False",
            "onion,Lasalgaon,2026-08-31,1,1650,1705,1760,True,2026-08-30,False"]
    (folder / "forecast_table.csv").write_text(header + "\n".join(rows) + "\n", encoding="utf-8")
    (folder / "prices_mh.csv").write_text(
        "date,crop,mandi,modal_price,min_price,max_price,arrivals\n"
        "2026-05-01,onion,Lasalgaon,1200,1000,1300,500\n"       # older than the history window
        "2026-08-28,onion,Lasalgaon,1650,1500,1700,900\n"
        "2026-08-30,onion,Lasalgaon,1700.4,1600,1800,950\n"
        "2026-09-02,onion,Lasalgaon,9999,1,1,1\n"               # after as_of_date: must not leak
        "2026-08-30,tomato,Pimpalgaon,800,700,900,100\n", encoding="utf-8")
    (folder / "selfcheck.csv").write_text(
        "crop,mandi,horizon_days,model_mae,same_as_today_mae,ratio,rows,passed\n"
        "onion,Lasalgaon,7,90,100,0.9,42,True\nonion,Lasalgaon,1,50,48,1.04,45,False\n"
        "tomato,Pimpalgaon,7,,,,0,False\n", encoding="utf-8")
    (folder / "coverage.csv").write_text("crop,horizon_days,coverage,n\nonion,7,0.78,120\ntomato,7,,0\n",
                                         encoding="utf-8")
    real_data, data_loader.DATA = data_loader.DATA, folder
    try:
        assert data_loader.sources()["data/forecast_table.csv"] == "real"
        fc = client.get("/forecast", params={"crop": "onion", "mandi": "LASALGAON"}).json()
        assert fc == {
            "crop": "onion", "mandi": "Lasalgaon", "prices_as_of": "2026-08-31",
            "history": [{"date": "2026-08-28", "price": 1650}, {"date": "2026-08-30", "price": 1700}],
            "forecast": [
                {"horizon_days": 1, "date": "2026-09-01", "price_low": 1650, "price_mid": 1705,
                 "price_high": 1760, "uses_baseline": True},
                {"horizon_days": 7, "date": "2026-09-07", "price_low": 1600, "price_mid": 1750,
                 "price_high": 1901, "uses_baseline": False}]}, fc
        bad(client.get("/forecast", params={"crop": "tomato", "mandi": "Lasalgaon"}), "mandi")
        assert [m["crops"] for m in client.get("/mandis").json()] == [["onion", "soybean"], ["onion", "tomato"]]

        # no backtest.json yet: ML 1's tables still show, with no example rows mixed in
        bt = client.get("/backtest", params={"crop": "onion"}).json()
        assert bt["avg_gain_per_qtl"] is None and bt["coverage"] == [{"horizon_days": 7, "coverage": 0.78, "n": 120}]
        assert bt["selfcheck"] == [
            {"mandi": "Lasalgaon", "horizon_days": 7, "ratio": 0.9, "rows": 42, "passed": True},
            {"mandi": "Lasalgaon", "horizon_days": 1, "ratio": 1.04, "rows": 45, "passed": False}]
        tomato = client.get("/backtest", params={"crop": "tomato"}).json()
        assert tomato["coverage"] == [{"horizon_days": 7, "coverage": None, "n": 0}], "unmeasured is null, never 0"
        assert tomato["selfcheck"][0]["ratio"] is None

        (folder / "backtest.json").write_text(json.dumps({"onion": {
            "crop": "onion", "assumptions": "default", "cases_tested": 88, "avg_gain_per_qtl": 61,
            "hold_cases": 30, "hold_success_rate": 0.63}}), encoding="utf-8")
        bt = client.get("/backtest", params={"crop": "onion"}).json()
        assert (bt["cases_tested"], bt["avg_gain_per_qtl"], bt["hold_success_rate"]) == (88, 61, 0.63)
        assert bt["median_gain_per_qtl"] is None and len(bt["selfcheck"]) == 2 and len(bt["ladder"]) == 4
        soy = client.get("/backtest", params={"crop": "soybean"}).json()      # not run for this crop
        assert soy["crop"] == "soybean" and soy["cases_tested"] == 0 and soy["hold_success_rate"] is None
        # the measured hold success rate reaches the advice card and the WhatsApp reply
        hold = client.post("/advise", json=EXAMPLE).json()
        assert hold["hold_success_rate"] == 0.63 and "63% वेळा फायद्याचा ठरला" in hold["message"]
    finally:
        data_loader.DATA = real_data


def test_real_engine():
    """A stub ml.engine.api stands in for ML 2's module to check how the real one gets called."""
    calls = []

    def advise(crop, quantity_qtl, village, lot_condition=None, cash_needed_in_days=None,
               blocked_mandis=None, overrides=None):
        calls.append({"crop": crop, "quantity_qtl": quantity_qtl, "village": village,
                      "lot_condition": lot_condition, "cash_needed_in_days": cash_needed_in_days,
                      "blocked_mandis": blocked_mandis, "overrides": overrides})
        if village == "Vani":
            raise ValueError("No mandi trades onion near Vani")
        return {**data_loader.fake("advise.json"), "mandi": "Junnar(Narayangaon)", "notes": []}

    def fpo_plan(lots, blocked_mandis=None, mandi_cap_qtl_per_day=None, collection_centre=None, overrides=None):
        calls.append({"lots": lots, "collection_centre": collection_centre})
        return {**data_loader.fake("fpo_plan.json"), "collection_centre": collection_centre["name"]}

    stub = types.ModuleType("ml.engine.api")
    stub.advise, stub.fpo_plan = advise, fpo_plan
    sys.modules.update({"ml": types.ModuleType("ml"), "ml.engine": types.ModuleType("ml.engine"),
                        "ml.engine.api": stub})
    engine_api._tried, engine_api._module, engine_api._import_error = False, None, None
    os.environ["ENGINE_MODE"] = "real"
    try:
        r = client.post("/advise", json={**EXAMPLE, "village": "निफाड", "lot_condition": True,
                                         "cash_needed_in_days": 7, "blocked_mandis": ["lasalgaon"],
                                         "overrides": {"fees_per_qtl": 5}})
        assert r.status_code == 200 and r.headers[ENGINE_HEADER] == "real"
        assert calls[-1] == {"crop": "onion", "quantity_qtl": 10, "village": "Niphad", "lot_condition": True,
                             "cash_needed_in_days": 7, "blocked_mandis": ["Lasalgaon"],
                             "overrides": {"fees_per_qtl": 5}}
        body = r.json()
        assert body["message"].splitlines()[0] == "🟢 *14 दिवस थांबा → जुन्नर (नारायणगाव)*"
        assert replies.EXAMPLE_DATA not in body["message"] and body["notes"] == []
        assert bad(client.post("/advise", json={**EXAMPLE, "village": "Vani"}), None)["error"] == "No mandi trades onion near Vani"

        plan = client.post("/fpo/plan", json={"lots": [{"member": "A", "crop": "onion", "quantity_qtl": 40,
                                                        "village": "niphad"}], "collection_centre": "Niphad"})
        assert plan.status_code == 200 and plan.json()["collection_centre"] == "Niphad"
        assert calls[-1]["collection_centre"] == {"name": "Niphad", "lat": 20.0797, "lon": 74.1071}
        assert calls[-1]["lots"] == [{"member": "A", "crop": "onion", "quantity_qtl": 40, "village": "Niphad",
                                      "lot_condition": None, "cash_needed_in_days": None}]

        del stub.fpo_plan                              # ENGINE_MODE=real never falls back to example data
        assert "fpo_plan" in bad(client.post("/fpo/plan", json={"lots": [{"member": "A", "crop": "onion",
                                 "quantity_qtl": 40, "village": "Niphad"}]}), None, status=503)["error"]
        os.environ["ENGINE_MODE"] = "auto"             # auto: the missing function alone is faked
        assert client.get("/health").json()["engine"] == {"mode": "auto", "advise": "real", "fpo_plan": "fake",
                                                          "import_error": None}
    finally:
        for name in ("ml", "ml.engine", "ml.engine.api"):
            sys.modules.pop(name, None)
        engine_api._tried, engine_api._module, engine_api._import_error = False, None, None
        os.environ["ENGINE_MODE"] = "fake"


def main():
    for module in (data_loader, tips, replies, parser, state, querylog, engine_api, advice, lookups,
                   conversation, speech, cloud_api):
        module._selftest()
        os.environ["ENGINE_MODE"] = "fake"

    real_log, real_recent = querylog.LOG_PATH, querylog._recent
    # example_data: the checks below assert on the contract's example numbers, so they must not
    # depend on whatever config.yaml and data files the other roles have committed
    with tempfile.TemporaryDirectory() as folder, data_loader.example_data():
        querylog.LOG_PATH, querylog._recent = Path(folder) / "queries.log", None
        try:
            for test in (test_advise, test_fpo_plan, test_lookups, test_message_and_queries, test_cors_and_500):
                test()
                print(f"api {test.__name__[5:]} ok")
            data = Path(folder) / "data"
            data.mkdir()
            (data / "villages.csv").write_bytes((data_loader.DATA / "villages.csv").read_bytes())
            test_real_data_files(data)
            print("api real_data_files ok")
            test_real_engine()
            print("api real_engine ok")
        finally:
            querylog.LOG_PATH, querylog._recent = real_log, real_recent
            state._sessions.clear()
    print("\nALL SELF-TESTS PASSED")


if __name__ == "__main__":
    main()
