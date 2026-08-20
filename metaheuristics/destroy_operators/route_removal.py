"""
Route Removal destroy operator.

Removes one or more complete trips/routes from the current solution.
This allows the repair operator to reinsert those customers elsewhere,
possibly reducing route count or improving consolidation.
"""

import copy
import random


# =====================================================
# STEP 1 — Extract customers from a trip
# =====================================================

def get_trip_customers(trip):

    return [
        node
        for node in trip
        if node != 0
    ]


# =====================================================
# STEP 2 — Compute trip load
# =====================================================

def compute_trip_load(
    trip,
    demand,
):

    trip_load = 0

    for customer in get_trip_customers(trip):

        trip_load += demand[customer]

    return trip_load


# =====================================================
# STEP 3 — Compute trip distance
# =====================================================

def compute_trip_distance(
    trip,
    routing_distance,
):

    trip_distance = 0

    for index in range(len(trip) - 1):

        trip_distance += routing_distance(
            trip[index],
            trip[index + 1],
        )

    return trip_distance


# =====================================================
# STEP 4 — Score routes for removal
# =====================================================

def score_routes_for_removal(

    solution,

    strategy="fewest_customers",

    demand=None,

    vehicle_capacity=None,

    routing_distance=None,
):

    route_scores = []

    for route_index, trip in enumerate(solution):

        customers = get_trip_customers(trip)

        if len(customers) == 0:
            continue

        if strategy == "fewest_customers":

            score = len(customers)

        elif strategy == "lowest_utilization":

            if demand is None or vehicle_capacity is None:

                score = len(customers)

            else:

                trip_load = compute_trip_load(
                    trip,
                    demand,
                )

                score = trip_load / vehicle_capacity

        elif strategy == "highest_distance":

            if routing_distance is None:

                score = len(customers)

            else:

                score = compute_trip_distance(
                    trip,
                    routing_distance,
                )

        elif strategy == "random":

            score = random.random()

        else:

            raise ValueError(
                f"Unknown route removal strategy: {strategy}"
            )

        route_scores.append(
            {
                "route_index": route_index,
                "trip": trip,
                "customers": customers,
                "score": score,
            }
        )

    return route_scores


# =====================================================
# STEP 5 — Main route removal operator
# =====================================================

def route_removal(

    solution,

    n_remove=4,

    seed=42,

    strategy="fewest_customers",

    demand=None,

    vehicle_capacity=None,

    routing_distance=None,

    max_routes_to_remove=1,

    keep_at_least_one_route=True,
):

    random.seed(seed)

    # =====================================================
    # STEP 5.1 — Defensive copy
    # =====================================================

    working_solution = copy.deepcopy(
        solution
    )

    removed_customers = []

    removed_route_indices = set()

    # =====================================================
    # STEP 5.2 — Safety checks
    # =====================================================

    if len(working_solution) == 0:

        return working_solution, removed_customers

    if (
        keep_at_least_one_route
        and len(working_solution) <= 1
    ):

        return working_solution, removed_customers

    # =====================================================
    # STEP 5.3 — Score candidate routes
    # =====================================================

    route_scores = score_routes_for_removal(

        solution=working_solution,

        strategy=strategy,

        demand=demand,

        vehicle_capacity=vehicle_capacity,

        routing_distance=routing_distance,
    )

    if len(route_scores) == 0:

        return working_solution, removed_customers

    # =====================================================
    # STEP 5.4 — Sort routes based on strategy
    # =====================================================

    if strategy in [
        "fewest_customers",
        "lowest_utilization",
    ]:

        route_scores.sort(
            key=lambda x: x["score"]
        )

    elif strategy == "highest_distance":

        route_scores.sort(
            key=lambda x: x["score"],
            reverse=True,
        )

    elif strategy == "random":

        random.shuffle(route_scores)

    # =====================================================
    # STEP 5.5 — Remove selected routes
    # =====================================================

    for route_data in route_scores:

        if len(removed_route_indices) >= max_routes_to_remove:
            break

        if len(removed_customers) >= n_remove:
            break

        if (
            keep_at_least_one_route
            and len(working_solution) - len(removed_route_indices) <= 1
        ):

            break

        route_index = route_data["route_index"]

        removed_route_indices.add(route_index)

        removed_customers.extend(
            route_data["customers"]
        )

    # =====================================================
    # STEP 5.6 — Build destroyed solution
    # =====================================================

    destroyed_solution = []

    for route_index, trip in enumerate(working_solution):

        if route_index not in removed_route_indices:

            destroyed_solution.append(trip)

    # =====================================================
    # STEP 5.7 — Return
    # =====================================================

    return (
        destroyed_solution,
        removed_customers,
    )


# =====================================================
# STEP 6 — Standalone test
# =====================================================

if __name__ == "__main__":

    sample_solution = [

        [0, 1, 2, 3, 0],

        [0, 4, 5, 0],

        [0, 6, 0],

        [0, 7, 8, 9, 0],
    ]

    demand = {

        1: 4,
        2: 5,
        3: 3,

        4: 2,
        5: 2,

        6: 1,

        7: 6,
        8: 5,
        9: 4,
    }

    customer_coordinates = {

        0: (0, 0),

        1: (1, 1),
        2: (2, 1),
        3: (3, 1),

        4: (8, 8),
        5: (9, 8),

        6: (20, 20),

        7: (15, 2),
        8: (16, 2),
        9: (17, 2),
    }

    def routing_distance(i, j):

        x1, y1 = customer_coordinates[i]

        x2, y2 = customer_coordinates[j]

        return (
            (
                (x1 - x2) ** 2
                +
                (y1 - y2) ** 2
            )
            ** 0.5
        )

    destroyed_solution, removed_customers = route_removal(

        solution=sample_solution,

        n_remove=4,

        seed=42,

        strategy="lowest_utilization",

        demand=demand,

        vehicle_capacity=15,

        routing_distance=routing_distance,

        max_routes_to_remove=1,
    )

    print("\n===================================")
    print("ORIGINAL SOLUTION")
    print("===================================")

    print(sample_solution)

    print("\n===================================")
    print("REMOVED CUSTOMERS")
    print("===================================")

    print(removed_customers)

    print("\n===================================")
    print("DESTROYED SOLUTION")
    print("===================================")

    print(destroyed_solution)