#!/usr/bin/env python3
"""Extract Chapter 6.4 non-timing LNS operator-pair comparison."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


INSTANCE_RE = re.compile(r"^(?P<customers>\d+)c_cap(?P<capacity>\d+)$")

OUTPUT_DIR = Path("extractor/section 6.4")
OUTPUT_CSV = "section_6_4_lns_operator_pair_table.csv"
OUTPUT_SUMMARY = "section_6_4_lns_operator_pair_summary.md"

OPERATOR_DETAILS = {
    "random_greedy": {
        "destroy_operator": "random_removal",
        "repair_operator": "greedy_insertion",
    },
    "random_regret": {
        "destroy_operator": "random_removal",
        "repair_operator": "regret_2_insertion",
    },
    "worst_greedy": {
        "destroy_operator": "worst_removal",
        "repair_operator": "greedy_insertion",
    },
    "worst_regret": {
        "destroy_operator": "worst_removal",
        "repair_operator": "regret_2_insertion",
    },
    "related_greedy": {
        "destroy_operator": "related_shaw_removal",
        "repair_operator": "greedy_insertion",
    },
    "related_regret": {
        "destroy_operator": "related_shaw_removal",
        "repair_operator": "regret_2_insertion",
    },
}

BASELINE_RANDOM_GREEDY_FOLDERS = [
    {
        "relative_path": Path("results/lns_supplier_customer_only_baseline_sweep_v1"),
        "routing_case": "case_2_supplier_customer_direct",
        "structure_variant": "sweep",
    },
    {
        "relative_path": Path("results/lns_supplier_customer_only_baseline_kmeans_v1"),
        "routing_case": "case_2_supplier_customer_direct",
        "structure_variant": "kmeans",
    },
    {
        "relative_path": Path("results/lns_supplier_customer_only_no_cluster_v1"),
        "routing_case": "case_2_supplier_customer_direct",
        "structure_variant": "no_clustering",
    },
    {
        "relative_path": Path("results/lns_hybrid_supplier_customer_sweep_v1"),
        "routing_case": "case_3_hybrid",
        "structure_variant": "sweep",
    },
    {
        "relative_path": Path("results/lns_hybrid_supplier_customer_kmeans_v1"),
        "routing_case": "case_3_hybrid",
        "structure_variant": "kmeans",
    },
    {
        "relative_path": Path("results/lns_hybrid_supplier_customer_no_cluster_v1"),
        "routing_case": "case_3_hybrid",
        "structure_variant": "no_clustering",
    },
]

ADDITIONAL_OPERATOR_FOLDERS = {
    "random_regret": Path("results/lns_operator_random_regret"),
    "worst_greedy": Path("results/lns_operator_worst_greedy"),
    "worst_regret": Path("results/lns_operator_worst_regret"),
    "related_greedy": Path("results/lns_operator_related_greedy"),
    "related_regret": Path("results/lns_operator_related_regret"),
}

SUBFOLDER_MAPPING = {
    "case2_sweep": ("case_2_supplier_customer_direct", "sweep"),
    "case2_kmeans": ("case_2_supplier_customer_direct", "kmeans"),
    "case2_no_cluster": ("case_2_supplier_customer_direct", "no_clustering"),
    "case3_sweep": ("case_3_hybrid", "sweep"),
    "case3_kmeans": ("case_3_hybrid", "kmeans"),
    "case3_no_cluster": ("case_3_hybrid", "no_clustering"),
}

EXPECTED_80_BUCKETS = [
    (routing_case, structure, capacity)
    for routing_case in ("case_2_supplier_customer_direct", "case_3_hybrid")
    for structure in ("sweep", "kmeans", "no_clustering")
    for capacity in (15, 25, 35)
]


@dataclass(frozen=True)
class FolderSpec:
    relative_path: Path
    routing_case: str
    structure_variant: str
    operator_pair: str


@dataclass(frozen=True)
class ExtractedRun:
    customer_count: int
    vehicle_capacity: int
    instance_name: str
    routing_case: str
    structure_variant: str
    operator_pair: str
    source_folder: str
    selected_run_timestamp: str
    run_folder_count: int
    metrics_source_file: str
    metrics: dict[str, Any]
    summary: dict[str, Any]
    runner_summary: dict[str, Any]
    warnings: list[str]


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def parse_instance_name(path: Path) -> tuple[int, int] | None:
    match = INSTANCE_RE.match(path.name)
    if not match:
        return None
    return int(match.group("customers")), int(match.group("capacity"))


def latest_run(instance_dir: Path) -> tuple[Path | None, int]:
    runs = sorted(p for p in instance_dir.iterdir() if p.is_dir() and p.name.startswith("run_"))
    return (runs[-1], len(runs)) if runs else (None, 0)


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


def read_best_metrics(run_dir: Path) -> tuple[dict[str, Any], str, list[str]]:
    warnings: list[str] = []
    for filename in ("lns_sa_metrics_best.json", "lns_sa_metrics.json"):
        path = run_dir / filename
        if not path.exists():
            continue
        data, warning = read_json(path)
        if warning:
            warnings.append(warning)
            continue
        return data, filename, warnings
    return {}, "", ["missing lns_sa_metrics_best.json and lns_sa_metrics.json"]


def value(data: dict[str, Any], key: str) -> Any:
    return data.get(key, "")


def first_value(*values: Any) -> Any:
    for item in values:
        if item not in ("", None):
            return item
    return ""


def as_float(raw: Any) -> float | None:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def pct_improvement(baseline: Any, final: Any) -> float | str:
    baseline_value = as_float(baseline)
    final_value = as_float(final)
    if baseline_value is None or final_value is None or baseline_value == 0:
        return ""
    return ((baseline_value - final_value) / baseline_value) * 100


def serialize(raw: Any) -> str:
    if raw in ("", None):
        return ""
    if isinstance(raw, (list, dict)):
        return json.dumps(raw, ensure_ascii=False, sort_keys=True)
    return str(raw)


def bool_value(metrics: dict[str, Any], key: str) -> Any:
    raw = metrics.get(key, "")
    if isinstance(raw, bool):
        return raw
    return raw


def operator_destroy(operator_pair: str, metrics: dict[str, Any]) -> str:
    return str(first_value(metrics.get("destroy_operator"), OPERATOR_DETAILS[operator_pair]["destroy_operator"]))


def operator_repair(operator_pair: str, metrics: dict[str, Any]) -> str:
    return str(first_value(metrics.get("repair_operator"), OPERATOR_DETAILS[operator_pair]["repair_operator"]))


def baseline_distance(metrics: dict[str, Any], routing_case: str) -> Any:
    if routing_case == "case_3_hybrid":
        return first_value(
            metrics.get("baseline_reference_customer_delivery_distance"),
            metrics.get("baseline_reference_distance"),
        )
    return metrics.get("baseline_reference_distance", "")


def lns_distance(metrics: dict[str, Any], routing_case: str) -> Any:
    if routing_case == "case_3_hybrid":
        return first_value(
            metrics.get("customer_delivery_lns_distance"),
            metrics.get("total_lns_distance"),
        )
    return metrics.get("total_lns_distance", "")


def baseline_total_system_distance(metrics: dict[str, Any], routing_case: str) -> Any:
    if routing_case == "case_3_hybrid":
        return first_value(
            metrics.get("baseline_reference_system_distance"),
            metrics.get("baseline_reference_distance"),
        )
    return metrics.get("baseline_reference_distance", "")


def lns_total_system_distance(metrics: dict[str, Any], routing_case: str) -> Any:
    if routing_case == "case_3_hybrid":
        return first_value(
            metrics.get("total_lns_system_distance"),
            metrics.get("total_lns_distance"),
        )
    return metrics.get("total_lns_distance", "")


def customer_delivery_distance(metrics: dict[str, Any], routing_case: str) -> Any:
    if routing_case == "case_3_hybrid":
        return first_value(
            metrics.get("customer_delivery_lns_distance"),
            metrics.get("total_lns_distance"),
        )
    return metrics.get("total_lns_distance", "")


def supplier_depot_replenishment_distance(metrics: dict[str, Any], routing_case: str) -> Any:
    if routing_case != "case_3_hybrid":
        return ""
    return metrics.get("supplier_depot_replenishment_distance", "")


def absolute_improvement(metrics: dict[str, Any], routing_case: str) -> Any:
    if routing_case == "case_3_hybrid":
        return first_value(
            metrics.get("system_improvement_distance"),
            metrics.get("improvement_distance"),
        )
    return metrics.get("improvement_distance", "")


def percent_improvement(metrics: dict[str, Any], routing_case: str) -> Any:
    if routing_case == "case_3_hybrid":
        saved = first_value(
            metrics.get("system_improvement_percent"),
            metrics.get("improvement_percent"),
        )
        if saved != "":
            return saved
        return pct_improvement(baseline_total_system_distance(metrics, routing_case), lns_total_system_distance(metrics, routing_case))
    saved = metrics.get("improvement_percent", "")
    if saved != "":
        return saved
    return pct_improvement(baseline_distance(metrics, routing_case), lns_distance(metrics, routing_case))


def best_run_dict(runner_summary: dict[str, Any]) -> dict[str, Any]:
    best_run = runner_summary.get("best_run")
    if not isinstance(best_run, dict):
        return {}
    run = best_run.get("run")
    return run if isinstance(run, dict) else {}


def tested_n_remove_values(runner_summary: dict[str, Any]) -> Any:
    values = runner_summary.get("n_remove_values")
    return values if isinstance(values, list) else ""


def runtime_seconds(metrics: dict[str, Any], runner_summary: dict[str, Any]) -> Any:
    return first_value(
        metrics.get("runtime_seconds"),
        best_run_dict(runner_summary).get("runtime_seconds"),
    )


def best_iteration(metrics: dict[str, Any], summary: dict[str, Any], runner_summary: dict[str, Any]) -> Any:
    return first_value(
        metrics.get("best_iteration"),
        summary.get("best_iteration"),
        best_run_dict(runner_summary).get("best_iteration"),
    )


def capacity_feasible(metrics: dict[str, Any], summary: dict[str, Any]) -> Any:
    return first_value(metrics.get("capacity_feasibility"), summary.get("capacity_feasibility"))


def customer_coverage_feasible(metrics: dict[str, Any], summary: dict[str, Any]) -> Any:
    return first_value(metrics.get("all_customers_served"), summary.get("all_customers_served"))


def supplier_feasible(metrics: dict[str, Any], summary: dict[str, Any]) -> Any:
    return first_value(metrics.get("supply_feasibility"), summary.get("supply_feasibility"))


def structural_validity(metrics: dict[str, Any], summary: dict[str, Any]) -> Any:
    return first_value(metrics.get("structural_validity"), summary.get("structural_validity"))


def hybrid_system_distance_check(metrics: dict[str, Any], routing_case: str) -> str:
    if routing_case != "case_3_hybrid":
        return "not_applicable"

    customer_delivery = as_float(customer_delivery_distance(metrics, routing_case))
    replenishment = as_float(supplier_depot_replenishment_distance(metrics, routing_case))
    total_system = as_float(lns_total_system_distance(metrics, routing_case))

    if customer_delivery is None or replenishment is None or total_system is None:
        return "missing"
    return "ok" if abs((customer_delivery + replenishment) - total_system) < 1e-6 else "mismatch"


def metric_warnings(metrics: dict[str, Any], routing_case: str, operator_pair: str) -> list[str]:
    warnings: list[str] = []
    common_keys = [
        "baseline_reference_distance",
        "total_lns_distance",
        "n_iterations",
        "n_remove",
        "seed",
        "initial_temperature",
        "cooling_rate",
        "minimum_temperature",
        "n_routes",
        "lns_avg_utilization",
    ]
    for key in common_keys:
        if key not in metrics:
            warnings.append(f"missing metric {key}")

    if operator_pair != "random_greedy":
        for key in ("operator_pair", "destroy_operator", "repair_operator", "accepted_moves", "rejected_moves"):
            if key not in metrics:
                warnings.append(f"missing metric {key}")

    if routing_case == "case_3_hybrid":
        for key in (
            "baseline_reference_system_distance",
            "customer_delivery_lns_distance",
            "supplier_depot_replenishment_distance",
            "total_lns_system_distance",
        ):
            if key not in metrics:
                warnings.append(f"missing metric {key}")
        if hybrid_system_distance_check(metrics, routing_case) != "ok":
            warnings.append("hybrid total LNS system distance does not match customer-delivery plus replenishment distance")

    return warnings


def load_instance(root: Path, spec: FolderSpec, instance_dir: Path) -> ExtractedRun:
    parsed = parse_instance_name(instance_dir)
    if parsed is None:
        raise ValueError(f"invalid instance folder {instance_dir}")

    customer_count, vehicle_capacity = parsed
    warnings: list[str] = []
    run_dir, run_count = latest_run(instance_dir)
    metrics: dict[str, Any] = {}
    summary: dict[str, Any] = {}
    runner_summary: dict[str, Any] = {}
    metrics_source_file = ""

    if run_dir is None:
        warnings.append("missing run folder")
        selected_run_timestamp = ""
    else:
        selected_run_timestamp = run_dir.name

        metrics, metrics_source_file, metric_load_warnings = read_best_metrics(run_dir)
        warnings.extend(metric_load_warnings)

        summary, summary_warning = read_json(run_dir / "lns_sa_summary.json")
        if summary_warning:
            warnings.append(summary_warning)

        runner_summary, runner_warning = read_json(run_dir / "lns_sa_runner_summary.json")
        if runner_warning:
            warnings.append(runner_warning)

        if not (run_dir / "best_lns_solution.json").exists():
            warnings.append("missing best_lns_solution.json")
        if not (run_dir / "route_lns_sa_records_best.json").exists():
            warnings.append("missing route_lns_sa_records_best.json")

        warnings.extend(metric_warnings(metrics, spec.routing_case, spec.operator_pair))

    return ExtractedRun(
        customer_count=customer_count,
        vehicle_capacity=vehicle_capacity,
        instance_name=instance_dir.name,
        routing_case=spec.routing_case,
        structure_variant=spec.structure_variant,
        operator_pair=spec.operator_pair,
        source_folder=str(spec.relative_path),
        selected_run_timestamp=selected_run_timestamp,
        run_folder_count=run_count,
        metrics_source_file=metrics_source_file,
        metrics=metrics,
        summary=summary,
        runner_summary=runner_summary,
        warnings=warnings,
    )


def load_folder(root: Path, spec: FolderSpec) -> list[ExtractedRun]:
    folder = root / spec.relative_path
    if not folder.exists():
        return [
            ExtractedRun(
                customer_count=0,
                vehicle_capacity=0,
                instance_name="",
                routing_case=spec.routing_case,
                structure_variant=spec.structure_variant,
                operator_pair=spec.operator_pair,
                source_folder=str(spec.relative_path),
                selected_run_timestamp="",
                run_folder_count=0,
                metrics_source_file="",
                metrics={},
                summary={},
                runner_summary={},
                warnings=[f"missing result folder {spec.relative_path}"],
            )
        ]

    rows: list[ExtractedRun] = []
    for instance_dir in sorted(p for p in folder.iterdir() if p.is_dir()):
        if parse_instance_name(instance_dir) is None:
            continue
        rows.append(load_instance(root, spec, instance_dir))
    return rows


def folder_specs() -> list[FolderSpec]:
    specs: list[FolderSpec] = []

    for raw in BASELINE_RANDOM_GREEDY_FOLDERS:
        specs.append(
            FolderSpec(
                relative_path=raw["relative_path"],
                routing_case=raw["routing_case"],
                structure_variant=raw["structure_variant"],
                operator_pair="random_greedy",
            )
        )

    for operator_pair, base_folder in ADDITIONAL_OPERATOR_FOLDERS.items():
        for subfolder, (routing_case, structure_variant) in SUBFOLDER_MAPPING.items():
            specs.append(
                FolderSpec(
                    relative_path=base_folder / subfolder,
                    routing_case=routing_case,
                    structure_variant=structure_variant,
                    operator_pair=operator_pair,
                )
            )

    return specs


def row_distance_for_ranking(row: dict[str, Any]) -> float | None:
    if row["routing_case"] == "case_3_hybrid":
        return as_float(row.get("lns_total_system_distance"))
    return as_float(row.get("lns_distance"))


def build_csv_rows(runs: list[ExtractedRun]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for run in sorted(
        runs,
        key=lambda item: (
            item.operator_pair,
            item.routing_case,
            item.structure_variant,
            item.customer_count,
            item.vehicle_capacity,
        ),
    ):
        metrics = run.metrics
        summary = run.summary
        runner_summary = run.runner_summary
        baseline = baseline_distance(metrics, run.routing_case)
        lns = lns_distance(metrics, run.routing_case)
        baseline_system = baseline_total_system_distance(metrics, run.routing_case)
        lns_system = lns_total_system_distance(metrics, run.routing_case)
        absolute = absolute_improvement(metrics, run.routing_case)
        percent = percent_improvement(metrics, run.routing_case)
        check = hybrid_system_distance_check(metrics, run.routing_case)

        rows.append(
            {
                "customer_count": run.customer_count,
                "vehicle_capacity": run.vehicle_capacity,
                "instance_name": run.instance_name,
                "routing_case": run.routing_case,
                "structure_variant": run.structure_variant,
                "operator_pair": run.operator_pair,
                "destroy_operator": operator_destroy(run.operator_pair, metrics),
                "repair_operator": operator_repair(run.operator_pair, metrics),
                "source_folder": run.source_folder,
                "selected_run_timestamp": run.selected_run_timestamp,
                "run_folder_count": run.run_folder_count,
                "metrics_source_file": run.metrics_source_file,
                "baseline_distance": baseline,
                "lns_distance": lns,
                "baseline_total_system_distance": baseline_system,
                "lns_total_system_distance": lns_system,
                "customer_delivery_distance": customer_delivery_distance(metrics, run.routing_case),
                "supplier_depot_replenishment_distance": supplier_depot_replenishment_distance(metrics, run.routing_case),
                "absolute_improvement": absolute,
                "percent_improvement": percent,
                "customer_delivery_improvement_distance": value(metrics, "customer_delivery_improvement_distance"),
                "customer_delivery_improvement_percent": value(metrics, "customer_delivery_improvement_percent"),
                "system_improvement_distance": value(metrics, "system_improvement_distance"),
                "system_improvement_percent": value(metrics, "system_improvement_percent"),
                "best_n_remove": value(metrics, "n_remove"),
                "tested_n_remove_values": serialize(tested_n_remove_values(runner_summary)),
                "iterations": value(metrics, "n_iterations"),
                "seed": value(metrics, "seed"),
                "temperature_initial": value(metrics, "initial_temperature"),
                "cooling_rate": value(metrics, "cooling_rate"),
                "temperature_minimum": value(metrics, "minimum_temperature"),
                "n_routes": value(metrics, "n_routes"),
                "avg_utilisation": value(metrics, "lns_avg_utilization"),
                "min_utilisation": value(metrics, "lns_min_utilization"),
                "max_utilisation": value(metrics, "lns_max_utilization"),
                "accepted_moves": value(metrics, "accepted_moves"),
                "rejected_moves": value(metrics, "rejected_moves"),
                "best_iteration": best_iteration(metrics, summary, runner_summary),
                "runtime_seconds": runtime_seconds(metrics, runner_summary),
                "supplier_count": value(metrics, "supplier_count"),
                "worst_removal_randomness": value(metrics, "worst_removal_randomness"),
                "related_removal_randomness": value(metrics, "related_removal_randomness"),
                "distance_weight": value(metrics, "distance_weight"),
                "demand_weight": value(metrics, "demand_weight"),
                "route_weight": value(metrics, "route_weight"),
                "capacity_feasible": capacity_feasible(metrics, summary),
                "customer_coverage_feasible": customer_coverage_feasible(metrics, summary),
                "supplier_feasible": supplier_feasible(metrics, summary),
                "structural_validity": structural_validity(metrics, summary),
                "hybrid_system_distance_check": check,
                "ranking_distance_used": row_distance_for_ranking(
                    {
                        "routing_case": run.routing_case,
                        "lns_total_system_distance": lns_system,
                        "lns_distance": lns,
                    }
                )
                or "",
                "notes_or_warnings": notes(run.warnings),
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


def notes(items: list[str]) -> str:
    return "; ".join(items)


def count_by(rows: list[dict[str, Any]], key: str) -> dict[Any, int]:
    counts: dict[Any, int] = {}
    for row in rows:
        value_ = row.get(key)
        counts[value_] = counts.get(value_, 0) + 1
    return counts


def warning_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if row.get("notes_or_warnings")]


def truthy_count(rows: list[dict[str, Any]], key: str) -> int:
    return sum(1 for row in rows if row.get(key) is True)


def recorded_count(rows: list[dict[str, Any]], key: str) -> int:
    return sum(1 for row in rows if row.get(key) not in ("", None))


def comparison_80_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if row.get("customer_count") == 80]


def comparison_buckets(rows: list[dict[str, Any]]) -> dict[tuple[Any, Any, Any], list[dict[str, Any]]]:
    buckets: dict[tuple[Any, Any, Any], list[dict[str, Any]]] = {}
    for row in comparison_80_rows(rows):
        key = (row["routing_case"], row["structure_variant"], row["vehicle_capacity"])
        buckets.setdefault(key, []).append(row)
    return buckets


def operator_stats(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    stats = {
        operator_pair: {"wins": 0, "ranks": [], "improvements": [], "comparable_buckets": 0}
        for operator_pair in OPERATOR_DETAILS
    }

    for bucket_rows in comparison_buckets(rows).values():
        comparable = []
        for row in bucket_rows:
            distance = row_distance_for_ranking(row)
            if distance is None:
                continue
            comparable.append((distance, row["operator_pair"], row))
        if not comparable:
            continue

        comparable.sort(key=lambda item: item[0])
        best_distance = comparable[0][0]
        for rank, (distance, operator_pair, row) in enumerate(comparable, start=1):
            stats.setdefault(operator_pair, {"wins": 0, "ranks": [], "improvements": [], "comparable_buckets": 0})
            stats[operator_pair]["ranks"].append(rank)
            stats[operator_pair]["comparable_buckets"] += 1
            improvement = as_float(row.get("percent_improvement"))
            if improvement is not None:
                stats[operator_pair]["improvements"].append(improvement)
            if abs(distance - best_distance) < 1e-9:
                stats[operator_pair]["wins"] += 1

    return stats


def average(values: list[float]) -> float | str:
    if not values:
        return ""
    return sum(values) / len(values)


def missing_80_buckets(rows: list[dict[str, Any]]) -> list[str]:
    buckets = comparison_buckets(rows)
    missing: list[str] = []
    for routing_case, structure, capacity in EXPECTED_80_BUCKETS:
        rows_for_bucket = buckets.get((routing_case, structure, capacity), [])
        operators = {row["operator_pair"] for row in rows_for_bucket}
        missing_ops = sorted(set(OPERATOR_DETAILS) - operators)
        if missing_ops:
            missing.append(f"{routing_case} {structure} 80c_cap{capacity}: missing {', '.join(missing_ops)}")
    return missing


def larger_hybrid_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if row.get("routing_case") == "case_3_hybrid" and row.get("customer_count") in {100, 150, 200}
    ]


def write_summary(path: Path, rows: list[dict[str, Any]], specs: list[FolderSpec]) -> None:
    warnings = warning_rows(rows)
    stats = operator_stats(rows)
    missing_buckets = missing_80_buckets(rows)
    larger_rows = larger_hybrid_rows(rows)
    row_counts_by_operator = count_by(rows, "operator_pair")
    row_counts_by_case = count_by(rows, "routing_case")
    row_counts_by_structure = count_by(rows, "structure_variant")
    hybrid_rows = [row for row in rows if row.get("routing_case") == "case_3_hybrid"]
    hybrid_ok = [row for row in hybrid_rows if row.get("hybrid_system_distance_check") in {"ok", "not_applicable"}]

    lines = [
        "# Section 6.4 LNS Operator-Pair Extraction Summary",
        "",
        "## Sources Checked",
        "",
    ]
    for spec in specs:
        lines.append(f"- `{spec.relative_path}`")

    lines.extend(["", "## Row Counts", "", f"- Rows written: {len(rows)}", f"- Rows with warnings: {len(warnings)}"])

    lines.extend(["", "## Rows by Operator Pair", ""])
    for key, count in sorted(row_counts_by_operator.items()):
        lines.append(f"- `{key}`: {count}")

    lines.extend(["", "## Rows by Routing Case", ""])
    for key, count in sorted(row_counts_by_case.items()):
        lines.append(f"- `{key}`: {count}")

    lines.extend(["", "## Rows by Structure Variant", ""])
    for key, count in sorted(row_counts_by_structure.items()):
        lines.append(f"- `{key}`: {count}")

    lines.extend(
        [
            "",
            "## 80-Customer Comparison Completeness",
            "",
            f"- Expected comparison buckets: {len(EXPECTED_80_BUCKETS)}",
            f"- Buckets detected: {len(comparison_buckets(rows))}",
            f"- Missing bucket/operator entries: {len(missing_buckets)}",
        ]
    )
    if missing_buckets:
        lines.extend(f"- {item}" for item in missing_buckets)
    else:
        lines.append("- All expected 80-customer operator-pair bucket entries are present.")

    lines.extend(["", "## Operator-Pair 80-Customer Summary", ""])
    lines.append("| Operator pair | Wins | Average rank | Average improvement (%) | Comparable bucket rows |")
    lines.append("|---|---:|---:|---:|---:|")
    for operator_pair in sorted(stats):
        data = stats[operator_pair]
        avg_rank = average(data["ranks"])
        avg_improvement = average(data["improvements"])
        lines.append(
            "| "
            f"`{operator_pair}` | "
            f"{data['wins']} | "
            f"{avg_rank if avg_rank == '' else round(avg_rank, 4)} | "
            f"{avg_improvement if avg_improvement == '' else round(avg_improvement, 4)} | "
            f"{data['comparable_buckets']} |"
        )

    lines.extend(
        [
            "",
            "## Larger Hybrid Availability",
            "",
            f"- Larger Hybrid rows detected: {len(larger_rows)}",
        ]
    )
    larger_counts = count_by(larger_rows, "operator_pair")
    if larger_counts:
        for key, count in sorted(larger_counts.items()):
            lines.append(f"- `{key}`: {count}")
    else:
        lines.append("- No larger Hybrid rows detected.")

    lines.extend(
        [
            "",
            "## Feasibility and Distance Checks",
            "",
            f"- Capacity-feasible rows recorded as true: {truthy_count(rows, 'capacity_feasible')} of {recorded_count(rows, 'capacity_feasible')} recorded.",
            f"- Customer-coverage-feasible rows recorded as true: {truthy_count(rows, 'customer_coverage_feasible')} of {recorded_count(rows, 'customer_coverage_feasible')} recorded.",
            f"- Supplier-feasible rows recorded as true: {truthy_count(rows, 'supplier_feasible')} of {recorded_count(rows, 'supplier_feasible')} recorded.",
            f"- Structurally valid rows recorded as true: {truthy_count(rows, 'structural_validity')} of {recorded_count(rows, 'structural_validity')} recorded.",
            f"- Hybrid rows with valid system-distance check: {len(hybrid_ok)} of {len(hybrid_rows)}",
            "",
            "## Retained Pairs for Later Timing-Aware LNS",
            "",
            "- `random_regret`",
            "- `related_regret`",
            "",
            "## Timing Exclusion Confirmation",
            "",
            "- Timing-aware LNS result folders were not read by this extractor.",
            "- Fixed timing, dispatch-wave timing, split-repair timing, speed40 timing, and 14:00-wave timing folders are excluded.",
            "",
            "## Warnings",
            "",
        ]
    )
    if warnings:
        for row in warnings[:120]:
            label = (
                f"{row.get('operator_pair')} {row.get('routing_case')} {row.get('structure_variant')} "
                f"{row.get('instance_name')} {row.get('selected_run_timestamp')}"
            )
            lines.append(f"- `{label}`: {row.get('notes_or_warnings')}")
        if len(warnings) > 120:
            lines.append(f"- Additional warnings omitted from summary: {len(warnings) - 120}")
    else:
        lines.append("- No warnings recorded.")

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- The extractor selects the latest `run_*` folder in each instance directory.",
            "- `lns_sa_metrics_best.json` is preferred over `lns_sa_metrics.json`.",
            "- For Case 2, ranking uses direct `lns_distance`.",
            "- For Case 3 Hybrid, ranking uses `lns_total_system_distance`.",
            "- All detected instance sizes are written to the CSV; the main matched thesis comparison should focus on the 80-customer rows.",
            "",
        ]
    )

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    root = project_root()
    output_dir = root / OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    specs = folder_specs()
    runs: list[ExtractedRun] = []
    for spec in specs:
        runs.extend(load_folder(root, spec))

    rows = build_csv_rows(runs)
    write_csv(output_dir / OUTPUT_CSV, rows)
    write_summary(output_dir / OUTPUT_SUMMARY, rows, specs)

    print(f"Wrote {output_dir / OUTPUT_CSV}")
    print(f"Wrote {output_dir / OUTPUT_SUMMARY}")


if __name__ == "__main__":
    main()
