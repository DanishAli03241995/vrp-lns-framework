"""
Related Removal destroy operator.

Removes geographically related customers together
to enable localized route restructuring.
"""

import copy
import math
import random


# =====================================================
# STEP 1 — Flatten solution into customer list
# =====================================================

def flatten_solution(solution):

    customers = []

    for trip in solution:

        for node in trip:

            if node != 0:

                customers.append(node)

    return customers


# =====================================================
# STEP 2 — Find customer coordinates
# =====================================================

def get_customer_coord(
    customer,
    customer_coordinates,
):

    return customer_coordinates[customer]


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
# STEP 4 — Remove customers from solution
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

        # Keep depot boundaries
        if len(updated_trip) > 2:

            updated_solution.append(updated_trip)

    return updated_solution


# =====================================================
# STEP 5 — Main related removal operator
# =====================================================

def related_removal(

    solution,

    customer_coordinates,

    n_remove=4,

    seed=42,

    randomness=0.2,
):

    random.seed(seed)

    # =====================================================
    # STEP 5.1 — Defensive copy
    # =====================================================

    working_solution = copy.deepcopy(solution)

    # =====================================================
    # STEP 5.2 — Flatten customers
    # =====================================================

    all_customers = flatten_solution(
        working_solution
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
    # STEP 5.4 — Select seed customer
    # =====================================================

    seed_customer = random.choice(
        all_customers
    )

    removed_customers = [seed_customer]

    remaining_customers = set(all_customers)

    remaining_customers.remove(seed_customer)

    # =====================================================
    # STEP 5.5 — Iteratively remove related customers
    # =====================================================

    while (
        len(removed_customers) < n_remove
        and len(remaining_customers) > 0
    ):

        candidate_scores = []

        # ---------------------------------------------
        # Compute relatedness
        # ---------------------------------------------

        for candidate in remaining_customers:

            candidate_coord = get_customer_coord(
                candidate,
                customer_coordinates,
            )

            min_distance = float("inf")

            for removed_customer in removed_customers:

                removed_coord = get_customer_coord(
                    removed_customer,
                    customer_coordinates,
                )

                distance = euclidean_distance(
                    candidate_coord,
                    removed_coord,
                )

                if distance < min_distance:

                    min_distance = distance

            candidate_scores.append(
                (
                    candidate,
                    min_distance,
                )
            )

        # ---------------------------------------------
        # Sort by proximity
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

        selected_candidate = random.choice(
            candidate_scores[:top_k]
        )[0]

        removed_customers.append(
            selected_candidate
        )

        remaining_customers.remove(
            selected_candidate
        )

    # =====================================================
    # STEP 5.6 — Remove from solution
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

    destroyed_solution, removed_customers = related_removal(

        solution=sample_solution,

        customer_coordinates=customer_coordinates,

        n_remove=4,

        seed=42,

        randomness=0.2,
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
