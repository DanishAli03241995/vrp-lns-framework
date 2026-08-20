#!/usr/bin/env python3
"""Extract Chapter 6.2 depot-customer clustering baseline comparison."""

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

OUTPUT_DIR = Path("extractor/section 6.2")
OUTPUT_CSV = "section_6_2_clustering_baseline_table.csv"
OUTPUT_SUMMARY = "section_6_2_clustering_baseline_summary.md"

RESULT_FOLDERS = [
    {
        "relative_path": Path("results/generated_depot_customer_initial_pipeline"),
        "depot_setting": "corner_depot",
        "clustering_strategy": "no_clustering",
        "requires_clusters": False,
    },
    {
        "relative_path": Path("results/generated_depot_customer_initial_pipeline_central_depot"),
        "depot_setting": "central_depot",
        "clustering_strategy": "no_clustering",
        "requires_clusters": False,
    },
    {
        "relative_path": Path("results/generated_depot_customer_sweep_initial_pipeline"),
        "depot_setting": "corner_depot",
        "clustering_strategy": "sweep",
        "requires_clusters": True,
    },
    {
        "relative_path": Path("results/generated_depot_customer_sweep_initial_pipeline_central_depot"),
        "depot_setting": "central_depot",
        "clustering_strategy": "sweep",
        "requires_clusters": True,
    },
    {
        "relative_path": Path("results/generated_depot_customer_kmeans_initial_pipeline"),
        "depot_setting": "corner_depot",
        "clustering_strategy": "kmeans",
        "requires_clusters": True,
    },
    {
        "relative_path": Path("results/generated_depot_customer_kmeans_initial_pipeline_central_depot"),
        "depot_setting": "central_depot",
        "clustering_strategy": "kmeans",
        "requires_clusters": True,
    },
]

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
    "post_reloc_2opt_distance",
    "trips",
    "post_reloc_2opt_avg_utilization",
    "post_reloc_2opt_min_utilization",
    "post_reloc_2opt_max_utilization",
    "capacity_feasibility",
    "all_customers_served",
    "structural_validity",
]


@dataclass(frozen=True)
class FolderSpec:
    relative_path: Path
    depot_setting: str
    clustering_strategy: str
    requires_clusters: bool


@dataclass(frozen=True)
class ExtractedRun:
    customer_count: int
    vehicle_capacity: int
    instance_name: str
    depot_setting: str
    clustering_strategy: str
    selected_run_timestamp: str
    metrics: dict[str, Any]
    clusters: dict[str, Any]
    warnings: list[str]


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def expected_pairs() -> list[tuple[int, int]]:
    return [(customers, capacity) for customers in sorted(CUSTOMER_COUNTS) for capacity in sorted(VEHICLE_CAPACITIES)]


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


def cluster_list(clusters_json: dict[str, Any]) -> list[Any]:
    clusters = clusters_json.get("clusters")
    return clusters if isinstance(clusters, list) else []


def cluster_check(clusters_json: dict[str, Any]) -> dict[str, Any]:
    check = clusters_json.get("cluster_check")
    return check if isinstance(check, dict) else {}


def cluster_count(clusters_json: dict[str, Any]) -> Any:
    check = cluster_check(clusters_json)
    if "num_clusters" in check:
        return check["num_clusters"]
    clusters = cluster_list(clusters_json)
    if clusters:
        return len(clusters)
    return ""


def cluster_sizes(clusters_json: dict[str, Any]) -> str:
    clusters = cluster_list(clusters_json)
    if not clusters:
        return ""
    sizes = [len(cluster) if isinstance(cluster, list) else "" for cluster in clusters]
    return "|".join(str(size) for size in sizes)


def cluster_warnings(clusters_json: dict[str, Any], customer_count: int) -> list[str]:
    warnings: list[str] = []
    check = cluster_check(clusters_json)

    missing_customers = check.get("missing_customers")
    if isinstance(missing_customers, list) and missing_customers:
        warnings.append(f"cluster_check missing_customers={missing_customers}")

    expected = check.get("num_expected_customers")
    if isinstance(expected, int) and expected != customer_count:
        warnings.append(f"cluster_check num_expected_customers={expected}, expected {customer_count}")

    clustered = check.get("num_clustered_customers")
    if isinstance(clustered, int) and clustered != customer_count:
        warnings.append(f"cluster_check num_clustered_customers={clustered}, expected {customer_count}")

    return warnings


def notes(items: list[str]) -> str:
    return "; ".join(items)


