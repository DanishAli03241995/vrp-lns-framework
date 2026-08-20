"""
Time-aware LNS-SA engine for Shaw-style Related Removal + Regret-2 Insertion.

This engine is designed for the dispatch-wave timing variant after same-wave
split repair, specifically for the speed-40 sensitivity run.

It keeps the original Shaw-style Related Removal + Regret-2 Insertion idea, but makes the
repair step dispatch-wave aware by allowing only insertion positions that keep:
- vehicle capacity feasible;
- route structure valid;
- route goods ready before the assigned dispatch wave;
- route departure fixed to the dispatch wave bucket;
- route finish time within the working day.

Scope:
- depot-side dispatch-wave routes only;
- customers stay inside their existing dispatch-wave bucket;
- no movement to earlier/later waves;
- no adaptive operator weighting;
- no vehicle reuse scheduling;
- infeasible candidate solutions are rejected before SA acceptance.
"""

import copy
import importlib
import math
import os
import random
import sys


sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


shaw_removal_module = importlib.import_module(
    "metaheuristics.destroy_operators.shaw_removal"
)

shaw_removal = shaw_removal_module.shaw_removal


# =====================================================
# Basic route and solution helpers
# =====================================================


def remove_empty_routes(solution):
    """Keep only routes that serve at least one customer."""
    return [route for route in solution if len(route) > 2]


def compute_route_distance(route, routing_distance):
    """Compute distance of one route."""
    total_distance = 0

    for index in range(len(route) - 1):
        total_distance += routing_distance(route[index], route[index + 1])

    return total_distance


def compute_solution_distance(solution, routing_distance):
    """Compute total distance of a full solution."""
    total_distance = 0

    for route in solution:
        total_distance += compute_route_distance(route, routing_distance)

    return total_distance


def compute_route_load(route, demand):
    """Compute total load carried by one route."""
    route_load = 0

    for node in route:
        if node != 0:
            route_load += demand[node]

    return route_load


def compute_route_service_time_hours(route, service_time):
    """Compute service time on one route in hours."""
    total_service_time = 0

    for node in route[1:-1]:
        total_service_time += service_time[node] / 60

    return total_service_time


def compute_route_duration_hours(
    route,
    routing_distance,
    average_speed,
    service_time,
):
    """Compute route duration as travel time plus customer service time."""
    route_distance = compute_route_distance(route, routing_distance)
    travel_time_hours = route_distance / average_speed
    service_time_hours = compute_route_service_time_hours(route, service_time)

    return travel_time_hours + service_time_hours


def format_hour(hour_value):
    """Convert decimal hour, e.g. 9.5, to a readable HH:MM label."""
    if hour_value is None:
        return None

    total_minutes = int(round(hour_value * 60))
    hours = total_minutes // 60
    minutes = total_minutes % 60

    return f"{hours:02d}:{minutes:02d}"


def label_wave(wave_value):
    """Return a stable string key for a dispatch wave."""
    if wave_value is None:
        return "None"

    return format_hour(wave_value)


# =====================================================
# Dispatch-wave timing feasibility helpers
# =====================================================


def build_customer_ready_record(
    customer_id,
    supplier_arrival_times,
    goods_ready_times,
    customer_dispatch_waves,
):
    """Create a readable customer timing record for a route."""
    supplier_arrival_time = supplier_arrival_times.get(customer_id)
    goods_ready_time = goods_ready_times.get(customer_id)
    assigned_dispatch_wave = customer_dispatch_waves.get(customer_id)

    return {
        "customer_id": customer_id,
        "supplier_arrival_time": supplier_arrival_time,
        "supplier_arrival_time_label": format_hour(supplier_arrival_time),
        "goods_ready_time": goods_ready_time,
        "goods_ready_time_label": format_hour(goods_ready_time),
        "assigned_dispatch_wave": assigned_dispatch_wave,
        "assigned_dispatch_wave_label": format_hour(assigned_dispatch_wave),
    }


def get_route_goods_ready_time(route, goods_ready_times):
    """Return the latest goods-ready time among customers in one route."""
    customer_ready_times = []

    for customer_id in route[1:-1]:
        goods_ready_time = goods_ready_times.get(customer_id)

        if goods_ready_time is not None:
            customer_ready_times.append(goods_ready_time)

    if not customer_ready_times:
        return None

    return max(customer_ready_times)


