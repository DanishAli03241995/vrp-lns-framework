# Section 6.4 Operator-Pair 80-Customer Matched Summary

## Final Dataset

| Operator Pair | Best-Ranked Environments Case 2 | Best-Ranked Environments Case 3 | Average Rank Case 2 | Average Rank Case 3 | Average Improvement (%) Case 2 | Average Improvement (%) Case 3 |
|---|---:|---:|---:|---:|---:|---:|
| Related + Regret-2 | 3 | 5 | 2.3333 | 2.2222 | 5.0586 | 5.0349 |
| Random + Regret-2 | 5 | 3 | 1.6667 | 3.0000 | 5.5460 | 4.6618 |
| Random + Greedy | 0 | 1 | 3.1111 | 2.6667 | 4.7403 | 4.7851 |
| Related + Greedy | 1 | 1 | 3.3333 | 2.6667 | 4.7033 | 4.8657 |
| Worst + Greedy | 0 | 0 | 5.1111 | 5.1111 | 2.4071 | 2.7467 |
| Worst + Regret-2 | 0 | 0 | 5.4444 | 5.3333 | 2.2486 | 2.4278 |

## Matched Comparison Set

- Total comparison environments: 18
- Cases included: Case 2 supplier-customer direct and Case 3 Hybrid.
- Customer size: 80 customers.
- Vehicle capacities: 15, 25, 35.
- Clustering configurations: No Clustering, Sweep, KMeans.
- Expected matched environments: 2 cases x 3 clustering configurations x 3 capacities = 18.
- Matched environments per case: 3 clustering configurations x 3 capacities = 9.
- Operator pairs per environment: 6.
- Rows used: 108.

## Methodological Note

- Each comparison environment is defined by `routing_case`, `structure_variant`, and `vehicle_capacity`, with `customer_count = 80`.
- For each environment, the six operator pairs are ranked by `ranking_distance_used` in ascending order.
- For Case 2, `ranking_distance_used` is the direct LNS distance.
- For Case 3 Hybrid, `ranking_distance_used` is the LNS total system distance, including supplier-depot replenishment distance.
- `Best-Ranked Environments` counts how many environments within each routing case an operator pair achieved the lowest ranking distance. If two operator pairs have exactly the same best distance, both are counted as best-ranked for that environment.
- `Average Rank` is the arithmetic mean of the rank assigned to that operator pair across the 9 environments within the relevant routing case.
- `Average Improvement (%)` is the arithmetic mean of `percent_improvement` across the same 9 case-specific environments. Each improvement percentage is relative to that environment's own pre-LNS baseline.
- Case 2 and Case 3 are reported separately because they are different fulfilment structures and should not be hidden inside a single cross-case average.
- The 20-, 40-, and 60-customer rows are not included in this main matched table; they remain supporting evidence.

## Warnings

- No incomplete matched environments were detected.
