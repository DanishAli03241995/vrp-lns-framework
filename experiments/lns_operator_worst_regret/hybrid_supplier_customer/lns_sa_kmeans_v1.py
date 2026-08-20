"""
Case 3: Hybrid Supplier-Customer + KMeans + LNS-SA.

Operator pair:
- Worst Removal
- Regret-2 Insertion
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


from instances.generate_supplier_customer_instance import (
    generate_supplier_customer_instance,
)
from utils.plot_routes import plot_supplier_routes


lns_sa_module = importlib.import_module(
    "metaheuristics.operator_pair_engines.lns_sa_worst_regret_v1"
)

run_lns_sa_worst_regret = lns_sa_module.run_lns_sa_worst_regret


def get_latest_run_folder(instance_path):
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


def remove_empty_routes(solution):
    return [
        route
        for route in solution
        if len(route) > 2
    ]


def collect_customer_data(supplier_metrics):
    customer_cord = {}
    demand = {}

    for supplier_data in supplier_metrics.values():
        for customer_id, coord in supplier_data["customer_cord"].items():
            customer_cord[int(customer_id)] = coord

        for customer_id, demand_value in supplier_data["demand"].items():
            demand[int(customer_id)] = demand_value

    return customer_cord, demand


def compute_trip_distance(trip, routing_distance):
    trip_distance = 0

    for index in range(len(trip) - 1):
        trip_distance += routing_distance(
            trip[index],
            trip[index + 1],
        )

    return trip_distance


def compute_trip_load(trip, demand):
    trip_load = 0

    for customer in trip[1:-1]:
        trip_load += demand[customer]

    return trip_load


def compute_euclidean_distance(coord_a, coord_b):
    x1, y1 = coord_a
    x2, y2 = coord_b

    return math.sqrt(
        (x1 - x2) ** 2
        + (y1 - y2) ** 2
    )


def compute_supplier_depot_replenishment(
    post_reloc_2opt_route_records,
    supplier_metrics,
    supplier_cord,
    depot_cord,
    vehicle_capacity,
):
    """
    Estimate first-echelon replenishment for depot-assigned customers.

    Each supplier sends the demand of its depot-served customers to the depot
    through simple supplier -> depot -> supplier round trips.
    """

    depot_customer_ids_by_supplier = {}

    for record in post_reloc_2opt_route_records:
        if record["origin_type"] != "depot":
            continue

        for customer in record["trip"][1:-1]:
            customer_supplier_map = record.get(
                "customer_supplier_map",
                {},
            )
            supplier_id = record.get(
                "supplier_region_id",
                record.get(
                    "supplier_id",
                    customer_supplier_map.get(str(customer)),
                ),
            )
            supplier_id = int(supplier_id)
            depot_customer_ids_by_supplier.setdefault(
                supplier_id,
                set(),
            )
            depot_customer_ids_by_supplier[supplier_id].add(
                int(customer)
            )

    replenishment_by_supplier = {}
    total_replenishment_distance = 0

    for supplier_id, customer_ids in depot_customer_ids_by_supplier.items():
        supplier_data = supplier_metrics[str(supplier_id)]
        supplier_demand = {
            int(customer_id): demand_value
            for customer_id, demand_value
            in supplier_data["demand"].items()
        }

        depot_assigned_demand = sum(
            supplier_demand[customer_id]
            for customer_id in customer_ids
        )

        supplier_depot_trips = math.ceil(
            depot_assigned_demand
            / vehicle_capacity
        )

        supplier_depot_roundtrip_distance = (
            supplier_depot_trips
            * 2
            * compute_euclidean_distance(
                supplier_cord[supplier_id],
                depot_cord,
            )
        )

        replenishment_by_supplier[str(supplier_id)] = {
            "depot_assigned_customer_ids": sorted(customer_ids),
            "depot_assigned_demand": depot_assigned_demand,
            "supplier_depot_trips": supplier_depot_trips,
            "supplier_depot_roundtrip_distance": (
                supplier_depot_roundtrip_distance
            ),
        }

        total_replenishment_distance += (
            supplier_depot_roundtrip_distance
        )

    return (
        total_replenishment_distance,
        replenishment_by_supplier,
    )


def build_trip_metrics(solution, demand, vehicle_capacity, routing_distance):
    trip_distances = []
    trip_loads = []
    trip_utilization = []

    for trip in remove_empty_routes(solution):
        trip_distance = compute_trip_distance(
            trip,
            routing_distance,
        )
        trip_load = compute_trip_load(
            trip,
            demand,
        )

        trip_distances.append(trip_distance)
        trip_loads.append(trip_load)
        trip_utilization.append(
            trip_load / vehicle_capacity
        )

    return trip_distances, trip_loads, trip_utilization


def build_default_output_path(instance_name):
    return os.path.join(
        ROOT_DIR,
        "results",
        "lns_operator_worst_regret",
        "case3_kmeans",
        instance_name,
    )


def run_lns_sa_experiment(
    instance_name,
    n_iterations=50,
    n_remove=4,
    seed=42,
    initial_temperature=10.0,
    cooling_rate=0.95,
    minimum_temperature=0.01,
    worst_removal_randomness=0.2,
    output_path=None,
):
    base_results_path = os.path.join(
        ROOT_DIR,
        "results",
        "hybrid_supplier_customer_kmeans_v1",
        instance_name,
    )

    latest_run_path = get_latest_run_folder(
        base_results_path
    )

    print("\n===================================")
    print("LATEST BASELINE RUN FOLDER")
    print("===================================")
    print(latest_run_path)

    save_path = output_path or build_default_output_path(
        instance_name
    )
    os.makedirs(save_path, exist_ok=True)

    print("\n===================================")
    print("WORST + REGRET HYBRID LNS OUTPUT FOLDER")
    print("===================================")
    print(save_path)

    metrics_path = os.path.join(
        latest_run_path,
        "metrics.json",
    )

    with open(metrics_path, "r") as file_handle:
        metrics = json.load(file_handle)

    supplier_metrics = metrics["supplier_metrics"]
    post_reloc_2opt_route_records = metrics[
        "post_reloc_2opt_route_records"
    ]

    reference_distance = metrics["post_reloc_2opt_distance"]
    vehicle_capacity = metrics["vehicle_capacity"]
    depot_cord = metrics["depot"]
    supplier_cord = {
        int(supplier_id): coord
        for supplier_id, coord
        in metrics["supplier_cord"].items()
    }
    customer_cord, demand = collect_customer_data(
        supplier_metrics
    )

    config_path = os.path.join(
        latest_run_path,
        "config_used.json",
    )

    if os.path.exists(config_path):
        with open(config_path, "r") as file_handle:
            config = json.load(file_handle)

        instance = generate_supplier_customer_instance(
            config
        )
        customer_cord = instance["customer_cord"]
        demand = instance["demand"]
        lns_config_source = config
    else:
        lns_config_source = "not_available_metrics_json_used"

    (
        supplier_depot_replenishment_distance,
        supplier_depot_replenishment_metrics,
    ) = compute_supplier_depot_replenishment(
        post_reloc_2opt_route_records=post_reloc_2opt_route_records,
        supplier_metrics=supplier_metrics,
        supplier_cord=supplier_cord,
        depot_cord=depot_cord,
        vehicle_capacity=vehicle_capacity,
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

    depot_lns_metrics = {}
    supplier_lns_metrics = {}

    depot_initial_solution = []

    for record in post_reloc_2opt_route_records:
        if record["origin_type"] == "depot":
            depot_initial_solution.append(
                record["trip"]
            )

    depot_initial_solution = remove_empty_routes(
        depot_initial_solution
    )

    if depot_initial_solution:
        print("\n===================================")
        print("DEPOT-SIDE LNS")
        print("===================================")

        print("\nINITIAL DEPOT SOLUTION:")
        print(depot_initial_solution)

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

            return math.sqrt(
                (x1 - x2) ** 2
                + (y1 - y2) ** 2
            )

        depot_best_solution, depot_best_distance, depot_summary = (
            run_lns_sa_worst_regret(
                initial_solution=depot_initial_solution,
                demand=demand,
                vehicle_capacity=vehicle_capacity,
                routing_distance=depot_routing_distance,
                n_iterations=n_iterations,
                n_remove=n_remove,
                seed=seed,
                initial_temperature=initial_temperature,
                cooling_rate=cooling_rate,
                minimum_temperature=minimum_temperature,
                worst_removal_randomness=worst_removal_randomness,
            )
        )
        depot_best_solution = remove_empty_routes(
            depot_best_solution
        )

        depot_lns_distance = depot_best_distance
        total_lns_distance += depot_best_distance
        accepted_moves += depot_summary["accepted_moves"]
        rejected_moves += depot_summary["rejected_moves"]
        operator_records["depot"] = depot_summary["records"]

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
            "lns_distance": depot_best_distance,
            "n_routes": len(depot_best_solution),
            "lns_trip_distances": depot_trip_distances,
            "lns_trip_loads": depot_trip_loads,
            "lns_trip_utilization": depot_trip_utilization,
            "operator_pair": depot_summary["operator_pair"],
            "best_iteration": depot_summary["best_iteration"],
            "accepted_moves": depot_summary["accepted_moves"],
            "rejected_moves": depot_summary["rejected_moves"],
            "route_lns_sa": depot_best_solution,
        }

        lns_trip_distances.extend(depot_trip_distances)
        lns_trip_loads.extend(depot_trip_loads)
        lns_trip_utilization.extend(depot_trip_utilization)

        for trip in depot_best_solution:
            all_lns_routes.append(trip)

            lns_route_records.append({
                "origin_type": "depot",
                "supplier_region_id": None,
                "trip": trip,
            })

    for supplier_id, supplier_data in supplier_metrics.items():
        initial_solution = remove_empty_routes(
            supplier_data["route_post_reloc_2opt"]
        )

        if not initial_solution:
            continue

        print("\n===================================")
        print(f"SUPPLIER-DIRECT LNS - SUPPLIER {supplier_id}")
        print("===================================")

        print("\nINITIAL SUPPLIER SOLUTION:")
        print(initial_solution)

        supplier_origin = supplier_data["origin"]

        supplier_customer_cord = {
            int(customer_id): coord
            for customer_id, coord
            in supplier_data["customer_cord"].items()
        }

        supplier_demand = {
            int(customer_id): demand_value
            for customer_id, demand_value
            in supplier_data["demand"].items()
        }

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

            return math.sqrt(
                (x1 - x2) ** 2
                + (y1 - y2) ** 2
            )

        supplier_best_solution, supplier_best_distance, supplier_summary = (
            run_lns_sa_worst_regret(
                initial_solution=initial_solution,
                demand=supplier_demand,
                vehicle_capacity=vehicle_capacity,
                routing_distance=supplier_routing_distance,
                n_iterations=n_iterations,
                n_remove=n_remove,
                seed=seed,
                initial_temperature=initial_temperature,
                cooling_rate=cooling_rate,
                minimum_temperature=minimum_temperature,
                worst_removal_randomness=worst_removal_randomness,
            )
        )
        supplier_best_solution = remove_empty_routes(
            supplier_best_solution
        )

        supplier_lns_distance += supplier_best_distance
        total_lns_distance += supplier_best_distance
        accepted_moves += supplier_summary["accepted_moves"]
        rejected_moves += supplier_summary["rejected_moves"]
        operator_records["suppliers"][str(supplier_id)] = (
            supplier_summary["records"]
        )

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

        supplier_reference_distance = supplier_data[
            "post_reloc_2opt_distance"
        ]

        supplier_lns_metrics[supplier_id] = {
            "initial_distance": supplier_reference_distance,
            "lns_distance": supplier_best_distance,
            "improvement_distance": (
                supplier_reference_distance
                - supplier_best_distance
            ),
            "improvement_percent": (
                (
                    supplier_reference_distance
                    - supplier_best_distance
                )
                / supplier_reference_distance
            ) * 100 if supplier_reference_distance else 0,
            "n_routes": len(supplier_best_solution),
            "lns_trip_distances": supplier_trip_distances,
            "lns_trip_loads": supplier_trip_loads,
            "lns_trip_utilization": supplier_trip_utilization,
            "operator_pair": supplier_summary["operator_pair"],
            "best_iteration": supplier_summary["best_iteration"],
            "accepted_moves": supplier_summary["accepted_moves"],
            "rejected_moves": supplier_summary["rejected_moves"],
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

    with open(os.path.join(save_path, "route_lns_sa.txt"), "w") as file_handle:
        file_handle.write(str(all_lns_routes))

    with open(
        os.path.join(save_path, "route_lns_sa_records.json"),
        "w",
    ) as file_handle:
        json.dump(
            lns_route_records,
            file_handle,
            indent=4,
        )

    with open(
        os.path.join(save_path, "operator_pair_records.json"),
        "w",
    ) as file_handle:
        json.dump(
            operator_records,
            file_handle,
            indent=4,
        )

    improvement_distance = (
        reference_distance
        - total_lns_distance
    )
    improvement_percent = (
        improvement_distance
        / reference_distance
    ) * 100

    baseline_reference_system_distance = (
        reference_distance
        + supplier_depot_replenishment_distance
    )
    total_lns_system_distance = (
        total_lns_distance
        + supplier_depot_replenishment_distance
    )
    system_improvement_distance = (
        baseline_reference_system_distance
        - total_lns_system_distance
    )
    system_improvement_percent = (
        system_improvement_distance
        / baseline_reference_system_distance
    ) * 100 if baseline_reference_system_distance else 0

    lns_metrics = {
        "algorithm": "hybrid_supplier_customer_lns_sa_kmeans_worst_regret_v1",
        "case": "Case_3_hybrid_supplier_customer",
        "clustering": "kmeans",
        "operator_pair": "worst_regret",
        "destroy_operator": "worst_removal",
        "repair_operator": "regret_2_insertion",
        "instance": instance_name,
        "n_iterations": n_iterations,
        "n_remove": n_remove,
        "seed": seed,
        "initial_temperature": initial_temperature,
        "cooling_rate": cooling_rate,
        "minimum_temperature": minimum_temperature,
        "worst_removal_randomness": worst_removal_randomness,
        "accepted_moves": accepted_moves,
        "rejected_moves": rejected_moves,
        "supplier_count": len(supplier_metrics),
        "baseline_reference_algorithm": metrics["algorithm"],
        "baseline_run_path": latest_run_path,
        "lns_output_path": save_path,
        "baseline_config_source": lns_config_source,
        "baseline_reference_distance": reference_distance,
        "baseline_reference_customer_delivery_distance": reference_distance,
        "baseline_reference_system_distance": (
            baseline_reference_system_distance
        ),
        "total_lns_distance": total_lns_distance,
        "customer_delivery_lns_distance": total_lns_distance,
        "supplier_depot_replenishment_distance": (
            supplier_depot_replenishment_distance
        ),
        "supplier_depot_replenishment_metrics": (
            supplier_depot_replenishment_metrics
        ),
        "total_lns_system_distance": total_lns_system_distance,
        "depot_lns_distance": depot_lns_distance,
        "supplier_lns_distance": supplier_lns_distance,
        "improvement_distance": improvement_distance,
        "improvement_percent": improvement_percent,
        "customer_delivery_improvement_distance": improvement_distance,
        "customer_delivery_improvement_percent": improvement_percent,
        "system_improvement_distance": system_improvement_distance,
        "system_improvement_percent": system_improvement_percent,
        "n_routes": len(all_lns_routes),
        "lns_trip_distances": lns_trip_distances,
        "lns_trip_loads": lns_trip_loads,
        "lns_trip_utilization": lns_trip_utilization,
        "lns_avg_utilization": (
            sum(lns_trip_utilization)
            / len(lns_trip_utilization)
            if lns_trip_utilization
            else 0
        ),
        "lns_max_utilization": (
            max(lns_trip_utilization)
            if lns_trip_utilization
            else 0
        ),
        "lns_min_utilization": (
            min(lns_trip_utilization)
            if lns_trip_utilization
            else 0
        ),
        "depot_lns_metrics": depot_lns_metrics,
        "supplier_lns_metrics": supplier_lns_metrics,
    }

    with open(
        os.path.join(save_path, "lns_sa_metrics.json"),
        "w",
    ) as file_handle:
        json.dump(
            lns_metrics,
            file_handle,
            indent=4,
        )

    lns_summary = {
        "algorithm": lns_metrics["algorithm"],
        "case": lns_metrics["case"],
        "clustering": lns_metrics["clustering"],
        "operator_pair": lns_metrics["operator_pair"],
        "destroy_operator": lns_metrics["destroy_operator"],
        "repair_operator": lns_metrics["repair_operator"],
        "instance": lns_metrics["instance"],
        "seed": lns_metrics["seed"],
        "n_iterations": lns_metrics["n_iterations"],
        "n_remove": lns_metrics["n_remove"],
        "baseline_reference_distance": reference_distance,
        "baseline_reference_customer_delivery_distance": reference_distance,
        "baseline_reference_system_distance": (
            baseline_reference_system_distance
        ),
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
        "supplier_count": len(supplier_metrics),
        "n_routes": len(all_lns_routes),
        "avg_utilization": lns_metrics["lns_avg_utilization"],
        "max_utilization": lns_metrics["lns_max_utilization"],
        "min_utilization": lns_metrics["lns_min_utilization"],
    }

    with open(
        os.path.join(save_path, "lns_sa_summary.json"),
        "w",
    ) as file_handle:
        json.dump(
            lns_summary,
            file_handle,
            indent=4,
        )

    plot_supplier_routes(
        lns_route_records,
        supplier_cord,
        customer_cord,
        save_path,
        filename="route_plot_lns_sa.png",
        title="Case 3 Hybrid KMeans + Worst Regret LNS-SA Routes",
        depot_cord=depot_cord,
    )

    print("\n===================================")
    print("HYBRID WORST + REGRET LNS-SA COMPLETE")
    print("===================================")
    print("Reference Distance:")
    print(reference_distance)
    print("\nTotal LNS Distance:")
    print(total_lns_distance)
    print("\nImprovement:")
    print(improvement_distance)
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