def route_customers_match_dispatch_wave(route, constructed_dispatch_wave, customer_dispatch_waves):
    """Check that every customer belongs to the current wave bucket.

    The LNS is intentionally conservative: customers are improved inside their
    assigned dispatch-wave bucket and are not moved between waves.
    """
    for customer_id in route[1:-1]:
        assigned_wave = customer_dispatch_waves.get(customer_id)

        if assigned_wave != constructed_dispatch_wave:
            return False

    return True


def evaluate_dispatch_wave_route(
    route,
    route_id,
    constructed_dispatch_wave,
    demand,
    vehicle_capacity,
    routing_distance,
    average_speed,
    service_time,
    supplier_arrival_times,
    goods_ready_times,
    customer_dispatch_waves,
    dispatch_waves,
    working_day_end_time,
):
    """Evaluate one depot-origin route under dispatch-wave timing."""
    route_distance = compute_route_distance(route, routing_distance)
    route_load = compute_route_load(route, demand)
    route_duration = compute_route_duration_hours(
        route=route,
        routing_distance=routing_distance,
        average_speed=average_speed,
        service_time=service_time,
    )

    route_goods_ready_time = get_route_goods_ready_time(route, goods_ready_times)
    departure_wave = constructed_dispatch_wave
    finish_time = None

    if departure_wave is not None:
        finish_time = departure_wave + route_duration

    customer_ready_records = []

    for customer_id in route[1:-1]:
        customer_ready_records.append(
            build_customer_ready_record(
                customer_id=customer_id,
                supplier_arrival_times=supplier_arrival_times,
                goods_ready_times=goods_ready_times,
                customer_dispatch_waves=customer_dispatch_waves,
            )
        )

    structural_valid = len(route) >= 2 and route[0] == 0 and route[-1] == 0
    capacity_feasible = route_load <= vehicle_capacity
    dispatch_wave_feasible = constructed_dispatch_wave in dispatch_waves
    same_wave_feasible = route_customers_match_dispatch_wave(
        route=route,
        constructed_dispatch_wave=constructed_dispatch_wave,
        customer_dispatch_waves=customer_dispatch_waves,
    )
    route_ready_before_departure = (
        route_goods_ready_time is not None
        and constructed_dispatch_wave is not None
        and route_goods_ready_time <= constructed_dispatch_wave
    )
    working_day_feasible = (
        finish_time is not None
        and finish_time <= working_day_end_time
    )

    timing_feasible = (
        structural_valid
        and capacity_feasible
        and dispatch_wave_feasible
        and same_wave_feasible
        and route_ready_before_departure
        and working_day_feasible
    )

    waiting_time_hours = None

    if route_goods_ready_time is not None and departure_wave is not None:
        waiting_time_hours = departure_wave - route_goods_ready_time

    return {
        "route_id": route_id,
        "supplier_region_id": "global_depot_pool_by_dispatch_wave",
        "origin_type": "depot",
        "timing_model": "depot_dispatch_waves_speed40_lns",
        "route_construction_scope": "dispatch_wave_bucket_lns",
        "trip": route,
        "customers": route[1:-1],
        "n_customers": len(route) - 2,
        "route_load": route_load,
        "vehicle_capacity": vehicle_capacity,
        "route_utilization": route_load / vehicle_capacity if vehicle_capacity else None,
        "route_distance": route_distance,
        "route_duration_hours": route_duration,
        "route_travel_time_hours": route_distance / average_speed,
        "route_service_time_hours": compute_route_service_time_hours(route, service_time),
        "customer_ready_records": customer_ready_records,
        "route_goods_ready_time": route_goods_ready_time,
        "route_goods_ready_time_label": format_hour(route_goods_ready_time),
        "dispatch_waves": dispatch_waves,
        "dispatch_wave_labels": [format_hour(wave) for wave in dispatch_waves],
        "constructed_dispatch_wave": constructed_dispatch_wave,
        "constructed_dispatch_wave_label": format_hour(constructed_dispatch_wave),
        "departure_wave": departure_wave,
        "departure_wave_label": format_hour(departure_wave),
        "waiting_time_hours": waiting_time_hours,
        "waiting_time_minutes": (
            int(round(waiting_time_hours * 60))
            if waiting_time_hours is not None
            else None
        ),
        "finish_time": finish_time,
        "finish_time_label": format_hour(finish_time),
        "working_day_end_time": working_day_end_time,
        "working_day_end_time_label": format_hour(working_day_end_time),
        "capacity_feasible": capacity_feasible,
        "structural_validity": structural_valid,
        "dispatch_wave_feasible": dispatch_wave_feasible,
        "same_wave_feasible": same_wave_feasible,
        "route_ready_before_departure": route_ready_before_departure,
        "working_day_feasible": working_day_feasible,
        "timing_feasible": timing_feasible,
        "repair_model": "same_wave_duration_split_with_2opt_before_lns",
        "lns_model": "same_wave_random_regret_lns",
    }


