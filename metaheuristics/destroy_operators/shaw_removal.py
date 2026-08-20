"""
Shaw Removal destroy operator.

Removes customers that are similar/related according to a weighted
relatedness score. Relatedness can combine spatial distance, demand
similarity, and same-route membership.
"""

import copy
import math
import random


# =====================================================
# STEP 1 — Flatten solution with route membership
# =====================================================

def flatten_solution_with_routes(solution):

    customer_route_map = {}

    for route_index, trip in enumerate(solution):

        for node in trip:

            if node != 0:

                customer_route_map[node] = route_index

    return customer_route_map


# =====================================================
# STEP 2 — Remove customers from solution
# =====================================================

def remove_customers_from_solution(
    solution,
    customers_to_remove,
):

    updated_solution = []

    for trip in solution:

        updated_trip = [

            node

            for node in trip

            if node not in customers_to_remove
        ]

        if len(updated_trip) > 2:

            updated_solution.append(updated_trip)

    return updated_solution


# =====================================================
# STEP 3 — Euclidean distance
# =====================================================

def euclidean_distance(
    coord_a,
    coord_b,
):

    x1, y1 = coord_a
    x2, y2 = coord_b

    return math.sqrt(
        (x1 - x2) ** 2
        + (y1 - y2) ** 2
    )


# =====================================================
# STEP 4 — Compute Shaw relatedness score
# =====================================================

def compute_shaw_relatedness(

    customer_a,

    customer_b,

    customer_coordinates,

    demand,

    customer_route_map,

    distance_weight=1.0,

    demand_weight=0.2,

    route_weight=1.0,
):

    # ---------------------------------------------
    # Spatial relatedness
    # ---------------------------------------------

    spatial_distance = euclidean_distance(

        customer_coordinates[customer_a],

        customer_coordinates[customer_b],
    )

    # ---------------------------------------------
    # Demand relatedness
    # ---------------------------------------------

    demand_difference = abs(
        demand[customer_a]
        -
        demand[customer_b]
    )

    # ---------------------------------------------
    # Route relatedness
    # ---------------------------------------------

    if (
        customer_route_map[customer_a]
        ==
        customer_route_map[customer_b]
    ):

        route_penalty = 0

    else:

        route_penalty = 1

    # ---------------------------------------------
    # Combined relatedness score
    # Lower score = more related
    # ---------------------------------------------

    relatedness_score = (

        distance_weight * spatial_distance

        +

        demand_weight * demand_difference

        +

        route_weight * route_penalty
    )

    return relatedness_score


# =====================================================
# STEP 5 — Main Shaw removal operator
# =====================================================

def shaw_removal(

    solution,

    customer_coordinates,

    demand,

    n_remove=4,

    seed=42,

    randomness=0.2,

    distance_weight=1.0,

    demand_weight=0.2,

    route_weight=1.0,
):

    random.seed(seed)

    # =====================================================
    # STEP 5.1 — Defensive copy
    # =====================================================

    working_solution = copy.deepcopy(
        solution
    )

    # =====================================================
    # STEP 5.2 — Build customer route map
    # =====================================================

    customer_route_map = flatten_solution_with_routes(
        working_solution
    )

    all_customers = list(
        customer_route_map.keys()
    )

    # =====================================================
    # STEP 5.3 — Safety checks
    # =====================================================

    if len(all_customers) == 0:

        return working_solution, []

    if n_remove >= len(all_customers):

        n_remove = len(all_customers) - 1

    if n_remove <= 0:

        return working_solution, []

    # =====================================================
    # STEP 5.4 — Select first seed customer
    # =====================================================

    seed_customer = random.choice(
        all_customers
    )

    removed_customers = [
        seed_customer
    ]

    remaining_customers = set(
        all_customers
    )

    remaining_customers.remove(
        seed_customer
    )

    # =====================================================
    # STEP 5.5 — Iteratively remove Shaw-related customers
    # =====================================================

    while (
        len(removed_customers) < n_remove
        and len(remaining_customers) > 0
    ):

        candidate_scores = []

        for candidate in remaining_customers:

            best_relatedness = float("inf")

            for removed_customer in removed_customers:

                relatedness_score = compute_shaw_relatedness(

                    customer_a=candidate,

                    customer_b=removed_customer,

                    customer_coordinates=customer_coordinates,

                    demand=demand,

                    customer_route_map=customer_route_map,

                    distance_weight=distance_weight,

                    demand_weight=demand_weight,

                    route_weight=route_weight,
                )

                if relatedness_score < best_relatedness:

                    best_relatedness = relatedness_score

            candidate_scores.append(
                (
                    candidate,
                    best_relatedness,
                )
            )

        # ---------------------------------------------
        # Lower score means more related
        # ---------------------------------------------

        candidate_scores.sort(
            key=lambda x: x[1]
        )

        # ---------------------------------------------
        # Controlled randomness
        # ---------------------------------------------

        top_k = max(
            1,
            int(
                randomness
                * len(candidate_scores)
            )
        )

        selected_customer = random.choice(
            candidate_scores[:top_k]
        )[0]

        removed_customers.append(
            selected_customer
        )

        remaining_customers.remove(
            selected_customer
        )

    # =====================================================
    # STEP 5.6 — Remove selected customers
    # =====================================================

    destroyed_solution = remove_customers_from_solution(

        working_solution,

        removed_customers,
    )

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

        [0, 4, 5, 6, 0],

        [0, 7, 8, 9, 0],
    ]

    customer_coordinates = {

        1: (1, 1),
        2: (2, 1),
        3: (3, 1),

        4: (8, 8),
        5: (9, 8),
        6: (10, 8),

        7: (15, 2),
        8: (16, 2),
        9: (17, 2),
    }

    demand = {

        1: 2,
        2: 3,
        3: 2,

        4: 8,
        5: 7,
        6: 8,

        7: 4,
        8: 5,
        9: 4,
    }

    destroyed_solution, removed_customers = shaw_removal(

        solution=sample_solution,

        customer_coordinates=customer_coordinates,

        demand=demand,

        n_remove=4,

        seed=42,

        randomness=0.2,

        distance_weight=1.0,

        demand_weight=0.2,

        route_weight=1.0,
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