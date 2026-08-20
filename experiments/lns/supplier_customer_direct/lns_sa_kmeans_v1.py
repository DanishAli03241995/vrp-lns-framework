"""
Case 2: Supplier -> Customer Direct + KMeans + LNS-SA.

Loads the latest supplier-customer direct KMeans baseline run, applies
supplier-level LNS-SA, and stores improved route outputs in the same run folder.
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


from utils.plot_routes import plot_supplier_routes


lns_sa_module = importlib.import_module(
    "metaheuristics.02_basic_lns_sa_v1"
)

run_basic_lns_sa = lns_sa_module.run_basic_lns_sa


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
    latest_folder = run_folders[-1]

    return os.path.join(instance_path, latest_folder)


def compute_trip_load(trip, demand):
    trip_load = 0

    for customer in trip[1:-1]:
        trip_load += demand[customer]

    return trip_load


def collect_customer_coordinates(supplier_metrics):
    customer_cord = {}

    for supplier_data in supplier_metrics.values():
        for customer_id, coord in supplier_data["customer_cord"].items():
            customer_cord[int(customer_id)] = coord

    return customer_cord


def run_lns_sa_experiment(
    instance_name,
    n_iterations=50,
    n_remove=4,
    seed=42,
    initial_temperature=10.0,
    cooling_rate=0.95,
    minimum_temperature=0.01,
    output_path=None,
):
    base_results_path = os.path.join(
        ROOT_DIR,
        "results",
        "supplier_customer_only_baseline_kmeans_v1",
        instance_name,
    )

    latest_run_path = get_latest_run_folder(
        base_results_path
    )

    print("\n===================================")
    print("LATEST RUN FOLDER")
    print("===================================")
    print(latest_run_path)

    save_path = output_path or latest_run_path
    os.makedirs(save_path, exist_ok=True)

    print("\n===================================")
    print("LNS OUTPUT FOLDER")
    print("===================================")
    print(save_path)

    metrics_path = os.path.join(
        latest_run_path,
        "metrics.json",
    )

    with open(metrics_path, "r") as file_handle:
        metrics = json.load(file_handle)

    supplier_metrics = metrics["supplier_metrics"]
    reference_distance = metrics["post_reloc_2opt_distance"]
    vehicle_capacity = metrics["vehicle_capacity"]
    supplier_cord = {
        int(supplier_id): coord
        for supplier_id, coord
        in metrics["supplier_cord"].items()
    }
    customer_cord = collect_customer_coordinates(
        supplier_metrics
    )

    # Older baseline runs may not save config_used.json. The LNS step starts
    # from metrics.json routes, so metrics.json is sufficient here.
    config_path = os.path.join(
        latest_run_path,
        "config_used.json",
    )

    if os.path.exists(config_path):
        with open(config_path, "r") as file_handle:
            lns_config_source = json.load(file_handle)
    else:
        lns_config_source = "not_available_metrics_json_used"

    all_lns_routes = []
    lns_route_records = []
    lns_trip_distances = []
    lns_trip_loads = []
    lns_trip_utilization = []
    supplier_lns_metrics = {}
    total_lns_distance = 0

    for supplier_id, supplier_data in supplier_metrics.items():
        print("\n===================================")
        print(f"SUPPLIER {supplier_id}")
        print("===================================")

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

        initial_solution = supplier_data[
            "route_post_reloc_2opt"
        ]

        print("\nINITIAL SOLUTION:")
        print(initial_solution)

        def routing_distance(i, j):
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

        best_solution, best_distance = run_basic_lns_sa(
            initial_solution=initial_solution,
            demand=supplier_demand,
            vehicle_capacity=vehicle_capacity,
            routing_distance=routing_distance,
            n_iterations=n_iterations,
            n_remove=n_remove,
            seed=seed,
            initial_temperature=initial_temperature,
            cooling_rate=cooling_rate,
            minimum_temperature=minimum_temperature,
        )

        print("\nSUPPLIER LNS DISTANCE:")
        print(best_distance)

        total_lns_distance += best_distance

        supplier_trip_distances = []
        supplier_trip_loads = []
        supplier_trip_utilization = []

        for trip in best_solution:
            trip_distance = 0

            for index in range(len(trip) - 1):
                trip_distance += routing_distance(
                    trip[index],
                    trip[index + 1],
                )

            trip_load = compute_trip_load(
                trip,
                supplier_demand,
            )

            supplier_trip_distances.append(trip_distance)
            supplier_trip_loads.append(trip_load)
            supplier_trip_utilization.append(
                trip_load / vehicle_capacity
            )

            lns_trip_distances.append(trip_distance)
            lns_trip_loads.append(trip_load)
            lns_trip_utilization.append(
                trip_load / vehicle_capacity
            )

            all_lns_routes.append(trip)

            lns_route_records.append({
                "supplier_id": int(supplier_id),
                "trip": trip,
            })

        supplier_reference_distance = supplier_data[
            "post_reloc_2opt_distance"
        ]

        supplier_lns_metrics[supplier_id] = {
            "initial_distance": supplier_reference_distance,
            "lns_distance": best_distance,
            "improvement_distance": (
                supplier_reference_distance
                - best_distance
            ),
            "improvement_percent": (
                (
                    supplier_reference_distance
                    - best_distance
                )
                / supplier_reference_distance
            ) * 100,
            "n_routes": len(best_solution),
            "lns_trip_distances": supplier_trip_distances,
            "lns_trip_loads": supplier_trip_loads,
            "lns_trip_utilization": supplier_trip_utilization,
            "route_lns_sa": best_solution,
        }

    lns_route_path = os.path.join(
        save_path,
        "route_lns_sa.txt",
    )

    with open(lns_route_path, "w") as file_handle:
        file_handle.write(str(all_lns_routes))

    lns_route_records_path = os.path.join(
        save_path,
        "route_lns_sa_records.json",
    )

    with open(lns_route_records_path, "w") as file_handle:
        json.dump(
            lns_route_records,
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

    lns_metrics = {
        "algorithm": "supplier_customer_lns_sa_kmeans_v1",
        "case": "Case_2_supplier_customer_direct",
        "clustering": "kmeans",
        "instance": instance_name,
        "n_iterations": n_iterations,
        "n_remove": n_remove,
        "seed": seed,
        "initial_temperature": initial_temperature,
        "cooling_rate": cooling_rate,
        "minimum_temperature": minimum_temperature,
        "baseline_reference_algorithm": metrics["algorithm"],
        "baseline_run_path": latest_run_path,
        "lns_output_path": save_path,
        "baseline_config_source": lns_config_source,
        "baseline_reference_distance": reference_distance,
        "total_lns_distance": total_lns_distance,
        "improvement_distance": improvement_distance,
        "improvement_percent": improvement_percent,
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
        "supplier_lns_metrics": supplier_lns_metrics,
    }

    lns_metrics_path = os.path.join(
        save_path,
        "lns_sa_metrics.json",
    )

    with open(lns_metrics_path, "w") as file_handle:
        json.dump(
            lns_metrics,
            file_handle,
            indent=4,
        )

    lns_summary = {
        "algorithm": lns_metrics["algorithm"],
        "case": lns_metrics["case"],
        "clustering": lns_metrics["clustering"],
        "instance": lns_metrics["instance"],
        "seed": lns_metrics["seed"],
        "n_iterations": lns_metrics["n_iterations"],
        "n_remove": lns_metrics["n_remove"],
        "baseline_reference_distance": reference_distance,
        "final_distance": total_lns_distance,
        "improvement_distance": improvement_distance,
        "improvement_percent": improvement_percent,
        "n_routes": len(all_lns_routes),
        "avg_utilization": lns_metrics["lns_avg_utilization"],
        "max_utilization": lns_metrics["lns_max_utilization"],
        "min_utilization": lns_metrics["lns_min_utilization"],
    }

    lns_summary_path = os.path.join(
        save_path,
        "lns_sa_summary.json",
    )

    with open(lns_summary_path, "w") as file_handle:
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
        title="Case 2 Direct KMeans + LNS-SA Routes",
    )

    print("\n===================================")
    print("LNS-SA COMPLETE")
    print("===================================")

    print("Reference Distance:")
    print(reference_distance)

    print("\nTOTAL LNS DISTANCE:")
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
