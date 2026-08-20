# Section 6.3 Supplier Routing Structures Extraction Summary

## Sources

- `results/supplier_depot_customer_baseline_sweep_v1`
- `results/supplier_depot_customer_baseline_kmeans_v1`
- `results/supplier_customer_only_baseline_sweep_v1`
- `results/supplier_customer_only_baseline_kmeans_v1`
- `results/supplier_customer_only_no_cluster_v1`
- `results/hybrid_supplier_customer_sweep_v1`
- `results/hybrid_supplier_customer_kmeans_v1`
- `results/hybrid_supplier_customer_no_cluster_v1`

## Main Grid

- Customer counts included in main CSV: `20, 40, 60, 80`.
- Vehicle capacities included in main CSV: `15, 25, 35`.
- Case 3 larger `100, 150, 200` customer runs are detected but not mixed into the main cross-case table.

## Row Counts

- Rows written: 108
- Rows with warnings: 12

## Rows by Routing Case

- `case_1_supplier_depot_customer`: 36
- `case_2_supplier_customer_direct`: 36
- `case_3_hybrid`: 36

## Rows by Clustering Strategy

- `kmeans`: 36
- `no_clustering`: 24
- `not_available`: 12
- `sweep`: 36

## Feasibility Checks

- Capacity-feasible rows: 96
- Customer-coverage-feasible rows: 96
- Supplier-feasible rows: 96
- Structurally valid rows: 96

## Hybrid Replenishment Check

- Hybrid rows in main grid: 36
- Hybrid rows with clean total-system-distance check and no warnings: 36
- The extractor selects the latest `run_*` folder in each instance directory.
- Hybrid rows are flagged if depot-bound customers exist but first-echelon replenishment distance is zero.

## Extra Hybrid Instances Detected

- `results/hybrid_supplier_customer_kmeans_v1`: 100c_cap15, 100c_cap25, 100c_cap35, 150c_cap15, 150c_cap25, 150c_cap35, 200c_cap15, 200c_cap25, 200c_cap35
- `results/hybrid_supplier_customer_no_cluster_v1`: 100c_cap15, 100c_cap25, 100c_cap35, 150c_cap15, 150c_cap25, 150c_cap35, 200c_cap15, 200c_cap25, 200c_cap35
- `results/hybrid_supplier_customer_sweep_v1`: 100c_cap15, 100c_cap25, 100c_cap35, 150c_cap15, 150c_cap25, 150c_cap35, 200c_cap15, 200c_cap25, 200c_cap35

## Warnings

- `case_1_supplier_depot_customer not_available 20c_cap15`: Case 1 no-clustering result folder not available
- `case_1_supplier_depot_customer not_available 20c_cap25`: Case 1 no-clustering result folder not available
- `case_1_supplier_depot_customer not_available 20c_cap35`: Case 1 no-clustering result folder not available
- `case_1_supplier_depot_customer not_available 40c_cap15`: Case 1 no-clustering result folder not available
- `case_1_supplier_depot_customer not_available 40c_cap25`: Case 1 no-clustering result folder not available
- `case_1_supplier_depot_customer not_available 40c_cap35`: Case 1 no-clustering result folder not available
- `case_1_supplier_depot_customer not_available 60c_cap15`: Case 1 no-clustering result folder not available
- `case_1_supplier_depot_customer not_available 60c_cap25`: Case 1 no-clustering result folder not available
- `case_1_supplier_depot_customer not_available 60c_cap35`: Case 1 no-clustering result folder not available
- `case_1_supplier_depot_customer not_available 80c_cap15`: Case 1 no-clustering result folder not available
- `case_1_supplier_depot_customer not_available 80c_cap25`: Case 1 no-clustering result folder not available
- `case_1_supplier_depot_customer not_available 80c_cap35`: Case 1 no-clustering result folder not available

## Notes

- `customer_delivery_distance` is extracted from `post_reloc_2opt_distance`.
- `total_system_distance` is extracted from `post_reloc_2opt_total_system_distance`.
- `supplier_depot_replenishment_distance` prefers `supplier_depot_replenishment_distance` and falls back to `total_first_echelon_distance`.
- Case 1 no-clustering rows are written as `not_available` placeholders.
- LNS, timing, dispatch-wave, split-repair, and time-aware LNS folders are excluded.