def evaluate_dispatch_wave_solution(
    solution,
    constructed_dispatch_wave,
    demand,
    vehicle_capacity,
    routing_distance,
    average_speed,
    service_time,
    supplier_arrival_times,
    goods_ready_times,
    customer_dispatch_waves,
    dispatch_waves,
    working_day_end_time,
    start_route_id=1,
):
    """Evaluate all routes in one dispatch-wave bucket."""
    records = []
    non_empty_solution = remove_empty_routes(solution)

    for index, route in enumerate(non_empty_solution):
        records.append(
            evaluate_dispatch_wave_route(
                route=route,
                route_id=start_route_id + index,
                constructed_dispatch_wave=constructed_dispatch_wave,
                demand=demand,
                vehicle_capacity=vehicle_capacity,
                routing_distance=routing_distance,
                average_speed=average_speed,
                service_time=service_time,
                supplier_arrival_times=supplier_arrival_times,
                goods_ready_times=goods_ready_times,
                customer_dispatch_waves=customer_dispatch_waves,
                dispatch_waves=dispatch_waves,
                working_day_end_time=working_day_end_time,
            )
        )

    return records


def summarize_dispatch_wave_records(records):
    """Summarize route-level dispatch-wave timing records."""
    if not records:
        return {
            "timing_model": "depot_dispatch_waves_speed40_lns",
            "n_depot_timing_routes": 0,
            "n_depot_timing_feasible_routes": 0,
            "n_depot_timing_infeasible_routes": 0,
            "depot_timing_feasibility": True,
            "infeasible_timing_route_ids": [],
            "infeasible_timing_customers": [],
            "n_routes_without_feasible_wave": 0,
            "n_routes_departing_before_goods_ready": 0,
            "n_routes_exceeding_working_day": 0,
            "routes_per_wave": {},
            "routes_per_wave_label": {},
            "latest_depot_route_finish_time": None,
            "latest_depot_route_finish_time_label": None,
            "max_depot_route_duration_hours": 0,
            "avg_depot_route_duration_hours": 0,
            "avg_depot_route_utilization": 0,
            "avg_waiting_time_hours": 0,
            "max_waiting_time_hours": 0,
            "avg_waiting_time_minutes": 0,
            "max_waiting_time_minutes": 0,
        }

    feasible_records = []
    infeasible_records = []
    routes_per_wave = {}
    routes_per_wave_label = {}

    for record in records:
        if record["timing_feasible"]:
            feasible_records.append(record)
        else:
            infeasible_records.append(record)

        wave = record.get("constructed_dispatch_wave")
        wave_label = record.get("constructed_dispatch_wave_label")
        routes_per_wave[str(wave)] = routes_per_wave.get(str(wave), 0) + 1
        routes_per_wave_label[wave_label] = routes_per_wave_label.get(wave_label, 0) + 1

    latest_finish_values = [
        record["finish_time"]
        for record in records
        if record.get("finish_time") is not None
    ]
    route_durations = [record["route_duration_hours"] for record in records]
    route_utils = [record["route_utilization"] for record in records]
    waiting_times = [
        record["waiting_time_hours"]
        for record in records
        if record.get("waiting_time_hours") is not None
    ]

    latest_finish = max(latest_finish_values) if latest_finish_values else None
    max_duration = max(route_durations) if route_durations else 0
    avg_duration = sum(route_durations) / len(route_durations) if route_durations else 0
    avg_utilization = sum(route_utils) / len(route_utils) if route_utils else 0
    avg_waiting = sum(waiting_times) / len(waiting_times) if waiting_times else 0
    max_waiting = max(waiting_times) if waiting_times else 0

    infeasible_customers = sorted({
        customer_id
        for record in infeasible_records
        for customer_id in record["customers"]
    })

    routes_without_feasible_wave = [
        record for record in records
        if not record.get("dispatch_wave_feasible")
    ]
    routes_departing_before_ready = [
        record for record in records
        if not record.get("route_ready_before_departure")
    ]
    routes_exceeding_working_day = [
        record for record in records
        if not record.get("working_day_feasible")
    ]

    return {
        "timing_model": "depot_dispatch_waves_speed40_lns",
        "n_depot_timing_routes": len(records),
        "n_depot_timing_feasible_routes": len(feasible_records),
        "n_depot_timing_infeasible_routes": len(infeasible_records),
        "depot_timing_feasibility": len(infeasible_records) == 0,
        "infeasible_timing_route_ids": [
            record["route_id"] for record in infeasible_records
        ],
        "infeasible_timing_customers": infeasible_customers,
        "n_routes_without_feasible_wave": len(routes_without_feasible_wave),
        "n_routes_departing_before_goods_ready": len(routes_departing_before_ready),
        "n_routes_exceeding_working_day": len(routes_exceeding_working_day),
        "routes_per_wave": routes_per_wave,
        "routes_per_wave_label": routes_per_wave_label,
        "latest_depot_route_finish_time": latest_finish,
        "latest_depot_route_finish_time_label": format_hour(latest_finish),
        "max_depot_route_duration_hours": max_duration,
        "avg_depot_route_duration_hours": avg_duration,
        "avg_depot_route_utilization": avg_utilization,
        "avg_waiting_time_hours": avg_waiting,
        "max_waiting_time_hours": max_waiting,
        "avg_waiting_time_minutes": int(round(avg_waiting * 60)),
        "max_waiting_time_minutes": int(round(max_waiting * 60)),
    }


