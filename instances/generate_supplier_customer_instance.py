"""Generate reusable supplier-depot-customer instance data."""

import math
import random


def split_total_demand_across_suppliers(total_demand, n_suppliers, shares=None):
    """Create supplier supply values whose total exactly matches demand."""
    if n_suppliers <= 0:
        raise ValueError("n_suppliers must be greater than zero.")

    if shares is None:
        base_share = 1 / n_suppliers
        shares = {supplier_id: base_share for supplier_id in range(1, n_suppliers + 1)}

    supplier_supply = {}
    remaining_supply = total_demand

    for supplier_id in range(1, n_suppliers):
        share = shares.get(supplier_id, 0)
        supply = int(total_demand * share)
        supplier_supply[supplier_id] = supply
        remaining_supply -= supply

    supplier_supply[n_suppliers] = remaining_supply

    return supplier_supply


def generate_supplier_customer_instance(config):
    """Generate one full instance used by supplier, depot, and hybrid cases."""
    n_customers = config["n_customers"]
    n_suppliers = config["n_suppliers"]
    seed = config["seed"]
    vehicle_capacity = config["vehicle_capacity"]

    grid_size = config.get("grid_size", 30)
    average_speed = config.get("average_speed", 30)
    service_time_minutes = config.get("service_time", 10)
    min_demand = config.get("min_demand", 1)
    max_demand = config.get("max_demand", 6)
    supplier_radius_factor = config.get("supplier_radius_factor", 0.4)
    supplier_supply_share = config.get("supplier_supply_share")

    random.seed(seed)

    depot_cord = (
        grid_size / 2,
        grid_size / 2,
    )

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

    total_demand = sum(demand.values())
    supplier_supply = split_total_demand_across_suppliers(
        total_demand,
        n_suppliers,
        supplier_supply_share,
    )

    supplier_cord = {}
    center_x, center_y = depot_cord
    supplier_radius = grid_size * supplier_radius_factor

    for supplier_id in range(1, n_suppliers + 1):
        angle = 2 * math.pi * (supplier_id - 1) / n_suppliers
        x_coord = center_x + supplier_radius * math.cos(angle)
        y_coord = center_y + supplier_radius * math.sin(angle)
        supplier_cord[supplier_id] = (x_coord, y_coord)

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

    def supplier_euc_distance(i, j):
        if i == 0:
            coord_i = depot_cord
        else:
            coord_i = supplier_cord[i]

        if j == 0:
            coord_j = depot_cord
        else:
            coord_j = supplier_cord[j]

        x_i, y_i = coord_i
        x_j, y_j = coord_j

        return ((x_i - x_j) ** 2 + (y_i - y_j) ** 2) ** 0.5

    def dynamic_euc_distance(i, j, origin, customer_subset):
        if i == 0:
            coord_i = origin
        else:
            coord_i = customer_subset[i]

        if j == 0:
            coord_j = origin
        else:
            coord_j = customer_subset[j]

        x_i, y_i = coord_i
        x_j, y_j = coord_j

        return ((x_i - x_j) ** 2 + (y_i - y_j) ** 2) ** 0.5

    return {
        "depot_cord": depot_cord,
        "customer_cord": customer_cord,
        "supplier_cord": supplier_cord,
        "demand": demand,
        "supplier_supply": supplier_supply,
        "service_time": service_time,
        "average_speed": average_speed,
        "vehicle_capacity": vehicle_capacity,
        "n_customers": n_customers,
        "n_suppliers": n_suppliers,
        "grid_size": grid_size,
        "total_demand": total_demand,
        "total_supply": sum(supplier_supply.values()),
        "euc_distance": euc_distance,
        "supplier_euc_distance": supplier_euc_distance,
        "dynamic_euc_distance": dynamic_euc_distance,
    }


def generate_supplier_depot_customer_instance(config):
    """Readable alias for the Supplier -> Depot -> Customer case."""
    return generate_supplier_customer_instance(config)


def generate_depot_customer_instance(config):
    """Readable alias for depot-customer experiments using the same base data."""
    return generate_supplier_customer_instance(config)
