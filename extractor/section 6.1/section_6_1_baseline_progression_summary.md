# Section 6.1.1 Baseline Progression Extraction Summary

## Source

- Source folder: `results/generated_depot_customer_initial_pipeline`
- Rows expected: 12
- Rows written: 12
- Rows with warnings: 0
- Capacity-feasible rows: 12
- Customer-coverage-feasible rows: 12

## Output

- CSV file: `section_6_1_baseline_progression_table.csv`

## Notes

- Final distance is extracted from `post_reloc_2opt_distance`.
- Final route count is extracted from `trips`, with route-list length available as a possible cross-check.
- Improvement percentages are recomputed from stage distances.
- Supplier cases, clustering, LNS, and timing results are not included.
