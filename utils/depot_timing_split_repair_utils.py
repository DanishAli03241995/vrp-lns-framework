"""Depot timing utilities with fixed-time route split repair.

This module extends the fixed depot-ready timing evaluation with a simple
repair layer for infeasible depot-origin routes.

Scope of this version:
- depot-bound goods are assumed to be available at one fixed time;
- every depot route departs at that fixed time;
- infeasible depot routes are repaired by a close-to-half split;
- each split route is improved with 2-opt and re-evaluated;
- the split is accepted only if all split routes are timing-feasible;
- dispatch waves, random supplier arrivals, and LNS are not included here.
"""


def format_hour(hour_value):
    """Convert a decimal hour value, e.g. 9.5, into '09:30'."""
    if hour_value is None:
        return None

    total_minutes = int(round(hour_value * 60))
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours:02d}:{minutes:02d}"


def calculate_route_distance(route, euc_distance):
    """Calculate route distance using the supplied distance function."""
    total_distance = 0

    for index in range(len(route) - 1):
        total_distance += euc_distance(route[index], route[index + 1])

    return total_distance


def calculate_total_distance(routes, euc_distance):
    """Calculate total distance over a list of routes."""
    return sum(calculate_route_distance(route, euc_distance) for route in routes)


def calculate_route_load(route, demand):
    """Calculate total demand carried on a route."""
    return sum(demand[customer_id] for customer_id in route if customer_id != 0)


def calculate_route_service_time_hours(route, service_time):
    """Calculate total customer service time on a route in hours."""
    total_service_time = 0

    for customer_id in route[1:-1]:
        total_service_time += service_time[customer_id] / 60

    return total_service_time


def calculate_route_duration_hours(route, euc_distance, average_speed, service_time):
    """Calculate route duration as travel time plus customer service time."""
    route_distance = calculate_route_distance(route, euc_distance)
    travel_time = route_distance / average_speed
    service_time_hours = calculate_route_service_time_hours(route, service_time)

    return travel_time + service_time_hours


def evaluate_fixed_depot_route(
    route,
    route_id,
    supplier_region_id,
    demand,
    vehicle_capacity,
    euc_distance,
    average_speed,
    service_time,
    fixed_depot_ready_time,
    working_day_end_time,
):
    """Evaluate one depot route under a fixed depot-ready time assumption."""
    route_distance = calculate_route_distance(route, euc_distance)
    route_load = calculate_route_load(route, demand)
    route_duration = calculate_route_duration_hours(
        route,
        euc_distance,
        average_speed,
        service_time,
    )

    departure_time = fixed_depot_ready_time
    finish_time = departure_time + route_duration

    capacity_feasible = route_load <= vehicle_capacity
    structural_valid = len(route) >= 2 and route[0] == 0 and route[-1] == 0
    working_day_feasible = finish_time <= working_day_end_time
    timing_feasible = capacity_feasible and structural_valid and working_day_feasible

    return {
        "route_id": route_id,
        "supplier_region_id": supplier_region_id,
        "origin_type": "depot",
        "timing_model": "fixed_depot_ready_time",
        "trip": route,
        "customers": route[1:-1],
        "n_customers": len(route) - 2,
        "route_load": route_load,
        "vehicle_capacity": vehicle_capacity,
        "route_utilization": route_load / vehicle_capacity if vehicle_capacity else None,
        "route_distance": route_distance,
        "route_duration_hours": route_duration,
        "route_travel_time_hours": route_distance / average_speed,
        "route_service_time_hours": calculate_route_service_time_hours(
            route,
            service_time,
        ),
        "fixed_depot_ready_time": fixed_depot_ready_time,
        "fixed_depot_ready_time_label": format_hour(fixed_depot_ready_time),
        "departure_time": departure_time,
        "departure_time_label": format_hour(departure_time),
        "finish_time": finish_time,
        "finish_time_label": format_hour(finish_time),
        "working_day_end_time": working_day_end_time,
        "working_day_end_time_label": format_hour(working_day_end_time),
        "capacity_feasible": capacity_feasible,
        "structural_validity": structural_valid,
        "working_day_feasible": working_day_feasible,
        "timing_feasible": timing_feasible,
    }


def evaluate_fixed_depot_routes(
    routes,
    demand,
    vehicle_capacity,
    euc_distance,
    average_speed,
    service_time,
    fixed_depot_ready_time,
    working_day_end_time,
    supplier_region_id=None,
    start_route_id=1,
):
    """Evaluate a list of depot routes under fixed depot-ready timing."""
    records = []
    non_empty_routes = [
        route
        for route in routes
        if len([customer_id for customer_id in route if customer_id != 0]) > 0
    ]

    for index, route in enumerate(non_empty_routes):
        records.append(
            evaluate_fixed_depot_route(
                route=route,
                route_id=start_route_id + index,
                supplier_region_id=supplier_region_id,
                demand=demand,
                vehicle_capacity=vehicle_capacity,
                euc_distance=euc_distance,
                average_speed=average_speed,
                service_time=service_time,
                fixed_depot_ready_time=fixed_depot_ready_time,
                working_day_end_time=working_day_end_time,
            )
        )

    return records


