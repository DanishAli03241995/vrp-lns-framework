#!/usr/bin/env python3
"""
Compute Section 6.3 routing-structure averages from the final extracted CSV.

This script intentionally uses the KMeans rows only, because the Section 6.3
cross-case comparison is designed as a 12-setting matched comparison:
4 customer counts x 3 vehicle capacities for each routing case.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean, stdev


BASE_DIR = Path(__file__).resolve().parent
INPUT_CSV = BASE_DIR / "section_6_3_supplier_routing_structures_table.csv"
OUTPUT_CSV = BASE_DIR / "section_6_3_case_average_routing_structure_metrics.csv"
OUTPUT_MD = BASE_DIR / "section_6_3_case_average_routing_structure_metrics_summary.md"

CASE_LABELS = {
    "case_1_supplier_depot_customer": "Case 1",
    "case_2_supplier_customer_direct": "Case 2",
    "case_3_hybrid": "Case 3",
}


def parse_float(value: str, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    return float(value)


def sample_stdev(values: list[float]) -> float:
    return stdev(values) if len(values) > 1 else 0.0


def rounded(value: float) -> str:
    return f"{value:.2f}"


def main() -> None:
    with INPUT_CSV.open(newline="") as f:
        rows = list(csv.DictReader(f))

    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    skipped_rows = []
    total_distance_mismatches = []

    for row in rows:
        case = row["routing_case"]
        if case not in CASE_LABELS:
            skipped_rows.append((row.get("instance_name", ""), case, "unknown routing case"))
            continue
        if row["clustering_strategy"] != "kmeans":
            continue
        if row.get("notes_or_warnings"):
            skipped_rows.append((row.get("instance_name", ""), case, row["notes_or_warnings"]))
            continue

        customer_delivery_distance = parse_float(row["customer_delivery_distance"])
        replenishment_distance = parse_float(row["supplier_depot_replenishment_distance"])
        calculated_total_system_distance = customer_delivery_distance + replenishment_distance
        recorded_total_system_distance = parse_float(row["total_system_distance"])

        if abs(calculated_total_system_distance - recorded_total_system_distance) > 1e-6:
            total_distance_mismatches.append(
                {
                    "case": case,
                    "instance": row["instance_name"],
                    "recorded": recorded_total_system_distance,
                    "calculated": calculated_total_system_distance,
                }
            )

        row = dict(row)
        row["_calculated_total_system_distance"] = str(calculated_total_system_distance)
        grouped[case].append(row)

    summary_rows = []
    for case_key in CASE_LABELS:
        case_rows = grouped[case_key]
        system_distances = [parse_float(r["_calculated_total_system_distance"]) for r in case_rows]
        customer_distances = [parse_float(r["customer_delivery_distance"]) for r in case_rows]
        routes = [parse_float(r["n_routes"]) for r in case_rows]
        utilisations = [parse_float(r["avg_utilisation"]) for r in case_rows]

        summary_rows.append(
            {
                "routing_case": CASE_LABELS[case_key],
                "routing_case_key": case_key,
                "clustering_strategy_used": "kmeans",
                "experimental_settings_included": len(case_rows),
                "avg_total_system_distance": mean(system_distances),
                "std_total_system_distance": sample_stdev(system_distances),
                "min_total_system_distance": min(system_distances),
                "max_total_system_distance": max(system_distances),
                "avg_customer_delivery_distance": mean(customer_distances),
                "std_customer_delivery_distance": sample_stdev(customer_distances),
                "min_customer_delivery_distance": min(customer_distances),
                "max_customer_delivery_distance": max(customer_distances),
                "avg_routes": mean(routes),
                "std_routes": sample_stdev(routes),
                "min_routes": min(routes),
                "max_routes": max(routes),
                "avg_vehicle_utilisation": mean(utilisations),
                "std_vehicle_utilisation": sample_stdev(utilisations),
                "min_vehicle_utilisation": min(utilisations),
                "max_vehicle_utilisation": max(utilisations),
            }
        )

    fieldnames = list(summary_rows[0].keys())
    with OUTPUT_CSV.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in summary_rows:
            writer.writerow(row)

    md_lines = [
        "# Section 6.3 Case-Average Routing Structure Metrics",
        "",
        "## Calculation Basis",
        "",
        f"- Input file: `{INPUT_CSV.name}`",
        "- Filter applied: `clustering_strategy == kmeans`.",
        "- Reason for filter: the Section 6.3 cross-case routing-structure comparison is a matched 12-setting comparison across Case 1, Case 2, and Case 3. KMeans is used as the representative common construction strategy because it is also carried forward into the Hybrid timing work.",
        "- Experimental settings per case: 4 customer counts (`20, 40, 60, 80`) x 3 vehicle capacities (`15, 25, 35`) = 12.",
        "- Rows with warnings are excluded. No KMeans rows used in this table contained warnings.",
        "",
        "## Distance Rule Used",
        "",
        "For operationally fair comparison, total system distance is recalculated from the extracted components:",
        "",
        "```text",
        "Total System Distance = Customer Delivery Distance + Supplier-Depot Replenishment Distance",
        "```",
        "",
        "For Case 2, supplier-depot replenishment distance is zero because customer delivery is direct from suppliers to customers, so total system distance equals customer delivery distance.",
        "",
        "## Thesis Table Values",
        "",
        "| Routing Structure | Settings Included | Avg. System Distance | Avg. Customer Delivery Distance | Avg. Routes | Avg. Vehicle Utilisation |",
        "|---|---:|---:|---:|---:|---:|",
    ]

    for row in summary_rows:
        md_lines.append(
            "| {case} | {n} | {system} | {customer} | {routes} | {util} |".format(
                case=row["routing_case"],
                n=row["experimental_settings_included"],
                system=rounded(row["avg_total_system_distance"]),
                customer=rounded(row["avg_customer_delivery_distance"]),
                routes=rounded(row["avg_routes"]),
                util=f"{row['avg_vehicle_utilisation']:.3f}",
            )
        )

    md_lines.extend(
        [
            "",
            "## Sanity-Check Statistics",
            "",
            "| Routing Structure | System Distance SD | System Distance Min | System Distance Max | Customer Delivery SD | Routes Min-Max | Utilisation Min-Max |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )

    for row in summary_rows:
        md_lines.append(
            "| {case} | {sd} | {minv} | {maxv} | {cust_sd} | {rmin}-{rmax} | {umin}-{umax} |".format(
                case=row["routing_case"],
                sd=rounded(row["std_total_system_distance"]),
                minv=rounded(row["min_total_system_distance"]),
                maxv=rounded(row["max_total_system_distance"]),
                cust_sd=rounded(row["std_customer_delivery_distance"]),
                rmin=rounded(row["min_routes"]),
                rmax=rounded(row["max_routes"]),
                umin=f"{row['min_vehicle_utilisation']:.3f}",
                umax=f"{row['max_vehicle_utilisation']:.3f}",
            )
        )

    md_lines.extend(
        [
            "",
            "## Reproducibility Notes",
            "",
            "- The aggregation is case-level, not clustering-level: Sweep and no-clustering rows remain in the Section 6.3 full CSV but are not included in this 12-setting routing-structure table.",
            "- `total_system_distance` is not averaged blindly; it is recalculated from `customer_delivery_distance` and `supplier_depot_replenishment_distance` so that Case 1 and Case 3 include replenishment while Case 2 remains direct-only.",
            "- The generated CSV stores standard deviation, minimum, and maximum values for distance, route count, and utilisation so the averages can be checked before thesis writing.",
        ]
    )

    if total_distance_mismatches:
        md_lines.extend(["", "## Warnings", ""])
        md_lines.append(
            f"- {len(total_distance_mismatches)} rows had a mismatch between recorded and recalculated total system distance."
        )
        for mismatch in total_distance_mismatches:
            md_lines.append(
                "- `{case}` `{instance}`: recorded `{recorded:.6f}`, recalculated `{calculated:.6f}`".format(
                    **mismatch
                )
            )
    else:
        md_lines.extend(
            [
                "",
                "## Warnings",
                "",
                "- No mismatches were detected between recorded total system distance and recalculated component-based total system distance for the included rows.",
            ]
        )

    if skipped_rows:
        md_lines.extend(["", "## Skipped Rows", ""])
        for instance, case, reason in skipped_rows:
            md_lines.append(f"- `{case}` `{instance}`: {reason}")

    OUTPUT_MD.write_text("\n".join(md_lines) + "\n")

    print(f"Wrote {OUTPUT_CSV}")
    print(f"Wrote {OUTPUT_MD}")


if __name__ == "__main__":
    main()
