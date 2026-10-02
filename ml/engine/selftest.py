"""Run with ml/engine/.venv/bin/python -B -m ml.engine.selftest.

The section 6 fixture stays in memory; no ML 1 data files are written.
"""

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

if __package__:
    from . import api
else:
    import api


def fake_forecast():
    common = {
        "crop": "onion", "as_of_date": "2026-08-31", "uses_baseline": False,
        "last_price_date": "2026-08-31", "falling": False,
    }
    return [
        {**common, "mandi": "Lasalgaon", "horizon_days": 0,
         "price_low": 1700, "price_mid": 1700, "price_high": 1700},
        {**common, "mandi": "Pimpalgaon", "horizon_days": 0,
         "price_low": 1760, "price_mid": 1760, "price_high": 1760},
        {**common, "mandi": "Pimpalgaon", "horizon_days": 14,
         "price_low": 1800, "price_mid": 2000, "price_high": 2200},
    ]


def assert_error(call, expected):
    try:
        call()
    except ValueError as error:
        assert str(error) == expected, (str(error), expected)
    else:
        raise AssertionError(f"expected ValueError({expected!r})")


def _test_hold_gate():
    as_of = "2025-09-21"
    data_dir = api._data_dir()
    forecast = [row for row in api._read_csv(data_dir / "forecast_history.csv") if row["as_of_date"] == as_of]
    arguments = {"as_of_date": as_of, "forecast": forecast}
    ungated = api.advise("onion", 20, "Niphad", apply_hold_gate=False, **arguments)
    gated = api.advise("onion", 20, "Niphad", **arguments)
    assert (ungated["action"], ungated["days"], ungated["mandi"], ungated["gain_from_waiting"]) == ("hold", 7, "Pimpalgaon", 130)
    assert not ungated["hold_suppressed"]
    assert (gated["action"], gated["days"], gated["mandi"], gated["net_per_qtl"]) == ("sell_now", 0, "Pimpalgaon", 1089)
    assert gated["hold_suppressed"] and gated["gain_from_waiting"] == 0
    assert gated["gain_vs_baseline"] == gated["gain_from_mandi"] == 35
    assert gated["net_low"] == gated["net_high"] == gated["best_today"]["net"]
    assert gated["break_even_price"] is None and gated["why"]["storage"] == 0
    assert gated["options"] == ungated["options"]
    assert gated["notes"] == ["Hold suppressed: 7 days at Pimpalgaon, expected extra Rs 130 per qtl; won 40 of 124."]
    distances = {"Niphad": {
        row["mandi"]: api.road_distance_km("Niphad", row["mandi"], data_dir=data_dir)
        for row in api._read_csv(data_dir / "mandis.csv") if "onion" in row["crops"].split("|")
    }}
    with TemporaryDirectory(prefix="hold-gate-test-", dir=Path(__file__).resolve().parent) as temporary:
        folder = Path(temporary)
        missing = api.advise("onion", 20, "Niphad", **arguments, data_dir=folder, distances=distances)
        assert missing["action"] == "hold" and not missing["hold_suppressed"]
        assert missing["options"] == ungated["options"] and missing["notes"] == ungated["notes"]
        settings = api._config(None)["hold_gate"]
        minimum, rate = settings["min_scored_holds"], settings["min_success_rate"]
        passed = {"hold_record": {"won": minimum // 2, "lost": minimum - minimum // 2}, "hold_success_rate": rate, "gain_split": {"from_holding": 1}}
        trials = [
            (passed, False),
            ({**passed, "hold_record": {"won": minimum - 1, "lost": 0}, "hold_success_rate": 1}, True),
            ({**passed, "hold_success_rate": rate / 2}, True),
            ({**passed, "gain_split": {"from_holding": 0}}, True),
            ({**passed, "gain_split": {"from_holding": -1}}, True),
            ({"hold_record": {"won": 0, "lost": 0}, "hold_success_rate": None, "gain_split": {"from_holding": None}}, True),
        ]
        for record, suppressed in trials:
            (folder / "backtest.json").write_text(json.dumps({"onion": record}), encoding="utf-8")
            api._read_backtest.cache_clear()
            decision = api.advise("onion", 20, "Niphad", **arguments, data_dir=folder, distances=distances)
            assert decision["hold_suppressed"] is suppressed
            assert decision["action"] == ("sell_now" if suppressed else "hold")
            assert decision["options"] == ungated["options"]
    api._read_backtest.cache_clear()
    print("PASS hold gate: real onion record suppresses; ungated and missing-file calls hold; options stay unchanged")
    print("PASS hold gate boundaries: scored count, success rate, zero/negative holding gain, unmeasured record")


def main():
    forecast = fake_forecast()
    distances = {"Niphad": {"Lasalgaon": 10, "Pimpalgaon": 20}}

    def advice(**kwargs):
        arguments = {"forecast": forecast, "distances": distances, "apply_hold_gate": False, **kwargs}
        return api.advise("onion", 10, "Niphad", **arguments)

    # Keep the fixture independent of handoff files supplied later by teammates.
    with patch.object(api, "_optional_csv", return_value=None), patch.object(api, "_hold_success_rate", return_value=None):
        result = advice()
        assert (result["action"], result["days"], result["mandi"]) == ("hold", 14, "Pimpalgaon")
        expected = {
            "baseline_today": 1660, "best_today": 1700, "net_per_qtl": 1844,
            "net_low": 1652, "net_high": 2035, "gain_vs_baseline": 184,
            "gain_from_mandi": 40, "gain_from_waiting": 144, "break_even_price": 1850,
        }
        for key, value in expected.items():
            actual = result[key]["net"] if key in ("baseline_today", "best_today") else result[key]
            assert actual == value, (key, actual, value)
        assert result["baseline_today"]["mandi"] == "Lasalgaon"
        assert result["best_today"]["mandi"] == "Pimpalgaon"
        assert result["why"] == {"price": 2000, "spoilage_loss": 82, "transport": 60, "storage": 14, "fees": 0}
        assert result["confidence"] == "medium"
        assert result["hold_limit_days"] == 21
        assert result["hold_success_rate"] is None
        assert result["prices_as_of"] == "2026-08-31"
        assert result["assumptions_default"] is True
        assert result["uses_baseline"] is False
        assert result["notes"] == []
        assert result["hold_suppressed"] is False
        assert "message" not in result and "storage_tip" not in result
        assert [row["net_per_qtl"] for row in result["options"]] == [1844, 1700, 1660]
        assert [row["distance_km"] for row in result["options"]] == [20, 20, 10]
        print("PASS worked example: baseline=1660 best_today=1700 net=1844 low=1652 high=2035")
        print("PASS gains: baseline=184 mandi=40 waiting=144 break_even=1850")

        for kwargs, mandi, net in (
            ({"cash_needed_in_days": 3}, "Pimpalgaon", 1700),
            ({"blocked_mandis": ["Pimpalgaon"]}, "Lasalgaon", 1660),
            ({"lot_condition": False}, "Pimpalgaon", 1700),
        ):
            flipped = advice(**kwargs)
            assert (flipped["action"], flipped["days"], flipped["mandi"], flipped["net_per_qtl"]) == ("sell_now", 0, mandi, net)
            assert flipped["break_even_price"] is None
            assert flipped["gain_from_waiting"] == 0
            assert flipped["notes"] == []
            print(f"PASS flip {kwargs}: sell_now at {mandi}, net={net}")

        # A higher-mid, unsafe hold must not prevent a lower-mid, safe hold.
        risky = {**forecast[-1], "horizon_days": 21, "price_low": 1000,
                 "price_mid": 2400, "price_high": 2600}
        assert advice(forecast=forecast + [risky])["days"] == 14

        failed = deepcopy(forecast)
        failed[-1]["uses_baseline"] = True
        fallback = advice(forecast=failed)
        assert fallback["action"] == "sell_now" and fallback["confidence"] == "low"
        assert fallback["notes"] == ["forecast not reliable here; compared today's prices only"]
        assert len(fallback["options"]) == 2

        rejected = deepcopy(forecast)
        rejected[-1].update(price_low=1720, price_mid=1800, price_high=1820)
        sell_now = advice(forecast=rejected)
        assert sell_now["action"] == "sell_now" and sell_now["confidence"] == "high"
        assert sell_now["notes"] == []
        assert len(sell_now["options"]) == 3

        stale = deepcopy(forecast)
        stale[-1].update(last_price_date="2026-08-27", falling=True)
        flagged = advice(forecast=stale)
        assert flagged["confidence"] == "low"
        assert flagged["options"][0]["flags"] == ["stale", "falling"]
        stale[-1]["last_price_date"] = "2026-08-28"
        assert advice(forecast=stale)["confidence"] == "medium"

        assert advice(overrides={})["assumptions_default"] is True
        expensive = advice(overrides={"transport": {"loading_per_qtl": 30}})
        assert expensive["best_today"]["net"] == 1690
        assert expensive["net_per_qtl"] == 1834
        assert expensive["assumptions_default"] is False
        assert advice(overrides={"transport": {"road_factor": 99}})["net_per_qtl"] == 1844
        assert advice()["net_per_qtl"] == 1844  # Overrides did not mutate defaults.

        strings = [{key: str(value).lower() if isinstance(value, bool) else str(value)
                    for key, value in row.items()} for row in forecast]
        assert advice(forecast=strings)["net_per_qtl"] == 1844
        assert_error(lambda: api.advise("wheat", 10, "Niphad", forecast=forecast, distances=distances), "unknown crop: wheat")
        assert_error(lambda: advice(distances=None), "no distance data for Niphad")
        assert_error(lambda: api.advise("onion", 10, "Unknown", forecast=forecast, distances=distances), "no distance data for Unknown to Lasalgaon")
        print("PASS hold ordering, self-check fallback, confidence/flags, overrides, CSV values and errors")

    coordinate_tables = {
        "villages.csv": [{"village": "Niphad", "name_mr": "", "name_hi": "", "lat": "20", "lon": "74"}],
        "mandis.csv": [
            {"mandi": "Lasalgaon", "lat": "20", "lon": "74", "crops": "tomato|soybean"},
            {"mandi": "Pimpalgaon", "lat": "20.1", "lon": "74.1", "crops": "onion|tomato"},
        ],
    }
    with patch.object(api, "_optional_csv", side_effect=lambda name, data_dir=None: coordinate_tables.get(name)), patch.object(api, "_hold_success_rate", return_value=None):
        filtered = advice()
        assert filtered["baseline_today"] == {"mandi": "Pimpalgaon", "net": 1700}
        assert all(option["mandi"] == "Pimpalgaon" for option in filtered["options"])
        config = api._config(None)
        straight = api.haversine((20, 74), (20.1, 74.1), unit=api.Unit.KILOMETERS)
        road = api.road_distance_km("Niphad", "Pimpalgaon")
        assert road == straight * config["transport"]["road_factor"]
        computed = advice(distances=None)
        assert all(option["distance_km"] == road for option in computed["options"])
        assert_error(lambda: api.road_distance_km("Unknown", "Pimpalgaon"), "unknown village: Unknown")
        print("PASS mandis.csv crop eligibility and haversine road-factor lookup")

    spec = (Path(__file__).resolve().parent / "fixtures" / "ML2_ENGINE.md").read_text(encoding="utf-8")
    section_ten = spec.split("## 10. `config.yaml`", 1)[1]
    exact_yaml = section_ten.split("```yaml\n", 1)[1].split("```", 1)[0]
    expected_config = api.yaml.safe_load(exact_yaml)
    forecast_keys = ("target_match_window_days", "selfcheck_ratio_max", "selfcheck_min_rows", "coverage_widen_below")
    expected_config["forecast"] = {key: expected_config["forecast"][key] for key in forecast_keys}
    expected_config["forecast"].update(min_reported_days=500, falling_ratio=0.90)
    expected_config["hold_gate"] = {"min_scored_holds": 20, "min_success_rate": 0.5}
    actual_config = api.yaml.safe_load((api._ROOT / "config.yaml").read_text(encoding="utf-8"))
    assert actual_config == expected_config
    print("PASS config.yaml matches section 10 with agreed spec updates")
    _test_hold_gate()
    print("All self-tests passed.")


if __name__ == "__main__":
    main()
