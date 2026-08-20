"""
Worst Removal destroy operator.

Removes customers contributing the highest
marginal routing cost from the current solution.
"""

import copy
import random


# =====================================================
# STEP 1 — Remove customers from solution
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

        # Keep only meaningful trips
        if len(updated_trip) > 2:

            updated_solution.append(
                updated_trip
            )

    return updated_solution


# =====================================================
# STEP 2 — Compute marginal contribution
# =====================================================

def compute_customer_removal_cost(

    prev_node,

    customer,

    next_node,

    routing_distance,
):

    current_cost = (

        routing_distance(prev_node, customer)

        +

        routing_distance(customer, next_node)
    )

    repaired_cost = routing_distance(
        prev_node,
        next_node,
    )

    removal_gain = (
        current_cost - repaired_cost
    )

    return removal_gain


# =====================================================
# STEP 3 — Main worst removal operator
# =====================================================

def worst_removal(

    solution,

    routing_distance,

    n_remove=4,

    seed=42,

    randomness=0.2,
):

    random.seed(seed)

    # =====================================================
    # STEP 3.1 — Defensive copy
    # =====================================================

    working_solution = copy.deepcopy(
        solution
    )

    removed_customers = []

    # =====================================================
    # STEP 3.2 — Iteratively remove worst customers
    # =====================================================

    while len(removed_customers) < n_remove:

        candidate_scores = []

        # ---------------------------------------------
        # Evaluate all customers
        # ---------------------------------------------

        for trip in working_solution:

            if len(trip) <= 3:
                continue

            for index in range(
                1,
                len(trip) - 1
            ):

                customer = trip[index]

                prev_node = trip[index - 1]

                next_node = trip[index + 1]

                removal_gain = compute_customer_removal_cost(

                    prev_node=prev_node,

                    customer=customer,

                    next_node=next_node,

                    routing_distance=routing_distance,
                )

                candidate_scores.append(

                    (
                        customer,
                        removal_gain,
                    )
                )

        # ---------------------------------------------
        # Safety check
        # ---------------------------------------------

        if len(candidate_scores) == 0:
            break

        # ---------------------------------------------
        # Sort by highest gain
        # ---------------------------------------------

        candidate_scores.sort(

            key=lambda x: x[1],

            reverse=True,
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

        # ---------------------------------------------
        # Remove selected customer
        # ---------------------------------------------

        working_solution = remove_customers_from_solution(

            working_solution,

            [selected_customer],
        )

    # =====================================================
    # STEP 3.3 — Return
    # =====================================================

    return (
        working_solution,
        removed_customers,
    )


# =====================================================
# STEP 4 — Standalone test
# =====================================================

if __name__ == "__main__":

    sample_solution = [

        [0, 1, 2, 3, 0],

        [0, 4, 5, 6, 0],

        [0, 7, 8, 9, 0],
    ]

    customer_coordinates = {

        0: (0, 0),

        1: (1, 1),
        2: (2, 1),
        3: (6, 1),

        4: (8, 8),
        5: (12, 8),
        6: (13, 8),

        7: (15, 2),
        8: (16, 2),
        9: (25, 2),
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

    destroyed_solution, removed_customers = worst_removal(

        solution=sample_solution,

        routing_distance=routing_distance,

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