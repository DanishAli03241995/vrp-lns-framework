"""
LNS-SA engine for Worst Removal + Greedy Insertion.
"""

import copy
import math
import os
import random
import sys
import importlib


sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


worst_removal_module = importlib.import_module(
    "metaheuristics.destroy_operators.worst_removal"
)

greedy_insertion_module = importlib.import_module(
    "metaheuristics.repair_operators.greedy_insertion_v1"
)

worst_removal = worst_removal_module.worst_removal
greedy_insertion = greedy_insertion_module.greedy_insertion


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


def run_lns_sa_worst_greedy(
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
    worst_removal_randomness=0.2,
):
    """
    Run LNS-SA using:
    - worst removal
    - greedy insertion
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
        partial_solution, removed_customers = worst_removal(
            solution=current_solution,
            routing_distance=routing_distance,
            n_remove=n_remove,
            seed=seed + iteration,
            randomness=worst_removal_randomness,
        )

        candidate_solution = greedy_insertion(
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
                "operator_pair": "worst_greedy",
                "destroy_operator": "worst_removal",
                "repair_operator": "greedy_insertion",
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
        "operator_pair": "worst_greedy",
        "destroy_operator": "worst_removal",
        "repair_operator": "greedy_insertion",
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

    best_solution, best_distance, summary = run_lns_sa_worst_greedy(
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
