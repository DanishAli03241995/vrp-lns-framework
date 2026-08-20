# Section 6.3 Case-Average Routing Structure Metrics

## Calculation Basis

- Input file: `section_6_3_supplier_routing_structures_table.csv`
- Filter applied: `clustering_strategy == kmeans`.
- Reason for filter: the Section 6.3 cross-case routing-structure comparison is a matched 12-setting comparison across Case 1, Case 2, and Case 3. KMeans is used as the representative common construction strategy because it is also carried forward into the Hybrid timing work.
- Experimental settings per case: 4 customer counts (`20, 40, 60, 80`) x 3 vehicle capacities (`15, 25, 35`) = 12.
- Rows with warnings are excluded. No KMeans rows used in this table contained warnings.

## Distance Rule Used

For operationally fair comparison, total system distance is recalculated from the extracted components:

```text
Total System Distance = Customer Delivery Distance + Supplier-Depot Replenishment Distance
```

For Case 2, supplier-depot replenishment distance is zero because customer delivery is direct from suppliers to customers, so total system distance equals customer delivery distance.

## Thesis Table Values

| Routing Structure | Settings Included | Avg. System Distance | Avg. Customer Delivery Distance | Avg. Routes | Avg. Vehicle Utilisation |
|---|---:|---:|---:|---:|---:|
| Case 1 | 12 | 348.92 | 318.92 | 9.42 | 0.815 |
| Case 2 | 12 | 335.92 | 335.92 | 13.00 | 0.570 |
| Case 3 | 12 | 520.88 | 413.55 | 11.00 | 0.682 |

## Sanity-Check Statistics

| Routing Structure | System Distance SD | System Distance Min | System Distance Max | Customer Delivery SD | Routes Min-Max | Utilisation Min-Max |
|---|---:|---:|---:|---:|---:|---:|
| Case 1 | 267.40 | 56.05 | 893.47 | 254.53 | 3.00-20.00 | 0.638-0.937 |
| Case 2 | 266.74 | 45.72 | 889.12 | 266.74 | 9.00-24.00 | 0.213-0.781 |
| Case 3 | 399.69 | 97.43 | 1367.17 | 315.83 | 6.00-24.00 | 0.319-0.865 |

## Reproducibility Notes

- The aggregation is case-level, not clustering-level: Sweep and no-clustering rows remain in the Section 6.3 full CSV but are not included in this 12-setting routing-structure table.
- `total_system_distance` is not averaged blindly; it is recalculated from `customer_delivery_distance` and `supplier_depot_replenishment_distance` so that Case 1 and Case 3 include replenishment while Case 2 remains direct-only.
- The generated CSV stores standard deviation, minimum, and maximum values for distance, route count, and utilisation so the averages can be checked before thesis writing.

## Warnings

- No mismatches were detected between recorded total system distance and recalculated component-based total system distance for the included rows.
