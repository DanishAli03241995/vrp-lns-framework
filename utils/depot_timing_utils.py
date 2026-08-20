"""Depot timing utilities for fixed depot-availability experiments.

This module is intentionally small and independent from the generic routing
heuristics. It evaluates depot-based Hybrid routes after they have already been
constructed by NN + 2-opt + relocation + 2-opt.

First timing version:
- all depot-bound goods are assumed to be ready at one fixed depot-ready time;
- every depot route departs at that fixed time;
- a route is timing-feasible only if it returns before the working-day end;
- no route splitting/repair is done here yet.
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
    """Calculate depot route distance using the supplied distance function."""
    total_distance = 0

    for index in range(len(route) - 1):
        total_distance += euc_distance(route[index], route[index + 1])

    return total_distance


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