def load_folder(root: Path, spec: FolderSpec) -> list[ExtractedRun]:
    folder = root / spec.relative_path
    runs: list[ExtractedRun] = []

    if not folder.exists():
        for customer_count, vehicle_capacity in expected_pairs():
            runs.append(
                ExtractedRun(
                    customer_count=customer_count,
                    vehicle_capacity=vehicle_capacity,
                    instance_name="",
                    depot_setting=spec.depot_setting,
                    clustering_strategy=spec.clustering_strategy,
                    selected_run_timestamp="",
                    metrics={},
                    clusters={},
                    warnings=[f"missing result folder {spec.relative_path}"],
                )
            )
        return runs

    by_pair: dict[tuple[int, int], Path] = {}
    for instance_dir in sorted(p for p in folder.iterdir() if p.is_dir()):
        parsed = parse_instance_name(instance_dir)
        if parsed:
            by_pair[parsed] = instance_dir

    for customer_count, vehicle_capacity in expected_pairs():
        instance_dir = by_pair.get((customer_count, vehicle_capacity))
        warnings: list[str] = []
        metrics: dict[str, Any] = {}
        clusters_json: dict[str, Any] = {}
        run_dir: Path | None = None

        if instance_dir is None:
            warnings.append("missing instance folder")
            instance_name = ""
        else:
            instance_name = instance_dir.name
            run_dir = latest_run(instance_dir)
            if run_dir is None:
                warnings.append("missing run folder")
            else:
                missing_files = [name for name in REQUIRED_RUN_FILES if not (run_dir / name).exists()]
                warnings.extend(f"missing {name}" for name in missing_files)

                metrics, metric_warning = read_json(run_dir / "metrics.json")
                if metric_warning:
                    warnings.append(metric_warning)

                missing_keys = [key for key in REQUIRED_METRIC_KEYS if key not in metrics]
                warnings.extend(f"missing metric {key}" for key in missing_keys)

                if spec.requires_clusters:
                    clusters_json, cluster_warning = read_json(run_dir / "clusters.json")
                    if cluster_warning:
                        warnings.append(cluster_warning)
                    else:
                        warnings.extend(cluster_warnings(clusters_json, customer_count))

        runs.append(
            ExtractedRun(
                customer_count=customer_count,
                vehicle_capacity=vehicle_capacity,
                instance_name=instance_name,
                depot_setting=spec.depot_setting,
                clustering_strategy=spec.clustering_strategy,
                selected_run_timestamp=run_dir.name if run_dir else "",
                metrics=metrics,
                clusters=clusters_json,
                warnings=warnings,
            )
        )

    return runs


def comparison_reference(rows: list[ExtractedRun]) -> dict[tuple[int, int, str], ExtractedRun]:
    refs: dict[tuple[int, int, str], ExtractedRun] = {}
    for row in rows:
        if row.clustering_strategy == "no_clustering":
            refs[(row.customer_count, row.vehicle_capacity, row.depot_setting)] = row
    return refs


def build_csv_rows(runs: list[ExtractedRun]) -> list[dict[str, Any]]:
    refs = comparison_reference(runs)
    csv_rows: list[dict[str, Any]] = []

    for run in sorted(runs, key=lambda item: (item.depot_setting, item.customer_count, item.vehicle_capacity, item.clustering_strategy)):
        metrics = run.metrics
        final_distance = value(metrics, "post_reloc_2opt_distance")
        n_routes = final_route_count(metrics)
        avg_utilisation = value(metrics, "post_reloc_2opt_avg_utilization")
        reference = refs.get((run.customer_count, run.vehicle_capacity, run.depot_setting))

        warnings = list(run.warnings)
        if reference is None:
            warnings.append("missing no_clustering reference for matched comparison")

        if run.clustering_strategy == "no_clustering":
            distance_change = ""
            route_change = ""
            utilisation_change = ""
        elif reference is None:
            distance_change = ""
            route_change = ""
            utilisation_change = ""
        else:
            reference_metrics = reference.metrics
            distance_change = pct_change(value(reference_metrics, "post_reloc_2opt_distance"), final_distance)
            route_change = number_change(final_route_count(reference_metrics), n_routes)
            utilisation_change = number_change(value(reference_metrics, "post_reloc_2opt_avg_utilization"), avg_utilisation)

        csv_rows.append(
            {
                "customer_count": run.customer_count,
                "vehicle_capacity": run.vehicle_capacity,
                "instance_name": run.instance_name,
                "depot_setting": run.depot_setting,
                "clustering_strategy": run.clustering_strategy,
                "selected_run_timestamp": run.selected_run_timestamp,
                "final_distance": final_distance,
                "n_routes": n_routes,
                "avg_utilisation": avg_utilisation,
                "min_utilisation": value(metrics, "post_reloc_2opt_min_utilization"),
                "max_utilisation": value(metrics, "post_reloc_2opt_max_utilization"),
                "cluster_count": "" if run.clustering_strategy == "no_clustering" else cluster_count(run.clusters),
                "cluster_sizes": "" if run.clustering_strategy == "no_clustering" else cluster_sizes(run.clusters),
                "capacity_feasible": bool_value(metrics, "capacity_feasibility"),
                "customer_coverage_feasible": bool_value(metrics, "all_customers_served"),
                "structural_validity": bool_value(metrics, "structural_validity"),
                "distance_change_vs_no_clustering_pct": distance_change,
                "route_change_vs_no_clustering": route_change,
                "utilisation_change_vs_no_clustering": utilisation_change,
                "notes_or_warnings": notes(warnings),
            }
        )

    return csv_rows


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