def collect_solution_customers(solution):
    """Return all non-depot customers in a solution, keeping duplicates."""
    customers = []

    for route in solution:
        for node in route:
            if node != 0:
                customers.append(node)

    return customers


def validate_solution_customer_coverage(solution, expected_customers):
    """Check that expected customers are served exactly once."""
    served_customers = collect_solution_customers(solution)
    served_set = set(served_customers)
    expected_set = set(expected_customers)

    duplicate_customers = sorted({
        customer_id
        for customer_id in served_customers
        if served_customers.count(customer_id) > 1
    })
    missing_customers = sorted(expected_set - served_set)
    extra_customers = sorted(served_set - expected_set)

    return {
        "all_customers_served_exactly_once": (
            len(duplicate_customers) == 0
            and len(missing_customers) == 0
            and len(extra_customers) == 0
        ),
        "n_expected_customers": len(expected_set),
        "n_served_customers": len(served_set),
        "duplicate_customers": duplicate_customers,
        "missing_customers": missing_customers,
        "extra_customers": extra_customers,
    }


def is_route_dispatch_wave_feasible(
    route,
    constructed_dispatch_wave,
    demand,
    vehicle_capacity,
    routing_distance,
    average_speed,
    service_time,
    supplier_arrival_times,
    goods_ready_times,
    customer_dispatch_waves,
    dispatch_waves,
    working_day_end_time,
):
    """Return True only if one route satisfies capacity and wave timing."""
    record = evaluate_dispatch_wave_route(
        route=route,
        route_id=1,
        constructed_dispatch_wave=constructed_dispatch_wave,
        demand=demand,
        vehicle_capacity=vehicle_capacity,
        routing_distance=routing_distance,
        average_speed=average_speed,
        service_time=service_time,
        supplier_arrival_times=supplier_arrival_times,
        goods_ready_times=goods_ready_times,
        customer_dispatch_waves=customer_dispatch_waves,
        dispatch_waves=dispatch_waves,
        working_day_end_time=working_day_end_time,
    )

    return record["timing_feasible"]


# =====================================================
# Dispatch-wave-aware regret-2 insertion
# =====================================================


def compute_insertion_cost(
    trip,
    customer,
    insert_position,
    routing_distance,
):
    """Compute incremental distance caused by inserting one customer."""
    previous_node = trip[insert_position - 1]
    next_node = trip[insert_position]

    added_cost = (
        routing_distance(previous_node, customer)
        + routing_distance(customer, next_node)
        - routing_distance(previous_node, next_node)
    )

    return added_cost


