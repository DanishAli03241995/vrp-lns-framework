# Experiment entry point: Supplier -> Customer baseline using KMeans clustering

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
angular_partition_v1 = importlib.import_module(
    "construction.04_angular_partition_assignment_v1"
)

from solvers import baseline_nn_2opt_relocation_2opt_v1
from utils.experiment_logger import create_experiment_folder
from utils.plot_routes import plot_supplier_routes


def run_experiment(config):
    instance = generate_supplier_customer_instance(config)

    depot_cord = instance["depot_cord"]
    customer_cord = instance["customer_cord"]
    supplier_cord = instance["supplier_cord"]
    demand = instance["demand"]
    n_suppliers = instance["n_suppliers"]
    vehicle_capacity = instance["vehicle_capacity"]
    average_speed = instance["average_speed"]
    service_time = instance["service_time"]
    dynamic_euc_distance = instance["dynamic_euc_distance"]

    INSTANCE_NAME = (
        f"{config['n_customers']}c_"
        f"cap{config['vehicle_capacity']}"
    )

    # ======================================================
    # System 2 preprocessing:
    # Angular partition assignment -> supplier subproblems
    # ======================================================

    supplier_subproblems = angular_partition_v1.build_system2_subproblems(
        depot_cord,
        customer_cord,
        demand,
        n_suppliers,
        supplier_cord,
    )

    # ======================================================
    # Placeholder values kept so existing metrics block remains intact.
    # These will be cleaned/refined later for System 2.
    # ======================================================

    total_first_echelon_distance = 0
    supplier_depot_distance = []
    total_demand = sum(demand.values())
    total_supply = None
    supply_feasibility = True
    supplier_supply = {}

    all_routes = []
    all_two_opt_routes = []
    all_relocation_routes = []
    all_post_reloc_2opt_routes = []

    baseline_route_records = []
    two_opt_route_records = []
    relocation_route_records = []
    post_reloc_2opt_route_records = []

    baseline_trip_distances = []
    two_opt_trip_distances = []
    relocation_trip_distances = []
    post_reloc_2opt_trip_distances = []

    baseline_trip_loads = []
    two_opt_trip_loads = []
    relocation_trip_loads = []
    post_reloc_2opt_trip_loads = []

    customers_per_trip_baseline = []
    customers_per_trip_2opt = []
    customers_per_trip_relocation = []
    customers_per_trip_post_reloc_2opt = []

    baseline_trip_utilization = []
    two_opt_trip_utilization = []
    relocation_trip_utilization = []
    post_reloc_2opt_trip_utilization = []

    relocation_travel_time = 0
    post_reloc_2opt_travel_time = 0

    baseline_cluster_distances = []
    baseline_cluster_travel_times = []
    baseline_cluster_trip_counts = []
    cluster_two_opt_distances = []
    cluster_two_opt_travel_times = []
    baseline_cluster_capacity_flags = []
    baseline_cluster_structural_flags = []
    baseline_cluster_unserved = []

    all_clusters = []
    supplier_metrics = {}

    # ======================================================
    # System 2 routing:
    # For each supplier -> cluster internally -> route locally
    # ======================================================

    for supplier_id, subproblem in supplier_subproblems.items():
        supplier_origin = subproblem["origin"]
        supplier_customer_cord = subproblem["customer_cord"]
        supplier_demand = subproblem["demand"]

        # skip empty supplier regions
        if len(supplier_customer_cord) == 0:
            continue

        current_routing_distance = lambda i, j: dynamic_euc_distance(
            i,
            j,
            supplier_origin,
            supplier_customer_cord,
        )

        supplier_relocation_distance = 0
        supplier_relocation_travel_time = 0
        supplier_post_reloc_2opt_distance = 0
        supplier_post_reloc_2opt_travel_time = 0

        # Intent: Build supplier-local KMeans clusters inside this supplier region.
        internal_k = min(3, len(supplier_customer_cord))

        clusters = kmeans_clustering_v1.kmeans_clustering(
            supplier_customer_cord,
            K=internal_k,
        )

        all_clusters.extend(clusters)

        supplier_routes = []
        supplier_two_opt_routes = []

        supplier_baseline_cluster_distances = []
        supplier_baseline_cluster_travel_times = []
        supplier_baseline_cluster_trip_counts = []
        supplier_cluster_two_opt_distances = []
        supplier_cluster_two_opt_travel_times = []
        supplier_baseline_capacity_flags = []
        supplier_baseline_structural_flags = []
        supplier_baseline_unserved = []

        supplier_baseline_trip_distances = []
        supplier_two_opt_trip_distances = []
        supplier_relocation_trip_distances = []
        supplier_post_reloc_2opt_trip_distances = []

        supplier_baseline_trip_loads = []
        supplier_two_opt_trip_loads = []
        supplier_relocation_trip_loads = []
        supplier_post_reloc_2opt_trip_loads = []

        supplier_customers_per_trip_baseline = []
        supplier_customers_per_trip_2opt = []
        supplier_customers_per_trip_relocation = []
        supplier_customers_per_trip_post_reloc_2opt = []

        supplier_baseline_trip_utilization = []
        supplier_two_opt_trip_utilization = []
        supplier_relocation_trip_utilization = []
        supplier_post_reloc_2opt_trip_utilization = []

        for cluster in clusters:
            cluster_customer_cord, cluster_demand = kmeans_clustering_v1.get_cluster_data(
                cluster,
                supplier_customer_cord,
                supplier_demand,
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
                supplier_origin,
                cluster_customer_cord,
                cluster_demand,
                vehicle_capacity,
                average_speed,
                service_time,
            )

            two_opt_route = baseline_nn_2opt_relocation_2opt_v1.run_2opt(
                route,
                current_routing_distance,
            )

            two_opt_distance = 0
            two_opt_travel_time = 0

            for trip in two_opt_route:
                trip_distance = 0
                for c in range(len(trip) - 1):
                    trip_distance += current_routing_distance(trip[c], trip[c + 1])

                trip_time = trip_distance / average_speed
                for customer in trip[1:-1]:
                    trip_time += service_time[customer] / 60

                two_opt_distance += trip_distance
                two_opt_travel_time += trip_time

            supplier_routes.extend(route)
            supplier_two_opt_routes.extend(two_opt_route)

            baseline_cluster_distances.append(total_distance)
            baseline_cluster_travel_times.append(total_travel_time)
            baseline_cluster_trip_counts.append(number_of_trip)
            cluster_two_opt_distances.append(two_opt_distance)
            cluster_two_opt_travel_times.append(two_opt_travel_time)
            baseline_cluster_capacity_flags.append(capacity_feasibility)
            baseline_cluster_structural_flags.append(structural_validity)
            baseline_cluster_unserved.extend(unserved_customers)

            supplier_baseline_cluster_distances.append(total_distance)
            supplier_baseline_cluster_travel_times.append(total_travel_time)
            supplier_baseline_cluster_trip_counts.append(number_of_trip)
            supplier_cluster_two_opt_distances.append(two_opt_distance)
            supplier_cluster_two_opt_travel_times.append(two_opt_travel_time)
            supplier_baseline_capacity_flags.append(capacity_feasibility)
            supplier_baseline_structural_flags.append(structural_validity)
            supplier_baseline_unserved.extend(unserved_customers)

        supplier_relocation_routes = baseline_nn_2opt_relocation_2opt_v1.run_relocation(
            copy.deepcopy(supplier_two_opt_routes),
            supplier_demand,
            vehicle_capacity,
            current_routing_distance,
        )

        supplier_post_reloc_2opt_routes = baseline_nn_2opt_relocation_2opt_v1.run_2opt(
            copy.deepcopy(supplier_relocation_routes),
            current_routing_distance,
        )

        for trip in supplier_routes:
            trip_distance = 0
            for c in range(len(trip) - 1):
                trip_distance += current_routing_distance(trip[c], trip[c + 1])

            baseline_trip_distances.append(trip_distance)
            supplier_baseline_trip_distances.append(trip_distance)

            trip_load = 0
            for customer in trip[1:-1]:
                trip_load += supplier_demand[customer]

            baseline_trip_loads.append(trip_load)
            customers_per_trip_baseline.append(len(trip) - 2)
            baseline_trip_utilization.append(trip_load / vehicle_capacity)

            supplier_baseline_trip_loads.append(trip_load)
            supplier_customers_per_trip_baseline.append(len(trip) - 2)
            supplier_baseline_trip_utilization.append(trip_load / vehicle_capacity)

        for trip in supplier_two_opt_routes:
            trip_distance = 0
            for c in range(len(trip) - 1):
                trip_distance += current_routing_distance(trip[c], trip[c + 1])

            two_opt_trip_distances.append(trip_distance)
            supplier_two_opt_trip_distances.append(trip_distance)

            trip_load = 0
            for customer in trip[1:-1]:
                trip_load += supplier_demand[customer]

            two_opt_trip_loads.append(trip_load)
            customers_per_trip_2opt.append(len(trip) - 2)
            two_opt_trip_utilization.append(trip_load / vehicle_capacity)

            supplier_two_opt_trip_loads.append(trip_load)
            supplier_customers_per_trip_2opt.append(len(trip) - 2)
            supplier_two_opt_trip_utilization.append(trip_load / vehicle_capacity)

        for trip in supplier_relocation_routes:
            trip_distance = 0
            for c in range(len(trip) - 1):
                trip_distance += current_routing_distance(trip[c], trip[c + 1])

            trip_time = trip_distance / average_speed
            for customer in trip[1:-1]:
                trip_time += service_time[customer] / 60

            supplier_relocation_distance += trip_distance
            supplier_relocation_travel_time += trip_time

            relocation_trip_distances.append(trip_distance)
            supplier_relocation_trip_distances.append(trip_distance)

            trip_load = 0
            for customer in trip[1:-1]:
                trip_load += supplier_demand[customer]

            relocation_trip_loads.append(trip_load)
            customers_per_trip_relocation.append(len(trip) - 2)
            relocation_trip_utilization.append(trip_load / vehicle_capacity)

            supplier_relocation_trip_loads.append(trip_load)
            supplier_customers_per_trip_relocation.append(len(trip) - 2)
            supplier_relocation_trip_utilization.append(trip_load / vehicle_capacity)

        for trip in supplier_post_reloc_2opt_routes:
            trip_distance = 0
            for c in range(len(trip) - 1):
                trip_distance += current_routing_distance(trip[c], trip[c + 1])

            trip_time = trip_distance / average_speed
            for customer in trip[1:-1]:
                trip_time += service_time[customer] / 60

            supplier_post_reloc_2opt_distance += trip_distance
            supplier_post_reloc_2opt_travel_time += trip_time

            post_reloc_2opt_trip_distances.append(trip_distance)
            supplier_post_reloc_2opt_trip_distances.append(trip_distance)

            trip_load = 0
            for customer in trip[1:-1]:
                trip_load += supplier_demand[customer]

            post_reloc_2opt_trip_loads.append(trip_load)
            customers_per_trip_post_reloc_2opt.append(len(trip) - 2)
            post_reloc_2opt_trip_utilization.append(trip_load / vehicle_capacity)

            supplier_post_reloc_2opt_trip_loads.append(trip_load)
            supplier_customers_per_trip_post_reloc_2opt.append(len(trip) - 2)
            supplier_post_reloc_2opt_trip_utilization.append(trip_load / vehicle_capacity)

        relocation_travel_time += supplier_relocation_travel_time
        post_reloc_2opt_travel_time += supplier_post_reloc_2opt_travel_time

        supplier_metrics[supplier_id] = {
            "origin": supplier_origin,
            "customer_cord": supplier_customer_cord,
            "demand": supplier_demand,
            "n_customers": len(supplier_customer_cord),
            "clusters": clusters,
            "baseline_distance": sum(supplier_baseline_cluster_distances),
            "two_opt_distance": sum(supplier_cluster_two_opt_distances),
            "relocation_distance": supplier_relocation_distance,
            "post_reloc_2opt_distance": supplier_post_reloc_2opt_distance,
            "baseline_travel_time": sum(supplier_baseline_cluster_travel_times),
            "two_opt_travel_time": sum(supplier_cluster_two_opt_travel_times),
            "relocation_travel_time": supplier_relocation_travel_time,
            "post_reloc_2opt_travel_time": supplier_post_reloc_2opt_travel_time,
            "trips": len(supplier_post_reloc_2opt_routes),
            "capacity_feasibility": all(supplier_baseline_capacity_flags),
            "structural_validity": all(supplier_baseline_structural_flags),
            "all_customers_served": len(supplier_baseline_unserved) == 0,
            "unserved_customers": supplier_baseline_unserved,
            "baseline_cluster_distances": supplier_baseline_cluster_distances,
            "baseline_cluster_travel_times": supplier_baseline_cluster_travel_times,
            "baseline_cluster_trip_counts": supplier_baseline_cluster_trip_counts,
            "cluster_two_opt_distances": supplier_cluster_two_opt_distances,
            "cluster_two_opt_travel_times": supplier_cluster_two_opt_travel_times,
            "baseline_trip_distances": supplier_baseline_trip_distances,
            "two_opt_trip_distances": supplier_two_opt_trip_distances,
            "relocation_trip_distances": supplier_relocation_trip_distances,
            "post_reloc_2opt_trip_distances": supplier_post_reloc_2opt_trip_distances,
            "baseline_trip_loads": supplier_baseline_trip_loads,
            "two_opt_trip_loads": supplier_two_opt_trip_loads,
            "relocation_trip_loads": supplier_relocation_trip_loads,
            "post_reloc_2opt_trip_loads": supplier_post_reloc_2opt_trip_loads,
            "customers_per_trip_baseline": supplier_customers_per_trip_baseline,
            "customers_per_trip_2opt": supplier_customers_per_trip_2opt,
            "customers_per_trip_relocation": supplier_customers_per_trip_relocation,
            "customers_per_trip_post_reloc_2opt": supplier_customers_per_trip_post_reloc_2opt,
            "baseline_trip_utilization": supplier_baseline_trip_utilization,
            "two_opt_trip_utilization": supplier_two_opt_trip_utilization,
            "relocation_trip_utilization": supplier_relocation_trip_utilization,
            "post_reloc_2opt_trip_utilization": supplier_post_reloc_2opt_trip_utilization,
            "route_baseline": supplier_routes,
            "route_2opt": supplier_two_opt_routes,
            "route_relocation": supplier_relocation_routes,
            "route_post_reloc_2opt": supplier_post_reloc_2opt_routes,
        }

        for trip in supplier_routes:
            baseline_route_records.append({
                "supplier_id": supplier_id,
                "trip": trip,
            })

        for trip in supplier_two_opt_routes:
            two_opt_route_records.append({
                "supplier_id": supplier_id,
                "trip": trip,
            })

        for trip in supplier_relocation_routes:
            relocation_route_records.append({
                "supplier_id": supplier_id,
                "trip": trip,
            })

        for trip in supplier_post_reloc_2opt_routes:
            post_reloc_2opt_route_records.append({
                "supplier_id": supplier_id,
                "trip": trip,
            })

        all_routes.extend(supplier_routes)
        all_two_opt_routes.extend(supplier_two_opt_routes)
        all_relocation_routes.extend(supplier_relocation_routes)
        all_post_reloc_2opt_routes.extend(supplier_post_reloc_2opt_routes)

    results_path = create_experiment_folder(
        "supplier_customer_only_baseline_kmeans_v1",
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

    relocation_distance = sum(relocation_trip_distances)
    post_reloc_2opt_distance = sum(post_reloc_2opt_trip_distances)

    baseline_avg_utilization = sum(baseline_trip_utilization) / len(baseline_trip_utilization)
    baseline_max_utilization = max(baseline_trip_utilization)
    baseline_min_utilization = min(baseline_trip_utilization)

    two_opt_avg_utilization = sum(two_opt_trip_utilization) / len(two_opt_trip_utilization)
    two_opt_max_utilization = max(two_opt_trip_utilization)
    two_opt_min_utilization = min(two_opt_trip_utilization)

    relocation_avg_utilization = sum(relocation_trip_utilization) / len(relocation_trip_utilization)
    relocation_max_utilization = max(relocation_trip_utilization)
    relocation_min_utilization = min(relocation_trip_utilization)

    post_reloc_2opt_avg_utilization = (
        sum(post_reloc_2opt_trip_utilization)
        / len(post_reloc_2opt_trip_utilization)
    )
    post_reloc_2opt_max_utilization = max(post_reloc_2opt_trip_utilization)
    post_reloc_2opt_min_utilization = min(post_reloc_2opt_trip_utilization)

    metrics = {
        "algorithm": "supplier_customer_only_baseline_kmeans_v1",
        "instance": INSTANCE_NAME,
        "seed": 42,
        "construction": "angular_partition + k_means_clustering + nearest_neighbor + 2-opt",
        "local_search": "2-opt + supplier-level 1-0 relocation + 2-opt",
        "relocation_scope": "supplier_level",
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
        "n_supplier_vrps": len(supplier_metrics),
        "supplier_depot_distance": supplier_depot_distance,
        "supplier_cord": supplier_cord,
        "supplier_supply": supplier_supply,
        "supplier_metrics": supplier_metrics,
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
        "clusters": all_clusters,
        "baseline_cluster_distances": baseline_cluster_distances,
        "baseline_cluster_travel_times": baseline_cluster_travel_times,
        "baseline_cluster_trip_counts": baseline_cluster_trip_counts,
        "cluster_two_opt_distances": cluster_two_opt_distances,
        "cluster_two_opt_travel_times": cluster_two_opt_travel_times,
        "baseline_trip_distances": baseline_trip_distances,
        "two_opt_trip_distances": two_opt_trip_distances,
        "relocation_trip_distances": relocation_trip_distances,
        "post_reloc_2opt_trip_distances": post_reloc_2opt_trip_distances,
        "baseline_route_records": baseline_route_records,
        "two_opt_route_records": two_opt_route_records,
        "relocation_route_records": relocation_route_records,
        "post_reloc_2opt_route_records": post_reloc_2opt_route_records,
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
                "clusters": all_clusters,
                "cluster_loads": [
                    sum(demand[customer] for customer in cluster)
                    for cluster in all_clusters
                ],
                "supplier_clusters": {
                    supplier_id: supplier_record["clusters"]
                    for supplier_id, supplier_record in supplier_metrics.items()
                },
            },
            f,
            indent=4,
        )

    with open(f"{results_path}/metrics.json", "w") as f:
        json.dump(metrics, f, indent=4)

    summary_metrics = {
        "algorithm": metrics["algorithm"],
        "instance": metrics["instance"],
        "seed": metrics["seed"],
        "n_customers": metrics["n_customers"],
        "vehicle_capacity": metrics["vehicle_capacity"],
        "baseline_distance": metrics["baseline_distance"],
        "final_distance": metrics["post_reloc_2opt_distance"],
        "improvement_distance": (
            metrics["baseline_distance"]
            - metrics["post_reloc_2opt_distance"]
        ),
        "improvement_percent": (
            (
                metrics["baseline_distance"]
                - metrics["post_reloc_2opt_distance"]
            )
            / metrics["baseline_distance"]
        ) * 100,
        "trips": metrics["trips"],
        "avg_utilization": metrics["post_reloc_2opt_avg_utilization"],
        "max_utilization": metrics["post_reloc_2opt_max_utilization"],
        "min_utilization": metrics["post_reloc_2opt_min_utilization"],
        "feasible": metrics["capacity_feasibility"],
        "structural_validity": metrics["structural_validity"],
        "customers_served": metrics["all_customers_served"],
    }

    with open(f"{results_path}/summary.json", "w") as f:
        json.dump(summary_metrics, f, indent=4)

    with open(f"{results_path}/route_baseline.txt", "w") as f:
        f.write(str(all_routes))

    with open(f"{results_path}/route_two_opt.txt", "w") as f:
        f.write(str(all_two_opt_routes))

    with open(f"{results_path}/route_relocation.txt", "w") as f:
        f.write(str(all_relocation_routes))

    with open(f"{results_path}/route_post_reloc_2opt.txt", "w") as f:
        f.write(str(all_post_reloc_2opt_routes))

    plot_supplier_routes(
        baseline_route_records,
        supplier_cord,
        customer_cord,
        results_path,
        filename="route_plot_baseline.png",
        title="Supplier-Level Routes - Angular Partition + KMeans + Baseline NN",
    )

    plot_supplier_routes(
        two_opt_route_records,
        supplier_cord,
        customer_cord,
        results_path,
        filename="route_plot_two_opt.png",
        title="Supplier-Level Routes - Angular Partition + KMeans + Baseline NN + 2-Opt",
    )

    plot_supplier_routes(
        relocation_route_records,
        supplier_cord,
        customer_cord,
        results_path,
        filename="route_plot_relocation.png",
        title="Supplier-Level Routes - Angular Partition + KMeans + 2-Opt + Supplier-Level Relocation",
    )

    plot_supplier_routes(
        post_reloc_2opt_route_records,
        supplier_cord,
        customer_cord,
        results_path,
        filename="route_plot_post_reloc_2opt.png",
        title="Supplier-Level Routes - Angular Partition + KMeans + 2-Opt + Supplier-Level Relocation + 2-Opt",
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
