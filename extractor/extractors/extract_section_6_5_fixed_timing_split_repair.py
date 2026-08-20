#!/usr/bin/env python3
"""Extract Chapter 6.5 fixed depot timing and fixed-time split repair results."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


INSTANCE_RE = re.compile(r"^(?P<customers>\d+)c_cap(?P<capacity>\d+)$")

OUTPUT_DIR = Path("extractor/section 6.5")
OUTPUT_CSV = "section_6_5_fixed_timing_split_repair_table.csv"
OUTPUT_SUMMARY = "section_6_5_fixed_timing_split_repair_summary.md"

EXPECTED_CUSTOMER_COUNTS = (20, 40, 60, 80, 100, 150, 200)
EXPECTED_CAPACITIES = (15, 25, 35)

FOLDER_SPECS = [
    {
        "timing_variant": "fixed_timing",
        "relative_path": Path("results/hybrid_supplier_customer_kmeans_timing_fixed_v1"),
        "description": "Hybrid + KMeans with fixed depot ready time",
    },
    {
        "timing_variant": "fixed_timing_split_repair",
        "relative_path": Path("results/hybrid_supplier_customer_kmeans_timing_fixed_split_v1"),
        "description": "Hybrid + KMeans with fixed depot ready time and split repair",
    },
]


@dataclass(frozen=True)
class ExtractedRun:
    customer_count: int
    vehicle_capacity: int
    instance_name: str
    timing_variant: str
    source_folder: str
    selected_run_timestamp: str
    run_folder_count: int
    run_classification: str
    metrics: dict[str, Any]
    summary: dict[str, Any]
    config: dict[str, Any]
    timing_summary: dict[str, Any]
    repair_summary: dict[str, Any]
    timing_records: list[dict[str, Any]]
    pre_repair_records: list[dict[str, Any]]
    repair_records: list[dict[str, Any]]
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


def read_json_dict(path: Path) -> tuple[dict[str, Any], str | None]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        return {}, f"missing {path.name}"
    except json.JSONDecodeError as exc:
        return {}, f"invalid JSON in {path.name}: {exc}"

    if not isinstance(data, dict):
        return {}, f"{path.name} is not a JSON object"
    return data, None


def read_json_list(path: Path) -> tuple[list[dict[str, Any]], str | None]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        return [], f"missing {path.name}"
    except json.JSONDecodeError as exc:
        return [], f"invalid JSON in {path.name}: {exc}"

    if not isinstance(data, list):
        return [], f"{path.name} is not a JSON list"
    records = [item for item in data if isinstance(item, dict)]
    if len(records) != len(data):
        return records, f"{path.name} contains non-object records"
    return records, None


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


def as_int(raw: Any) -> int | None:
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def numeric_delta(after: Any, before: Any) -> float | str:
    after_value = as_float(after)
    before_value = as_float(before)
    if after_value is None or before_value is None:
        return ""
    return after_value - before_value


def pct_delta(after: Any, before: Any) -> float | str:
    after_value = as_float(after)
    before_value = as_float(before)
    if after_value is None or before_value is None or before_value == 0:
        return ""
    return ((after_value - before_value) / before_value) * 100


def serialize(raw: Any) -> str:
    if raw in ("", None):
        return ""
    if isinstance(raw, (dict, list)):
        return json.dumps(raw, ensure_ascii=False, sort_keys=True)
    return str(raw)


def boolish(raw: Any) -> Any:
    if isinstance(raw, bool):
        return raw
    return raw


def count_unique_customers(records: list[dict[str, Any]]) -> int | str:
    customers: set[int] = set()
    for record in records:
        raw_customers = record.get("customers", [])
        if not isinstance(raw_customers, list):
            continue
        for customer in raw_customers:
            try:
                customers.add(int(customer))
            except (TypeError, ValueError):
                continue
    return len(customers) if customers else ""


def estimate_service_time_per_customer(records: list[dict[str, Any]]) -> float | str:
    values: list[float] = []
    for record in records:
        service_time = as_float(record.get("route_service_time_hours"))
        customer_count = as_float(record.get("n_customers"))
        if service_time is None or customer_count is None or customer_count == 0:
            continue
        values.append(service_time / customer_count)
    if not values:
        return ""
    return sum(values) / len(values)


def estimate_average_speed(records: list[dict[str, Any]]) -> float | str:
    values: list[float] = []
    for record in records:
        distance = as_float(record.get("route_distance"))
        travel_time = as_float(record.get("route_travel_time_hours"))
        if distance is None or travel_time is None or travel_time == 0:
            continue
        values.append(distance / travel_time)
    if not values:
        return ""
    return sum(values) / len(values)


def source_file_exists(run_dir: Path, filename: str) -> bool:
    return (run_dir / filename).exists()


def metric_warnings(run: ExtractedRun) -> list[str]:
    warnings: list[str] = []
    required_common = [
        "post_reloc_2opt_distance",
        "post_reloc_2opt_total_system_distance",
        "supplier_depot_replenishment_distance",
        "trips",
        "capacity_feasibility",
        "all_customers_served",
        "depot_timing_feasibility",
        "n_depot_timing_routes",
        "n_depot_timing_infeasible_routes",
        "latest_depot_route_finish_time",
    ]
    for key in required_common:
        if key not in run.metrics and key not in run.summary and key not in run.timing_summary:
            warnings.append(f"missing metric {key}")

    if run.timing_variant == "fixed_timing_split_repair":
        required_repair = [
            "n_routes_before_repair",
            "n_routes_after_repair",
            "n_infeasible_routes_before_repair",
            "n_infeasible_routes_after_repair",
            "n_repair_attempts",
            "n_successful_repairs",
            "n_unresolved_repairs",
            "distance_before_repair",
            "distance_after_repair",
            "latest_finish_before_repair",
            "latest_finish_after_repair",
        ]
        for key in required_repair:
            if key not in run.repair_summary:
                warnings.append(f"missing repair summary {key}")

    depot_scope = first_value(run.metrics.get("depot_routing_scope"), run.summary.get("depot_routing_scope"))
    if depot_scope not in ("", "global_depot_customer_pool", "global_depot_pool"):
        warnings.append("depot routing scope is not global_depot_customer_pool")

    replenishment = as_float(
        first_value(
            run.metrics.get("supplier_depot_replenishment_distance"),
            run.metrics.get("total_first_echelon_distance"),
        )
    )
    depot_customers = as_int(run.metrics.get("n_depot_customers"))
    if depot_customers and (replenishment is None or replenishment <= 0):
        warnings.append("depot customers exist but supplier-depot replenishment distance is missing or zero")

    if boolish(first_value(run.metrics.get("capacity_feasibility"), run.summary.get("feasible"))) is False:
        warnings.append("capacity infeasible")
    if boolish(first_value(run.metrics.get("all_customers_served"), run.summary.get("customers_served"))) is False:
        warnings.append("customer coverage infeasible")
    if boolish(first_value(run.metrics.get("depot_timing_feasibility"), run.timing_summary.get("depot_timing_feasibility"))) is False:
        warnings.append("timing infeasible")
    if as_int(first_value(run.metrics.get("n_fixed_timing_unresolved_repairs"), run.repair_summary.get("n_unresolved_repairs"))) not in (None, 0):
        warnings.append("unresolved split repair remains")

    return warnings


def load_instance(spec: dict[str, Any], instance_dir: Path) -> ExtractedRun:
    parsed = parse_instance_name(instance_dir)
    if parsed is None:
        raise ValueError(f"invalid instance folder {instance_dir}")

    customer_count, vehicle_capacity = parsed
    warnings: list[str] = []
    run_dir, run_count = latest_run(instance_dir)

    metrics: dict[str, Any] = {}
    summary: dict[str, Any] = {}
    config: dict[str, Any] = {}
    timing_summary: dict[str, Any] = {}
    repair_summary: dict[str, Any] = {}
    timing_records: list[dict[str, Any]] = []
    pre_repair_records: list[dict[str, Any]] = []
    repair_records: list[dict[str, Any]] = []

    if run_dir is None:
        selected_run_timestamp = ""
        warnings.append("missing run folder")
    else:
        selected_run_timestamp = run_dir.name

        for filename, target in (
            ("metrics.json", "metrics"),
            ("summary.json", "summary"),
            ("config_used.json", "config"),
            ("depot_timing_fixed_summary.json", "timing_summary"),
            ("depot_timing_fixed_repair_summary.json", "repair_summary"),
        ):
            data, warning = read_json_dict(run_dir / filename)
            if warning and filename not in ("depot_timing_fixed_repair_summary.json",):
                warnings.append(warning)
            if warning and spec["timing_variant"] == "fixed_timing_split_repair" and filename == "depot_timing_fixed_repair_summary.json":
                warnings.append(warning)
            if target == "metrics":
                metrics = data
            elif target == "summary":
                summary = data
            elif target == "config":
                config = data
            elif target == "timing_summary":
                timing_summary = data
            elif target == "repair_summary":
                repair_summary = data

        timing_records, warning = read_json_list(run_dir / "depot_timing_fixed_records.json")
        if warning:
            warnings.append(warning)

        if spec["timing_variant"] == "fixed_timing_split_repair":
            pre_repair_records, warning = read_json_list(run_dir / "depot_timing_fixed_pre_repair_records.json")
            if warning:
                warnings.append(warning)
            repair_records, warning = read_json_list(run_dir / "depot_timing_fixed_repair_records.json")
            if warning:
                warnings.append(warning)
            if not source_file_exists(run_dir, "route_plot_timing_split_repair.png"):
                warnings.append("missing route_plot_timing_split_repair.png")

    run = ExtractedRun(
        customer_count=customer_count,
        vehicle_capacity=vehicle_capacity,
        instance_name=instance_dir.name,
        timing_variant=spec["timing_variant"],
        source_folder=str(spec["relative_path"]),
        selected_run_timestamp=selected_run_timestamp,
        run_folder_count=run_count,
        run_classification="main" if run_dir is not None else "needs_check",
        metrics=metrics,
        summary=summary,
        config=config,
        timing_summary=timing_summary,
        repair_summary=repair_summary,
        timing_records=timing_records,
        pre_repair_records=pre_repair_records,
        repair_records=repair_records,
        warnings=warnings,
    )
    return ExtractedRun(
        **{
            **run.__dict__,
            "warnings": [*warnings, *metric_warnings(run)],
        }
    )


def load_folder(root: Path, spec: dict[str, Any]) -> list[ExtractedRun]:
    folder = root / spec["relative_path"]
    if not folder.exists():
        return [
            ExtractedRun(
                customer_count=0,
                vehicle_capacity=0,
                instance_name="",
                timing_variant=spec["timing_variant"],
                source_folder=str(spec["relative_path"]),
                selected_run_timestamp="",
                run_folder_count=0,
                run_classification="needs_check",
                metrics={},
                summary={},
                config={},
                timing_summary={},
                repair_summary={},
                timing_records=[],
                pre_repair_records=[],
                repair_records=[],
                warnings=[f"missing result folder {spec['relative_path']}"],
            )
        ]

    runs: list[ExtractedRun] = []
    for instance_dir in sorted(p for p in folder.iterdir() if p.is_dir()):
        if parse_instance_name(instance_dir) is None:
            continue
        runs.append(load_instance(spec, instance_dir))
    return runs


def paired_fixed_map(runs: list[ExtractedRun]) -> dict[tuple[int, int], ExtractedRun]:
    return {
        (run.customer_count, run.vehicle_capacity): run
        for run in runs
        if run.timing_variant == "fixed_timing"
    }


def pre_repair_customer_delivery_distance(run: ExtractedRun) -> Any:
    if run.timing_variant == "fixed_timing":
        return first_value(run.metrics.get("post_reloc_2opt_distance"), run.summary.get("final_distance"))
    final_distance = as_float(first_value(run.metrics.get("post_reloc_2opt_distance"), run.summary.get("final_distance")))
    repair_delta = as_float(
        first_value(
            run.metrics.get("distance_delta_after_fixed_timing_repair"),
            run.repair_summary.get("distance_delta_after_repair"),
        )
    )
    if final_distance is None or repair_delta is None:
        return ""
    return final_distance - repair_delta


def post_repair_customer_delivery_distance(run: ExtractedRun) -> Any:
    if run.timing_variant == "fixed_timing":
        return ""
    return first_value(run.metrics.get("post_reloc_2opt_distance"), run.summary.get("final_distance"))


def final_customer_delivery_distance(run: ExtractedRun) -> Any:
    return first_value(
        post_repair_customer_delivery_distance(run),
        run.metrics.get("post_reloc_2opt_distance"),
        run.summary.get("final_distance"),
    )


def final_total_system_distance(run: ExtractedRun) -> Any:
    return first_value(
        run.metrics.get("post_reloc_2opt_total_system_distance"),
        run.summary.get("final_total_system_distance"),
    )


def pre_repair_total_system_distance(run: ExtractedRun) -> Any:
    if run.timing_variant == "fixed_timing":
        return first_value(
            run.metrics.get("post_reloc_2opt_total_system_distance"),
            run.summary.get("final_total_system_distance"),
        )

    final_total = as_float(
        first_value(
            run.metrics.get("post_reloc_2opt_total_system_distance"),
            run.summary.get("final_total_system_distance"),
        )
    )
    repair_delta = as_float(
        first_value(
            run.metrics.get("distance_delta_after_fixed_timing_repair"),
            run.repair_summary.get("distance_delta_after_repair"),
        )
    )
    if final_total is None or repair_delta is None:
        return ""
    return final_total - repair_delta


def post_repair_total_system_distance(run: ExtractedRun) -> Any:
    if run.timing_variant == "fixed_timing":
        return ""
    return first_value(
        run.metrics.get("post_reloc_2opt_total_system_distance"),
        run.summary.get("final_total_system_distance"),
    )


def pre_repair_total_routes(run: ExtractedRun) -> Any:
    if run.timing_variant == "fixed_timing":
        return first_value(run.metrics.get("trips"), run.summary.get("trips"))
    return first_value(run.repair_summary.get("n_routes_before_repair"), run.metrics.get("n_depot_timing_routes_before_repair"))


def post_repair_total_routes(run: ExtractedRun) -> Any:
    if run.timing_variant == "fixed_timing":
        return ""
    return first_value(run.metrics.get("trips"), run.summary.get("trips"), run.repair_summary.get("n_routes_after_repair"))


def depot_routes(run: ExtractedRun) -> Any:
    return first_value(
        run.metrics.get("n_depot_timing_routes"),
        run.timing_summary.get("n_depot_timing_routes"),
        run.repair_summary.get("n_routes_after_repair"),
    )


def pre_repair_depot_routes(run: ExtractedRun) -> Any:
    if run.timing_variant == "fixed_timing":
        return depot_routes(run)
    return first_value(run.metrics.get("n_depot_timing_routes_before_repair"), run.repair_summary.get("n_routes_before_repair"))


def post_repair_depot_routes(run: ExtractedRun) -> Any:
    if run.timing_variant == "fixed_timing":
        return ""
    return first_value(run.metrics.get("n_depot_timing_routes"), run.repair_summary.get("n_routes_after_repair"))


def pre_repair_infeasible_routes(run: ExtractedRun) -> Any:
    if run.timing_variant == "fixed_timing":
        return first_value(run.metrics.get("n_depot_timing_infeasible_routes"), run.timing_summary.get("n_depot_timing_infeasible_routes"))
    return first_value(run.metrics.get("n_depot_timing_infeasible_routes_before_repair"), run.repair_summary.get("n_infeasible_routes_before_repair"))


def post_repair_infeasible_routes(run: ExtractedRun) -> Any:
    if run.timing_variant == "fixed_timing":
        return ""
    return first_value(run.metrics.get("n_depot_timing_infeasible_routes"), run.repair_summary.get("n_infeasible_routes_after_repair"))


def latest_finish_time(run: ExtractedRun) -> Any:
    return first_value(
        run.metrics.get("latest_depot_route_finish_time"),
        run.timing_summary.get("latest_depot_route_finish_time"),
        run.repair_summary.get("latest_finish_after_repair"),
    )


def latest_finish_label(run: ExtractedRun) -> Any:
    return first_value(
        run.metrics.get("latest_depot_route_finish_time_label"),
        run.timing_summary.get("latest_depot_route_finish_time_label"),
        run.repair_summary.get("latest_finish_after_repair_label"),
        run.summary.get("latest_depot_route_finish_time_label"),
    )


def build_csv_rows(runs: list[ExtractedRun]) -> list[dict[str, Any]]:
    fixed_rows = paired_fixed_map(runs)
    rows: list[dict[str, Any]] = []

    for run in sorted(runs, key=lambda item: (item.customer_count, item.vehicle_capacity, item.timing_variant)):
        fixed_pair = fixed_rows.get((run.customer_count, run.vehicle_capacity))
        timing_records = run.timing_records
        pre_records = run.pre_repair_records or run.timing_records

        pre_customer_distance = pre_repair_customer_delivery_distance(run)
        post_customer_distance = post_repair_customer_delivery_distance(run)
        pre_total_distance = pre_repair_total_system_distance(run)
        post_total_distance = post_repair_total_system_distance(run)
        row_total_distance = final_total_system_distance(run)
        row_customer_distance = final_customer_delivery_distance(run)

        fixed_total_distance = final_total_system_distance(fixed_pair) if fixed_pair else ""
        split_vs_fixed_total_delta = numeric_delta(row_total_distance, fixed_total_distance) if run.timing_variant == "fixed_timing_split_repair" else ""
        split_vs_fixed_total_delta_pct = pct_delta(row_total_distance, fixed_total_distance) if run.timing_variant == "fixed_timing_split_repair" else ""

        route_count_change = numeric_delta(post_repair_total_routes(run), pre_repair_total_routes(run))
        depot_route_count_change = numeric_delta(post_repair_depot_routes(run), pre_repair_depot_routes(run))
        infeasible_change = numeric_delta(post_repair_infeasible_routes(run), pre_repair_infeasible_routes(run))

        warnings = list(dict.fromkeys(run.warnings))
        if run.timing_variant == "fixed_timing_split_repair" and fixed_pair is None:
            warnings.append("missing paired fixed timing row")

        rows.append(
            {
                "customer_count": run.customer_count,
                "vehicle_capacity": run.vehicle_capacity,
                "instance_name": run.instance_name,
                "timing_variant": run.timing_variant,
                "source_folder": run.source_folder,
                "selected_run_timestamp": run.selected_run_timestamp,
                "run_folder_count": run.run_folder_count,
                "run_classification": run.run_classification,
                "algorithm": first_value(run.metrics.get("algorithm"), run.summary.get("algorithm")),
                "timing_model": first_value(run.metrics.get("timing_model"), run.summary.get("timing_model")),
                "base_timing_model": first_value(run.metrics.get("base_timing_model"), run.summary.get("base_timing_model")),
                "timing_repair_model": first_value(run.metrics.get("timing_repair_model"), run.repair_summary.get("repair_model")),
                "fixed_timing_repair_scope": run.metrics.get("fixed_timing_repair_scope", ""),
                "depot_ready_time": first_value(run.metrics.get("fixed_depot_ready_time"), run.summary.get("fixed_depot_ready_time"), run.config.get("fixed_depot_ready_time")),
                "depot_ready_time_label": first_value(run.metrics.get("fixed_depot_ready_time_label"), run.summary.get("fixed_depot_ready_time_label")),
                "outbound_departure_time": first_value(run.metrics.get("fixed_depot_ready_time"), run.summary.get("fixed_depot_ready_time"), run.config.get("fixed_depot_ready_time")),
                "working_day_end_time": first_value(run.metrics.get("working_day_end_time"), run.summary.get("working_day_end_time"), run.config.get("working_day_end_time")),
                "working_day_end_time_label": first_value(run.metrics.get("working_day_end_time_label"), run.summary.get("working_day_end_time_label")),
                "service_time_per_customer_hours_estimate": estimate_service_time_per_customer(timing_records or pre_records),
                "average_speed_estimate": first_value(run.config.get("average_speed"), run.metrics.get("average_speed"), estimate_average_speed(timing_records or pre_records)),
                "depot_handling_time": "not_applicable_fixed_timing",
                "n_suppliers": first_value(run.metrics.get("n_suppliers"), run.summary.get("n_suppliers"), run.config.get("n_suppliers")),
                "direct_delivery_threshold": first_value(run.metrics.get("direct_delivery_threshold"), run.summary.get("direct_delivery_threshold"), run.config.get("direct_delivery_threshold")),
                "seed": first_value(run.metrics.get("seed"), run.summary.get("seed"), run.config.get("seed")),
                "grid_size": run.config.get("grid_size", ""),
                "n_supplier_direct_customers": first_value(run.metrics.get("n_supplier_direct_customers"), run.summary.get("n_supplier_direct_customers")),
                "n_depot_customers": first_value(run.metrics.get("n_depot_customers"), run.summary.get("n_depot_customers")),
                "supplier_direct_routing_scope": first_value(run.metrics.get("supplier_direct_routing_scope"), run.summary.get("supplier_direct_routing_scope")),
                "depot_routing_scope": first_value(run.metrics.get("depot_routing_scope"), run.summary.get("depot_routing_scope")),
                "customer_delivery_distance": row_customer_distance,
                "supplier_depot_replenishment_distance": first_value(run.metrics.get("supplier_depot_replenishment_distance"), run.metrics.get("total_first_echelon_distance"), run.summary.get("supplier_depot_replenishment_distance")),
                "total_system_distance": row_total_distance,
                "pre_repair_customer_delivery_distance": pre_customer_distance,
                "post_repair_customer_delivery_distance": post_customer_distance,
                "pre_repair_total_system_distance": pre_total_distance,
                "post_repair_total_system_distance": post_total_distance,
                "pre_repair_depot_outbound_distance": run.repair_summary.get("distance_before_repair", ""),
                "post_repair_depot_outbound_distance": run.repair_summary.get("distance_after_repair", ""),
                "depot_outbound_distance_change_after_repair": run.repair_summary.get("distance_delta_after_repair", ""),
                "distance_change_after_repair": numeric_delta(post_total_distance, pre_total_distance),
                "distance_change_after_repair_pct": pct_delta(post_total_distance, pre_total_distance),
                "matched_fixed_total_system_distance": fixed_total_distance,
                "split_vs_fixed_total_system_distance_delta": split_vs_fixed_total_delta,
                "split_vs_fixed_total_system_distance_delta_pct": split_vs_fixed_total_delta_pct,
                "total_routes": first_value(run.metrics.get("trips"), run.summary.get("trips")),
                "pre_repair_total_routes": pre_repair_total_routes(run),
                "post_repair_total_routes": post_repair_total_routes(run),
                "depot_routes": depot_routes(run),
                "pre_repair_depot_routes": pre_repair_depot_routes(run),
                "post_repair_depot_routes": post_repair_depot_routes(run),
                "route_count_change_after_repair": route_count_change,
                "depot_route_count_change_after_repair": depot_route_count_change,
                "routes_added_by_repair": depot_route_count_change,
                "timing_routes_checked": first_value(run.metrics.get("n_depot_timing_routes"), run.timing_summary.get("n_depot_timing_routes")),
                "timing_feasible_routes": first_value(run.metrics.get("n_depot_timing_feasible_routes"), run.timing_summary.get("n_depot_timing_feasible_routes")),
                "timing_infeasible_routes": first_value(run.metrics.get("n_depot_timing_infeasible_routes"), run.timing_summary.get("n_depot_timing_infeasible_routes")),
                "pre_repair_timing_infeasible_routes": pre_repair_infeasible_routes(run),
                "post_repair_timing_infeasible_routes": post_repair_infeasible_routes(run),
                "infeasible_route_change_after_repair": infeasible_change,
                "infeasible_timing_route_ids": serialize(first_value(run.metrics.get("infeasible_timing_route_ids"), run.timing_summary.get("infeasible_timing_route_ids"))),
                "infeasible_timing_customers": serialize(first_value(run.metrics.get("infeasible_timing_customers"), run.timing_summary.get("infeasible_timing_customers"))),
                "latest_finish_time": latest_finish_time(run),
                "latest_finish_time_label": latest_finish_label(run),
                "pre_repair_latest_finish_time": first_value(run.repair_summary.get("latest_finish_before_repair"), latest_finish_time(run) if run.timing_variant == "fixed_timing" else ""),
                "pre_repair_latest_finish_time_label": first_value(run.repair_summary.get("latest_finish_before_repair_label"), latest_finish_label(run) if run.timing_variant == "fixed_timing" else ""),
                "post_repair_latest_finish_time": run.repair_summary.get("latest_finish_after_repair", ""),
                "post_repair_latest_finish_time_label": run.repair_summary.get("latest_finish_after_repair_label", ""),
                "max_route_duration": first_value(run.metrics.get("max_depot_route_duration_hours"), run.timing_summary.get("max_depot_route_duration_hours")),
                "avg_route_duration": first_value(run.metrics.get("avg_depot_route_duration_hours"), run.timing_summary.get("avg_depot_route_duration_hours")),
                "repair_attempts": first_value(run.metrics.get("n_fixed_timing_repair_attempts"), run.repair_summary.get("n_repair_attempts")),
                "successful_repairs": first_value(run.metrics.get("n_fixed_timing_successful_repairs"), run.repair_summary.get("n_successful_repairs")),
                "unresolved_repairs": first_value(run.metrics.get("n_fixed_timing_unresolved_repairs"), run.repair_summary.get("n_unresolved_repairs")),
                "unresolved_infeasible_route_ids": serialize(run.repair_summary.get("unresolved_infeasible_route_ids", "")),
                "unresolved_customers": count_unique_customers(run.repair_records),
                "overall_timing_feasible": first_value(run.metrics.get("overall_feasible_with_fixed_timing"), run.summary.get("overall_feasible_with_fixed_timing")),
                "depot_timing_feasibility": first_value(run.metrics.get("depot_timing_feasibility"), run.timing_summary.get("depot_timing_feasibility")),
                "capacity_feasible": first_value(run.metrics.get("capacity_feasibility"), run.summary.get("feasible")),
                "customer_coverage_feasible": first_value(run.metrics.get("all_customers_served"), run.summary.get("customers_served")),
                "supplier_feasible": run.metrics.get("supply_feasibility", ""),
                "structural_validity": first_value(run.metrics.get("structural_validity"), run.summary.get("structural_validity")),
                "avg_utilisation": first_value(run.metrics.get("post_reloc_2opt_avg_utilization"), run.summary.get("avg_utilization")),
                "min_utilisation": first_value(run.metrics.get("post_reloc_2opt_min_utilization"), run.summary.get("min_utilization")),
                "max_utilisation": first_value(run.metrics.get("post_reloc_2opt_max_utilization"), run.summary.get("max_utilization")),
                "depot_avg_utilisation": first_value(run.timing_summary.get("avg_depot_route_utilization"), run.metrics.get("avg_depot_route_utilization")),
                "route_records_count": len(timing_records),
                "pre_repair_route_records_count": len(pre_records),
                "repair_records_count": len(run.repair_records),
                "best_n_remove": "",
                "tested_n_remove_values": "",
                "n_remove_applicability": "not_applicable_section_6_5_is_not_lns",
                "notes_or_warnings": " | ".join(warnings),
            }
        )

    return rows


def expected_instances() -> set[tuple[int, int]]:
    return {
        (customer_count, capacity)
        for customer_count in EXPECTED_CUSTOMER_COUNTS
        for capacity in EXPECTED_CAPACITIES
    }


def write_csv(root: Path, rows: list[dict[str, Any]]) -> Path:
    output_dir = root / OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / OUTPUT_CSV
    if not rows:
        output_path.write_text("", encoding="utf-8")
        return output_path

    fieldnames = list(rows[0].keys())
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: serialize(value) for key, value in row.items()})
    return output_path


def variant_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        variant = str(row["timing_variant"])
        counts[variant] = counts.get(variant, 0) + 1
    return counts


def missing_instances(rows: list[dict[str, Any]], variant: str) -> list[str]:
    present = {
        (int(row["customer_count"]), int(row["vehicle_capacity"]))
        for row in rows
        if row["timing_variant"] == variant and row["customer_count"] and row["vehicle_capacity"]
    }
    return [f"{customers}c_cap{capacity}" for customers, capacity in sorted(expected_instances() - present)]


def warning_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if row.get("notes_or_warnings")]


def repair_outcome_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        "split_rows": 0,
        "feasible_after_repair": 0,
        "infeasible_after_repair": 0,
        "unresolved_repair_rows": 0,
        "rows_with_repairs_attempted": 0,
    }
    for row in rows:
        if row["timing_variant"] != "fixed_timing_split_repair":
            continue
        counts["split_rows"] += 1
        if str(row.get("depot_timing_feasibility")) == "True":
            counts["feasible_after_repair"] += 1
        if str(row.get("depot_timing_feasibility")) == "False":
            counts["infeasible_after_repair"] += 1
        unresolved = as_int(row.get("unresolved_repairs"))
        if unresolved and unresolved > 0:
            counts["unresolved_repair_rows"] += 1
        attempts = as_int(row.get("repair_attempts"))
        if attempts and attempts > 0:
            counts["rows_with_repairs_attempted"] += 1
    return counts


def write_summary(root: Path, rows: list[dict[str, Any]], runs: list[ExtractedRun]) -> Path:
    output_dir = root / OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / OUTPUT_SUMMARY

    counts = variant_counts(rows)
    warnings = warning_rows(rows)
    repair_counts = repair_outcome_counts(rows)
    run_counts_by_variant: dict[str, list[int]] = {}
    for run in runs:
        run_counts_by_variant.setdefault(run.timing_variant, []).append(run.run_folder_count)

    lines: list[str] = [
        "# Section 6.5 Fixed Depot Timing and Fixed-Time Split Repair Extraction Summary",
        "",
        "## Source Folders",
        "",
    ]
    for spec in FOLDER_SPECS:
        lines.append(f"- `{spec['relative_path']}`: {spec['description']}")

    lines.extend(
        [
            "",
            "## Output Files",
            "",
            f"- CSV: `{OUTPUT_DIR / OUTPUT_CSV}`",
            f"- Summary: `{OUTPUT_DIR / OUTPUT_SUMMARY}`",
            "",
            "## Extraction Rule",
            "",
            "- The extractor selects the lexicographically latest `run_*` folder for every instance folder.",
            "- Older timestamped folders are not written as main rows; `run_folder_count` records where multiple runs exist.",
            "- The extractor deliberately excludes dispatch-wave timing, speed sensitivity, 14:00-wave sensitivity, time-aware LNS, and non-timing LNS folders.",
            "- `best_n_remove` and `tested_n_remove_values` are left blank because Section 6.5 is a timing-baseline section, not an LNS section.",
            "",
            "## Rows Written",
            "",
            f"- Total rows: {len(rows)}",
        ]
    )
    for variant in sorted(counts):
        lines.append(f"- `{variant}` rows: {counts[variant]}")

    lines.extend(["", "## Expected Instance Grid", ""])
    lines.append("- Expected customer counts: `20, 40, 60, 80, 100, 150, 200`")
    lines.append("- Expected vehicle capacities: `15, 25, 35`")
    for spec in FOLDER_SPECS:
        missing = missing_instances(rows, spec["timing_variant"])
        if missing:
            lines.append(f"- Missing `{spec['timing_variant']}` rows: {', '.join(missing)}")
        else:
            lines.append(f"- Missing `{spec['timing_variant']}` rows: none")

    lines.extend(
        [
            "",
            "## Pre-Repair Versus Post-Repair Handling",
            "",
            "- Fixed-timing rows use the fixed timing outputs as the pre-repair baseline.",
            "- Split-repair rows keep pre-repair route-count and timing values from `depot_timing_fixed_repair_summary.json` fields such as `n_routes_before_repair`, `n_infeasible_routes_before_repair`, and `latest_finish_before_repair`.",
            "- Split-repair rows keep post-repair route-count and timing values from `n_routes_after_repair`, `n_infeasible_routes_after_repair`, and `latest_finish_after_repair`, cross-checked against final timing metrics where available.",
            "- `distance_before_repair` and `distance_after_repair` from the repair summary are stored as depot-outbound repair distances, not full system distances.",
            "- Full pre-repair customer/system distances are derived from the final saved distances minus `distance_delta_after_fixed_timing_repair`; full post-repair customer/system distances use the final saved metrics.",
            "- Derived delta fields compare post-repair values against pre-repair values only when both values are available.",
            "",
            "## Split Repair Outcome Counts",
            "",
        ]
    )
    for key, value in repair_counts.items():
        lines.append(f"- `{key}`: {value}")

    lines.extend(["", "## Run Folder Counts", ""])
    for variant, counts_for_variant in sorted(run_counts_by_variant.items()):
        if not counts_for_variant:
            continue
        lines.append(
            f"- `{variant}`: min {min(counts_for_variant)}, max {max(counts_for_variant)}, instances with multiple runs {sum(1 for count in counts_for_variant if count > 1)}"
        )

    lines.extend(["", "## Warnings", ""])
    if warnings:
        lines.append(f"- Rows with warnings: {len(warnings)}")
        for row in warnings[:80]:
            lines.append(
                f"- `{row['timing_variant']}` `{row['instance_name']}` `{row['selected_run_timestamp']}`: {row['notes_or_warnings']}"
            )
        if len(warnings) > 80:
            lines.append(f"- Additional warning rows omitted from summary: {len(warnings) - 80}")
    else:
        lines.append("- Rows with warnings: 0")

    lines.extend(
        [
            "",
            "## Thesis Use Notes",
            "",
            "- Use this extraction for Section 6.5 only.",
            "- Treat fixed timing as feasibility flagging under a common depot ready time.",
            "- Treat split repair as a route-level timing feasibility repair, not as split delivery of individual customer demand.",
            "- Do not describe these rows as dispatch-wave timing or time-aware LNS.",
        ]
    )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def main() -> None:
    root = project_root()
    runs: list[ExtractedRun] = []
    for spec in FOLDER_SPECS:
        runs.extend(load_folder(root, spec))

    rows = build_csv_rows(runs)
    csv_path = write_csv(root, rows)
    summary_path = write_summary(root, rows, runs)

    print(f"Wrote {csv_path}")
    print(f"Wrote {summary_path}")
    print(f"Rows: {len(rows)}")
    print(f"Warnings: {len(warning_rows(rows))}")


if __name__ == "__main__":
    main()
