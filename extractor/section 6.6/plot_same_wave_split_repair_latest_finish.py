#!/usr/bin/env python3
"""
Generate Section 6.6 figure: latest depot-route finish before/after repair.

The figure uses the maximum latest depot-route finish time across capacities
for the nine same-wave split-repair settings:
100, 150, and 200 customers with capacities 15, 25, and 35.
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MultipleLocator


BASE_DIR = Path(__file__).resolve().parent
INPUT_CSV = BASE_DIR / "section_6_6_dispatch_wave_split_repair_table.csv"
OUTPUT_DATA_CSV = BASE_DIR / "figure_6_6_same_wave_split_repair_latest_finish_data.csv"
OUTPUT_PNG = BASE_DIR / "figure_6_6_same_wave_split_repair_latest_finish.png"
OUTPUT_PDF = BASE_DIR / "figure_6_6_same_wave_split_repair_latest_finish.pdf"
OUTPUT_CAPTION = BASE_DIR / "figure_6_6_same_wave_split_repair_latest_finish_caption.md"

CUSTOMER_COUNTS = [100, 150, 200]
CAPACITIES = [15, 25, 35]
TIMING_VARIANT = "dispatch_wave_constructed_split_repair"
WORKING_DAY_LIMIT = 18.0


def decimal_hour_to_label(hour: float) -> str:
    total_minutes = int(round(hour * 60))
    hh, mm = divmod(total_minutes, 60)
    return f"{hh:02d}:{mm:02d}"


def time_axis_formatter(value: float, _position: int) -> str:
    return decimal_hour_to_label(value)


def read_repair_rows() -> list[dict[str, str]]:
    with INPUT_CSV.open(newline="") as f:
        rows = list(csv.DictReader(f))
    return [
        row
        for row in rows
        if row["timing_variant"] == TIMING_VARIANT
        and int(row["customer_count"]) in CUSTOMER_COUNTS
        and int(row["vehicle_capacity"]) in CAPACITIES
    ]


def max_finish_by_customer(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    output_rows: list[dict[str, str]] = []
    for customer_count in CUSTOMER_COUNTS:
        subset = [row for row in rows if int(row["customer_count"]) == customer_count]
        if len(subset) != len(CAPACITIES):
            raise RuntimeError(
                f"Expected {len(CAPACITIES)} capacity rows for {customer_count} customers, "
                f"found {len(subset)}"
            )

        before_row = max(subset, key=lambda row: float(row["pre_repair_latest_finish_time"]))
        after_row = max(subset, key=lambda row: float(row["post_repair_latest_finish_time"]))

        output_rows.append(
            {
                "customer_count": str(customer_count),
                "before_latest_finish_decimal_hours": f"{float(before_row['pre_repair_latest_finish_time']):.6f}",
                "before_latest_finish_label": before_row["pre_repair_latest_finish_time_label"],
                "before_capacity_with_max_finish": before_row["vehicle_capacity"],
                "after_latest_finish_decimal_hours": f"{float(after_row['post_repair_latest_finish_time']):.6f}",
                "after_latest_finish_label": after_row["post_repair_latest_finish_time_label"],
                "after_capacity_with_max_finish": after_row["vehicle_capacity"],
                "working_day_limit_decimal_hours": f"{WORKING_DAY_LIMIT:.1f}",
                "working_day_limit_label": decimal_hour_to_label(WORKING_DAY_LIMIT),
            }
        )
    return output_rows


def write_plot_data(rows: list[dict[str, str]]) -> None:
    fieldnames = [
        "customer_count",
        "before_latest_finish_decimal_hours",
        "before_latest_finish_label",
        "before_capacity_with_max_finish",
        "after_latest_finish_decimal_hours",
        "after_latest_finish_label",
        "after_capacity_with_max_finish",
        "working_day_limit_decimal_hours",
        "working_day_limit_label",
    ]
    with OUTPUT_DATA_CSV.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def make_plot(rows: list[dict[str, str]]) -> None:
    x_values = [int(row["customer_count"]) for row in rows]
    before_values = [float(row["before_latest_finish_decimal_hours"]) for row in rows]
    after_values = [float(row["after_latest_finish_decimal_hours"]) for row in rows]

    plt.rcParams.update(
        {
            "font.size": 10,
            "axes.labelsize": 11,
            "legend.fontsize": 9,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )

    fig, ax = plt.subplots(figsize=(6.4, 4.2), constrained_layout=True)

    ax.plot(
        x_values,
        before_values,
        marker="o",
        linestyle="-",
        linewidth=1.9,
        markersize=4.8,
        color="#1b1b1b",
        label="Before repair",
    )
    ax.plot(
        x_values,
        after_values,
        marker="s",
        linestyle="--",
        linewidth=1.9,
        markersize=4.8,
        color="#2f6f9f",
        label="After repair",
    )

    ax.axhline(WORKING_DAY_LIMIT, color="#7a7a7a", linestyle="--", linewidth=1.0)
    ax.text(
        104,
        WORKING_DAY_LIMIT + 0.12,
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
    ax.set_ylim(17.0, 24.1)
    ax.grid(True, axis="y", linestyle=":", linewidth=0.7, color="0.82")
    ax.grid(False, axis="x")
    ax.legend(
        loc="upper left",
        frameon=True,
        framealpha=0.92,
        edgecolor="0.85",
        facecolor="white",
        handlelength=2.4,
        borderpad=0.6,
        labelspacing=0.45,
    )

    fig.savefig(OUTPUT_PNG, dpi=300)
    fig.savefig(OUTPUT_PDF)
    plt.close(fig)


def write_caption() -> None:
    caption = """# Figure Caption: Same-Wave Split Repair Latest Finish Time

Latest depot-route completion time before and after same-wave split repair under the dispatch-wave timing model. For each customer size, the plotted value is the maximum latest finish time across capacities 15, 25, and 35. The dashed horizontal reference line marks the 18:00 working-day limit. The figure shows that same-wave split repair substantially reduces the latest completion time for the large dispatch-wave instances, restoring the 100- and 150-customer settings below the working-day limit while leaving the 200-customer setting slightly above the threshold.
"""
    OUTPUT_CAPTION.write_text(caption)


def main() -> None:
    repair_rows = read_repair_rows()
    expected = len(CUSTOMER_COUNTS) * len(CAPACITIES)
    if len(repair_rows) != expected:
        raise RuntimeError(f"Expected {expected} same-wave split-repair rows, found {len(repair_rows)}")

    plot_rows = max_finish_by_customer(repair_rows)
    write_plot_data(plot_rows)
    make_plot(plot_rows)
    write_caption()

    print(f"Wrote {OUTPUT_DATA_CSV}")
    print(f"Wrote {OUTPUT_PNG}")
    print(f"Wrote {OUTPUT_PDF}")
    print(f"Wrote {OUTPUT_CAPTION}")


if __name__ == "__main__":
    main()
