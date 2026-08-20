"""Depot dispatch-wave utilities with duration-based split repair.

This module extends the wave-aware depot dispatch construction utilities with a
simple repair layer for depot routes that cannot finish before the working-day
end.

Scope of this version:
- depot customers are first assigned to dispatch-wave buckets by goods-ready
  time;
- routes are constructed inside those wave buckets;
- infeasible routes are repaired by splitting them into smaller same-wave
  routes;
- each split route is cleaned with 2-opt and re-evaluated;
- the split is accepted as successful only when all resulting routes satisfy
  capacity, goods-readiness, dispatch-wave, and working-day feasibility;
- customers are not moved to another dispatch wave in this repair stage;
- vehicle reuse and LNS are not included here.
"""

from utils import depot_timing_wave_constructed_utils as base_utils


# ---------------------------------------------------------------------------
# Re-export the base wave-construction helpers so the experiment file can use
# this module as a drop-in replacement for depot_timing_wave_constructed_utils.
# ---------------------------------------------------------------------------

format_hour = base_utils.format_hour
round_hour_to_step = base_utils.round_hour_to_step
calculate_route_distance = base_utils.calculate_route_distance
calculate_total_distance = base_utils.calculate_total_distance
calculate_route_load = base_utils.calculate_route_load
calculate_route_service_time_hours = base_utils.calculate_route_service_time_hours
calculate_route_duration_hours = base_utils.calculate_route_duration_hours
choose_earliest_dispatch_wave = base_utils.choose_earliest_dispatch_wave
generate_depot_customer_wave_times = base_utils.generate_depot_customer_wave_times
group_customer_records_by_dispatch_wave = base_utils.group_customer_records_by_dispatch_wave
summarize_customer_wave_assignment = base_utils.summarize_customer_wave_assignment
get_route_goods_ready_time = base_utils.get_route_goods_ready_time
build_route_customer_ready_records = base_utils.build_route_customer_ready_records
evaluate_wave_constructed_route = base_utils.evaluate_wave_constructed_route
evaluate_wave_constructed_routes = base_utils.evaluate_wave_constructed_routes
base_summarize_dispatch_wave_timing = base_utils.summarize_dispatch_wave_timing


def summarize_dispatch_wave_timing(records):
    """Summarize final dispatch-wave timing records after split repair."""
    summary = base_summarize_dispatch_wave_timing(records)
    summary["timing_model"] = (
        "depot_dispatch_waves_wave_constructed_with_duration_split_repair"
    )
    return summary


def build_route_from_customers(customers):
    """Create a depot-origin route from an ordered customer list."""
    route = [0]

    for customer_id in customers:
        route.append(customer_id)

    route.append(0)
    return route


def improve_route_2opt(route, euc_distance):
    """Run a readable 2-opt cleanup on one route."""
    if len(route) <= 4:
        return route.copy()

    current_route = route.copy()

    while True:
        improved = False
        best_route = current_route.copy()
        best_distance = calculate_route_distance(current_route, euc_distance)

        first_index = 0

        while first_index < len(current_route) - 3:
            second_index = first_index + 2

            while second_index < len(current_route) - 1:
                route_before_reversed_part = current_route[: first_index + 1]
                route_part_to_reverse = current_route[first_index + 1 : second_index + 1]
                route_after_reversed_part = current_route[second_index + 1 :]

                candidate_route = []
                candidate_route.extend(route_before_reversed_part)
                candidate_route.extend(list(reversed(route_part_to_reverse)))
                candidate_route.extend(route_after_reversed_part)

                candidate_distance = calculate_route_distance(
                    candidate_route,
                    euc_distance,
                )

                if candidate_distance < best_distance:
                    improved = True
                    best_route = candidate_route
                    best_distance = candidate_distance

                second_index += 1

            first_index += 1

        if not improved:
            break

        current_route = best_route

    return current_route


def optimize_routes_with_2opt(routes, euc_distance):
    """Apply 2-opt cleanup to each route in a list."""
    optimized_routes = []

    for route in routes:
        optimized_route = improve_route_2opt(route, euc_distance)
        optimized_routes.append(optimized_route)

    return optimized_routes


def split_route_by_index(route, split_index):
    """Split route customers at split_index and add depot at both ends."""
    customers = route[1:-1]

    first_customers = customers[:split_index]
    second_customers = customers[split_index:]

    first_route = build_route_from_customers(first_customers)
    second_route = build_route_from_customers(second_customers)

    return first_route, second_route


