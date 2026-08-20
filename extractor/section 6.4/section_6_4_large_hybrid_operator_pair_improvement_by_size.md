# Section 6.4 Larger Hybrid LNS Improvement by Customer Size

## Final Dataset

| Operator Pair | 100 Customers | 150 Customers | 200 Customers |
|---|---:|---:|---:|
| Related + Regret-2 | 4.3199 | 3.5033 | 3.4090 |
| Random + Regret-2 | 4.0030 | 3.6533 | 3.5313 |
| Random + Greedy | 4.0358 | 3.3733 | 2.8600 |
| Related + Greedy | 4.5112 | 3.5276 | 2.9267 |
| Worst + Greedy | 3.0274 | 2.0725 | 2.2142 |
| Worst + Regret-2 | 2.8082 | 2.3733 | 2.1154 |

## Matched Comparison Basis

- Routing case included: Case 3 Hybrid only.
- Customer sizes: 100, 150, and 200 customers.
- Vehicle capacities per customer size: 15, 25, and 35.
- Structure variants per customer size: No Clustering, Sweep, and KMeans.
- Matched environments per cell: 3 capacities x 3 structure variants = 9.
- Operator pairs per customer size: 6.
- Total rows used: 162.

## Methodological Note

- Each table cell reports the average LNS improvement percentage for one operator pair at one customer size.
- The improvement is measured relative to the pre-LNS solution that enters LNS, i.e. the post-relocation/post-local-search baseline solution for that case.
- For Hybrid rows, `system_improvement_percent` is used because it compares total system distance, including supplier-depot replenishment distance.
- The table does not average 100, 150, and 200 customers together; the columns are kept separate to show how operator-pair behaviour changes with instance size.
- Final raw distances are not used in this table because they naturally increase with customer count and would not isolate the LNS contribution as clearly.

## Warnings

- No missing or incomplete larger-Hybrid environments were detected.
