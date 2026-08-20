if __name__ == "__main__":
    from utils.experiment_logger import create_experiment_folder
    from utils.plot_routes import plot_routes
    import json

    results_path = create_experiment_folder("baseline_nn_2opt_1_0_relocate", INSTANCE_NAME)

    (
        route,
        total_distance,
        number_of_trip,
        new_route,
        total_distance_route,
        total_travel_time,
        total_travel_time_after_2opt,
        capacity_feasibility,
        structural_validity,
        vehicle_capacity,
        unserved_customers,
    ) = run_baseline_nn()

    baseline_route = route
    two_opt_route = [trip.copy() for trip in new_route]

    # 🔁 Apply 1-0 relocation improvement
    relocation_route = run_relocation(two_opt_route)

    # 🔁 recompute FINAL distance after relocation
    relocation_total_distance = total_solution_distance(relocation_route)

    relocation_travel_time = 0
    for trip in relocation_route:
        trip_distance = 0
        for c in range(len(trip)-1):
            trip_distance += euc_distance(trip[c], trip[c+1])

        trip_time = trip_distance / average_speed
        for customer in trip[1:-1]:
            trip_time += service_time[customer] / 60

        relocation_travel_time += trip_time

    # compute trip distances for all three stages
    baseline_trip_distances = []
    for trip in baseline_route:
        trip_distance = 0
        for c in range(len(trip)-1):
            trip_distance += euc_distance(trip[c], trip[c+1])
        baseline_trip_distances.append(trip_distance)

    two_opt_trip_distances = []
    for trip in two_opt_route:
        trip_distance = 0
        for c in range(len(trip)-1):
            trip_distance += euc_distance(trip[c], trip[c+1])
        two_opt_trip_distances.append(trip_distance)

    relocation_trip_distances = []
    for trip in relocation_route:
        trip_distance = 0
        for c in range(len(trip)-1):
            trip_distance += euc_distance(trip[c], trip[c+1])
        relocation_trip_distances.append(trip_distance)

    # demand load for all three stages
    baseline_trip_loads = []
    for trip in baseline_route:
        trip_load = 0
        for customer in trip[1:-1]:
            trip_load += demand[customer]
        baseline_trip_loads.append(trip_load)

    two_opt_trip_loads = []
    for trip in two_opt_route:
        trip_load = 0
        for customer in trip[1:-1]:
            trip_load += demand[customer]
        two_opt_trip_loads.append(trip_load)

    relocation_trip_loads = []
    for trip in relocation_route:
        trip_load = 0
        for customer in trip[1:-1]:
            trip_load += demand[customer]
        relocation_trip_loads.append(trip_load)

    # customers per trip for all three stages
    customers_per_trip_baseline = []
    for trip in baseline_route:
        customers_per_trip_baseline.append(len(trip)-2) #subtracting 2 to exclude the depot at the start and end of the trip

    customers_per_trip_2opt = []
    for trip in two_opt_route:
        customers_per_trip_2opt.append(len(trip)-2) #subtracting 2 to exclude the depot at the start and end of the trip

    customers_per_trip_relocation = []
    for trip in relocation_route:
        customers_per_trip_relocation.append(len(trip)-2) #subtracting 2 to exclude the depot at the start and end of the trip

    # trip utilization rate for all three stages
    baseline_trip_utilization = []
    for trip in baseline_route:
        trip_load = 0
        for customer in trip[1:-1]:
            trip_load += demand[customer]
        utilization = trip_load / vehicle_capacity
        baseline_trip_utilization.append(utilization)

    two_opt_trip_utilization = []
    for trip in two_opt_route:
        trip_load = 0
        for customer in trip[1:-1]:
            trip_load += demand[customer]
        utilization = trip_load / vehicle_capacity
        two_opt_trip_utilization.append(utilization)

    relocation_trip_utilization = []
    for trip in relocation_route:
        trip_load = 0
        for customer in trip[1:-1]:
            trip_load += demand[customer]
        utilization = trip_load / vehicle_capacity
        relocation_trip_utilization.append(utilization)

    # average trip utilization for all three stages
    baseline_avg_utilization = sum(baseline_trip_utilization) / len(baseline_trip_utilization)
    two_opt_avg_utilization = sum(two_opt_trip_utilization) / len(two_opt_trip_utilization)
    relocation_avg_utilization = sum(relocation_trip_utilization) / len(relocation_trip_utilization)

    # max trip utilization for all three stages
    baseline_max_utilization = max(baseline_trip_utilization)
    two_opt_max_utilization = max(two_opt_trip_utilization)
    relocation_max_utilization = max(relocation_trip_utilization)

    # min trip utilization for all three stages
    baseline_min_utilization = min(baseline_trip_utilization)
    two_opt_min_utilization = min(two_opt_trip_utilization)
    relocation_min_utilization = min(relocation_trip_utilization)


    metrics = {
        "algorithm": "baseline_nn_2opt",
        "instance": INSTANCE_NAME,
        "seed": 42,
        "construction": "nearest_neighbor",
        "local_search": "2-opt" + " + " + "relocation",
        "baseline_distance": total_distance,
        "two_opt_distance": total_distance_route,
        "relocation_distance": relocation_total_distance,
        "relocation_gain_over_2opt": total_distance_route - relocation_total_distance,
        "relocation_percent_gain_over_2opt": ((total_distance_route - relocation_total_distance) / total_distance_route) * 100,
        "baseline_travel_time": total_travel_time,
        "two_opt_travel_time": total_travel_time_after_2opt,
        "relocation_travel_time": relocation_travel_time,
        "trips": number_of_trip,
        "absolute_improvement": total_distance - relocation_total_distance,
        "percent_improvement": ((total_distance - relocation_total_distance) / total_distance) * 100,
        "capacity_feasibility": capacity_feasibility,
        "structural_validity": structural_validity,
        "all_customers_served": unserved_customers == [],
        "vehicle_capacity": vehicle_capacity,
        "unserved_customers": unserved_customers,
        "n_customers": len(customer_cord),
        "depot": depot_cord,
        "baseline_trip_distances": baseline_trip_distances,
        "two_opt_trip_distances": two_opt_trip_distances,
        "relocation_trip_distances": relocation_trip_distances,
        "baseline_trip_loads": baseline_trip_loads,
        "two_opt_trip_loads": two_opt_trip_loads,
        "relocation_trip_loads": relocation_trip_loads,
        "customers_per_trip_baseline": customers_per_trip_baseline,
        "customers_per_trip_2opt": customers_per_trip_2opt,
        "customers_per_trip_relocation": customers_per_trip_relocation,
        "baseline_trip_utilization": baseline_trip_utilization,
        "two_opt_trip_utilization": two_opt_trip_utilization,
        "relocation_trip_utilization": relocation_trip_utilization,
        "baseline_avg_utilization": baseline_avg_utilization,
        "two_opt_avg_utilization": two_opt_avg_utilization,
        "relocation_avg_utilization": relocation_avg_utilization,
        "baseline_max_utilization": baseline_max_utilization,
        "two_opt_max_utilization": two_opt_max_utilization,
        "relocation_max_utilization": relocation_max_utilization,
        "baseline_min_utilization": baseline_min_utilization,
        "two_opt_min_utilization": two_opt_min_utilization,
        "relocation_min_utilization": relocation_min_utilization,
    }

    with open(f"{results_path}/metrics.json", "w") as f:
        json.dump(metrics, f, indent=4)

    with open(f"{results_path}/route_baseline.txt", "w") as f:
        f.write(str(baseline_route))

    with open(f"{results_path}/route_2opt.txt", "w") as f:
        f.write(str(two_opt_route))

    with open(f"{results_path}/route_relocation.txt", "w") as f:
        f.write(str(relocation_route))

    plot_routes(
        baseline_route,
        depot_cord,
        customer_cord,
        results_path,
        filename="route_plot_baseline_nn.png",
        title="Vehicle Routes - Baseline NN",
    )
    plot_routes(
        two_opt_route,
        depot_cord,
        customer_cord,
        results_path,
        filename="route_plot_2opt.png",
        title="Vehicle Routes - 2-Opt",
    )
    plot_routes(
        relocation_route,
        depot_cord,
        customer_cord,
        results_path,
        filename="route_plot_relocation.png",
        title="Vehicle Routes - Relocation",
    )

    print("Results stored in:", results_path)
