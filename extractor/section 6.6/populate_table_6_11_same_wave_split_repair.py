#!/usr/bin/env python3
"""
Populate the Section 6.6 same-wave split-repair table.

The output includes only the nine dispatch-wave settings that required
same-wave split repair:
100, 150, and 200 customers with capacities 15, 25, and 35.
"""

from __future__ import annotations

import csv
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
INPUT_CSV = BASE_DIR / "section_6_6_dispatch_wave_split_repair_table.csv"
OUTPUT_CSV = BASE_DIR / "table_6_11_same_wave_split_repair.csv"
OUTPUT_MD = BASE_DIR / "table_6_11_same_wave_split_repair.md"

CUSTOMER_COUNTS = [100, 150, 200]
CAPACITIES = [15, 25, 35]
TIMING_VARIANT = "dispatch_wave_constructed_split_repair"

OUTPUT_FIELDS = [
    "Customers",
    "Capacity",
    "Depot Routes Before",
    "Depot Routes After",
    "Latest Finish Before",
    "Latest Finish After",
    "Distance Change (%)",
]


def read_rows() -> list[dict[str, str]]:
    with INPUT_CSV.open(newline="") as f:
        return list(csv.DictReader(f))


def format_percent(value: str) -> str:
    if value == "":
        return "NOT FOUND"
    return f"{float(value):.2f}"


def required_value(row: dict[str, str], key: str) -> str:
    value = row.get(key, "")
    return value if value != "" else "NOT FOUND"


def build_table_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    by_key = {
        (int(row["customer_count"]), int(row["vehicle_capacity"])): row
        for row in rows
        if row.get("timing_variant") == TIMING_VARIANT
        and int(row["customer_count"]) in CUSTOMER_COUNTS
        and int(row["vehicle_capacity"]) in CAPACITIES
    }

    output_rows: list[dict[str, str]] = []
    for customer_count in CUSTOMER_COUNTS:
        for capacity in CAPACITIES:
            row = by_key.get((customer_count, capacity))
            if row is None:
                output_rows.append(
                    {
                        "Customers": str(customer_count),
                        "Capacity": str(capacity),
                        "Depot Routes Before": "NOT FOUND",
                        "Depot Routes After": "NOT FOUND",
                        "Latest Finish Before": "NOT FOUND",
                        "Latest Finish After": "NOT FOUND",
                        "Distance Change (%)": "NOT FOUND",
                    }
                )
                continue

            output_rows.append(
                {
                    "Customers": str(customer_count),
                    "Capacity": str(capacity),
                    "Depot Routes Before": required_value(row, "pre_repair_depot_routes"),
                    "Depot Routes After": required_value(row, "post_repair_depot_routes"),
                    "Latest Finish Before": required_value(row, "pre_repair_latest_finish_time_label"),
                    "Latest Finish After": required_value(row, "post_repair_latest_finish_time_label"),
                    "Distance Change (%)": format_percent(row.get("distance_change_after_repair_pct", "")),
                }
            )
    return output_rows


def write_csv(rows: list[dict[str, str]]) -> None:
    with OUTPUT_CSV.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(rows: list[dict[str, str]]) -> None:
    lines = [
        "| Customers | Capacity | Depot Routes Before | Depot Routes After | Latest Finish Before | Latest Finish After | Distance Change (%) |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {Customers} | {Capacity} | {Depot Routes Before} | {Depot Routes After} | "
            "{Latest Finish Before} | {Latest Finish After} | {Distance Change (%)} |".format(**row)
        )
    OUTPUT_MD.write_text("\n".join(lines) + "\n")


def main() -> None:
    rows = build_table_rows(read_rows())
    write_csv(rows)
    write_markdown(rows)
    print(f"Wrote {OUTPUT_CSV}")
    print(f"Wrote {OUTPUT_MD}")


if __name__ == "__main__":
    main()