def summarize_fixed_depot_timing(records):
    """Create summary metrics from route-level fixed timing records."""
    if not records:
        return {
            "timing_model": "fixed_depot_ready_time",
            "n_depot_timing_routes": 0,
            "n_depot_timing_feasible_routes": 0,
            "n_depot_timing_infeasible_routes": 0,
            "depot_timing_feasibility": True,
            "infeasible_timing_route_ids": [],
            "infeasible_timing_customers": [],
            "latest_depot_route_finish_time": None,
            "latest_depot_route_finish_time_label": None,
            "max_depot_route_duration_hours": 0,
            "avg_depot_route_duration_hours": 0,
            "avg_depot_route_utilization": 0,
        }

    feasible_records = [record for record in records if record["timing_feasible"]]
    infeasible_records = [record for record in records if not record["timing_feasible"]]

    latest_finish = max(record["finish_time"] for record in records)
    max_duration = max(record["route_duration_hours"] for record in records)
    avg_duration = (
        sum(record["route_duration_hours"] for record in records) / len(records)
    )
    avg_utilization = (
        sum(record["route_utilization"] for record in records) / len(records)
    )

    infeasible_customers = sorted({
        customer_id
        for record in infeasible_records
        for customer_id in record["customers"]
    })

    return {
        "timing_model": "fixed_depot_ready_time",
        "n_depot_timing_routes": len(records),
        "n_depot_timing_feasible_routes": len(feasible_records),
        "n_depot_timing_infeasible_routes": len(infeasible_records),
        "depot_timing_feasibility": len(infeasible_records) == 0,
        "infeasible_timing_route_ids": [
            record["route_id"] for record in infeasible_records
        ],
        "infeasible_timing_customers": infeasible_customers,
        "latest_depot_route_finish_time": latest_finish,
        "latest_depot_route_finish_time_label": format_hour(latest_finish),
        "max_depot_route_duration_hours": max_duration,
        "avg_depot_route_duration_hours": avg_duration,
        "avg_depot_route_utilization": avg_utilization,
    }


def improve_route_2opt(route, euc_distance):
    """Run a simple 2-opt improvement on one route."""
    if len(route) <= 4:
        return route.copy()

    current_route = route.copy()

    while True:
        improved = False
        best_route = current_route
        best_distance = calculate_route_distance(current_route, euc_distance)

        for i in range(len(current_route) - 3):
            for j in range(i + 2, len(current_route) - 1):
                candidate_route = (
                    current_route[: i + 1]
                    + current_route[i + 1 : j + 1][::-1]
                    + current_route[j + 1 :]
                )
                candidate_distance = calculate_route_distance(
                    candidate_route,
                    euc_distance,
                )

                if candidate_distance < best_distance:
                    improved = True
                    best_route = candidate_route
                    best_distance = candidate_distance

        if not improved:
            break

        current_route = best_route

    return current_route


def optimize_split_routes(split_routes, euc_distance):
    """Apply 2-opt to each split route."""
    return [improve_route_2opt(route, euc_distance) for route in split_routes]


def split_route_by_index(route, split_index):
    """Split route customers at split_index and add depot at both ends."""
    customers = route[1:-1]

    first_customers = customers[:split_index]
    second_customers = customers[split_index:]

    return [0] + first_customers + [0], [0] + second_customers + [0]


