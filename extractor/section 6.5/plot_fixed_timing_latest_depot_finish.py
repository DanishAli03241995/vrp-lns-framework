#!/usr/bin/env python3
"""
Generate Section 6.5 figure: latest depot-route finish time under fixed timing.

The figure uses only fixed-timing rows before split repair from:
section_6_5_fixed_timing_split_repair_table.csv
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MultipleLocator


BASE_DIR = Path(__file__).resolve().parent
INPUT_CSV = BASE_DIR / "section_6_5_fixed_timing_split_repair_table.csv"
OUTPUT_DATA_CSV = BASE_DIR / "section_6_5_fixed_timing_latest_finish_plot_data.csv"
OUTPUT_PNG = BASE_DIR / "section_6_5_fixed_timing_latest_depot_finish.png"
OUTPUT_PDF = BASE_DIR / "section_6_5_fixed_timing_latest_depot_finish.pdf"
OUTPUT_CAPTION = BASE_DIR / "section_6_5_fixed_timing_latest_depot_finish_caption.md"

CUSTOMER_COUNTS = [20, 40, 60, 80, 100, 150, 200]
CAPACITIES = [15, 25, 35]
WORKING_DAY_LIMIT = 18.0


def parse_float(value: str) -> float:
    return float(value)


def decimal_hour_to_label(hour: float) -> str:
    total_minutes = int(round(hour * 60))
    hh, mm = divmod(total_minutes, 60)
    return f"{hh:02d}:{mm:02d}"


def time_axis_formatter(value: float, _position: int) -> str:
    return decimal_hour_to_label(value)


def load_fixed_timing_rows() -> list[dict[str, str]]:
    with INPUT_CSV.open(newline="") as f:
        rows = list(csv.DictReader(f))
    return [
        row
        for row in rows
        if row["timing_variant"] == "fixed_timing"
        and int(row["customer_count"]) in CUSTOMER_COUNTS
        and int(row["vehicle_capacity"]) in CAPACITIES
    ]


def write_plot_data(rows: list[dict[str, str]]) -> None:
    fieldnames = [
        "customer_count",
        "vehicle_capacity",
        "latest_finish_time_decimal_hours",
        "latest_finish_time_label",
        "working_day_limit_decimal_hours",
        "working_day_limit_label",
        "timing_feasible",
        "selected_run_timestamp",
    ]
    with OUTPUT_DATA_CSV.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in sorted(rows, key=lambda r: (int(r["vehicle_capacity"]), int(r["customer_count"]))):
            latest = parse_float(row["latest_finish_time"])
            writer.writerow(
                {
                    "customer_count": row["customer_count"],
                    "vehicle_capacity": row["vehicle_capacity"],
                    "latest_finish_time_decimal_hours": f"{latest:.6f}",
                    "latest_finish_time_label": decimal_hour_to_label(latest),
                    "working_day_limit_decimal_hours": f"{WORKING_DAY_LIMIT:.1f}",
                    "working_day_limit_label": decimal_hour_to_label(WORKING_DAY_LIMIT),
                    "timing_feasible": row["overall_timing_feasible"],
                    "selected_run_timestamp": row["selected_run_timestamp"],
                }
            )


def make_plot(rows: list[dict[str, str]]) -> None:
    values = {
        capacity: {
            int(row["customer_count"]): parse_float(row["latest_finish_time"])
            for row in rows
            if int(row["vehicle_capacity"]) == capacity
        }
        for capacity in CAPACITIES
    }

    plt.rcParams.update(
        {
            "font.size": 10,
            "axes.labelsize": 11,
            "axes.titlesize": 12,
            "legend.fontsize": 9,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )

    fig, ax = plt.subplots(figsize=(7.2, 4.5), constrained_layout=True)

    styles = {
        15: {"marker": "o", "linestyle": "-", "color": "#1b1b1b", "label": "Capacity 15"},
        25: {"marker": "s", "linestyle": "--", "color": "#2f6f9f", "label": "Capacity 25"},
        35: {"marker": "^", "linestyle": "-.", "color": "#b45f06", "label": "Capacity 35"},
    }

    for capacity in CAPACITIES:
        y_values = [values[capacity][customer_count] for customer_count in CUSTOMER_COUNTS]
        ax.plot(CUSTOMER_COUNTS, y_values, linewidth=1.8, markersize=4.6, **styles[capacity])

        for customer_count, finish_time in zip(CUSTOMER_COUNTS, y_values):
            if finish_time > WORKING_DAY_LIMIT:
                ax.scatter(
                    [customer_count],
                    [finish_time],
                    s=68,
                    facecolors="none",
                    edgecolors="#1b1b1b",
                    linewidths=1.4,
                    zorder=5,
                )

    ax.axhline(WORKING_DAY_LIMIT, color="#7a7a7a", linestyle="--", linewidth=1.0)
    ax.text(
        105,
        WORKING_DAY_LIMIT + 0.18,
        "18:00 working-day limit",
        ha="left",
        va="bottom",
        fontsize=9,
        color="#6a6a6a",
    )

    ax.set_xlabel("Customer count")
    ax.set_ylabel("Latest depot-route finish time")
    ax.set_xticks(CUSTOMER_COUNTS)
    ax.yaxis.set_major_locator(MultipleLocator(1.0))
    ax.yaxis.set_major_formatter(FuncFormatter(time_axis_formatter))
    ax.set_ylim(10.0, 19.25)
    ax.grid(True, axis="y", linestyle=":", linewidth=0.7, color="0.8")
    ax.grid(False, axis="x")
    ax.legend(
        loc="lower right",
        frameon=True,
        framealpha=0.92,
        edgecolor="0.85",
        facecolor="white",
        ncol=1,
        handlelength=2.4,
        borderpad=0.6,
        labelspacing=0.45,
    )

    fig.savefig(OUTPUT_PNG, dpi=300)
    fig.savefig(OUTPUT_PDF)
    plt.close(fig)


def write_caption() -> None:
    caption = """# Figure Caption: Fixed Depot Timing Latest Finish Time

Latest depot-route completion time under the fixed depot-ready-time model for the Hybrid + KMeans routing structure before split repair. Each line represents one vehicle-capacity setting, and the dashed horizontal reference line marks the 18:00 working-day limit. The figure shows that all instances up to 150 customers remain within the timing limit, while two 200-customer settings exceed the threshold, indicating the point at which distance-optimised depot routes begin to become operationally infeasible under the fixed timing assumption.
"""
    OUTPUT_CAPTION.write_text(caption)


def main() -> None:
    rows = load_fixed_timing_rows()
    expected = len(CUSTOMER_COUNTS) * len(CAPACITIES)
    if len(rows) != expected:
        raise RuntimeError(f"Expected {expected} fixed-timing rows, found {len(rows)}")

    seen = {(int(row["customer_count"]), int(row["vehicle_capacity"])) for row in rows}
    missing = [
        (customer_count, capacity)
        for customer_count in CUSTOMER_COUNTS
        for capacity in CAPACITIES
        if (customer_count, capacity) not in seen
    ]
    if missing:
        raise RuntimeError(f"Missing fixed-timing combinations: {missing}")

    write_plot_data(rows)
    make_plot(rows)
    write_caption()

    print(f"Wrote {OUTPUT_DATA_CSV}")
    print(f"Wrote {OUTPUT_PNG}")
    print(f"Wrote {OUTPUT_PDF}")
    print(f"Wrote {OUTPUT_CAPTION}")


if __name__ == "__main__":
    main()
