# Synthetic backtest fixtures

These are made-up prices and forecasts for testing, not measured model evidence.
Every CSV uses the handoff schema in `ML2_ENGINE.md`. Prices span 40 calendar days
from 2026-06-28 through 2026-08-06; forecasts are dated every third day, including
dates outside the test block to check split filtering. Both villages are nearest
to Lasalgaon. All costs and thresholds come from the repository's `config.yaml`.

Onion cases in the test block:

| Forecast date | Expected evaluation |
| --- | --- |
| 2026-07-01 | Hold 14 days; real sale loses against the nearest-today baseline |
| 2026-07-04 | One-day hold; target and next day missing, so exclude both villages |
| 2026-07-07 | Hold 14 days; target missing, next report wins over previous; beats best today |
| 2026-07-10 | Self-check fallback; sell today |
| 2026-07-13 | Hold 14 days; target and next missing, use previous; beats baseline but loses to best today |
| 2026-07-16 | Baseline's last report is four days old; exclude both villages |
| 2026-07-19 | Another tradable mandi has no recent report, preventing a real best-today comparison; exclude both villages |

Tomato has sell-today cases and no holds. Soybean has no forecast cases, testing
null metrics. The self-test writes `backtest.json` here and checks that results
for other crops are preserved. Temporary test variants stay under `ml/engine`.

Run from the repository root:

```sh
ml/engine/.venv/bin/python -B -m ml.engine.test_backtest
```