def build_half_split_candidates(
    route,
    demand,
    vehicle_capacity,
    euc_distance,
    average_speed,
    service_time,
    fixed_depot_ready_time,
    working_day_end_time,
    supplier_region_id,
):
    """Generate and score possible close-to-half splits for a route.

    The split is attempted along the current route sequence. Each candidate is
    improved with 2-opt and evaluated from scratch. Feasible candidates are
    preferred. Among feasible candidates, the best candidate is the one with the
    lowest maximum route duration, then the best duration balance, then the
    lowest total distance.
    """
    customers = route[1:-1]

    if len(customers) < 2:
        return []

    candidates = []

    for split_index in range(1, len(customers)):
        split_routes = split_route_by_index(route, split_index)
        optimized_routes = optimize_split_routes(split_routes, euc_distance)
        split_records = evaluate_fixed_depot_routes(
            routes=optimized_routes,
            demand=demand,
            vehicle_capacity=vehicle_capacity,
            euc_distance=euc_distance,
            average_speed=average_speed,
            service_time=service_time,
            fixed_depot_ready_time=fixed_depot_ready_time,
            working_day_end_time=working_day_end_time,
            supplier_region_id=supplier_region_id,
            start_route_id=1,
        )

        durations = [record["route_duration_hours"] for record in split_records]
        distances = [record["route_distance"] for record in split_records]
        loads = [record["route_load"] for record in split_records]
        customer_counts = [record["n_customers"] for record in split_records]

        all_feasible = all(record["timing_feasible"] for record in split_records)
        max_duration = max(durations)
        duration_imbalance = abs(durations[0] - durations[1])
        load_imbalance = abs(loads[0] - loads[1])
        customer_count_imbalance = abs(customer_counts[0] - customer_counts[1])
        total_distance = sum(distances)
        latest_finish = max(record["finish_time"] for record in split_records)
        max_lateness = max(
            max(0, record["finish_time"] - working_day_end_time)
            for record in split_records
        )

        candidates.append({
            "split_index": split_index,
            "split_routes": optimized_routes,
            "split_records": split_records,
            "all_feasible": all_feasible,
            "total_distance": total_distance,
            "max_duration": max_duration,
            "duration_imbalance": duration_imbalance,
            "load_imbalance": load_imbalance,
            "customer_count_imbalance": customer_count_imbalance,
            "latest_finish": latest_finish,
            "max_lateness": max_lateness,
        })

    return candidates


def choose_best_half_split_candidate(candidates):
    """Choose the best split candidate from generated candidates."""
    if not candidates:
        return None

    feasible_candidates = [candidate for candidate in candidates if candidate["all_feasible"]]

    if feasible_candidates:
        return min(
            feasible_candidates,
            key=lambda candidate: (
                candidate["max_duration"],
                candidate["duration_imbalance"],
                candidate["total_distance"],
            ),
        )

    return min(
        candidates,
        key=lambda candidate: (
            candidate["max_lateness"],
            candidate["max_duration"],
            candidate["duration_imbalance"],
            candidate["total_distance"],
        ),
    )


def repair_infeasible_fixed_depot_routes_by_half_split(
    routes,
    demand,
    vehicle_capacity,
    euc_distance,
    average_speed,
    service_time,
    fixed_depot_ready_time,
    working_day_end_time,
    supplier_region_id="global_depot_pool",
):
    """Repair infeasible fixed-time depot routes using close-to-half split.

    Feasible routes are retained unchanged. Each infeasible route is split into
    two candidate routes using all possible split positions along the route
    sequence. The chosen split is accepted only if both split routes are timing
    feasible. If no feasible split exists, the original infeasible route is kept
    and marked as unresolved in the repair log.
    """
    pre_repair_records = evaluate_fixed_depot_routes(
        routes=routes,
        demand=demand,
        vehicle_capacity=vehicle_capacity,
        euc_distance=euc_distance,
        average_speed=average_speed,
        service_time=service_time,
        fixed_depot_ready_time=fixed_depot_ready_time,
        working_day_end_time=working_day_end_time,
        supplier_region_id=supplier_region_id,
        start_route_id=1,
    )

    repaired_routes = []
    repair_records = []

    for record in pre_repair_records:
        original_route = record["trip"]

        if record["timing_feasible"]:
            repaired_routes.append(original_route)
            repair_records.append({
                "original_route_id": record["route_id"],
                "repair_attempted": False,
                "repair_successful": False,
                "reason": "route_already_feasible",
                "original_trip": original_route,
                "final_trips": [original_route],
                "original_distance": record["route_distance"],
                "final_distance": record["route_distance"],
                "distance_delta": 0,
                "original_finish_time": record["finish_time"],
                "original_finish_time_label": record["finish_time_label"],
                "final_latest_finish_time": record["finish_time"],
                "final_latest_finish_time_label": record["finish_time_label"],
            })
            continue

        candidates = build_half_split_candidates(
            route=original_route,
            demand=demand,
            vehicle_capacity=vehicle_capacity,
            euc_distance=euc_distance,
            average_speed=average_speed,
            service_time=service_time,
            fixed_depot_ready_time=fixed_depot_ready_time,
            working_day_end_time=working_day_end_time,
            supplier_region_id=supplier_region_id,
        )
        best_candidate = choose_best_half_split_candidate(candidates)

        if best_candidate is not None and best_candidate["all_feasible"]:
            repaired_routes.extend(best_candidate["split_routes"])
            final_distance = best_candidate["total_distance"]
            repair_records.append({
                "original_route_id": record["route_id"],
                "repair_attempted": True,
                "repair_successful": True,
                "repair_method": "close_to_half_split_with_2opt",
                "split_index": best_candidate["split_index"],
                "original_trip": original_route,
                "final_trips": best_candidate["split_routes"],
                "original_customers": record["customers"],
                "final_customers_by_trip": [
                    split_record["customers"]
                    for split_record in best_candidate["split_records"]
                ],
                "original_distance": record["route_distance"],
                "final_distance": final_distance,
                "distance_delta": final_distance - record["route_distance"],
                "original_duration_hours": record["route_duration_hours"],
                "final_route_durations_hours": [
                    split_record["route_duration_hours"]
                    for split_record in best_candidate["split_records"]
                ],
                "original_finish_time": record["finish_time"],
                "original_finish_time_label": record["finish_time_label"],
                "final_latest_finish_time": best_candidate["latest_finish"],
                "final_latest_finish_time_label": format_hour(best_candidate["latest_finish"]),
                "working_day_end_time": working_day_end_time,
                "working_day_end_time_label": format_hour(working_day_end_time),
            })
            continue

        repaired_routes.append(original_route)
        reason = "no_split_candidate_available"
        if best_candidate is not None:
            reason = "no_feasible_half_split_found"

        repair_records.append({
            "original_route_id": record["route_id"],
            "repair_attempted": True,
            "repair_successful": False,
            "repair_method": "close_to_half_split_with_2opt",
            "reason": reason,
            "original_trip": original_route,
            "final_trips": [original_route],
            "original_customers": record["customers"],
            "original_distance": record["route_distance"],
            "final_distance": record["route_distance"],
            "distance_delta": 0,
            "original_duration_hours": record["route_duration_hours"],
            "original_finish_time": record["finish_time"],
            "original_finish_time_label": record["finish_time_label"],
            "working_day_end_time": working_day_end_time,
            "working_day_end_time_label": format_hour(working_day_end_time),
            "best_candidate": best_candidate,
        })

    post_repair_records = evaluate_fixed_depot_routes(
        routes=repaired_routes,
        demand=demand,
        vehicle_capacity=vehicle_capacity,
        euc_distance=euc_distance,
        average_speed=average_speed,
        service_time=service_time,
        fixed_depot_ready_time=fixed_depot_ready_time,
        working_day_end_time=working_day_end_time,
        supplier_region_id=supplier_region_id,
        start_route_id=1,
    )

    repair_summary = summarize_fixed_depot_repair(
        pre_repair_records,
        post_repair_records,
        repair_records,
    )

    return {
        "routes_before_repair": routes,
        "routes_after_repair": repaired_routes,
        "pre_repair_records": pre_repair_records,
        "post_repair_records": post_repair_records,
        "repair_records": repair_records,
        "repair_summary": repair_summary,
    }


