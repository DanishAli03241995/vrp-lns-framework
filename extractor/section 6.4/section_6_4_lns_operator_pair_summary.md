# Section 6.4 LNS Operator-Pair Extraction Summary

## Sources Checked

- `results/lns_supplier_customer_only_baseline_sweep_v1`
- `results/lns_supplier_customer_only_baseline_kmeans_v1`
- `results/lns_supplier_customer_only_no_cluster_v1`
- `results/lns_hybrid_supplier_customer_sweep_v1`
- `results/lns_hybrid_supplier_customer_kmeans_v1`
- `results/lns_hybrid_supplier_customer_no_cluster_v1`
- `results/lns_operator_random_regret/case2_sweep`
- `results/lns_operator_random_regret/case2_kmeans`
- `results/lns_operator_random_regret/case2_no_cluster`
- `results/lns_operator_random_regret/case3_sweep`
- `results/lns_operator_random_regret/case3_kmeans`
- `results/lns_operator_random_regret/case3_no_cluster`
- `results/lns_operator_worst_greedy/case2_sweep`
- `results/lns_operator_worst_greedy/case2_kmeans`
- `results/lns_operator_worst_greedy/case2_no_cluster`
- `results/lns_operator_worst_greedy/case3_sweep`
- `results/lns_operator_worst_greedy/case3_kmeans`
- `results/lns_operator_worst_greedy/case3_no_cluster`
- `results/lns_operator_worst_regret/case2_sweep`
- `results/lns_operator_worst_regret/case2_kmeans`
- `results/lns_operator_worst_regret/case2_no_cluster`
- `results/lns_operator_worst_regret/case3_sweep`
- `results/lns_operator_worst_regret/case3_kmeans`
- `results/lns_operator_worst_regret/case3_no_cluster`
- `results/lns_operator_related_greedy/case2_sweep`
- `results/lns_operator_related_greedy/case2_kmeans`
- `results/lns_operator_related_greedy/case2_no_cluster`
- `results/lns_operator_related_greedy/case3_sweep`
- `results/lns_operator_related_greedy/case3_kmeans`
- `results/lns_operator_related_greedy/case3_no_cluster`
- `results/lns_operator_related_regret/case2_sweep`
- `results/lns_operator_related_regret/case2_kmeans`
- `results/lns_operator_related_regret/case2_no_cluster`
- `results/lns_operator_related_regret/case3_sweep`
- `results/lns_operator_related_regret/case3_kmeans`
- `results/lns_operator_related_regret/case3_no_cluster`

## Row Counts

- Rows written: 594
- Rows with warnings: 0

## Rows by Operator Pair

- `random_greedy`: 99
- `random_regret`: 99
- `related_greedy`: 99
- `related_regret`: 99
- `worst_greedy`: 99
- `worst_regret`: 99

## Rows by Routing Case

- `case_2_supplier_customer_direct`: 216
- `case_3_hybrid`: 378

## Rows by Structure Variant

- `kmeans`: 198
- `no_clustering`: 198
- `sweep`: 198

## 80-Customer Comparison Completeness

- Expected comparison buckets: 18
- Buckets detected: 18
- Missing bucket/operator entries: 0
- All expected 80-customer operator-pair bucket entries are present.

## Operator-Pair 80-Customer Summary

| Operator pair | Wins | Average rank | Average improvement (%) | Comparable bucket rows |
|---|---:|---:|---:|---:|
| `random_greedy` | 1 | 2.8889 | 4.7627 | 18 |
| `random_regret` | 8 | 2.3333 | 5.1039 | 18 |
| `related_greedy` | 2 | 3.0 | 4.7845 | 18 |
| `related_regret` | 8 | 2.2778 | 5.0468 | 18 |
| `worst_greedy` | 0 | 5.1111 | 2.5769 | 18 |
| `worst_regret` | 0 | 5.3889 | 2.3382 | 18 |

## Larger Hybrid Availability

- Larger Hybrid rows detected: 162
- `random_greedy`: 27
- `random_regret`: 27
- `related_greedy`: 27
- `related_regret`: 27
- `worst_greedy`: 27
- `worst_regret`: 27

## Feasibility and Distance Checks

- Capacity-feasible rows recorded as true: 0 of 0 recorded.
- Customer-coverage-feasible rows recorded as true: 0 of 0 recorded.
- Supplier-feasible rows recorded as true: 0 of 0 recorded.
- Structurally valid rows recorded as true: 0 of 0 recorded.
- Hybrid rows with valid system-distance check: 378 of 378

## Retained Pairs for Later Timing-Aware LNS

- `random_regret`
- `related_regret`

## Timing Exclusion Confirmation

- Timing-aware LNS result folders were not read by this extractor.
- Fixed timing, dispatch-wave timing, split-repair timing, speed40 timing, and 14:00-wave timing folders are excluded.

## Warnings

- No warnings recorded.

## Notes

- The extractor selects the latest `run_*` folder in each instance directory.
- `lns_sa_metrics_best.json` is preferred over `lns_sa_metrics.json`.
- For Case 2, ranking uses direct `lns_distance`.
- For Case 3 Hybrid, ranking uses `lns_total_system_distance`.
- All detected instance sizes are written to the CSV; the main matched thesis comparison should focus on the 80-customer rows.
