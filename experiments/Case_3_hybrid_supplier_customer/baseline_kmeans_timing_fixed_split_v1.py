# Experiment entry point:
# Hybrid Supplier-Customer KMeans baseline with fixed depot timing and split repair

import sys
import os
import json
import copy
import importlib
import math

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(PROJECT_ROOT)
os.environ.setdefault("MPLCONFIGDIR", os.path.join(PROJECT_ROOT, ".matplotlib_cache"))

from instances.generate_supplier_customer_instance import (
    generate_supplier_customer_instance,
)

from solvers import baseline_nn_2opt_relocation_2opt_v1
from utils import depot_timing_split_repair_utils as depot_timing_utils
from utils.experiment_logger import create_experiment_folder
from utils.plot_routes import plot_supplier_routes


kmeans_clustering_v1 = importlib.import_module(
    "construction.02_k_means_clustering_v1"
)

angular_partition_v1 = importlib.import_module(
    "construction.04_angular_partition_assignment_v1"
)


def filter_non_empty_routes(routes):
    """Keep only routes that visit at least one customer."""
    return [
        route
        for route in routes
        if len([customer_id for customer_id in route if customer_id != 0]) > 0
    ]


def compute_euclidean_distance(coord_a, coord_b):
    x1, y1 = coord_a
    x2, y2 = coord_b

    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)


