"""
Random removal destroy operator for LNS / ALNS.
"""

import random


def random_removal(
    solution,
    n_remove,
    seed=None,
):
    """
    Randomly remove customers from a solution.

    Parameters
    ----------
    solution : list
        List of routes/trips.

    n_remove : int
        Number of customers to remove.

    seed : int or None
        Optional random seed for reproducibility.

    Returns
    -------
    partial_solution : list
        Solution after removals.

    removed_customers : list
        Customers removed from solution.
    """

    # =========================================
    # STEP 1 — Optional reproducibility
    # =========================================

    if seed is not None:
        random.seed(seed)

    # =========================================
    # STEP 2 — Collect all removable customers
    # Ignore depot node 0
    # =========================================

    all_customers = []

    for route in solution:

        for customer in route:

            if customer != 0:
                all_customers.append(customer)

    # =========================================
    # STEP 3 — Prevent over-removal
    # =========================================

    n_remove = min(n_remove, len(all_customers))

    # =========================================
    # STEP 4 — Randomly select customers
    # =========================================

    removed_customers = random.sample(
        all_customers,
        n_remove,
    )

    # =========================================
    # STEP 5 — Build partial solution
    # Remove selected customers from routes
    # =========================================

    partial_solution = []

    for route in solution:

        new_route = []

        for customer in route:

            if customer not in removed_customers:
                new_route.append(customer)

        # =========================================
        # Keep only meaningful routes
        # [0,0] routes are discarded
        # =========================================

        if len(new_route) > 2:
            partial_solution.append(new_route)

    # =========================================
    # STEP 6 — Return outputs
    # =========================================

    return (
        partial_solution,
        removed_customers,
    )


# =========================================
# Small standalone test
# =========================================

if __name__ == "__main__":

    solution = [
        [0, 4, 7, 9, 0],
        [0, 12, 15, 18, 0],
    ]

    partial_solution, removed_customers = random_removal(
        solution=solution,
        n_remove=3,
        seed=42,
    )

    print("\nOriginal Solution:")
    print(solution)

    print("\nRemoved Customers:")
    print(removed_customers)

    print("\nPartial Solution:")
    print(partial_solution)