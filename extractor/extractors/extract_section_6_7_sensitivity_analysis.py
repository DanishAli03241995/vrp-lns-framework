#!/usr/bin/env python3
"""Extract Chapter 6.7 dispatch-wave sensitivity analysis results."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


INSTANCE_RE = re.compile(r"^(?P<customers>\d+)c_cap(?P<capacity>\d+)$")

OUTPUT_DIR = Path("extractor/section 6.7")
OUTPUT_LONG_CSV = "section_6_7_sensitivity_analysis_table.csv"
OUTPUT_SPEED_CSV = "section_6_7_speed_sensitivity_comparison.csv"
OUTPUT_14WAVE_CSV = "section_6_7_14wave_sensitivity_comparison.csv"
OUTPUT_SUMMARY = "section_6_7_sensitivity_analysis_summary.md"

EXPECTED_CUSTOMER_COUNTS = (20, 40, 60, 80, 100, 150, 200)
EXPECTED_CAPACITIES = (15, 25, 35)

BASE_WAVES = (9.0, 11.0, 13.0, 15.0)
WAVE14_WAVES = (9.0, 11.0, 13.0, 14.0, 15.0)
SPEED_TOLERANCE = 0.25
DISTANCE_TOLERANCE = 1e-6

SCENARIO_SPECS = [
    {
        "timing_scenario": "base_speed30",
        "sensitivity_dimension": "reference",
        "scenario_role": "reference",
        "relative_path": Path("results/hybrid_supplier_customer_kmeans_timing_waves_constructed_split_v1"),
        "expected_speed": 30.0,
        "expected_waves": BASE_WAVES,
        "description": "Base dispatch-wave split-repair reference with speed 30 and waves 09/11/13/15",
    },
    {
        "timing_scenario": "speed40",
        "sensitivity_dimension": "speed",
        "scenario_role": "sensitivity_variant",
        "relative_path": Path("results/hybrid_supplier_customer_kmeans_timing_waves_constructed_split_v1_40_speed"),
        "expected_speed": 40.0,
        "expected_waves": BASE_WAVES,
        "description": "Speed sensitivity with average speed 40 and base dispatch waves",
    },
    {
        "timing_scenario": "added_14_wave",
        "sensitivity_dimension": "dispatch_policy",
        "scenario_role": "sensitivity_variant",
        "relative_path": Path("results/hybrid_supplier_customer_kmeans_timing_waves_constructed_split_14wave_v1"),
        "expected_speed": 30.0,
        "expected_waves": WAVE14_WAVES,
        "description": "Dispatch-policy sensitivity with speed 30 and an added 14:00 wave",
    },
]

EXCLUDED_FOLDERS = [
    "results/hybrid_supplier_customer_kmeans_timing_fixed_v1",
    "results/hybrid_supplier_customer_kmeans_timing_fixed_split_v1",
    "results/hybrid_supplier_customer_kmeans_timing_waves_constructed_v1",
    "results/hybrid_supplier_customer_kmeans_timing_waves_v1",
    "results/lns_timing_*",
    "results/lns_operator_*",
]


@dataclass(frozen=True)
class ExtractedRun:
    customer_count: int
    vehicle_capacity: int
    instance_name: str
    timing_scenario: str
    sensitivity_dimension: str
    scenario_role: str
    source_folder: str
    expected_speed: float
    expected_waves: tuple[float, ...]
    selected_run_timestamp: str
    run_folder_count: int
    latest_available_run_timestamp: str
    selected_run_is_latest_available: bool
    run_classification: str
    run_dir: Path | None
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
    for value in values:
        if value not in ("", None):
            return value
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


def dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(item for item in items if item))


def boolish(raw: Any) -> Any:
    if isinstance(raw, bool):
        return raw
    return raw


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


def estimate_service_time_per_customer(records: list[dict[str, Any]]) -> float | str:
    values: list[float] = []
    for record in records:
        service_time = as_float(record.get("route_service_time_hours"))
        customer_count = as_float(record.get("n_customers"))
        if service_time is None or customer_count in (None, 0):
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
        if distance is None or travel_time in (None, 0):
            continue
        values.append(distance / travel_time)
    if not values:
        return ""
    return sum(values) / len(values)


def average_speed_value(run: ExtractedRun) -> tuple[Any, str]:
    config_speed = first_value(run.config.get("average_speed"), "")
    if config_speed != "":
        return config_speed, "config_used.json"
    metrics_speed = first_value(run.metrics.get("average_speed"), "")
    if metrics_speed != "":
        return metrics_speed, "metrics.json"
    estimate = estimate_average_speed(run.timing_records or run.pre_repair_records)
    if estimate != "":
        return estimate, "route_record_estimate"
    return "", "missing"


def dispatch_waves_value(run: ExtractedRun) -> tuple[Any, str]:
    config_waves = first_value(run.config.get("dispatch_waves"), "")
    if config_waves != "":
        return config_waves, "config_used.json"
    metrics_waves = first_value(run.metrics.get("dispatch_waves"), "")
    if metrics_waves != "":
        return metrics_waves, "metrics.json"
    return "", "missing"


def dispatch_wave_labels(run: ExtractedRun) -> Any:
    return first_value(
        run.metrics.get("dispatch_wave_labels"),
        run.summary.get("dispatch_wave_labels"),
    )


def scenario_parameter_check(run: ExtractedRun) -> tuple[str, list[str]]:
    warnings: list[str] = []
    speed, speed_source = average_speed_value(run)
    waves, wave_source = dispatch_waves_value(run)
    speed_float = as_float(speed)
    wave_tuple = normalize_waves(waves)

    speed_ok = speed_float is not None and abs(speed_float - run.expected_speed) <= SPEED_TOLERANCE
    waves_ok = wave_tuple == run.expected_waves

    if speed_source == "missing":
        warnings.append("average speed missing")
    elif not speed_ok:
        warnings.append(f"average speed mismatch expected {run.expected_speed}")

    if wave_source == "missing":
        warnings.append("dispatch wave schedule missing")
    elif not waves_ok:
        warnings.append(f"dispatch wave schedule mismatch expected {run.expected_waves}")

    if run.timing_scenario in ("base_speed30", "speed40") and wave_tuple and 14.0 in wave_tuple:
        warnings.append("14:00 wave present outside 14-wave scenario")
    if run.timing_scenario == "added_14_wave" and wave_tuple and 14.0 not in wave_tuple:
        warnings.append("14:00 wave missing from 14-wave scenario")
    if run.timing_scenario == "added_14_wave" and speed_float is not None and abs(speed_float - 40.0) <= SPEED_TOLERANCE:
        warnings.append("speed40 mixed into 14-wave scenario")

    if speed_ok and waves_ok:
        return "ok", warnings
    if speed_source == "missing":
        return "missing_speed", warnings
    if wave_source == "missing":
        return "missing_wave_schedule", warnings
    if not speed_ok:
        return "speed_mismatch", warnings
    if not waves_ok:
        return "wave_schedule_mismatch", warnings
    return "needs_check", warnings


def quick_candidate_parameter_check(run_dir: Path, spec: dict[str, Any]) -> tuple[bool, list[str]]:
    config, config_warning = read_json_dict(run_dir / "config_used.json")
    metrics, metrics_warning = read_json_dict(run_dir / "metrics.json")
    timing_records, records_warning = read_json_list(run_dir / "depot_timing_wave_records.json")
    pre_records, pre_records_warning = read_json_list(run_dir / "depot_timing_wave_pre_repair_records.json")

    warnings = [item for item in (config_warning, metrics_warning, records_warning, pre_records_warning) if item]

    speed = first_value(config.get("average_speed"), metrics.get("average_speed"))
    speed_source = "saved"
    if speed == "":
        speed = estimate_average_speed(timing_records or pre_records)
        speed_source = "route_record_estimate" if speed != "" else "missing"

    waves = first_value(config.get("dispatch_waves"), metrics.get("dispatch_waves"))
    wave_tuple = normalize_waves(waves)
    speed_float = as_float(speed)

    expected_speed = float(spec["expected_speed"])
    expected_waves = tuple(spec["expected_waves"])

    speed_ok = speed_float is not None and abs(speed_float - expected_speed) <= SPEED_TOLERANCE
    waves_ok = wave_tuple == expected_waves

    if speed_source == "missing":
        warnings.append("candidate average speed missing")
    elif not speed_ok:
        warnings.append(f"candidate average speed mismatch expected {expected_speed}")
    if wave_tuple is None:
        warnings.append("candidate dispatch waves missing")
    elif not waves_ok:
        warnings.append(f"candidate dispatch waves mismatch expected {expected_waves}")

    return speed_ok and waves_ok, warnings


def select_latest_matching_run(instance_dir: Path, spec: dict[str, Any]) -> tuple[Path | None, int, Path | None, list[str]]:
    runs = timestamped_runs(instance_dir)
    if not runs:
        return None, 0, None, ["missing run folder"]

    latest_available = runs[-1]
    rejected_later: list[str] = []
    for run_dir in reversed(runs):
        ok, candidate_warnings = quick_candidate_parameter_check(run_dir, spec)
        if ok:
            warnings: list[str] = []
            if run_dir != latest_available:
                rejected_later = [item.name for item in runs if item > run_dir]
                warnings.append(
                    "selected latest scenario-parameter-matching run; newer mismatched run(s) ignored: "
                    + ", ".join(rejected_later)
                )
            return run_dir, len(runs), latest_available, warnings
        rejected_later.append(f"{run_dir.name} ({'; '.join(candidate_warnings)})")

    warnings = [
        "no run matched expected scenario parameters; selected latest available run",
        "candidate parameter issues: " + " | ".join(rejected_later[:5]),
    ]
    return latest_available, len(runs), latest_available, warnings


def final_customer_delivery_distance(run: ExtractedRun) -> Any:
    return first_value(run.metrics.get("post_reloc_2opt_distance"), run.summary.get("final_distance"))


def final_total_system_distance(run: ExtractedRun) -> Any:
    return first_value(
        run.metrics.get("post_reloc_2opt_total_system_distance"),
        run.summary.get("final_total_system_distance"),
    )


def supplier_depot_replenishment_distance(run: ExtractedRun) -> Any:
    return first_value(
        run.metrics.get("supplier_depot_replenishment_distance"),
        run.metrics.get("total_first_echelon_distance"),
        run.summary.get("supplier_depot_replenishment_distance"),
    )


def repair_delta(run: ExtractedRun) -> Any:
    return first_value(
        run.metrics.get("distance_delta_after_wave_repair"),
        run.repair_summary.get("distance_delta_after_wave_repair"),
    )


def pre_repair_customer_delivery_distance(run: ExtractedRun) -> Any:
    final_value = as_float(final_customer_delivery_distance(run))
    delta = as_float(repair_delta(run))
    if final_value is None or delta is None:
        return ""
    return final_value - delta


def pre_repair_total_system_distance(run: ExtractedRun) -> Any:
    final_value = as_float(final_total_system_distance(run))
    delta = as_float(repair_delta(run))
    if final_value is None or delta is None:
        return ""
    return final_value - delta


def timing_routes(run: ExtractedRun) -> Any:
    return first_value(run.metrics.get("n_depot_timing_routes"), run.timing_summary.get("n_depot_timing_routes"))


def pre_summary_value(run: ExtractedRun, key: str) -> Any:
    return first_value(run.pre_repair_summary.get(key), run.metrics.get(key))


def post_summary_value(run: ExtractedRun, key: str) -> Any:
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
    final_routes = as_int(first_value(run.metrics.get("trips"), run.summary.get("trips")))
    added_routes = as_int(routes_added_by_repair(run))
    if final_routes is None or added_routes is None:
        return ""
    return final_routes - added_routes


def post_repair_total_routes(run: ExtractedRun) -> Any:
    return first_value(run.metrics.get("trips"), run.summary.get("trips"))


def pre_repair_depot_routes(run: ExtractedRun) -> Any:
    return first_value(
        run.metrics.get("n_depot_timing_routes_before_repair"),
        run.repair_summary.get("n_depot_timing_routes_before_repair"),
        run.pre_repair_summary.get("n_depot_timing_routes"),
    )


def post_repair_depot_routes(run: ExtractedRun) -> Any:
    return first_value(
        run.metrics.get("n_depot_timing_routes_after_repair"),
        run.repair_summary.get("n_depot_timing_routes_after_repair"),
        timing_routes(run),
    )


def hybrid_system_distance_check(run: ExtractedRun) -> str:
    customer_distance = as_float(final_customer_delivery_distance(run))
    replenishment = as_float(supplier_depot_replenishment_distance(run))
    total = as_float(final_total_system_distance(run))
    if customer_distance is None or replenishment is None or total is None:
        return "missing"
    if abs((customer_distance + replenishment) - total) <= DISTANCE_TOLERANCE:
        return "ok"
    return "mismatch"


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
        "n_routes_departing_before_goods_ready",
        "n_routes_exceeding_working_day",
        "latest_depot_route_finish_time",
    ]
    for key in required_common:
        if key not in run.metrics and key not in run.summary and key not in run.timing_summary:
            warnings.append(f"missing metric {key}")

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

    if not run.wave_assignment_summary:
        warnings.append("missing customer wave assignment summary")
    if not run.customer_wave_records:
        warnings.append("missing customer wave timing records")
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

    if run.run_dir is not None and not (run.run_dir / "route_plot_dispatch_wave_constructed_split_repair.png").exists():
        warnings.append("missing route_plot_dispatch_wave_constructed_split_repair.png")

    depot_scope = first_value(run.metrics.get("depot_routing_scope"), run.summary.get("depot_routing_scope"))
    if depot_scope not in ("", "global_depot_pool_by_dispatch_wave"):
        warnings.append("depot routing scope is not global_depot_pool_by_dispatch_wave")

    repair_model = first_value(run.metrics.get("timing_repair_model"), run.repair_summary.get("repair_model"))
    if repair_model != "same_wave_duration_split_with_2opt":
        warnings.append("same-wave split repair model not confirmed")

    replenishment = as_float(supplier_depot_replenishment_distance(run))
    depot_customers = as_int(run.metrics.get("n_depot_customers"))
    if depot_customers and (replenishment is None or replenishment <= 0):
        warnings.append("depot customers exist but supplier-depot replenishment distance is missing or zero")

    if hybrid_system_distance_check(run) == "mismatch":
        warnings.append("hybrid system distance mismatch")

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

    _, parameter_warnings = scenario_parameter_check(run)
    warnings.extend(parameter_warnings)

    return warnings


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
            if warning:
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
        timing_scenario=str(spec["timing_scenario"]),
        sensitivity_dimension=str(spec["sensitivity_dimension"]),
        scenario_role=str(spec["scenario_role"]),
        source_folder=str(spec["relative_path"]),
        expected_speed=float(spec["expected_speed"]),
        expected_waves=tuple(spec["expected_waves"]),
        selected_run_timestamp=selected_run_timestamp,
        run_folder_count=run_count,
        latest_available_run_timestamp=latest_available_run_dir.name if latest_available_run_dir is not None else "",
        selected_run_is_latest_available=run_dir == latest_available_run_dir if run_dir is not None else False,
        run_classification="main" if run_dir is not None else "needs_check",
        run_dir=run_dir,
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
            "warnings": dedupe([*warnings, *metric_warnings(run)]),
        }
    )


def missing_folder_run(spec: dict[str, Any]) -> ExtractedRun:
    return ExtractedRun(
        customer_count=0,
        vehicle_capacity=0,
        instance_name="",
        timing_scenario=str(spec["timing_scenario"]),
        sensitivity_dimension=str(spec["sensitivity_dimension"]),
        scenario_role=str(spec["scenario_role"]),
        source_folder=str(spec["relative_path"]),
        expected_speed=float(spec["expected_speed"]),
        expected_waves=tuple(spec["expected_waves"]),
        selected_run_timestamp="",
        run_folder_count=0,
        latest_available_run_timestamp="",
        selected_run_is_latest_available=False,
        run_classification="needs_check",
        run_dir=None,
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


def load_folder(root: Path, spec: dict[str, Any]) -> list[ExtractedRun]:
    folder = root / spec["relative_path"]
    if not folder.exists():
        return [missing_folder_run(spec)]

    runs: list[ExtractedRun] = []
    for instance_dir in sorted(p for p in folder.iterdir() if p.is_dir()):
        if parse_instance_name(instance_dir) is None:
            continue
        runs.append(load_instance(spec, instance_dir))
    return runs


def build_row(run: ExtractedRun) -> dict[str, Any]:
    speed, speed_source = average_speed_value(run)
    waves, waves_source = dispatch_waves_value(run)
    waves_tuple = normalize_waves(waves)
    parameter_check, parameter_warnings = scenario_parameter_check(run)

    pre_customer_distance = pre_repair_customer_delivery_distance(run)
    post_customer_distance = final_customer_delivery_distance(run)
    pre_total_distance = pre_repair_total_system_distance(run)
    post_total_distance = final_total_system_distance(run)

    pre_infeasible = pre_summary_value(run, "n_depot_timing_infeasible_routes")
    post_infeasible = post_summary_value(run, "n_depot_timing_infeasible_routes")
    pre_goods_ready = pre_summary_value(run, "n_routes_departing_before_goods_ready")
    post_goods_ready = post_summary_value(run, "n_routes_departing_before_goods_ready")
    pre_workday = pre_summary_value(run, "n_routes_exceeding_working_day")
    post_workday = post_summary_value(run, "n_routes_exceeding_working_day")

    warnings = dedupe([*run.warnings, *parameter_warnings])

    return {
        "customer_count": run.customer_count,
        "vehicle_capacity": run.vehicle_capacity,
        "instance_name": run.instance_name,
        "timing_scenario": run.timing_scenario,
        "sensitivity_dimension": run.sensitivity_dimension,
        "scenario_role": run.scenario_role,
        "source_folder": run.source_folder,
        "selected_run_timestamp": run.selected_run_timestamp,
        "run_folder_count": run.run_folder_count,
        "latest_available_run_timestamp": run.latest_available_run_timestamp,
        "selected_run_is_latest_available": run.selected_run_is_latest_available,
        "run_classification": run.run_classification,
        "algorithm": first_value(run.metrics.get("algorithm"), run.summary.get("algorithm")),
        "timing_model": first_value(run.metrics.get("timing_model"), run.summary.get("timing_model")),
        "base_timing_model": first_value(run.metrics.get("base_timing_model"), run.summary.get("base_timing_model")),
        "timing_repair_model": first_value(run.metrics.get("timing_repair_model"), run.repair_summary.get("repair_model")),
        "wave_timing_repair_scope": run.metrics.get("wave_timing_repair_scope", ""),
        "construction": first_value(run.metrics.get("construction"), run.summary.get("construction")),
        "local_search": first_value(run.metrics.get("local_search"), run.summary.get("local_search")),
        "supplier_direct_routing_scope": first_value(run.metrics.get("supplier_direct_routing_scope"), run.summary.get("supplier_direct_routing_scope")),
        "depot_routing_scope": first_value(run.metrics.get("depot_routing_scope"), run.summary.get("depot_routing_scope")),
        "relocation_scope": first_value(run.metrics.get("relocation_scope"), run.summary.get("relocation_scope")),
        "dispatch_waves": serialize(waves),
        "dispatch_wave_labels": serialize(dispatch_wave_labels(run)),
        "n_dispatch_waves": len(waves_tuple) if waves_tuple is not None else "",
        "has_14_wave": bool(waves_tuple and 14.0 in waves_tuple),
        "dispatch_waves_source": waves_source,
        "working_day_end_time": first_value(run.metrics.get("working_day_end_time"), run.config.get("working_day_end_time"), run.summary.get("working_day_end_time")),
        "working_day_end_time_label": first_value(run.metrics.get("working_day_end_time_label"), run.summary.get("working_day_end_time_label")),
        "average_speed": speed,
        "average_speed_source": speed_source,
        "expected_average_speed": run.expected_speed,
        "service_time_per_customer": estimate_service_time_per_customer(run.timing_records or run.pre_repair_records),
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
        "customers_per_wave": serialize(first_value(run.metrics.get("customers_per_wave_label"), run.wave_assignment_summary.get("customers_per_wave_label"))),
        "routes_per_wave": serialize(first_value(run.metrics.get("routes_per_wave_label"), run.timing_summary.get("routes_per_wave_label"), run.summary.get("routes_per_wave_label"))),
        "customer_delivery_distance": post_customer_distance,
        "supplier_depot_replenishment_distance": supplier_depot_replenishment_distance(run),
        "total_first_echelon_distance": first_value(run.metrics.get("total_first_echelon_distance"), supplier_depot_replenishment_distance(run)),
        "total_system_distance": post_total_distance,
        "pre_repair_customer_delivery_distance": pre_customer_distance,
        "post_repair_customer_delivery_distance": post_customer_distance,
        "pre_repair_total_system_distance": pre_total_distance,
        "post_repair_total_system_distance": post_total_distance,
        "pre_repair_depot_outbound_distance": first_value(run.metrics.get("depot_distance_before_wave_repair"), run.repair_summary.get("depot_distance_before_wave_repair")),
        "post_repair_depot_outbound_distance": first_value(run.metrics.get("depot_distance_after_wave_repair"), run.repair_summary.get("depot_distance_after_wave_repair")),
        "depot_outbound_distance_change_after_repair": repair_delta(run),
        "distance_change_after_repair": numeric_delta(post_total_distance, pre_total_distance),
        "distance_change_after_repair_pct": pct_delta(post_total_distance, pre_total_distance),
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
        "routes_exceeding_workday": first_value(run.metrics.get("n_routes_exceeding_working_day"), run.timing_summary.get("n_routes_exceeding_working_day")),
        "pre_repair_routes_exceeding_workday": pre_workday,
        "post_repair_routes_exceeding_workday": post_workday,
        "routes_without_feasible_wave": first_value(run.metrics.get("n_routes_without_feasible_wave"), run.timing_summary.get("n_routes_without_feasible_wave")),
        "customers_without_feasible_wave": first_value(run.metrics.get("n_depot_customers_without_feasible_wave"), run.wave_assignment_summary.get("n_depot_customers_without_feasible_wave"), run.summary.get("n_depot_customers_without_feasible_wave")),
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
        "unresolved_customers_count": first_value(run.metrics.get("n_unresolved_customers_after_wave_repair"), run.repair_summary.get("n_unresolved_customers_after_wave_repair")),
        "unresolved_customers": serialize(first_value(run.metrics.get("unresolved_customers_after_wave_repair"), run.repair_summary.get("unresolved_customers_after_wave_repair"))),
        "unresolved_route_ids": serialize(first_value(run.metrics.get("unresolved_route_ids_after_wave_repair"), run.repair_summary.get("unresolved_route_ids_after_wave_repair"))),
        "routes_added_by_repair": routes_added_by_repair(run),
        "overall_timing_feasible": first_value(run.metrics.get("overall_feasible_with_dispatch_waves"), run.summary.get("overall_feasible_with_dispatch_waves")),
        "depot_timing_feasibility": first_value(run.metrics.get("depot_timing_feasibility"), run.timing_summary.get("depot_timing_feasibility")),
        "capacity_feasible": first_value(run.metrics.get("capacity_feasibility"), run.summary.get("feasible")),
        "customer_coverage_feasible": first_value(run.metrics.get("all_customers_served"), run.summary.get("customers_served")),
        "supplier_feasible": run.metrics.get("supply_feasibility", ""),
        "structural_validity": first_value(run.metrics.get("structural_validity"), run.summary.get("structural_validity")),
        "avg_utilisation": first_value(run.metrics.get("post_reloc_2opt_avg_utilization"), run.summary.get("avg_utilization")),
        "depot_avg_utilisation": first_value(run.timing_summary.get("avg_depot_route_utilization"), run.metrics.get("avg_depot_route_utilization")),
        "hybrid_system_distance_check": hybrid_system_distance_check(run),
        "scenario_parameter_check": parameter_check,
        "notes_or_warnings": " | ".join(warnings),
    }


def build_long_rows(runs: list[ExtractedRun]) -> list[dict[str, Any]]:
    return [
        build_row(run)
        for run in sorted(runs, key=lambda item: (item.customer_count, item.vehicle_capacity, item.timing_scenario))
    ]


def expected_instances() -> set[tuple[int, int]]:
    return {
        (customer_count, capacity)
        for customer_count in EXPECTED_CUSTOMER_COUNTS
        for capacity in EXPECTED_CAPACITIES
    }


def rows_by_scenario(rows: list[dict[str, Any]]) -> dict[str, dict[tuple[int, int], dict[str, Any]]]:
    output: dict[str, dict[tuple[int, int], dict[str, Any]]] = {}
    for row in rows:
        customer_count = as_int(row.get("customer_count"))
        vehicle_capacity = as_int(row.get("vehicle_capacity"))
        if customer_count is None or vehicle_capacity is None:
            continue
        output.setdefault(str(row["timing_scenario"]), {})[(customer_count, vehicle_capacity)] = row
    return output


def prefixed(row: dict[str, Any] | None, prefix: str, keys: list[str]) -> dict[str, Any]:
    if row is None:
        return {f"{prefix}_{key}": "" for key in keys}
    return {f"{prefix}_{key}": row.get(key, "") for key in keys}


def warning_text(*parts: str) -> str:
    return " | ".join(part for part in parts if part)


def build_speed_comparison_rows(long_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_scenario = rows_by_scenario(long_rows)
    base_rows = by_scenario.get("base_speed30", {})
    speed_rows = by_scenario.get("speed40", {})
    rows: list[dict[str, Any]] = []

    for customer_count, vehicle_capacity in sorted(expected_instances()):
        base = base_rows.get((customer_count, vehicle_capacity))
        speed = speed_rows.get((customer_count, vehicle_capacity))
        warnings: list[str] = []
        if base is None:
            warnings.append("missing base_speed30 row")
        if speed is None:
            warnings.append("missing speed40 row")
        if base and speed:
            if normalize_waves(base.get("dispatch_waves")) != normalize_waves(speed.get("dispatch_waves")):
                warnings.append("dispatch waves differ in speed comparison")

        row = {
            "customer_count": customer_count,
            "vehicle_capacity": vehicle_capacity,
            "base_selected_run_timestamp": base.get("selected_run_timestamp", "") if base else "",
            "speed40_selected_run_timestamp": speed.get("selected_run_timestamp", "") if speed else "",
            "base_total_system_distance": base.get("total_system_distance", "") if base else "",
            "speed40_total_system_distance": speed.get("total_system_distance", "") if speed else "",
            "speed40_minus_base_total_system_distance": numeric_delta(speed.get("total_system_distance", "") if speed else "", base.get("total_system_distance", "") if base else ""),
            "speed40_minus_base_total_system_distance_pct": pct_delta(speed.get("total_system_distance", "") if speed else "", base.get("total_system_distance", "") if base else ""),
            "base_timing_feasible": base.get("depot_timing_feasibility", "") if base else "",
            "speed40_timing_feasible": speed.get("depot_timing_feasibility", "") if speed else "",
            "base_timing_infeasible_routes": base.get("post_repair_timing_infeasible_routes", "") if base else "",
            "speed40_timing_infeasible_routes": speed.get("post_repair_timing_infeasible_routes", "") if speed else "",
            "speed40_minus_base_timing_infeasible_routes": numeric_delta(speed.get("post_repair_timing_infeasible_routes", "") if speed else "", base.get("post_repair_timing_infeasible_routes", "") if base else ""),
            "base_routes_exceeding_workday": base.get("post_repair_routes_exceeding_workday", "") if base else "",
            "speed40_routes_exceeding_workday": speed.get("post_repair_routes_exceeding_workday", "") if speed else "",
            "base_unresolved_repairs": base.get("unresolved_repairs", "") if base else "",
            "speed40_unresolved_repairs": speed.get("unresolved_repairs", "") if speed else "",
            "base_unresolved_customers_count": base.get("unresolved_customers_count", "") if base else "",
            "speed40_unresolved_customers_count": speed.get("unresolved_customers_count", "") if speed else "",
            "speed40_minus_base_unresolved_customers": numeric_delta(speed.get("unresolved_customers_count", "") if speed else "", base.get("unresolved_customers_count", "") if base else ""),
            "base_latest_finish_time_label": base.get("post_repair_latest_finish_time_label", "") if base else "",
            "speed40_latest_finish_time_label": speed.get("post_repair_latest_finish_time_label", "") if speed else "",
            "base_latest_finish_time": base.get("post_repair_latest_finish_time", "") if base else "",
            "speed40_latest_finish_time": speed.get("post_repair_latest_finish_time", "") if speed else "",
            "speed40_minus_base_latest_finish_hours": numeric_delta(speed.get("post_repair_latest_finish_time", "") if speed else "", base.get("post_repair_latest_finish_time", "") if base else ""),
            "base_total_routes": base.get("post_repair_total_routes", "") if base else "",
            "speed40_total_routes": speed.get("post_repair_total_routes", "") if speed else "",
            "speed40_minus_base_total_routes": numeric_delta(speed.get("post_repair_total_routes", "") if speed else "", base.get("post_repair_total_routes", "") if base else ""),
            "base_depot_routes": base.get("post_repair_depot_routes", "") if base else "",
            "speed40_depot_routes": speed.get("post_repair_depot_routes", "") if speed else "",
            "speed40_minus_base_depot_routes": numeric_delta(speed.get("post_repair_depot_routes", "") if speed else "", base.get("post_repair_depot_routes", "") if base else ""),
            "base_repair_attempts": base.get("repair_attempts", "") if base else "",
            "speed40_repair_attempts": speed.get("repair_attempts", "") if speed else "",
            "base_successful_repairs": base.get("successful_repairs", "") if base else "",
            "speed40_successful_repairs": speed.get("successful_repairs", "") if speed else "",
            "base_routes_added_by_repair": base.get("routes_added_by_repair", "") if base else "",
            "speed40_routes_added_by_repair": speed.get("routes_added_by_repair", "") if speed else "",
            "notes_or_warnings": warning_text(
                " | ".join(warnings),
                base.get("notes_or_warnings", "") if base else "",
                speed.get("notes_or_warnings", "") if speed else "",
            ),
        }
        rows.append(row)
    return rows


def build_14wave_comparison_rows(long_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_scenario = rows_by_scenario(long_rows)
    base_rows = by_scenario.get("base_speed30", {})
    wave_rows = by_scenario.get("added_14_wave", {})
    rows: list[dict[str, Any]] = []

    for customer_count, vehicle_capacity in sorted(expected_instances()):
        base = base_rows.get((customer_count, vehicle_capacity))
        wave = wave_rows.get((customer_count, vehicle_capacity))
        warnings: list[str] = []
        if base is None:
            warnings.append("missing base_speed30 row")
        if wave is None:
            warnings.append("missing added_14_wave row")
        if base and wave:
            base_speed = as_float(base.get("average_speed"))
            wave_speed = as_float(wave.get("average_speed"))
            if base_speed is not None and wave_speed is not None and abs(base_speed - wave_speed) > SPEED_TOLERANCE:
                warnings.append("average speed differs in 14-wave comparison")

        row = {
            "customer_count": customer_count,
            "vehicle_capacity": vehicle_capacity,
            "base_selected_run_timestamp": base.get("selected_run_timestamp", "") if base else "",
            "wave14_selected_run_timestamp": wave.get("selected_run_timestamp", "") if wave else "",
            "base_dispatch_waves": base.get("dispatch_waves", "") if base else "",
            "wave14_dispatch_waves": wave.get("dispatch_waves", "") if wave else "",
            "base_total_system_distance": base.get("total_system_distance", "") if base else "",
            "wave14_total_system_distance": wave.get("total_system_distance", "") if wave else "",
            "wave14_minus_base_total_system_distance": numeric_delta(wave.get("total_system_distance", "") if wave else "", base.get("total_system_distance", "") if base else ""),
            "wave14_minus_base_total_system_distance_pct": pct_delta(wave.get("total_system_distance", "") if wave else "", base.get("total_system_distance", "") if base else ""),
            "base_timing_feasible": base.get("depot_timing_feasibility", "") if base else "",
            "wave14_timing_feasible": wave.get("depot_timing_feasibility", "") if wave else "",
            "base_timing_infeasible_routes": base.get("post_repair_timing_infeasible_routes", "") if base else "",
            "wave14_timing_infeasible_routes": wave.get("post_repair_timing_infeasible_routes", "") if wave else "",
            "wave14_minus_base_timing_infeasible_routes": numeric_delta(wave.get("post_repair_timing_infeasible_routes", "") if wave else "", base.get("post_repair_timing_infeasible_routes", "") if base else ""),
            "base_routes_exceeding_workday": base.get("post_repair_routes_exceeding_workday", "") if base else "",
            "wave14_routes_exceeding_workday": wave.get("post_repair_routes_exceeding_workday", "") if wave else "",
            "base_unresolved_repairs": base.get("unresolved_repairs", "") if base else "",
            "wave14_unresolved_repairs": wave.get("unresolved_repairs", "") if wave else "",
            "base_unresolved_customers_count": base.get("unresolved_customers_count", "") if base else "",
            "wave14_unresolved_customers_count": wave.get("unresolved_customers_count", "") if wave else "",
            "wave14_minus_base_unresolved_customers": numeric_delta(wave.get("unresolved_customers_count", "") if wave else "", base.get("unresolved_customers_count", "") if base else ""),
            "base_latest_finish_time_label": base.get("post_repair_latest_finish_time_label", "") if base else "",
            "wave14_latest_finish_time_label": wave.get("post_repair_latest_finish_time_label", "") if wave else "",
            "base_latest_finish_time": base.get("post_repair_latest_finish_time", "") if base else "",
            "wave14_latest_finish_time": wave.get("post_repair_latest_finish_time", "") if wave else "",
            "wave14_minus_base_latest_finish_hours": numeric_delta(wave.get("post_repair_latest_finish_time", "") if wave else "", base.get("post_repair_latest_finish_time", "") if base else ""),
            "base_total_routes": base.get("post_repair_total_routes", "") if base else "",
            "wave14_total_routes": wave.get("post_repair_total_routes", "") if wave else "",
            "wave14_minus_base_total_routes": numeric_delta(wave.get("post_repair_total_routes", "") if wave else "", base.get("post_repair_total_routes", "") if base else ""),
            "base_depot_routes": base.get("post_repair_depot_routes", "") if base else "",
            "wave14_depot_routes": wave.get("post_repair_depot_routes", "") if wave else "",
            "wave14_minus_base_depot_routes": numeric_delta(wave.get("post_repair_depot_routes", "") if wave else "", base.get("post_repair_depot_routes", "") if base else ""),
            "base_avg_waiting_time": base.get("avg_waiting_time", "") if base else "",
            "wave14_avg_waiting_time": wave.get("avg_waiting_time", "") if wave else "",
            "wave14_minus_base_avg_waiting_time": numeric_delta(wave.get("avg_waiting_time", "") if wave else "", base.get("avg_waiting_time", "") if base else ""),
            "base_max_waiting_time": base.get("max_waiting_time", "") if base else "",
            "wave14_max_waiting_time": wave.get("max_waiting_time", "") if wave else "",
            "wave14_minus_base_max_waiting_time": numeric_delta(wave.get("max_waiting_time", "") if wave else "", base.get("max_waiting_time", "") if base else ""),
            "base_customers_per_wave": base.get("customers_per_wave", "") if base else "",
            "wave14_customers_per_wave": wave.get("customers_per_wave", "") if wave else "",
            "base_routes_per_wave": base.get("routes_per_wave", "") if base else "",
            "wave14_routes_per_wave": wave.get("routes_per_wave", "") if wave else "",
            "notes_or_warnings": warning_text(
                " | ".join(warnings),
                base.get("notes_or_warnings", "") if base else "",
                wave.get("notes_or_warnings", "") if wave else "",
            ),
        }
        rows.append(row)
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: serialize(value) for key, value in row.items()})


def scenario_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        scenario = str(row.get("timing_scenario", ""))
        counts[scenario] = counts.get(scenario, 0) + 1
    return counts


def missing_instances(rows: list[dict[str, Any]], scenario: str) -> list[str]:
    present = {
        (int(row["customer_count"]), int(row["vehicle_capacity"]))
        for row in rows
        if row.get("timing_scenario") == scenario and row.get("customer_count") and row.get("vehicle_capacity")
    }
    return [f"{customers}c_cap{capacity}" for customers, capacity in sorted(expected_instances() - present)]


def warning_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if row.get("notes_or_warnings")]


def count_rows(rows: list[dict[str, Any]], scenario: str, key: str, predicate: Any) -> int:
    total = 0
    for row in rows:
        if row.get("timing_scenario") != scenario:
            continue
        if predicate(row.get(key)):
            total += 1
    return total


def sum_numeric(rows: list[dict[str, Any]], scenario: str, key: str) -> float:
    total = 0.0
    for row in rows:
        if row.get("timing_scenario") != scenario:
            continue
        value = as_float(row.get(key))
        if value is not None:
            total += value
    return total


def write_summary(root: Path, rows: list[dict[str, Any]], speed_rows: list[dict[str, Any]], wave_rows: list[dict[str, Any]]) -> Path:
    output_path = root / OUTPUT_DIR / OUTPUT_SUMMARY
    output_path.parent.mkdir(parents=True, exist_ok=True)

    counts = scenario_counts(rows)
    warnings = warning_rows(rows)
    parameter_statuses: dict[str, dict[str, int]] = {}
    speeds_by_scenario: dict[str, set[str]] = {}
    waves_by_scenario: dict[str, set[str]] = {}
    for row in rows:
        scenario = str(row.get("timing_scenario", ""))
        status = str(row.get("scenario_parameter_check", ""))
        parameter_statuses.setdefault(scenario, {})[status] = parameter_statuses.setdefault(scenario, {}).get(status, 0) + 1
        speeds_by_scenario.setdefault(scenario, set()).add(str(row.get("average_speed", "")))
        waves_by_scenario.setdefault(scenario, set()).add(str(row.get("dispatch_waves", "")))

    lines = [
        "# Section 6.7 Sensitivity Analysis Extraction Summary",
        "",
        "## Source Folders",
        "",
    ]
    for spec in SCENARIO_SPECS:
        lines.append(f"- `{spec['relative_path']}`: {spec['description']}")

    lines.extend(["", "## Explicitly Excluded Folders", ""])
    for folder in EXCLUDED_FOLDERS:
        lines.append(f"- `{folder}`")

    lines.extend(
        [
            "",
            "## Output Files",
            "",
            f"- Long CSV: `{OUTPUT_DIR / OUTPUT_LONG_CSV}`",
            f"- Speed comparison CSV: `{OUTPUT_DIR / OUTPUT_SPEED_CSV}`",
            f"- 14:00-wave comparison CSV: `{OUTPUT_DIR / OUTPUT_14WAVE_CSV}`",
            f"- Summary: `{OUTPUT_DIR / OUTPUT_SUMMARY}`",
            "",
            "## Extraction Rule",
            "",
            "- The extractor selects the latest `run_*` folder that matches the expected scenario parameters for every instance folder.",
            "- If the newest timestamped run has the wrong speed or dispatch-wave list, it is skipped and recorded in the warnings/status notes.",
            "- The base speed30 dispatch-wave split-repair folder is extracted again as the Section 6.7 reference scenario.",
            "- The speed40 comparison changes average speed while keeping the base dispatch waves.",
            "- The 14:00-wave comparison changes the dispatch-wave list while keeping speed at 30.",
            "- The extractor does not read fixed timing, route-first waves, wave construction without split repair, time-aware LNS, or non-timing LNS result folders.",
            "",
            "## Rows Written",
            "",
            f"- Long-format rows: {len(rows)}",
            f"- Speed comparison rows: {len(speed_rows)}",
            f"- 14:00-wave comparison rows: {len(wave_rows)}",
        ]
    )
    for scenario in sorted(counts):
        lines.append(f"- `{scenario}` rows: {counts[scenario]}")

    lines.extend(["", "## Expected Instance Grid", ""])
    lines.append("- Expected customer counts: `20, 40, 60, 80, 100, 150, 200`")
    lines.append("- Expected vehicle capacities: `15, 25, 35`")
    for spec in SCENARIO_SPECS:
        scenario = str(spec["timing_scenario"])
        missing = missing_instances(rows, scenario)
        if missing:
            lines.append(f"- Missing `{scenario}` rows: {', '.join(missing)}")
        else:
            lines.append(f"- Missing `{scenario}` rows: none")

    lines.extend(["", "## Scenario Parameter Verification", ""])
    for spec in SCENARIO_SPECS:
        scenario = str(spec["timing_scenario"])
        lines.append(f"### `{scenario}`")
        lines.append(f"- Expected speed: {spec['expected_speed']}")
        lines.append(f"- Expected waves: {list(spec['expected_waves'])}")
        lines.append(f"- Speed values extracted: {', '.join(sorted(speeds_by_scenario.get(scenario, set())))}")
        lines.append(f"- Dispatch wave values extracted: {', '.join(sorted(waves_by_scenario.get(scenario, set())))}")
        statuses = parameter_statuses.get(scenario, {})
        if statuses:
            for status, count in sorted(statuses.items()):
                lines.append(f"- `{status}` rows: {count}")
        else:
            lines.append("- No rows extracted.")

    lines.extend(["", "## Feasibility Summary By Scenario", ""])
    for scenario in sorted(counts):
        lines.append(f"### `{scenario}`")
        lines.append(f"- Feasible timing rows: {count_rows(rows, scenario, 'depot_timing_feasibility', lambda value: str(value) == 'True')}")
        lines.append(f"- Infeasible timing rows: {count_rows(rows, scenario, 'depot_timing_feasibility', lambda value: str(value) == 'False')}")
        lines.append(f"- Rows with post-repair workday violations: {count_rows(rows, scenario, 'post_repair_routes_exceeding_workday', lambda value: (as_int(value) or 0) > 0)}")
        lines.append(f"- Rows with unresolved repairs: {count_rows(rows, scenario, 'unresolved_repairs', lambda value: (as_int(value) or 0) > 0)}")
        lines.append(f"- Total unresolved customers: {sum_numeric(rows, scenario, 'unresolved_customers_count')}")

    lines.extend(["", "## Matched Comparison Summary", ""])
    speed_missing = [row for row in speed_rows if "missing" in str(row.get("notes_or_warnings", ""))]
    wave_missing = [row for row in wave_rows if "missing" in str(row.get("notes_or_warnings", ""))]
    lines.append(f"- Speed comparison matched rows written: {len(speed_rows)}")
    lines.append(f"- Speed comparison rows with missing pair warnings: {len(speed_missing)}")
    lines.append(f"- 14:00-wave comparison matched rows written: {len(wave_rows)}")
    lines.append(f"- 14:00-wave comparison rows with missing pair warnings: {len(wave_missing)}")

    lines.extend(["", "## Warnings / Status Notes", ""])
    if warnings:
        lines.append(f"- Long-format rows with warnings/status notes: {len(warnings)}")
        for row in warnings[:120]:
            lines.append(
                f"- `{row['timing_scenario']}` `{row['instance_name']}` `{row['selected_run_timestamp']}`: {row['notes_or_warnings']}"
            )
        if len(warnings) > 120:
            lines.append(f"- Additional warning rows omitted from summary: {len(warnings) - 120}")
    else:
        lines.append("- Long-format rows with warnings/status notes: 0")

    lines.extend(
        [
            "",
            "## Thesis Use Notes",
            "",
            "- Use this extraction for Section 6.7 only.",
            "- Treat `base_speed30` as the reference scenario for both matched comparisons.",
            "- Treat `speed40` as speed sensitivity only; the dispatch-wave list should remain 09/11/13/15.",
            "- Treat `added_14_wave` as dispatch-policy sensitivity only; average speed should remain 30.",
            "- Do not mix these rows with fixed timing, route-first waves, wave construction without split repair, or timing-aware LNS results.",
            "- Remaining timing infeasibility and unresolved repairs should remain visible in the thesis discussion.",
        ]
    )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def main() -> None:
    root = project_root()
    runs: list[ExtractedRun] = []
    for spec in SCENARIO_SPECS:
        runs.extend(load_folder(root, spec))

    long_rows = build_long_rows(runs)
    speed_rows = build_speed_comparison_rows(long_rows)
    wave_rows = build_14wave_comparison_rows(long_rows)

    output_dir = root / OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    long_csv = output_dir / OUTPUT_LONG_CSV
    speed_csv = output_dir / OUTPUT_SPEED_CSV
    wave_csv = output_dir / OUTPUT_14WAVE_CSV

    write_csv(long_csv, long_rows)
    write_csv(speed_csv, speed_rows)
    write_csv(wave_csv, wave_rows)
    summary_path = write_summary(root, long_rows, speed_rows, wave_rows)

    print(f"Wrote {long_csv}")
    print(f"Wrote {speed_csv}")
    print(f"Wrote {wave_csv}")
    print(f"Wrote {summary_path}")
    print(f"Rows: {len(long_rows)}")
    print(f"Speed comparison rows: {len(speed_rows)}")
    print(f"14-wave comparison rows: {len(wave_rows)}")
    print(f"Warnings: {len(warning_rows(long_rows))}")


if __name__ == "__main__":
    main()
