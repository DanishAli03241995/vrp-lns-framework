"""Generate simple single-depot CVRP instance data."""

import random


def get_grid_size(n_customers):
    """Scale the coordinate region with the customer count."""
    if n_customers == 20:
        return 10
    if n_customers == 40:
        return 20
    if n_customers == 60:
        return 30
    if n_customers == 80:
        return 40
    return max(10, n_customers // 2)


def generate_depot_customer_instance(config):
    """Generate one depot-customer instance for initial heuristic experiments."""
    n_customers = config["n_customers"]
    seed = config["seed"]
    vehicle_capacity = config["vehicle_capacity"]

    grid_size = config.get("grid_size", get_grid_size(n_customers))
    depot_cord = config.get("depot_cord", (0, 0))
    average_speed = config.get("average_speed", 30)
    service_time_minutes = config.get("service_time", 10)
    min_demand = config.get("min_demand", 1)
    max_demand = config.get("max_demand", 6)

    random.seed(seed)

    customer_cord = {}
    demand = {}
    service_time = {}

    for customer_id in range(1, n_customers + 1):
        x_coord = random.uniform(0, grid_size)
        y_coord = random.uniform(0, grid_size)

        customer_cord[customer_id] = (x_coord, y_coord)
        demand[customer_id] = random.randint(min_demand, max_demand)
        service_time[customer_id] = service_time_minutes

    demand[0] = 0

    def euc_distance(i, j):
        if i == 0:
            coord_i = depot_cord
        else:
            coord_i = customer_cord[i]

        if j == 0:
            coord_j = depot_cord
        else:
            coord_j = customer_cord[j]

        x_i, y_i = coord_i
        x_j, y_j = coord_j

        return ((x_i - x_j) ** 2 + (y_i - y_j) ** 2) ** 0.5

    return {
        "depot_cord": depot_cord,
        "customer_cord": customer_cord,
        "demand": demand,
        "service_time": service_time,
        "average_speed": average_speed,
        "vehicle_capacity": vehicle_capacity,
        "n_customers": n_customers,
        "grid_size": grid_size,
        "seed": seed,
        "euc_distance": euc_distance,
    }
