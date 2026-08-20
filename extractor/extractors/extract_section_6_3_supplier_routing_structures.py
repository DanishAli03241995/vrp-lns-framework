#!/usr/bin/env python3
"""Extract Chapter 6.3 supplier-based routing-structure comparison."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


INSTANCE_RE = re.compile(r"^(?P<customers>\d+)c_cap(?P<capacity>\d+)$")

MAIN_CUSTOMER_COUNTS = {20, 40, 60, 80}
EXTRA_HYBRID_CUSTOMER_COUNTS = {100, 150, 200}
VEHICLE_CAPACITIES = {15, 25, 35}

OUTPUT_DIR = Path("extractor/section 6.3")
OUTPUT_CSV = "section_6_3_supplier_routing_structures_table.csv"
OUTPUT_SUMMARY = "section_6_3_supplier_routing_structures_summary.md"

RESULT_FOLDERS = [
    {
        "relative_path": Path("results/supplier_depot_customer_baseline_sweep_v1"),
        "routing_case": "case_1_supplier_depot_customer",
        "clustering_strategy": "sweep",
        "depot_setting_or_geometry": "central_depot_supplier_network",
        "requires_clusters": True,
    },
    {
        "relative_path": Path("results/supplier_depot_customer_baseline_kmeans_v1"),
        "routing_case": "case_1_supplier_depot_customer",
        "clustering_strategy": "kmeans",
        "depot_setting_or_geometry": "central_depot_supplier_network",
        "requires_clusters": True,
    },
    {
        "relative_path": Path("results/supplier_customer_only_baseline_sweep_v1"),
        "routing_case": "case_2_supplier_customer_direct",
        "clustering_strategy": "sweep",
        "depot_setting_or_geometry": "direct_supplier_customer_no_depot_route",
        "requires_clusters": True,
    },
    {
        "relative_path": Path("results/supplier_customer_only_baseline_kmeans_v1"),
        "routing_case": "case_2_supplier_customer_direct",
        "clustering_strategy": "kmeans",
        "depot_setting_or_geometry": "direct_supplier_customer_no_depot_route",
        "requires_clusters": True,
    },
    {
        "relative_path": Path("results/supplier_customer_only_no_cluster_v1"),
        "routing_case": "case_2_supplier_customer_direct",
        "clustering_strategy": "no_clustering",
        "depot_setting_or_geometry": "direct_supplier_customer_no_depot_route",
        "requires_clusters": False,
    },
    {
        "relative_path": Path("results/hybrid_supplier_customer_sweep_v1"),
        "routing_case": "case_3_hybrid",
        "clustering_strategy": "sweep",
        "depot_setting_or_geometry": "central_depot_supplier_network",
        "requires_clusters": True,
    },
    {
        "relative_path": Path("results/hybrid_supplier_customer_kmeans_v1"),
        "routing_case": "case_3_hybrid",
        "clustering_strategy": "kmeans",
        "depot_setting_or_geometry": "central_depot_supplier_network",
        "requires_clusters": True,
    },
    {
        "relative_path": Path("results/hybrid_supplier_customer_no_cluster_v1"),
        "routing_case": "case_3_hybrid",
        "clustering_strategy": "no_clustering",
        "depot_setting_or_geometry": "central_depot_supplier_network",
        "requires_clusters": False,
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
    "post_reloc_2opt_total_system_distance",
    "total_first_echelon_distance",
    "trips",
    "post_reloc_2opt_avg_utilization",
    "post_reloc_2opt_min_utilization",
    "post_reloc_2opt_max_utilization",
    "capacity_feasibility",
    "all_customers_served",
    "structural_validity",
    "supply_feasibility",
]


@dataclass(frozen=True)
class FolderSpec:
    relative_path: Path
    routing_case: str
    clustering_strategy: str
    depot_setting_or_geometry: str
    requires_clusters: bool


@dataclass(frozen=True)
class ExtractedRun:
    customer_count: int
    vehicle_capacity: int
    instance_name: str
    routing_case: str
    clustering_strategy: str
    depot_setting_or_geometry: str
    selected_run_timestamp: str
    metrics: dict[str, Any]
    clusters: dict[str, Any]
    warnings: list[str]


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def expected_pairs() -> list[tuple[int, int]]:
    return [(customers, capacity) for customers in sorted(MAIN_CUSTOMER_COUNTS) for capacity in sorted(VEHICLE_CAPACITIES)]


def parse_instance_name(path: Path) -> tuple[int, int] | None:
    match = INSTANCE_RE.match(path.name)
    if not match:
        return None
    customer_count = int(match.group("customers"))
    vehicle_capacity = int(match.group("capacity"))
    if vehicle_capacity not in VEHICLE_CAPACITIES:
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


def final_route_count(metrics: dict[str, Any]) -> Any:
    if "trips" in metrics:
        return metrics["trips"]
    distances = metrics.get("post_reloc_2opt_trip_distances")
    if isinstance(distances, list):
        return len(distances)
    return ""


def as_float(raw: Any) -> float | None:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def cluster_list(clusters_json: dict[str, Any]) -> list[Any]:
    clusters = clusters_json.get("clusters")
    return clusters if isinstance(clusters, list) else []


def cluster_count(clusters_json: dict[str, Any]) -> Any:
    check = clusters_json.get("cluster_check")
    if isinstance(check, dict) and "num_clusters" in check:
        return check["num_clusters"]
    clusters = cluster_list(clusters_json)
    return len(clusters) if clusters else ""


def cluster_sizes(clusters_json: dict[str, Any]) -> str:
    clusters = cluster_list(clusters_json)
    if not clusters:
        return ""
    return "|".join(str(len(cluster)) if isinstance(cluster, list) else "" for cluster in clusters)


def cluster_warnings(clusters_json: dict[str, Any], customer_count: int) -> list[str]:
    warnings: list[str] = []
    check = clusters_json.get("cluster_check")
    if not isinstance(check, dict):
        return warnings

    missing_customers = check.get("missing_customers")
    if isinstance(missing_customers, list) and missing_customers:
        warnings.append(f"cluster_check missing_customers={missing_customers}")

    expected = check.get("num_expected_customers")
    clustered = check.get("num_clustered_customers")
    if isinstance(expected, int) and expected != customer_count:
        warnings.append(f"cluster_check num_expected_customers={expected}, expected {customer_count}")
    if isinstance(clustered, int) and clustered != customer_count:
        warnings.append(f"cluster_check num_clustered_customers={clustered}, expected {customer_count}")

    return warnings


def notes(items: list[str]) -> str:
    return "; ".join(items)


def has_positive_depot_customers(metrics: dict[str, Any]) -> bool:
    raw = metrics.get("n_depot_customers")
    return isinstance(raw, int) and raw > 0


def replenishment_distance(metrics: dict[str, Any]) -> Any:
    if "supplier_depot_replenishment_distance" in metrics:
        return metrics["supplier_depot_replenishment_distance"]
    return metrics.get("total_first_echelon_distance", "")


def direct_customer_count(metrics: dict[str, Any], routing_case: str) -> Any:
    if routing_case == "case_3_hybrid":
        return metrics.get("n_supplier_direct_customers", "")
    if routing_case == "case_2_supplier_customer_direct":
        return metrics.get("n_customers", "")
    return ""


def depot_customer_count(metrics: dict[str, Any], routing_case: str, customer_count: int) -> Any:
    if routing_case == "case_1_supplier_depot_customer":
        return customer_count
    if routing_case == "case_3_hybrid":
        return metrics.get("n_depot_customers", "")
    return ""


def supplier_direct_distance(metrics: dict[str, Any], routing_case: str) -> Any:
    if routing_case == "case_2_supplier_customer_direct":
        return metrics.get("post_reloc_2opt_distance", "")
    return metrics.get("supplier_direct_distance", "")


def depot_customer_distance(metrics: dict[str, Any], routing_case: str) -> Any:
    if routing_case in {"case_1_supplier_depot_customer", "case_3_hybrid"}:
        return metrics.get("post_reloc_2opt_distance", "")
    return ""


def total_system_check(metrics: dict[str, Any]) -> str:
    customer_delivery = as_float(metrics.get("post_reloc_2opt_distance"))
    first_echelon = as_float(metrics.get("total_first_echelon_distance"))
    total_system = as_float(metrics.get("post_reloc_2opt_total_system_distance"))
    if customer_delivery is None or first_echelon is None or total_system is None:
        return "needs_check"
    return "ok" if abs((customer_delivery + first_echelon) - total_system) < 1e-6 else "mismatch"


def load_folder(root: Path, spec: FolderSpec) -> tuple[list[ExtractedRun], list[str]]:
    folder = root / spec.relative_path
    runs: list[ExtractedRun] = []
    extra_instances: list[str] = []

    if not folder.exists():
        for customer_count, vehicle_capacity in expected_pairs():
            runs.append(
                ExtractedRun(
                    customer_count=customer_count,
                    vehicle_capacity=vehicle_capacity,
                    instance_name="",
                    routing_case=spec.routing_case,
                    clustering_strategy=spec.clustering_strategy,
                    depot_setting_or_geometry=spec.depot_setting_or_geometry,
                    selected_run_timestamp="",
                    metrics={},
                    clusters={},
                    warnings=[f"missing result folder {spec.relative_path}"],
                )
            )
        return runs, extra_instances

    by_pair: dict[tuple[int, int], Path] = {}
    for instance_dir in sorted(p for p in folder.iterdir() if p.is_dir()):
        parsed = parse_instance_name(instance_dir)
        if not parsed:
            continue
        customer_count, vehicle_capacity = parsed
        if customer_count in EXTRA_HYBRID_CUSTOMER_COUNTS and spec.routing_case == "case_3_hybrid":
            extra_instances.append(instance_dir.name)
        if customer_count in MAIN_CUSTOMER_COUNTS and vehicle_capacity in VEHICLE_CAPACITIES:
            by_pair[(customer_count, vehicle_capacity)] = instance_dir

    for customer_count, vehicle_capacity in expected_pairs():
        instance_dir = by_pair.get((customer_count, vehicle_capacity))
        warnings: list[str] = []
        metrics: dict[str, Any] = {}
        clusters_json: dict[str, Any] = {}
        run_dir: Path | None = None

        if instance_dir is None:
            instance_name = ""
            warnings.append("missing instance folder")
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

                if spec.routing_case == "case_3_hybrid" and has_positive_depot_customers(metrics):
                    first_echelon = as_float(metrics.get("total_first_echelon_distance"))
                    if first_echelon is None or first_echelon == 0:
                        warnings.append(
                            "hybrid depot-bound customers present but supplier-depot replenishment distance is zero; "
                            "check whether this run predates replenishment-distance correction"
                        )
                    if "supplier_depot_replenishment_metrics" not in metrics:
                        warnings.append("missing supplier_depot_replenishment_metrics")
                    if total_system_check(metrics) != "ok":
                        warnings.append("hybrid total system distance does not match customer-delivery plus first-echelon distance")

        runs.append(
            ExtractedRun(
                customer_count=customer_count,
                vehicle_capacity=vehicle_capacity,
                instance_name=instance_name,
                routing_case=spec.routing_case,
                clustering_strategy=spec.clustering_strategy,
                depot_setting_or_geometry=spec.depot_setting_or_geometry,
                selected_run_timestamp=run_dir.name if run_dir else "",
                metrics=metrics,
                clusters=clusters_json,
                warnings=warnings,
            )
        )

    return runs, extra_instances


def not_available_case1_no_cluster_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for customer_count, vehicle_capacity in expected_pairs():
        rows.append(
            {
                "customer_count": customer_count,
                "vehicle_capacity": vehicle_capacity,
                "instance_name": f"{customer_count}c_cap{vehicle_capacity}",
                "routing_case": "case_1_supplier_depot_customer",
                "clustering_strategy": "not_available",
                "selected_run_timestamp": "",
                "depot_setting_or_geometry": "central_depot_supplier_network",
                "customer_delivery_distance": "",
                "supplier_depot_replenishment_distance": "",
                "supplier_direct_distance": "",
                "depot_customer_distance": "",
                "total_system_distance": "",
                "reported_final_distance": "",
                "direct_customer_count": "",
                "depot_customer_count": customer_count,
                "n_routes": "",
                "avg_utilisation": "",
                "min_utilisation": "",
                "max_utilisation": "",
                "capacity_feasible": "",
                "customer_coverage_feasible": "",
                "supplier_feasible": "",
                "structural_validity": "",
                "cluster_count": "",
                "cluster_sizes": "",
                "global_depot_pool_used": "not_applicable",
                "total_system_distance_check": "not_available",
                "notes_or_warnings": "Case 1 no-clustering result folder not available",
            }
        )
    return rows


def build_csv_rows(runs: list[ExtractedRun]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for run in sorted(runs, key=lambda item: (item.routing_case, item.clustering_strategy, item.customer_count, item.vehicle_capacity)):
        metrics = run.metrics
        global_depot_pool_used = "not_applicable"
        if run.routing_case == "case_3_hybrid":
            global_depot_pool_used = metrics.get("global_depot_pool_used", "needs_check")

        rows.append(
            {
                "customer_count": run.customer_count,
                "vehicle_capacity": run.vehicle_capacity,
                "instance_name": run.instance_name,
                "routing_case": run.routing_case,
                "clustering_strategy": run.clustering_strategy,
                "selected_run_timestamp": run.selected_run_timestamp,
                "depot_setting_or_geometry": run.depot_setting_or_geometry,
                "customer_delivery_distance": value(metrics, "post_reloc_2opt_distance"),
                "supplier_depot_replenishment_distance": replenishment_distance(metrics),
                "supplier_direct_distance": supplier_direct_distance(metrics, run.routing_case),
                "depot_customer_distance": depot_customer_distance(metrics, run.routing_case),
                "total_system_distance": value(metrics, "post_reloc_2opt_total_system_distance"),
                "reported_final_distance": value(metrics, "post_reloc_2opt_distance"),
                "direct_customer_count": direct_customer_count(metrics, run.routing_case),
                "depot_customer_count": depot_customer_count(metrics, run.routing_case, run.customer_count),
                "n_routes": final_route_count(metrics),
                "avg_utilisation": value(metrics, "post_reloc_2opt_avg_utilization"),
                "min_utilisation": value(metrics, "post_reloc_2opt_min_utilization"),
                "max_utilisation": value(metrics, "post_reloc_2opt_max_utilization"),
                "capacity_feasible": bool_value(metrics, "capacity_feasibility"),
                "customer_coverage_feasible": bool_value(metrics, "all_customers_served"),
                "supplier_feasible": bool_value(metrics, "supply_feasibility"),
                "structural_validity": bool_value(metrics, "structural_validity"),
                "cluster_count": "" if run.clustering_strategy == "no_clustering" else cluster_count(run.clusters),
                "cluster_sizes": "" if run.clustering_strategy == "no_clustering" else cluster_sizes(run.clusters),
                "global_depot_pool_used": global_depot_pool_used,
                "total_system_distance_check": total_system_check(metrics),
                "notes_or_warnings": notes(run.warnings),
            }
        )

    rows.extend(not_available_case1_no_cluster_rows())
    return sorted(rows, key=lambda row: (row["routing_case"], row["clustering_strategy"], row["customer_count"], row["vehicle_capacity"]))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def count_by(rows: list[dict[str, Any]], key: str) -> dict[Any, int]:
    counts: dict[Any, int] = {}
    for row in rows:
        value_ = row.get(key)
        counts[value_] = counts.get(value_, 0) + 1
    return counts


def truthy_count(rows: list[dict[str, Any]], key: str) -> int:
    return sum(1 for row in rows if row.get(key) is True)


def warning_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if row.get("notes_or_warnings")]


def hybrid_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if row.get("routing_case") == "case_3_hybrid" and row.get("clustering_strategy") != "not_available"]


def write_summary(path: Path, rows: list[dict[str, Any]], extra_instances: dict[str, list[str]]) -> None:
    case_counts = count_by(rows, "routing_case")
    strategy_counts = count_by(rows, "clustering_strategy")
    warnings = warning_rows(rows)
    hybrid = hybrid_rows(rows)
    hybrid_replenishment_ok = [
        row for row in hybrid if row.get("total_system_distance_check") == "ok" and not row.get("notes_or_warnings")
    ]

    lines = [
        "# Section 6.3 Supplier Routing Structures Extraction Summary",
        "",
        "## Sources",
        "",
    ]
    for raw_spec in RESULT_FOLDERS:
        lines.append(f"- `{raw_spec['relative_path']}`")

    lines.extend(
        [
            "",
            "## Main Grid",
            "",
            "- Customer counts included in main CSV: `20, 40, 60, 80`.",
            "- Vehicle capacities included in main CSV: `15, 25, 35`.",
            "- Case 3 larger `100, 150, 200` customer runs are detected but not mixed into the main cross-case table.",
            "",
            "## Row Counts",
            "",
            f"- Rows written: {len(rows)}",
            f"- Rows with warnings: {len(warnings)}",
            "",
            "## Rows by Routing Case",
            "",
        ]
    )
    for key, count in sorted(case_counts.items()):
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
            f"- Supplier-feasible rows: {truthy_count(rows, 'supplier_feasible')}",
            f"- Structurally valid rows: {truthy_count(rows, 'structural_validity')}",
            "",
            "## Hybrid Replenishment Check",
            "",
            f"- Hybrid rows in main grid: {len(hybrid)}",
            f"- Hybrid rows with clean total-system-distance check and no warnings: {len(hybrid_replenishment_ok)}",
            "- The extractor selects the latest `run_*` folder in each instance directory.",
            "- Hybrid rows are flagged if depot-bound customers exist but first-echelon replenishment distance is zero.",
            "",
            "## Extra Hybrid Instances Detected",
            "",
        ]
    )
    if extra_instances:
        for folder, instances in sorted(extra_instances.items()):
            if instances:
                lines.append(f"- `{folder}`: {', '.join(sorted(instances))}")
            else:
                lines.append(f"- `{folder}`: none")
    else:
        lines.append("- None detected.")

    lines.extend(["", "## Warnings", ""])
    if warnings:
        for row in warnings:
            label = (
                f"{row.get('routing_case')} "
                f"{row.get('clustering_strategy')} "
                f"{row.get('customer_count')}c_cap{row.get('vehicle_capacity')} "
                f"{row.get('selected_run_timestamp')}"
            ).strip()
            lines.append(f"- `{label}`: {row.get('notes_or_warnings')}")
    else:
        lines.append("- No warnings recorded.")

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- `customer_delivery_distance` is extracted from `post_reloc_2opt_distance`.",
            "- `total_system_distance` is extracted from `post_reloc_2opt_total_system_distance`.",
            "- `supplier_depot_replenishment_distance` prefers `supplier_depot_replenishment_distance` and falls back to `total_first_echelon_distance`.",
            "- Case 1 no-clustering rows are written as `not_available` placeholders.",
            "- LNS, timing, dispatch-wave, split-repair, and time-aware LNS folders are excluded.",
            "",
        ]
    )

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    root = project_root()
    output_dir = root / OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    runs: list[ExtractedRun] = []
    extra_instances: dict[str, list[str]] = {}
    for raw_spec in RESULT_FOLDERS:
        spec = FolderSpec(**raw_spec)
        folder_runs, folder_extra = load_folder(root, spec)
        runs.extend(folder_runs)
        if spec.routing_case == "case_3_hybrid":
            extra_instances[str(spec.relative_path)] = folder_extra

    csv_rows = build_csv_rows(runs)
    write_csv(output_dir / OUTPUT_CSV, csv_rows)
    write_summary(output_dir / OUTPUT_SUMMARY, csv_rows, extra_instances)

    print(f"Wrote {output_dir / OUTPUT_CSV}")
    print(f"Wrote {output_dir / OUTPUT_SUMMARY}")


if __name__ == "__main__":
    main()
