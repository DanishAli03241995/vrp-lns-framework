#!/usr/bin/env python3
"""
Generate Section 6.7 figure: 200-customer sensitivity latest finish time.

The figure compares the base dispatch-wave split-repair scenario against two
operational sensitivity scenarios for the 200-customer instances only.
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MultipleLocator


BASE_DIR = Path(__file__).resolve().parent
SPEED_CSV = BASE_DIR / "section_6_7_speed_sensitivity_comparison.csv"
WAVE14_CSV = BASE_DIR / "section_6_7_14wave_sensitivity_comparison.csv"
OUTPUT_DATA_CSV = BASE_DIR / "figure_6_7_200_customer_sensitivity_latest_finish_data.csv"
OUTPUT_PNG = BASE_DIR / "figure_6_7_200_customer_sensitivity_latest_finish.png"
OUTPUT_PDF = BASE_DIR / "figure_6_7_200_customer_sensitivity_latest_finish.pdf"
OUTPUT_CAPTION = BASE_DIR / "figure_6_7_200_customer_sensitivity_latest_finish_caption.md"

CUSTOMER_COUNT = 200
CAPACITIES = [15, 25, 35]
WORKING_DAY_LIMIT = 18.0


def decimal_hour_to_label(hour: float) -> str:
    total_minutes = int(round(hour * 60))
    hh, mm = divmod(total_minutes, 60)
    return f"{hh:02d}:{mm:02d}"


def time_axis_formatter(value: float, _position: int) -> str:
    return decimal_hour_to_label(value)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def rows_for_200(rows: list[dict[str, str]]) -> dict[int, dict[str, str]]:
    selected = {
        int(row["vehicle_capacity"]): row
        for row in rows
        if int(row["customer_count"]) == CUSTOMER_COUNT
        and int(row["vehicle_capacity"]) in CAPACITIES
    }
    missing = [capacity for capacity in CAPACITIES if capacity not in selected]
    if missing:
        raise RuntimeError(f"Missing 200-customer rows for capacities: {missing}")
    return selected


def build_plot_rows() -> list[dict[str, str]]:
    speed_rows = rows_for_200(read_csv(SPEED_CSV))
    wave14_rows = rows_for_200(read_csv(WAVE14_CSV))

    output_rows: list[dict[str, str]] = []
    for capacity in CAPACITIES:
        speed_row = speed_rows[capacity]
        wave14_row = wave14_rows[capacity]

        base_speed_value = float(speed_row["base_latest_finish_time"])
        base_wave_value = float(wave14_row["base_latest_finish_time"])
        if abs(base_speed_value - base_wave_value) > 1e-9:
            raise RuntimeError(
                f"Base latest finish mismatch for capacity {capacity}: "
                f"{base_speed_value} versus {base_wave_value}"
            )

        output_rows.append(
            {
                "customer_count": str(CUSTOMER_COUNT),
                "vehicle_capacity": str(capacity),
                "base_latest_finish_decimal_hours": f"{base_speed_value:.6f}",
                "base_latest_finish_label": speed_row["base_latest_finish_time_label"],
                "speed40_latest_finish_decimal_hours": f"{float(speed_row['speed40_latest_finish_time']):.6f}",
                "speed40_latest_finish_label": speed_row["speed40_latest_finish_time_label"],
                "wave14_latest_finish_decimal_hours": f"{float(wave14_row['wave14_latest_finish_time']):.6f}",
                "wave14_latest_finish_label": wave14_row["wave14_latest_finish_time_label"],
                "working_day_limit_decimal_hours": f"{WORKING_DAY_LIMIT:.1f}",
                "working_day_limit_label": decimal_hour_to_label(WORKING_DAY_LIMIT),
            }
        )
    return output_rows


def write_plot_data(rows: list[dict[str, str]]) -> None:
    fieldnames = [
        "customer_count",
        "vehicle_capacity",
        "base_latest_finish_decimal_hours",
        "base_latest_finish_label",
        "speed40_latest_finish_decimal_hours",
        "speed40_latest_finish_label",
        "wave14_latest_finish_decimal_hours",
        "wave14_latest_finish_label",
        "working_day_limit_decimal_hours",
        "working_day_limit_label",
    ]
    with OUTPUT_DATA_CSV.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def make_plot(rows: list[dict[str, str]]) -> None:
    x_values = [int(row["vehicle_capacity"]) for row in rows]
    base_values = [float(row["base_latest_finish_decimal_hours"]) for row in rows]
    speed40_values = [float(row["speed40_latest_finish_decimal_hours"]) for row in rows]
    wave14_values = [float(row["wave14_latest_finish_decimal_hours"]) for row in rows]

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
        base_values,
        marker="o",
        linestyle="-",
        linewidth=1.35,
        markersize=4.0,
        color="#1b1b1b",
        label="Base scenario",
    )
    ax.plot(
        x_values,
        speed40_values,
        marker="s",
        linestyle="--",
        linewidth=1.35,
        markersize=4.0,
        color="#2f6f9f",
        label="Speed 40",
    )
    ax.plot(
        x_values,
        wave14_values,
        marker="^",
        linestyle="-.",
        linewidth=1.35,
        markersize=4.0,
        color="#2b7a3d",
        label="+14:00 wave",
    )

    ax.axhline(WORKING_DAY_LIMIT, color="#7a7a7a", linestyle="--", linewidth=1.0)
    ax.text(
        15.4,
        WORKING_DAY_LIMIT + 0.03,
        "18:00 working-day limit",
        ha="left",
        va="bottom",
        fontsize=9,
        color="#6a6a6a",
    )

    ax.set_xlabel("Vehicle capacity")
    ax.set_ylabel("Latest depot-route finish time")
    ax.set_xticks(CAPACITIES)
    ax.yaxis.set_major_locator(MultipleLocator(0.25))
    ax.yaxis.set_major_formatter(FuncFormatter(time_axis_formatter))
    ax.set_ylim(17.78, 19.02)
    ax.grid(True, axis="y", linestyle=":", linewidth=0.7, color="0.82")
    ax.grid(False, axis="x")
    ax.legend(
        loc="center right",
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
    caption = """# Figure Caption: 200-Customer Operational Sensitivity

Latest depot-route completion time for the 200-customer dispatch-wave split-repair cases under the base scenario, the speed40 sensitivity, and the additional-14:00-wave sensitivity. The dashed horizontal reference line marks the 18:00 working-day limit. The base scenario remains above the working-day threshold for all three capacity settings, while both operational sensitivity scenarios move the latest depot-route finish time below 18:00.
"""
    OUTPUT_CAPTION.write_text(caption)


def main() -> None:
    plot_rows = build_plot_rows()
    write_plot_data(plot_rows)
    make_plot(plot_rows)
    write_caption()

    print(f"Wrote {OUTPUT_DATA_CSV}")
    print(f"Wrote {OUTPUT_PNG}")
    print(f"Wrote {OUTPUT_PDF}")
    print(f"Wrote {OUTPUT_CAPTION}")


if __name__ == "__main__":
    main()
