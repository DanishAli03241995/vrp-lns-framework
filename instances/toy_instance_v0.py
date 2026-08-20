"""Toy single-depot CVRP instance used by the first NN baseline."""

depot_cord = (0, 0)

customer_cord = {
    1: (2, 1),
    2: (3, 2),
    3: (1, 3),
    4: (5, 1),
    5: (6, 3),
    6: (7, 2),
    7: (4, 5),
    8: (2, 6),
}

demand = {
    0: 0,
    1: 3,
    2: 4,
    3: 2,
    4: 5,
    5: 4,
    6: 6,
    7: 3,
    8: 2,
}


def euc_distance(i, j):
    if i == 0:
        coord_i = depot_cord
    else:
        coord_i = customer_cord[i]

    if j == 0:
        coord_j = depot_cord
    else:
        coord_j = customer_cord[j]

    x_i = coord_i[0]
    y_i = coord_i[1]

    x_j = coord_j[0]
    y_j = coord_j[1]

    d_x = x_i - x_j
    d_y = y_i - y_j

    distance = (d_x**2 + d_y**2) ** 0.5
    return distance