def calculate_available_time_after_wave(constructed_dispatch_wave, working_day_end_time):
    """Calculate the route-duration limit for a dispatch wave."""
    if constructed_dispatch_wave is None:
        return None

    return working_day_end_time - constructed_dispatch_wave


def calculate_record_lateness(record, working_day_end_time):
    """Return how many hours a record exceeds the working-day end by."""
    finish_time = record.get("finish_time")

    if finish_time is None:
        return None

    lateness = finish_time - working_day_end_time

    if lateness < 0:
        lateness = 0

    return lateness


def calculate_max_lateness(records, working_day_end_time):
    """Calculate maximum positive lateness over route records."""
    max_lateness = 0

    for record in records:
        record_lateness = calculate_record_lateness(record, working_day_end_time)

        if record_lateness is None:
            record_lateness = working_day_end_time

        if record_lateness > max_lateness:
            max_lateness = record_lateness

    return max_lateness


def calculate_total_record_distance(records):
    """Calculate total route distance from route-level records."""
    total_distance = 0

    for record in records:
        total_distance += record["route_distance"]

    return total_distance


def collect_unresolved_customers(records):
    """Collect customers from timing-infeasible records."""
    unresolved_customers = set()

    for record in records:
        if record["timing_feasible"]:
            continue

        for customer_id in record["customers"]:
            unresolved_customers.add(customer_id)

    return sorted(unresolved_customers)


def evaluate_candidate_routes(
    routes,
    constructed_dispatch_wave,
    demand,
    vehicle_capacity,
    euc_distance,
    average_speed,
    service_time,
    supplier_arrival_times,
    goods_ready_times,
    customer_dispatch_waves,
    dispatch_waves,
    working_day_end_time,
    supplier_region_id,
):
    """Evaluate candidate routes under the same dispatch wave."""
    return evaluate_wave_constructed_routes(
        routes=routes,
        constructed_dispatch_wave=constructed_dispatch_wave,
        demand=demand,
        vehicle_capacity=vehicle_capacity,
        euc_distance=euc_distance,
        average_speed=average_speed,
        service_time=service_time,
        supplier_arrival_times=supplier_arrival_times,
        goods_ready_times=goods_ready_times,
        customer_dispatch_waves=customer_dispatch_waves,
        dispatch_waves=dispatch_waves,
        working_day_end_time=working_day_end_time,
        supplier_region_id=supplier_region_id,
        start_route_id=1,
    )


def build_duration_split_candidates(
    route,
    constructed_dispatch_wave,
    demand,
    vehicle_capacity,
    euc_distance,
    average_speed,
    service_time,
    supplier_arrival_times,
    goods_ready_times,
    customer_dispatch_waves,
    dispatch_waves,
    working_day_end_time,
    supplier_region_id,
):
    """Generate and score all two-way splits of one route.

    The split is attempted along the current route sequence. Each candidate is
    cleaned with 2-opt and re-evaluated under the same dispatch wave.
    """
    customers = route[1:-1]

    if len(customers) < 2:
        return []

    candidates = []

    split_index = 1

    while split_index < len(customers):
        first_route, second_route = split_route_by_index(route, split_index)
        split_routes = [first_route, second_route]
        optimized_routes = optimize_routes_with_2opt(split_routes, euc_distance)

        split_records = evaluate_candidate_routes(
            routes=optimized_routes,
            constructed_dispatch_wave=constructed_dispatch_wave,
            demand=demand,
            vehicle_capacity=vehicle_capacity,
            euc_distance=euc_distance,
            average_speed=average_speed,
            service_time=service_time,
            supplier_arrival_times=supplier_arrival_times,
            goods_ready_times=goods_ready_times,
            customer_dispatch_waves=customer_dispatch_waves,
            dispatch_waves=dispatch_waves,
            working_day_end_time=working_day_end_time,
            supplier_region_id=supplier_region_id,
        )

        all_feasible = True

        for record in split_records:
            if not record["timing_feasible"]:
                all_feasible = False
                break

        route_durations = []
        route_loads = []
        route_customer_counts = []

        for record in split_records:
            route_durations.append(record["route_duration_hours"])
            route_loads.append(record["route_load"])
            route_customer_counts.append(record["n_customers"])

        max_duration = max(route_durations)
        duration_imbalance = abs(route_durations[0] - route_durations[1])
        load_imbalance = abs(route_loads[0] - route_loads[1])
        customer_count_imbalance = abs(route_customer_counts[0] - route_customer_counts[1])
        total_distance = calculate_total_record_distance(split_records)
        max_lateness = calculate_max_lateness(split_records, working_day_end_time)
        unresolved_customers = collect_unresolved_customers(split_records)

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
            "max_lateness": max_lateness,
            "unresolved_customers": unresolved_customers,
            "n_unresolved_customers": len(unresolved_customers),
        })

        split_index += 1

    return candidates


