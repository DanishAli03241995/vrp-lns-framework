"""Compatibility solver wrapper matching recovered experiment-file calls."""


def calculate_route_distance(route, euc_distance):
    total_distance = 0

    for index in range(len(route) - 1):
        total_distance += euc_distance(route[index], route[index + 1])

    return total_distance


def calculate_total_distance(routes, euc_distance):
    return sum(calculate_route_distance(route, euc_distance) for route in routes)


def calculate_route_load(route, demand):
    return sum(demand[customer_id] for customer_id in route if customer_id != 0)


def calculate_travel_time(routes, euc_distance, average_speed, service_time):
    total_travel_time = 0

    for route in routes:
        trip_distance = calculate_route_distance(route, euc_distance)
        trip_time = trip_distance / average_speed

        for customer_id in route[1:-1]:
            trip_time += service_time[customer_id] / 60

        total_travel_time += trip_time

    return total_travel_time


def run_baseline_nn(
    depot_cord,
    customer_cord,
    demand,
    vehicle_capacity,
    average_speed,
    service_time,
):
    def local_euc_distance(i, j):
        if i == 0:
            coord_i = depot_cord
        else:
            coord_i = customer_cord[i]

        if j == 0:
            coord_j = depot_cord
        else:
            coord_j = customer_cord[j]

        x_i, y_i = coord_i
        x_j, y_j = coord_j

        return ((x_i - x_j) ** 2 + (y_i - y_j) ** 2) ** 0.5

    unserved_customers = list(customer_cord.keys())
    routes = []
    vehicle_capacity_used = []

    while unserved_customers:
        current_node = 0
        current_route = [0]
        current_load = 0

        while True:
            feasible_customers = [
                customer_id
                for customer_id in unserved_customers
                if current_load + demand[customer_id] <= vehicle_capacity
            ]

            if not feasible_customers:
                break

            nearest_customer = min(
                feasible_customers,
                key=lambda customer_id: local_euc_distance(current_node, customer_id),
            )

            current_route.append(nearest_customer)
            unserved_customers.remove(nearest_customer)
            current_load += demand[nearest_customer]
            current_node = nearest_customer

        current_route.append(0)
        routes.append(current_route)
        vehicle_capacity_used.append(current_load)

    total_distance = calculate_total_distance(routes, local_euc_distance)
    number_of_trip = len(routes)
    total_travel_time = calculate_travel_time(
        routes,
        local_euc_distance,
        average_speed,
        service_time,
    )
    capacity_feasibility = all(load <= vehicle_capacity for load in vehicle_capacity_used)
    served_customers = {
        customer_id
        for route in routes
        for customer_id in route
        if customer_id != 0
    }
    structural_validity = all(
        route[0] == 0 and route[-1] == 0
        for route in routes
    )
    unserved_after_routing = [
        customer_id
        for customer_id in customer_cord
        if customer_id not in served_customers
    ]

    return (
        routes,
        total_distance,
        number_of_trip,
        total_travel_time,
        capacity_feasibility,
        structural_validity,
        vehicle_capacity_used,
        unserved_after_routing,
    )


def improve_route_2opt(route, euc_distance):
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
                candidate_distance = calculate_route_distance(candidate_route, euc_distance)

                if candidate_distance < best_distance:
                    improved = True
                    best_route = candidate_route
                    best_distance = candidate_distance

        if not improved:
            break

        current_route = best_route

    return current_route


def run_2opt(routes, euc_distance):
    return [improve_route_2opt(route, euc_distance) for route in routes]


def run_relocation(routes, demand, vehicle_capacity, euc_distance):
    current_routes = [route.copy() for route in routes]

    while True:
        best_delta = 0
        best_move = None

        for from_index, source_route in enumerate(current_routes):
            for customer_id in source_route[1:-1]:
                source_after_removal = [
                    node_id
                    for node_id in source_route
                    if node_id != customer_id
                ]
                source_before_distance = calculate_route_distance(
                    source_route,
                    euc_distance,
                )
                source_after_distance = calculate_route_distance(
                    source_after_removal,
                    euc_distance,
                )

                for to_index, target_route in enumerate(current_routes):
                    if to_index == from_index:
                        continue

                    target_before_distance = calculate_route_distance(
                        target_route,
                        euc_distance,
                    )

                    for insert_index in range(1, len(target_route)):
                        target_after_insertion = (
                            target_route[:insert_index]
                            + [customer_id]
                            + target_route[insert_index:]
                        )

                        if calculate_route_load(target_after_insertion, demand) > vehicle_capacity:
                            continue

                        target_after_distance = calculate_route_distance(
                            target_after_insertion,
                            euc_distance,
                        )
                        old_cost = source_before_distance + target_before_distance
                        new_cost = source_after_distance + target_after_distance
                        delta = new_cost - old_cost

                        if delta < best_delta:
                            best_delta = delta
                            best_move = {
                                "from_index": from_index,
                                "to_index": to_index,
                                "source_after_removal": source_after_removal,
                                "target_after_insertion": target_after_insertion,
                            }

        if best_move is None:
            break

        current_routes[best_move["from_index"]] = best_move["source_after_removal"]
        current_routes[best_move["to_index"]] = best_move["target_after_insertion"]

    return current_routes
