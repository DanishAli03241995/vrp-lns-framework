# Section 6.7 Sensitivity Analysis Extraction Summary

## Source Folders

- `results/hybrid_supplier_customer_kmeans_timing_waves_constructed_split_v1`: Base dispatch-wave split-repair reference with speed 30 and waves 09/11/13/15
- `results/hybrid_supplier_customer_kmeans_timing_waves_constructed_split_v1_40_speed`: Speed sensitivity with average speed 40 and base dispatch waves
- `results/hybrid_supplier_customer_kmeans_timing_waves_constructed_split_14wave_v1`: Dispatch-policy sensitivity with speed 30 and an added 14:00 wave

## Explicitly Excluded Folders

- `results/hybrid_supplier_customer_kmeans_timing_fixed_v1`
- `results/hybrid_supplier_customer_kmeans_timing_fixed_split_v1`
- `results/hybrid_supplier_customer_kmeans_timing_waves_constructed_v1`
- `results/hybrid_supplier_customer_kmeans_timing_waves_v1`
- `results/lns_timing_*`
- `results/lns_operator_*`

## Output Files

- Long CSV: `extractor/section 6.7/section_6_7_sensitivity_analysis_table.csv`
- Speed comparison CSV: `extractor/section 6.7/section_6_7_speed_sensitivity_comparison.csv`
- 14:00-wave comparison CSV: `extractor/section 6.7/section_6_7_14wave_sensitivity_comparison.csv`
- Summary: `extractor/section 6.7/section_6_7_sensitivity_analysis_summary.md`

## Extraction Rule

- The extractor selects the latest `run_*` folder that matches the expected scenario parameters for every instance folder.
- If the newest timestamped run has the wrong speed or dispatch-wave list, it is skipped and recorded in the warnings/status notes.
- The base speed30 dispatch-wave split-repair folder is extracted again as the Section 6.7 reference scenario.
- The speed40 comparison changes average speed while keeping the base dispatch waves.
- The 14:00-wave comparison changes the dispatch-wave list while keeping speed at 30.
- The extractor does not read fixed timing, route-first waves, wave construction without split repair, time-aware LNS, or non-timing LNS result folders.

## Rows Written

- Long-format rows: 63
- Speed comparison rows: 21
- 14:00-wave comparison rows: 21
- `added_14_wave` rows: 21
- `base_speed30` rows: 21
- `speed40` rows: 21

## Expected Instance Grid

- Expected customer counts: `20, 40, 60, 80, 100, 150, 200`
- Expected vehicle capacities: `15, 25, 35`
- Missing `base_speed30` rows: none
- Missing `speed40` rows: none
- Missing `added_14_wave` rows: none

## Scenario Parameter Verification

### `base_speed30`
- Expected speed: 30.0
- Expected waves: [9.0, 11.0, 13.0, 15.0]
- Speed values extracted: 30.0
- Dispatch wave values extracted: [9.0, 11.0, 13.0, 15.0]
- `ok` rows: 21
### `speed40`
- Expected speed: 40.0
- Expected waves: [9.0, 11.0, 13.0, 15.0]
- Speed values extracted: 40
- Dispatch wave values extracted: [9.0, 11.0, 13.0, 15.0]
- `ok` rows: 21
### `added_14_wave`
- Expected speed: 30.0
- Expected waves: [9.0, 11.0, 13.0, 14.0, 15.0]
- Speed values extracted: 30
- Dispatch wave values extracted: [9.0, 11.0, 13.0, 14.0, 15.0]
- `ok` rows: 21

## Feasibility Summary By Scenario

### `added_14_wave`
- Feasible timing rows: 21
- Infeasible timing rows: 0
- Rows with post-repair workday violations: 0
- Rows with unresolved repairs: 0
- Total unresolved customers: 0.0
### `base_speed30`
- Feasible timing rows: 18
- Infeasible timing rows: 3
- Rows with post-repair workday violations: 3
- Rows with unresolved repairs: 3
- Total unresolved customers: 15.0
### `speed40`
- Feasible timing rows: 21
- Infeasible timing rows: 0
- Rows with post-repair workday violations: 0
- Rows with unresolved repairs: 0
- Total unresolved customers: 0.0

## Matched Comparison Summary

- Speed comparison matched rows written: 21
- Speed comparison rows with missing pair warnings: 0
- 14:00-wave comparison matched rows written: 21
- 14:00-wave comparison rows with missing pair warnings: 0

## Warnings / Status Notes

- Long-format rows with warnings/status notes: 4
- `base_speed30` `40c_cap25` `run_2026_07_17_201712`: selected latest scenario-parameter-matching run; newer mismatched run(s) ignored: run_2026_07_17_204003
- `base_speed30` `200c_cap15` `run_2026_07_17_201720`: timing infeasible | routes exceed working day | unresolved same-wave split repair remains | unresolved customers after wave repair
- `base_speed30` `200c_cap25` `run_2026_07_17_201721`: timing infeasible | routes exceed working day | unresolved same-wave split repair remains | unresolved customers after wave repair
- `base_speed30` `200c_cap35` `run_2026_07_17_201721`: timing infeasible | routes exceed working day | unresolved same-wave split repair remains | unresolved customers after wave repair

## Thesis Use Notes

- Use this extraction for Section 6.7 only.
- Treat `base_speed30` as the reference scenario for both matched comparisons.
- Treat `speed40` as speed sensitivity only; the dispatch-wave list should remain 09/11/13/15.
- Treat `added_14_wave` as dispatch-policy sensitivity only; average speed should remain 30.
- Do not mix these rows with fixed timing, route-first waves, wave construction without split repair, or timing-aware LNS results.
- Remaining timing infeasibility and unresolved repairs should remain visible in the thesis discussion.
