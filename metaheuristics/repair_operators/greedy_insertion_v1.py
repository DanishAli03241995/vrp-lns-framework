"""
Greedy insertion repair operator for LNS / ALNS.
"""

import copy


def greedy_insertion(
    partial_solution,
    removed_customers,
    demand,
    vehicle_capacity,
    routing_distance,
):
    """
    Greedily reinsert removed customers into solution.

    Parameters
    ----------
    partial_solution : list
        Current partial solution.

    removed_customers : list
        Customers to reinsert.

    demand : dict
        Customer demand dictionary.

    vehicle_capacity : int
        Vehicle capacity limit.

    routing_distance : function
        Distance callback function.

    Returns
    -------
    repaired_solution : list
        Solution after reinsertion.
    """

    # =========================================
    # STEP 1 — Copy solution
    # Avoid modifying original object
    # =========================================

    repaired_solution = copy.deepcopy(partial_solution)

    # =========================================
    # STEP 2 — Reinsert customers one-by-one
    # =========================================

    for customer in removed_customers:

        best_route_index = None
        best_position = None
        best_increase = float("inf")

        # =========================================
        # STEP 3 — Try insertion into every route
        # =========================================

        for r, route in enumerate(repaired_solution):

            # -----------------------------------------
            # Compute current route load
            # -----------------------------------------

            current_load = 0

            for node in route:

                if node != 0:
                    current_load += demand[node]

            # -----------------------------------------
            # Capacity feasibility check
            # -----------------------------------------

            if current_load + demand[customer] > vehicle_capacity:
                continue

            # =========================================
            # STEP 4 — Try every insertion position
            # =========================================

            for pos in range(1, len(route)):

                prev_node = route[pos - 1]
                next_node = route[pos]

                # -----------------------------------------
                # Distance increase calculation
                # -----------------------------------------

                added_cost = (
                    routing_distance(prev_node, customer)
                    + routing_distance(customer, next_node)
                )

                removed_cost = routing_distance(
                    prev_node,
                    next_node,
                )

                increase = added_cost - removed_cost

                # -----------------------------------------
                # Track best insertion
                # -----------------------------------------

                if increase < best_increase:

                    best_increase = increase
                    best_route_index = r
                    best_position = pos

        # =========================================
        # STEP 5 — Insert into best feasible position
        # =========================================

        if best_route_index is not None:

            repaired_solution[best_route_index].insert(
                best_position,
                customer,
            )

        # =========================================
        # STEP 6 — If no feasible route exists
        # Create new route
        # =========================================

        else:

            repaired_solution.append(
                [0, customer, 0]
            )

    # =========================================
    # STEP 7 — Return repaired solution
    # =========================================

    return repaired_solution


# =========================================
# Small standalone example
# =========================================

if __name__ == "__main__":

    # -----------------------------------------
    # Example partial solution
    # -----------------------------------------

    partial_solution = [
        [0, 7, 9, 0],
        [0, 12, 0],
    ]

    removed_customers = [18, 4, 15]

    demand = {
        4: 3,
        7: 4,
        9: 5,
        12: 4,
        15: 2,
        18: 3,
    }

    vehicle_capacity = 12

    # -----------------------------------------
    # Simple Euclidean-like distance example
    # -----------------------------------------

    coords = {
        0: (0, 0),
        4: (2, 1),
        7: (4, 3),
        9: (5, 5),
        12: (1, 4),
        15: (6, 2),
        18: (3, 6),
    }

    def routing_distance(i, j):

        x1, y1 = coords[i]
        x2, y2 = coords[j]

        return ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5

    repaired_solution = greedy_insertion(
        partial_solution,
        removed_customers,
        demand,
        vehicle_capacity,
        routing_distance,
    )

    print("\nPartial Solution:")
    print(partial_solution)

    print("\nRemoved Customers:")
    print(removed_customers)

    print("\nRepaired Solution:")
    print(repaired_solution)