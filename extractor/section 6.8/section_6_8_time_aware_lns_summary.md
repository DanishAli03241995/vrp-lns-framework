# Section 6.8 Time-Aware LNS Extraction Summary

## Scope

This extraction covers only Case 3 Hybrid + KMeans timing-aware LNS rows:

- fixed timing + split repair with random-regret and related-regret;
- dispatch-wave split repair with speed40 and random-regret / related-regret;
- dispatch-wave split repair with speed30 plus a 14:00 wave and random-regret / related-regret.

Non-timing LNS, Case 1, Case 2, Sweep, no-clustering, and route-first timing folders are excluded from the main table.

## Output Files

- `section_6_8_time_aware_lns_table.csv`
- `section_6_8_operator_pair_comparison.csv`
- `section_6_8_scenario_operator_summary.csv`
- `section_6_8_baseline_vs_lns_comparison.csv`

## Completeness

- Expected rows: 126
- Extracted rows: 126
- Missing expected rows: 0
- Operator-comparison rows: 63
- Scenario/operator summary rows: 6
- Rows with warnings: 0

## Scenario Parameter Checks

| Check status | Row count |
|---|---:|
| ok | 126 |

## Scenario/Operator Row Counts

| Timing scenario | Operator pair | Rows | Timing-feasible rows | Avg system improvement percent |
|---|---|---:|---:|---:|
| fixed_split | random_regret | 21 | 21 | 4.419307872452938 |
| fixed_split | related_regret | 21 | 21 | 4.6322141623583 |
| wave_speed30_14wave_split | random_regret | 21 | 21 | 5.464744469362073 |
| wave_speed30_14wave_split | related_regret | 21 | 21 | 5.134670250836323 |
| wave_speed40_split | random_regret | 21 | 21 | 5.339339945765055 |
| wave_speed40_split | related_regret | 21 | 21 | 5.058560217525876 |

## Extraction Notes

- The extractor prefers `lns_sa_metrics_best.json` and `lns_sa_summary_best.json`.
- The selected run must match the intended timing scenario, speed/wave setting, and operator pair where these fields are recorded.
- If a newer timestamp does not match the expected scenario, the latest matching run is selected and the ignored newer timestamp is recorded.
- `total_lns_system_distance` is the main Hybrid timing-aware LNS distance because it includes customer-delivery distance and supplier-to-depot replenishment distance.
- Timing-infeasible candidate acceptance is checked only from saved feasibility evidence where available; missing iteration-level feasibility records are reported conservatively.
