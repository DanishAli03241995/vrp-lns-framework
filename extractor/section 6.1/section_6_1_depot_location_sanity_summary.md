# Section 6.1.2 Depot-Location Sanity Check Extraction Summary

## Sources

- Corner-depot folder: `results/generated_depot_customer_initial_pipeline`
- Central-depot folder: `results/generated_depot_customer_initial_pipeline_central_depot`
- Rows expected: 12
- Rows written: 12
- Rows with warnings: 0
- Corner capacity-feasible rows: 12
- Central capacity-feasible rows: 12
- Corner customer-coverage-feasible rows: 12
- Central customer-coverage-feasible rows: 12

## Output

- CSV file: `section_6_1_depot_location_sanity_table.csv`

## Notes

- This is a depot-location sanity check, not depot-location optimisation.
- Final distance is extracted from `post_reloc_2opt_distance` for both depot settings.
- Route count is extracted from `trips` for both depot settings.
- Average utilisation is extracted from `post_reloc_2opt_avg_utilization` for both depot settings.
- Supplier cases, clustering, LNS, and timing results are not included.
