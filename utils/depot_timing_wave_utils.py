"""Depot dispatch-wave timing utilities for Hybrid depot routes.

This module is separate from the instance generator and from the generic
routing heuristics. It adds depot-side timing information after the Hybrid +
KMeans route structure has already been constructed.

First dispatch-wave version:
- supplier arrivals to the depot are generated only for depot-assigned
  customers;
- arrivals are random but bounded inside an inbound receiving window;
- handling time is added to create each customer's goods-ready time;
- each depot route departs at the first dispatch wave after all goods in that
  route are ready;
- routes are only flagged as feasible or infeasible;
- no route splitting/repair is done in this version.
"""

import random


def format_hour(hour_value):
    """Convert a decimal hour value, e.g. 9.5, into '09:30'."""
    if hour_value is None:
        return None

    total_minutes = int(round(hour_value * 60))
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours:02d}:{minutes:02d}"


def round_hour_to_step(hour_value, step_minutes):
    """Round a decimal-hour value to the nearest step in minutes."""
    if step_minutes is None:
        return hour_value

    if step_minutes <= 0:
        return hour_value

    total_minutes = int(round(hour_value * 60))
    rounded_minutes = int(round(total_minutes / step_minutes) * step_minutes)

    return rounded_minutes / 60


def calculate_route_distance(route, euc_distance):
    """Calculate route distance using the supplied distance function."""
    total_distance = 0

    for index in range(len(route) - 1):
        from_node = route[index]
        to_node = route[index + 1]
        total_distance += euc_distance(from_node, to_node)

    return total_distance


def calculate_route_load(route, demand):
    """Calculate total demand carried on a route."""
    total_load = 0

    for customer_id in route:
        if customer_id != 0:
            total_load += demand[customer_id]

    return total_load


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


def generate_depot_customer_wave_times(
    depot_customer_ids,
    depot_customer_supplier_map,
    supplier_arrival_start_time,
    supplier_arrival_end_time,
    depot_handling_time,
    seed,
    arrival_time_step_minutes=15,
):
    """Create arrival and goods-ready times for depot-assigned customers.

    The random draw is deterministic for a given seed. This keeps wave-timing
    experiments reproducible while avoiding changes to the main instance
    generator.
    """
    random_generator = random.Random(seed)

    customer_records = []
    supplier_arrival_times = {}
    goods_ready_times = {}

    sorted_customer_ids = sorted(depot_customer_ids)

    for customer_id in sorted_customer_ids:
        random_arrival_time = random_generator.uniform(
            supplier_arrival_start_time,
            supplier_arrival_end_time,
        )

        supplier_arrival_time = round_hour_to_step(
            random_arrival_time,
            arrival_time_step_minutes,
        )

        if supplier_arrival_time < supplier_arrival_start_time:
            supplier_arrival_time = supplier_arrival_start_time

        if supplier_arrival_time > supplier_arrival_end_time:
            supplier_arrival_time = supplier_arrival_end_time

        goods_ready_time = supplier_arrival_time + depot_handling_time
        supplier_id = depot_customer_supplier_map.get(customer_id)

        supplier_arrival_times[customer_id] = supplier_arrival_time
        goods_ready_times[customer_id] = goods_ready_time

        customer_records.append({
            "customer_id": customer_id,
            "supplier_id": supplier_id,
            "supplier_arrival_time": supplier_arrival_time,
            "supplier_arrival_time_label": format_hour(supplier_arrival_time),
            "depot_handling_time_hours": depot_handling_time,
            "depot_handling_time_minutes": int(round(depot_handling_time * 60)),
            "goods_ready_time": goods_ready_time,
            "goods_ready_time_label": format_hour(goods_ready_time),
        })

    return customer_records, supplier_arrival_times, goods_ready_times


def get_route_goods_ready_time(route, goods_ready_times):
    """Return the latest goods-ready time among the customers in a route."""
    route_goods_ready_time = None

    for customer_id in route[1:-1]:
        customer_ready_time = goods_ready_times[customer_id]

        if route_goods_ready_time is None:
            route_goods_ready_time = customer_ready_time

        elif customer_ready_time > route_goods_ready_time:
            route_goods_ready_time = customer_ready_time

    return route_goods_ready_time


def build_route_customer_ready_records(route, goods_ready_times, supplier_arrival_times):
    """Create readable customer-level timing records for one route."""
    records = []

    for customer_id in route[1:-1]:
        supplier_arrival_time = supplier_arrival_times[customer_id]
        goods_ready_time = goods_ready_times[customer_id]

        records.append({
            "customer_id": customer_id,
            "supplier_arrival_time": supplier_arrival_time,
            "supplier_arrival_time_label": format_hour(supplier_arrival_time),
            "goods_ready_time": goods_ready_time,
            "goods_ready_time_label": format_hour(goods_ready_time),
        })

    return records


def choose_earliest_dispatch_wave(route_goods_ready_time, dispatch_waves):
    """Choose the first dispatch wave not earlier than goods-ready time."""
    if route_goods_ready_time is None:
        return None

    sorted_waves = sorted(dispatch_waves)
    selected_wave = None

    for wave in sorted_waves:
        if wave >= route_goods_ready_time:
            selected_wave = wave
            break

    return selected_wave


