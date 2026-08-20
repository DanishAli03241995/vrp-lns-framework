from pathlib import Path
import csv
import os

SCRIPT_DIR = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", str(SCRIPT_DIR / ".matplotlib_cache"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


BASE_DIR = SCRIPT_DIR
INPUT_CSV = BASE_DIR / "section_6_1_baseline_progression_table.csv"
OUTPUT_PNG = BASE_DIR / "section_6_1_average_optimisation_progression_indexed.png"
OUTPUT_PDF = BASE_DIR / "section_6_1_average_optimisation_progression_indexed.pdf"


STAGES = [
    ("NN", "nn_distance"),
    ("2-opt", "two_opt_distance"),
    ("1-0 relocation", "relocation_distance"),
    ("Post-relocation 2-opt", "post_relocation_two_opt_distance"),
]


def read_rows(csv_path):
    with csv_path.open(newline="") as f:
        return list(csv.DictReader(f))


def average(values):
    return sum(values) / len(values)


def compute_indexed_progression(rows):
    if not rows:
        raise ValueError(f"No rows found in {INPUT_CSV}")

    average_distances = []
    for _, column in STAGES:
        values = [float(row[column]) for row in rows]
        average_distances.append(average(values))

    nn_average = average_distances[0]
    indexed_values = [(distance / nn_average) * 100 for distance in average_distances]
    return average_distances, indexed_values


def make_plot(indexed_values, average_distances):
    stage_labels = [label for label, _ in STAGES]
    x_values = list(range(len(stage_labels)))

    plt.rcParams.update(
        {
            "figure.dpi": 150,
            "savefig.dpi": 300,
            "font.family": "serif",
            "font.size": 10,
            "axes.labelsize": 10,
            "axes.titlesize": 11,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.fontsize": 9,
        }
    )

    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    ax.plot(
        x_values,
        indexed_values,
        marker="o",
        linewidth=2.0,
        markersize=5.5,
        color="#1f77b4",
    )

    for x, indexed, distance in zip(x_values, indexed_values, average_distances):
        ax.annotate(
            f"{indexed:.1f}",
            xy=(x, indexed),
            xytext=(0, 7),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8.5,
        )

    ax.set_xticks(x_values)
    ax.set_xticklabels(stage_labels)
    ax.set_ylabel("Average distance index (NN = 100)")
    ax.set_title("Average Optimisation Progression Across 12 Baseline Instances")
    ax.grid(axis="y", linestyle="--", linewidth=0.6, alpha=0.45)
    ax.set_ylim(min(indexed_values) - 4, 103)

    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)

    note = "Distances averaged over 20, 40, 60, and 80 customers with capacities 15, 25, and 35."
    fig.text(0.5, 0.01, note, ha="center", va="bottom", fontsize=8)
    fig.tight_layout(rect=(0, 0.05, 1, 1))

    fig.savefig(OUTPUT_PNG, bbox_inches="tight")
    fig.savefig(OUTPUT_PDF, bbox_inches="tight")
    plt.close(fig)


def main():
    rows = read_rows(INPUT_CSV)
    average_distances, indexed_values = compute_indexed_progression(rows)
    make_plot(indexed_values, average_distances)

    print(f"Rows used: {len(rows)}")
    for (label, _), distance, indexed in zip(STAGES, average_distances, indexed_values):
        print(f"{label}: average_distance={distance:.4f}, indexed={indexed:.2f}")
    print(f"Saved PNG: {OUTPUT_PNG}")
    print(f"Saved PDF: {OUTPUT_PDF}")


if __name__ == "__main__":
    main()
