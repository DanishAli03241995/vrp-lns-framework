"""Nearest-neighbor construction heuristic for depot-customer CVRP."""

import math


def node_coord(node_id, depot_cord, customer_cord, depot_id=0):
    if node_id == depot_id:
        return depot_cord

    return customer_cord[node_id]


def euclidean_distance(from_node, to_node, depot_cord, customer_cord, depot_id=0):
    x1, y1 = node_coord(from_node, depot_cord, customer_cord, depot_id)
    x2, y2 = node_coord(to_node, depot_cord, customer_cord, depot_id)

    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def route_distance(route, depot_cord, customer_cord, depot_id=0):
    total_distance = 0

    for index in range(len(route) - 1):
        total_distance += euclidean_distance(
            route[index],
            route[index + 1],
            depot_cord,
            customer_cord,
            depot_id,
        )

    return total_distance


def total_route_distance(routes, depot_cord, customer_cord, depot_id=0):
    return sum(route_distance(route, depot_cord, customer_cord, depot_id) for route in routes)


def run_baseline_nn(
    depot_cord,
    customer_cord,
    demand,
    vehicle_capacity,
    depot_id=0,
):
    unserved_customers = list(customer_cord.keys())
    routes = []

    while unserved_customers:
        current_node = depot_id
        current_route = [depot_id]
        remaining_capacity = vehicle_capacity

        while True:
            feasible_customers = [
                customer_id
                for customer_id in unserved_customers
                if demand[customer_id] <= remaining_capacity
            ]

            if not feasible_customers:
                break

            nearest_customer = min(
                feasible_customers,
                key=lambda customer_id: euclidean_distance(
                    current_node,
                    customer_id,
                    depot_cord,
                    customer_cord,
                    depot_id,
                ),
            )

            current_route.append(nearest_customer)
            unserved_customers.remove(nearest_customer)
            remaining_capacity -= demand[nearest_customer]
            current_node = nearest_customer

        current_route.append(depot_id)
        routes.append(current_route)

    return routes
