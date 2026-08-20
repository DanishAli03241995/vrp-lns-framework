"""
Case 3: Hybrid Supplier-Customer + KMeans + fixed timing split repair + LNS-SA.

Timing variant:
- fixed depot-ready time;
- split repair has already been applied in the baseline timing run;
- LNS starts from the split-repaired solution;
- depot-side LNS is time-aware;
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


fixed_timing_lns_module = importlib.import_module(
    "metaheuristics.operator_pair_engines."
    "lns_sa_related_regret_fixed_timing_v1"
)
standard_lns_module = importlib.import_module(
    "metaheuristics.operator_pair_engines.lns_sa_related_regret_v1"
)

run_lns_sa_related_regret_fixed_timing = (
    fixed_timing_lns_module.run_lns_sa_related_regret_fixed_timing
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
    average_speed = 30

    return {
        "customer_cord": customer_cord,
        "demand": demand,
        "service_time": service_time,
        "average_speed": average_speed,
        "config_source": "config_used.json_missing_default_speed30_service10_used",
    }


def extract_depot_initial_solution(metrics):
    """Use split-repaired fixed timing records as the depot LNS start."""
    depot_timing_records = metrics.get("depot_timing_route_records", [])

    depot_routes = []

    for record in depot_timing_records:
        depot_routes.append(normalize_route(record["trip"]))

    return remove_empty_routes(depot_routes)


def extract_supplier_direct_initial_solution(supplier_data):
    """Extract supplier-direct post-relocation 2-opt routes."""
    return remove_empty_routes(
        normalize_routes(supplier_data["route_post_reloc_2opt"])
    )


def get_expected_customer_sets(metrics):
    """Return depot, supplier-direct, and all expected customer ids."""
    depot_customers = [int(customer) for customer in metrics["depot_customer_ids"]]
    supplier_direct_customers = [
        int(customer) for customer in metrics["supplier_direct_customer_ids"]
    ]
    all_customers = sorted(set(depot_customers) | set(supplier_direct_customers))

    return depot_customers, supplier_direct_customers, all_customers


# =====================================================
# Routing distance helpers
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
# Main experiment
# =====================================================


def build_default_output_path(instance_name):
    """Default output path when the shared runner does not provide one."""
    return os.path.join(
        ROOT_DIR,
        "results",
        "lns_timing_fixed_split_related_regret",
        "case3_kmeans",
        instance_name,
    )


def add_depot_timing_record_metadata(records):
    """Add consistent metadata to LNS depot timing records."""
    enriched_records = []

    for record in records:
        enriched_record = dict(record)
        enriched_record["supplier_region_id"] = "global_depot_pool"
        enriched_record["routing_scope"] = "global_depot_pool"
        enriched_record["timing_stage"] = "after_time_aware_lns"
        enriched_records.append(enriched_record)

    return enriched_records


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
    """Run fixed-timing split-repair LNS for one instance."""
    baseline_results_name = "hybrid_supplier_customer_kmeans_timing_fixed_split_v1"
    base_results_path = os.path.join(
        ROOT_DIR,
        "results",
        baseline_results_name,
        instance_name,
    )
    latest_run_path = get_latest_run_folder(base_results_path)

    print("\n===================================")
    print("LATEST FIXED TIMING + SPLIT BASELINE RUN FOLDER")
    print("===================================")
    print(latest_run_path)

    save_path = output_path or build_default_output_path(instance_name)
    os.makedirs(save_path, exist_ok=True)

    print("\n===================================")
    print("FIXED TIMING SPLIT + RELATED REGRET LNS OUTPUT FOLDER")
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
    fixed_depot_ready_time = metrics.get("fixed_depot_ready_time", 9.0)
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

    depot_expected_customers, supplier_direct_expected_customers, all_expected_customers = (
        get_expected_customer_sets(metrics)
    )

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
        "depot": [],
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

    # =====================================================
    # Depot-side time-aware LNS
    # =====================================================

    depot_initial_solution = extract_depot_initial_solution(metrics)
    depot_routing_distance = build_depot_routing_distance(
        depot_cord=depot_cord,
        customer_cord=customer_cord,
    )

    depot_reference_distance = compute_solution_distance(
        depot_initial_solution,
        depot_routing_distance,
    )

    if depot_initial_solution:
        print("\n===================================")
        print("DEPOT-SIDE FIXED TIMING LNS")
        print("===================================")
        print("Initial depot solution:")
        print(depot_initial_solution)

        depot_best_solution, depot_best_distance, depot_summary = (
            run_lns_sa_related_regret_fixed_timing(
                initial_solution=depot_initial_solution,
                customer_coordinates=customer_cord,
                demand=demand,
                vehicle_capacity=vehicle_capacity,
                routing_distance=depot_routing_distance,
                average_speed=average_speed,
                service_time=service_time,
                fixed_depot_ready_time=fixed_depot_ready_time,
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
        depot_best_solution = remove_empty_routes(depot_best_solution)

        depot_lns_distance = depot_best_distance
        total_lns_distance += depot_best_distance
        accepted_moves += depot_summary["accepted_moves"]
        rejected_moves += depot_summary["rejected_moves"]
        rejected_infeasible_moves += depot_summary["rejected_infeasible_moves"]
        operator_records["depot"] = depot_summary["records"]

        depot_timing_lns_records = add_depot_timing_record_metadata(
            depot_summary["best_timing_records"]
        )
        depot_timing_lns_summary = depot_summary["best_timing_summary"]
        depot_lns_coverage_summary = depot_summary["best_coverage_summary"]

        (
            depot_trip_distances,
            depot_trip_loads,
            depot_trip_utilization,
        ) = build_trip_metrics(
            depot_best_solution,
            demand,
            vehicle_capacity,
            depot_routing_distance,
        )

        depot_lns_metrics = {
            "initial_distance": depot_reference_distance,
            "lns_distance": depot_best_distance,
            "improvement_distance": depot_reference_distance - depot_best_distance,
            "improvement_percent": safe_percent(
                depot_reference_distance - depot_best_distance,
                depot_reference_distance,
            ),
            "n_routes": len(depot_best_solution),
            "lns_trip_distances": depot_trip_distances,
            "lns_trip_loads": depot_trip_loads,
            "lns_trip_utilization": depot_trip_utilization,
            "operator_pair": depot_summary["operator_pair"],
            "destroy_operator": depot_summary["destroy_operator"],
            "repair_operator": depot_summary["repair_operator"],
            "best_iteration": depot_summary["best_iteration"],
            "accepted_moves": depot_summary["accepted_moves"],
            "rejected_moves": depot_summary["rejected_moves"],
            "rejected_infeasible_moves": depot_summary[
                "rejected_infeasible_moves"
            ],
            "initial_timing_summary": depot_summary["initial_timing_summary"],
            "lns_timing_summary": depot_timing_lns_summary,
            "initial_coverage_summary": depot_summary["initial_coverage_summary"],
            "lns_coverage_summary": depot_lns_coverage_summary,
            "route_lns_sa": depot_best_solution,
        }

        lns_trip_distances.extend(depot_trip_distances)
        lns_trip_loads.extend(depot_trip_loads)
        lns_trip_utilization.extend(depot_trip_utilization)

        for trip in depot_best_solution:
            all_lns_routes.append(trip)
            lns_route_records.append({
                "origin_type": "depot",
                "routing_scope": "global_depot_pool",
                "timing_model": "fixed_depot_ready_time_lns",
                "supplier_region_id": "global_depot_pool",
                "trip": trip,
            })
    else:
        depot_timing_lns_records = []
        depot_timing_lns_summary = fixed_timing_lns_module.summarize_fixed_timing_records([])
        depot_lns_coverage_summary = validate_customer_coverage(
            routes=[],
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

    overall_feasible_with_fixed_timing_lns = (
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
        os.path.join(save_path, "depot_timing_fixed_lns_records.json"),
        depot_timing_lns_records,
    )
    write_json(
        os.path.join(save_path, "depot_timing_fixed_lns_summary.json"),
        depot_timing_lns_summary,
    )

    with open(os.path.join(save_path, "route_lns_sa.txt"), "w") as file_handle:
        file_handle.write(str(all_lns_routes))

    with open(
        os.path.join(save_path, "route_lns_sa_fixed_timing_related_regret.txt"),
        "w",
    ) as file_handle:
        file_handle.write(str(all_lns_routes))

    lns_metrics = {
        "algorithm": (
            "hybrid_supplier_customer_kmeans_timing_fixed_split_"
            "lns_related_regret_v1"
        ),
        "case": "Case_3_hybrid_supplier_customer",
        "clustering": "kmeans",
        "timing_model": "fixed_depot_ready_time_with_half_split_repair_and_lns",
        "base_timing_model": metrics.get("timing_model"),
        "operator_pair": "related_regret_fixed_timing",
        "destroy_operator": "shaw_related_removal",
        "repair_operator": "regret_2_insertion_fixed_timing_for_depot",
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
        "fixed_depot_ready_time": fixed_depot_ready_time,
        "fixed_depot_ready_time_label": fixed_timing_lns_module.format_hour(
            fixed_depot_ready_time
        ),
        "working_day_end_time": working_day_end_time,
        "working_day_end_time_label": fixed_timing_lns_module.format_hour(
            working_day_end_time
        ),
        "average_speed": average_speed,
        "accepted_moves": accepted_moves,
        "rejected_moves": rejected_moves,
        "rejected_infeasible_moves": rejected_infeasible_moves,
        "supplier_count": len(supplier_metrics),
        "baseline_reference_algorithm": metrics["algorithm"],
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
        "overall_feasible_with_fixed_timing_lns": (
            overall_feasible_with_fixed_timing_lns
        ),
        "depot_lns_metrics": depot_lns_metrics,
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
        "baseline_reference_distance": reference_distance,
        "baseline_reference_customer_delivery_distance": reference_distance,
        "baseline_reference_system_distance": baseline_reference_system_distance,
        "final_distance": total_lns_distance,
        "customer_delivery_lns_distance": total_lns_distance,
        "supplier_depot_replenishment_distance": (
            supplier_depot_replenishment_distance
        ),
        "total_lns_system_distance": total_lns_system_distance,
        "depot_lns_distance": depot_lns_distance,
        "supplier_lns_distance": supplier_lns_distance,
        "improvement_distance": improvement_distance,
        "improvement_percent": improvement_percent,
        "system_improvement_distance": system_improvement_distance,
        "system_improvement_percent": system_improvement_percent,
        "accepted_moves": accepted_moves,
        "rejected_moves": rejected_moves,
        "rejected_infeasible_moves": rejected_infeasible_moves,
        "supplier_count": len(supplier_metrics),
        "n_routes": len(all_lns_routes),
        "n_depot_lns_routes": lns_metrics["n_depot_lns_routes"],
        "n_supplier_lns_routes": lns_metrics["n_supplier_lns_routes"],
        "avg_utilization": lns_metrics["lns_avg_utilization"],
        "max_utilization": lns_metrics["lns_max_utilization"],
        "min_utilization": lns_metrics["lns_min_utilization"],
        "depot_timing_feasibility_after_lns": (
            depot_timing_lns_summary["depot_timing_feasibility"]
        ),
        "latest_depot_route_finish_time_after_lns": (
            depot_timing_lns_summary["latest_depot_route_finish_time"]
        ),
        "latest_depot_route_finish_time_after_lns_label": (
            depot_timing_lns_summary["latest_depot_route_finish_time_label"]
        ),
        "overall_feasible_with_fixed_timing_lns": (
            overall_feasible_with_fixed_timing_lns
        ),
    }

    write_json(os.path.join(save_path, "lns_sa_summary.json"), lns_summary)

    plot_supplier_routes(
        lns_route_records,
        supplier_cord,
        customer_cord,
        save_path,
        filename="route_plot_lns_sa.png",
        title="Case 3 KMeans Fixed Timing Split + Related Regret LNS-SA Routes",
        depot_cord=depot_cord,
    )

    print("\n===================================")
    print("FIXED TIMING SPLIT + RELATED REGRET LNS-SA COMPLETE")
    print("===================================")
    print("Reference customer-delivery distance:")
    print(reference_distance)
    print("\nTotal LNS customer-delivery distance:")
    print(total_lns_distance)
    print("\nImprovement:")
    print(improvement_distance)
    print("\nDepot timing feasible after LNS:")
    print(depot_timing_lns_summary["depot_timing_feasibility"])
    print("\nSaved To:")
    print(save_path)

    return lns_metrics


if __name__ == "__main__":
    run_lns_sa_experiment(
        instance_name="40c_cap25",
        n_iterations=50,
        n_remove=4,
        seed=42,
        initial_temperature=10.0,
        cooling_rate=0.95,
        minimum_temperature=0.01,
    )
