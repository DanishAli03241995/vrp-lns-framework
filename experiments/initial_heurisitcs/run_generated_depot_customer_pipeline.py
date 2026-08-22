"""Run generated depot-customer instances through the initial heuristic pipeline."""

import json
import os
import sys


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(PROJECT_ROOT)
os.environ.setdefault("MPLCONFIGDIR", os.path.join(PROJECT_ROOT, ".matplotlib_cache"))


from instances.generate_depot_customer_instance import generate_depot_customer_instance
from solvers.nearest_neighbor import run_baseline_nn, total_route_distance
from solvers.relocation import run_relocation
from solvers.two_opt import run_2opt
from utils.experiment_logger import create_experiment_folder
from utils.plot_routes import plot_routes


ALGORITHM_NAME = "generated_depot_customer_initial_pipeline"

RUN_MODE = "test"
# RUN_MODE = "batch"


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


def build_metrics(config, instance, routes_by_stage):
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
        "construction": "nearest_neighbor",
        "local_search": "2-opt + relocation + 2-opt",
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


def run_experiment(config):
    instance = generate_depot_customer_instance(config)
    label = experiment_label(config)
    results_path = create_experiment_folder(ALGORITHM_NAME, label)

    baseline_routes = run_baseline_nn(
        instance["depot_cord"],
        instance["customer_cord"],
        instance["demand"],
        instance["vehicle_capacity"],
    )
    two_opt_routes = run_2opt(
        baseline_routes,
        instance["depot_cord"],
        instance["customer_cord"],
    )
    relocation_routes = run_relocation(
        two_opt_routes,
        instance["depot_cord"],
        instance["customer_cord"],
        instance["demand"],
        instance["vehicle_capacity"],
    )
    post_reloc_2opt_routes = run_2opt(
        relocation_routes,
        instance["depot_cord"],
        instance["customer_cord"],
    )

    routes_by_stage = {
        "baseline": baseline_routes,
        "two_opt": two_opt_routes,
        "relocation": relocation_routes,
        "post_reloc_2opt": post_reloc_2opt_routes,
    }
    metrics = build_metrics(config, instance, routes_by_stage)

    with open(f"{results_path}/config_used.json", "w") as file_handle:
        json.dump(config, file_handle, indent=4)

    with open(f"{results_path}/metrics.json", "w") as file_handle:
        json.dump(metrics, file_handle, indent=4)

    for stage_name, routes in routes_by_stage.items():
        with open(f"{results_path}/route_{stage_name}.txt", "w") as file_handle:
            file_handle.write(str(routes))

        plot_routes(
            routes,
            instance["depot_cord"],
            instance["customer_cord"],
            results_path,
            filename=f"route_plot_{stage_name}.png",
            title=f"{label} - {stage_name}",
        )

    print("Results stored in:", results_path)
    print("Final distance:", round(metrics["post_reloc_2opt_distance"], 3))
    print("Final improvement %:", round(metrics["final_percent_improvement"], 3))

    return results_path, metrics


def build_experiments():
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


if __name__ == "__main__":
    for experiment_config in build_experiments():
        print("\n===================================")
        print("Running generated depot-customer experiment:")
        print(experiment_config)
        print("===================================\n")
        run_experiment(experiment_config)
