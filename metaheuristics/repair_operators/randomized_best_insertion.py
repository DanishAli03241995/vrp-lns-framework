"""
Randomized Best Insertion repair operator.

Reinserts removed customers into a partial solution by choosing among
the best feasible insertion positions with controlled randomness.
"""

import copy
import random


# =====================================================
# STEP 1 — Compute trip load
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
# STEP 2 — Compute insertion cost
# =====================================================

def compute_insertion_cost(

    trip,

    customer,

    insert_position,

    routing_distance,
):

    prev_node = trip[insert_position - 1]

    next_node = trip[insert_position]

    insertion_cost = (

        routing_distance(prev_node, customer)

        +

        routing_distance(customer, next_node)

        -

        routing_distance(prev_node, next_node)
    )

    return insertion_cost


# =====================================================
# STEP 3 — Find feasible insertions for one customer
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
# STEP 4 — Create new route for customer
# =====================================================

def create_single_customer_route(customer):

    return [
        0,
        customer,
        0,
    ]


# =====================================================
# STEP 5 — Main randomized best insertion operator
# =====================================================

def randomized_best_insertion(

    partial_solution,

    removed_customers,

    demand,

    vehicle_capacity,

    routing_distance,

    seed=42,

    top_k=3,

    customer_order="random",
):

    random.seed(seed)

    # =====================================================
    # STEP 5.1 — Defensive copies
    # =====================================================

    working_solution = copy.deepcopy(
        partial_solution
    )

    customers_to_insert = list(
        removed_customers
    )

    # =====================================================
    # STEP 5.2 — Choose customer insertion order
    # =====================================================

    if customer_order == "random":

        random.shuffle(
            customers_to_insert
        )

    elif customer_order == "largest_demand_first":

        customers_to_insert.sort(

            key=lambda customer: demand[customer],

            reverse=True,
        )

    elif customer_order == "given":

        pass

    else:

        raise ValueError(
            f"Unknown customer_order: {customer_order}"
        )

    # =====================================================
    # STEP 5.3 — Insert customers one by one
    # =====================================================

    for customer in customers_to_insert:

        # ---------------------------------------------
        # Empty solution case
        # ---------------------------------------------

        if len(working_solution) == 0:

            working_solution.append(

                create_single_customer_route(
                    customer
                )
            )

            continue

        # ---------------------------------------------
        # Find feasible insertions
        # ---------------------------------------------

        feasible_insertions = find_feasible_insertions(

            solution=working_solution,

            customer=customer,

            demand=demand,

            vehicle_capacity=vehicle_capacity,

            routing_distance=routing_distance,
        )

        # ---------------------------------------------
        # Insert into one of the best feasible positions
        # ---------------------------------------------

        if len(feasible_insertions) > 0:

            candidate_pool_size = min(
                top_k,
                len(feasible_insertions),
            )

            selected_insertion = random.choice(

                feasible_insertions[
                    :candidate_pool_size
                ]
            )

            route_index = selected_insertion[
                "route_index"
            ]

            insert_position = selected_insertion[
                "insert_position"
            ]

            working_solution[route_index].insert(

                insert_position,

                customer,
            )

        # ---------------------------------------------
        # Otherwise create new route
        # ---------------------------------------------

        else:

            working_solution.append(

                create_single_customer_route(
                    customer
                )
            )

    return working_solution


# =====================================================
# STEP 6 — Standalone test
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

    repaired_solution = randomized_best_insertion(

        partial_solution=partial_solution,

        removed_customers=removed_customers,

        demand=demand,

        vehicle_capacity=15,

        routing_distance=routing_distance,

        seed=42,

        top_k=3,

        customer_order="random",
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