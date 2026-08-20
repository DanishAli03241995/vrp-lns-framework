"""2-opt local search for depot-customer routes."""

from solvers.nearest_neighbor import route_distance


def improve_route_2opt(route, depot_cord, customer_cord, depot_id=0):
    if len(route) <= 4:
        return route.copy()

    current_route = route.copy()

    while True:
        improved = False
        best_route = current_route
        best_distance = route_distance(current_route, depot_cord, customer_cord, depot_id)

        for i in range(len(current_route) - 3):
            for j in range(i + 2, len(current_route) - 1):
                candidate_route = (
                    current_route[: i + 1]
                    + current_route[i + 1 : j + 1][::-1]
                    + current_route[j + 1 :]
                )
                candidate_distance = route_distance(
                    candidate_route,
                    depot_cord,
                    customer_cord,
                    depot_id,
                )

                if candidate_distance < best_distance:
                    improved = True
                    best_route = candidate_route
                    best_distance = candidate_distance

        if not improved:
            break

        current_route = best_route

    return current_route


def run_2opt(routes, depot_cord, customer_cord, depot_id=0):
    return [
        improve_route_2opt(route, depot_cord, customer_cord, depot_id)
        for route in routes
    ]
