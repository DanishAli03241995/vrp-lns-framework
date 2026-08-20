"""
Basic LNS skeleton with Simulated Annealing acceptance:
random removal + greedy insertion + SA acceptance.
"""

import copy
import math
import os
import random
import sys
import importlib


sys.path.append(os.path.dirname(os.path.dirname(__file__)))


# =========================================
# STEP 1 — Import modular operators
# =========================================

random_removal_v1 = importlib.import_module(
    "metaheuristics.destroy_operators.random_removal_v1"
)

greedy_insertion_v1 = importlib.import_module(
    "metaheuristics.repair_operators.greedy_insertion_v1"
)

random_removal = random_removal_v1.random_removal
greedy_insertion = greedy_insertion_v1.greedy_insertion


# =========================================
# STEP 2 — Route distance helper
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
# STEP 3 — Simulated Annealing acceptance
# =========================================

def accept_solution_sa(
    current_distance,
    candidate_distance,
    temperature,
):
    """
    Decide whether to accept candidate solution using
    Simulated Annealing acceptance logic.
    """

    # -----------------------------------------
    # Always accept improving solutions
    # -----------------------------------------

    if candidate_distance < current_distance:

        return True, "improved"

    # -----------------------------------------
    # Compute worsening amount
    # -----------------------------------------

    delta = candidate_distance - current_distance

    # -----------------------------------------
    # Avoid division by zero / frozen search
    # -----------------------------------------

    if temperature <= 0:

        return False, "rejected"

    # -----------------------------------------
    # SA acceptance probability
    # -----------------------------------------

    acceptance_probability = math.exp(
        -delta / temperature
    )

    random_number = random.random()

    if random_number < acceptance_probability:

        return True, "accepted_worse"

    return False, "rejected"


# =========================================
# STEP 4 — Basic LNS + SA loop
# =========================================

def run_basic_lns_sa(
    initial_solution,
    demand,
    vehicle_capacity,
    routing_distance,
    n_iterations=20,
    n_remove=3,
    seed=42,
    initial_temperature=10.0,
    cooling_rate=0.95,
    minimum_temperature=0.01,
):
    """
    Run basic LNS with Simulated Annealing acceptance.

    Current version:
    - random removal
    - greedy insertion
    - SA acceptance
    """

    # =========================================
    # STEP 4.1 — Set random seed
    # =========================================

    random.seed(seed)

    # =========================================
    # STEP 4.2 — Initialize current solution
    # =========================================

    current_solution = copy.deepcopy(initial_solution)

    current_distance = compute_solution_distance(
        current_solution,
        routing_distance,
    )

    # =========================================
    # STEP 4.3 — Track best solution
    # =========================================

    best_solution = copy.deepcopy(current_solution)

    best_distance = current_distance

    # =========================================
    # STEP 4.4 — Initialize temperature
    # =========================================

    temperature = initial_temperature

    print("\n===================================")
    print("INITIAL SOLUTION")
    print("===================================")

    print("Initial Distance:", current_distance)
    print("Initial Temperature:", temperature)
    print(current_solution)

    # =========================================
    # STEP 4.5 — Main LNS + SA loop
    # =========================================

    for iteration in range(n_iterations):

        print("\n-----------------------------------")
        print(f"Iteration {iteration + 1}")
        print("-----------------------------------")
        print("Current Distance:", current_distance)
        print("Best Distance:", best_distance)
        print("Temperature:", temperature)

        # =========================================
        # STEP 5 — Destroy
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
        # STEP 6 — Repair
        # =========================================

        candidate_solution = greedy_insertion(
            partial_solution=partial_solution,
            removed_customers=removed_customers,
            demand=demand,
            vehicle_capacity=vehicle_capacity,
            routing_distance=routing_distance,
        )

        candidate_distance = compute_solution_distance(
            candidate_solution,
            routing_distance,
        )

        print("\nCandidate Solution:")
        print(candidate_solution)

        print("\nCandidate Distance:")
        print(candidate_distance)

        # =========================================
        # STEP 7 — SA accept/reject
        # =========================================

        accepted, acceptance_reason = accept_solution_sa(
            current_distance=current_distance,
            candidate_distance=candidate_distance,
            temperature=temperature,
        )

        print("\nAcceptance Decision:")
        print(acceptance_reason)

        if accepted:

            current_solution = copy.deepcopy(candidate_solution)

            current_distance = candidate_distance

            # -------------------------------------
            # Update global best only if genuinely best
            # -------------------------------------

            if current_distance < best_distance:

                best_solution = copy.deepcopy(current_solution)

                best_distance = current_distance

        # =========================================
        # STEP 8 — Cool temperature
        # =========================================

        temperature = max(
            temperature * cooling_rate,
            minimum_temperature,
        )

    # =========================================
    # STEP 9 — Final output
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
# STEP 10 — Small standalone example
# =========================================

if __name__ == "__main__":

    initial_solution = [
        [0, 4, 7, 9, 0],
        [0, 12, 15, 18, 0],
    ]

    demand = {
        4: 3,
        7: 4,
        9: 5,
        12: 4,
        15: 2,
        18: 3,
    }

    vehicle_capacity = 12

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

    best_solution, best_distance = run_basic_lns_sa(
        initial_solution=initial_solution,
        demand=demand,
        vehicle_capacity=vehicle_capacity,
        routing_distance=routing_distance,
        n_iterations=20,
        n_remove=3,
        seed=42,
        initial_temperature=10.0,
        cooling_rate=0.95,
        minimum_temperature=0.01,
    )