def choose_best_duration_split_candidate(candidates):
    """Choose the best split candidate for duration feasibility."""
    if not candidates:
        return None

    feasible_candidates = []

    for candidate in candidates:
        if candidate["all_feasible"]:
            feasible_candidates.append(candidate)

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
            candidate["n_unresolved_customers"],
            candidate["max_lateness"],
            candidate["max_duration"],
            candidate["duration_imbalance"],
            candidate["total_distance"],
        ),
    )


def recursively_split_infeasible_route(
    route,
    constructed_dispatch_wave,
    demand,
    vehicle_capacity,
    euc_distance,
    average_speed,
    service_time,
    supplier_arrival_times,
    goods_ready_times,
    customer_dispatch_waves,
    dispatch_waves,
    working_day_end_time,
    supplier_region_id,
    recursion_depth,
    max_recursion_depth,
):
    """Split one route until it becomes feasible or cannot be split further."""
    current_records = evaluate_candidate_routes(
        routes=[route],
        constructed_dispatch_wave=constructed_dispatch_wave,
        demand=demand,
        vehicle_capacity=vehicle_capacity,
        euc_distance=euc_distance,
        average_speed=average_speed,
        service_time=service_time,
        supplier_arrival_times=supplier_arrival_times,
        goods_ready_times=goods_ready_times,
        customer_dispatch_waves=customer_dispatch_waves,
        dispatch_waves=dispatch_waves,
        working_day_end_time=working_day_end_time,
        supplier_region_id=supplier_region_id,
    )

    current_record = current_records[0]

    if current_record["timing_feasible"]:
        return [route]

    customers = route[1:-1]

    if len(customers) <= 1:
        return [route]

    if recursion_depth >= max_recursion_depth:
        return [route]

    candidates = build_duration_split_candidates(
        route=route,
        constructed_dispatch_wave=constructed_dispatch_wave,
        demand=demand,
        vehicle_capacity=vehicle_capacity,
        euc_distance=euc_distance,
        average_speed=average_speed,
        service_time=service_time,
        supplier_arrival_times=supplier_arrival_times,
        goods_ready_times=goods_ready_times,
        customer_dispatch_waves=customer_dispatch_waves,
        dispatch_waves=dispatch_waves,
        working_day_end_time=working_day_end_time,
        supplier_region_id=supplier_region_id,
    )

    best_candidate = choose_best_duration_split_candidate(candidates)

    if best_candidate is None:
        return [route]

    final_routes = []

    for split_route in best_candidate["split_routes"]:
        split_route_records = evaluate_candidate_routes(
            routes=[split_route],
            constructed_dispatch_wave=constructed_dispatch_wave,
            demand=demand,
            vehicle_capacity=vehicle_capacity,
            euc_distance=euc_distance,
            average_speed=average_speed,
            service_time=service_time,
            supplier_arrival_times=supplier_arrival_times,
            goods_ready_times=goods_ready_times,
            customer_dispatch_waves=customer_dispatch_waves,
            dispatch_waves=dispatch_waves,
            working_day_end_time=working_day_end_time,
            supplier_region_id=supplier_region_id,
        )

        split_route_record = split_route_records[0]

        if split_route_record["timing_feasible"]:
            final_routes.append(split_route)

        else:
            child_routes = recursively_split_infeasible_route(
                route=split_route,
                constructed_dispatch_wave=constructed_dispatch_wave,
                demand=demand,
                vehicle_capacity=vehicle_capacity,
                euc_distance=euc_distance,
                average_speed=average_speed,
                service_time=service_time,
                supplier_arrival_times=supplier_arrival_times,
                goods_ready_times=goods_ready_times,
                customer_dispatch_waves=customer_dispatch_waves,
                dispatch_waves=dispatch_waves,
                working_day_end_time=working_day_end_time,
                supplier_region_id=supplier_region_id,
                recursion_depth=recursion_depth + 1,
                max_recursion_depth=max_recursion_depth,
            )

            for child_route in child_routes:
                final_routes.append(child_route)

    return final_routes


