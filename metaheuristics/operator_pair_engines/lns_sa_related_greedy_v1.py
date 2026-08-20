"""
LNS-SA engine for Shaw-style Related Removal + Greedy Insertion.
"""

import copy
import math
import os
import random
import sys
import importlib


sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


shaw_removal_module = importlib.import_module(
    "metaheuristics.destroy_operators.shaw_removal"
)

greedy_insertion_module = importlib.import_module(
    "metaheuristics.repair_operators.greedy_insertion_v1"
)

shaw_removal = shaw_removal_module.shaw_removal
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


def run_lns_sa_related_greedy(
    initial_solution,
    customer_coordinates,
    demand,
    vehicle_capacity,
    routing_distance,
    n_iterations=20,
    n_remove=3,
    seed=42,
    initial_temperature=10.0,
    cooling_rate=0.95,
    minimum_temperature=0.01,
    related_removal_randomness=0.2,
    distance_weight=1.0,
    demand_weight=0.2,
    route_weight=1.0,
):
    """
    Run LNS-SA using:
    - Shaw-style related removal
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
        partial_solution, removed_customers = shaw_removal(
            solution=current_solution,
            customer_coordinates=customer_coordinates,
            demand=demand,
            n_remove=n_remove,
            seed=seed + iteration,
            randomness=related_removal_randomness,
            distance_weight=distance_weight,
            demand_weight=demand_weight,
            route_weight=route_weight,
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
                "operator_pair": "related_greedy",
                "destroy_operator": "shaw_related_removal",
                "repair_operator": "greedy_insertion",
                "removed_customers": removed_customers,
                "candidate_distance": candidate_distance,
                "current_distance": current_distance,
                "best_distance": best_distance,
                "temperature": temperature,
                "accepted": accepted,
                "acceptance_reason": acceptance_reason,
                "related_removal_randomness": related_removal_randomness,
                "distance_weight": distance_weight,
                "demand_weight": demand_weight,
                "route_weight": route_weight,
            }
        )

        temperature = max(
            temperature * cooling_rate,
            minimum_temperature,
        )

    summary = {
        "operator_pair": "related_greedy",
        "destroy_operator": "shaw_related_removal",
        "repair_operator": "greedy_insertion",
        "best_iteration": best_iteration,
        "accepted_moves": accepted_moves,
        "rejected_moves": rejected_moves,
        "related_removal_randomness": related_removal_randomness,
        "distance_weight": distance_weight,
        "demand_weight": demand_weight,
        "route_weight": route_weight,
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

    best_solution, best_distance, summary = run_lns_sa_related_greedy(
        initial_solution=initial_solution,
        customer_coordinates=coords,
        demand=demand,
        vehicle_capacity=vehicle_capacity,
        routing_distance=routing_distance,
        n_iterations=20,
        n_remove=3,
        seed=42,
        initial_temperature=10.0,
        cooling_rate=0.95,
        minimum_temperature=0.01,
        related_removal_randomness=0.2,
        distance_weight=1.0,
        demand_weight=0.2,
        route_weight=1.0,
    )

    print("\nBest Distance:")
    print(best_distance)
    print("\nBest Solution:")
    print(best_solution)
    print("\nSummary:")
    print(
        {
            "operator_pair": summary["operator_pair"],
            "destroy_operator": summary["destroy_operator"],
            "repair_operator": summary["repair_operator"],
            "best_iteration": summary["best_iteration"],
            "accepted_moves": summary["accepted_moves"],
            "rejected_moves": summary["rejected_moves"],
            "distance_weight": summary["distance_weight"],
            "demand_weight": summary["demand_weight"],
            "route_weight": summary["route_weight"],
        }
    )
