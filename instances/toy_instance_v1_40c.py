"""Generated 40-customer toy CVRP instance with service times."""

import random


random.seed(42)

n_customers = 40
depot_cord = (0, 0)
average_speed = 30

customer_cord = {}
demand = {}
service_time = {}

for i in range(1, n_customers + 1):
    x = random.uniform(0, 20)
    y = random.uniform(0, 20)

    customer_cord[i] = (x, y)
    demand[i] = random.randint(1, 6)
    service_time[i] = 10

demand[0] = 0


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