def repair_infeasible_wave_routes_by_duration_split(
    routes,
    constructed_dispatch_wave,
    demand,
    vehicle_capacity,
    euc_distance,
    average_speed,
    service_time,
    supplier_arrival_times,
    goods_ready_times,
    customer_dispatch_waves,
    dispatch_waves,
    working_day_end_time,
    supplier_region_id="global_depot_pool_by_dispatch_wave",
    start_route_id=1,
    max_recursion_depth=10,
):
    """Repair timing-infeasible routes by duration-based splitting.

    Only routes that violate timing feasibility are split. All split routes stay
    in the same dispatch wave as the original route.
    """
    pre_repair_records = evaluate_wave_constructed_routes(
        routes=routes,
        constructed_dispatch_wave=constructed_dispatch_wave,
        demand=demand,
        vehicle_capacity=vehicle_capacity,
        euc_distance=euc_distance,
        average_speed=average_speed,
        service_time=service_time,
        supplier_arrival_times=supplier_arrival_times,
        goods_ready_times=goods_ready_times,
        customer_dispatch_waves=customer_dispatch_waves,
        dispatch_waves=dispatch_waves,
        working_day_end_time=working_day_end_time,
        supplier_region_id=supplier_region_id,
        start_route_id=start_route_id,
    )

    repaired_routes = []
    repair_records = []

    for route_index, route in enumerate(routes):
        pre_record = pre_repair_records[route_index]

        if pre_record["timing_feasible"]:
            repaired_routes.append(route)
            continue

        repaired_candidate_routes = recursively_split_infeasible_route(
            route=route,
            constructed_dispatch_wave=constructed_dispatch_wave,
            demand=demand,
            vehicle_capacity=vehicle_capacity,
            euc_distance=euc_distance,
            average_speed=average_speed,
            service_time=service_time,
            supplier_arrival_times=supplier_arrival_times,
            goods_ready_times=goods_ready_times,
            customer_dispatch_waves=customer_dispatch_waves,
            dispatch_waves=dispatch_waves,
            working_day_end_time=working_day_end_time,
            supplier_region_id=supplier_region_id,
            recursion_depth=0,
            max_recursion_depth=max_recursion_depth,
        )

        repaired_candidate_records = evaluate_candidate_routes(
            routes=repaired_candidate_routes,
            constructed_dispatch_wave=constructed_dispatch_wave,
            demand=demand,
            vehicle_capacity=vehicle_capacity,
            euc_distance=euc_distance,
            average_speed=average_speed,
            service_time=service_time,
            supplier_arrival_times=supplier_arrival_times,
            goods_ready_times=goods_ready_times,
            customer_dispatch_waves=customer_dispatch_waves,
            dispatch_waves=dispatch_waves,
            working_day_end_time=working_day_end_time,
            supplier_region_id=supplier_region_id,
        )

        for repaired_record in repaired_candidate_records:
            repaired_record["timing_model"] = (
                "depot_dispatch_waves_wave_constructed_with_duration_split_repair"
            )
            repaired_record["repair_model"] = "same_wave_duration_split_with_2opt"
            repaired_record["source_route_id_before_repair"] = pre_record["route_id"]

        repair_successful = True

        for repaired_record in repaired_candidate_records:
            if not repaired_record["timing_feasible"]:
                repair_successful = False
                break

        for repaired_route in repaired_candidate_routes:
            repaired_routes.append(repaired_route)

        distance_before = pre_record["route_distance"]
        distance_after = calculate_total_record_distance(repaired_candidate_records)
        max_lateness_before = calculate_max_lateness([pre_record], working_day_end_time)
        max_lateness_after = calculate_max_lateness(
            repaired_candidate_records,
            working_day_end_time,
        )
        unresolved_customers = collect_unresolved_customers(repaired_candidate_records)
        available_time_after_wave = calculate_available_time_after_wave(
            constructed_dispatch_wave,
            working_day_end_time,
        )

        repair_records.append({
            "original_route_id": pre_record["route_id"],
            "constructed_dispatch_wave": constructed_dispatch_wave,
            "constructed_dispatch_wave_label": format_hour(constructed_dispatch_wave),
            "available_time_after_wave_hours": available_time_after_wave,
            "available_time_after_wave_minutes": (
                int(round(available_time_after_wave * 60))
                if available_time_after_wave is not None
                else None
            ),
            "repair_model": "same_wave_duration_split_with_2opt",
            "repair_attempted": True,
            "repair_successful": repair_successful,
            "original_trip": pre_record["trip"],
            "original_customers": pre_record["customers"],
            "original_n_customers": pre_record["n_customers"],
            "original_route_load": pre_record["route_load"],
            "original_route_distance": distance_before,
            "original_route_duration_hours": pre_record["route_duration_hours"],
            "original_finish_time": pre_record["finish_time"],
            "original_finish_time_label": pre_record["finish_time_label"],
            "original_lateness_hours": max_lateness_before,
            "n_routes_before_repair": 1,
            "n_routes_after_repair": len(repaired_candidate_routes),
            "repaired_routes": repaired_candidate_routes,
            "repaired_route_records": repaired_candidate_records,
            "repaired_total_distance": distance_after,
            "distance_delta_after_repair": distance_after - distance_before,
            "max_lateness_after_repair_hours": max_lateness_after,
            "unresolved_customers_after_repair": unresolved_customers,
            "n_unresolved_customers_after_repair": len(unresolved_customers),
        })

    final_records = evaluate_wave_constructed_routes(
        routes=repaired_routes,
        constructed_dispatch_wave=constructed_dispatch_wave,
        demand=demand,
        vehicle_capacity=vehicle_capacity,
        euc_distance=euc_distance,
        average_speed=average_speed,
        service_time=service_time,
        supplier_arrival_times=supplier_arrival_times,
        goods_ready_times=goods_ready_times,
        customer_dispatch_waves=customer_dispatch_waves,
        dispatch_waves=dispatch_waves,
        working_day_end_time=working_day_end_time,
        supplier_region_id=supplier_region_id,
        start_route_id=start_route_id,
    )

    for final_record in final_records:
        final_record["timing_model"] = (
            "depot_dispatch_waves_wave_constructed_with_duration_split_repair"
        )
        final_record["repair_model"] = "same_wave_duration_split_with_2opt"

    return {
        "pre_repair_records": pre_repair_records,
        "repaired_routes": repaired_routes,
        "final_records": final_records,
        "repair_records": repair_records,
    }


