"""Basic depot-customer Sweep experiment pipeline."""

import json
import os
import sys
from importlib import import_module
from pathlib import Path


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(PROJECT_ROOT)
os.environ.setdefault("MPLCONFIGDIR", os.path.join(PROJECT_ROOT, ".matplotlib_cache"))

from instances.generate_depot_customer_instance import generate_depot_customer_instance
from solvers.nearest_neighbor import run_baseline_nn, total_route_distance
from solvers.relocation import run_relocation
from solvers.two_opt import run_2opt
from utils.experiment_logger import create_experiment_folder
from utils.plot_routes import plot_routes


sweep = import_module("construction.01_sweep_clustering_v1")

DEFAULT_INSTANCE_MODULE = "instances.toy_instance_v1_40c"
DEFAULT_RESULT_DIR = Path("results/depot_customer_sweep")
ALGORITHM_NAME = "generated_depot_customer_sweep_initial_pipeline"

# RUN_MODE = "test"
RUN_MODE = "batch"

# TODO: Experimental runs should cover both depot positions:
# corner depot, e.g. (0, 0), and center depot, e.g. (5, 5) for a 10x10 grid.
# No pipeline logic change is needed; only the instance depot_cord changes.


def load_instance_data(instance_module_path=DEFAULT_INSTANCE_MODULE):
    instance = import_module(instance_module_path)

    return {
        "instance_name": instance_module_path.split(".")[-1],
        "depot_cord": instance.depot_cord,
        "customer_cord": instance.customer_cord,
        "demand": instance.demand,
        "vehicle_capacity": instance.vehicle_capacity,
    }


def build_sweep_clusters(depot_cord, customer_cord, demand, vehicle_capacity):
    angle_data = sweep.compute_sweep_order(depot_cord, customer_cord, demand)
    clusters = sweep.form_sweep_clusters(angle_data, vehicle_capacity)

    return angle_data, clusters


def experiment_label(config):
    return (
        f"{config['n_customers']}c_"
        f"cap{config['vehicle_capacity']}_"
        f"dem{config.get('min_demand', 1)}-{config.get('max_demand', 6)}"
    )


def trip_distance(route, depot_cord, customer_cord):
    return total_route_distance([route], depot_cord, customer_cord)


def route_load(route, demand):
    return sum(demand[node_id] for node_id in route if node_id != 0)


def trip_distances(routes, depot_cord, customer_cord):
    return [trip_distance(route, depot_cord, customer_cord) for route in routes]


def trip_loads(routes, demand):
    return [route_load(route, demand) for route in routes]


def trip_utilization(routes, demand, vehicle_capacity):
    return [route_load(route, demand) / vehicle_capacity for route in routes]


def total_travel_time(routes, depot_cord, customer_cord, service_time, average_speed):
    total_time = 0

    for route in routes:
        route_time = trip_distance(route, depot_cord, customer_cord) / average_speed
        for customer_id in route[1:-1]:
            route_time += service_time[customer_id] / 60
        total_time += route_time

    return total_time


def structural_validity(routes):
    for route in routes:
        if route[0] != 0 or route[-1] != 0:
            return False
        if 0 in route[1:-1]:
            return False
    return True


def capacity_feasibility(routes, demand, vehicle_capacity):
    return all(route_load(route, demand) <= vehicle_capacity for route in routes)


def all_customers_served(routes, customer_cord):
    served_customers = []
    for route in routes:
        served_customers.extend(route[1:-1])

    return sorted(served_customers) == sorted(customer_cord.keys())


