# Experiment entry point: Supplier -> Depot -> Customer baseline using KMeans clustering

import sys
import os
import json
import copy
import importlib

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(PROJECT_ROOT)
os.environ.setdefault("MPLCONFIGDIR", os.path.join(PROJECT_ROOT, ".matplotlib_cache"))

from instances.generate_supplier_customer_instance import (
    generate_supplier_customer_instance,
)

kmeans_clustering_v1 = importlib.import_module(
    "construction.02_k_means_clustering_v1"
)
supplier_preprocessing_v1 = importlib.import_module(
    "construction.03_supplier_preprocessing_v1"
)

from solvers import baseline_nn_2opt_relocation_2opt_v1
from utils.experiment_logger import create_experiment_folder
from utils.plot_routes import plot_routes


def run_experiment(config):
    instance = generate_supplier_customer_instance(config)

    depot_cord = instance["depot_cord"]
    customer_cord = instance["customer_cord"]
    supplier_cord = instance["supplier_cord"]
    demand = instance["demand"]
    supplier_supply = instance["supplier_supply"]
    n_suppliers = instance["n_suppliers"]
    vehicle_capacity = instance["vehicle_capacity"]
    average_speed = instance["average_speed"]
    service_time = instance["service_time"]
    euc_distance = instance["euc_distance"]
    supplier_euc_distance = instance["supplier_euc_distance"]

    INSTANCE_NAME = (
        f"{config['n_customers']}c_"
        f"cap{config['vehicle_capacity']}"
    )

    (
        supply_feasibility,
        total_demand,
        total_supply,
    ) = supplier_preprocessing_v1.supplier_depot_echelon(
        demand,
        supplier_supply,
    )

    supplier_depot_distance = []

    for supplier in range(1, n_suppliers + 1):
        trip_distance = supplier_euc_distance(supplier, 0)
        supplier_depot_distance.append(trip_distance)

    total_first_echelon_distance = sum(supplier_depot_distance)

    cluster_count = min(3, len(customer_cord))

    clusters = kmeans_clustering_v1.kmeans_clustering(
        customer_cord,
        K=cluster_count,
    )

    all_routes = []
    all_two_opt_routes = []
    all_relocation_routes = []

    baseline_cluster_distances = []
    baseline_cluster_travel_times = []
    baseline_cluster_trip_counts = []
    cluster_two_opt_distances = []
    cluster_two_opt_travel_times = []
    baseline_cluster_capacity_flags = []
    baseline_cluster_structural_flags = []
    baseline_cluster_unserved = []

    for cluster in clusters:
        cluster_customer_cord, cluster_demand = kmeans_clustering_v1.get_cluster_data(
            cluster,
            customer_cord,
            demand,
        )

        # Unpack the full baseline output so the experiment can use the route now
        # and keep the other summary values available later.
        (
            route,
            total_distance,
            number_of_trip,
            total_travel_time,
            capacity_feasibility,
            structural_validity,
            vehicle_capacity_used,
            unserved_customers,
        ) = baseline_nn_2opt_relocation_2opt_v1.run_baseline_nn(
            depot_cord,
            cluster_customer_cord,
            cluster_demand,
            vehicle_capacity,
            average_speed,
            service_time,
        )

        two_opt_route = baseline_nn_2opt_relocation_2opt_v1.run_2opt(
            route,
            euc_distance,
        )

        two_opt_distance = 0
        two_opt_travel_time = 0

        for trip in two_opt_route:
            trip_distance = 0

            for c in range(len(trip) - 1):
                trip_distance += euc_distance(trip[c], trip[c + 1])

            trip_time = trip_distance / average_speed

            for customer in trip[1:-1]:
                trip_time += service_time[customer] / 60

            two_opt_distance += trip_distance
            two_opt_travel_time += trip_time

        all_routes.extend(route)
        all_two_opt_routes.extend(two_opt_route)

        baseline_cluster_distances.append(total_distance)
        baseline_cluster_travel_times.append(total_travel_time)
        baseline_cluster_trip_counts.append(number_of_trip)
        cluster_two_opt_distances.append(two_opt_distance)
        cluster_two_opt_travel_times.append(two_opt_travel_time)
        baseline_cluster_capacity_flags.append(capacity_feasibility)
        baseline_cluster_structural_flags.append(structural_validity)
        baseline_cluster_unserved.extend(unserved_customers)

    all_relocation_routes = baseline_nn_2opt_relocation_2opt_v1.run_relocation(
        copy.deepcopy(all_two_opt_routes),
        demand,
        vehicle_capacity,
        euc_distance,
    )

    all_post_reloc_2opt_routes = baseline_nn_2opt_relocation_2opt_v1.run_2opt(
        copy.deepcopy(all_relocation_routes),
        euc_distance,
    )

    results_path = create_experiment_folder(
        "supplier_depot_customer_baseline_kmeans_v1",
        INSTANCE_NAME,
    )

    total_distance = sum(baseline_cluster_distances)
    total_travel_time = sum(baseline_cluster_travel_times)
    two_opt_distance = sum(cluster_two_opt_distances)
    two_opt_travel_time = sum(cluster_two_opt_travel_times)
    number_of_trip = len(all_post_reloc_2opt_routes)
    capacity_feasibility = all(baseline_cluster_capacity_flags)
    structural_validity = all(baseline_cluster_structural_flags)
    all_customers_served = len(baseline_cluster_unserved) == 0

    relocation_distance = 0
    relocation_travel_time = 0

    for trip in all_relocation_routes:
        trip_distance = 0

        for c in range(len(trip) - 1):
            trip_distance += euc_distance(trip[c], trip[c + 1])

        trip_time = trip_distance / average_speed

        for customer in trip[1:-1]:
            trip_time += service_time[customer] / 60

        relocation_distance += trip_distance
        relocation_travel_time += trip_time

    post_reloc_2opt_distance = 0
    post_reloc_2opt_travel_time = 0

    for trip in all_post_reloc_2opt_routes:
        trip_distance = 0

        for c in range(len(trip) - 1):
            trip_distance += euc_distance(trip[c], trip[c + 1])

        trip_time = trip_distance / average_speed

        for customer in trip[1:-1]:
            trip_time += service_time[customer] / 60

        post_reloc_2opt_distance += trip_distance
        post_reloc_2opt_travel_time += trip_time

    baseline_trip_distances = []

    for trip in all_routes:
        trip_distance = 0

        for c in range(len(trip) - 1):
            trip_distance += euc_distance(trip[c], trip[c + 1])

        baseline_trip_distances.append(trip_distance)

    baseline_trip_loads = []

    for trip in all_routes:
        trip_load = 0

        for customer in trip[1:-1]:
            trip_load += demand[customer]

        baseline_trip_loads.append(trip_load)

    customers_per_trip_baseline = []

    for trip in all_routes:
        customers_per_trip_baseline.append(len(trip) - 2)

    baseline_trip_utilization = []

    for trip in all_routes:
        trip_load = 0

        for customer in trip[1:-1]:
            trip_load += demand[customer]

        utilization = trip_load / vehicle_capacity
        baseline_trip_utilization.append(utilization)

    baseline_avg_utilization = sum(baseline_trip_utilization) / len(baseline_trip_utilization)
    baseline_max_utilization = max(baseline_trip_utilization)
    baseline_min_utilization = min(baseline_trip_utilization)

    two_opt_trip_distances = []

    for trip in all_two_opt_routes:
        trip_distance = 0

        for c in range(len(trip) - 1):
            trip_distance += euc_distance(trip[c], trip[c + 1])

        two_opt_trip_distances.append(trip_distance)

    two_opt_trip_loads = []

    for trip in all_two_opt_routes:
        trip_load = 0

        for customer in trip[1:-1]:
            trip_load += demand[customer]

        two_opt_trip_loads.append(trip_load)

    customers_per_trip_2opt = []

    for trip in all_two_opt_routes:
        customers_per_trip_2opt.append(len(trip) - 2)

    two_opt_trip_utilization = []

    for trip in all_two_opt_routes:
        trip_load = 0

        for customer in trip[1:-1]:
            trip_load += demand[customer]

        utilization = trip_load / vehicle_capacity
        two_opt_trip_utilization.append(utilization)

    two_opt_avg_utilization = sum(two_opt_trip_utilization) / len(two_opt_trip_utilization)
    two_opt_max_utilization = max(two_opt_trip_utilization)
    two_opt_min_utilization = min(two_opt_trip_utilization)

    relocation_trip_distances = []

    for trip in all_relocation_routes:
        trip_distance = 0

        for c in range(len(trip) - 1):
            trip_distance += euc_distance(trip[c], trip[c + 1])

        relocation_trip_distances.append(trip_distance)

    relocation_trip_loads = []

    for trip in all_relocation_routes:
        trip_load = 0

        for customer in trip[1:-1]:
            trip_load += demand[customer]

        relocation_trip_loads.append(trip_load)

    customers_per_trip_relocation = []

    for trip in all_relocation_routes:
        customers_per_trip_relocation.append(len(trip) - 2)

    relocation_trip_utilization = []

    for trip in all_relocation_routes:
        trip_load = 0

        for customer in trip[1:-1]:
            trip_load += demand[customer]

        utilization = trip_load / vehicle_capacity
        relocation_trip_utilization.append(utilization)

    relocation_avg_utilization = sum(relocation_trip_utilization) / len(relocation_trip_utilization)
    relocation_max_utilization = max(relocation_trip_utilization)
    relocation_min_utilization = min(relocation_trip_utilization)

    post_reloc_2opt_trip_distances = []

    for trip in all_post_reloc_2opt_routes:
        trip_distance = 0

        for c in range(len(trip) - 1):
            trip_distance += euc_distance(trip[c], trip[c + 1])

        post_reloc_2opt_trip_distances.append(trip_distance)

    post_reloc_2opt_trip_loads = []

    for trip in all_post_reloc_2opt_routes:
        trip_load = 0

        for customer in trip[1:-1]:
            trip_load += demand[customer]

        post_reloc_2opt_trip_loads.append(trip_load)

    customers_per_trip_post_reloc_2opt = []

    for trip in all_post_reloc_2opt_routes:
        customers_per_trip_post_reloc_2opt.append(len(trip) - 2)

    post_reloc_2opt_trip_utilization = []

    for trip in all_post_reloc_2opt_routes:
        trip_load = 0

        for customer in trip[1:-1]:
            trip_load += demand[customer]

        utilization = trip_load / vehicle_capacity
        post_reloc_2opt_trip_utilization.append(utilization)

    post_reloc_2opt_avg_utilization = (
        sum(post_reloc_2opt_trip_utilization)
        / len(post_reloc_2opt_trip_utilization)
    )
    post_reloc_2opt_max_utilization = max(post_reloc_2opt_trip_utilization)
    post_reloc_2opt_min_utilization = min(post_reloc_2opt_trip_utilization)

    metrics = {
        "algorithm": "supplier_depot_customer_baseline_kmeans_v1",
        "instance": INSTANCE_NAME,
        "seed": 42,
        "construction": "k_means_clustering + nearest_neighbor",
        "local_search": "2-opt + global 1-0 relocation + 2-opt",
        "relocation_scope": "global",
        "total_first_echelon_distance": total_first_echelon_distance,
        "baseline_distance": total_distance,
        "baseline_total_system_distance": total_first_echelon_distance + total_distance,
        "two_opt_distance": two_opt_distance,
        "two_opt_total_system_distance": total_first_echelon_distance + two_opt_distance,
        "relocation_distance": relocation_distance,
        "relocation_total_system_distance": total_first_echelon_distance + relocation_distance,
        "post_reloc_2opt_distance": post_reloc_2opt_distance,
        "post_reloc_2opt_total_system_distance": total_first_echelon_distance + post_reloc_2opt_distance,
        "two_opt_gain_over_baseline": total_distance - two_opt_distance,
        "two_opt_percent_gain_over_baseline": ((total_distance - two_opt_distance) / total_distance) * 100,
        "relocation_gain_over_2opt": two_opt_distance - relocation_distance,
        "relocation_percent_gain_over_2opt": ((two_opt_distance - relocation_distance) / two_opt_distance) * 100,
        "relocation_gain_over_baseline": total_distance - relocation_distance,
        "relocation_percent_gain_over_baseline": ((total_distance - relocation_distance) / total_distance) * 100,
        "post_reloc_2opt_gain_over_relocation": relocation_distance - post_reloc_2opt_distance,
        "post_reloc_2opt_percent_gain_over_relocation": ((relocation_distance - post_reloc_2opt_distance) / relocation_distance) * 100,
        "total_demand": total_demand,
        "total_supply": total_supply,
        "supply_feasibility": supply_feasibility,
        "n_suppliers": n_suppliers,
        "supplier_depot_distance": supplier_depot_distance,
        "supplier_cord": supplier_cord,
        "supplier_supply": supplier_supply,
        "baseline_travel_time": total_travel_time,
        "two_opt_travel_time": two_opt_travel_time,
        "relocation_travel_time": relocation_travel_time,
        "post_reloc_2opt_travel_time": post_reloc_2opt_travel_time,
        "trips": number_of_trip,
        "capacity_feasibility": capacity_feasibility,
        "structural_validity": structural_validity,
        "all_customers_served": all_customers_served,
        "vehicle_capacity": vehicle_capacity,
        "unserved_customers": baseline_cluster_unserved,
        "n_customers": len(customer_cord),
        "depot": depot_cord,
        "clusters": clusters,
        "baseline_cluster_distances": baseline_cluster_distances,
        "baseline_cluster_travel_times": baseline_cluster_travel_times,
        "baseline_cluster_trip_counts": baseline_cluster_trip_counts,
        "cluster_two_opt_distances": cluster_two_opt_distances,
        "cluster_two_opt_travel_times": cluster_two_opt_travel_times,
        "baseline_trip_distances": baseline_trip_distances,
        "two_opt_trip_distances": two_opt_trip_distances,
        "relocation_trip_distances": relocation_trip_distances,
        "post_reloc_2opt_trip_distances": post_reloc_2opt_trip_distances,
        "baseline_trip_loads": baseline_trip_loads,
        "two_opt_trip_loads": two_opt_trip_loads,
        "relocation_trip_loads": relocation_trip_loads,
        "post_reloc_2opt_trip_loads": post_reloc_2opt_trip_loads,
        "customers_per_trip_baseline": customers_per_trip_baseline,
        "customers_per_trip_2opt": customers_per_trip_2opt,
        "customers_per_trip_relocation": customers_per_trip_relocation,
        "customers_per_trip_post_reloc_2opt": customers_per_trip_post_reloc_2opt,
        "baseline_trip_utilization": baseline_trip_utilization,
        "two_opt_trip_utilization": two_opt_trip_utilization,
        "relocation_trip_utilization": relocation_trip_utilization,
        "post_reloc_2opt_trip_utilization": post_reloc_2opt_trip_utilization,
        "baseline_avg_utilization": baseline_avg_utilization,
        "two_opt_avg_utilization": two_opt_avg_utilization,
        "relocation_avg_utilization": relocation_avg_utilization,
        "post_reloc_2opt_avg_utilization": post_reloc_2opt_avg_utilization,
        "baseline_max_utilization": baseline_max_utilization,
        "two_opt_max_utilization": two_opt_max_utilization,
        "relocation_max_utilization": relocation_max_utilization,
        "post_reloc_2opt_max_utilization": post_reloc_2opt_max_utilization,
        "baseline_min_utilization": baseline_min_utilization,
        "two_opt_min_utilization": two_opt_min_utilization,
        "relocation_min_utilization": relocation_min_utilization,
        "post_reloc_2opt_min_utilization": post_reloc_2opt_min_utilization,
    }

    with open(f"{results_path}/config_used.json", "w") as f:
        json.dump(config, f, indent=4)

    with open(f"{results_path}/clusters.json", "w") as f:
        json.dump(
            {
                "K": cluster_count,
                "clusters": clusters,
                "cluster_loads": [
                    sum(demand[customer] for customer in cluster)
                    for cluster in clusters
                ],
            },
            f,
            indent=4,
        )

    with open(f"{results_path}/metrics.json", "w") as f:
        json.dump(metrics, f, indent=4)

    with open(f"{results_path}/route_baseline.txt", "w") as f:
        f.write(str(all_routes))

    with open(f"{results_path}/route_two_opt.txt", "w") as f:
        f.write(str(all_two_opt_routes))

    with open(f"{results_path}/route_relocation.txt", "w") as f:
        f.write(str(all_relocation_routes))

    with open(f"{results_path}/route_post_reloc_2opt.txt", "w") as f:
        f.write(str(all_post_reloc_2opt_routes))

    plot_routes(
        all_routes,
        depot_cord,
        customer_cord,
        results_path,
        filename="route_plot_baseline.png",
        title="Vehicle Routes - KMeans + Baseline NN",
        supplier_cord=supplier_cord,
    )

    plot_routes(
        all_two_opt_routes,
        depot_cord,
        customer_cord,
        results_path,
        filename="route_plot_two_opt.png",
        title="Vehicle Routes - KMeans + Baseline NN + 2-Opt",
        supplier_cord=supplier_cord,
    )

    plot_routes(
        all_relocation_routes,
        depot_cord,
        customer_cord,
        results_path,
        filename="route_plot_relocation.png",
        title="Vehicle Routes - KMeans + Baseline NN + 2-Opt + Global 1-0 Relocation",
        supplier_cord=supplier_cord,
    )

    plot_routes(
        all_post_reloc_2opt_routes,
        depot_cord,
        customer_cord,
        results_path,
        filename="route_plot_post_reloc_2opt.png",
        title="Vehicle Routes - KMeans + Baseline NN + 2-Opt + Global 1-0 Relocation + 2-Opt",
        supplier_cord=supplier_cord,
    )

    print("Results stored in:", results_path)


if __name__ == "__main__":
    config = {
        "n_customers": 60,
        "vehicle_capacity": 25,
        "n_suppliers": 3,
        "seed": 42,
    }

    run_experiment(config)
