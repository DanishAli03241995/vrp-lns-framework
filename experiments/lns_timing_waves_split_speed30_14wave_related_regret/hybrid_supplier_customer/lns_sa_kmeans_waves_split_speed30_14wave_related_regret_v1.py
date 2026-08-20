"""
Case 3: Hybrid Supplier-Customer + KMeans + dispatch-wave split repair + LNS-SA.

Timing variant:
- dispatch-wave depot timing;
- speed30 + added 14:00-wave sensitivity baseline is used;
- same-wave split repair has already been applied in the baseline timing run;
- LNS starts from the split-repaired dispatch-wave solution;
- depot-side LNS is dispatch-wave aware and works inside each wave bucket;
- supplier-direct LNS keeps the original Shaw-style Related Removal + Regret-2 logic.

Operator pair:
- Shaw-style Related Removal
- Regret-2 Insertion

This is not adaptive LNS. The operator pair is fixed throughout the run.
"""

import importlib
import json
import math
import os
import sys


ROOT_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(__file__)
        )
    )
)
sys.path.append(ROOT_DIR)
os.environ.setdefault("MPLCONFIGDIR", os.path.join(ROOT_DIR, ".matplotlib_cache"))


from instances.generate_supplier_customer_instance import (
    generate_supplier_customer_instance,
)
from utils.plot_routes import plot_supplier_routes


dispatch_wave_lns_module = importlib.import_module(
    "metaheuristics.operator_pair_engines."
    "lns_sa_related_regret_dispatch_wave_speed30_14wave_v1"
)
standard_lns_module = importlib.import_module(
    "metaheuristics.operator_pair_engines.lns_sa_related_regret_v1"
)

run_lns_sa_related_regret_dispatch_wave_timing = (
    dispatch_wave_lns_module.run_lns_sa_related_regret_dispatch_wave_timing
)
run_lns_sa_related_regret = standard_lns_module.run_lns_sa_related_regret


# =====================================================
# Folder and JSON helpers
# =====================================================


def get_latest_run_folder(instance_path):
    """Return the latest run_* folder inside an instance result folder."""
    run_folders = []

    for folder in os.listdir(instance_path):
        full_path = os.path.join(instance_path, folder)

        if os.path.isdir(full_path) and folder.startswith("run_"):
            run_folders.append(folder)

    if not run_folders:
        raise FileNotFoundError(
            f"No run_* folders found under: {instance_path}"
        )

    run_folders.sort()
    return os.path.join(instance_path, run_folders[-1])


def load_json(path):
    """Load a JSON file."""
    with open(path, "r") as file_handle:
        return json.load(file_handle)


def write_json(path, payload):
    """Write a JSON file with indentation."""
    with open(path, "w") as file_handle:
        json.dump(payload, file_handle, indent=4)


# =====================================================
# Route, distance, and metric helpers
# =====================================================


def remove_empty_routes(solution):
    """Keep only routes that serve at least one customer."""
    return [route for route in solution if len(route) > 2]


def normalize_route(route):
    """Convert JSON-loaded route values to integer customer ids."""
    return [int(node) for node in route]


def normalize_routes(routes):
    """Normalize a list of routes."""
    return [normalize_route(route) for route in routes]


def collect_customers_from_routes(routes):
    """Collect all non-depot customers from a list of routes."""
    customers = []

    for route in routes:
        for node in route:
            if node != 0:
                customers.append(node)

    return customers


def validate_customer_coverage(routes, expected_customers):
    """Check that expected customers are served exactly once."""
    served_customers = collect_customers_from_routes(routes)
    served_set = set(served_customers)
    expected_set = set(expected_customers)

    duplicate_customers = sorted({
        customer_id
        for customer_id in served_customers
        if served_customers.count(customer_id) > 1
    })
    missing_customers = sorted(expected_set - served_set)
    extra_customers = sorted(served_set - expected_set)

    return {
        "all_customers_served_exactly_once": (
            len(duplicate_customers) == 0
            and len(missing_customers) == 0
            and len(extra_customers) == 0
        ),
        "n_expected_customers": len(expected_set),
        "n_served_customers": len(served_set),
        "duplicate_customers": duplicate_customers,
        "missing_customers": missing_customers,
        "extra_customers": extra_customers,
    }


def compute_trip_distance(trip, routing_distance):
    """Compute one route distance."""
    trip_distance = 0

    for index in range(len(trip) - 1):
        trip_distance += routing_distance(trip[index], trip[index + 1])

    return trip_distance


def compute_solution_distance(routes, routing_distance):
    """Compute total distance for a list of routes."""
    return sum(compute_trip_distance(route, routing_distance) for route in routes)


def compute_trip_load(trip, demand):
    """Compute one route load."""
    trip_load = 0

    for customer in trip[1:-1]:
        trip_load += demand[customer]

    return trip_load


