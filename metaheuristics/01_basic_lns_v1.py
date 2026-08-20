"""
Basic LNS skeleton:
random removal + greedy insertion.
"""

import copy
import importlib
import os
import sys


sys.path.append(os.path.dirname(os.path.dirname(__file__)))


random_removal_v1 = importlib.import_module(
    "metaheuristics.destroy_operators.random_removal_v1"
)

greedy_insertion_v1 = importlib.import_module(
    "metaheuristics.repair_operators.greedy_insertion_v1"
)

random_removal = random_removal_v1.random_removal
greedy_insertion = greedy_insertion_v1.greedy_insertion


# =========================================
# STEP 1 — Route distance helper
# =========================================

def compute_solution_distance(
    solution,
    routing_distance,
):
    """
    Compute total distance of full solution.
    """

    total_distance = 0

    for route in solution:

        for i in range(len(route) - 1):

            total_distance += routing_distance(
                route[i],
                route[i + 1],
            )

    return total_distance


# =========================================
# STEP 2 — Basic LNS loop
# =========================================

def run_basic_lns(
    initial_solution,
    demand,
    vehicle_capacity,
    routing_distance,
    n_iterations=10,
    n_remove=2,
    seed=42,
):
    """
    Run very basic LNS.

    Current version:
    - random removal
    - greedy insertion
    - accept only improving solutions
    """

    # =========================================
    # STEP 2.1 — Initialize current solution
    # =========================================

    current_solution = copy.deepcopy(initial_solution)

    current_distance = compute_solution_distance(
        current_solution,
        routing_distance,
    )

    # =========================================
    # STEP 2.2 — Track best solution
    # =========================================

    best_solution = copy.deepcopy(current_solution)

    best_distance = current_distance

    print("\n===================================")
    print("INITIAL SOLUTION")
    print("===================================")

    print("Initial Distance:", current_distance)
    print(current_solution)

    # =========================================
    # STEP 2.3 — Main LNS loop
    # =========================================

    for iteration in range(n_iterations):

        print("\n-----------------------------------")
        print(f"Iteration {iteration + 1}")
        print("-----------------------------------")

        # =========================================
        # STEP 3 — Destroy
        # =========================================

        partial_solution, removed_customers = random_removal(
            solution=current_solution,
            n_remove=n_remove,
            seed=seed + iteration,
        )

        print("\nRemoved Customers:")
        print(removed_customers)

        print("\nPartial Solution:")
        print(partial_solution)

        # =========================================
        # STEP 4 — Repair
        # =========================================

        repaired_solution = greedy_insertion(
            partial_solution=partial_solution,
            removed_customers=removed_customers,
            demand=demand,
            vehicle_capacity=vehicle_capacity,
            routing_distance=routing_distance,
        )

        repaired_distance = compute_solution_distance(
            repaired_solution,
            routing_distance,
        )

        print("\nRepaired Solution:")
        print(repaired_solution)

        print("\nRepaired Distance:")
        print(repaired_distance)

        # =========================================
        # STEP 5 — Accept only improving solutions
        # =========================================

        if repaired_distance < current_distance:

            print("\nImproved Solution Accepted")

            current_solution = copy.deepcopy(repaired_solution)

            current_distance = repaired_distance

            # -------------------------------------
            # Update best solution
            # -------------------------------------

            if current_distance < best_distance:

                best_solution = copy.deepcopy(current_solution)

                best_distance = current_distance

        else:

            print("\nSolution Rejected")

    # =========================================
    # STEP 6 — Final output
    # =========================================

    print("\n===================================")
    print("FINAL BEST SOLUTION")
    print("===================================")

    print("Best Distance:", best_distance)

    print(best_solution)

    return (
        best_solution,
        best_distance,
    )


# =========================================
# STEP 7 — Small standalone example
# =========================================

if __name__ == "__main__":

    # =========================================
    # Example initial solution
    # =========================================

    initial_solution = [
        [0, 4, 7, 9, 0],
        [0, 12, 15, 18, 0],
    ]

    # =========================================
    # Demand
    # =========================================

    demand = {
        4: 3,
        7: 4,
        9: 5,
        12: 4,
        15: 2,
        18: 3,
    }

    vehicle_capacity = 12

    # =========================================
    # Coordinates
    # =========================================

    coords = {
        0: (0, 0),
        4: (2, 1),
        7: (4, 3),
        9: (5, 5),
        12: (1, 4),
        15: (6, 2),
        18: (3, 6),
    }

    # =========================================
    # Distance callback
    # =========================================

    def routing_distance(i, j):

        x1, y1 = coords[i]
        x2, y2 = coords[j]

        return ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5

    # =========================================
    # Run LNS
    # =========================================

    best_solution, best_distance = run_basic_lns(
        initial_solution=initial_solution,
        demand=demand,
        vehicle_capacity=vehicle_capacity,
        routing_distance=routing_distance,
        n_iterations=10,
        n_remove=2,
        seed=42,
    )