def stage_metrics(stage_name, routes, instance):
    depot_cord = instance["depot_cord"]
    customer_cord = instance["customer_cord"]
    demand = instance["demand"]
    vehicle_capacity = instance["vehicle_capacity"]
    utilization = trip_utilization(routes, demand, vehicle_capacity)

    return {
        f"{stage_name}_distance": total_route_distance(
            routes,
            depot_cord,
            customer_cord,
        ),
        f"{stage_name}_travel_time": total_travel_time(
            routes,
            depot_cord,
            customer_cord,
            instance["service_time"],
            instance["average_speed"],
        ),
        f"{stage_name}_trip_distances": trip_distances(
            routes,
            depot_cord,
            customer_cord,
        ),
        f"{stage_name}_trip_loads": trip_loads(routes, demand),
        f"{stage_name}_customers_per_trip": [len(route) - 2 for route in routes],
        f"{stage_name}_trip_utilization": utilization,
        f"{stage_name}_avg_utilization": sum(utilization) / len(utilization),
        f"{stage_name}_max_utilization": max(utilization),
        f"{stage_name}_min_utilization": min(utilization),
    }


def validate_clusters(clusters, demand, vehicle_capacity, depot_id=0):
    expected_customers = set(demand.keys()) - {depot_id}
    clustered_customers = [customer_id for cluster in clusters for customer_id in cluster]
    clustered_customer_set = set(clustered_customers)

    duplicate_customers = sorted(
        customer_id
        for customer_id in clustered_customer_set
        if clustered_customers.count(customer_id) > 1
    )
    missing_customers = sorted(expected_customers - clustered_customer_set)
    extra_customers = sorted(clustered_customer_set - expected_customers)

    cluster_loads = [sum(demand[customer_id] for customer_id in cluster) for cluster in clusters]
    overloaded_clusters = [
        {
            "cluster_index": index,
            "load": load,
            "customers": clusters[index],
        }
        for index, load in enumerate(cluster_loads)
        if load > vehicle_capacity
    ]

    return {
        "num_clusters": len(clusters),
        "num_expected_customers": len(expected_customers),
        "num_clustered_customers": len(clustered_customers),
        "cluster_loads": cluster_loads,
        "missing_customers": missing_customers,
        "duplicate_customers": duplicate_customers,
        "extra_customers": extra_customers,
        "overloaded_clusters": overloaded_clusters,
        "is_valid": (
            len(missing_customers) == 0
            and len(duplicate_customers) == 0
            and len(extra_customers) == 0
            and len(overloaded_clusters) == 0
        ),
    }


def validate_routes(routes, demand, depot_id=0):
    expected_customers = set(demand.keys()) - {depot_id}
    routed_customers = [
        customer_id
        for route in routes
        for customer_id in route
        if customer_id != depot_id
    ]
    routed_customer_set = set(routed_customers)

    duplicate_customers = sorted(
        customer_id
        for customer_id in routed_customer_set
        if routed_customers.count(customer_id) > 1
    )
    missing_customers = sorted(expected_customers - routed_customer_set)
    extra_customers = sorted(routed_customer_set - expected_customers)

    return {
        "num_routes": len(routes),
        "num_expected_customers": len(expected_customers),
        "num_routed_customers": len(routed_customers),
        "missing_customers": missing_customers,
        "duplicate_customers": duplicate_customers,
        "extra_customers": extra_customers,
        "is_valid": (
            len(missing_customers) == 0
            and len(duplicate_customers) == 0
            and len(extra_customers) == 0
        ),
    }


def run_cluster_routing(
    depot_cord,
    customer_cord,
    demand,
    clusters,
    routing_fn,
    **routing_kwargs,
):
    all_routes = []

    for cluster in clusters:
        cluster_customer_cord, cluster_demand = sweep.get_cluster_data(
            cluster,
            customer_cord,
            demand,
        )

        routes = routing_fn(
            depot_cord,
            cluster_customer_cord,
            cluster_demand,
            **routing_kwargs,
        )

        all_routes.extend(routes)

    return all_routes