def create_single_customer_route(customer):
    """Create a new depot-customer-depot route."""
    return [0, customer, 0]


def find_time_feasible_insertions(
    solution,
    customer,
    constructed_dispatch_wave,
    demand,
    vehicle_capacity,
    routing_distance,
    average_speed,
    service_time,
    supplier_arrival_times,
    goods_ready_times,
    customer_dispatch_waves,
    dispatch_waves,
    working_day_end_time,
    allow_new_route=True,
):
    """Find all capacity- and wave-timing-feasible positions for one customer."""
    feasible_insertions = []
    customer_demand = demand[customer]

    if customer_dispatch_waves.get(customer) != constructed_dispatch_wave:
        return feasible_insertions

    for route_index, trip in enumerate(solution):
        current_route_load = compute_route_load(trip, demand)

        if current_route_load + customer_demand > vehicle_capacity:
            continue

        for insert_position in range(1, len(trip)):
            candidate_trip = (
                trip[:insert_position]
                + [customer]
                + trip[insert_position:]
            )

            if not is_route_dispatch_wave_feasible(
                route=candidate_trip,
                constructed_dispatch_wave=constructed_dispatch_wave,
                demand=demand,
                vehicle_capacity=vehicle_capacity,
                routing_distance=routing_distance,
                average_speed=average_speed,
                service_time=service_time,
                supplier_arrival_times=supplier_arrival_times,
                goods_ready_times=goods_ready_times,
                customer_dispatch_waves=customer_dispatch_waves,
                dispatch_waves=dispatch_waves,
                working_day_end_time=working_day_end_time,
            ):
                continue

            feasible_insertions.append({
                "route_index": route_index,
                "insert_position": insert_position,
                "insertion_cost": compute_insertion_cost(
                    trip=trip,
                    customer=customer,
                    insert_position=insert_position,
                    routing_distance=routing_distance,
                ),
                "creates_new_route": False,
            })

    if allow_new_route:
        new_route = create_single_customer_route(customer)

        if is_route_dispatch_wave_feasible(
            route=new_route,
            constructed_dispatch_wave=constructed_dispatch_wave,
            demand=demand,
            vehicle_capacity=vehicle_capacity,
            routing_distance=routing_distance,
            average_speed=average_speed,
            service_time=service_time,
            supplier_arrival_times=supplier_arrival_times,
            goods_ready_times=goods_ready_times,
            customer_dispatch_waves=customer_dispatch_waves,
            dispatch_waves=dispatch_waves,
            working_day_end_time=working_day_end_time,
        ):
            feasible_insertions.append({
                "route_index": None,
                "insert_position": None,
                "insertion_cost": compute_route_distance(
                    new_route,
                    routing_distance,
                ),
                "creates_new_route": True,
            })

    feasible_insertions.sort(key=lambda item: item["insertion_cost"])

    return feasible_insertions


def compute_regret_2_score(feasible_insertions):
    """Compute regret-2 score from sorted feasible insertion options."""
    best_insertion = feasible_insertions[0]
    best_cost = best_insertion["insertion_cost"]

    if len(feasible_insertions) >= 2:
        second_best_cost = feasible_insertions[1]["insertion_cost"]
    else:
        second_best_cost = best_cost

    regret_score = second_best_cost - best_cost

    return regret_score, best_insertion


