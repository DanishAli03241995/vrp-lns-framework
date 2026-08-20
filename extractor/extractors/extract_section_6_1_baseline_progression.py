#!/usr/bin/env python3
"""Extract Chapter 6.1 baseline progression and depot-location sanity tables."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


INSTANCE_RE = re.compile(r"^(?P<customers>\d+)c_cap(?P<capacity>\d+)_dem(?P<demand_low>\d+)-(?P<demand_high>\d+)$")

CUSTOMER_COUNTS = {20, 40, 60, 80}
VEHICLE_CAPACITIES = {15, 25, 35}

CORNER_RESULTS_DIR = Path("results/generated_depot_customer_initial_pipeline")
CENTRAL_RESULTS_DIR = Path("results/generated_depot_customer_initial_pipeline_central_depot")
OUTPUT_DIR = Path("extractor/section 6.1")

PROGRESSION_CSV = "section_6_1_baseline_progression_table.csv"
PROGRESSION_SUMMARY = "section_6_1_baseline_progression_summary.md"
DEPOT_LOCATION_CSV = "section_6_1_depot_location_sanity_table.csv"
DEPOT_LOCATION_SUMMARY = "section_6_1_depot_location_sanity_summary.md"

REQUIRED_RUN_FILES = [
    "config_used.json",
    "metrics.json",
    "route_baseline.txt",
    "route_two_opt.txt",
    "route_relocation.txt",
    "route_post_reloc_2opt.txt",
    "route_plot_baseline.png",
    "route_plot_two_opt.png",
    "route_plot_relocation.png",
    "route_plot_post_reloc_2opt.png",
]

REQUIRED_METRIC_KEYS = [
    "baseline_distance",
    "two_opt_distance",
    "relocation_distance",
    "post_reloc_2opt_distance",
    "trips",
    "post_reloc_2opt_avg_utilization",
    "post_reloc_2opt_min_utilization",
    "capacity_feasibility",
    "structural_validity",
    "all_customers_served",
]


@dataclass(frozen=True)
class InstanceRun:
    instance_name: str
    customer_count: int
    vehicle_capacity: int
    instance_dir: Path
    run_dir: Path | None
    metrics: dict[str, Any]
    warnings: list[str]


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def parse_instance_name(path: Path) -> tuple[int, int] | None:
    match = INSTANCE_RE.match(path.name)
    if not match:
        return None

    customer_count = int(match.group("customers"))
    vehicle_capacity = int(match.group("capacity"))
    if customer_count not in CUSTOMER_COUNTS or vehicle_capacity not in VEHICLE_CAPACITIES:
        return None

    return customer_count, vehicle_capacity


def latest_run(instance_dir: Path) -> Path | None:
    runs = sorted(p for p in instance_dir.iterdir() if p.is_dir() and p.name.startswith("run_"))
    return runs[-1] if runs else None


def read_json(path: Path) -> tuple[dict[str, Any], str | None]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            return {}, f"{path.name} is not a JSON object"
        return data, None
    except FileNotFoundError:
        return {}, f"missing {path.name}"
    except json.JSONDecodeError as exc:
        return {}, f"invalid JSON in {path.name}: {exc}"


def load_instance_runs(root: Path, relative_results_dir: Path) -> dict[tuple[int, int], InstanceRun]:
    results_dir = root / relative_results_dir
    runs: dict[tuple[int, int], InstanceRun] = {}

    if not results_dir.exists():
        return runs

    for instance_dir in sorted(p for p in results_dir.iterdir() if p.is_dir()):
        parsed = parse_instance_name(instance_dir)
        if not parsed:
            continue

        customer_count, vehicle_capacity = parsed
        warnings: list[str] = []
        run_dir = latest_run(instance_dir)
        metrics: dict[str, Any] = {}

        if run_dir is None:
            warnings.append("missing run folder")
        else:
            missing_files = [name for name in REQUIRED_RUN_FILES if not (run_dir / name).exists()]
            warnings.extend(f"missing {name}" for name in missing_files)

            metrics, json_warning = read_json(run_dir / "metrics.json")
            if json_warning:
                warnings.append(json_warning)

            missing_keys = [key for key in REQUIRED_METRIC_KEYS if key not in metrics]
            warnings.extend(f"missing metric {key}" for key in missing_keys)

        runs[(customer_count, vehicle_capacity)] = InstanceRun(
            instance_name=instance_dir.name,
            customer_count=customer_count,
            vehicle_capacity=vehicle_capacity,
            instance_dir=instance_dir,
            run_dir=run_dir,
            metrics=metrics,
            warnings=warnings,
        )

    return runs


def value(metrics: dict[str, Any], key: str) -> Any:
    return metrics.get(key, "")


def bool_value(metrics: dict[str, Any], key: str) -> Any:
    raw = metrics.get(key, "")
    if isinstance(raw, bool):
        return raw
    return raw


def pct_change(old: Any, new: Any) -> float | str:
    try:
        old_value = float(old)
        new_value = float(new)
    except (TypeError, ValueError):
        return ""
    if old_value == 0:
        return ""
    return ((new_value - old_value) / old_value) * 100


def pct_improvement(previous: Any, current: Any) -> float | str:
    change = pct_change(previous, current)
    if change == "":
        return ""
    return -change


def number_change(old: Any, new: Any) -> int | float | str:
    try:
        return new - old
    except TypeError:
        return ""


def final_route_count(metrics: dict[str, Any]) -> Any:
    if "trips" in metrics:
        return metrics["trips"]
    distances = metrics.get("post_reloc_2opt_trip_distances")
    if isinstance(distances, list):
        return len(distances)
    return ""


def notes(warnings: list[str], extra: list[str] | None = None) -> str:
    items = list(warnings)
    if extra:
        items.extend(extra)
    return "; ".join(items)


def expected_pairs() -> list[tuple[int, int]]:
    return [(customers, capacity) for customers in sorted(CUSTOMER_COUNTS) for capacity in sorted(VEHICLE_CAPACITIES)]


def build_progression_rows(corner_runs: dict[tuple[int, int], InstanceRun]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for pair in expected_pairs():
        run = corner_runs.get(pair)
        if run is None:
            customer_count, vehicle_capacity = pair
            rows.append(
                {
                    "customer_count": customer_count,
                    "vehicle_capacity": vehicle_capacity,
                    "instance_name": "",
                    "selected_run_timestamp": "",
                    "nn_distance": "",
                    "two_opt_distance": "",
                    "relocation_distance": "",
                    "post_relocation_two_opt_distance": "",
                    "improvement_nn_to_two_opt_pct": "",
                    "improvement_two_opt_to_relocation_pct": "",
                    "improvement_relocation_to_final_pct": "",
                    "improvement_nn_to_final_pct": "",
                    "final_n_routes": "",
                    "final_avg_utilisation": "",
                    "final_min_utilisation": "",
                    "capacity_feasible": "",
                    "customer_coverage_feasible": "",
                    "notes_or_warnings": "missing instance folder",
                }
            )
            continue

        metrics = run.metrics
        baseline = value(metrics, "baseline_distance")
        two_opt = value(metrics, "two_opt_distance")
        relocation = value(metrics, "relocation_distance")
        final = value(metrics, "post_reloc_2opt_distance")

        rows.append(
            {
                "customer_count": run.customer_count,
                "vehicle_capacity": run.vehicle_capacity,
                "instance_name": run.instance_name,
                "selected_run_timestamp": run.run_dir.name if run.run_dir else "",
                "nn_distance": baseline,
                "two_opt_distance": two_opt,
                "relocation_distance": relocation,
                "post_relocation_two_opt_distance": final,
                "improvement_nn_to_two_opt_pct": pct_improvement(baseline, two_opt),
                "improvement_two_opt_to_relocation_pct": pct_improvement(two_opt, relocation),
                "improvement_relocation_to_final_pct": pct_improvement(relocation, final),
                "improvement_nn_to_final_pct": pct_improvement(baseline, final),
                "final_n_routes": final_route_count(metrics),
                "final_avg_utilisation": value(metrics, "post_reloc_2opt_avg_utilization"),
                "final_min_utilisation": value(metrics, "post_reloc_2opt_min_utilization"),
                "capacity_feasible": bool_value(metrics, "capacity_feasibility"),
                "customer_coverage_feasible": bool_value(metrics, "all_customers_served"),
                "notes_or_warnings": notes(run.warnings),
            }
        )

    return rows


def build_depot_location_rows(
    corner_runs: dict[tuple[int, int], InstanceRun],
    central_runs: dict[tuple[int, int], InstanceRun],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for pair in expected_pairs():
        customer_count, vehicle_capacity = pair
        corner = corner_runs.get(pair)
        central = central_runs.get(pair)

        corner_metrics = corner.metrics if corner else {}
        central_metrics = central.metrics if central else {}
        corner_final = value(corner_metrics, "post_reloc_2opt_distance")
        central_final = value(central_metrics, "post_reloc_2opt_distance")
        corner_routes = final_route_count(corner_metrics)
        central_routes = final_route_count(central_metrics)
        corner_util = value(corner_metrics, "post_reloc_2opt_avg_utilization")
        central_util = value(central_metrics, "post_reloc_2opt_avg_utilization")

        extra_notes: list[str] = []
        if corner is None:
            extra_notes.append("missing corner instance")
        if central is None:
            extra_notes.append("missing central instance")

        combined_warnings: list[str] = []
        if corner:
            combined_warnings.extend(f"corner: {warning}" for warning in corner.warnings)
        if central:
            combined_warnings.extend(f"central: {warning}" for warning in central.warnings)

        rows.append(
            {
                "customer_count": customer_count,
                "vehicle_capacity": vehicle_capacity,
                "instance_name_corner": corner.instance_name if corner else "",
                "selected_run_corner": corner.run_dir.name if corner and corner.run_dir else "",
                "corner_final_distance": corner_final,
                "corner_final_routes": corner_routes,
                "corner_avg_utilisation": corner_util,
                "corner_capacity_feasible": bool_value(corner_metrics, "capacity_feasibility"),
                "corner_customer_coverage_feasible": bool_value(corner_metrics, "all_customers_served"),
                "instance_name_central": central.instance_name if central else "",
                "selected_run_central": central.run_dir.name if central and central.run_dir else "",
                "central_final_distance": central_final,
                "central_final_routes": central_routes,
                "central_avg_utilisation": central_util,
                "central_capacity_feasible": bool_value(central_metrics, "capacity_feasibility"),
                "central_customer_coverage_feasible": bool_value(central_metrics, "all_customers_served"),
                "distance_change_corner_to_central_pct": pct_change(corner_final, central_final),
                "route_count_change": number_change(corner_routes, central_routes),
                "utilisation_change": number_change(corner_util, central_util),
                "notes_or_warnings": notes(combined_warnings, extra_notes),
            }
        )

    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def warning_count(rows: list[dict[str, Any]]) -> int:
    return sum(1 for row in rows if row.get("notes_or_warnings"))


def truthy_count(rows: list[dict[str, Any]], key: str) -> int:
    return sum(1 for row in rows if row.get(key) is True)


def write_progression_summary(path: Path, rows: list[dict[str, Any]], source_dir: Path) -> None:
    lines = [
        "# Section 6.1.1 Baseline Progression Extraction Summary",
        "",
        "## Source",
        "",
        f"- Source folder: `{source_dir}`",
        f"- Rows expected: {len(expected_pairs())}",
        f"- Rows written: {len(rows)}",
        f"- Rows with warnings: {warning_count(rows)}",
        f"- Capacity-feasible rows: {truthy_count(rows, 'capacity_feasible')}",
        f"- Customer-coverage-feasible rows: {truthy_count(rows, 'customer_coverage_feasible')}",
        "",
        "## Output",
        "",
        f"- CSV file: `{PROGRESSION_CSV}`",
        "",
        "## Notes",
        "",
        "- Final distance is extracted from `post_reloc_2opt_distance`.",
        "- Final route count is extracted from `trips`, with route-list length available as a possible cross-check.",
        "- Improvement percentages are recomputed from stage distances.",
        "- Supplier cases, clustering, LNS, and timing results are not included.",
        "",
    ]

    warning_rows = [row for row in rows if row.get("notes_or_warnings")]
    if warning_rows:
        lines.extend(["## Warnings", ""])
        for row in warning_rows:
            lines.append(
                f"- `{row.get('instance_name') or row.get('customer_count')}`: {row.get('notes_or_warnings')}"
            )
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def write_depot_location_summary(path: Path, rows: list[dict[str, Any]], corner_dir: Path, central_dir: Path) -> None:
    lines = [
        "# Section 6.1.2 Depot-Location Sanity Check Extraction Summary",
        "",
        "## Sources",
        "",
        f"- Corner-depot folder: `{corner_dir}`",
        f"- Central-depot folder: `{central_dir}`",
        f"- Rows expected: {len(expected_pairs())}",
        f"- Rows written: {len(rows)}",
        f"- Rows with warnings: {warning_count(rows)}",
        f"- Corner capacity-feasible rows: {truthy_count(rows, 'corner_capacity_feasible')}",
        f"- Central capacity-feasible rows: {truthy_count(rows, 'central_capacity_feasible')}",
        f"- Corner customer-coverage-feasible rows: {truthy_count(rows, 'corner_customer_coverage_feasible')}",
        f"- Central customer-coverage-feasible rows: {truthy_count(rows, 'central_customer_coverage_feasible')}",
        "",
        "## Output",
        "",
        f"- CSV file: `{DEPOT_LOCATION_CSV}`",
        "",
        "## Notes",
        "",
        "- This is a depot-location sanity check, not depot-location optimisation.",
        "- Final distance is extracted from `post_reloc_2opt_distance` for both depot settings.",
        "- Route count is extracted from `trips` for both depot settings.",
        "- Average utilisation is extracted from `post_reloc_2opt_avg_utilization` for both depot settings.",
        "- Supplier cases, clustering, LNS, and timing results are not included.",
        "",
    ]

    warning_rows = [row for row in rows if row.get("notes_or_warnings")]
    if warning_rows:
        lines.extend(["## Warnings", ""])
        for row in warning_rows:
            label = f"{row.get('customer_count')}c_cap{row.get('vehicle_capacity')}"
            lines.append(f"- `{label}`: {row.get('notes_or_warnings')}")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    root = project_root()
    output_dir = root / OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    corner_runs = load_instance_runs(root, CORNER_RESULTS_DIR)
    central_runs = load_instance_runs(root, CENTRAL_RESULTS_DIR)

    progression_rows = build_progression_rows(corner_runs)
    depot_location_rows = build_depot_location_rows(corner_runs, central_runs)

    write_csv(output_dir / PROGRESSION_CSV, progression_rows)
    write_csv(output_dir / DEPOT_LOCATION_CSV, depot_location_rows)

    write_progression_summary(output_dir / PROGRESSION_SUMMARY, progression_rows, CORNER_RESULTS_DIR)
    write_depot_location_summary(
        output_dir / DEPOT_LOCATION_SUMMARY,
        depot_location_rows,
        CORNER_RESULTS_DIR,
        CENTRAL_RESULTS_DIR,
    )

    print(f"Wrote {output_dir / PROGRESSION_CSV}")
    print(f"Wrote {output_dir / PROGRESSION_SUMMARY}")
    print(f"Wrote {output_dir / DEPOT_LOCATION_CSV}")
    print(f"Wrote {output_dir / DEPOT_LOCATION_SUMMARY}")


if __name__ == "__main__":
    main()