def compute_supplier_depot_replenishment(
    depot_customer_supplier_map,
    depot_customer_demand,
    supplier_cord,
    depot_cord,
    vehicle_capacity,
):
    """Estimate supplier -> depot -> supplier replenishment distance."""
    depot_customer_ids_by_supplier = {}

    for customer_id, supplier_id in depot_customer_supplier_map.items():
        depot_customer_ids_by_supplier.setdefault(supplier_id, set())
        depot_customer_ids_by_supplier[supplier_id].add(customer_id)

    replenishment_by_supplier = {}
    supplier_depot_distances = []
    total_replenishment_distance = 0

    for supplier_id, customer_ids in depot_customer_ids_by_supplier.items():
        depot_assigned_demand = sum(
            depot_customer_demand[customer_id]
            for customer_id in customer_ids
        )

        supplier_depot_trips = math.ceil(
            depot_assigned_demand / vehicle_capacity
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

        supplier_depot_distances.append(supplier_depot_roundtrip_distance)
        total_replenishment_distance += supplier_depot_roundtrip_distance

    return (
        total_replenishment_distance,
        supplier_depot_distances,
        replenishment_by_supplier,
    )


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

    direct_delivery_threshold = config["direct_delivery_threshold"]

    # Fixed depot timing parameters.
    # Times are represented as decimal hours, e.g. 9.0 = 09:00.
    fixed_depot_ready_time = config.get("fixed_depot_ready_time", 9.0)
    working_day_end_time = config.get("working_day_end_time", 18.0)

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
    # Placeholder values kept so existing metrics block
    # remains intact.
    # ======================================================

    total_first_echelon_distance = 0
    supplier_depot_distance = []
    supplier_depot_replenishment_metrics = {}

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

    all_supplier_direct_customers = set()
    all_depot_customers = set()
    global_depot_customer_cord = {}
    global_depot_customer_demand = {}
    depot_customer_supplier_map = {}

    # Fixed depot timing outputs. These are only for depot-origin routes.
    depot_timing_route_records = []
    depot_timing_pre_repair_route_records = []
    depot_timing_repair_records = []
    depot_timing_repair_summary = None
    supplier_depot_timing_metrics = {}
    depot_timing_route_counter = 1

    # ======================================================
    # System 2 routing:
    # supplier-direct routes stay local to supplier regions;
    # depot-side customers are collected for global depot routing.
    # ======================================================

    for supplier_id, subproblem in supplier_subproblems.items():
        supplier_origin = subproblem["origin"]
        supplier_customer_cord = subproblem["customer_cord"]
        supplier_demand = subproblem["demand"]

        # ==================================================
        # Hybrid split:
        # Large-demand customers -> supplier-direct delivery
        # Small-demand customers -> depot delivery
        # ==================================================

        supplier_direct_customer_cord = {}
        supplier_direct_demand = {}

        depot_customer_cord = {}
        depot_customer_demand = {}

        for customer_id, coord in supplier_customer_cord.items():
            customer_demand = supplier_demand[customer_id]

            if customer_demand >= direct_delivery_threshold:
                supplier_direct_customer_cord[customer_id] = coord
                supplier_direct_demand[customer_id] = customer_demand
                all_supplier_direct_customers.add(customer_id)

            else:
                depot_customer_cord[customer_id] = coord
                depot_customer_demand[customer_id] = customer_demand
                global_depot_customer_cord[customer_id] = coord
                global_depot_customer_demand[customer_id] = customer_demand
                depot_customer_supplier_map[customer_id] = supplier_id
                all_depot_customers.add(customer_id)

        print("\n===================================")
        print(f"Supplier Region {supplier_id}")
        print("Supplier-direct customers:")
        print(list(supplier_direct_customer_cord.keys()))
        print("Depot customers:")
        print(list(depot_customer_cord.keys()))
        print("===================================\n")

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

        supplier_routes = []
        supplier_two_opt_routes = []
        supplier_fixed_depot_timing_records = []
        supplier_fixed_depot_timing_summary = (
            depot_timing_utils.summarize_fixed_depot_timing([])
        )

        # ==================================================
        # Supplier-direct KMeans clustering
        # ==================================================

        clusters = []

        if len(supplier_direct_customer_cord) > 0:
            internal_k = min(3, len(supplier_direct_customer_cord))

            clusters = kmeans_clustering_v1.kmeans_clustering(
                supplier_direct_customer_cord,
                K=internal_k,
            )

        all_clusters.extend(clusters)

        # ==================================================
        # Supplier-side metric containers
        # ==================================================

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

        # ==================================================
        # Supplier-direct routing
        # ==================================================

        for cluster in clusters:
            cluster_customer_cord, cluster_demand = (
                kmeans_clustering_v1.get_cluster_data(
                    cluster,
                    supplier_direct_customer_cord,
                    supplier_direct_demand,
                )
            )

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
            route = filter_non_empty_routes(route)

            two_opt_route = baseline_nn_2opt_relocation_2opt_v1.run_2opt(
                route,
                current_routing_distance,
            )
            two_opt_route = filter_non_empty_routes(two_opt_route)

            two_opt_distance = 0
            two_opt_travel_time = 0

            for trip in two_opt_route:
                trip_distance = 0

                for c in range(len(trip) - 1):
                    trip_distance += current_routing_distance(
                        trip[c],
                        trip[c + 1],
                    )

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

        supplier_relocation_routes = (
            baseline_nn_2opt_relocation_2opt_v1.run_relocation(
                copy.deepcopy(supplier_two_opt_routes),
                supplier_demand,
                vehicle_capacity,
                current_routing_distance,
            )
        )
        supplier_relocation_routes = filter_non_empty_routes(
            supplier_relocation_routes
        )

        supplier_post_reloc_2opt_routes = (
            baseline_nn_2opt_relocation_2opt_v1.run_2opt(
                copy.deepcopy(supplier_relocation_routes),
                current_routing_distance,
            )
        )
        supplier_post_reloc_2opt_routes = filter_non_empty_routes(
            supplier_post_reloc_2opt_routes
        )

        for trip in supplier_routes:
            trip_distance = 0

            for c in range(len(trip) - 1):
                trip_distance += current_routing_distance(
                    trip[c],
                    trip[c + 1],
                )

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
            supplier_baseline_trip_utilization.append(
                trip_load / vehicle_capacity
            )

        for trip in supplier_two_opt_routes:
            trip_distance = 0

            for c in range(len(trip) - 1):
                trip_distance += current_routing_distance(
                    trip[c],
                    trip[c + 1],
                )

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
            supplier_two_opt_trip_utilization.append(
                trip_load / vehicle_capacity
            )

        for trip in supplier_relocation_routes:
            trip_distance = 0

            for c in range(len(trip) - 1):
                trip_distance += current_routing_distance(
                    trip[c],
                    trip[c + 1],
                )

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
            supplier_relocation_trip_utilization.append(
                trip_load / vehicle_capacity
            )

        for trip in supplier_post_reloc_2opt_routes:
            trip_distance = 0

            for c in range(len(trip) - 1):
                trip_distance += current_routing_distance(
                    trip[c],
                    trip[c + 1],
                )

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
            post_reloc_2opt_trip_utilization.append(
                trip_load / vehicle_capacity
            )

            supplier_post_reloc_2opt_trip_loads.append(trip_load)
            supplier_customers_per_trip_post_reloc_2opt.append(len(trip) - 2)
            supplier_post_reloc_2opt_trip_utilization.append(
                trip_load / vehicle_capacity
            )

        relocation_travel_time += supplier_relocation_travel_time
        post_reloc_2opt_travel_time += supplier_post_reloc_2opt_travel_time

        supplier_depot_timing_metrics[supplier_id] = (
            supplier_fixed_depot_timing_summary
        )

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
            "post_reloc_2opt_trip_distances": (
                supplier_post_reloc_2opt_trip_distances
            ),

            "baseline_trip_loads": supplier_baseline_trip_loads,
            "two_opt_trip_loads": supplier_two_opt_trip_loads,
            "relocation_trip_loads": supplier_relocation_trip_loads,
            "post_reloc_2opt_trip_loads": supplier_post_reloc_2opt_trip_loads,

            "customers_per_trip_baseline": supplier_customers_per_trip_baseline,
            "customers_per_trip_2opt": supplier_customers_per_trip_2opt,
            "customers_per_trip_relocation": (
                supplier_customers_per_trip_relocation
            ),
            "customers_per_trip_post_reloc_2opt": (
                supplier_customers_per_trip_post_reloc_2opt
            ),

            "baseline_trip_utilization": supplier_baseline_trip_utilization,
            "two_opt_trip_utilization": supplier_two_opt_trip_utilization,
            "relocation_trip_utilization": supplier_relocation_trip_utilization,
            "post_reloc_2opt_trip_utilization": (
                supplier_post_reloc_2opt_trip_utilization
            ),

            "depot_timing_fixed_summary": (
                supplier_fixed_depot_timing_summary
            ),
            "depot_timing_fixed_records": (
                supplier_fixed_depot_timing_records
            ),

            "route_baseline": supplier_routes,
            "route_2opt": supplier_two_opt_routes,
            "route_relocation": supplier_relocation_routes,
            "route_post_reloc_2opt": supplier_post_reloc_2opt_routes,
        }

        # ==================================================
        # Route records for plotting and tracking
        # ==================================================

        for trip in supplier_routes:
            baseline_route_records.append({
                "origin_type": "supplier",
                "supplier_id": supplier_id,
                "trip": trip,
            })

        for trip in supplier_two_opt_routes:
            two_opt_route_records.append({
                "origin_type": "supplier",
                "supplier_id": supplier_id,
                "trip": trip,
            })

        for trip in supplier_relocation_routes:
            relocation_route_records.append({
                "origin_type": "supplier",
                "supplier_id": supplier_id,
                "trip": trip,
            })

        for trip in supplier_post_reloc_2opt_routes:
            post_reloc_2opt_route_records.append({
                "origin_type": "supplier",
                "supplier_id": supplier_id,
                "trip": trip,
            })

        all_routes.extend(supplier_routes)

        all_two_opt_routes.extend(supplier_two_opt_routes)

        all_relocation_routes.extend(supplier_relocation_routes)

        all_post_reloc_2opt_routes.extend(supplier_post_reloc_2opt_routes)

    # ======================================================
    # Global depot-side routing:
    # all depot customers are pooled after supplier assignment.
    # ======================================================

    global_depot_routes = []
    global_depot_two_opt_routes = []
    global_depot_relocation_routes = []
    global_depot_post_reloc_2opt_routes = []
    global_depot_clusters = []

    global_depot_routing_distance = lambda i, j: dynamic_euc_distance(
        i,
        j,
        depot_cord,
        global_depot_customer_cord,
    )

    if len(global_depot_customer_cord) > 0:
        depot_k = min(3, len(global_depot_customer_cord))

        global_depot_clusters = kmeans_clustering_v1.kmeans_clustering(
            global_depot_customer_cord,
            K=depot_k,
        )
        all_clusters.extend(global_depot_clusters)

        for depot_cluster in global_depot_clusters:
            depot_cluster_customer_cord, depot_cluster_demand = (
                kmeans_clustering_v1.get_cluster_data(
                    depot_cluster,
                    global_depot_customer_cord,
                    global_depot_customer_demand,
                )
            )

            (
                depot_route,
                depot_total_distance,
                depot_number_of_trip,
                depot_total_travel_time,
                depot_capacity_feasibility,
                depot_structural_validity,
                depot_vehicle_capacity_used,
                depot_unserved_customers,
            ) = baseline_nn_2opt_relocation_2opt_v1.run_baseline_nn(
                depot_cord,
                depot_cluster_customer_cord,
                depot_cluster_demand,
                vehicle_capacity,
                average_speed,
                service_time,
            )

            depot_route = filter_non_empty_routes(depot_route)

            depot_two_opt_route = baseline_nn_2opt_relocation_2opt_v1.run_2opt(
                depot_route,
                global_depot_routing_distance,
            )
            depot_two_opt_route = filter_non_empty_routes(depot_two_opt_route)

            depot_two_opt_distance = 0
            depot_two_opt_travel_time = 0

            for trip in depot_two_opt_route:
                trip_distance = 0

                for c in range(len(trip) - 1):
                    trip_distance += global_depot_routing_distance(
                        trip[c],
                        trip[c + 1],
                    )

                trip_time = trip_distance / average_speed

                for customer in trip[1:-1]:
                    trip_time += service_time[customer] / 60

                depot_two_opt_distance += trip_distance
                depot_two_opt_travel_time += trip_time

            baseline_cluster_distances.append(depot_total_distance)
            baseline_cluster_travel_times.append(depot_total_travel_time)
            baseline_cluster_trip_counts.append(depot_number_of_trip)

            baseline_cluster_capacity_flags.append(depot_capacity_feasibility)
            baseline_cluster_structural_flags.append(depot_structural_validity)
            baseline_cluster_unserved.extend(depot_unserved_customers)

            cluster_two_opt_distances.append(depot_two_opt_distance)
            cluster_two_opt_travel_times.append(depot_two_opt_travel_time)

            for trip in depot_route:
                trip_distance = 0

                for c in range(len(trip) - 1):
                    trip_distance += global_depot_routing_distance(
                        trip[c],
                        trip[c + 1],
                    )

                baseline_trip_distances.append(trip_distance)

                trip_load = 0

                for customer in trip[1:-1]:
                    trip_load += global_depot_customer_demand[customer]

                baseline_trip_loads.append(trip_load)
                customers_per_trip_baseline.append(len(trip) - 2)
                baseline_trip_utilization.append(trip_load / vehicle_capacity)

            for trip in depot_two_opt_route:
                trip_distance = 0

                for c in range(len(trip) - 1):
                    trip_distance += global_depot_routing_distance(
                        trip[c],
                        trip[c + 1],
                    )

                two_opt_trip_distances.append(trip_distance)

                trip_load = 0

                for customer in trip[1:-1]:
                    trip_load += global_depot_customer_demand[customer]

                two_opt_trip_loads.append(trip_load)
                customers_per_trip_2opt.append(len(trip) - 2)
                two_opt_trip_utilization.append(trip_load / vehicle_capacity)

            global_depot_routes.extend(depot_route)
            global_depot_two_opt_routes.extend(depot_two_opt_route)

        global_depot_two_opt_routes = filter_non_empty_routes(
            global_depot_two_opt_routes
        )

        global_depot_relocation_routes = (
            baseline_nn_2opt_relocation_2opt_v1.run_relocation(
                copy.deepcopy(global_depot_two_opt_routes),
                global_depot_customer_demand,
                vehicle_capacity,
                global_depot_routing_distance,
            )
        )
        global_depot_relocation_routes = filter_non_empty_routes(
            global_depot_relocation_routes
        )

        global_depot_post_reloc_2opt_routes = (
            baseline_nn_2opt_relocation_2opt_v1.run_2opt(
                copy.deepcopy(global_depot_relocation_routes),
                global_depot_routing_distance,
            )
        )
        global_depot_post_reloc_2opt_routes = filter_non_empty_routes(
            global_depot_post_reloc_2opt_routes
        )

        # ==================================================
        # Fixed timing repair:
        # First evaluate the final depot routes under fixed depot timing.
        # If any depot route is infeasible, try a close-to-half split,
        # apply 2-opt to each split route, and accept the split only if
        # the resulting routes are timing-feasible.
        # ==================================================

        depot_timing_repair_result = (
            depot_timing_utils.repair_infeasible_fixed_depot_routes_by_half_split(
                routes=global_depot_post_reloc_2opt_routes,
                demand=global_depot_customer_demand,
                vehicle_capacity=vehicle_capacity,
                euc_distance=global_depot_routing_distance,
                average_speed=average_speed,
                service_time=service_time,
                fixed_depot_ready_time=fixed_depot_ready_time,
                working_day_end_time=working_day_end_time,
                supplier_region_id="global_depot_pool",
            )
        )

        global_depot_post_reloc_2opt_routes_before_timing_repair = (
            depot_timing_repair_result["routes_before_repair"]
        )
        global_depot_post_reloc_2opt_routes = (
            depot_timing_repair_result["routes_after_repair"]
        )
        depot_timing_pre_repair_route_records = (
            depot_timing_repair_result["pre_repair_records"]
        )
        global_depot_timing_records = (
            depot_timing_repair_result["post_repair_records"]
        )
        depot_timing_repair_records = (
            depot_timing_repair_result["repair_records"]
        )
        depot_timing_repair_summary = (
            depot_timing_repair_result["repair_summary"]
        )

        for trip in global_depot_relocation_routes:
            trip_distance = 0

            for c in range(len(trip) - 1):
                trip_distance += global_depot_routing_distance(
                    trip[c],
                    trip[c + 1],
                )

            trip_time = trip_distance / average_speed

            for customer in trip[1:-1]:
                trip_time += service_time[customer] / 60

            relocation_travel_time += trip_time
            relocation_trip_distances.append(trip_distance)

            trip_load = 0

            for customer in trip[1:-1]:
                trip_load += global_depot_customer_demand[customer]

            relocation_trip_loads.append(trip_load)
            customers_per_trip_relocation.append(len(trip) - 2)
            relocation_trip_utilization.append(trip_load / vehicle_capacity)

        for trip in global_depot_post_reloc_2opt_routes:
            trip_distance = 0

            for c in range(len(trip) - 1):
                trip_distance += global_depot_routing_distance(
                    trip[c],
                    trip[c + 1],
                )

            trip_time = trip_distance / average_speed

            for customer in trip[1:-1]:
                trip_time += service_time[customer] / 60

            post_reloc_2opt_travel_time += trip_time
            post_reloc_2opt_trip_distances.append(trip_distance)

            trip_load = 0

            for customer in trip[1:-1]:
                trip_load += global_depot_customer_demand[customer]

            post_reloc_2opt_trip_loads.append(trip_load)
            customers_per_trip_post_reloc_2opt.append(len(trip) - 2)
            post_reloc_2opt_trip_utilization.append(
                trip_load / vehicle_capacity
            )

        # The repair helper evaluates routes starting from route_id=1.
        # Re-number here using the experiment-level route counter so the
        # saved route records remain consistent if more depot pools are added.
        for index, record in enumerate(global_depot_timing_records):
            record["route_id"] = depot_timing_route_counter + index

        for index, record in enumerate(depot_timing_pre_repair_route_records):
            record["route_id"] = depot_timing_route_counter + index

        depot_timing_route_counter += len(global_depot_timing_records)
        depot_timing_route_records.extend(global_depot_timing_records)
        supplier_depot_timing_metrics["global_depot_pool"] = (
            depot_timing_utils.summarize_fixed_depot_timing(
                global_depot_timing_records
            )
        )

        for trip in global_depot_routes:
            baseline_route_records.append({
                "origin_type": "depot",
                "routing_scope": "global_depot_pool",
                "trip": trip,
                "customer_supplier_map": {
                    customer: depot_customer_supplier_map[customer]
                    for customer in trip
                    if customer != 0
                },
            })

        for trip in global_depot_two_opt_routes:
            two_opt_route_records.append({
                "origin_type": "depot",
                "routing_scope": "global_depot_pool",
                "trip": trip,
                "customer_supplier_map": {
                    customer: depot_customer_supplier_map[customer]
                    for customer in trip
                    if customer != 0
                },
            })

        for trip in global_depot_relocation_routes:
            relocation_route_records.append({
                "origin_type": "depot",
                "routing_scope": "global_depot_pool",
                "trip": trip,
                "customer_supplier_map": {
                    customer: depot_customer_supplier_map[customer]
                    for customer in trip
                    if customer != 0
                },
            })

        for trip in global_depot_post_reloc_2opt_routes:
            post_reloc_2opt_route_records.append({
                "origin_type": "depot",
                "routing_scope": "global_depot_pool",
                "trip": trip,
                "customer_supplier_map": {
                    customer: depot_customer_supplier_map[customer]
                    for customer in trip
                    if customer != 0
                },
            })

        all_routes.extend(global_depot_routes)
        all_two_opt_routes.extend(global_depot_two_opt_routes)
        all_relocation_routes.extend(global_depot_relocation_routes)
        all_post_reloc_2opt_routes.extend(global_depot_post_reloc_2opt_routes)

    (
        total_first_echelon_distance,
        supplier_depot_distance,
        supplier_depot_replenishment_metrics,
    ) = compute_supplier_depot_replenishment(
        depot_customer_supplier_map=depot_customer_supplier_map,
        depot_customer_demand=global_depot_customer_demand,
        supplier_cord=supplier_cord,
        depot_cord=depot_cord,
        vehicle_capacity=vehicle_capacity,
    )

    # ======================================================
    # Hybrid customer coverage validation
    # ======================================================

    all_hybrid_customers = (
        all_supplier_direct_customers | all_depot_customers
    )

    missing_customers = set(customer_cord.keys()) - all_hybrid_customers

    duplicate_customers = (
        all_supplier_direct_customers & all_depot_customers
    )

    print("\n========== HYBRID VALIDATION ==========")
    print("Supplier-direct customers:", len(all_supplier_direct_customers))
    print("Depot customers:", len(all_depot_customers))
    print("Total assigned customers:", len(all_hybrid_customers))
    print("Missing customers:", missing_customers)
    print("Duplicate customers:", duplicate_customers)

    # ======================================================
    # Save results
    # ======================================================

    results_path = create_experiment_folder(
        "hybrid_supplier_customer_kmeans_timing_fixed_split_v1",
        INSTANCE_NAME,
    )

    with open(f"{results_path}/config_used.json", "w") as f:
        json.dump(config, f, indent=4)

    with open(f"{results_path}/clusters.json", "w") as f:
        json.dump(
            {
                "clustering": "kmeans",
                "clusters": all_clusters,
                "cluster_loads": [
                    sum(demand[customer] for customer in cluster)
                    for cluster in all_clusters
                ],
                "supplier_clusters": {
                    supplier_id: supplier_record["clusters"]
                    for supplier_id, supplier_record in supplier_metrics.items()
                },
                "depot_clusters": global_depot_clusters,
                "supplier_direct_customer_ids": sorted(
                    list(all_supplier_direct_customers)
                ),
                "depot_customer_ids": sorted(list(all_depot_customers)),
                "depot_customer_supplier_map": depot_customer_supplier_map,
            },
            f,
            indent=4,
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

    baseline_avg_utilization = (
        sum(baseline_trip_utilization) / len(baseline_trip_utilization)
    )
    baseline_max_utilization = max(baseline_trip_utilization)
    baseline_min_utilization = min(baseline_trip_utilization)

    two_opt_avg_utilization = (
        sum(two_opt_trip_utilization) / len(two_opt_trip_utilization)
    )
    two_opt_max_utilization = max(two_opt_trip_utilization)
    two_opt_min_utilization = min(two_opt_trip_utilization)

    relocation_avg_utilization = (
        sum(relocation_trip_utilization) / len(relocation_trip_utilization)
    )
    relocation_max_utilization = max(relocation_trip_utilization)
    relocation_min_utilization = min(relocation_trip_utilization)

    post_reloc_2opt_avg_utilization = (
        sum(post_reloc_2opt_trip_utilization)
        / len(post_reloc_2opt_trip_utilization)
    )
    post_reloc_2opt_max_utilization = max(post_reloc_2opt_trip_utilization)
    post_reloc_2opt_min_utilization = min(post_reloc_2opt_trip_utilization)

    depot_timing_summary = depot_timing_utils.summarize_fixed_depot_timing(
        depot_timing_route_records
    )
    depot_timing_pre_repair_summary = (
        depot_timing_utils.summarize_fixed_depot_timing(
            depot_timing_pre_repair_route_records
        )
    )

    if depot_timing_repair_summary is None:
        depot_timing_repair_summary = (
            depot_timing_utils.summarize_fixed_depot_repair(
                depot_timing_pre_repair_route_records,
                depot_timing_route_records,
                depot_timing_repair_records,
            )
        )

    metrics = {
        "algorithm": "hybrid_supplier_customer_kmeans_timing_fixed_split_v1",
        "instance": INSTANCE_NAME,
        "seed": config["seed"],

        "direct_delivery_threshold": direct_delivery_threshold,

        "timing_model": "fixed_depot_ready_time_with_half_split_repair",
        "base_timing_model": "fixed_depot_ready_time",
        "timing_repair_model": "close_to_half_split_with_2opt",
        "fixed_depot_ready_time": fixed_depot_ready_time,
        "fixed_depot_ready_time_label": (
            depot_timing_utils.format_hour(fixed_depot_ready_time)
        ),
        "working_day_end_time": working_day_end_time,
        "working_day_end_time_label": (
            depot_timing_utils.format_hour(working_day_end_time)
        ),

        "n_supplier_direct_customers": len(all_supplier_direct_customers),
        "n_depot_customers": len(all_depot_customers),

        "supplier_direct_customer_ids": sorted(
            list(all_supplier_direct_customers)
        ),
        "depot_customer_ids": sorted(list(all_depot_customers)),

        "construction": (
            "angular_partition supplier-direct assignment + global depot "
            "kmeans_clustering + nearest_neighbor + 2-opt"
        ),
        "local_search": (
            "2-opt + supplier-level 1-0 relocation + 2-opt"
        ),
        "supplier_direct_routing_scope": "supplier_region",
        "depot_routing_scope": "global_depot_pool",
        "relocation_scope": (
            "supplier_direct_routes within supplier region; depot routes global"
        ),
        "fixed_timing_repair_scope": (
            "depot routes only after post-relocation 2-opt"
        ),

        "total_first_echelon_distance": total_first_echelon_distance,

        "baseline_distance": total_distance,
        "baseline_total_system_distance": (
            total_first_echelon_distance + total_distance
        ),

        "two_opt_distance": two_opt_distance,
        "two_opt_total_system_distance": (
            total_first_echelon_distance + two_opt_distance
        ),

        "relocation_distance": relocation_distance,
        "relocation_total_system_distance": (
            total_first_echelon_distance + relocation_distance
        ),

        "post_reloc_2opt_distance": post_reloc_2opt_distance,
        "post_reloc_2opt_total_system_distance": (
            total_first_echelon_distance + post_reloc_2opt_distance
        ),

        "two_opt_gain_over_baseline": total_distance - two_opt_distance,
        "two_opt_percent_gain_over_baseline": (
            ((total_distance - two_opt_distance) / total_distance) * 100
        ),

        "relocation_gain_over_2opt": two_opt_distance - relocation_distance,
        "relocation_percent_gain_over_2opt": (
            ((two_opt_distance - relocation_distance) / two_opt_distance) * 100
        ),

        "relocation_gain_over_baseline": total_distance - relocation_distance,
        "relocation_percent_gain_over_baseline": (
            ((total_distance - relocation_distance) / total_distance) * 100
        ),

        "post_reloc_2opt_gain_over_relocation": (
            relocation_distance - post_reloc_2opt_distance
        ),
        "post_reloc_2opt_percent_gain_over_relocation": (
            (
                (relocation_distance - post_reloc_2opt_distance)
                / relocation_distance
            )
            * 100
        ),

        "total_demand": total_demand,
        "total_supply": total_supply,
        "supply_feasibility": supply_feasibility,

        "n_suppliers": n_suppliers,
        "n_supplier_vrps": len(supplier_metrics),

        "supplier_depot_distance": supplier_depot_distance,
        "supplier_depot_replenishment_distance": (
            total_first_echelon_distance
        ),
        "supplier_depot_replenishment_metrics": (
            supplier_depot_replenishment_metrics
        ),
        "supplier_cord": supplier_cord,
        "supplier_supply": supplier_supply,
        "supplier_metrics": supplier_metrics,
        "depot_customer_supplier_map": depot_customer_supplier_map,
        "depot_clusters": global_depot_clusters,

        "depot_timing_route_records": depot_timing_route_records,
        "depot_timing_pre_repair_route_records": (
            depot_timing_pre_repair_route_records
        ),
        "depot_timing_repair_records": depot_timing_repair_records,
        "depot_timing_repair_summary": depot_timing_repair_summary,
        "supplier_depot_timing_metrics": supplier_depot_timing_metrics,
        "depot_timing_pre_repair_summary": (
            depot_timing_pre_repair_summary
        ),
        "depot_timing_summary": depot_timing_summary,
        "depot_timing_feasibility": (
            depot_timing_summary["depot_timing_feasibility"]
        ),
        "n_depot_timing_routes": (
            depot_timing_summary["n_depot_timing_routes"]
        ),
        "n_depot_timing_feasible_routes": (
            depot_timing_summary["n_depot_timing_feasible_routes"]
        ),
        "n_depot_timing_infeasible_routes": (
            depot_timing_summary["n_depot_timing_infeasible_routes"]
        ),
        "n_depot_timing_routes_before_repair": (
            depot_timing_pre_repair_summary["n_depot_timing_routes"]
        ),
        "n_depot_timing_infeasible_routes_before_repair": (
            depot_timing_pre_repair_summary[
                "n_depot_timing_infeasible_routes"
            ]
        ),
        "n_fixed_timing_repair_attempts": (
            depot_timing_repair_summary["n_repair_attempts"]
        ),
        "n_fixed_timing_successful_repairs": (
            depot_timing_repair_summary["n_successful_repairs"]
        ),
        "n_fixed_timing_unresolved_repairs": (
            depot_timing_repair_summary["n_unresolved_repairs"]
        ),
        "distance_delta_after_fixed_timing_repair": (
            depot_timing_repair_summary["distance_delta_after_repair"]
        ),
        "infeasible_timing_route_ids": (
            depot_timing_summary["infeasible_timing_route_ids"]
        ),
        "infeasible_timing_customers": (
            depot_timing_summary["infeasible_timing_customers"]
        ),
        "latest_depot_route_finish_time": (
            depot_timing_summary["latest_depot_route_finish_time"]
        ),
        "latest_depot_route_finish_time_label": (
            depot_timing_summary["latest_depot_route_finish_time_label"]
        ),
        "max_depot_route_duration_hours": (
            depot_timing_summary["max_depot_route_duration_hours"]
        ),
        "avg_depot_route_duration_hours": (
            depot_timing_summary["avg_depot_route_duration_hours"]
        ),

        "baseline_travel_time": total_travel_time,
        "two_opt_travel_time": two_opt_travel_time,
        "relocation_travel_time": relocation_travel_time,
        "post_reloc_2opt_travel_time": post_reloc_2opt_travel_time,

        "trips": number_of_trip,

        "capacity_feasibility": capacity_feasibility,
        "structural_validity": structural_validity,
        "all_customers_served": all_customers_served,
        "overall_feasible_with_fixed_timing": (
            capacity_feasibility
            and structural_validity
            and all_customers_served
            and depot_timing_summary["depot_timing_feasibility"]
        ),

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
        "customers_per_trip_post_reloc_2opt": (
            customers_per_trip_post_reloc_2opt
        ),

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

    with open(f"{results_path}/metrics.json", "w") as f:
        json.dump(metrics, f, indent=4)

    with open(f"{results_path}/depot_timing_fixed_records.json", "w") as f:
        json.dump(depot_timing_route_records, f, indent=4)

    with open(
        f"{results_path}/depot_timing_fixed_pre_repair_records.json",
        "w",
    ) as f:
        json.dump(depot_timing_pre_repair_route_records, f, indent=4)

    with open(f"{results_path}/depot_timing_fixed_repair_records.json", "w") as f:
        json.dump(depot_timing_repair_records, f, indent=4)

    with open(f"{results_path}/depot_timing_fixed_summary.json", "w") as f:
        json.dump(depot_timing_summary, f, indent=4)

    with open(
        f"{results_path}/depot_timing_fixed_repair_summary.json",
        "w",
    ) as f:
        json.dump(depot_timing_repair_summary, f, indent=4)

    summary_metrics = {
        "algorithm": metrics["algorithm"],
        "instance": metrics["instance"],
        "seed": metrics["seed"],

        "n_customers": metrics["n_customers"],
        "vehicle_capacity": metrics["vehicle_capacity"],
        "direct_delivery_threshold": metrics["direct_delivery_threshold"],
        "supplier_direct_routing_scope": (
            metrics["supplier_direct_routing_scope"]
        ),
        "depot_routing_scope": metrics["depot_routing_scope"],

        "timing_model": metrics["timing_model"],
        "base_timing_model": metrics["base_timing_model"],
        "timing_repair_model": metrics["timing_repair_model"],
        "fixed_depot_ready_time": metrics["fixed_depot_ready_time"],
        "fixed_depot_ready_time_label": (
            metrics["fixed_depot_ready_time_label"]
        ),
        "working_day_end_time": metrics["working_day_end_time"],
        "working_day_end_time_label": (
            metrics["working_day_end_time_label"]
        ),

        "baseline_distance": metrics["baseline_distance"],
        "baseline_total_system_distance": (
            metrics["baseline_total_system_distance"]
        ),
        "final_distance": metrics["post_reloc_2opt_distance"],
        "final_total_system_distance": (
            metrics["post_reloc_2opt_total_system_distance"]
        ),
        "supplier_depot_replenishment_distance": (
            metrics["supplier_depot_replenishment_distance"]
        ),

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
        "overall_feasible_with_fixed_timing": (
            metrics["overall_feasible_with_fixed_timing"]
        ),

        "depot_timing_feasibility": metrics["depot_timing_feasibility"],
        "n_depot_timing_routes": metrics["n_depot_timing_routes"],
        "n_depot_timing_feasible_routes": (
            metrics["n_depot_timing_feasible_routes"]
        ),
        "n_depot_timing_infeasible_routes": (
            metrics["n_depot_timing_infeasible_routes"]
        ),
        "n_depot_timing_infeasible_routes_before_repair": (
            metrics["n_depot_timing_infeasible_routes_before_repair"]
        ),
        "n_fixed_timing_repair_attempts": (
            metrics["n_fixed_timing_repair_attempts"]
        ),
        "n_fixed_timing_successful_repairs": (
            metrics["n_fixed_timing_successful_repairs"]
        ),
        "n_fixed_timing_unresolved_repairs": (
            metrics["n_fixed_timing_unresolved_repairs"]
        ),
        "distance_delta_after_fixed_timing_repair": (
            metrics["distance_delta_after_fixed_timing_repair"]
        ),
        "latest_depot_route_finish_time_label": (
            metrics["latest_depot_route_finish_time_label"]
        ),

        "n_supplier_direct_customers": (
            metrics["n_supplier_direct_customers"]
        ),

        "n_depot_customers": metrics["n_depot_customers"],
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
        depot_cord=depot_cord,
    )

    plot_supplier_routes(
        two_opt_route_records,
        supplier_cord,
        customer_cord,
        results_path,
        filename="route_plot_two_opt.png",
        title="Supplier-Level Routes - Angular Partition + KMeans + Baseline NN + 2-Opt",
        depot_cord=depot_cord,
    )

    plot_supplier_routes(
        relocation_route_records,
        supplier_cord,
        customer_cord,
        results_path,
        filename="route_plot_relocation.png",
        title=(
            "Supplier-Level Routes - Angular Partition + KMeans + "
            "2-Opt + Supplier-Level Relocation"
        ),
        depot_cord=depot_cord,
    )

    plot_supplier_routes(
        post_reloc_2opt_route_records,
        supplier_cord,
        customer_cord,
        results_path,
        filename="route_plot_post_reloc_2opt.png",
        title=(
            "Supplier-Level Routes - Angular Partition + KMeans + "
            "2-Opt + Supplier-Level Relocation + 2-Opt"
        ),
        depot_cord=depot_cord,
    )

    plot_supplier_routes(
        post_reloc_2opt_route_records,
        supplier_cord,
        customer_cord,
        results_path,
        filename="route_plot_timing_split_repair.png",
        title=(
            "Supplier-Level Routes - Angular Partition + KMeans + "
            "Fixed Depot Timing Split Repair"
        ),
        depot_cord=depot_cord,
    )

    print("Results stored in:", results_path)


if __name__ == "__main__":
    config = {
        "n_customers": 60,
        "vehicle_capacity": 25,
        "n_suppliers": 3,
        "seed": 42,
        "direct_delivery_threshold": 5,
        "fixed_depot_ready_time": 9.0,
        "working_day_end_time": 18.0,
    }

    run_experiment(config)
