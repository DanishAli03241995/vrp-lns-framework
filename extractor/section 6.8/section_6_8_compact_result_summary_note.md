# Section 6.8 Compact Result Summary Note

Source files:

- `section_6_8_time_aware_lns_table.csv`
- `section_6_8_operator_pair_comparison.csv`
- `section_6_8_scenario_operator_summary.csv`
- `section_6_8_baseline_vs_lns_comparison.csv`

## Extraction Coverage

| Item | Value |
|---|---:|
| Total LNS rows | 126 |
| Timing scenarios | 3 |
| Operator pairs per scenario | 2 |
| Instance-capacity combinations per scenario/operator | 21 |
| Scenario parameter checks | 126 ok |
| Hybrid system distance checks | 126 ok |
| Warning rows | 0 |

Section 6.8 covers only Case 3 Hybrid + KMeans timing-aware LNS:

- fixed timing + split repair;
- dispatch-wave split repair with speed40;
- dispatch-wave split repair with speed30 plus added 14:00 wave.

## Key Averages by Scenario and Operator

| Timing scenario | Operator pair | Rows | Timing-feasible rows | Avg baseline system distance | Avg LNS system distance | Avg system improvement % | Avg customer-delivery improvement % | Avg n_remove | Avg routes |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| fixed_split | random_regret | 21 | 21 | 1768.94 | 1711.93 | 4.42 | 5.62 | 12.24 | 17.95 |
| fixed_split | related_regret | 21 | 21 | 1768.94 | 1709.62 | 4.63 | 5.89 | 11.05 | 17.81 |
| wave_speed40_split | random_regret | 21 | 21 | 2160.43 | 2041.03 | 5.34 | 6.41 | 6.86 | 21.05 |
| wave_speed40_split | related_regret | 21 | 21 | 2160.43 | 2048.11 | 5.06 | 6.07 | 5.86 | 20.90 |
| wave_speed30_14wave_split | random_regret | 21 | 21 | 2257.06 | 2119.27 | 5.46 | 6.55 | 7.19 | 22.14 |
| wave_speed30_14wave_split | related_regret | 21 | 21 | 2257.06 | 2130.43 | 5.13 | 6.15 | 5.33 | 22.10 |

## Operator Wins

Winner is based on lower `total_lns_system_distance` for the same timing scenario, customer count, and vehicle capacity.

| Scope | Random-regret wins | Related-regret wins | Ties |
|---|---:|---:|---:|
| All timing-aware LNS rows | 29 | 16 | 18 |
| Fixed split | 5 | 9 | 7 |
| Wave speed40 split | 11 | 5 | 5 |
| Wave speed30 + 14:00 split | 13 | 2 | 6 |

Short reading:

- Related-regret is slightly stronger on the fixed-timing split-repair scenario.
- Random-regret is stronger on both dispatch-wave scenarios.
- The difference is not one-sided across all scenarios, so the thesis should compare by timing scenario rather than claiming one universal operator winner.

## Feasibility Preservation

| Metric | Result |
|---|---:|
| Total rows timing-feasible after LNS | 126 / 126 |
| Fixed split feasible rows | 42 / 42 |
| Wave speed40 feasible rows | 42 / 42 |
| Wave speed30 + 14:00 feasible rows | 42 / 42 |
| Rows with scenario mismatch warnings | 0 |
| Rows with system-distance mismatch warnings | 0 |

Safe interpretation:

- The timing-aware LNS preserved depot-side timing feasibility in all extracted best runs.
- This should be worded as an extracted-result observation, not as a guarantee for all possible instances or parameters.

## Rejected Infeasible Moves

| Timing scenario | Operator pair | Sum rejected infeasible moves | Avg rejected infeasible moves | Max rejected infeasible moves |
|---|---|---:|---:|---:|
| fixed_split | random_regret | 0 | 0 | 0 |
| fixed_split | related_regret | 0 | 0 | 0 |
| wave_speed40_split | random_regret | 0 | 0 | 0 |
| wave_speed40_split | related_regret | 0 | 0 | 0 |
| wave_speed30_14wave_split | random_regret | 0 | 0 | 0 |
| wave_speed30_14wave_split | related_regret | 0 | 0 | 0 |

Short reading:

- The selected best-run metrics record no rejected infeasible moves for these extracted runs.
- The thesis can still state the algorithm checks timing feasibility before SA acceptance, but the result table should report that the extracted best runs did not record infeasible candidate rejections.

## Representative 200c_cap35 Values

| Scenario | Operator pair | Baseline system distance | LNS system distance | System improvement % | Best n_remove | Rejected infeasible moves |
|---|---|---:|---:|---:|---:|---:|
| fixed_split | random_regret | 3943.27 | 3740.88 | 5.13 | 52 | 0 |
| fixed_split | related_regret | 3943.27 | 3727.35 | 5.48 | 30 | 0 |
| wave_speed40_split | random_regret | 5457.25 | 5003.96 | 8.31 | 13 | 0 |
| wave_speed40_split | related_regret | 5457.25 | 4997.66 | 8.42 | 7 | 0 |
| wave_speed30_14wave_split | random_regret | 6227.42 | 5604.45 | 10.00 | 18 | 0 |
| wave_speed30_14wave_split | related_regret | 6227.42 | 5643.97 | 9.37 | 8 | 0 |

This representative larger instance shows clear additional LNS improvement after timing-aware construction and split repair, while retaining timing feasibility.

## Recommended Main Thesis Tables

Use three compact tables in Section 6.8:

1. Scenario/operator average table:
   - timing scenario;
   - operator pair;
   - average baseline system distance;
   - average LNS system distance;
   - average system improvement percent;
   - timing-feasible rows;
   - average `n_remove`.

2. Operator-pair win table:
   - scenario;
   - random-regret wins;
   - related-regret wins;
   - ties.

3. Representative large-instance table:
   - use `200c_cap35`;
   - show baseline system distance, LNS system distance, improvement percent, `n_remove`, rejected infeasible moves.

Detailed per-instance values can remain in CSV/extractor outputs or appendix-style supporting material.

## Safe Thesis Wording Bullets

- Time-aware LNS was evaluated only for Case 3 Hybrid + KMeans timing scenarios.
- The main comparison metric is `total_lns_system_distance`, because it includes customer-delivery distance plus supplier-to-depot replenishment distance.
- Across all extracted best runs, timing feasibility was preserved after LNS.
- The fixed-timing scenario slightly favoured related-regret on average, while the two dispatch-wave scenarios favoured random-regret on average.
- These findings should be treated as empirical results for the tested synthetic instances and parameter settings, not as universal operator rankings.
