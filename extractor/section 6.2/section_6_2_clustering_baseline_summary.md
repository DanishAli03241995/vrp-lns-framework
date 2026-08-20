# Section 6.2 Clustering Baseline Extraction Summary

## Sources

- `results/generated_depot_customer_initial_pipeline`
- `results/generated_depot_customer_initial_pipeline_central_depot`
- `results/generated_depot_customer_sweep_initial_pipeline`
- `results/generated_depot_customer_sweep_initial_pipeline_central_depot`
- `results/generated_depot_customer_kmeans_initial_pipeline`
- `results/generated_depot_customer_kmeans_initial_pipeline_central_depot`

## Row Counts

- Rows expected: 72
- Rows written: 72
- Rows with warnings: 0

## Rows by Depot Setting

- `central_depot`: 36
- `corner_depot`: 36

## Rows by Clustering Strategy

- `kmeans`: 24
- `no_clustering`: 24
- `sweep`: 24

## Feasibility Checks

- Capacity-feasible rows: 72
- Customer-coverage-feasible rows: 72
- Structurally valid rows: 72

## Best Final Distance by Matched Group

- `central_depot 20c_cap15`: `sweep` with final distance 59.8428
- `central_depot 20c_cap25`: `sweep` with final distance 46.9411
- `central_depot 20c_cap35`: `sweep` with final distance 40.7816
- `central_depot 40c_cap15`: `kmeans` with final distance 217.6740
- `central_depot 40c_cap25`: `no_clustering` with final distance 167.2502
- `central_depot 40c_cap35`: `no_clustering` with final distance 137.1566
- `central_depot 60c_cap15`: `kmeans` with final distance 502.5122
- `central_depot 60c_cap25`: `no_clustering` with final distance 354.1006
- `central_depot 60c_cap35`: `sweep` with final distance 293.4518
- `central_depot 80c_cap15`: `kmeans` with final distance 835.5724
- `central_depot 80c_cap25`: `kmeans` with final distance 586.6891
- `central_depot 80c_cap35`: `sweep` with final distance 476.0876
- `corner_depot 20c_cap15`: `no_clustering` with final distance 85.8087
- `corner_depot 20c_cap25`: `no_clustering` with final distance 62.4284
- `corner_depot 20c_cap35`: `sweep` with final distance 48.5179
- `corner_depot 40c_cap15`: `kmeans` with final distance 350.3804
- `corner_depot 40c_cap25`: `kmeans` with final distance 247.1617
- `corner_depot 40c_cap35`: `kmeans` with final distance 192.3290
- `corner_depot 60c_cap15`: `kmeans` with final distance 839.5841
- `corner_depot 60c_cap25`: `no_clustering` with final distance 569.3718
- `corner_depot 60c_cap35`: `kmeans` with final distance 449.7507
- `corner_depot 80c_cap15`: `kmeans` with final distance 1389.8177
- `corner_depot 80c_cap25`: `kmeans` with final distance 912.6392
- `corner_depot 80c_cap35`: `kmeans` with final distance 720.2352

## Warnings

- No warnings recorded.

## Notes

- Final distance is extracted from `post_reloc_2opt_distance`.
- Route count is extracted from `trips`, with route-list length available as a possible cross-check.
- Cluster metadata is extracted from `clusters.json` for Sweep and KMeans only.
- Distance changes are computed against the no-clustering run within the same depot setting, customer count, and vehicle capacity.
- Supplier cases, LNS results, timing results, and broad Chapter 6 extraction are not included.
