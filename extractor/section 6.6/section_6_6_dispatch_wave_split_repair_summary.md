# Section 6.6 Dispatch-Wave Timing and Same-Wave Split Repair Extraction Summary

## Source Folders

- `results/hybrid_supplier_customer_kmeans_timing_waves_constructed_v1`: Hybrid + KMeans with wave-aware dispatch construction
- `results/hybrid_supplier_customer_kmeans_timing_waves_constructed_split_v1`: Hybrid + KMeans with wave-aware dispatch construction and same-wave split repair
- `results/hybrid_supplier_customer_kmeans_timing_waves_v1`: archive/development only; not included in the main CSV

## Output Files

- CSV: `extractor/section 6.6/section_6_6_dispatch_wave_split_repair_table.csv`
- Summary: `extractor/section 6.6/section_6_6_dispatch_wave_split_repair_summary.md`

## Extraction Rule

- The extractor selects the latest `run_*` folder that matches the Section 6.6 base speed/wave parameters for every instance folder.
- Expected Section 6.6 parameters are speed 30 and dispatch waves 09:00, 11:00, 13:00, 15:00.
- If the newest timestamped run has the wrong speed or dispatch-wave list, it is skipped and recorded in the warnings/status notes.
- Only the two wave-aware final folders are written to the main CSV.
- The older route-first folder is inspected only as archive/development evidence and is not included in the main CSV.
- The extractor deliberately excludes fixed timing, speed40 sensitivity, 14:00-wave sensitivity, time-aware LNS, and non-timing LNS folders.
- `best_n_remove` and `tested_n_remove_values` are left blank because Section 6.6 is a timing-baseline section, not an LNS section.

## Rows Written

- Total rows: 42
- `dispatch_wave_constructed` rows: 21
- `dispatch_wave_constructed_split_repair` rows: 21

## Expected Instance Grid

- Expected customer counts: `20, 40, 60, 80, 100, 150, 200`
- Expected vehicle capacities: `15, 25, 35`
- Missing `dispatch_wave_constructed` rows: none
- Missing `dispatch_wave_constructed_split_repair` rows: none

## Route-First Dispatch-Wave Archive Folder

- Folder: `results/hybrid_supplier_customer_kmeans_timing_waves_v1`
- Exists: True
- Instance folders detected: 21
- Timestamped runs detected: 22
- Instances with multiple timestamped runs: 1
- Archive/development rows written to main CSV: 0

## Pre-Repair Versus Post-Repair Handling

- Wave-aware construction rows use final construction outputs as the pre-repair baseline.
- Split-repair rows keep pre-repair timing values from `depot_timing_wave_pre_repair_summary.json` and `depot_timing_wave_pre_repair_records.json`.
- Split-repair rows keep post-repair timing values from `depot_timing_wave_summary.json` and `depot_timing_wave_records.json`.
- `depot_distance_before_wave_repair` and `depot_distance_after_wave_repair` are stored as depot-outbound repair distances, not full system distances.
- Full pre-repair customer/system distances are derived from the final saved distances minus `distance_delta_after_wave_repair`; full post-repair customer/system distances use the final saved metrics.
- Derived delta fields compare post-repair values against pre-repair values only when both values are available.

## Same-Wave Split Repair Outcome Counts

- `split_rows`: 21
- `feasible_after_repair`: 18
- `infeasible_after_repair`: 3
- `unresolved_repair_rows`: 3
- `rows_with_repairs_attempted`: 9
- `rows_with_goods_ready_violations_after_repair`: 0
- `rows_with_workday_violations_after_repair`: 3

## Run Folder Counts

- `dispatch_wave_constructed`: min 2, max 4, instances with multiple runs 21
- `dispatch_wave_constructed_split_repair`: min 1, max 3, instances with multiple runs 1

## Warnings

- Rows with warnings/status notes: 13
- `dispatch_wave_constructed_split_repair` `40c_cap25` `run_2026_07_17_201712`: selected latest scenario-parameter-matching run; newer mismatched run(s) ignored: run_2026_07_17_204003
- `dispatch_wave_constructed` `100c_cap15` `run_2026_07_17_182631`: timing infeasible | routes exceed working day
- `dispatch_wave_constructed` `100c_cap25` `run_2026_07_17_182631`: timing infeasible | routes exceed working day
- `dispatch_wave_constructed` `100c_cap35` `run_2026_07_17_182632`: timing infeasible | routes exceed working day
- `dispatch_wave_constructed` `150c_cap15` `run_2026_07_17_182633`: timing infeasible | routes exceed working day
- `dispatch_wave_constructed` `150c_cap25` `run_2026_07_17_182633`: timing infeasible | routes exceed working day
- `dispatch_wave_constructed` `150c_cap35` `run_2026_07_17_182634`: timing infeasible | routes exceed working day
- `dispatch_wave_constructed` `200c_cap15` `run_2026_07_17_182635`: timing infeasible | routes exceed working day
- `dispatch_wave_constructed_split_repair` `200c_cap15` `run_2026_07_17_201720`: timing infeasible | routes exceed working day | unresolved same-wave split repair remains | unresolved customers after wave repair
- `dispatch_wave_constructed` `200c_cap25` `run_2026_07_17_182636`: timing infeasible | routes exceed working day
- `dispatch_wave_constructed_split_repair` `200c_cap25` `run_2026_07_17_201721`: timing infeasible | routes exceed working day | unresolved same-wave split repair remains | unresolved customers after wave repair
- `dispatch_wave_constructed` `200c_cap35` `run_2026_07_17_182637`: timing infeasible | routes exceed working day
- `dispatch_wave_constructed_split_repair` `200c_cap35` `run_2026_07_17_201721`: timing infeasible | routes exceed working day | unresolved same-wave split repair remains | unresolved customers after wave repair

## Thesis Use Notes

- Use this extraction for Section 6.6 only.
- Treat dispatch-wave construction as customer wave assignment before depot routing.
- Treat same-wave split repair as a route-level timing repair inside the assigned dispatch wave.
- Do not describe this as fixed timing, speed sensitivity, 14:00-wave sensitivity, or time-aware LNS.
- Do not describe route-first dispatch-wave results as final evidence.
- Remaining infeasibility after same-wave split repair should remain visible in the thesis discussion.