def build_trip_metrics(solution, demand, vehicle_capacity, routing_distance):
    """Build per-trip distance, load, and utilization lists."""
    trip_distances = []
    trip_loads = []
    trip_utilization = []

    for trip in remove_empty_routes(solution):
        trip_distance = compute_trip_distance(trip, routing_distance)
        trip_load = compute_trip_load(trip, demand)

        trip_distances.append(trip_distance)
        trip_loads.append(trip_load)
        trip_utilization.append(trip_load / vehicle_capacity)

    return trip_distances, trip_loads, trip_utilization


def safe_percent(numerator, denominator):
    """Return percentage while avoiding division by zero."""
    if not denominator:
        return 0

    return (numerator / denominator) * 100


def format_hour(hour_value):
    """Delegate time formatting to the dispatch-wave LNS utility."""
    return dispatch_wave_lns_module.format_hour(hour_value)


# =====================================================
# Baseline data extraction helpers
# =====================================================


def collect_customer_data_from_supplier_metrics(supplier_metrics):
    """Collect all customer coordinates and demands from supplier subproblems."""
    customer_cord = {}
    demand = {}

    for supplier_data in supplier_metrics.values():
        for customer_id, coord in supplier_data["customer_cord"].items():
            customer_cord[int(customer_id)] = coord

        for customer_id, demand_value in supplier_data["demand"].items():
            demand[int(customer_id)] = demand_value

    demand[0] = 0

    return customer_cord, demand


def load_instance_data(latest_run_path, metrics):
    """Load instance data from config_used.json when available."""
    config_path = os.path.join(latest_run_path, "config_used.json")
    supplier_metrics = metrics["supplier_metrics"]

    if os.path.exists(config_path):
        config = load_json(config_path)
        instance = generate_supplier_customer_instance(config)

        return {
            "customer_cord": instance["customer_cord"],
            "demand": instance["demand"],
            "service_time": instance["service_time"],
            "average_speed": instance["average_speed"],
            "config_source": config,
        }

    customer_cord, demand = collect_customer_data_from_supplier_metrics(
        supplier_metrics
    )

    service_time = {
        customer_id: 10
        for customer_id in customer_cord
    }
    average_speed = metrics.get("average_speed", 30)

    return {
        "customer_cord": customer_cord,
        "demand": demand,
        "service_time": service_time,
        "average_speed": average_speed,
        "config_source": "config_used.json_missing_default_speed30_14wave_service10_used",
    }


def get_expected_customer_sets(metrics):
    """Extract depot, supplier-direct, and overall customer sets from metrics."""
    depot_expected_customers = [
        int(customer_id)
        for customer_id in metrics.get("depot_customer_ids", [])
    ]
    supplier_direct_expected_customers = [
        int(customer_id)
        for customer_id in metrics.get("supplier_direct_customer_ids", [])
    ]

    if not depot_expected_customers:
        depot_expected_customers = collect_customers_from_routes([
            normalize_route(record["trip"])
            for record in metrics.get("post_reloc_2opt_route_records", [])
            if record.get("origin_type") == "depot"
        ])

    if not supplier_direct_expected_customers:
        supplier_direct_expected_customers = []

        for supplier_data in metrics["supplier_metrics"].values():
            supplier_direct_expected_customers.extend(
                collect_customers_from_routes(
                    normalize_routes(supplier_data["route_post_reloc_2opt"])
                )
            )

    all_expected_customers = sorted(
        set(depot_expected_customers) | set(supplier_direct_expected_customers)
    )

    return (
        sorted(set(depot_expected_customers)),
        sorted(set(supplier_direct_expected_customers)),
        all_expected_customers,
    )


def extract_depot_timing_records(metrics):
    """Extract final post-repair depot timing records from metrics."""
    records = metrics.get("depot_timing_route_records", [])

    if not records:
        records = metrics.get("depot_timing_wave_records", [])

    if records:
        normalized_records = []

        for record in records:
            normalized_record = dict(record)
            normalized_record["trip"] = normalize_route(record["trip"])
            normalized_record["customers"] = [
                int(customer_id)
                for customer_id in record.get("customers", normalized_record["trip"][1:-1])
            ]
            normalized_records.append(normalized_record)

        return normalized_records

    # Fallback: use route records if detailed timing records are missing.
    fallback_records = []

    for route_id, record in enumerate(metrics.get("post_reloc_2opt_route_records", []), start=1):
        if record.get("origin_type") != "depot":
            continue

        trip = normalize_route(record["trip"])
        dispatch_wave = record.get("dispatch_wave")

        fallback_records.append({
            "route_id": route_id,
            "origin_type": "depot",
            "trip": trip,
            "customers": trip[1:-1],
            "constructed_dispatch_wave": dispatch_wave,
            "constructed_dispatch_wave_label": format_hour(dispatch_wave),
        })

    return fallback_records