def run_sweep_nn_experiment(
    depot_cord,
    customer_cord,
    demand,
    vehicle_capacity,
    depot_id=0,
):
    angle_data, clusters = build_sweep_clusters(
        depot_cord,
        customer_cord,
        demand,
        vehicle_capacity,
    )
    cluster_check = validate_clusters(clusters, demand, vehicle_capacity)

    routes = run_cluster_routing(
        depot_cord,
        customer_cord,
        demand,
        clusters,
        run_baseline_nn,
        vehicle_capacity=vehicle_capacity,
        depot_id=depot_id,
    )
    route_check = validate_routes(routes, demand, depot_id)
    total_distance = total_route_distance(routes, depot_cord, customer_cord, depot_id)

    return {
        "algorithm": "depot_customer_sweep_nn_v1",
        "angle_data": angle_data,
        "clusters": clusters,
        "cluster_check": cluster_check,
        "routes": routes,
        "route_check": route_check,
        "total_distance": total_distance,
        "number_of_clusters": len(clusters),
        "number_of_routes": len(routes),
    }


def run_sweep_nn_2opt_experiment(
    depot_cord,
    customer_cord,
    demand,
    vehicle_capacity,
    depot_id=0,
):
    nn_result = run_sweep_nn_experiment(
        depot_cord,
        customer_cord,
        demand,
        vehicle_capacity,
        depot_id=depot_id,
    )

    two_opt_routes = run_2opt(
        nn_result["routes"],
        depot_cord,
        customer_cord,
        depot_id,
    )
    two_opt_route_check = validate_routes(two_opt_routes, demand, depot_id)
    two_opt_distance = total_route_distance(
        two_opt_routes,
        depot_cord,
        customer_cord,
        depot_id,
    )

    return {
        **nn_result,
        "algorithm": "depot_customer_sweep_nn_2opt_v1",
        "nn_routes": nn_result["routes"],
        "nn_total_distance": nn_result["total_distance"],
        "routes": two_opt_routes,
        "route_check": two_opt_route_check,
        "total_distance": two_opt_distance,
        "two_opt_absolute_improvement": nn_result["total_distance"] - two_opt_distance,
        "two_opt_percent_improvement": (
            (nn_result["total_distance"] - two_opt_distance)
            / nn_result["total_distance"]
            * 100
            if nn_result["total_distance"] > 0
            else 0
        ),
    }


def run_sweep_nn_2opt_relocation_2opt_experiment(
    depot_cord,
    customer_cord,
    demand,
    vehicle_capacity,
    depot_id=0,
):
    two_opt_result = run_sweep_nn_2opt_experiment(
        depot_cord,
        customer_cord,
        demand,
        vehicle_capacity,
        depot_id=depot_id,
    )

    relocation_routes = run_relocation(
        two_opt_result["routes"],
        depot_cord,
        customer_cord,
        demand,
        vehicle_capacity,
        depot_id,
    )
    relocation_route_check = validate_routes(relocation_routes, demand, depot_id)
    relocation_distance = total_route_distance(
        relocation_routes,
        depot_cord,
        customer_cord,
        depot_id,
    )

    post_reloc_2opt_routes = run_2opt(
        relocation_routes,
        depot_cord,
        customer_cord,
        depot_id,
    )
    post_reloc_2opt_route_check = validate_routes(
        post_reloc_2opt_routes,
        demand,
        depot_id,
    )
    post_reloc_2opt_distance = total_route_distance(
        post_reloc_2opt_routes,
        depot_cord,
        customer_cord,
        depot_id,
    )

    two_opt_distance = two_opt_result["total_distance"]

    return {
        **two_opt_result,
        "algorithm": "depot_customer_sweep_nn_2opt_relocation_2opt_v1",
        "local_search": "2-opt + global 1-0 relocation + 2-opt",
        "relocation_scope": "global",
        "two_opt_routes": two_opt_result["routes"],
        "two_opt_distance": two_opt_distance,
        "relocation_routes": relocation_routes,
        "relocation_route_check": relocation_route_check,
        "relocation_distance": relocation_distance,
        "routes": post_reloc_2opt_routes,
        "route_check": post_reloc_2opt_route_check,
        "total_distance": post_reloc_2opt_distance,
        "post_reloc_2opt_routes": post_reloc_2opt_routes,
        "post_reloc_2opt_distance": post_reloc_2opt_distance,
        "relocation_gain_over_2opt": two_opt_distance - relocation_distance,
        "relocation_percent_gain_over_2opt": (
            (two_opt_distance - relocation_distance) / two_opt_distance * 100
            if two_opt_distance > 0
            else 0
        ),
        "post_reloc_2opt_gain_over_relocation": (
            relocation_distance - post_reloc_2opt_distance
        ),
        "post_reloc_2opt_percent_gain_over_relocation": (
            (relocation_distance - post_reloc_2opt_distance)
            / relocation_distance
            * 100
            if relocation_distance > 0
            else 0
        ),
    }


