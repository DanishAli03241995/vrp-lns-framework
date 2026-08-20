"""
Regret-2 Insertion repair operator.

Reinserts removed customers into a partial solution by prioritizing
customers whose second-best insertion option is much worse than their
best insertion option.
"""

import copy


# =====================================================
# STEP 1 - Compute trip load
# =====================================================

def compute_trip_load(
    trip,
    demand,
):

    trip_load = 0

    for node in trip:

        if node != 0:

            trip_load += demand[node]

    return trip_load


# =====================================================
# STEP 2 - Compute insertion cost
# =====================================================

def compute_insertion_cost(

    trip,

    customer,

    insert_position,

    routing_distance,
):

    prev_node = trip[insert_position - 1]

    next_node = trip[insert_position]

    added_cost = (

        routing_distance(prev_node, customer)

        +

        routing_distance(customer, next_node)

        -

        routing_distance(prev_node, next_node)
    )

    return added_cost


# =====================================================
# STEP 3 - Find feasible insertions for one customer
# =====================================================

def find_feasible_insertions(

    solution,

    customer,

    demand,

    vehicle_capacity,

    routing_distance,
):

    feasible_insertions = []

    customer_demand = demand[customer]

    for route_index, trip in enumerate(solution):

        trip_load = compute_trip_load(
            trip,
            demand,
        )

        if trip_load + customer_demand > vehicle_capacity:

            continue

        for insert_position in range(
            1,
            len(trip),
        ):

            insertion_cost = compute_insertion_cost(

                trip=trip,

                customer=customer,

                insert_position=insert_position,

                routing_distance=routing_distance,
            )

            feasible_insertions.append(
                {
                    "route_index": route_index,
                    "insert_position": insert_position,
                    "insertion_cost": insertion_cost,
                }
            )

    feasible_insertions.sort(
        key=lambda x: x["insertion_cost"]
    )

    return feasible_insertions


# =====================================================
# STEP 4 - Compute regret-2 score
# =====================================================

def compute_regret_2_score(
    feasible_insertions,
):

    best_insertion = feasible_insertions[0]

    best_cost = best_insertion[
        "insertion_cost"
    ]

    if len(feasible_insertions) >= 2:

        second_best_cost = feasible_insertions[1][
            "insertion_cost"
        ]

    else:

        second_best_cost = best_cost

    regret_score = (
        second_best_cost - best_cost
    )

    return (
        regret_score,
        best_insertion,
    )


# =====================================================
# STEP 5 - Create new route for customer
# =====================================================

def create_single_customer_route(customer):

    return [
        0,
        customer,
        0,
    ]


# =====================================================
# STEP 6 - Main regret-2 insertion operator
# =====================================================

def regret_2_insertion(

    partial_solution,

    removed_customers,

    demand,

    vehicle_capacity,

    routing_distance,
):

    # =====================================================
    # STEP 6.1 - Defensive copies
    # =====================================================

    working_solution = copy.deepcopy(
        partial_solution
    )

    customers_to_insert = list(
        removed_customers
    )

    if len(customers_to_insert) == 0:

        return working_solution

    # =====================================================
    # STEP 6.2 - Ensure solution is not empty
    # =====================================================

    if len(working_solution) == 0:

        first_customer = customers_to_insert.pop(0)

        working_solution.append(
            create_single_customer_route(
                first_customer
            )
        )

    # =====================================================
    # STEP 6.3 - Insert customers one by one
    # =====================================================

    while len(customers_to_insert) > 0:

        customer_scores = []

        # ---------------------------------------------
        # Evaluate every uninserted customer
        # ---------------------------------------------

        for customer in customers_to_insert:

            feasible_insertions = find_feasible_insertions(

                solution=working_solution,

                customer=customer,

                demand=demand,

                vehicle_capacity=vehicle_capacity,

                routing_distance=routing_distance,
            )

            if len(feasible_insertions) == 0:

                customer_scores.append(
                    {
                        "customer": customer,
                        "regret_score": float("inf"),
                        "best_insertion": None,
                    }
                )

            else:

                regret_score, best_insertion = compute_regret_2_score(
                    feasible_insertions
                )

                customer_scores.append(
                    {
                        "customer": customer,
                        "regret_score": regret_score,
                        "best_insertion": best_insertion,
                    }
                )

        # ---------------------------------------------
        # Select customer with highest regret
        # ---------------------------------------------

        customer_scores.sort(
            key=lambda x: x["regret_score"],
            reverse=True,
        )

        selected = customer_scores[0]

        selected_customer = selected[
            "customer"
        ]

        best_insertion = selected[
            "best_insertion"
        ]

        # ---------------------------------------------
        # Insert into existing route if feasible
        # ---------------------------------------------

        if best_insertion is not None:

            route_index = best_insertion[
                "route_index"
            ]

            insert_position = best_insertion[
                "insert_position"
            ]

            working_solution[route_index].insert(

                insert_position,

                selected_customer,
            )

        # ---------------------------------------------
        # Otherwise create new route
        # ---------------------------------------------

        else:

            working_solution.append(

                create_single_customer_route(
                    selected_customer
                )
            )

        customers_to_insert.remove(
            selected_customer
        )

    return working_solution


# =====================================================
# STEP 7 - Standalone test
# =====================================================

if __name__ == "__main__":

    partial_solution = [

        [0, 1, 3, 0],

        [0, 4, 6, 0],
    ]

    removed_customers = [
        2,
        5,
        7,
    ]

    demand = {

        1: 4,
        2: 3,
        3: 5,

        4: 4,
        5: 3,
        6: 5,

        7: 6,
    }

    customer_coordinates = {

        0: (0, 0),

        1: (1, 1),
        2: (2, 1),
        3: (3, 1),

        4: (8, 8),
        5: (9, 8),
        6: (10, 8),

        7: (15, 2),
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

    repaired_solution = regret_2_insertion(

        partial_solution=partial_solution,

        removed_customers=removed_customers,

        demand=demand,

        vehicle_capacity=15,

        routing_distance=routing_distance,
    )

    print("\n===================================")
    print("PARTIAL SOLUTION")
    print("===================================")

    print(partial_solution)

    print("\n===================================")
    print("REMOVED CUSTOMERS")
    print("===================================")

    print(removed_customers)

    print("\n===================================")
    print("REPAIRED SOLUTION")
    print("===================================")

    print(repaired_solution)