def summarize_fixed_depot_repair(pre_repair_records, post_repair_records, repair_records):
    """Summarize the fixed-time split repair step."""
    pre_summary = summarize_fixed_depot_timing(pre_repair_records)
    post_summary = summarize_fixed_depot_timing(post_repair_records)

    attempted_records = [record for record in repair_records if record["repair_attempted"]]
    successful_records = [record for record in repair_records if record["repair_successful"]]
    unresolved_records = [
        record
        for record in repair_records
        if record["repair_attempted"] and not record["repair_successful"]
    ]

    distance_before = calculate_records_distance(pre_repair_records)
    distance_after = calculate_records_distance(post_repair_records)

    return {
        "repair_model": "fixed_depot_half_split_repair",
        "n_routes_before_repair": len(pre_repair_records),
        "n_routes_after_repair": len(post_repair_records),
        "n_infeasible_routes_before_repair": pre_summary[
            "n_depot_timing_infeasible_routes"
        ],
        "n_infeasible_routes_after_repair": post_summary[
            "n_depot_timing_infeasible_routes"
        ],
        "n_repair_attempts": len(attempted_records),
        "n_successful_repairs": len(successful_records),
        "n_unresolved_repairs": len(unresolved_records),
        "distance_before_repair": distance_before,
        "distance_after_repair": distance_after,
        "distance_delta_after_repair": distance_after - distance_before,
        "latest_finish_before_repair": pre_summary[
            "latest_depot_route_finish_time"
        ],
        "latest_finish_before_repair_label": pre_summary[
            "latest_depot_route_finish_time_label"
        ],
        "latest_finish_after_repair": post_summary[
            "latest_depot_route_finish_time"
        ],
        "latest_finish_after_repair_label": post_summary[
            "latest_depot_route_finish_time_label"
        ],
        "depot_timing_feasible_before_repair": pre_summary[
            "depot_timing_feasibility"
        ],
        "depot_timing_feasible_after_repair": post_summary[
            "depot_timing_feasibility"
        ],
        "unresolved_infeasible_route_ids": [
            record["original_route_id"] for record in unresolved_records
        ],
    }


def calculate_records_distance(records):
    """Calculate total route distance from timing records."""
    return sum(record["route_distance"] for record in records)
