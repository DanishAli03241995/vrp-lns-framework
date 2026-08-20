"""Angular supplier assignment and supplier subproblem construction."""

import math


def compute_customer_angles(depot_cord, customer_cord, demand):
    center_x, center_y = depot_cord
    customer_angles = []

    for customer_id, (x_coord, y_coord) in customer_cord.items():
        customer_demand = demand[customer_id]
        dx = x_coord - center_x
        dy = y_coord - center_y
        angle = math.atan2(dy, dx)

        if angle < 0:
            angle += 2 * math.pi

        customer_angles.append(
            (customer_id, x_coord, y_coord, customer_demand, angle)
        )

    customer_angles.sort(key=lambda item: item[4])

    return customer_angles


def compute_sector_size(n_suppliers):
    if n_suppliers <= 0:
        raise ValueError("Number of suppliers must be greater than zero.")

    return 2 * math.pi / n_suppliers


def sector_assignment(customer_angles, sector_size, n_suppliers):
    supplier_groups = {
        supplier_id: []
        for supplier_id in range(1, n_suppliers + 1)
    }

    for customer_id, x_coord, y_coord, customer_demand, angle in customer_angles:
        supplier_id = int(angle / sector_size) + 1

        if supplier_id > n_suppliers:
            supplier_id = n_suppliers

        supplier_groups[supplier_id].append(customer_id)

    return supplier_groups


def construct_supplier_subproblems(
    supplier_groups,
    customer_cord,
    demand,
    supplier_cord,
):
    supplier_subproblems = {}

    for supplier_id, customer_ids in supplier_groups.items():
        customer_subset = {}
        demand_subset = {}

        for customer_id in customer_ids:
            customer_subset[customer_id] = customer_cord[customer_id]
            demand_subset[customer_id] = demand[customer_id]

        supplier_subproblems[supplier_id] = {
            "origin": supplier_cord[supplier_id],
            "customer_cord": customer_subset,
            "demand": demand_subset,
        }

    return supplier_subproblems


def build_system2_subproblems(
    depot_cord,
    customer_cord,
    demand,
    n_suppliers,
    supplier_cord,
):
    customer_angles = compute_customer_angles(depot_cord, customer_cord, demand)
    sector_size = compute_sector_size(n_suppliers)
    supplier_groups = sector_assignment(
        customer_angles,
        sector_size,
        n_suppliers,
    )

    return construct_supplier_subproblems(
        supplier_groups,
        customer_cord,
        demand,
        supplier_cord,
    )
