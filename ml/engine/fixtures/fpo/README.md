# Synthetic FPO fixtures

These made-up forecasts test a rule-based allocator, not real market performance.
Nashik trades tomato only, allowing all onion mandis to be blocked while tomato
planning continues. The forecast flag is `falling`; all thresholds and costs come
from the repository's `config.yaml`.

`request.json` is in the POST /fpo/plan request shape. It deliberately lists a
non-urgent lot first. At a cap of 100 quintals per mandi/day, A and B go first,
E's shorter hold limit precedes D, and C comes last. B and C split across
destinations/days; half of D remains unplaced. Totals compare only placed produce.

The test also exercises mixed-crop trucks, multiple trips, fractional quantities,
closure rerouting, an unavailable crop alongside an available crop, no placement,
collection-centre overrides, and matching Advice baselines. Whole-rupee truck
shares use proportional weights and largest-remainder rounding so they add up
exactly to the displayed group trip cost.

Run from the repository root:

```sh
ml/engine/.venv/bin/python -B -m ml.engine.test_fpo
```