def regret_2_insertion_dispatch_wave_timing(
    partial_solution,
    removed_customers,
    constructed_dispatch_wave,
    demand,
    vehicle_capacity,
    routing_distance,
    average_speed,
    service_time,
    supplier_arrival_times,
    goods_ready_times,
    customer_dispatch_waves,
    dispatch_waves,
    working_day_end_time,
):
    """Reinsert removed customers using dispatch-wave-aware regret-2 insertion."""
    working_solution = remove_empty_routes(copy.deepcopy(partial_solution))
    customers_to_insert = list(removed_customers)

    insertion_records = []
    created_new_routes = 0
    failed_customers = []

    while customers_to_insert:
        customer_scores = []

        for customer in customers_to_insert:
            feasible_insertions = find_time_feasible_insertions(
                solution=working_solution,
                customer=customer,
                constructed_dispatch_wave=constructed_dispatch_wave,
                demand=demand,
                vehicle_capacity=vehicle_capacity,
                routing_distance=routing_distance,
                average_speed=average_speed,
                service_time=service_time,
                supplier_arrival_times=supplier_arrival_times,
                goods_ready_times=goods_ready_times,
                customer_dispatch_waves=customer_dispatch_waves,
                dispatch_waves=dispatch_waves,
                working_day_end_time=working_day_end_time,
                allow_new_route=True,
            )

            if not feasible_insertions:
                customer_scores.append({
                    "customer": customer,
                    "regret_score": float("-inf"),
                    "best_insertion": None,
                    "n_feasible_insertions": 0,
                })
                continue

            regret_score, best_insertion = compute_regret_2_score(
                feasible_insertions
            )

            customer_scores.append({
                "customer": customer,
                "regret_score": regret_score,
                "best_insertion": best_insertion,
                "n_feasible_insertions": len(feasible_insertions),
            })

        feasible_customer_scores = [
            score
            for score in customer_scores
            if score["best_insertion"] is not None
        ]

        if not feasible_customer_scores:
            failed_customers = customers_to_insert.copy()
            break

        feasible_customer_scores.sort(
            key=lambda item: (
                item["regret_score"],
                -item["best_insertion"]["insertion_cost"],
            ),
            reverse=True,
        )

        selected = feasible_customer_scores[0]
        selected_customer = selected["customer"]
        best_insertion = selected["best_insertion"]

        if best_insertion["creates_new_route"]:
            working_solution.append(create_single_customer_route(selected_customer))
            created_new_routes += 1
        else:
            route_index = best_insertion["route_index"]
            insert_position = best_insertion["insert_position"]
            working_solution[route_index].insert(insert_position, selected_customer)

        insertion_records.append({
            "customer": selected_customer,
            "regret_score": selected["regret_score"],
            "n_feasible_insertions": selected["n_feasible_insertions"],
            "selected_insertion_cost": best_insertion["insertion_cost"],
            "selected_route_index": best_insertion["route_index"],
            "selected_insert_position": best_insertion["insert_position"],
            "created_new_route": best_insertion["creates_new_route"],
            "dispatch_wave": constructed_dispatch_wave,
            "dispatch_wave_label": format_hour(constructed_dispatch_wave),
        })

        customers_to_insert.remove(selected_customer)

    working_solution = remove_empty_routes(working_solution)

    return {
        "solution": working_solution,
        "all_customers_inserted": len(failed_customers) == 0,
        "failed_customers": failed_customers,
        "created_new_routes": created_new_routes,
        "insertion_records": insertion_records,
    }


# =====================================================
# Solution-level validation and SA acceptance
# =====================================================


def validate_dispatch_wave_solution(
    solution,
    expected_customers,
    constructed_dispatch_wave,
    demand,
    vehicle_capacity,
    routing_distance,
    average_speed,
    service_time,
    supplier_arrival_times,
    goods_ready_times,
    customer_dispatch_waves,
    dispatch_waves,
    working_day_end_time,
):
    """Validate customer coverage, capacity, goods-readiness, and wave timing."""
    records = evaluate_dispatch_wave_solution(
        solution=solution,
        constructed_dispatch_wave=constructed_dispatch_wave,
        demand=demand,
        vehicle_capacity=vehicle_capacity,
        routing_distance=routing_distance,
        average_speed=average_speed,
        service_time=service_time,
        supplier_arrival_times=supplier_arrival_times,
        goods_ready_times=goods_ready_times,
        customer_dispatch_waves=customer_dispatch_waves,
        dispatch_waves=dispatch_waves,
        working_day_end_time=working_day_end_time,
    )
    timing_summary = summarize_dispatch_wave_records(records)
    coverage_summary = validate_solution_customer_coverage(
        solution=solution,
        expected_customers=expected_customers,
    )

    solution_feasible = (
        timing_summary["depot_timing_feasibility"]
        and coverage_summary["all_customers_served_exactly_once"]
    )

    return {
        "solution_feasible": solution_feasible,
        "timing_records": records,
        "timing_summary": timing_summary,
        "coverage_summary": coverage_summary,
    }


