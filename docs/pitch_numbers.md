# SellSmart: pitch numbers

Every number below is read from a file; the source file and key are given beside it. Percentages are
computed from two file values, and the two keys are named. Nothing here is estimated.

## 1. Scope and date ranges

- Crops: onion, tomato, soybean (`data/backtest.json` → `top-level keys`)
- Mandis: 14 (`data/mandis.csv` → `rows`): Akola, Amarawati, Junnar (Narayangaon), Lasalgaon, Lasalgaon (Niphad), Lasalgaon (Vinchur), Latur, Nagpur, Nasik, Pimpalgaon, Pune, Pune (Pimpri), Solapur, Washim
- Villages: 26 (`data/villages.csv` → `rows`)
- Model blocks (`data/splits.json` → `*`): train to 2025-03-24; validation 2025-04-15 to 2025-07-10; test 2025-08-01 to 2025-11-04; demo date (`as_of_date`) 2025-09-21
- Backtest test period 2025-08-01 to 2025-11-04 (`data/backtest.json` → `<crop>.test_period`); forecast dates 2025-08-01 to 2025-11-02, 32 dates (`data/backtest.json` → `<crop>.forecast_period, .forecast_dates`); villages tested per crop 26 (`data/backtest.json` → `<crop>.villages_tested`); assumptions: default (`data/backtest.json` → `<crop>.assumptions`)

## 2. Backtest size and exclusions

| crop | cases attempted | cases scored | excluded | excluded, by reason (share of attempted) |
|---|---|---|---|---|
| onion | 832 | 707 (85.0%) | 125 (15.0%) | no recent price at baseline mandi: 53 (6.4%); no recent price at chosen mandi: 72 (8.7%) |
| tomato | 832 | 739 (88.8%) | 93 (11.2%) | no recent price at baseline mandi: 30 (3.6%); no recent price at chosen mandi: 63 (7.6%) |
| soybean | 832 | 649 (78.0%) | 183 (22.0%) | missing real price: 13 (1.6%); no recent price at baseline mandi: 20 (2.4%); no recent price at chosen mandi: 150 (18.0%) |

Sources: `data/backtest.json` → `<crop>.cases_attempted`, `data/backtest.json` → `<crop>.cases_tested`, `data/backtest.json` → `<crop>.cases_excluded_by_reason`. Excluded = sum of the reasons; it equals attempted minus scored for every crop.

## 3. Four-policy ladder (average net ₹ per quintal) and the gain split

| crop | nearest mandi today | highest price today | best net today | with hold rule (before the gate) | gain from mandi choice | gain from holding |
|---|---|---|---|---|---|---|
| onion | 1000 | 1015 | 1069 | 1058 | 69 (6.9% of nearest) | -11 (-1.1% of nearest) |
| tomato | 1574 | 1763 | 1798 | 1798 | 224 (14.2% of nearest) | 0 (0.0% of nearest) |
| soybean | 3789 | 3750 | 3825 | 3826 | 36 (1.0% of nearest) | 1 (0.0% of nearest) |

Sources: `data/backtest.json` → `<crop>.ladder[policy].avg_net` for nearest_today, highest_price_today, best_net_today, full_advice; `data/backtest.json` → `<crop>.gain_split.from_mandi_choice / .from_holding`. Percentages: gain ÷ `ladder[nearest_today].avg_net`. The last ladder column is the backtest's `full_advice` policy, measured without the hold gate (the gate was added afterwards).

## 4. Gain per quintal against the nearest mandi

| crop | average gain ₹/qtl | median gain ₹/qtl | share of cases with a loss | worst loss ₹/qtl |
|---|---|---|---|---|
| onion | 58 | 15 | 9.6% | -200 |
| tomato | 224 | 52 | 0.0% | 0 |
| soybean | 37 | 0 | 0.2% | -3 |

