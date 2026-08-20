#!/usr/bin/env python3
"""Extract Chapter 6.6 dispatch-wave timing and same-wave split repair results."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


INSTANCE_RE = re.compile(r"^(?P<customers>\d+)c_cap(?P<capacity>\d+)$")

OUTPUT_DIR = Path("extractor/section 6.6")
OUTPUT_CSV = "section_6_6_dispatch_wave_split_repair_table.csv"
OUTPUT_SUMMARY = "section_6_6_dispatch_wave_split_repair_summary.md"

EXPECTED_CUSTOMER_COUNTS = (20, 40, 60, 80, 100, 150, 200)
EXPECTED_CAPACITIES = (15, 25, 35)
EXPECTED_SPEED = 30.0
EXPECTED_WAVES = (9.0, 11.0, 13.0, 15.0)
SPEED_TOLERANCE = 0.25

MAIN_FOLDER_SPECS = [
    {
        "timing_variant": "dispatch_wave_constructed",
        "relative_path": Path("results/hybrid_supplier_customer_kmeans_timing_waves_constructed_v1"),
        "description": "Hybrid + KMeans with wave-aware dispatch construction",
        "expected_speed": EXPECTED_SPEED,
        "expected_waves": EXPECTED_WAVES,
    },
    {
        "timing_variant": "dispatch_wave_constructed_split_repair",
        "relative_path": Path("results/hybrid_supplier_customer_kmeans_timing_waves_constructed_split_v1"),
        "description": "Hybrid + KMeans with wave-aware dispatch construction and same-wave split repair",
        "expected_speed": EXPECTED_SPEED,
        "expected_waves": EXPECTED_WAVES,
    },
]

ARCHIVE_FOLDER_SPEC = {
    "timing_variant": "route_first_dispatch_wave_archive",
    "relative_path": Path("results/hybrid_supplier_customer_kmeans_timing_waves_v1"),
    "description": "Older route-first dispatch-wave implementation; archive/development only",
}


@dataclass(frozen=True)
class ExtractedRun:
    customer_count: int
    vehicle_capacity: int
    instance_name: str
    timing_variant: str
    source_folder: str
    selected_run_timestamp: str
    run_folder_count: int
    latest_available_run_timestamp: str
    selected_run_is_latest_available: bool
    run_classification: str
    metrics: dict[str, Any]
    summary: dict[str, Any]
    config: dict[str, Any]
    wave_assignment_summary: dict[str, Any]
    timing_summary: dict[str, Any]
    pre_repair_summary: dict[str, Any]
    repair_summary: dict[str, Any]
    timing_records: list[dict[str, Any]]
    customer_wave_records: list[dict[str, Any]]
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


def timestamped_runs(instance_dir: Path) -> list[Path]:
    return sorted(p for p in instance_dir.iterdir() if p.is_dir() and p.name.startswith("run_"))


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
    if isinstance(raw, (dict, list, tuple)):
        return json.dumps(raw, ensure_ascii=False, sort_keys=True)
    return str(raw)


def boolish(raw: Any) -> Any:
    if isinstance(raw, bool):
        return raw
    return raw


def source_file_exists(run_dir: Path, filename: str) -> bool:
    return (run_dir / filename).exists()


def count_archive_runs(root: Path) -> dict[str, Any]:
    folder = root / ARCHIVE_FOLDER_SPEC["relative_path"]
    if not folder.exists():
        return {
            "folder": str(ARCHIVE_FOLDER_SPEC["relative_path"]),
            "exists": False,
            "instance_count": 0,
            "run_count": 0,
            "instances_with_multiple_runs": 0,
        }

    instance_count = 0
    run_count = 0
    instances_with_multiple_runs = 0
    for instance_dir in sorted(p for p in folder.iterdir() if p.is_dir()):
        if parse_instance_name(instance_dir) is None:
            continue
        instance_count += 1
        _, count = latest_run(instance_dir)
        run_count += count
        if count > 1:
            instances_with_multiple_runs += 1
    return {
        "folder": str(ARCHIVE_FOLDER_SPEC["relative_path"]),
        "exists": True,
        "instance_count": instance_count,
        "run_count": run_count,
        "instances_with_multiple_runs": instances_with_multiple_runs,
    }


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


def normalize_waves(raw: Any) -> tuple[float, ...] | None:
    if raw in ("", None):
        return None
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return None
    if not isinstance(raw, (list, tuple)):
        return None
    waves: list[float] = []
    for item in raw:
        value = as_float(item)
        if value is None:
            return None
        waves.append(value)
    return tuple(waves)


def first_saved_or_estimated_speed(config: dict[str, Any], metrics: dict[str, Any], records: list[dict[str, Any]], pre_records: list[dict[str, Any]]) -> tuple[Any, str]:
    config_speed = first_value(config.get("average_speed"), "")
    if config_speed != "":
        return config_speed, "config_used.json"
    metrics_speed = first_value(metrics.get("average_speed"), "")
    if metrics_speed != "":
        return metrics_speed, "metrics.json"
    estimate = estimate_average_speed(records or pre_records)
    if estimate != "":
        return estimate, "route_record_estimate"
    return "", "missing"


def first_saved_waves(config: dict[str, Any], metrics: dict[str, Any]) -> tuple[Any, str]:
    config_waves = first_value(config.get("dispatch_waves"), "")
    if config_waves != "":
        return config_waves, "config_used.json"
    metrics_waves = first_value(metrics.get("dispatch_waves"), "")
    if metrics_waves != "":
        return metrics_waves, "metrics.json"
    return "", "missing"


def quick_candidate_parameter_check(run_dir: Path, spec: dict[str, Any]) -> tuple[bool, list[str]]:
    config, config_warning = read_json_dict(run_dir / "config_used.json")
    metrics, metrics_warning = read_json_dict(run_dir / "metrics.json")
    timing_records, records_warning = read_json_list(run_dir / "depot_timing_wave_records.json")
    pre_records, pre_records_warning = read_json_list(run_dir / "depot_timing_wave_pre_repair_records.json")
    warnings = [item for item in (config_warning, metrics_warning, records_warning, pre_records_warning) if item]

    speed, speed_source = first_saved_or_estimated_speed(config, metrics, timing_records, pre_records)
    waves, wave_source = first_saved_waves(config, metrics)
    speed_float = as_float(speed)
    wave_tuple = normalize_waves(waves)
    expected_speed = float(spec["expected_speed"])
    expected_waves = tuple(spec["expected_waves"])

    speed_ok = speed_float is not None and abs(speed_float - expected_speed) <= SPEED_TOLERANCE
    waves_ok = wave_tuple == expected_waves
    if speed_source == "missing":
        warnings.append("candidate average speed missing")
    elif not speed_ok:
        warnings.append(f"candidate average speed mismatch expected {expected_speed}")
    if wave_source == "missing":
        warnings.append("candidate dispatch waves missing")
    elif not waves_ok:
        warnings.append(f"candidate dispatch waves mismatch expected {expected_waves}")
    return speed_ok and waves_ok, warnings


def select_latest_matching_run(instance_dir: Path, spec: dict[str, Any]) -> tuple[Path | None, int, Path | None, list[str]]:
    runs = timestamped_runs(instance_dir)
    if not runs:
        return None, 0, None, ["missing run folder"]

    latest_available = runs[-1]
    rejected: list[str] = []
    for run_dir in reversed(runs):
        ok, candidate_warnings = quick_candidate_parameter_check(run_dir, spec)
        if ok:
            warnings: list[str] = []
            if run_dir != latest_available:
                newer = [item.name for item in runs if item > run_dir]
                warnings.append(
                    "selected latest scenario-parameter-matching run; newer mismatched run(s) ignored: "
                    + ", ".join(newer)
                )
            return run_dir, len(runs), latest_available, warnings
        rejected.append(f"{run_dir.name} ({'; '.join(candidate_warnings)})")

    return (
        latest_available,
        len(runs),
        latest_available,
        [
            "no run matched expected Section 6.6 speed/wave parameters; selected latest available run",
            "candidate parameter issues: " + " | ".join(rejected[:5]),
        ],
    )


def metric_warnings(run: ExtractedRun) -> list[str]:
    warnings: list[str] = []
    required_common = [
        "post_reloc_2opt_distance",
        "post_reloc_2opt_total_system_distance",
        "supplier_depot_replenishment_distance",
        "trips",
        "capacity_feasibility",
        "all_customers_served",
        "overall_feasible_with_dispatch_waves",
        "depot_timing_feasibility",
        "n_depot_timing_routes",
        "n_depot_timing_infeasible_routes",
        "n_routes_departing_before_goods_ready",
        "n_routes_exceeding_working_day",
        "latest_depot_route_finish_time",
    ]
    for key in required_common:
        if key not in run.metrics and key not in run.summary and key not in run.timing_summary:
            warnings.append(f"missing metric {key}")

    if not run.customer_wave_records:
        warnings.append("missing customer wave timing records")
    if not run.wave_assignment_summary:
        warnings.append("missing customer wave assignment summary")

    depot_scope = first_value(run.metrics.get("depot_routing_scope"), run.summary.get("depot_routing_scope"))
    if depot_scope not in ("", "global_depot_pool_by_dispatch_wave"):
        warnings.append("depot routing scope is not global_depot_pool_by_dispatch_wave")

    if run.timing_variant == "dispatch_wave_constructed":
        if not run.timing_records:
            warnings.append("missing wave route records")

    if run.timing_variant == "dispatch_wave_constructed_split_repair":
        required_repair = [
            "n_wave_timing_repair_attempts",
            "n_wave_timing_successful_repairs",
            "n_wave_timing_unresolved_repairs",
            "n_depot_timing_routes_before_repair",
            "n_depot_timing_routes_after_repair",
            "routes_added_by_wave_repair",
            "depot_distance_before_wave_repair",
            "depot_distance_after_wave_repair",
            "distance_delta_after_wave_repair",
            "n_unresolved_customers_after_wave_repair",
        ]
        for key in required_repair:
            if key not in run.repair_summary and key not in run.metrics:
                warnings.append(f"missing repair summary {key}")
        if not run.pre_repair_summary:
            warnings.append("missing pre-repair timing summary")
        if not run.pre_repair_records:
            warnings.append("missing pre-repair wave route records")
        repair_attempts = as_int(
            first_value(
                run.metrics.get("n_wave_timing_repair_attempts"),
                run.repair_summary.get("n_wave_timing_repair_attempts"),
            )
        )
        if repair_attempts and repair_attempts > 0 and not run.repair_records:
            warnings.append("missing wave repair records despite repair attempts")
        if not source_file_exists(run_dir_from_run(root=project_root(), run=run), "route_plot_dispatch_wave_constructed_split_repair.png"):
            warnings.append("missing route_plot_dispatch_wave_constructed_split_repair.png")
        repair_model = first_value(run.metrics.get("timing_repair_model"), run.repair_summary.get("repair_model"))
        if repair_model != "same_wave_duration_split_with_2opt":
            warnings.append("same-wave split repair model not confirmed")

    replenishment = as_float(
        first_value(
            run.metrics.get("supplier_depot_replenishment_distance"),
            run.metrics.get("total_first_echelon_distance"),
        )
    )
    depot_customers = as_int(run.metrics.get("n_depot_customers"))
    if depot_customers and (replenishment is None or replenishment <= 0):
        warnings.append("depot customers exist but supplier-depot replenishment distance is missing or zero")

    if first_value(run.metrics.get("wave_assignment_before_routing"), "") == "false":
        warnings.append("wave assignment before routing is false")
    if run.timing_variant == "dispatch_wave_constructed_split_repair" and first_value(run.metrics.get("same_wave_repair_used"), "") == "false":
        warnings.append("same-wave repair used is false")

    if boolish(first_value(run.metrics.get("capacity_feasibility"), run.summary.get("feasible"))) is False:
        warnings.append("capacity infeasible")
    if boolish(first_value(run.metrics.get("all_customers_served"), run.summary.get("customers_served"))) is False:
        warnings.append("customer coverage infeasible")
    if boolish(first_value(run.metrics.get("depot_timing_feasibility"), run.timing_summary.get("depot_timing_feasibility"))) is False:
        warnings.append("timing infeasible")
    if as_int(first_value(run.metrics.get("n_routes_departing_before_goods_ready"), run.timing_summary.get("n_routes_departing_before_goods_ready"))) not in (None, 0):
        warnings.append("routes depart before goods ready")
    if as_int(first_value(run.metrics.get("n_routes_exceeding_working_day"), run.timing_summary.get("n_routes_exceeding_working_day"))) not in (None, 0):
        warnings.append("routes exceed working day")
    if as_int(first_value(run.metrics.get("n_wave_timing_unresolved_repairs"), run.repair_summary.get("n_wave_timing_unresolved_repairs"))) not in (None, 0):
        warnings.append("unresolved same-wave split repair remains")
    if as_int(first_value(run.metrics.get("n_unresolved_customers_after_wave_repair"), run.repair_summary.get("n_unresolved_customers_after_wave_repair"))) not in (None, 0):
        warnings.append("unresolved customers after wave repair")

    return warnings


def run_dir_from_run(root: Path, run: ExtractedRun) -> Path:
    return root / run.source_folder / run.instance_name / run.selected_run_timestamp


def load_instance(spec: dict[str, Any], instance_dir: Path) -> ExtractedRun:
    parsed = parse_instance_name(instance_dir)
    if parsed is None:
        raise ValueError(f"invalid instance folder {instance_dir}")

    customer_count, vehicle_capacity = parsed
    warnings: list[str] = []
    run_dir, run_count, latest_available_run_dir, selection_warnings = select_latest_matching_run(instance_dir, spec)
    warnings.extend(selection_warnings)

    metrics: dict[str, Any] = {}
    summary: dict[str, Any] = {}
    config: dict[str, Any] = {}
    wave_assignment_summary: dict[str, Any] = {}
    timing_summary: dict[str, Any] = {}
    pre_repair_summary: dict[str, Any] = {}
    repair_summary: dict[str, Any] = {}
    timing_records: list[dict[str, Any]] = []
    customer_wave_records: list[dict[str, Any]] = []
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
            ("depot_customer_wave_assignment_summary.json", "wave_assignment_summary"),
            ("depot_timing_wave_summary.json", "timing_summary"),
            ("depot_timing_wave_pre_repair_summary.json", "pre_repair_summary"),
            ("depot_timing_wave_repair_summary.json", "repair_summary"),
        ):
            data, warning = read_json_dict(run_dir / filename)
            optional = filename in ("depot_timing_wave_pre_repair_summary.json", "depot_timing_wave_repair_summary.json")
            if warning and not optional:
                warnings.append(warning)
            if warning and optional and spec["timing_variant"] == "dispatch_wave_constructed_split_repair":
                warnings.append(warning)
            if target == "metrics":
                metrics = data
            elif target == "summary":
                summary = data
            elif target == "config":
                config = data
            elif target == "wave_assignment_summary":
                wave_assignment_summary = data
            elif target == "timing_summary":
                timing_summary = data
            elif target == "pre_repair_summary":
                pre_repair_summary = data
            elif target == "repair_summary":
                repair_summary = data

        timing_records, warning = read_json_list(run_dir / "depot_timing_wave_records.json")
        if warning:
            warnings.append(warning)

        customer_wave_records, warning = read_json_list(run_dir / "depot_customer_wave_timing_records.json")
        if warning:
            warnings.append(warning)

        if spec["timing_variant"] == "dispatch_wave_constructed_split_repair":
            pre_repair_records, warning = read_json_list(run_dir / "depot_timing_wave_pre_repair_records.json")
            if warning:
                warnings.append(warning)
            repair_records, warning = read_json_list(run_dir / "depot_timing_wave_repair_records.json")
            if warning:
                warnings.append(warning)

    run = ExtractedRun(
        customer_count=customer_count,
        vehicle_capacity=vehicle_capacity,
        instance_name=instance_dir.name,
        timing_variant=spec["timing_variant"],
        source_folder=str(spec["relative_path"]),
        selected_run_timestamp=selected_run_timestamp,
        run_folder_count=run_count,
        latest_available_run_timestamp=latest_available_run_dir.name if latest_available_run_dir is not None else "",
        selected_run_is_latest_available=run_dir == latest_available_run_dir if run_dir is not None else False,
        run_classification="main" if run_dir is not None else "needs_check",
        metrics=metrics,
        summary=summary,
        config=config,
        wave_assignment_summary=wave_assignment_summary,
        timing_summary=timing_summary,
        pre_repair_summary=pre_repair_summary,
        repair_summary=repair_summary,
        timing_records=timing_records,
        customer_wave_records=customer_wave_records,
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
                latest_available_run_timestamp="",
                selected_run_is_latest_available=False,
                run_classification="needs_check",
                metrics={},
                summary={},
                config={},
                wave_assignment_summary={},
                timing_summary={},
                pre_repair_summary={},
                repair_summary={},
                timing_records=[],
                customer_wave_records=[],
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


def constructed_map(runs: list[ExtractedRun]) -> dict[tuple[int, int], ExtractedRun]:
    return {
        (run.customer_count, run.vehicle_capacity): run
        for run in runs
        if run.timing_variant == "dispatch_wave_constructed"
    }


def repair_delta(run: ExtractedRun) -> Any:
    return first_value(
        run.metrics.get("distance_delta_after_wave_repair"),
        run.repair_summary.get("distance_delta_after_wave_repair"),
    )


def final_customer_delivery_distance(run: ExtractedRun) -> Any:
    return first_value(run.metrics.get("post_reloc_2opt_distance"), run.summary.get("final_distance"))


def final_total_system_distance(run: ExtractedRun) -> Any:
    return first_value(run.metrics.get("post_reloc_2opt_total_system_distance"), run.summary.get("final_total_system_distance"))


def pre_repair_customer_delivery_distance(run: ExtractedRun) -> Any:
    if run.timing_variant == "dispatch_wave_constructed":
        return final_customer_delivery_distance(run)
    final_value = as_float(final_customer_delivery_distance(run))
    delta = as_float(repair_delta(run))
    if final_value is None or delta is None:
        return ""
    return final_value - delta


def post_repair_customer_delivery_distance(run: ExtractedRun) -> Any:
    if run.timing_variant == "dispatch_wave_constructed":
        return ""
    return final_customer_delivery_distance(run)


def pre_repair_total_system_distance(run: ExtractedRun) -> Any:
    if run.timing_variant == "dispatch_wave_constructed":
        return final_total_system_distance(run)
    final_value = as_float(final_total_system_distance(run))
    delta = as_float(repair_delta(run))
    if final_value is None or delta is None:
        return ""
    return final_value - delta


def post_repair_total_system_distance(run: ExtractedRun) -> Any:
    if run.timing_variant == "dispatch_wave_constructed":
        return ""
    return final_total_system_distance(run)


def timing_routes(run: ExtractedRun) -> Any:
    return first_value(run.metrics.get("n_depot_timing_routes"), run.timing_summary.get("n_depot_timing_routes"))


def pre_repair_depot_routes(run: ExtractedRun) -> Any:
    if run.timing_variant == "dispatch_wave_constructed":
        return timing_routes(run)
    return first_value(
        run.metrics.get("n_depot_timing_routes_before_repair"),
        run.repair_summary.get("n_depot_timing_routes_before_repair"),
        run.pre_repair_summary.get("n_depot_timing_routes"),
    )


def post_repair_depot_routes(run: ExtractedRun) -> Any:
    if run.timing_variant == "dispatch_wave_constructed":
        return ""
    return first_value(
        run.metrics.get("n_depot_timing_routes_after_repair"),
        run.repair_summary.get("n_depot_timing_routes_after_repair"),
        timing_routes(run),
    )


def pre_summary_value(run: ExtractedRun, key: str) -> Any:
    if run.timing_variant == "dispatch_wave_constructed":
        return first_value(run.metrics.get(key), run.timing_summary.get(key))
    return first_value(run.pre_repair_summary.get(key), run.metrics.get(key))


def post_summary_value(run: ExtractedRun, key: str) -> Any:
    if run.timing_variant == "dispatch_wave_constructed":
        return ""
    return first_value(run.timing_summary.get(key), run.metrics.get(key))


def latest_finish_time(run: ExtractedRun) -> Any:
    return first_value(run.metrics.get("latest_depot_route_finish_time"), run.timing_summary.get("latest_depot_route_finish_time"))


def latest_finish_label(run: ExtractedRun) -> Any:
    return first_value(
        run.metrics.get("latest_depot_route_finish_time_label"),
        run.timing_summary.get("latest_depot_route_finish_time_label"),
        run.summary.get("latest_depot_route_finish_time_label"),
    )


def routes_added_by_repair(run: ExtractedRun) -> Any:
    return first_value(run.metrics.get("routes_added_by_wave_repair"), run.repair_summary.get("routes_added_by_wave_repair"))


def pre_repair_total_routes(run: ExtractedRun) -> Any:
    if run.timing_variant == "dispatch_wave_constructed":
        return first_value(run.metrics.get("trips"), run.summary.get("trips"))
    final_routes = as_int(first_value(run.metrics.get("trips"), run.summary.get("trips")))
    added_routes = as_int(routes_added_by_repair(run))
    if final_routes is None or added_routes is None:
        return ""
    return final_routes - added_routes


def post_repair_total_routes(run: ExtractedRun) -> Any:
    if run.timing_variant == "dispatch_wave_constructed":
        return ""
    return first_value(run.metrics.get("trips"), run.summary.get("trips"))


def wave_assignment_before_routing(run: ExtractedRun) -> str:
    model = first_value(run.metrics.get("timing_model"), run.summary.get("timing_model"))
    scope = first_value(run.metrics.get("depot_routing_scope"), run.summary.get("depot_routing_scope"))
    if "wave_constructed" in str(model) and scope == "global_depot_pool_by_dispatch_wave":
        return "true"
    return "needs_check"


def same_wave_repair_used(run: ExtractedRun) -> str:
    if run.timing_variant != "dispatch_wave_constructed_split_repair":
        return "not_applicable"
    repair_model = first_value(run.metrics.get("timing_repair_model"), run.repair_summary.get("repair_model"))
    return "true" if repair_model == "same_wave_duration_split_with_2opt" else "needs_check"


def build_csv_rows(runs: list[ExtractedRun]) -> list[dict[str, Any]]:
    constructed_rows = constructed_map(runs)
    rows: list[dict[str, Any]] = []

    for run in sorted(runs, key=lambda item: (item.customer_count, item.vehicle_capacity, item.timing_variant)):
        paired_constructed = constructed_rows.get((run.customer_count, run.vehicle_capacity))
        timing_records = run.timing_records
        pre_records = run.pre_repair_records or run.timing_records

        pre_customer_distance = pre_repair_customer_delivery_distance(run)
        post_customer_distance = post_repair_customer_delivery_distance(run)
        pre_total_distance = pre_repair_total_system_distance(run)
        post_total_distance = post_repair_total_system_distance(run)
        row_total_distance = final_total_system_distance(run)
        row_customer_distance = final_customer_delivery_distance(run)

        constructed_total_distance = final_total_system_distance(paired_constructed) if paired_constructed else ""
        split_vs_constructed_delta = numeric_delta(row_total_distance, constructed_total_distance) if run.timing_variant == "dispatch_wave_constructed_split_repair" else ""
        split_vs_constructed_delta_pct = pct_delta(row_total_distance, constructed_total_distance) if run.timing_variant == "dispatch_wave_constructed_split_repair" else ""

        pre_infeasible = pre_summary_value(run, "n_depot_timing_infeasible_routes")
        post_infeasible = post_summary_value(run, "n_depot_timing_infeasible_routes")
        pre_goods_ready = pre_summary_value(run, "n_routes_departing_before_goods_ready")
        post_goods_ready = post_summary_value(run, "n_routes_departing_before_goods_ready")
        pre_workday = pre_summary_value(run, "n_routes_exceeding_working_day")
        post_workday = post_summary_value(run, "n_routes_exceeding_working_day")

        warnings = list(dict.fromkeys(run.warnings))
        if run.timing_variant == "dispatch_wave_constructed_split_repair" and paired_constructed is None:
            warnings.append("missing paired dispatch_wave_constructed row")

        rows.append(
            {
                "customer_count": run.customer_count,
                "vehicle_capacity": run.vehicle_capacity,
                "instance_name": run.instance_name,
                "timing_variant": run.timing_variant,
                "source_folder": run.source_folder,
                "selected_run_timestamp": run.selected_run_timestamp,
                "run_folder_count": run.run_folder_count,
                "latest_available_run_timestamp": run.latest_available_run_timestamp,
                "selected_run_is_latest_available": run.selected_run_is_latest_available,
                "run_classification": run.run_classification,
                "wave_assignment_before_routing": wave_assignment_before_routing(run),
                "same_wave_repair_used": same_wave_repair_used(run),
                "algorithm": first_value(run.metrics.get("algorithm"), run.summary.get("algorithm")),
                "timing_model": first_value(run.metrics.get("timing_model"), run.summary.get("timing_model")),
                "base_timing_model": first_value(run.metrics.get("base_timing_model"), run.summary.get("base_timing_model")),
                "timing_repair_model": first_value(run.metrics.get("timing_repair_model"), run.repair_summary.get("repair_model")),
                "wave_timing_repair_scope": run.metrics.get("wave_timing_repair_scope", ""),
                "wave_repair_max_recursion_depth": first_value(run.metrics.get("wave_repair_max_recursion_depth"), run.config.get("wave_repair_max_recursion_depth"), run.summary.get("wave_repair_max_recursion_depth")),
                "dispatch_waves": serialize(first_value(run.metrics.get("dispatch_waves"), run.config.get("dispatch_waves"))),
                "dispatch_wave_labels": serialize(first_value(run.metrics.get("dispatch_wave_labels"), run.summary.get("dispatch_wave_labels"))),
                "working_day_end_time": first_value(run.metrics.get("working_day_end_time"), run.config.get("working_day_end_time"), run.summary.get("working_day_end_time")),
                "working_day_end_time_label": first_value(run.metrics.get("working_day_end_time_label"), run.summary.get("working_day_end_time_label")),
                "service_time_per_customer_hours_estimate": estimate_service_time_per_customer(timing_records or pre_records),
                "average_speed_estimate": first_value(run.config.get("average_speed"), run.metrics.get("average_speed"), estimate_average_speed(timing_records or pre_records)),
                "depot_handling_time": first_value(run.metrics.get("depot_handling_time"), run.config.get("depot_handling_time")),
                "depot_handling_time_minutes": first_value(run.metrics.get("depot_handling_time_minutes"), run.summary.get("depot_handling_time_minutes")),
                "supplier_arrival_window_start": first_value(run.metrics.get("supplier_arrival_start_time"), run.config.get("supplier_arrival_start_time")),
                "supplier_arrival_window_start_label": first_value(run.metrics.get("supplier_arrival_start_time_label"), run.summary.get("supplier_arrival_start_time_label")),
                "supplier_arrival_window_end": first_value(run.metrics.get("supplier_arrival_end_time"), run.config.get("supplier_arrival_end_time")),
                "supplier_arrival_window_end_label": first_value(run.metrics.get("supplier_arrival_end_time_label"), run.summary.get("supplier_arrival_end_time_label")),
                "arrival_time_step_minutes": first_value(run.metrics.get("arrival_time_step_minutes"), run.config.get("arrival_time_step_minutes")),
                "depot_arrival_seed": first_value(run.metrics.get("depot_arrival_seed"), run.config.get("depot_arrival_seed")),
                "n_suppliers": first_value(run.metrics.get("n_suppliers"), run.summary.get("n_suppliers"), run.config.get("n_suppliers")),
                "direct_delivery_threshold": first_value(run.metrics.get("direct_delivery_threshold"), run.summary.get("direct_delivery_threshold"), run.config.get("direct_delivery_threshold")),
                "seed": first_value(run.metrics.get("seed"), run.summary.get("seed"), run.config.get("seed")),
                "grid_size": run.config.get("grid_size", ""),
                "n_supplier_direct_customers": first_value(run.metrics.get("n_supplier_direct_customers"), run.summary.get("n_supplier_direct_customers")),
                "n_depot_customers": first_value(run.metrics.get("n_depot_customers"), run.summary.get("n_depot_customers")),
                "supplier_direct_routing_scope": first_value(run.metrics.get("supplier_direct_routing_scope"), run.summary.get("supplier_direct_routing_scope")),
                "depot_routing_scope": first_value(run.metrics.get("depot_routing_scope"), run.summary.get("depot_routing_scope")),
                "customers_per_wave": serialize(first_value(run.metrics.get("customers_per_wave_label"), run.wave_assignment_summary.get("customers_per_wave_label"))),
                "routes_per_wave": serialize(first_value(run.metrics.get("routes_per_wave_label"), run.timing_summary.get("routes_per_wave_label"), run.summary.get("routes_per_wave_label"))),
                "customer_delivery_distance": row_customer_distance,
                "supplier_depot_replenishment_distance": first_value(run.metrics.get("supplier_depot_replenishment_distance"), run.metrics.get("total_first_echelon_distance"), run.summary.get("supplier_depot_replenishment_distance")),
                "total_system_distance": row_total_distance,
                "pre_repair_customer_delivery_distance": pre_customer_distance,
                "post_repair_customer_delivery_distance": post_customer_distance,
                "pre_repair_total_system_distance": pre_total_distance,
                "post_repair_total_system_distance": post_total_distance,
                "pre_repair_depot_outbound_distance": first_value(run.metrics.get("depot_distance_before_wave_repair"), run.repair_summary.get("depot_distance_before_wave_repair")),
                "post_repair_depot_outbound_distance": first_value(run.metrics.get("depot_distance_after_wave_repair"), run.repair_summary.get("depot_distance_after_wave_repair")),
                "depot_outbound_distance_change_after_repair": repair_delta(run),
                "distance_change_after_repair": numeric_delta(post_total_distance, pre_total_distance),
                "distance_change_after_repair_pct": pct_delta(post_total_distance, pre_total_distance),
                "matched_constructed_total_system_distance": constructed_total_distance,
                "split_vs_constructed_total_system_distance_delta": split_vs_constructed_delta,
                "split_vs_constructed_total_system_distance_delta_pct": split_vs_constructed_delta_pct,
                "total_routes": first_value(run.metrics.get("trips"), run.summary.get("trips")),
                "pre_repair_total_routes": pre_repair_total_routes(run),
                "post_repair_total_routes": post_repair_total_routes(run),
                "depot_routes": timing_routes(run),
                "pre_repair_depot_routes": pre_repair_depot_routes(run),
                "post_repair_depot_routes": post_repair_depot_routes(run),
                "route_count_change_after_repair": numeric_delta(post_repair_total_routes(run), pre_repair_total_routes(run)),
                "depot_route_count_change_after_repair": numeric_delta(post_repair_depot_routes(run), pre_repair_depot_routes(run)),
                "timing_routes_checked": timing_routes(run),
                "timing_feasible_routes": first_value(run.metrics.get("n_depot_timing_feasible_routes"), run.timing_summary.get("n_depot_timing_feasible_routes")),
                "timing_infeasible_routes": first_value(run.metrics.get("n_depot_timing_infeasible_routes"), run.timing_summary.get("n_depot_timing_infeasible_routes")),
                "pre_repair_timing_infeasible_routes": pre_infeasible,
                "post_repair_timing_infeasible_routes": post_infeasible,
                "infeasible_route_change_after_repair": numeric_delta(post_infeasible, pre_infeasible),
                "routes_before_goods_ready": first_value(run.metrics.get("n_routes_departing_before_goods_ready"), run.timing_summary.get("n_routes_departing_before_goods_ready")),
                "pre_repair_routes_before_goods_ready": pre_goods_ready,
                "post_repair_routes_before_goods_ready": post_goods_ready,
                "goods_ready_violation_change_after_repair": numeric_delta(post_goods_ready, pre_goods_ready),
                "routes_exceeding_workday": first_value(run.metrics.get("n_routes_exceeding_working_day"), run.timing_summary.get("n_routes_exceeding_working_day")),
                "pre_repair_routes_exceeding_workday": pre_workday,
                "post_repair_routes_exceeding_workday": post_workday,
                "workday_violation_change_after_repair": numeric_delta(post_workday, pre_workday),
                "routes_without_feasible_wave": first_value(run.metrics.get("n_routes_without_feasible_wave"), run.timing_summary.get("n_routes_without_feasible_wave")),
                "customers_without_feasible_wave": first_value(run.metrics.get("n_depot_customers_without_feasible_wave"), run.wave_assignment_summary.get("n_depot_customers_without_feasible_wave"), run.summary.get("n_depot_customers_without_feasible_wave")),
                "infeasible_timing_route_ids": serialize(first_value(run.metrics.get("infeasible_timing_route_ids"), run.timing_summary.get("infeasible_timing_route_ids"))),
                "infeasible_timing_customers": serialize(first_value(run.metrics.get("infeasible_timing_customers"), run.timing_summary.get("infeasible_timing_customers"))),
                "latest_finish_time": latest_finish_time(run),
                "latest_finish_time_label": latest_finish_label(run),
                "pre_repair_latest_finish_time": pre_summary_value(run, "latest_depot_route_finish_time"),
                "pre_repair_latest_finish_time_label": pre_summary_value(run, "latest_depot_route_finish_time_label"),
                "post_repair_latest_finish_time": post_summary_value(run, "latest_depot_route_finish_time"),
                "post_repair_latest_finish_time_label": post_summary_value(run, "latest_depot_route_finish_time_label"),
                "max_route_duration": first_value(run.metrics.get("max_depot_route_duration_hours"), run.timing_summary.get("max_depot_route_duration_hours")),
                "avg_route_duration": first_value(run.metrics.get("avg_depot_route_duration_hours"), run.timing_summary.get("avg_depot_route_duration_hours")),
                "avg_waiting_time": first_value(run.metrics.get("avg_waiting_time_minutes"), run.timing_summary.get("avg_waiting_time_minutes"), run.summary.get("avg_waiting_time_minutes")),
                "max_waiting_time": first_value(run.metrics.get("max_waiting_time_minutes"), run.timing_summary.get("max_waiting_time_minutes"), run.summary.get("max_waiting_time_minutes")),
                "repair_attempts": first_value(run.metrics.get("n_wave_timing_repair_attempts"), run.repair_summary.get("n_wave_timing_repair_attempts")),
                "successful_repairs": first_value(run.metrics.get("n_wave_timing_successful_repairs"), run.repair_summary.get("n_wave_timing_successful_repairs")),
                "unresolved_repairs": first_value(run.metrics.get("n_wave_timing_unresolved_repairs"), run.repair_summary.get("n_wave_timing_unresolved_repairs")),
                "unresolved_customers": serialize(first_value(run.metrics.get("unresolved_customers_after_wave_repair"), run.repair_summary.get("unresolved_customers_after_wave_repair"))),
                "n_unresolved_customers": first_value(run.metrics.get("n_unresolved_customers_after_wave_repair"), run.repair_summary.get("n_unresolved_customers_after_wave_repair")),
                "routes_added_by_repair": routes_added_by_repair(run),
                "overall_timing_feasible": first_value(run.metrics.get("overall_feasible_with_dispatch_waves"), run.summary.get("overall_feasible_with_dispatch_waves")),
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
                "customer_wave_records_count": len(run.customer_wave_records),
                "pre_repair_route_records_count": len(pre_records),
                "repair_records_count": len(run.repair_records),
                "best_n_remove": "",
                "tested_n_remove_values": "",
                "n_remove_applicability": "not_applicable_section_6_6_is_not_lns",
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


def split_outcome_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        "split_rows": 0,
        "feasible_after_repair": 0,
        "infeasible_after_repair": 0,
        "unresolved_repair_rows": 0,
        "rows_with_repairs_attempted": 0,
        "rows_with_goods_ready_violations_after_repair": 0,
        "rows_with_workday_violations_after_repair": 0,
    }
    for row in rows:
        if row["timing_variant"] != "dispatch_wave_constructed_split_repair":
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
        goods_ready = as_int(row.get("post_repair_routes_before_goods_ready"))
        if goods_ready and goods_ready > 0:
            counts["rows_with_goods_ready_violations_after_repair"] += 1
        workday = as_int(row.get("post_repair_routes_exceeding_workday"))
        if workday and workday > 0:
            counts["rows_with_workday_violations_after_repair"] += 1
    return counts


def write_summary(root: Path, rows: list[dict[str, Any]], runs: list[ExtractedRun], archive_info: dict[str, Any]) -> Path:
    output_dir = root / OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / OUTPUT_SUMMARY

    counts = variant_counts(rows)
    warnings = warning_rows(rows)
    split_counts = split_outcome_counts(rows)
    run_counts_by_variant: dict[str, list[int]] = {}
    for run in runs:
        run_counts_by_variant.setdefault(run.timing_variant, []).append(run.run_folder_count)

    lines: list[str] = [
        "# Section 6.6 Dispatch-Wave Timing and Same-Wave Split Repair Extraction Summary",
        "",
        "## Source Folders",
        "",
    ]
    for spec in MAIN_FOLDER_SPECS:
        lines.append(f"- `{spec['relative_path']}`: {spec['description']}")
    lines.append(f"- `{ARCHIVE_FOLDER_SPEC['relative_path']}`: archive/development only; not included in the main CSV")

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
            "- The extractor selects the latest `run_*` folder that matches the Section 6.6 base speed/wave parameters for every instance folder.",
            "- Expected Section 6.6 parameters are speed 30 and dispatch waves 09:00, 11:00, 13:00, 15:00.",
            "- If the newest timestamped run has the wrong speed or dispatch-wave list, it is skipped and recorded in the warnings/status notes.",
            "- Only the two wave-aware final folders are written to the main CSV.",
            "- The older route-first folder is inspected only as archive/development evidence and is not included in the main CSV.",
            "- The extractor deliberately excludes fixed timing, speed40 sensitivity, 14:00-wave sensitivity, time-aware LNS, and non-timing LNS folders.",
            "- `best_n_remove` and `tested_n_remove_values` are left blank because Section 6.6 is a timing-baseline section, not an LNS section.",
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
    for spec in MAIN_FOLDER_SPECS:
        missing = missing_instances(rows, spec["timing_variant"])
        if missing:
            lines.append(f"- Missing `{spec['timing_variant']}` rows: {', '.join(missing)}")
        else:
            lines.append(f"- Missing `{spec['timing_variant']}` rows: none")

    lines.extend(
        [
            "",
            "## Route-First Dispatch-Wave Archive Folder",
            "",
            f"- Folder: `{archive_info['folder']}`",
            f"- Exists: {archive_info['exists']}",
            f"- Instance folders detected: {archive_info['instance_count']}",
            f"- Timestamped runs detected: {archive_info['run_count']}",
            f"- Instances with multiple timestamped runs: {archive_info['instances_with_multiple_runs']}",
            "- Archive/development rows written to main CSV: 0",
            "",
            "## Pre-Repair Versus Post-Repair Handling",
            "",
            "- Wave-aware construction rows use final construction outputs as the pre-repair baseline.",
            "- Split-repair rows keep pre-repair timing values from `depot_timing_wave_pre_repair_summary.json` and `depot_timing_wave_pre_repair_records.json`.",
            "- Split-repair rows keep post-repair timing values from `depot_timing_wave_summary.json` and `depot_timing_wave_records.json`.",
            "- `depot_distance_before_wave_repair` and `depot_distance_after_wave_repair` are stored as depot-outbound repair distances, not full system distances.",
            "- Full pre-repair customer/system distances are derived from the final saved distances minus `distance_delta_after_wave_repair`; full post-repair customer/system distances use the final saved metrics.",
            "- Derived delta fields compare post-repair values against pre-repair values only when both values are available.",
            "",
            "## Same-Wave Split Repair Outcome Counts",
            "",
        ]
    )
    for key, value in split_counts.items():
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
        lines.append(f"- Rows with warnings/status notes: {len(warnings)}")
        for row in warnings[:100]:
            lines.append(
                f"- `{row['timing_variant']}` `{row['instance_name']}` `{row['selected_run_timestamp']}`: {row['notes_or_warnings']}"
            )
        if len(warnings) > 100:
            lines.append(f"- Additional warning rows omitted from summary: {len(warnings) - 100}")
    else:
        lines.append("- Rows with warnings/status notes: 0")

    lines.extend(
        [
            "",
            "## Thesis Use Notes",
            "",
            "- Use this extraction for Section 6.6 only.",
            "- Treat dispatch-wave construction as customer wave assignment before depot routing.",
            "- Treat same-wave split repair as a route-level timing repair inside the assigned dispatch wave.",
            "- Do not describe this as fixed timing, speed sensitivity, 14:00-wave sensitivity, or time-aware LNS.",
            "- Do not describe route-first dispatch-wave results as final evidence.",
            "- Remaining infeasibility after same-wave split repair should remain visible in the thesis discussion.",
        ]
    )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def main() -> None:
    root = project_root()
    runs: list[ExtractedRun] = []
    for spec in MAIN_FOLDER_SPECS:
        runs.extend(load_folder(root, spec))

    rows = build_csv_rows(runs)
    csv_path = write_csv(root, rows)
    summary_path = write_summary(root, rows, runs, count_archive_runs(root))

    print(f"Wrote {csv_path}")
    print(f"Wrote {summary_path}")
    print(f"Rows: {len(rows)}")
    print(f"Warnings: {len(warning_rows(rows))}")


if __name__ == "__main__":
    main()