def accept_solution_sa(
    current_distance,
    candidate_distance,
    temperature,
):
    """SA acceptance for feasible candidate solutions only."""
    if candidate_distance < current_distance:
        return True, "improved"

    delta = candidate_distance - current_distance

    if temperature <= 0:
        return False, "rejected"

    acceptance_probability = math.exp(-delta / temperature)

    if random.random() < acceptance_probability:
        return True, "accepted_worse"

    return False, "rejected"


# =====================================================
# Main dispatch-wave related + regret LNS-SA engine
# =====================================================


def run_lns_sa_related_regret_dispatch_wave_timing(
    initial_solution,
    constructed_dispatch_wave,
    customer_coordinates,
    demand,
    vehicle_capacity,
    routing_distance,
    average_speed,
    service_time,
    supplier_arrival_times,
    goods_ready_times,
    customer_dispatch_waves,
    dispatch_waves,
    working_day_end_time,
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
    """Run same-wave dispatch-aware LNS-SA using related removal and regret-2 insertion."""
    random.seed(seed)

    expected_customers = collect_solution_customers(initial_solution)

    current_solution = remove_empty_routes(copy.deepcopy(initial_solution))
    current_distance = compute_solution_distance(
        current_solution,
        routing_distance,
    )

    initial_validation = validate_dispatch_wave_solution(
        solution=current_solution,
        expected_customers=expected_customers,
        constructed_dispatch_wave=constructed_dispatch_wave,
        demand=demand,
        vehicle_capacity=vehicle_capacity,
        routing_distance=routing_distance,
        average_speed=average_speed,
        service_time=service_time,
        supplier_arrival_times=supplier_arrival_times,
        goods_ready_times=goods_ready_times,
        customer_dispatch_waves=customer_dispatch_waves,
        dispatch_waves=dispatch_waves,
        working_day_end_time=working_day_end_time,
    )

    if not initial_validation["solution_feasible"]:
        raise ValueError(
            "Initial dispatch-wave LNS solution is not feasible. "
            "Run wave-aware split repair before LNS, or verify speed40 inputs."
        )

    best_solution = copy.deepcopy(current_solution)
    best_distance = current_distance
    best_iteration = 0
    best_validation = copy.deepcopy(initial_validation)

    temperature = initial_temperature
    accepted_moves = 0
    rejected_moves = 0
    rejected_infeasible_moves = 0
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

        insertion_result = regret_2_insertion_dispatch_wave_timing(
            partial_solution=partial_solution,
            removed_customers=removed_customers,
            constructed_dispatch_wave=constructed_dispatch_wave,
            demand=demand,
            vehicle_capacity=vehicle_capacity,
            routing_distance=routing_distance,
            average_speed=average_speed,
            service_time=service_time,
            supplier_arrival_times=supplier_arrival_times,
            goods_ready_times=goods_ready_times,
            customer_dispatch_waves=customer_dispatch_waves,
            dispatch_waves=dispatch_waves,
            working_day_end_time=working_day_end_time,
        )

        candidate_solution = insertion_result["solution"]
        candidate_distance = compute_solution_distance(
            candidate_solution,
            routing_distance,
        )

        candidate_validation = validate_dispatch_wave_solution(
            solution=candidate_solution,
            expected_customers=expected_customers,
            constructed_dispatch_wave=constructed_dispatch_wave,
            demand=demand,
            vehicle_capacity=vehicle_capacity,
            routing_distance=routing_distance,
            average_speed=average_speed,
            service_time=service_time,
            supplier_arrival_times=supplier_arrival_times,
            goods_ready_times=goods_ready_times,
            customer_dispatch_waves=customer_dispatch_waves,
            dispatch_waves=dispatch_waves,
            working_day_end_time=working_day_end_time,
        )

        candidate_feasible = (
            insertion_result["all_customers_inserted"]
            and candidate_validation["solution_feasible"]
        )

        if not candidate_feasible:
            accepted = False
            acceptance_reason = "rejected_infeasible"
            rejected_moves += 1
            rejected_infeasible_moves += 1
        else:
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
                    best_validation = copy.deepcopy(candidate_validation)
            else:
                rejected_moves += 1

        records.append({
            "iteration": iteration + 1,
            "operator_pair": "related_regret_dispatch_wave_timing",
            "destroy_operator": "shaw_related_removal",
            "repair_operator": "regret_2_insertion_dispatch_wave_timing",
            "constructed_dispatch_wave": constructed_dispatch_wave,
            "constructed_dispatch_wave_label": format_hour(constructed_dispatch_wave),
            "removed_customers": removed_customers,
            "candidate_distance": candidate_distance,
            "current_distance": current_distance,
            "best_distance": best_distance,
            "temperature": temperature,
            "candidate_feasible": candidate_feasible,
            "candidate_timing_feasible": (
                candidate_validation["timing_summary"]["depot_timing_feasibility"]
            ),
            "candidate_customer_coverage_feasible": (
                candidate_validation["coverage_summary"][
                    "all_customers_served_exactly_once"
                ]
            ),
            "failed_customers": insertion_result["failed_customers"],
            "created_new_routes": insertion_result["created_new_routes"],
            "accepted": accepted,
            "acceptance_reason": acceptance_reason,
            "related_removal_randomness": related_removal_randomness,
            "distance_weight": distance_weight,
            "demand_weight": demand_weight,
            "route_weight": route_weight,
        })

        temperature = max(
            temperature * cooling_rate,
            minimum_temperature,
        )

    summary = {
        "operator_pair": "related_regret_dispatch_wave_timing",
        "destroy_operator": "shaw_related_removal",
        "repair_operator": "regret_2_insertion_dispatch_wave_timing",
        "timing_model": "depot_dispatch_waves_speed40_lns",
        "constructed_dispatch_wave": constructed_dispatch_wave,
        "constructed_dispatch_wave_label": format_hour(constructed_dispatch_wave),
        "best_iteration": best_iteration,
        "accepted_moves": accepted_moves,
        "rejected_moves": rejected_moves,
        "rejected_infeasible_moves": rejected_infeasible_moves,
        "related_removal_randomness": related_removal_randomness,
        "distance_weight": distance_weight,
        "demand_weight": demand_weight,
        "route_weight": route_weight,
        "initial_timing_summary": initial_validation["timing_summary"],
        "initial_coverage_summary": initial_validation["coverage_summary"],
        "best_timing_summary": best_validation["timing_summary"],
        "best_coverage_summary": best_validation["coverage_summary"],
        "best_timing_records": best_validation["timing_records"],
        "records": records,
    }

    return best_solution, best_distance, summary


if __name__ == "__main__":
    demo_solution = [
        [0, 1, 2, 0],
        [0, 3, 4, 0],
    ]
    demo_demand = {
        0: 0,
        1: 3,
        2: 3,
        3: 3,
        4: 3,
    }
    demo_service_time = {
        1: 10,
        2: 10,
        3: 10,
        4: 10,
    }
    demo_coords = {
        0: (0, 0),
        1: (1, 0),
        2: (2, 0),
        3: (0, 1),
        4: (0, 2),
    }
    demo_supplier_arrivals = {
        1: 8.0,
        2: 8.25,
        3: 8.0,
        4: 8.25,
    }
    demo_ready = {
        1: 8.5,
        2: 8.75,
        3: 8.5,
        4: 8.75,
    }
    demo_waves = {
        1: 9.0,
        2: 9.0,
        3: 9.0,
        4: 9.0,
    }

    def demo_distance(i, j):
        x1, y1 = demo_coords[i]
        x2, y2 = demo_coords[j]
        return ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5

    best, distance, run_summary = run_lns_sa_related_regret_dispatch_wave_timing(
        initial_solution=demo_solution,
        constructed_dispatch_wave=9.0,
        customer_coordinates=demo_coords,
        demand=demo_demand,
        vehicle_capacity=6,
        routing_distance=demo_distance,
        average_speed=40,
        service_time=demo_service_time,
        supplier_arrival_times=demo_supplier_arrivals,
        goods_ready_times=demo_ready,
        customer_dispatch_waves=demo_waves,
        dispatch_waves=[9.0, 11.0, 13.0, 15.0],
        working_day_end_time=18.0,
        n_iterations=5,
        n_remove=2,
        seed=42,
    )

    print("Best solution:", best)
    print("Best distance:", distance)
    print("Summary:", {
        "accepted_moves": run_summary["accepted_moves"],
        "rejected_moves": run_summary["rejected_moves"],
        "best_iteration": run_summary["best_iteration"],
    })
