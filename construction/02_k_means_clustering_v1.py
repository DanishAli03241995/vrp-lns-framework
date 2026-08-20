"""K-means clustering construction helper for depot-customer routing."""

# Original recovered .md version used:
# from sklearn.cluster import KMeans
# Current rebuild uses a small built-in KMeans fallback because sklearn is not
# installed here. If sklearn is installed later, run_kmeans(...) can be switched
# back to the sklearn implementation.

import math


def prepare_kmeans_input(customer_cord):
    coords = []
    customer_ids = []

    for customer_id, (x_coord, y_coord) in customer_cord.items():
        coords.append((x_coord, y_coord))
        customer_ids.append(customer_id)

    return coords, customer_ids


def euclidean_distance(point_a, point_b):
    return math.sqrt(
        (point_a[0] - point_b[0]) ** 2
        + (point_a[1] - point_b[1]) ** 2
    )


def initialize_centroids(coords, k):
    if k <= 0:
        raise ValueError("K must be greater than 0.")

    if k > len(coords):
        raise ValueError("K cannot be greater than the number of customers.")

    return [coords[index] for index in range(k)]


def assign_labels(coords, centroids):
    labels = []

    for coord in coords:
        nearest_centroid_index = min(
            range(len(centroids)),
            key=lambda index: euclidean_distance(coord, centroids[index]),
        )
        labels.append(nearest_centroid_index)

    return labels


def recompute_centroids(coords, labels, k, previous_centroids):
    centroids = []

    for cluster_index in range(k):
        cluster_points = [
            coord
            for coord, label in zip(coords, labels)
            if label == cluster_index
        ]

        if not cluster_points:
            centroids.append(previous_centroids[cluster_index])
            continue

        avg_x = sum(point[0] for point in cluster_points) / len(cluster_points)
        avg_y = sum(point[1] for point in cluster_points) / len(cluster_points)
        centroids.append((avg_x, avg_y))

    return centroids


def run_kmeans(coords, K, max_iterations=100):
    centroids = initialize_centroids(coords, K)

    for _ in range(max_iterations):
        labels = assign_labels(coords, centroids)
        new_centroids = recompute_centroids(coords, labels, K, centroids)

        if new_centroids == centroids:
            break

        centroids = new_centroids

    return labels


def build_clusters_from_labels(labels, customer_ids, K):
    clusters = [[] for _ in range(K)]

    for index, label in enumerate(labels):
        customer_id = customer_ids[index]
        clusters[label].append(customer_id)

    return [cluster for cluster in clusters if cluster]


def kmeans_clustering(customer_cord, K):
    coords, customer_ids = prepare_kmeans_input(customer_cord)
    labels = run_kmeans(coords, K)

    return build_clusters_from_labels(labels, customer_ids, K)


def get_cluster_data(cluster, customer_cord, demand):
    cluster_customer_cord = {}
    cluster_demand = {}

    for customer_id in cluster:
        cluster_customer_cord[customer_id] = customer_cord[customer_id]
        cluster_demand[customer_id] = demand[customer_id]

    return cluster_customer_cord, cluster_demand
