#!/usr/bin/env python3
"""
Compute the final Section 6.4 matched 80-customer operator-pair table.

The table is intentionally limited to the common 80-customer comparison set:
2 routing cases x 3 structure variants x 3 vehicle capacities = 18
matched comparison environments. The output separates Case 2 and Case 3
instead of collapsing both routing structures into one average.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean


BASE_DIR = Path(__file__).resolve().parent
INPUT_CSV = BASE_DIR / "section_6_4_lns_operator_pair_table.csv"
OUTPUT_CSV = BASE_DIR / "section_6_4_operator_pair_80c_matched_summary.csv"
OUTPUT_MD = BASE_DIR / "section_6_4_operator_pair_80c_matched_summary.md"

OPERATOR_LABELS = {
    "random_greedy": "Random + Greedy",
    "random_regret": "Random + Regret-2",
    "worst_greedy": "Worst + Greedy",
    "worst_regret": "Worst + Regret-2",
    "related_greedy": "Related + Greedy",
    "related_regret": "Related + Regret-2",
}

OPERATOR_ORDER = [
    "related_regret",
    "random_regret",
    "random_greedy",
    "related_greedy",
    "worst_greedy",
    "worst_regret",
]

CASE_KEYS = ["case_2_supplier_customer_direct", "case_3_hybrid"]
CASE_SHORT = {
    "case_2_supplier_customer_direct": "case2",
    "case_3_hybrid": "case3",
}


def parse_float(value: str) -> float | None:
    if value in ("", None):
        return None
    return float(value)


def round4(value: float) -> str:
    return f"{value:.4f}"


def main() -> None:
    with INPUT_CSV.open(newline="") as f:
        rows = list(csv.DictReader(f))

    matched_rows = [
        row
        for row in rows
        if row["customer_count"] == "80"
        and row["routing_case"] in {"case_2_supplier_customer_direct", "case_3_hybrid"}
        and row["structure_variant"] in {"no_clustering", "sweep", "kmeans"}
        and row["vehicle_capacity"] in {"15", "25", "35"}
        and row["operator_pair"] in OPERATOR_LABELS
    ]

    buckets: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in matched_rows:
        key = (row["routing_case"], row["structure_variant"], row["vehicle_capacity"])
        buckets[key].append(row)

    stats = {
        operator: {
            case: {
                "wins": 0,
                "ranks": [],
                "improvements": [],
            }
            for case in CASE_KEYS
        }
        for operator in OPERATOR_ORDER
    }

    incomplete_buckets = []
    for key, bucket_rows in sorted(buckets.items()):
        present = {row["operator_pair"] for row in bucket_rows}
        missing = [operator for operator in OPERATOR_ORDER if operator not in present]
        if missing:
            incomplete_buckets.append((key, missing))

        comparable = []
        for row in bucket_rows:
            distance = parse_float(row["ranking_distance_used"])
            if distance is None:
                continue
            comparable.append((distance, row["operator_pair"], row))

        comparable.sort(key=lambda item: item[0])
        if not comparable:
            continue

        best_distance = comparable[0][0]
        for rank, (distance, operator_pair, row) in enumerate(comparable, start=1):
            case = row["routing_case"]
            stats[operator_pair][case]["ranks"].append(rank)
            improvement = parse_float(row["percent_improvement"])
            if improvement is not None:
                stats[operator_pair][case]["improvements"].append(improvement)
            if abs(distance - best_distance) < 1e-9:
                stats[operator_pair][case]["wins"] += 1

    output_rows = []
    for operator in OPERATOR_ORDER:
        row = {"operator_pair": OPERATOR_LABELS[operator], "operator_pair_key": operator}
        for case in CASE_KEYS:
            case_key = CASE_SHORT[case]
            ranks = stats[operator][case]["ranks"]
            improvements = stats[operator][case]["improvements"]
            row[f"{case_key}_best_ranked_environments"] = stats[operator][case]["wins"]
            row[f"{case_key}_average_rank"] = mean(ranks) if ranks else ""
            row[f"{case_key}_average_improvement_percent"] = mean(improvements) if improvements else ""
            row[f"{case_key}_matched_environments_used"] = len(ranks)
        output_rows.append(row)

    with OUTPUT_CSV.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "operator_pair",
                "operator_pair_key",
                "case2_best_ranked_environments",
                "case3_best_ranked_environments",
                "case2_average_rank",
                "case3_average_rank",
                "case2_average_improvement_percent",
                "case3_average_improvement_percent",
                "case2_matched_environments_used",
                "case3_matched_environments_used",
            ],
        )
        writer.writeheader()
        writer.writerows(output_rows)

    md_lines = [
        "# Section 6.4 Operator-Pair 80-Customer Matched Summary",
        "",
        "## Final Dataset",
        "",
        "| Operator Pair | Best-Ranked Environments Case 2 | Best-Ranked Environments Case 3 | Average Rank Case 2 | Average Rank Case 3 | Average Improvement (%) Case 2 | Average Improvement (%) Case 3 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]

    for row in output_rows:
        md_lines.append(
            "| {operator_pair} | {case2_wins} | {case3_wins} | {case2_rank} | {case3_rank} | {case2_improvement} | {case3_improvement} |".format(
                operator_pair=row["operator_pair"],
                case2_wins=row["case2_best_ranked_environments"],
                case3_wins=row["case3_best_ranked_environments"],
                case2_rank=round4(row["case2_average_rank"]),
                case3_rank=round4(row["case3_average_rank"]),
                case2_improvement=round4(row["case2_average_improvement_percent"]),
                case3_improvement=round4(row["case3_average_improvement_percent"]),
            )
        )

    md_lines.extend(
        [
            "",
            "## Matched Comparison Set",
            "",
            f"- Total comparison environments: {len(buckets)}",
            "- Cases included: Case 2 supplier-customer direct and Case 3 Hybrid.",
            "- Customer size: 80 customers.",
            "- Vehicle capacities: 15, 25, 35.",
            "- Clustering configurations: No Clustering, Sweep, KMeans.",
            "- Expected matched environments: 2 cases x 3 clustering configurations x 3 capacities = 18.",
            "- Matched environments per case: 3 clustering configurations x 3 capacities = 9.",
            "- Operator pairs per environment: 6.",
            f"- Rows used: {len(matched_rows)}.",
            "",
            "## Methodological Note",
            "",
            "- Each comparison environment is defined by `routing_case`, `structure_variant`, and `vehicle_capacity`, with `customer_count = 80`.",
            "- For each environment, the six operator pairs are ranked by `ranking_distance_used` in ascending order.",
            "- For Case 2, `ranking_distance_used` is the direct LNS distance.",
            "- For Case 3 Hybrid, `ranking_distance_used` is the LNS total system distance, including supplier-depot replenishment distance.",
            "- `Best-Ranked Environments` counts how many environments within each routing case an operator pair achieved the lowest ranking distance. If two operator pairs have exactly the same best distance, both are counted as best-ranked for that environment.",
            "- `Average Rank` is the arithmetic mean of the rank assigned to that operator pair across the 9 environments within the relevant routing case.",
            "- `Average Improvement (%)` is the arithmetic mean of `percent_improvement` across the same 9 case-specific environments. Each improvement percentage is relative to that environment's own pre-LNS baseline.",
            "- Case 2 and Case 3 are reported separately because they are different fulfilment structures and should not be hidden inside a single cross-case average.",
            "- The 20-, 40-, and 60-customer rows are not included in this main matched table; they remain supporting evidence.",
        ]
    )

    if incomplete_buckets:
        md_lines.extend(["", "## Warnings", ""])
        md_lines.append(f"- Incomplete buckets detected: {len(incomplete_buckets)}")
        for key, missing in incomplete_buckets:
            md_lines.append(f"- `{key}` missing: {', '.join(missing)}")
    else:
        md_lines.extend(
            [
                "",
                "## Warnings",
                "",
                "- No incomplete matched environments were detected.",
            ]
        )

    OUTPUT_MD.write_text("\n".join(md_lines) + "\n")

    print(f"Wrote {OUTPUT_CSV}")
    print(f"Wrote {OUTPUT_MD}")


if __name__ == "__main__":
    main()
