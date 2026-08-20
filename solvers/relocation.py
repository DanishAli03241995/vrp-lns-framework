"""Global 1-0 relocation local search for depot-customer routes."""

from solvers.nearest_neighbor import route_distance, total_route_distance


def route_load(route, demand, depot_id=0):
    return sum(demand[node_id] for node_id in route if node_id != depot_id)


def run_relocation(
    routes,
    depot_cord,
    customer_cord,
    demand,
    vehicle_capacity,
    depot_id=0,
):
    current_routes = [route.copy() for route in routes]

    while True:
        best_delta = 0
        best_move = None

        for from_index, source_route in enumerate(current_routes):
            for customer_id in source_route[1:-1]:
                source_after_removal = [
                    node_id for node_id in source_route if node_id != customer_id
                ]
                source_before_distance = route_distance(
                    source_route,
                    depot_cord,
                    customer_cord,
                    depot_id,
                )
                source_after_distance = route_distance(
                    source_after_removal,
                    depot_cord,
                    customer_cord,
                    depot_id,
                )

                for to_index, target_route in enumerate(current_routes):
                    if to_index == from_index:
                        continue

                    target_before_distance = route_distance(
                        target_route,
                        depot_cord,
                        customer_cord,
                        depot_id,
                    )

                    for insert_index in range(1, len(target_route)):
                        target_after_insertion = (
                            target_route[:insert_index]
                            + [customer_id]
                            + target_route[insert_index:]
                        )

                        if route_load(target_after_insertion, demand, depot_id) > vehicle_capacity:
                            continue

                        target_after_distance = route_distance(
                            target_after_insertion,
                            depot_cord,
                            customer_cord,
                            depot_id,
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


def relocation_improvement(
    before_routes,
    after_routes,
    depot_cord,
    customer_cord,
    depot_id=0,
):
    before_distance = total_route_distance(
        before_routes,
        depot_cord,
        customer_cord,
        depot_id,
    )
    after_distance = total_route_distance(
        after_routes,
        depot_cord,
        customer_cord,
        depot_id,
    )

    return before_distance - after_distance
