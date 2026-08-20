import math


def compute_sweep_order(depot_cord, customer_cord, demand):
    """
    customers: list of tuples -> [(id, x, y, demand), ...]
    depot: tuple -> (x_d, y_d)
    """
    xd, yd = depot_cord
    customer_angles = []

    for customer_id, (x, y) in customer_cord.items():
        customer_demand = demand[customer_id]

        # Step 1 — shift coordinates relative to depot
        dx = x - xd
        dy = y - yd

        # Step 2 — compute angle
        angle = math.atan2(dy, dx)

        # Step 3 — normalize angle to [0, 2π]
        if angle < 0:
            angle += 2 * math.pi

        customer_angles.append((customer_id, x, y, customer_demand, angle))

    # Step 4 — sort by angle
    customer_angles.sort(key=lambda x: x[4])

    return customer_angles


def form_sweep_clusters(angle_data, vehicle_capacity):
    clusters = []

    current_cluster = []
    current_load = 0

    for item in angle_data:
        customer_id, x, y, customer_demand, angle = item

        if current_load + customer_demand > vehicle_capacity:
            if len(current_cluster) > 0:
                clusters.append(current_cluster)

            current_cluster = [customer_id]
            current_load = customer_demand

        else:
            current_cluster.append(customer_id)
            current_load += customer_demand

    if len(current_cluster) > 0:
        clusters.append(current_cluster)

    return clusters


def get_cluster_data(cluster, customer_cord, demand):
    cluster_customer_cord = {}
    cluster_demand = {}

    for customer_id in cluster:
        cluster_customer_cord[customer_id] = customer_cord[customer_id]
        cluster_demand[customer_id] = demand[customer_id]

    return cluster_customer_cord, cluster_demand
