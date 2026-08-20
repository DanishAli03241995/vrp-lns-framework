# Section 6.5 Fixed Depot Timing and Fixed-Time Split Repair Extraction Summary

## Source Folders

- `results/hybrid_supplier_customer_kmeans_timing_fixed_v1`: Hybrid + KMeans with fixed depot ready time
- `results/hybrid_supplier_customer_kmeans_timing_fixed_split_v1`: Hybrid + KMeans with fixed depot ready time and split repair

## Output Files

- CSV: `extractor/section 6.5/section_6_5_fixed_timing_split_repair_table.csv`
- Summary: `extractor/section 6.5/section_6_5_fixed_timing_split_repair_summary.md`

## Extraction Rule

- The extractor selects the lexicographically latest `run_*` folder for every instance folder.
- Older timestamped folders are not written as main rows; `run_folder_count` records where multiple runs exist.
- The extractor deliberately excludes dispatch-wave timing, speed sensitivity, 14:00-wave sensitivity, time-aware LNS, and non-timing LNS folders.
- `best_n_remove` and `tested_n_remove_values` are left blank because Section 6.5 is a timing-baseline section, not an LNS section.

## Rows Written

- Total rows: 42
- `fixed_timing` rows: 21
- `fixed_timing_split_repair` rows: 21

## Expected Instance Grid

- Expected customer counts: `20, 40, 60, 80, 100, 150, 200`
- Expected vehicle capacities: `15, 25, 35`
- Missing `fixed_timing` rows: none
- Missing `fixed_timing_split_repair` rows: none

## Pre-Repair Versus Post-Repair Handling

- Fixed-timing rows use the fixed timing outputs as the pre-repair baseline.
- Split-repair rows keep pre-repair route-count and timing values from `depot_timing_fixed_repair_summary.json` fields such as `n_routes_before_repair`, `n_infeasible_routes_before_repair`, and `latest_finish_before_repair`.
- Split-repair rows keep post-repair route-count and timing values from `n_routes_after_repair`, `n_infeasible_routes_after_repair`, and `latest_finish_after_repair`, cross-checked against final timing metrics where available.
- `distance_before_repair` and `distance_after_repair` from the repair summary are stored as depot-outbound repair distances, not full system distances.
- Full pre-repair customer/system distances are derived from the final saved distances minus `distance_delta_after_fixed_timing_repair`; full post-repair customer/system distances use the final saved metrics.
- Derived delta fields compare post-repair values against pre-repair values only when both values are available.

## Split Repair Outcome Counts

- `split_rows`: 21
- `feasible_after_repair`: 21
- `infeasible_after_repair`: 0
- `unresolved_repair_rows`: 0
- `rows_with_repairs_attempted`: 2

## Run Folder Counts

- `fixed_timing`: min 1, max 6, instances with multiple runs 1
- `fixed_timing_split_repair`: min 2, max 4, instances with multiple runs 21

## Warnings

- Rows with warnings: 2
- `fixed_timing` `200c_cap15` `run_2026_07_16_170814`: timing infeasible
- `fixed_timing` `200c_cap35` `run_2026_07_16_170820`: timing infeasible

## Thesis Use Notes

- Use this extraction for Section 6.5 only.
- Treat fixed timing as feasibility flagging under a common depot ready time.
- Treat split repair as a route-level timing feasibility repair, not as split delivery of individual customer demand.
- Do not describe these rows as dispatch-wave timing or time-aware LNS.