def count_by(rows: list[dict[str, Any]], key: str) -> dict[Any, int]:
    counts: dict[Any, int] = {}
    for row in rows:
        value_ = row.get(key)
        counts[value_] = counts.get(value_, 0) + 1
    return counts


def truthy_count(rows: list[dict[str, Any]], key: str) -> int:
    return sum(1 for row in rows if row.get(key) is True)


def best_strategy_rows(rows: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    grouped: dict[tuple[Any, Any, Any], list[dict[str, Any]]] = {}
    for row in rows:
        key = (row["depot_setting"], row["customer_count"], row["vehicle_capacity"])
        grouped.setdefault(key, []).append(row)

    for key in sorted(grouped):
        comparable = []
        for row in grouped[key]:
            try:
                distance = float(row["final_distance"])
            except (TypeError, ValueError):
                continue
            comparable.append((distance, row["clustering_strategy"]))
        if not comparable:
            continue
        best_distance, best_strategy = min(comparable)
        depot_setting, customer_count, vehicle_capacity = key
        lines.append(
            f"- `{depot_setting} {customer_count}c_cap{vehicle_capacity}`: "
            f"`{best_strategy}` with final distance {best_distance:.4f}"
        )
    return lines


def write_summary(path: Path, rows: list[dict[str, Any]]) -> None:
    strategy_counts = count_by(rows, "clustering_strategy")
    depot_counts = count_by(rows, "depot_setting")
    expected_rows = len(RESULT_FOLDERS) * len(expected_pairs())

    lines = [
        "# Section 6.2 Clustering Baseline Extraction Summary",
        "",
        "## Sources",
        "",
    ]
    for spec in RESULT_FOLDERS:
        lines.append(f"- `{spec['relative_path']}`")

    lines.extend(
        [
            "",
            "## Row Counts",
            "",
            f"- Rows expected: {expected_rows}",
            f"- Rows written: {len(rows)}",
            f"- Rows with warnings: {warning_count(rows)}",
            "",
            "## Rows by Depot Setting",
            "",
        ]
    )
    for key, count in sorted(depot_counts.items()):
        lines.append(f"- `{key}`: {count}")

    lines.extend(["", "## Rows by Clustering Strategy", ""])
    for key, count in sorted(strategy_counts.items()):
        lines.append(f"- `{key}`: {count}")

    lines.extend(
        [
            "",
            "## Feasibility Checks",
            "",
            f"- Capacity-feasible rows: {truthy_count(rows, 'capacity_feasible')}",
            f"- Customer-coverage-feasible rows: {truthy_count(rows, 'customer_coverage_feasible')}",
            f"- Structurally valid rows: {truthy_count(rows, 'structural_validity')}",
            "",
            "## Best Final Distance by Matched Group",
            "",
        ]
    )
    best_lines = best_strategy_rows(rows)
    lines.extend(best_lines if best_lines else ["- No comparable rows available."])

    warning_rows = [row for row in rows if row.get("notes_or_warnings")]
    lines.extend(["", "## Warnings", ""])
    if warning_rows:
        for row in warning_rows:
            label = (
                f"{row.get('depot_setting')} "
                f"{row.get('clustering_strategy')} "
                f"{row.get('customer_count')}c_cap{row.get('vehicle_capacity')}"
            )
            lines.append(f"- `{label}`: {row.get('notes_or_warnings')}")
    else:
        lines.append("- No warnings recorded.")

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Final distance is extracted from `post_reloc_2opt_distance`.",
            "- Route count is extracted from `trips`, with route-list length available as a possible cross-check.",
            "- Cluster metadata is extracted from `clusters.json` for Sweep and KMeans only.",
            "- Distance changes are computed against the no-clustering run within the same depot setting, customer count, and vehicle capacity.",
            "- Supplier cases, LNS results, timing results, and broad Chapter 6 extraction are not included.",
            "",
        ]
    )

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    root = project_root()
    output_dir = root / OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    runs: list[ExtractedRun] = []
    for raw_spec in RESULT_FOLDERS:
        spec = FolderSpec(**raw_spec)
        runs.extend(load_folder(root, spec))

    csv_rows = build_csv_rows(runs)
    write_csv(output_dir / OUTPUT_CSV, csv_rows)
    write_summary(output_dir / OUTPUT_SUMMARY, csv_rows)

    print(f"Wrote {output_dir / OUTPUT_CSV}")
    print(f"Wrote {output_dir / OUTPUT_SUMMARY}")


if __name__ == "__main__":
    main()