def add_instance_metadata(result, instance_data, instance_module_path):
    result["instance_name"] = instance_data["instance_name"]
    result["instance_module"] = instance_module_path

    return result


def run_from_instance(instance_module_path=DEFAULT_INSTANCE_MODULE, depot_id=0):
    instance_data = load_instance_data(instance_module_path)

    result = run_sweep_nn_experiment(
        instance_data["depot_cord"],
        instance_data["customer_cord"],
        instance_data["demand"],
        instance_data["vehicle_capacity"],
        depot_id=depot_id,
    )

    return add_instance_metadata(result, instance_data, instance_module_path)


def run_final_from_instance(instance_module_path=DEFAULT_INSTANCE_MODULE, depot_id=0):
    instance_data = load_instance_data(instance_module_path)

    result = run_sweep_nn_2opt_relocation_2opt_experiment(
        instance_data["depot_cord"],
        instance_data["customer_cord"],
        instance_data["demand"],
        instance_data["vehicle_capacity"],
        depot_id=depot_id,
    )

    return add_instance_metadata(result, instance_data, instance_module_path)


def build_generated_metrics(config, instance, result, routes_by_stage):
    baseline_distance = total_route_distance(
        routes_by_stage["baseline"],
        instance["depot_cord"],
        instance["customer_cord"],
    )
    final_distance = total_route_distance(
        routes_by_stage["post_reloc_2opt"],
        instance["depot_cord"],
        instance["customer_cord"],
    )

    metrics = {
        "algorithm": ALGORITHM_NAME,
        "construction": "sweep_clustering + nearest_neighbor",
        "local_search": "2-opt + global 1-0 relocation + 2-opt",
        "relocation_scope": result["relocation_scope"],
        "instance": experiment_label(config),
        "seed": config["seed"],
        "n_customers": instance["n_customers"],
        "grid_size": instance["grid_size"],
        "depot_cord": instance["depot_cord"],
        "vehicle_capacity": instance["vehicle_capacity"],
        "min_demand": config.get("min_demand", 1),
        "max_demand": config.get("max_demand", 6),
        "average_speed": instance["average_speed"],
        "service_time": config.get("service_time", 10),
        "number_of_clusters": result["number_of_clusters"],
        "cluster_loads": result["cluster_check"]["cluster_loads"],
        "cluster_check": result["cluster_check"],
        "trips": len(routes_by_stage["post_reloc_2opt"]),
        "capacity_feasibility": capacity_feasibility(
            routes_by_stage["post_reloc_2opt"],
            instance["demand"],
            instance["vehicle_capacity"],
        ),
        "structural_validity": structural_validity(routes_by_stage["post_reloc_2opt"]),
        "all_customers_served": all_customers_served(
            routes_by_stage["post_reloc_2opt"],
            instance["customer_cord"],
        ),
        "final_absolute_improvement": baseline_distance - final_distance,
        "final_percent_improvement": (
            (baseline_distance - final_distance) / baseline_distance
        )
        * 100,
    }

    for stage_name, routes in routes_by_stage.items():
        metrics.update(stage_metrics(stage_name, routes, instance))

    metrics["two_opt_gain_over_baseline"] = (
        metrics["baseline_distance"] - metrics["two_opt_distance"]
    )
    metrics["relocation_gain_over_2opt"] = (
        metrics["two_opt_distance"] - metrics["relocation_distance"]
    )
    metrics["post_reloc_2opt_gain_over_relocation"] = (
        metrics["relocation_distance"] - metrics["post_reloc_2opt_distance"]
    )

    return metrics


