Hold gate demo: 2025-09-21, 20 qtl for each Advice case. All three self-tests pass. data/backtest.json was not rerun or edited; before and after SHA256: b3ca944625796f897730cc8dca14ab3d28af514e4e86893ed30be92e2d9cd10f. Existing configuration values are unchanged; added hold_gate min_scored_holds=20 and min_success_rate=0.5.

Initial push failed: auth. Continued locally as instructed; the final push outcome is reported in the chat.

| case | action | days | mandi | net Rs/qtl | gain baseline | gain waiting | hold suppressed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| onion, Niphad | sell_now | 0 | Pimpalgaon | 1089 | 35 | 0 | True |
| onion, Niphad, gate disabled | hold | 7 | Pimpalgaon | 1219 | 164 | 130 | False |
| tomato, Manchar | sell_now | 0 | Pimpalgaon | 1597 | 152 | 0 | False |

Exact onion note: Hold suppressed: 7 days at Pimpalgaon, expected extra Rs 130 per qtl; won 40 of 124.

Tomato notes: []. Tomato is otherwise byte-for-byte equivalent as a parsed response to the previous saved Advice output; the new hold_suppressed field is false.

Collection centre: Niphad. Six Nashik-district sample lots; every village name exists in data/villages.csv:

| member | crop | qtl | village | condition | cash deadline |
| --- | --- | --- | --- | --- | --- |
| A | onion | 100 | Niphad | default | none |
| B | onion | 80 | Sinnar | default | 3 |
| C | onion | 70 | Chandori | False | none |
| D | tomato | 60 | Dindori | 1 | none |
| E | tomato | 50 | Yeola | 0 | 1 |
| F | tomato | 40 | Lasalgaon | 2 | none |

| FPO scenario | placed qtl | unplaced qtl | total net Rs | baseline Rs | gain Rs |
| --- | --- | --- | --- | --- | --- |
| open | 400 | 0 | 538495 | 513320 | 25175 |
| Pimpalgaon_blocked | 400 | 0 | 475667 | 364210 | 111457 |

Assignments: open

| member | crop | qtl | mandi | day | net total Rs | reason |
| --- | --- | --- | --- | --- | --- | --- |
| E | tomato | 50 | Pimpalgaon | 0 | 95942 | needs cash in 1 day; holds suppressed: won 0 of 0 |
| B | onion | 80 | Pimpalgaon | 0 | 89106 | needs cash in 3 days; holds suppressed: won 40 of 124 |
| F | tomato | 40 | Pimpalgaon | 0 | 76753 | short hold limit; holds suppressed: won 0 of 0 |
| D | tomato | 30 | Pimpalgaon | 0 | 57565 | short hold limit; holds suppressed: won 0 of 0 |
| D | tomato | 30 | Junnar (Narayangaon) | 0 | 38851 | moved: mandi cap reached; holds suppressed: won 0 of 0 |
| C | onion | 70 | Lasalgaon | 0 | 74232 | moved: mandi cap reached; holds suppressed: won 40 of 124 |
| A | onion | 100 | Lasalgaon | 0 | 106046 | moved: mandi cap reached; holds suppressed: won 40 of 124 |

Assignments: Pimpalgaon_blocked

| member | crop | qtl | mandi | day | net total Rs | reason |
| --- | --- | --- | --- | --- | --- | --- |
| E | tomato | 50 | Junnar (Narayangaon) | 0 | 70450 | moved: mandi unavailable; holds suppressed: won 0 of 0 |
| B | onion | 80 | Lasalgaon | 0 | 85131 | moved: mandi unavailable; holds suppressed: won 40 of 124 |
| F | tomato | 40 | Junnar (Narayangaon) | 0 | 56360 | moved: mandi unavailable; holds suppressed: won 0 of 0 |
| D | tomato | 60 | Junnar (Narayangaon) | 0 | 84541 | moved: mandi unavailable; holds suppressed: won 0 of 0 |
| C | onion | 70 | Lasalgaon | 0 | 74490 | short hold limit; holds suppressed: won 40 of 124 |
| A | onion | 50 | Lasalgaon | 0 | 53207 | best net; holds suppressed: won 40 of 124 |
| A | onion | 50 | Lasalgaon (Niphad) | 0 | 51488 | moved: mandi cap reached; holds suppressed: won 40 of 124 |

No demo mismatch. No gated lot is held; every group respects the cap; quantities, per-lot baselines, truck shares and totals reconcile. Full unabridged outputs, including options and trucks, are saved in demo_2025-09-21.json. The existing backtest continues to measure the ungated rule via apply_hold_gate=False.