def group_depot_records_by_dispatch_wave(depot_timing_records):
    """Group final depot routes by their constructed dispatch wave."""
    routes_by_wave = {}

    for record in depot_timing_records:
        wave = record.get("constructed_dispatch_wave")

        if wave is None:
            wave = record.get("dispatch_wave")

        if wave is None:
            raise ValueError(
                "Depot timing record is missing constructed_dispatch_wave."
            )

        routes_by_wave.setdefault(float(wave), [])
        routes_by_wave[float(wave)].append(normalize_route(record["trip"]))

    return routes_by_wave


def extract_customer_wave_maps(metrics):
    """Build supplier-arrival, goods-ready, and assigned-wave maps."""
    timing_records = metrics.get("depot_customer_wave_timing_records", [])

    if not timing_records:
        raise ValueError(
            "depot_customer_wave_timing_records are required for dispatch-wave LNS."
        )

    supplier_arrival_times = {}
    goods_ready_times = {}
    customer_dispatch_waves = {}

    for record in timing_records:
        customer_id = int(record["customer_id"])
        supplier_arrival_times[customer_id] = record.get("supplier_arrival_time")
        goods_ready_times[customer_id] = record.get("goods_ready_time")
        customer_dispatch_waves[customer_id] = record.get("assigned_dispatch_wave")

    return supplier_arrival_times, goods_ready_times, customer_dispatch_waves


def extract_supplier_direct_initial_solution(supplier_data):
    """Extract supplier-direct routes for one supplier."""
    return remove_empty_routes(
        normalize_routes(supplier_data["route_post_reloc_2opt"])
    )


# =====================================================
# Distance functions
# =====================================================


def build_depot_routing_distance(depot_cord, customer_cord):
    """Create a distance function for depot-origin routes."""
    def depot_routing_distance(i, j):
        if i == 0:
            coord_i = depot_cord
        else:
            coord_i = customer_cord[i]

        if j == 0:
            coord_j = depot_cord
        else:
            coord_j = customer_cord[j]

        x1, y1 = coord_i
        x2, y2 = coord_j

        return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)

    return depot_routing_distance


def build_supplier_routing_distance(supplier_origin, supplier_customer_cord):
    """Create a distance function for supplier-origin routes."""
    def supplier_routing_distance(i, j):
        if i == 0:
            coord_i = supplier_origin
        else:
            coord_i = supplier_customer_cord[i]

        if j == 0:
            coord_j = supplier_origin
        else:
            coord_j = supplier_customer_cord[j]

        x1, y1 = coord_i
        x2, y2 = coord_j

        return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)

    return supplier_routing_distance


# =====================================================
# Output helpers
# =====================================================


def build_default_output_path(instance_name):
    """Default output path when no runner output_path is provided."""
    return os.path.join(
        ROOT_DIR,
        "results",
        "lns_timing_waves_split_speed30_14wave_related_regret",
        "case3_kmeans",
        instance_name,
    )


def renumber_depot_timing_records(records):
    """Renumber combined depot records after wave-by-wave LNS."""
    renumbered_records = []

    for index, record in enumerate(records, start=1):
        renumbered_record = dict(record)
        renumbered_record["route_id"] = index
        renumbered_records.append(renumbered_record)

    return renumbered_records


def add_depot_timing_record_metadata(records):
    """Add consistent experiment metadata to depot LNS records."""
    enriched_records = []

    for record in records:
        enriched_record = dict(record)
        enriched_record["supplier_region_id"] = "global_depot_pool_by_dispatch_wave"
        enriched_record["routing_scope"] = "global_depot_pool_by_dispatch_wave"
        enriched_record["timing_stage"] = "after_time_aware_lns"
        enriched_record["operator_pair"] = "related_regret_dispatch_wave_speed30_14wave"
        enriched_records.append(enriched_record)

    return enriched_records


# =====================================================
# Main experiment entry point
# =====================================================


