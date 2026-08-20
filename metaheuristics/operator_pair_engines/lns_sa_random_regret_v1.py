"""
LNS-SA engine for Random Removal + Regret-2 Insertion.
"""

import copy
import math
import os
import random
import sys
import importlib


sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


random_removal_module = importlib.import_module(
    "metaheuristics.destroy_operators.random_removal_v1"
)

regret_insertion_module = importlib.import_module(
    "metaheuristics.repair_operators.regret_2_insertion"
)

random_removal = random_removal_module.random_removal
regret_2_insertion = regret_insertion_module.regret_2_insertion


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


def remove_empty_routes(solution):
    """
    Keep only routes that serve at least one customer.
    """

    return [
        route
        for route in solution
        if len(route) > 2
    ]


def accept_solution_sa(
    current_distance,
    candidate_distance,
    temperature,
):
    """
    Decide whether to accept candidate solution using SA logic.
    """

    if candidate_distance < current_distance:
        return True, "improved"

    delta = candidate_distance - current_distance

    if temperature <= 0:
        return False, "rejected"

    acceptance_probability = math.exp(
        -delta / temperature
    )

    if random.random() < acceptance_probability:
        return True, "accepted_worse"

    return False, "rejected"


def run_lns_sa_random_regret(
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
    Run LNS-SA using:
    - random removal
    - regret-2 insertion
    """

    random.seed(seed)

    current_solution = remove_empty_routes(
        copy.deepcopy(initial_solution)
    )
    current_distance = compute_solution_distance(
        current_solution,
        routing_distance,
    )

    best_solution = copy.deepcopy(current_solution)
    best_distance = current_distance
    best_iteration = 0

    temperature = initial_temperature
    accepted_moves = 0
    rejected_moves = 0
    records = []

    for iteration in range(n_iterations):
        partial_solution, removed_customers = random_removal(
            solution=current_solution,
            n_remove=n_remove,
            seed=seed + iteration,
        )

        candidate_solution = regret_2_insertion(
            partial_solution=partial_solution,
            removed_customers=removed_customers,
            demand=demand,
            vehicle_capacity=vehicle_capacity,
            routing_distance=routing_distance,
        )
        candidate_solution = remove_empty_routes(
            candidate_solution
        )

        candidate_distance = compute_solution_distance(
            candidate_solution,
            routing_distance,
        )

        accepted, acceptance_reason = accept_solution_sa(
            current_distance=current_distance,
            candidate_distance=candidate_distance,
            temperature=temperature,
        )

        if accepted:
            accepted_moves += 1
            current_solution = copy.deepcopy(candidate_solution)
            current_distance = candidate_distance

            if current_distance < best_distance:
                best_solution = copy.deepcopy(current_solution)
                best_distance = current_distance
                best_iteration = iteration + 1
        else:
            rejected_moves += 1

        records.append(
            {
                "iteration": iteration + 1,
                "operator_pair": "random_regret",
                "destroy_operator": "random_removal",
                "repair_operator": "regret_2_insertion",
                "removed_customers": removed_customers,
                "candidate_distance": candidate_distance,
                "current_distance": current_distance,
                "best_distance": best_distance,
                "temperature": temperature,
                "accepted": accepted,
                "acceptance_reason": acceptance_reason,
            }
        )

        temperature = max(
            temperature * cooling_rate,
            minimum_temperature,
        )

    summary = {
        "operator_pair": "random_regret",
        "destroy_operator": "random_removal",
        "repair_operator": "regret_2_insertion",
        "best_iteration": best_iteration,
        "accepted_moves": accepted_moves,
        "rejected_moves": rejected_moves,
        "records": records,
    }

    return (
        best_solution,
        best_distance,
        summary,
    )


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

    best_solution, best_distance, summary = run_lns_sa_random_regret(
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

    print("\nBest Distance:")
    print(best_distance)
    print("\nBest Solution:")
    print(best_solution)
    print("\nSummary:")
    print(
        {
            "operator_pair": summary["operator_pair"],
            "best_iteration": summary["best_iteration"],
            "accepted_moves": summary["accepted_moves"],
            "rejected_moves": summary["rejected_moves"],
        }
    )
