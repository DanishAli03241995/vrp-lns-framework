#!/usr/bin/env python3
"""
Compute the Section 6.4 larger-Hybrid operator-pair improvement table.

Each cell is the average LNS improvement percentage for one operator pair and
one customer size, averaged over:
3 vehicle capacities x 3 structure variants = 9 matched environments.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean


BASE_DIR = Path(__file__).resolve().parent
INPUT_CSV = BASE_DIR / "section_6_4_lns_operator_pair_table.csv"
OUTPUT_CSV = BASE_DIR / "section_6_4_large_hybrid_operator_pair_improvement_by_size.csv"
OUTPUT_MD = BASE_DIR / "section_6_4_large_hybrid_operator_pair_improvement_by_size.md"

OPERATOR_LABELS = {
    "related_regret": "Related + Regret-2",
    "random_regret": "Random + Regret-2",
    "random_greedy": "Random + Greedy",
    "related_greedy": "Related + Greedy",
    "worst_greedy": "Worst + Greedy",
    "worst_regret": "Worst + Regret-2",
}

OPERATOR_ORDER = [
    "related_regret",
    "random_regret",
    "random_greedy",
    "related_greedy",
    "worst_greedy",
    "worst_regret",
]

CUSTOMER_SIZES = ["100", "150", "200"]
STRUCTURES = {"kmeans", "sweep", "no_clustering"}
CAPACITIES = {"15", "25", "35"}


def parse_float(value: str) -> float | None:
    if value in ("", None):
        return None
    return float(value)


def format4(value: float) -> str:
    return f"{value:.4f}"


def main() -> None:
    with INPUT_CSV.open(newline="") as f:
        rows = list(csv.DictReader(f))

    relevant_rows = [
        row
        for row in rows
        if row["routing_case"] == "case_3_hybrid"
        and row["customer_count"] in CUSTOMER_SIZES
        and row["structure_variant"] in STRUCTURES
        and row["vehicle_capacity"] in CAPACITIES
        and row["operator_pair"] in OPERATOR_LABELS
    ]

    grouped: dict[tuple[str, str], list[float]] = defaultdict(list)
    environments: dict[tuple[str, str], set[tuple[str, str]]] = defaultdict(set)
    warnings = []

    for row in relevant_rows:
        key = (row["operator_pair"], row["customer_count"])
        improvement = parse_float(row.get("system_improvement_percent", ""))
        if improvement is None:
            improvement = parse_float(row.get("percent_improvement", ""))
        if improvement is None:
            warnings.append(
                f"Missing improvement for {row['operator_pair']} {row['instance_name']} {row['structure_variant']}"
            )
            continue
        grouped[key].append(improvement)
        environments[key].add((row["structure_variant"], row["vehicle_capacity"]))

    output_rows = []
    for operator in OPERATOR_ORDER:
        output_row = {"operator_pair": OPERATOR_LABELS[operator], "operator_pair_key": operator}
        for size in CUSTOMER_SIZES:
            key = (operator, size)
            vals = grouped[key]
            output_row[f"{size}_customers_avg_improvement_percent"] = mean(vals) if vals else ""
            output_row[f"{size}_customers_environment_count"] = len(environments[key])
            if len(environments[key]) != 9:
                warnings.append(
                    f"{operator} {size} customers has {len(environments[key])} environments instead of 9"
                )
        output_rows.append(output_row)

    fieldnames = [
        "operator_pair",
        "operator_pair_key",
        "100_customers_avg_improvement_percent",
        "100_customers_environment_count",
        "150_customers_avg_improvement_percent",
        "150_customers_environment_count",
        "200_customers_avg_improvement_percent",
        "200_customers_environment_count",
    ]

    with OUTPUT_CSV.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    md_lines = [
        "# Section 6.4 Larger Hybrid LNS Improvement by Customer Size",
        "",
        "## Final Dataset",
        "",
        "| Operator Pair | 100 Customers | 150 Customers | 200 Customers |",
        "|---|---:|---:|---:|",
    ]

    for row in output_rows:
        md_lines.append(
            "| {op} | {c100} | {c150} | {c200} |".format(
                op=row["operator_pair"],
                c100=format4(row["100_customers_avg_improvement_percent"]),
                c150=format4(row["150_customers_avg_improvement_percent"]),
                c200=format4(row["200_customers_avg_improvement_percent"]),
            )
        )

    md_lines.extend(
        [
            "",
            "## Matched Comparison Basis",
            "",
            "- Routing case included: Case 3 Hybrid only.",
            "- Customer sizes: 100, 150, and 200 customers.",
            "- Vehicle capacities per customer size: 15, 25, and 35.",
            "- Structure variants per customer size: No Clustering, Sweep, and KMeans.",
            "- Matched environments per cell: 3 capacities x 3 structure variants = 9.",
            "- Operator pairs per customer size: 6.",
            "- Total rows used: 162.",
            "",
            "## Methodological Note",
            "",
            "- Each table cell reports the average LNS improvement percentage for one operator pair at one customer size.",
            "- The improvement is measured relative to the pre-LNS solution that enters LNS, i.e. the post-relocation/post-local-search baseline solution for that case.",
            "- For Hybrid rows, `system_improvement_percent` is used because it compares total system distance, including supplier-depot replenishment distance.",
            "- The table does not average 100, 150, and 200 customers together; the columns are kept separate to show how operator-pair behaviour changes with instance size.",
            "- Final raw distances are not used in this table because they naturally increase with customer count and would not isolate the LNS contribution as clearly.",
        ]
    )

    if warnings:
        md_lines.extend(["", "## Warnings", ""])
        for warning in warnings:
            md_lines.append(f"- {warning}")
    else:
        md_lines.extend(["", "## Warnings", "", "- No missing or incomplete larger-Hybrid environments were detected."])

    OUTPUT_MD.write_text("\n".join(md_lines) + "\n")

    print(f"Wrote {OUTPUT_CSV}")
    print(f"Wrote {OUTPUT_MD}")


if __name__ == "__main__":
    main()