def run_lns_sa_experiment(
    instance_name,
    n_iterations=50,
    n_remove=4,
    seed=42,
    initial_temperature=10.0,
    cooling_rate=0.95,
    minimum_temperature=0.01,
    related_removal_randomness=0.2,
    distance_weight=1.0,
    demand_weight=0.2,
    route_weight=1.0,
    output_path=None,
):
    """Run dispatch-wave speed30 + 14:00-wave split-repair LNS for one instance."""
    baseline_results_name = "hybrid_supplier_customer_kmeans_timing_waves_constructed_split_14wave_v1"
    base_results_path = os.path.join(
        ROOT_DIR,
        "results",
        baseline_results_name,
        instance_name,
    )

    if not os.path.exists(base_results_path):
        fallback_name = "hybrid_supplier_customer_kmeans_timing_waves_constructed_split_v1"
        fallback_path = os.path.join(
            ROOT_DIR,
            "results",
            fallback_name,
            instance_name,
        )

        if os.path.exists(fallback_path):
            baseline_results_name = fallback_name
            base_results_path = fallback_path

    latest_run_path = get_latest_run_folder(base_results_path)

    print("\n===================================")
    print("LATEST DISPATCH-WAVE SPEED30 + 14:00 WAVE + SPLIT BASELINE RUN FOLDER")
    print("===================================")
    print(latest_run_path)

    save_path = output_path or build_default_output_path(instance_name)
    os.makedirs(save_path, exist_ok=True)

    print("\n===================================")
    print("DISPATCH-WAVE SPEED30 + 14:00 WAVE SPLIT + RELATED REGRET LNS OUTPUT FOLDER")
    print("===================================")
    print(save_path)

    metrics_path = os.path.join(latest_run_path, "metrics.json")
    metrics = load_json(metrics_path)

    supplier_metrics = metrics["supplier_metrics"]
    vehicle_capacity = metrics["vehicle_capacity"]
    depot_cord = metrics["depot"]
    supplier_cord = {
        int(supplier_id): coord
        for supplier_id, coord in metrics["supplier_cord"].items()
    }
    dispatch_waves = metrics.get("dispatch_waves", [9.0, 11.0, 13.0, 14.0, 15.0])
    dispatch_waves = [float(wave) for wave in dispatch_waves]
    working_day_end_time = metrics.get("working_day_end_time", 18.0)

    instance_data = load_instance_data(
        latest_run_path=latest_run_path,
        metrics=metrics,
    )
    customer_cord = instance_data["customer_cord"]
    demand = instance_data["demand"]
    service_time = instance_data["service_time"]
    average_speed = instance_data["average_speed"]
    lns_config_source = instance_data["config_source"]

    if average_speed != 30:
        print("\nWARNING: speed30 + 14:00-wave LNS case expected average_speed = 30.")
        print("Loaded average_speed:", average_speed)

    if 14.0 not in dispatch_waves:
        raise ValueError(
            "Case 6 expects dispatch_waves to include 14.0. "
            f"Loaded dispatch_waves: {dispatch_waves}"
        )

    (
        depot_expected_customers,
        supplier_direct_expected_customers,
        all_expected_customers,
    ) = get_expected_customer_sets(metrics)

    (
        supplier_arrival_times,
        goods_ready_times,
        customer_dispatch_waves,
    ) = extract_customer_wave_maps(metrics)

    reference_distance = metrics["post_reloc_2opt_distance"]
    supplier_depot_replenishment_distance = metrics.get(
        "supplier_depot_replenishment_distance",
        metrics.get("total_first_echelon_distance", 0),
    )
    supplier_depot_replenishment_metrics = metrics.get(
        "supplier_depot_replenishment_metrics",
        {},
    )
    baseline_reference_system_distance = metrics.get(
        "post_reloc_2opt_total_system_distance",
        reference_distance + supplier_depot_replenishment_distance,
    )

    all_lns_routes = []
    lns_route_records = []
    lns_trip_distances = []
    lns_trip_loads = []
    lns_trip_utilization = []
    operator_records = {
        "depot_by_wave": {},
        "suppliers": {},
    }

    total_lns_distance = 0
    depot_lns_distance = 0
    supplier_lns_distance = 0
    accepted_moves = 0
    rejected_moves = 0
    rejected_infeasible_moves = 0

    depot_lns_metrics = {}
    supplier_lns_metrics = {}
    depot_timing_lns_records = []

    # =====================================================
    # Depot-side dispatch-wave-aware LNS
    # =====================================================

    depot_timing_records = extract_depot_timing_records(metrics)
    depot_routes_by_wave = group_depot_records_by_dispatch_wave(
        depot_timing_records
    )
    depot_routing_distance = build_depot_routing_distance(
        depot_cord=depot_cord,
        customer_cord=customer_cord,
    )

    depot_reference_distance = 0

    for wave, wave_initial_solution in sorted(depot_routes_by_wave.items()):
        wave_initial_solution = remove_empty_routes(wave_initial_solution)

        if not wave_initial_solution:
            continue

        print("\n===================================")
        print(f"DEPOT-SIDE DISPATCH-WAVE RELATED-REGRET LNS - {format_hour(wave)}")
        print("===================================")
        print("Initial depot wave solution:")
        print(wave_initial_solution)

        wave_reference_distance = compute_solution_distance(
            wave_initial_solution,
            depot_routing_distance,
        )
        depot_reference_distance += wave_reference_distance

        wave_best_solution, wave_best_distance, wave_summary = (
            run_lns_sa_related_regret_dispatch_wave_timing(
                initial_solution=wave_initial_solution,
                constructed_dispatch_wave=wave,
                customer_coordinates=customer_cord,
                demand=demand,
                vehicle_capacity=vehicle_capacity,
                routing_distance=depot_routing_distance,
                average_speed=average_speed,
                service_time=service_time,
                supplier_arrival_times=supplier_arrival_times,
                goods_ready_times=goods_ready_times,
                customer_dispatch_waves=customer_dispatch_waves,
                dispatch_waves=dispatch_waves,
                working_day_end_time=working_day_end_time,
                n_iterations=n_iterations,
                n_remove=n_remove,
                seed=seed,
                initial_temperature=initial_temperature,
                cooling_rate=cooling_rate,
                minimum_temperature=minimum_temperature,
                related_removal_randomness=related_removal_randomness,
                distance_weight=distance_weight,
                demand_weight=demand_weight,
                route_weight=route_weight,
            )
        )
        wave_best_solution = remove_empty_routes(wave_best_solution)

        depot_lns_distance += wave_best_distance
        total_lns_distance += wave_best_distance
        accepted_moves += wave_summary["accepted_moves"]
        rejected_moves += wave_summary["rejected_moves"]
        rejected_infeasible_moves += wave_summary["rejected_infeasible_moves"]
        operator_records["depot_by_wave"][str(wave)] = wave_summary["records"]

        wave_timing_records = add_depot_timing_record_metadata(
            wave_summary["best_timing_records"]
        )
        depot_timing_lns_records.extend(wave_timing_records)

        (
            wave_trip_distances,
            wave_trip_loads,
            wave_trip_utilization,
        ) = build_trip_metrics(
            wave_best_solution,
            demand,
            vehicle_capacity,
            depot_routing_distance,
        )

        wave_key = format_hour(wave)
        depot_lns_metrics[wave_key] = {
            "dispatch_wave": wave,
            "dispatch_wave_label": wave_key,
            "initial_distance": wave_reference_distance,
            "lns_distance": wave_best_distance,
            "improvement_distance": wave_reference_distance - wave_best_distance,
            "improvement_percent": safe_percent(
                wave_reference_distance - wave_best_distance,
                wave_reference_distance,
            ),
            "n_routes": len(wave_best_solution),
            "lns_trip_distances": wave_trip_distances,
            "lns_trip_loads": wave_trip_loads,
            "lns_trip_utilization": wave_trip_utilization,
            "operator_pair": wave_summary["operator_pair"],
            "destroy_operator": wave_summary["destroy_operator"],
            "repair_operator": wave_summary["repair_operator"],
            "best_iteration": wave_summary["best_iteration"],
            "accepted_moves": wave_summary["accepted_moves"],
            "rejected_moves": wave_summary["rejected_moves"],
            "rejected_infeasible_moves": wave_summary[
                "rejected_infeasible_moves"
            ],
            "initial_timing_summary": wave_summary["initial_timing_summary"],
            "lns_timing_summary": wave_summary["best_timing_summary"],
            "initial_coverage_summary": wave_summary["initial_coverage_summary"],
            "lns_coverage_summary": wave_summary["best_coverage_summary"],
            "route_lns_sa": wave_best_solution,
        }

        lns_trip_distances.extend(wave_trip_distances)
        lns_trip_loads.extend(wave_trip_loads)
        lns_trip_utilization.extend(wave_trip_utilization)

        for trip in wave_best_solution:
            all_lns_routes.append(trip)
            lns_route_records.append({
                "origin_type": "depot",
                "routing_scope": "global_depot_pool_by_dispatch_wave",
                "timing_model": "depot_dispatch_waves_speed30_14wave_lns",
                "dispatch_wave": wave,
                "dispatch_wave_label": format_hour(wave),
                "supplier_region_id": "global_depot_pool_by_dispatch_wave",
                "trip": trip,
            })

    depot_timing_lns_records = renumber_depot_timing_records(
        depot_timing_lns_records
    )
    depot_timing_lns_summary = (
        dispatch_wave_lns_module.summarize_dispatch_wave_records(
            depot_timing_lns_records
        )
    )
    depot_lns_coverage_summary = validate_customer_coverage(
        routes=[
            record["trip"]
            for record in lns_route_records
            if record["origin_type"] == "depot"
        ],
        expected_customers=depot_expected_customers,
    )

    # =====================================================
    # Supplier-direct standard LNS
    # =====================================================

    for supplier_id, supplier_data in supplier_metrics.items():
        initial_solution = extract_supplier_direct_initial_solution(supplier_data)

        if not initial_solution:
            continue

        print("\n===================================")
        print(f"SUPPLIER-DIRECT RELATED REGRET LNS - SUPPLIER {supplier_id}")
        print("===================================")
        print("Initial supplier solution:")
        print(initial_solution)

        supplier_origin = supplier_data["origin"]
        supplier_customer_cord = {
            int(customer_id): coord
            for customer_id, coord in supplier_data["customer_cord"].items()
        }
        supplier_demand = {
            int(customer_id): demand_value
            for customer_id, demand_value in supplier_data["demand"].items()
        }
        supplier_demand[0] = 0

        supplier_routing_distance = build_supplier_routing_distance(
            supplier_origin=supplier_origin,
            supplier_customer_cord=supplier_customer_cord,
        )

        supplier_best_solution, supplier_best_distance, supplier_summary = (
            run_lns_sa_related_regret(
                initial_solution=initial_solution,
                customer_coordinates=supplier_customer_cord,
                demand=supplier_demand,
                vehicle_capacity=vehicle_capacity,
                routing_distance=supplier_routing_distance,
                n_iterations=n_iterations,
                n_remove=n_remove,
                seed=seed,
                initial_temperature=initial_temperature,
                cooling_rate=cooling_rate,
                minimum_temperature=minimum_temperature,
                related_removal_randomness=related_removal_randomness,
                distance_weight=distance_weight,
                demand_weight=demand_weight,
                route_weight=route_weight,
            )
        )
        supplier_best_solution = remove_empty_routes(supplier_best_solution)

        supplier_lns_distance += supplier_best_distance
        total_lns_distance += supplier_best_distance
        accepted_moves += supplier_summary["accepted_moves"]
        rejected_moves += supplier_summary["rejected_moves"]
        operator_records["suppliers"][str(supplier_id)] = supplier_summary[
            "records"
        ]

        (
            supplier_trip_distances,
            supplier_trip_loads,
            supplier_trip_utilization,
        ) = build_trip_metrics(
            supplier_best_solution,
            supplier_demand,
            vehicle_capacity,
            supplier_routing_distance,
        )

        supplier_reference_distance = supplier_data["post_reloc_2opt_distance"]
        supplier_direct_customer_ids = collect_customers_from_routes(
            initial_solution
        )
        supplier_coverage_summary = validate_customer_coverage(
            routes=supplier_best_solution,
            expected_customers=supplier_direct_customer_ids,
        )

        supplier_lns_metrics[str(supplier_id)] = {
            "initial_distance": supplier_reference_distance,
            "lns_distance": supplier_best_distance,
            "improvement_distance": (
                supplier_reference_distance - supplier_best_distance
            ),
            "improvement_percent": safe_percent(
                supplier_reference_distance - supplier_best_distance,
                supplier_reference_distance,
            ),
            "n_routes": len(supplier_best_solution),
            "lns_trip_distances": supplier_trip_distances,
            "lns_trip_loads": supplier_trip_loads,
            "lns_trip_utilization": supplier_trip_utilization,
            "operator_pair": supplier_summary["operator_pair"],
            "destroy_operator": supplier_summary["destroy_operator"],
            "repair_operator": supplier_summary["repair_operator"],
            "best_iteration": supplier_summary["best_iteration"],
            "accepted_moves": supplier_summary["accepted_moves"],
            "rejected_moves": supplier_summary["rejected_moves"],
            "coverage_summary": supplier_coverage_summary,
            "route_lns_sa": supplier_best_solution,
        }

        lns_trip_distances.extend(supplier_trip_distances)
        lns_trip_loads.extend(supplier_trip_loads)
        lns_trip_utilization.extend(supplier_trip_utilization)

        for trip in supplier_best_solution:
            all_lns_routes.append(trip)
            lns_route_records.append({
                "origin_type": "supplier",
                "supplier_id": int(supplier_id),
                "trip": trip,
            })

    # =====================================================
    # Final validation and output metrics
    # =====================================================

    final_customer_coverage_summary = validate_customer_coverage(
        routes=all_lns_routes,
        expected_customers=all_expected_customers,
    )
    supplier_direct_coverage_summary = validate_customer_coverage(
        routes=[
            record["trip"]
            for record in lns_route_records
            if record["origin_type"] == "supplier"
        ],
        expected_customers=supplier_direct_expected_customers,
    )
    depot_customer_coverage_summary = validate_customer_coverage(
        routes=[
            record["trip"]
            for record in lns_route_records
            if record["origin_type"] == "depot"
        ],
        expected_customers=depot_expected_customers,
    )

    improvement_distance = reference_distance - total_lns_distance
    improvement_percent = safe_percent(improvement_distance, reference_distance)

    total_lns_system_distance = (
        total_lns_distance + supplier_depot_replenishment_distance
    )
    system_improvement_distance = (
        baseline_reference_system_distance - total_lns_system_distance
    )
    system_improvement_percent = safe_percent(
        system_improvement_distance,
        baseline_reference_system_distance,
    )

    overall_feasible_with_dispatch_wave_lns = (
        final_customer_coverage_summary["all_customers_served_exactly_once"]
        and depot_timing_lns_summary["depot_timing_feasibility"]
    )

    write_json(
        os.path.join(save_path, "route_lns_sa_records.json"),
        lns_route_records,
    )
    write_json(
        os.path.join(save_path, "operator_pair_records.json"),
        operator_records,
    )
    write_json(
        os.path.join(save_path, "depot_timing_wave_lns_records.json"),
        depot_timing_lns_records,
    )
    write_json(
        os.path.join(save_path, "depot_timing_wave_lns_summary.json"),
        depot_timing_lns_summary,
    )

    with open(os.path.join(save_path, "route_lns_sa.txt"), "w") as file_handle:
        file_handle.write(str(all_lns_routes))

    with open(
        os.path.join(save_path, "route_lns_sa_dispatch_wave_speed30_14wave_related_regret.txt"),
        "w",
    ) as file_handle:
        file_handle.write(str(all_lns_routes))

    lns_metrics = {
        "algorithm": (
            "hybrid_supplier_customer_kmeans_waves_split_speed30_14wave_"
            "lns_related_regret_v1"
        ),
        "case": "Case_3_hybrid_supplier_customer",
        "clustering": "kmeans",
        "timing_model": (
            "depot_dispatch_waves_wave_constructed_with_duration_split_repair_"
            "speed30_14wave_and_lns"
        ),
        "base_timing_model": metrics.get("timing_model"),
        "operator_pair": "related_regret_dispatch_wave_speed30_14wave",
        "destroy_operator": "shaw_related_removal",
        "repair_operator": "regret_2_insertion_dispatch_wave_timing_for_depot",
        "supplier_direct_destroy_operator": "shaw_related_removal",
        "supplier_direct_repair_operator": "regret_2_insertion",
        "adaptive_operator_selection": False,
        "instance": instance_name,
        "n_iterations": n_iterations,
        "n_remove": n_remove,
        "seed": seed,
        "initial_temperature": initial_temperature,
        "cooling_rate": cooling_rate,
        "minimum_temperature": minimum_temperature,
        "related_removal_randomness": related_removal_randomness,
        "distance_weight": distance_weight,
        "demand_weight": demand_weight,
        "route_weight": route_weight,
        "supplier_arrival_start_time": metrics.get("supplier_arrival_start_time"),
        "supplier_arrival_start_time_label": metrics.get("supplier_arrival_start_time_label"),
        "supplier_arrival_end_time": metrics.get("supplier_arrival_end_time"),
        "supplier_arrival_end_time_label": metrics.get("supplier_arrival_end_time_label"),
        "depot_handling_time": metrics.get("depot_handling_time"),
        "depot_handling_time_minutes": metrics.get("depot_handling_time_minutes"),
        "dispatch_waves": dispatch_waves,
        "dispatch_wave_labels": [format_hour(wave) for wave in dispatch_waves],
        "working_day_end_time": working_day_end_time,
        "working_day_end_time_label": format_hour(working_day_end_time),
        "average_speed": average_speed,
        "speed_sensitivity_case": 30,
        "dispatch_policy_sensitivity_case": "added_14_00_wave",
        "accepted_moves": accepted_moves,
        "rejected_moves": rejected_moves,
        "rejected_infeasible_moves": rejected_infeasible_moves,
        "supplier_count": len(supplier_metrics),
        "baseline_reference_algorithm": metrics["algorithm"],
        "baseline_results_name_used": baseline_results_name,
        "baseline_run_path": latest_run_path,
        "lns_output_path": save_path,
        "baseline_config_source": lns_config_source,
        "baseline_reference_distance": reference_distance,
        "baseline_reference_customer_delivery_distance": reference_distance,
        "baseline_reference_system_distance": baseline_reference_system_distance,
        "total_lns_distance": total_lns_distance,
        "customer_delivery_lns_distance": total_lns_distance,
        "supplier_depot_replenishment_distance": (
            supplier_depot_replenishment_distance
        ),
        "supplier_depot_replenishment_metrics": (
            supplier_depot_replenishment_metrics
        ),
        "total_lns_system_distance": total_lns_system_distance,
        "depot_reference_distance": depot_reference_distance,
        "depot_lns_distance": depot_lns_distance,
        "supplier_lns_distance": supplier_lns_distance,
        "improvement_distance": improvement_distance,
        "improvement_percent": improvement_percent,
        "customer_delivery_improvement_distance": improvement_distance,
        "customer_delivery_improvement_percent": improvement_percent,
        "system_improvement_distance": system_improvement_distance,
        "system_improvement_percent": system_improvement_percent,
        "n_routes": len(all_lns_routes),
        "n_depot_lns_routes": len([
            record for record in lns_route_records
            if record["origin_type"] == "depot"
        ]),
        "n_supplier_lns_routes": len([
            record for record in lns_route_records
            if record["origin_type"] == "supplier"
        ]),
        "lns_trip_distances": lns_trip_distances,
        "lns_trip_loads": lns_trip_loads,
        "lns_trip_utilization": lns_trip_utilization,
        "lns_avg_utilization": (
            sum(lns_trip_utilization) / len(lns_trip_utilization)
            if lns_trip_utilization
            else 0
        ),
        "lns_max_utilization": max(lns_trip_utilization) if lns_trip_utilization else 0,
        "lns_min_utilization": min(lns_trip_utilization) if lns_trip_utilization else 0,
        "depot_timing_lns_summary": depot_timing_lns_summary,
        "depot_timing_lns_records": depot_timing_lns_records,
        "depot_customer_coverage_summary": depot_customer_coverage_summary,
        "supplier_direct_coverage_summary": supplier_direct_coverage_summary,
        "final_customer_coverage_summary": final_customer_coverage_summary,
        "overall_feasible_with_dispatch_wave_lns": (
            overall_feasible_with_dispatch_wave_lns
        ),
        "depot_lns_metrics_by_wave": depot_lns_metrics,
        "supplier_lns_metrics": supplier_lns_metrics,
    }

    write_json(os.path.join(save_path, "lns_sa_metrics.json"), lns_metrics)

    lns_summary = {
        "algorithm": lns_metrics["algorithm"],
        "case": lns_metrics["case"],
        "clustering": lns_metrics["clustering"],
        "timing_model": lns_metrics["timing_model"],
        "operator_pair": lns_metrics["operator_pair"],
        "destroy_operator": lns_metrics["destroy_operator"],
        "repair_operator": lns_metrics["repair_operator"],
        "instance": lns_metrics["instance"],
        "seed": lns_metrics["seed"],
        "n_iterations": lns_metrics["n_iterations"],
        "n_remove": lns_metrics["n_remove"],
        "related_removal_randomness": lns_metrics["related_removal_randomness"],
        "distance_weight": lns_metrics["distance_weight"],
        "demand_weight": lns_metrics["demand_weight"],
        "route_weight": lns_metrics["route_weight"],
        "average_speed": lns_metrics["average_speed"],
        "dispatch_wave_labels": lns_metrics["dispatch_wave_labels"],
        "baseline_reference_distance": lns_metrics["baseline_reference_distance"],
        "total_lns_distance": lns_metrics["total_lns_distance"],
        "improvement_distance": lns_metrics["improvement_distance"],
        "improvement_percent": lns_metrics["improvement_percent"],
        "baseline_reference_system_distance": lns_metrics[
            "baseline_reference_system_distance"
        ],
        "total_lns_system_distance": lns_metrics["total_lns_system_distance"],
        "system_improvement_distance": lns_metrics[
            "system_improvement_distance"
        ],
        "system_improvement_percent": lns_metrics[
            "system_improvement_percent"
        ],
        "n_routes": lns_metrics["n_routes"],
        "n_depot_lns_routes": lns_metrics["n_depot_lns_routes"],
        "n_supplier_lns_routes": lns_metrics["n_supplier_lns_routes"],
        "lns_avg_utilization": lns_metrics["lns_avg_utilization"],
        "accepted_moves": lns_metrics["accepted_moves"],
        "rejected_moves": lns_metrics["rejected_moves"],
        "rejected_infeasible_moves": lns_metrics[
            "rejected_infeasible_moves"
        ],
        "depot_timing_lns_summary": lns_metrics[
            "depot_timing_lns_summary"
        ],
        "final_customer_coverage_summary": lns_metrics[
            "final_customer_coverage_summary"
        ],
        "overall_feasible_with_dispatch_wave_lns": lns_metrics[
            "overall_feasible_with_dispatch_wave_lns"
        ],
        "baseline_run_path": latest_run_path,
        "lns_output_path": save_path,
    }

    write_json(os.path.join(save_path, "lns_sa_summary.json"), lns_summary)

    try:
        plot_supplier_routes(
            route_records=lns_route_records,
            supplier_cord=supplier_cord,
            customer_cord=customer_cord,
            results_path=save_path,
            filename="route_plot_lns_sa.png",
            title=(
                "Case 3 KMeans Dispatch-Wave Speed30 + 14:00-wave Split + Related-Regret LNS"
            ),
            depot_cord=depot_cord,
        )
    except Exception as error:
        with open(
            os.path.join(save_path, "route_plot_lns_sa_plot_skipped.txt"),
            "w",
        ) as file_handle:
            file_handle.write(f"Plot skipped due to error: {error}\n")

    print("\n===================================")
    print("DISPATCH-WAVE SPEED30 + 14:00 WAVE RELATED-REGRET LNS SUMMARY")
    print("===================================")
    print(json.dumps(lns_summary, indent=4))

    return lns_metrics