def summarize_wave_duration_split_repair(
    repair_records,
    pre_repair_records,
    final_records,
):
    """Summarize the duration-based split repair layer."""
    n_attempts = len(repair_records)
    n_successful_repairs = 0
    n_unresolved_repairs = 0
    total_distance_before_repair = calculate_total_record_distance(pre_repair_records)
    total_distance_after_repair = calculate_total_record_distance(final_records)

    unresolved_customers = set()

    for repair_record in repair_records:
        if repair_record["repair_successful"]:
            n_successful_repairs += 1
        else:
            n_unresolved_repairs += 1

        for customer_id in repair_record["unresolved_customers_after_repair"]:
            unresolved_customers.add(customer_id)

    n_routes_before_repair = len(pre_repair_records)
    n_routes_after_repair = len(final_records)

    return {
        "repair_model": "same_wave_duration_split_with_2opt",
        "n_wave_timing_repair_attempts": n_attempts,
        "n_wave_timing_successful_repairs": n_successful_repairs,
        "n_wave_timing_unresolved_repairs": n_unresolved_repairs,
        "n_depot_timing_routes_before_repair": n_routes_before_repair,
        "n_depot_timing_routes_after_repair": n_routes_after_repair,
        "routes_added_by_wave_repair": (
            n_routes_after_repair - n_routes_before_repair
        ),
        "depot_distance_before_wave_repair": total_distance_before_repair,
        "depot_distance_after_wave_repair": total_distance_after_repair,
        "distance_delta_after_wave_repair": (
            total_distance_after_repair - total_distance_before_repair
        ),
        "unresolved_customers_after_wave_repair": sorted(unresolved_customers),
        "n_unresolved_customers_after_wave_repair": len(unresolved_customers),
    }