def run_generated_experiment(config):
    instance = generate_depot_customer_instance(config)
    label = experiment_label(config)
    results_path = create_experiment_folder(ALGORITHM_NAME, label)

    result = run_sweep_nn_2opt_relocation_2opt_experiment(
        instance["depot_cord"],
        instance["customer_cord"],
        instance["demand"],
        instance["vehicle_capacity"],
    )

    routes_by_stage = {
        "baseline": result["nn_routes"],
        "two_opt": result["two_opt_routes"],
        "relocation": result["relocation_routes"],
        "post_reloc_2opt": result["post_reloc_2opt_routes"],
    }
    metrics = build_generated_metrics(config, instance, result, routes_by_stage)

    with open(f"{results_path}/config_used.json", "w") as file_handle:
        json.dump(config, file_handle, indent=4)

    with open(f"{results_path}/metrics.json", "w") as file_handle:
        json.dump(metrics, file_handle, indent=4)

    with open(f"{results_path}/clusters.json", "w") as file_handle:
        json.dump(
            {
                "angle_data": result["angle_data"],
                "clusters": result["clusters"],
                "cluster_check": result["cluster_check"],
            },
            file_handle,
            indent=4,
        )

    for stage_name, routes in routes_by_stage.items():
        with open(f"{results_path}/route_{stage_name}.txt", "w") as file_handle:
            file_handle.write(str(routes))

        plot_routes(
            routes,
            instance["depot_cord"],
            instance["customer_cord"],
            results_path,
            filename=f"route_plot_{stage_name}.png",
            title=f"{label} - sweep - {stage_name}",
        )

    print("Results stored in:", results_path)
    print("Number of clusters:", metrics["number_of_clusters"])
    print("Cluster valid:", metrics["cluster_check"]["is_valid"])
    print("Final distance:", round(metrics["post_reloc_2opt_distance"], 3))
    print("Final improvement %:", round(metrics["final_percent_improvement"], 3))

    return results_path, metrics


def build_generated_experiments():
    if RUN_MODE == "test":
        return [
            {
                "n_customers": 40,
                "vehicle_capacity": 25,
                "seed": 42,
            }
        ]

    if RUN_MODE == "batch":
        experiments = []
        for n_customers in [20, 40, 60, 80]:
            for vehicle_capacity in [15, 25, 35]:
                experiments.append(
                    {
                        "n_customers": n_customers,
                        "vehicle_capacity": vehicle_capacity,
                        "seed": 42,
                    }
                )
        return experiments

    raise ValueError(f"Unsupported RUN_MODE: {RUN_MODE}")


def print_experiment_summary(result):
    print("==================================")
    print("DEPOT-CUSTOMER SWEEP NN SUMMARY")
    print("==================================")
    print(f"Algorithm: {result['algorithm']}")
    print(f"Instance: {result.get('instance_name', 'manual_data')}")
    print(f"Number of clusters: {result['number_of_clusters']}")
    print(f"Number of routes: {result['number_of_routes']}")
    print(f"Cluster valid: {result['cluster_check']['is_valid']}")
    print(f"Route valid: {result['route_check']['is_valid']}")
    print(f"Cluster loads: {result['cluster_check']['cluster_loads']}")
    print(f"Total distance: {result['total_distance']:.3f}")
    print("==================================")


def save_result_json(result, output_dir=DEFAULT_RESULT_DIR, filename=None):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if filename is None:
        algorithm = result["algorithm"]
        instance_name = result.get("instance_name", "manual_data")
        filename = f"{algorithm}__{instance_name}.json"

    output_path = output_dir / filename

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(result, file, indent=2)

    return output_path


if __name__ == "__main__":
    for experiment_config in build_generated_experiments():
        print("\n===================================")
        print("Running generated depot-customer Sweep experiment:")
        print(experiment_config)
        print("===================================\n")
        run_generated_experiment(experiment_config)
