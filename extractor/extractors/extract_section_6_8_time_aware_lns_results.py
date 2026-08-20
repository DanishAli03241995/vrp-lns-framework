#!/usr/bin/env python3
"""Extract Chapter 6.8 time-aware LNS result tables."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any


INSTANCE_RE = re.compile(r"^(?P<customers>\d+)c_cap(?P<capacity>\d+)$")

OUTPUT_DIR = Path("extractor/section 6.8")
OUTPUT_LONG_CSV = "section_6_8_time_aware_lns_table.csv"
OUTPUT_OPERATOR_CSV = "section_6_8_operator_pair_comparison.csv"
OUTPUT_SCENARIO_CSV = "section_6_8_scenario_operator_summary.csv"
OUTPUT_BASELINE_CSV = "section_6_8_baseline_vs_lns_comparison.csv"
OUTPUT_SUMMARY = "section_6_8_time_aware_lns_summary.md"

EXPECTED_CUSTOMER_COUNTS = (20, 40, 60, 80, 100, 150, 200)
EXPECTED_CAPACITIES = (15, 25, 35)

BASE_WAVES = (9.0, 11.0, 13.0, 15.0)
WAVE14_WAVES = (9.0, 11.0, 13.0, 14.0, 15.0)
SPEED_TOLERANCE = 0.25
DISTANCE_TOLERANCE = 1e-6


SCENARIO_SPECS = [
    {
        "timing_lns_scenario": "fixed_split",
        "timing_model_family": "fixed_timing",
        "operator_pair": "random_regret",
        "destroy_operator": "random_removal",
        "repair_operator": "regret_2_insertion",
        "relative_path": Path("results/lns_timing_fixed_split_random_regret/case3_kmeans"),
        "baseline_reference_scenario": "fixed_timing_split_repair",
        "baseline_reference_folder": Path("results/hybrid_supplier_customer_kmeans_timing_fixed_split_v1"),
        "expected_speed": 30.0,
        "expected_fixed_ready_time": 9.0,
        "expected_waves": (),
        "timing_summary_file": "depot_timing_fixed_lns_summary.json",
        "timing_records_file": "depot_timing_fixed_lns_records.json",
        "operator_pair_token": "random_regret",
    },
    {
        "timing_lns_scenario": "fixed_split",
        "timing_model_family": "fixed_timing",
        "operator_pair": "related_regret",
        "destroy_operator": "related_shaw_removal",
        "repair_operator": "regret_2_insertion",
        "relative_path": Path("results/lns_timing_fixed_split_related_regret/case3_kmeans"),
        "baseline_reference_scenario": "fixed_timing_split_repair",
        "baseline_reference_folder": Path("results/hybrid_supplier_customer_kmeans_timing_fixed_split_v1"),
        "expected_speed": 30.0,
        "expected_fixed_ready_time": 9.0,
        "expected_waves": (),
        "timing_summary_file": "depot_timing_fixed_lns_summary.json",
        "timing_records_file": "depot_timing_fixed_lns_records.json",
        "operator_pair_token": "related_regret",
    },
    {
        "timing_lns_scenario": "wave_speed40_split",
        "timing_model_family": "dispatch_wave",
        "operator_pair": "random_regret",
        "destroy_operator": "random_removal",
        "repair_operator": "regret_2_insertion",
        "relative_path": Path("results/lns_timing_waves_split_speed40_random_regret/case3_kmeans"),
        "baseline_reference_scenario": "dispatch_wave_speed40_split_repair",
        "baseline_reference_folder": Path("results/hybrid_supplier_customer_kmeans_timing_waves_constructed_split_v1_40_speed"),
        "expected_speed": 40.0,
        "expected_fixed_ready_time": "",
        "expected_waves": BASE_WAVES,
        "timing_summary_file": "depot_timing_wave_lns_summary.json",
        "timing_records_file": "depot_timing_wave_lns_records.json",
        "operator_pair_token": "random_regret",
    },
    {
        "timing_lns_scenario": "wave_speed40_split",
        "timing_model_family": "dispatch_wave",
        "operator_pair": "related_regret",
        "destroy_operator": "related_shaw_removal",
        "repair_operator": "regret_2_insertion",
        "relative_path": Path("results/lns_timing_waves_split_speed40_related_regret/case3_kmeans"),
        "baseline_reference_scenario": "dispatch_wave_speed40_split_repair",
        "baseline_reference_folder": Path("results/hybrid_supplier_customer_kmeans_timing_waves_constructed_split_v1_40_speed"),
        "expected_speed": 40.0,
        "expected_fixed_ready_time": "",
        "expected_waves": BASE_WAVES,
        "timing_summary_file": "depot_timing_wave_lns_summary.json",
        "timing_records_file": "depot_timing_wave_lns_records.json",
        "operator_pair_token": "related_regret",
    },
    {
        "timing_lns_scenario": "wave_speed30_14wave_split",
        "timing_model_family": "dispatch_wave",
        "operator_pair": "random_regret",
        "destroy_operator": "random_removal",
        "repair_operator": "regret_2_insertion",
        "relative_path": Path("results/lns_timing_waves_split_speed30_14wave_random_regret/case3_kmeans"),
        "baseline_reference_scenario": "dispatch_wave_speed30_14wave_split_repair",
        "baseline_reference_folder": Path("results/hybrid_supplier_customer_kmeans_timing_waves_constructed_split_14wave_v1"),
        "expected_speed": 30.0,
        "expected_fixed_ready_time": "",
        "expected_waves": WAVE14_WAVES,
        "timing_summary_file": "depot_timing_wave_lns_summary.json",
        "timing_records_file": "depot_timing_wave_lns_records.json",
        "operator_pair_token": "random_regret",
    },
    {
        "timing_lns_scenario": "wave_speed30_14wave_split",
        "timing_model_family": "dispatch_wave",
        "operator_pair": "related_regret",
        "destroy_operator": "related_shaw_removal",
        "repair_operator": "regret_2_insertion",
        "relative_path": Path("results/lns_timing_waves_split_speed30_14wave_related_regret/case3_kmeans"),
        "baseline_reference_scenario": "dispatch_wave_speed30_14wave_split_repair",
        "baseline_reference_folder": Path("results/hybrid_supplier_customer_kmeans_timing_waves_constructed_split_14wave_v1"),
        "expected_speed": 30.0,
        "expected_fixed_ready_time": "",
        "expected_waves": WAVE14_WAVES,
        "timing_summary_file": "depot_timing_wave_lns_summary.json",
        "timing_records_file": "depot_timing_wave_lns_records.json",
        "operator_pair_token": "related_regret",
    },
]


@dataclass(frozen=True)
class ExtractedRun:
    customer_count: int
    vehicle_capacity: int
    instance_name: str
    timing_lns_scenario: str
    timing_model_family: str
    operator_pair: str
    source_folder: str
    baseline_reference_scenario: str
    baseline_reference_folder: str
    expected_speed: Any
    expected_waves: tuple[float, ...]
    selected_run_timestamp: str
    latest_available_run_timestamp: str
    selected_run_is_latest_available: bool
    run_folder_count: int
    run_dir: Path | None
    metrics_source_file: str
    summary_source_file: str
    metrics: dict[str, Any]
    summary: dict[str, Any]
    runner_summary: dict[str, Any]
    timing_summary: dict[str, Any]
    timing_records: list[dict[str, Any]]
    route_records: list[dict[str, Any]]
    warnings: list[str]


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def parse_instance_name(path: Path) -> tuple[int, int] | None:
    match = INSTANCE_RE.match(path.name)
    if not match:
        return None
    return int(match.group("customers")), int(match.group("capacity"))


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


def serialize(raw: Any) -> str:
    if raw in ("", None):
        return ""
    if isinstance(raw, (dict, list, tuple)):
        return json.dumps(raw, ensure_ascii=False, sort_keys=True)
    return str(raw)


def dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(item for item in items if item))


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


def pct_change(after: Any, before: Any) -> float | str:
    after_value = as_float(after)
    before_value = as_float(before)
    if after_value is None or before_value is None or before_value == 0:
        return ""
    return ((after_value - before_value) / before_value) * 100


def rate(numerator: Any, denominator: Any) -> float | str:
    numerator_value = as_float(numerator)
    denominator_value = as_float(denominator)
    if numerator_value is None or denominator_value in (None, 0):
        return ""
    return numerator_value / denominator_value


def load_best_metrics(run_dir: Path) -> tuple[dict[str, Any], str, list[str]]:
    warnings: list[str] = []
    for filename in ("lns_sa_metrics_best.json", "lns_sa_metrics.json"):
        metrics, warning = read_json_dict(run_dir / filename)
        if warning:
            warnings.append(warning)
            continue
        return metrics, filename, warnings
    return {}, "", ["missing lns_sa_metrics_best.json and lns_sa_metrics.json"]


def load_best_summary(run_dir: Path) -> tuple[dict[str, Any], str, list[str]]:
    warnings: list[str] = []
    for filename in ("lns_sa_summary_best.json", "lns_sa_summary.json"):
        summary, warning = read_json_dict(run_dir / filename)
        if warning:
            warnings.append(warning)
            continue
        return summary, filename, warnings
    return {}, "", ["missing lns_sa_summary_best.json and lns_sa_summary.json"]


def recorded_speed(metrics: dict[str, Any]) -> Any:
    return first_value(metrics.get("average_speed"), metrics.get("speed"))


def recorded_waves(metrics: dict[str, Any]) -> tuple[float, ...] | None:
    return normalize_waves(metrics.get("dispatch_waves"))


def operator_pair_matches(metrics: dict[str, Any], spec: dict[str, Any]) -> bool:
    expected_token = str(spec["operator_pair_token"])
    operator_pair = str(metrics.get("operator_pair", ""))
    destroy_operator = str(metrics.get("destroy_operator", ""))
    repair_operator = str(metrics.get("repair_operator", ""))
    if expected_token not in operator_pair:
        return False
    expected_repair = str(spec["repair_operator"])
    if expected_repair and repair_operator:
        if expected_repair == "regret_2_insertion" and "regret" not in repair_operator:
            return False
        if expected_repair != "regret_2_insertion" and repair_operator != expected_repair:
            return False
    expected_destroy = str(spec["destroy_operator"])
    if expected_destroy == "related_shaw_removal":
        return "related" in destroy_operator or "shaw" in destroy_operator
    if destroy_operator:
        return destroy_operator == expected_destroy
    return True


def scenario_matches(metrics: dict[str, Any], spec: dict[str, Any]) -> tuple[bool, list[str]]:
    warnings: list[str] = []
    if not operator_pair_matches(metrics, spec):
        warnings.append("operator pair mismatch")

    speed = as_float(recorded_speed(metrics))
    expected_speed = as_float(spec.get("expected_speed"))
    if expected_speed is not None:
        if speed is None:
            warnings.append("average speed missing")
        elif abs(speed - expected_speed) > SPEED_TOLERANCE:
            warnings.append(f"average speed mismatch expected {expected_speed}")

    if spec["timing_model_family"] == "fixed_timing":
        fixed_ready = as_float(metrics.get("fixed_depot_ready_time"))
        expected_ready = as_float(spec.get("expected_fixed_ready_time"))
        if expected_ready is not None:
            if fixed_ready is None:
                warnings.append("fixed depot ready time missing")
            elif abs(fixed_ready - expected_ready) > DISTANCE_TOLERANCE:
                warnings.append(f"fixed depot ready time mismatch expected {expected_ready}")
        waves = recorded_waves(metrics)
        if waves:
            warnings.append("dispatch waves present in fixed-timing row")
    else:
        waves = recorded_waves(metrics)
        expected_waves = tuple(spec["expected_waves"])
        if waves is None:
            warnings.append("dispatch waves missing")
        elif waves != expected_waves:
            warnings.append(f"dispatch waves mismatch expected {expected_waves}")
        if spec["timing_lns_scenario"] == "wave_speed30_14wave_split" and waves and 14.0 not in waves:
            warnings.append("14:00 wave missing from 14-wave scenario")
        if spec["timing_lns_scenario"] == "wave_speed40_split" and waves and 14.0 in waves:
            warnings.append("14:00 wave present in speed40 base-wave scenario")

    return not warnings, warnings


def select_latest_matching_run(instance_dir: Path, spec: dict[str, Any]) -> tuple[Path | None, int, Path | None, str, str, list[str]]:
    runs = timestamped_runs(instance_dir)
    if not runs:
        return None, 0, None, "", "", ["missing run folder"]

    latest_available = runs[-1]
    rejected_later: list[str] = []
    for run_dir in reversed(runs):
        metrics, metrics_source, metrics_warnings = load_best_metrics(run_dir)
        if not metrics:
            rejected_later.append(f"{run_dir.name} ({'; '.join(metrics_warnings)})")
            continue
        ok, match_warnings = scenario_matches(metrics, spec)
        if ok:
            warnings: list[str] = []
            if metrics_source != "lns_sa_metrics_best.json":
                warnings.append(f"used fallback metrics source {metrics_source}")
            if run_dir != latest_available:
                newer = [item.name for item in runs if item > run_dir]
                warnings.append(
                    "selected latest scenario-parameter-matching run; newer mismatched run(s) ignored: "
                    + ", ".join(newer)
                )
            return run_dir, len(runs), latest_available, metrics_source, "ok", warnings
        rejected_later.append(f"{run_dir.name} ({'; '.join(match_warnings)})")

    warnings = [
        "no run matched expected timing/operator parameters; selected latest available run",
        "candidate issues: " + " | ".join(rejected_later[:5]),
    ]
    metrics, metrics_source, metrics_warnings = load_best_metrics(latest_available)
    warnings.extend(metrics_warnings)
    return latest_available, len(runs), latest_available, metrics_source, "needs_check", warnings


def load_run(instance_dir: Path, spec: dict[str, Any]) -> ExtractedRun:
    parsed = parse_instance_name(instance_dir)
    if parsed is None:
        raise ValueError(f"invalid instance folder: {instance_dir}")

    customer_count, vehicle_capacity = parsed
    warnings: list[str] = []
    run_dir, run_count, latest_available, metrics_source, scenario_check, selection_warnings = select_latest_matching_run(instance_dir, spec)
    warnings.extend(selection_warnings)

    metrics: dict[str, Any] = {}
    summary: dict[str, Any] = {}
    runner_summary: dict[str, Any] = {}
    timing_summary: dict[str, Any] = {}
    timing_records: list[dict[str, Any]] = []
    route_records: list[dict[str, Any]] = []
    summary_source = ""

    if run_dir is not None:
        metrics, metrics_source, metric_warnings = load_best_metrics(run_dir)
        warnings.extend(metric_warnings)
        summary, summary_source, summary_warnings = load_best_summary(run_dir)
        warnings.extend(summary_warnings)
        runner_summary, warning = read_json_dict(run_dir / "lns_sa_runner_summary.json")
        if warning:
            warnings.append(warning)
        timing_summary, warning = read_json_dict(run_dir / str(spec["timing_summary_file"]))
        if warning:
            warnings.append(warning)
        timing_records, warning = read_json_list(run_dir / str(spec["timing_records_file"]))
        if warning:
            warnings.append(warning)
        route_records, warning = read_json_list(run_dir / "route_lns_sa_records_best.json")
        if warning:
            warnings.append(warning)

    if scenario_check != "ok":
        warnings.append(f"scenario_parameter_check={scenario_check}")

    return ExtractedRun(
        customer_count=customer_count,
        vehicle_capacity=vehicle_capacity,
        instance_name=instance_dir.name,
        timing_lns_scenario=str(spec["timing_lns_scenario"]),
        timing_model_family=str(spec["timing_model_family"]),
        operator_pair=str(spec["operator_pair"]),
        source_folder=str(spec["relative_path"]),
        baseline_reference_scenario=str(spec["baseline_reference_scenario"]),
        baseline_reference_folder=str(spec["baseline_reference_folder"]),
        expected_speed=spec.get("expected_speed", ""),
        expected_waves=tuple(spec["expected_waves"]),
        selected_run_timestamp=run_dir.name if run_dir else "",
        latest_available_run_timestamp=latest_available.name if latest_available else "",
        selected_run_is_latest_available=bool(run_dir and latest_available and run_dir == latest_available),
        run_folder_count=run_count,
        run_dir=run_dir,
        metrics_source_file=metrics_source,
        summary_source_file=summary_source,
        metrics=metrics,
        summary=summary,
        runner_summary=runner_summary,
        timing_summary=timing_summary,
        timing_records=timing_records,
        route_records=route_records,
        warnings=warnings,
    )


def metric(run: ExtractedRun, key: str) -> Any:
    return first_value(run.metrics.get(key), run.summary.get(key), run.timing_summary.get(key))


def timing_feasible(run: ExtractedRun) -> Any:
    if run.timing_model_family == "fixed_timing":
        return first_value(
            run.metrics.get("overall_feasible_with_fixed_timing_lns"),
            run.summary.get("overall_feasible_with_fixed_timing_lns"),
            run.timing_summary.get("depot_timing_feasibility"),
        )
    return first_value(
        run.metrics.get("overall_feasible_with_dispatch_wave_lns"),
        run.summary.get("overall_feasible_with_dispatch_wave_lns"),
        run.timing_summary.get("depot_timing_feasibility"),
    )


def total_system_distance(run: ExtractedRun) -> Any:
    return first_value(run.metrics.get("total_lns_system_distance"), run.summary.get("total_lns_system_distance"))


def customer_delivery_distance(run: ExtractedRun) -> Any:
    return first_value(
        run.metrics.get("customer_delivery_lns_distance"),
        run.metrics.get("total_lns_distance"),
        run.summary.get("final_distance"),
    )


def supplier_depot_distance(run: ExtractedRun) -> Any:
    return first_value(run.metrics.get("supplier_depot_replenishment_distance"), run.summary.get("supplier_depot_replenishment_distance"))


def hybrid_system_distance_check(run: ExtractedRun) -> str:
    customer_distance = as_float(customer_delivery_distance(run))
    replenishment = as_float(supplier_depot_distance(run))
    total = as_float(total_system_distance(run))
    if customer_distance is None or replenishment is None or total is None:
        return "missing"
    if abs((customer_distance + replenishment) - total) <= DISTANCE_TOLERANCE:
        return "ok"
    return "mismatch"


def scenario_parameter_check(run: ExtractedRun) -> str:
    ok, warnings = scenario_matches(run.metrics, {
        "operator_pair_token": run.operator_pair,
        "operator_pair": run.operator_pair,
        "destroy_operator": run.metrics.get("destroy_operator", ""),
        "repair_operator": run.metrics.get("repair_operator", ""),
        "timing_model_family": run.timing_model_family,
        "expected_speed": run.expected_speed,
        "expected_fixed_ready_time": 9.0 if run.timing_model_family == "fixed_timing" else "",
        "expected_waves": run.expected_waves,
        "timing_lns_scenario": run.timing_lns_scenario,
    })
    if ok:
        return "ok"
    if any("average speed" in item for item in warnings):
        return "speed_mismatch_or_missing"
    if any("dispatch waves" in item or "14:00 wave" in item for item in warnings):
        return "wave_schedule_mismatch_or_missing"
    if any("operator pair" in item for item in warnings):
        return "operator_pair_mismatch"
    return "needs_check"


def accepted_infeasible_candidate_check(run: ExtractedRun) -> str:
    records_file = run.run_dir / "operator_pair_records.json" if run.run_dir else None
    if records_file is None or not records_file.exists():
        return "no_iteration_feasibility_records_available"

    records, warning = read_json_dict(records_file)
    if warning:
        return "operator_pair_records_unreadable"

    text = json.dumps(records, ensure_ascii=False).lower()
    if "candidate_timing_feasible" in text or "candidate_feasible" in text:
        if '"candidate_timing_feasible": false' in text or '"candidate_feasible": false' in text:
            if '"accepted": true' in text:
                return "needs_manual_check"
            return "no_accepted_infeasible_detected"
    if as_int(run.metrics.get("rejected_infeasible_moves")) not in (None, 0):
        return "infeasible_candidates_rejected_count_recorded"
    return "no_infeasible_acceptance_evidence_in_saved_records"


def route_count_from_solution(run: ExtractedRun) -> int | str:
    if run.run_dir is None:
        return ""
    path = run.run_dir / "best_lns_solution.json"
    try:
        data = json.load(path.open("r", encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return ""
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        routes = first_value(data.get("routes"), data.get("solution"))
        if isinstance(routes, list):
            return len(routes)
    return ""


def run_warnings(run: ExtractedRun) -> list[str]:
    warnings = list(run.warnings)
    for key in (
        "baseline_reference_system_distance",
        "customer_delivery_lns_distance",
        "supplier_depot_replenishment_distance",
        "total_lns_system_distance",
        "n_remove",
        "n_iterations",
        "accepted_moves",
        "rejected_moves",
        "rejected_infeasible_moves",
    ):
        if key not in run.metrics:
            warnings.append(f"missing metric {key}")
    if hybrid_system_distance_check(run) != "ok":
        warnings.append(f"hybrid_system_distance_check={hybrid_system_distance_check(run)}")
    if scenario_parameter_check(run) != "ok":
        warnings.append(f"scenario_parameter_check={scenario_parameter_check(run)}")
    if timing_feasible(run) in ("", None):
        warnings.append("missing timing feasibility after LNS")
    return dedupe(warnings)


def route_scope_from_runner(run: ExtractedRun) -> Any:
    return first_value(run.runner_summary.get("route_scope"), run.metrics.get("route_scope"))


def long_row(run: ExtractedRun) -> dict[str, Any]:
    n_iterations = metric(run, "n_iterations")
    accepted = metric(run, "accepted_moves")
    rejected = metric(run, "rejected_moves")
    rejected_infeasible = metric(run, "rejected_infeasible_moves")
    non_infeasible_rejected = ""
    rejected_value = as_float(rejected)
    rejected_infeasible_value = as_float(rejected_infeasible)
    if rejected_value is not None and rejected_infeasible_value is not None:
        non_infeasible_rejected = rejected_value - rejected_infeasible_value

    baseline_system = metric(run, "baseline_reference_system_distance")
    lns_system = total_system_distance(run)

    return {
        "timing_lns_scenario": run.timing_lns_scenario,
        "timing_model_family": run.timing_model_family,
        "operator_pair": run.operator_pair,
        "destroy_operator": first_value(run.metrics.get("destroy_operator"), ""),
        "repair_operator": first_value(run.metrics.get("repair_operator"), ""),
        "routing_case": "case_3_hybrid",
        "clustering": "kmeans",
        "instance_name": run.instance_name,
        "customer_count": run.customer_count,
        "vehicle_capacity": run.vehicle_capacity,
        "source_folder": run.source_folder,
        "selected_run_timestamp": run.selected_run_timestamp,
        "latest_available_run_timestamp": run.latest_available_run_timestamp,
        "selected_run_is_latest_available": run.selected_run_is_latest_available,
        "run_folder_count": run.run_folder_count,
        "metrics_source_file": run.metrics_source_file,
        "summary_source_file": run.summary_source_file,
        "baseline_reference_scenario": run.baseline_reference_scenario,
        "baseline_reference_folder": run.baseline_reference_folder,
        "baseline_run_path": metric(run, "baseline_run_path"),
        "baseline_reference_algorithm": metric(run, "baseline_reference_algorithm"),
        "baseline_reference_distance": metric(run, "baseline_reference_distance"),
        "baseline_reference_customer_delivery_distance": metric(run, "baseline_reference_customer_delivery_distance"),
        "baseline_reference_system_distance": baseline_system,
        "total_lns_distance": metric(run, "total_lns_distance"),
        "customer_delivery_lns_distance": customer_delivery_distance(run),
        "supplier_depot_replenishment_distance": supplier_depot_distance(run),
        "total_lns_system_distance": lns_system,
        "depot_lns_distance": metric(run, "depot_lns_distance"),
        "supplier_lns_distance": metric(run, "supplier_lns_distance"),
        "improvement_distance": metric(run, "improvement_distance"),
        "improvement_percent": metric(run, "improvement_percent"),
        "system_improvement_distance": metric(run, "system_improvement_distance"),
        "system_improvement_percent": metric(run, "system_improvement_percent"),
        "customer_delivery_improvement_distance": metric(run, "customer_delivery_improvement_distance"),
        "customer_delivery_improvement_percent": metric(run, "customer_delivery_improvement_percent"),
        "system_distance_change_pct_check": pct_change(lns_system, baseline_system),
        "hybrid_system_distance_check": hybrid_system_distance_check(run),
        "n_routes": metric(run, "n_routes"),
        "best_solution_route_count": route_count_from_solution(run),
        "n_depot_lns_routes": metric(run, "n_depot_lns_routes"),
        "n_supplier_lns_routes": metric(run, "n_supplier_lns_routes"),
        "lns_avg_utilization": metric(run, "lns_avg_utilization"),
        "lns_min_utilization": metric(run, "lns_min_utilization"),
        "lns_max_utilization": metric(run, "lns_max_utilization"),
        "lns_trip_distances": serialize(run.metrics.get("lns_trip_distances")),
        "lns_trip_loads": serialize(run.metrics.get("lns_trip_loads")),
        "lns_trip_utilization": serialize(run.metrics.get("lns_trip_utilization")),
        "n_remove": metric(run, "n_remove"),
        "tested_n_remove_values": serialize(run.runner_summary.get("n_remove_values")),
        "n_iterations": n_iterations,
        "best_iteration": metric(run, "best_iteration"),
        "accepted_moves": accepted,
        "rejected_moves": rejected,
        "rejected_infeasible_moves": rejected_infeasible,
        "non_infeasible_rejected_moves": non_infeasible_rejected,
        "acceptance_rate": rate(accepted, n_iterations),
        "infeasible_rejection_rate": rate(rejected_infeasible, n_iterations),
        "non_infeasible_rejection_rate": rate(non_infeasible_rejected, n_iterations),
        "initial_temperature": metric(run, "initial_temperature"),
        "cooling_rate": metric(run, "cooling_rate"),
        "minimum_temperature": metric(run, "minimum_temperature"),
        "seed": metric(run, "seed"),
        "route_scope": route_scope_from_runner(run),
        "adaptive_operator_selection": metric(run, "adaptive_operator_selection"),
        "average_speed": metric(run, "average_speed"),
        "scenario_parameter_check": scenario_parameter_check(run),
        "fixed_depot_ready_time": metric(run, "fixed_depot_ready_time"),
        "fixed_depot_ready_time_label": metric(run, "fixed_depot_ready_time_label"),
        "supplier_arrival_start_time": metric(run, "supplier_arrival_start_time"),
        "supplier_arrival_start_time_label": metric(run, "supplier_arrival_start_time_label"),
        "supplier_arrival_end_time": metric(run, "supplier_arrival_end_time"),
        "supplier_arrival_end_time_label": metric(run, "supplier_arrival_end_time_label"),
        "depot_handling_time": metric(run, "depot_handling_time"),
        "depot_handling_time_minutes": metric(run, "depot_handling_time_minutes"),
        "dispatch_waves": serialize(metric(run, "dispatch_waves")),
        "dispatch_wave_labels": serialize(metric(run, "dispatch_wave_labels")),
        "working_day_end_time": metric(run, "working_day_end_time"),
        "working_day_end_time_label": metric(run, "working_day_end_time_label"),
        "depot_timing_feasibility_after_lns": timing_feasible(run),
        "n_depot_timing_routes": metric(run, "n_depot_timing_routes"),
        "n_depot_timing_feasible_routes": metric(run, "n_depot_timing_feasible_routes"),
        "n_depot_timing_infeasible_routes": metric(run, "n_depot_timing_infeasible_routes"),
        "infeasible_timing_route_ids": serialize(metric(run, "infeasible_timing_route_ids")),
        "infeasible_timing_customers": serialize(metric(run, "infeasible_timing_customers")),
        "latest_depot_route_finish_time_after_lns": metric(run, "latest_depot_route_finish_time"),
        "latest_depot_route_finish_time_after_lns_label": metric(run, "latest_depot_route_finish_time_label"),
        "avg_depot_route_duration_hours": metric(run, "avg_depot_route_duration_hours"),
        "max_depot_route_duration_hours": metric(run, "max_depot_route_duration_hours"),
        "avg_depot_route_utilization": metric(run, "avg_depot_route_utilization"),
        "routes_per_wave": serialize(metric(run, "routes_per_wave")),
        "routes_per_wave_label": serialize(metric(run, "routes_per_wave_label")),
        "n_routes_departing_before_goods_ready": metric(run, "n_routes_departing_before_goods_ready"),
        "n_routes_exceeding_working_day": metric(run, "n_routes_exceeding_working_day"),
        "n_routes_without_feasible_wave": metric(run, "n_routes_without_feasible_wave"),
        "avg_waiting_time_minutes": metric(run, "avg_waiting_time_minutes"),
        "max_waiting_time_minutes": metric(run, "max_waiting_time_minutes"),
        "timing_records_count": len(run.timing_records),
        "route_records_count": len(run.route_records),
        "accepted_infeasible_candidate_check": accepted_infeasible_candidate_check(run),
        "final_customer_coverage_summary": serialize(metric(run, "final_customer_coverage_summary")),
        "depot_customer_coverage_summary": serialize(metric(run, "depot_customer_coverage_summary")),
        "supplier_direct_coverage_summary": serialize(metric(run, "supplier_direct_coverage_summary")),
        "notes_or_warnings": " | ".join(run_warnings(run)),
    }


def fieldnames(rows: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for row in rows:
        for key in row:
            if key not in names:
                names.append(key)
    return names


def write_csv(path: Path, rows: list[dict[str, Any]], names: list[str] | None = None) -> None:
    names = names or fieldnames(rows)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=names)
        writer.writeheader()
        writer.writerows(rows)


def collect_runs(root: Path) -> list[ExtractedRun]:
    extracted: list[ExtractedRun] = []
    expected_instances = {f"{customers}c_cap{capacity}" for customers in EXPECTED_CUSTOMER_COUNTS for capacity in EXPECTED_CAPACITIES}

    for spec in SCENARIO_SPECS:
        folder = root / spec["relative_path"]
        if not folder.exists():
            for instance_name in sorted(expected_instances):
                parsed = INSTANCE_RE.match(instance_name)
                if parsed:
                    dummy_dir = folder / instance_name
                    extracted.append(load_missing_instance(dummy_dir, spec, "missing source folder"))
            continue

        seen = set()
        for instance_dir in sorted(p for p in folder.iterdir() if p.is_dir()):
            parsed = parse_instance_name(instance_dir)
            if parsed is None:
                continue
            seen.add(instance_dir.name)
            extracted.append(load_run(instance_dir, spec))

        for missing in sorted(expected_instances - seen):
            extracted.append(load_missing_instance(folder / missing, spec, "missing expected instance folder"))

    return extracted


def load_missing_instance(instance_dir: Path, spec: dict[str, Any], warning: str) -> ExtractedRun:
    parsed = parse_instance_name(instance_dir)
    customers, capacity = parsed if parsed else (0, 0)
    return ExtractedRun(
        customer_count=customers,
        vehicle_capacity=capacity,
        instance_name=instance_dir.name,
        timing_lns_scenario=str(spec["timing_lns_scenario"]),
        timing_model_family=str(spec["timing_model_family"]),
        operator_pair=str(spec["operator_pair"]),
        source_folder=str(spec["relative_path"]),
        baseline_reference_scenario=str(spec["baseline_reference_scenario"]),
        baseline_reference_folder=str(spec["baseline_reference_folder"]),
        expected_speed=spec.get("expected_speed", ""),
        expected_waves=tuple(spec["expected_waves"]),
        selected_run_timestamp="",
        latest_available_run_timestamp="",
        selected_run_is_latest_available=False,
        run_folder_count=0,
        run_dir=None,
        metrics_source_file="",
        summary_source_file="",
        metrics={},
        summary={},
        runner_summary={},
        timing_summary={},
        timing_records=[],
        route_records=[],
        warnings=[warning],
    )


def numeric(row: dict[str, Any], key: str) -> float | None:
    return as_float(row.get(key))


def comparison_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[tuple[str, str, int, int], dict[str, dict[str, Any]]] = {}
    for row in rows:
        key = (
            str(row["timing_lns_scenario"]),
            str(row["instance_name"]),
            int(row["customer_count"]),
            int(row["vehicle_capacity"]),
        )
        by_key.setdefault(key, {})[str(row["operator_pair"])] = row

    comparisons: list[dict[str, Any]] = []
    for (scenario, instance_name, customers, capacity), pair_rows in sorted(by_key.items()):
        random_row = pair_rows.get("random_regret")
        related_row = pair_rows.get("related_regret")
        random_distance = numeric(random_row or {}, "total_lns_system_distance")
        related_distance = numeric(related_row or {}, "total_lns_system_distance")
        winning_pair = ""
        distance_gap = ""
        distance_gap_pct = ""
        if random_distance is not None and related_distance is not None:
            if abs(random_distance - related_distance) <= DISTANCE_TOLERANCE:
                winning_pair = "tie"
            elif random_distance < related_distance:
                winning_pair = "random_regret"
            else:
                winning_pair = "related_regret"
            distance_gap = related_distance - random_distance
            if random_distance != 0:
                distance_gap_pct = ((related_distance - random_distance) / random_distance) * 100

        comparisons.append(
            {
                "timing_lns_scenario": scenario,
                "instance_name": instance_name,
                "customer_count": customers,
                "vehicle_capacity": capacity,
                "random_regret_total_lns_system_distance": "" if random_distance is None else random_distance,
                "random_regret_system_improvement_percent": (random_row or {}).get("system_improvement_percent", ""),
                "random_regret_n_remove": (random_row or {}).get("n_remove", ""),
                "random_regret_rejected_infeasible_moves": (random_row or {}).get("rejected_infeasible_moves", ""),
                "random_regret_timing_feasible": (random_row or {}).get("depot_timing_feasibility_after_lns", ""),
                "related_regret_total_lns_system_distance": "" if related_distance is None else related_distance,
                "related_regret_system_improvement_percent": (related_row or {}).get("system_improvement_percent", ""),
                "related_regret_n_remove": (related_row or {}).get("n_remove", ""),
                "related_regret_rejected_infeasible_moves": (related_row or {}).get("rejected_infeasible_moves", ""),
                "related_regret_timing_feasible": (related_row or {}).get("depot_timing_feasibility_after_lns", ""),
                "winning_operator_pair_by_system_distance": winning_pair,
                "related_minus_random_system_distance": distance_gap,
                "related_minus_random_system_distance_pct_of_random": distance_gap_pct,
                "notes_or_warnings": " | ".join(
                    item
                    for item in [
                        (random_row or {}).get("notes_or_warnings", ""),
                        (related_row or {}).get("notes_or_warnings", ""),
                    ]
                    if item
                ),
            }
        )
    return comparisons


def scenario_summary_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault((str(row["timing_lns_scenario"]), str(row["operator_pair"])), []).append(row)

    summary_rows: list[dict[str, Any]] = []
    for (scenario, operator_pair), group in sorted(groups.items()):
        def avg(key: str) -> Any:
            values = [numeric(row, key) for row in group]
            values = [value for value in values if value is not None]
            return mean(values) if values else ""

        timing_feasible_count = sum(1 for row in group if str(row.get("depot_timing_feasibility_after_lns")).lower() == "true")
        warnings_count = sum(1 for row in group if row.get("notes_or_warnings"))
        summary_rows.append(
            {
                "timing_lns_scenario": scenario,
                "operator_pair": operator_pair,
                "row_count": len(group),
                "timing_feasible_row_count": timing_feasible_count,
                "warning_row_count": warnings_count,
                "avg_baseline_reference_system_distance": avg("baseline_reference_system_distance"),
                "avg_total_lns_system_distance": avg("total_lns_system_distance"),
                "avg_system_improvement_percent": avg("system_improvement_percent"),
                "avg_customer_delivery_lns_distance": avg("customer_delivery_lns_distance"),
                "avg_customer_delivery_improvement_percent": avg("customer_delivery_improvement_percent"),
                "avg_n_remove": avg("n_remove"),
                "avg_accepted_moves": avg("accepted_moves"),
                "avg_rejected_moves": avg("rejected_moves"),
                "avg_rejected_infeasible_moves": avg("rejected_infeasible_moves"),
                "avg_acceptance_rate": avg("acceptance_rate"),
                "avg_lns_avg_utilization": avg("lns_avg_utilization"),
                "avg_n_routes": avg("n_routes"),
            }
        )
    return summary_rows


def baseline_comparison_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    comparison: list[dict[str, Any]] = []
    for row in rows:
        comparison.append(
            {
                "timing_lns_scenario": row["timing_lns_scenario"],
                "operator_pair": row["operator_pair"],
                "instance_name": row["instance_name"],
                "customer_count": row["customer_count"],
                "vehicle_capacity": row["vehicle_capacity"],
                "baseline_reference_scenario": row["baseline_reference_scenario"],
                "baseline_run_path": row["baseline_run_path"],
                "baseline_reference_system_distance": row["baseline_reference_system_distance"],
                "total_lns_system_distance": row["total_lns_system_distance"],
                "system_improvement_distance": row["system_improvement_distance"],
                "system_improvement_percent": row["system_improvement_percent"],
                "baseline_reference_customer_delivery_distance": row["baseline_reference_customer_delivery_distance"],
                "customer_delivery_lns_distance": row["customer_delivery_lns_distance"],
                "customer_delivery_improvement_distance": row["customer_delivery_improvement_distance"],
                "customer_delivery_improvement_percent": row["customer_delivery_improvement_percent"],
                "supplier_depot_replenishment_distance": row["supplier_depot_replenishment_distance"],
                "depot_timing_feasibility_after_lns": row["depot_timing_feasibility_after_lns"],
                "n_depot_timing_infeasible_routes": row["n_depot_timing_infeasible_routes"],
                "latest_depot_route_finish_time_after_lns_label": row["latest_depot_route_finish_time_after_lns_label"],
                "n_remove": row["n_remove"],
                "rejected_infeasible_moves": row["rejected_infeasible_moves"],
                "notes_or_warnings": row["notes_or_warnings"],
            }
        )
    return comparison


def expected_keys() -> set[tuple[str, str, str]]:
    return {
        (scenario, operator_pair, f"{customers}c_cap{capacity}")
        for scenario in ("fixed_split", "wave_speed40_split", "wave_speed30_14wave_split")
        for operator_pair in ("random_regret", "related_regret")
        for customers in EXPECTED_CUSTOMER_COUNTS
        for capacity in EXPECTED_CAPACITIES
    }


def write_summary(path: Path, rows: list[dict[str, Any]], comparisons: list[dict[str, Any]], scenario_summaries: list[dict[str, Any]]) -> None:
    keys = {(row["timing_lns_scenario"], row["operator_pair"], row["instance_name"]) for row in rows}
    missing = sorted(expected_keys() - keys)
    warning_rows = [row for row in rows if row.get("notes_or_warnings")]
    parameter_counts: dict[str, int] = {}
    for row in rows:
        key = str(row.get("scenario_parameter_check", ""))
        parameter_counts[key] = parameter_counts.get(key, 0) + 1

    lines = [
        "# Section 6.8 Time-Aware LNS Extraction Summary",
        "",
        "## Scope",
        "",
        "This extraction covers only Case 3 Hybrid + KMeans timing-aware LNS rows:",
        "",
        "- fixed timing + split repair with random-regret and related-regret;",
        "- dispatch-wave split repair with speed40 and random-regret / related-regret;",
        "- dispatch-wave split repair with speed30 plus a 14:00 wave and random-regret / related-regret.",
        "",
        "Non-timing LNS, Case 1, Case 2, Sweep, no-clustering, and route-first timing folders are excluded from the main table.",
        "",
        "## Output Files",
        "",
        f"- `{OUTPUT_LONG_CSV}`",
        f"- `{OUTPUT_OPERATOR_CSV}`",
        f"- `{OUTPUT_SCENARIO_CSV}`",
        f"- `{OUTPUT_BASELINE_CSV}`",
        "",
        "## Completeness",
        "",
        f"- Expected rows: 126",
        f"- Extracted rows: {len(rows)}",
        f"- Missing expected rows: {len(missing)}",
        f"- Operator-comparison rows: {len(comparisons)}",
        f"- Scenario/operator summary rows: {len(scenario_summaries)}",
        f"- Rows with warnings: {len(warning_rows)}",
        "",
        "## Scenario Parameter Checks",
        "",
        "| Check status | Row count |",
        "|---|---:|",
    ]
    for key, count in sorted(parameter_counts.items()):
        lines.append(f"| {key} | {count} |")

    lines.extend(["", "## Scenario/Operator Row Counts", "", "| Timing scenario | Operator pair | Rows | Timing-feasible rows | Avg system improvement percent |", "|---|---|---:|---:|---:|"])
    for row in scenario_summaries:
        lines.append(
            "| {timing_lns_scenario} | {operator_pair} | {row_count} | {timing_feasible_row_count} | {avg_system_improvement_percent} |".format(
                **row
            )
        )

    if missing:
        lines.extend(["", "## Missing Rows", ""])
        for scenario, operator_pair, instance in missing:
            lines.append(f"- {scenario} / {operator_pair} / {instance}")

    if warning_rows:
        lines.extend(["", "## Warning Rows", ""])
        for row in warning_rows[:80]:
            lines.append(
                f"- {row['timing_lns_scenario']} / {row['operator_pair']} / {row['instance_name']} / "
                f"{row['selected_run_timestamp']}: {row['notes_or_warnings']}"
            )
        if len(warning_rows) > 80:
            lines.append(f"- ... {len(warning_rows) - 80} additional warning rows omitted from this summary.")

    lines.extend(
        [
            "",
            "## Extraction Notes",
            "",
            "- The extractor prefers `lns_sa_metrics_best.json` and `lns_sa_summary_best.json`.",
            "- The selected run must match the intended timing scenario, speed/wave setting, and operator pair where these fields are recorded.",
            "- If a newer timestamp does not match the expected scenario, the latest matching run is selected and the ignored newer timestamp is recorded.",
            "- `total_lns_system_distance` is the main Hybrid timing-aware LNS distance because it includes customer-delivery distance and supplier-to-depot replenishment distance.",
            "- Timing-infeasible candidate acceptance is checked only from saved feasibility evidence where available; missing iteration-level feasibility records are reported conservatively.",
        ]
    )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    root = project_root()
    output_dir = root / OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    runs = collect_runs(root)
    rows = [long_row(run) for run in runs]
    rows.sort(key=lambda row: (row["timing_lns_scenario"], row["operator_pair"], int(row["customer_count"]), int(row["vehicle_capacity"])))

    comparisons = comparison_rows(rows)
    scenario_summaries = scenario_summary_rows(rows)
    baseline_rows = baseline_comparison_rows(rows)

    write_csv(output_dir / OUTPUT_LONG_CSV, rows)
    write_csv(output_dir / OUTPUT_OPERATOR_CSV, comparisons)
    write_csv(output_dir / OUTPUT_SCENARIO_CSV, scenario_summaries)
    write_csv(output_dir / OUTPUT_BASELINE_CSV, baseline_rows)
    write_summary(output_dir / OUTPUT_SUMMARY, rows, comparisons, scenario_summaries)

    warning_count = sum(1 for row in rows if row.get("notes_or_warnings"))
    print(f"Wrote {len(rows)} Section 6.8 rows to {output_dir / OUTPUT_LONG_CSV}")
    print(f"Wrote {len(comparisons)} operator-pair comparison rows")
    print(f"Wrote {len(scenario_summaries)} scenario/operator summary rows")
    print(f"Wrote {len(baseline_rows)} baseline-vs-LNS rows")
    print(f"Rows with warnings: {warning_count}")


if __name__ == "__main__":
    main()