Sources: `data/backtest.json` → `<crop>.avg_gain_per_qtl / .median_gain_per_qtl / .loss_share / .worst_loss_per_qtl` (loss share shown as a percentage of the file's fraction).

## 5. Hold record and the hold gate

| crop | holds advised | won | lost | unscored | success rate (won ÷ scored) | gate |
|---|---|---|---|---|---|---|
| onion | 124 | 40 | 84 | 0 | 32.3% | suppresses holds: success 0.323 < 0.5 |
| tomato | 0 | 0 | 0 | 0 | not enough data | suppresses holds: 0 scored < 20 |
| soybean | 21 | 7 | 1 | 13 | 87.5% | suppresses holds: 8 scored < 20 |

Sources: `data/backtest.json` → `<crop>.decision_counts.hold / .hold_record / .hold_success_rate`; gate thresholds `config.yaml` → `hold_gate` = min_scored_holds 20, min_success_rate 0.5.

Gate rule (`ml/engine/api.py` → `_suppressed_hold_record`): a hold is replaced by selling today when the crop has fewer than 20 scored holds, or a success rate below 0.5, or a holding gain of zero or less. With the current record it suppresses holds for all three crops: onion for its success rate, tomato and soybean for too few scored holds.

## 6. Forecast honesty

Model against "same as today" on the test block (ratio below 1 = the model beats "price stays the same"):

| crop | v1 ratio | v1 coverage | v1 model rows | v2 ratio | v2 coverage | v2 model rows |
|---|---|---|---|---|---|---|
| onion | 1.251 | 0.666 | 567 | 1.207 | 0.715 | 477 |
| tomato | 0.907 | 0.773 | 55 | 1.027 | 0.781 | 228 |
| soybean | 0.978 | 0.736 | 139 | 1.037 | 0.756 | 130 |

Source: `ml/forecast/summary.json` → `crops.<crop>.v1|v2.ratio / .coverage / .model_rows`. Note from that file: "Version 2's rules (monthly refit, trailing self-check, trailing widening) were chosen after seeing version 1's test-block result, so version 2's test numbers are not an untouched holdout."

Coverage per horizon on the test block (share of real prices inside the forecast range):

| crop | 1 d | 2 d | 3 d | 7 d | 14 d | 21 d |
|---|---|---|---|---|---|---|
| onion | 0.819 (n 166) | 0.811 (n 180) | 0.729 (n 188) | 0.682 (n 179) | 0.639 (n 155) | 0.582 (n 146) |
| tomato | 0.745 (n 137) | 0.79 (n 143) | 0.734 (n 139) | 0.813 (n 134) | 0.813 (n 123) | 0.798 (n 109) |
| soybean | 0.687 (n 99) | 0.767 (n 120) | 0.732 (n 123) | 0.796 (n 113) | 0.792 (n 101) | 0.758 (n 95) |

Source: `data/coverage.csv` → `crop, horizon_days, coverage, n`.

Trailing self-check on the demo date 2025-09-21 (`data/splits.json` → `as_of_date`): (mandi, horizon) pairs where the model may be used:

- onion: 20 of 42 pass
- tomato: 16 of 30 pass
- soybean: 2 of 30 pass

Source: `data/selfcheck.csv` → `passed (rows per crop)`.

## 7. Demo cases (2025-09-21, 20 quintal each)

| case | action | mandi | net ₹/qtl | nearest mandi (net) | gain vs nearest | hold suppressed |
|---|---|---|---|---|---|---|
| onion, Niphad | sell_now | Pimpalgaon | 1089 | Lasalgaon (Niphad) (1054) | 35 | True |
| onion, Niphad, gate off | hold 7 d | Pimpalgaon | 1219 | Lasalgaon (Niphad) (1054) | 164 | False |
| tomato, Manchar | sell_now | Pimpalgaon | 1597 | Junnar (Narayangaon) (1445) | 152 | False |

Source: `ml/engine/real_run/demo_2025-09-21.json` → `<case>.action / .mandi / .net_per_qtl / .baseline_today / .gain_vs_baseline / .hold_suppressed`.

Exact note text, onion Niphad (`onion_Niphad_20qtl.notes`):

> Hold suppressed: 7 days at Pimpalgaon, expected extra Rs 130 per qtl; won 40 of 124.

Tomato Manchar notes (`tomato_Manchar_20qtl.notes`): []

FPO plan, six lots, collection centre Niphad:

| scenario | placed qtl | unplaced qtl | total net ₹ | nearest-mandi total ₹ | gain ₹ |
|---|---|---|---|---|---|
| open | 400 | 0 | 538495 | 513320 | 25175 |
| Pimpalgaon_blocked | 400 | 0 | 475667 | 364210 | 111457 |

Blocking Pimpalgaon changes total net by -62828 ₹ (`Pimpalgaon_blocked.total_net` − `open.total_net`). Source: `ml/engine/real_run/demo_2025-09-21.json` → `fpo.<scenario>.placed_qtl / .unplaced_qtl / .total_net / .baseline_total / .gain_vs_baseline`.

## 8. Caveats

- The backtest replays simulated farmer cases (26 villages × 32 dates per crop) at the default assumptions (`assumptions: default`): transport, storage and spoilage are placeholders in `config.yaml`, not measured costs.
- Cases with no recent price at the nearest or chosen mandi, or no real price to score against, are excluded (section 2); the averages describe the scored cases only.
- The hold gate and forecast v2 were both designed after seeing test-block results, so their test numbers are not an untouched holdout.
- Part of the gap to the nearest mandi may reflect grade differences between mandis (one variety per crop and mandi, across grades), not only a better price for the same produce.
- Soybean has only 8 scored holds (`data/backtest.json` → `soybean.hold_record`: won 7, lost 1, unscored 13); its 87.5% success rate rests on that.

**Three numbers for the first slide:** ₹224/qtl average gain for tomato from choosing the mandi (`data/backtest.json` → `tomato.gain_split.from_mandi_choice`); ₹69/qtl for onion (`data/backtest.json` → `onion.gain_split.from_mandi_choice`); and onion holds won only 40 of 124, so the advice now says sell today (`data/backtest.json` → `onion.hold_record`).