def evaluate_dispatch_wave_route(
    route,
    route_id,
    supplier_region_id,
    demand,
    vehicle_capacity,
    euc_distance,
    average_speed,
    service_time,
    supplier_arrival_times,
    goods_ready_times,
    dispatch_waves,
    working_day_end_time,
):
    """Evaluate one depot route under dispatch-wave timing."""
    route_distance = calculate_route_distance(route, euc_distance)
    route_load = calculate_route_load(route, demand)
    route_duration = calculate_route_duration_hours(
        route,
        euc_distance,
        average_speed,
        service_time,
    )

    route_goods_ready_time = get_route_goods_ready_time(route, goods_ready_times)
    departure_wave = choose_earliest_dispatch_wave(
        route_goods_ready_time,
        dispatch_waves,
    )

    if departure_wave is None:
        finish_time = None
        waiting_time_hours = None
        dispatch_wave_feasible = False
        working_day_feasible = False

    else:
        finish_time = departure_wave + route_duration
        waiting_time_hours = departure_wave - route_goods_ready_time
        dispatch_wave_feasible = True
        working_day_feasible = finish_time <= working_day_end_time

    capacity_feasible = route_load <= vehicle_capacity
    structural_valid = len(route) >= 2 and route[0] == 0 and route[-1] == 0

    timing_feasible = (
        capacity_feasible
        and structural_valid
        and dispatch_wave_feasible
        and working_day_feasible
    )

    return {
        "route_id": route_id,
        "supplier_region_id": supplier_region_id,
        "origin_type": "depot",
        "timing_model": "depot_dispatch_waves",
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
        "customer_ready_records": build_route_customer_ready_records(
            route,
            goods_ready_times,
            supplier_arrival_times,
        ),
        "route_goods_ready_time": route_goods_ready_time,
        "route_goods_ready_time_label": format_hour(route_goods_ready_time),
        "dispatch_waves": dispatch_waves,
        "dispatch_wave_labels": [format_hour(wave) for wave in dispatch_waves],
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
        "working_day_feasible": working_day_feasible,
        "timing_feasible": timing_feasible,
    }


def evaluate_dispatch_wave_routes(
    routes,
    demand,
    vehicle_capacity,
    euc_distance,
    average_speed,
    service_time,
    supplier_arrival_times,
    goods_ready_times,
    dispatch_waves,
    working_day_end_time,
    supplier_region_id=None,
    start_route_id=1,
):
    """Evaluate depot routes under dispatch-wave timing."""
    records = []
    non_empty_routes = []

    for route in routes:
        customers = []

        for customer_id in route:
            if customer_id != 0:
                customers.append(customer_id)

        if len(customers) > 0:
            non_empty_routes.append(route)

    for index, route in enumerate(non_empty_routes):
        route_id = start_route_id + index

        record = evaluate_dispatch_wave_route(
            route=route,
            route_id=route_id,
            supplier_region_id=supplier_region_id,
            demand=demand,
            vehicle_capacity=vehicle_capacity,
            euc_distance=euc_distance,
            average_speed=average_speed,
            service_time=service_time,
            supplier_arrival_times=supplier_arrival_times,
            goods_ready_times=goods_ready_times,
            dispatch_waves=dispatch_waves,
            working_day_end_time=working_day_end_time,
        )

        records.append(record)

    return records


def summarize_dispatch_wave_timing(records):
    """Create summary metrics from route-level dispatch-wave records."""
    if not records:
        return {
            "timing_model": "depot_dispatch_waves",
            "n_depot_timing_routes": 0,
            "n_depot_timing_feasible_routes": 0,
            "n_depot_timing_infeasible_routes": 0,
            "depot_timing_feasibility": True,
            "infeasible_timing_route_ids": [],
            "infeasible_timing_customers": [],
            "n_routes_without_feasible_wave": 0,
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
    no_wave_records = []
    working_day_infeasible_records = []
    finish_times = []
    waiting_times = []
    routes_per_wave = {}
    routes_per_wave_label = {}

    for record in records:
        if record["timing_feasible"]:
            feasible_records.append(record)
        else:
            infeasible_records.append(record)

        if not record["dispatch_wave_feasible"]:
            no_wave_records.append(record)

        if record["dispatch_wave_feasible"] and not record["working_day_feasible"]:
            working_day_infeasible_records.append(record)

        if record["finish_time"] is not None:
            finish_times.append(record["finish_time"])

        if record["waiting_time_hours"] is not None:
            waiting_times.append(record["waiting_time_hours"])

        departure_wave_label = record["departure_wave_label"]

        if departure_wave_label is not None:
            if departure_wave_label not in routes_per_wave_label:
                routes_per_wave_label[departure_wave_label] = 0

            routes_per_wave_label[departure_wave_label] += 1

        departure_wave = record["departure_wave"]

        if departure_wave is not None:
            wave_key = str(departure_wave)

            if wave_key not in routes_per_wave:
                routes_per_wave[wave_key] = 0

            routes_per_wave[wave_key] += 1

    if finish_times:
        latest_finish = max(finish_times)
    else:
        latest_finish = None

    max_duration = max(record["route_duration_hours"] for record in records)
    avg_duration = sum(record["route_duration_hours"] for record in records) / len(records)
    avg_utilization = sum(record["route_utilization"] for record in records) / len(records)

    if waiting_times:
        avg_waiting = sum(waiting_times) / len(waiting_times)
        max_waiting = max(waiting_times)
    else:
        avg_waiting = 0
        max_waiting = 0

    infeasible_customers = set()

    for record in infeasible_records:
        for customer_id in record["customers"]:
            infeasible_customers.add(customer_id)

    return {
        "timing_model": "depot_dispatch_waves",
        "n_depot_timing_routes": len(records),
        "n_depot_timing_feasible_routes": len(feasible_records),
        "n_depot_timing_infeasible_routes": len(infeasible_records),
        "depot_timing_feasibility": len(infeasible_records) == 0,
        "infeasible_timing_route_ids": [
            record["route_id"] for record in infeasible_records
        ],
        "infeasible_timing_customers": sorted(infeasible_customers),
        "n_routes_without_feasible_wave": len(no_wave_records),
        "n_routes_exceeding_working_day": len(working_day_infeasible_records),
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
