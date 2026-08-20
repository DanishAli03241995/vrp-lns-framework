"""Route plotting helpers used by recovered experiment files."""

try:
    import matplotlib

    matplotlib.use("Agg")

    import matplotlib.pyplot as plt
except ModuleNotFoundError:
    plt = None


def _write_plot_placeholder(results_path, filename, title):
    placeholder_name = filename.rsplit(".", 1)[0] + "_plot_skipped.txt"

    with open(f"{results_path}/{placeholder_name}", "w") as file_handle:
        file_handle.write(
            "Plot skipped because matplotlib is not installed.\n"
            f"Requested plot: {title}\n"
        )


def _coord(node_id, origin, customer_cord):
    if node_id == 0:
        return origin

    return customer_cord[node_id]


def plot_routes(
    routes,
    depot_cord,
    customer_cord,
    results_path,
    filename="route_plot.png",
    title="Vehicle Routes",
    supplier_cord=None,
):
    if plt is None:
        _write_plot_placeholder(results_path, filename, title)
        return

    plt.figure(figsize=(9, 7))

    if customer_cord:
        customer_x = [coord[0] for coord in customer_cord.values()]
        customer_y = [coord[1] for coord in customer_cord.values()]
        plt.scatter(customer_x, customer_y, c="tab:blue", s=25, label="Customers")

    plt.scatter(
        [depot_cord[0]],
        [depot_cord[1]],
        c="tab:red",
        s=90,
        marker="s",
        label="Depot",
    )

    if supplier_cord:
        supplier_x = [coord[0] for coord in supplier_cord.values()]
        supplier_y = [coord[1] for coord in supplier_cord.values()]
        plt.scatter(
            supplier_x,
            supplier_y,
            c="tab:green",
            s=80,
            marker="^",
            label="Suppliers",
        )

    for route in routes:
        route_coords = [_coord(node_id, depot_cord, customer_cord) for node_id in route]
        x_values = [coord[0] for coord in route_coords]
        y_values = [coord[1] for coord in route_coords]
        plt.plot(x_values, y_values, linewidth=1.2, alpha=0.8)

    plt.title(title)
    plt.xlabel("X")
    plt.ylabel("Y")
    plt.legend()
    plt.tight_layout()
    plt.savefig(f"{results_path}/{filename}", dpi=150)
    plt.close()


def plot_supplier_routes(
    route_records,
    supplier_cord,
    customer_cord,
    results_path,
    filename="route_plot.png",
    title="Supplier Routes",
    depot_cord=None,
):
    if plt is None:
        _write_plot_placeholder(results_path, filename, title)
        return

    plt.figure(figsize=(9, 7))

    if customer_cord:
        customer_x = [coord[0] for coord in customer_cord.values()]
        customer_y = [coord[1] for coord in customer_cord.values()]
        plt.scatter(customer_x, customer_y, c="tab:blue", s=25, label="Customers")

    if depot_cord is not None:
        plt.scatter(
            [depot_cord[0]],
            [depot_cord[1]],
            c="tab:red",
            s=90,
            marker="s",
            label="Depot",
        )

    if supplier_cord:
        supplier_x = [coord[0] for coord in supplier_cord.values()]
        supplier_y = [coord[1] for coord in supplier_cord.values()]
        plt.scatter(
            supplier_x,
            supplier_y,
            c="tab:green",
            s=80,
            marker="^",
            label="Suppliers",
        )

    for record in route_records:
        trip = record["trip"]
        origin_type = record.get("origin_type")

        if origin_type == "depot" and depot_cord is not None:
            origin = depot_cord
        else:
            supplier_id = record.get("supplier_id") or record.get("supplier_region_id")
            origin = supplier_cord[supplier_id]

        route_coords = [_coord(node_id, origin, customer_cord) for node_id in trip]
        x_values = [coord[0] for coord in route_coords]
        y_values = [coord[1] for coord in route_coords]
        plt.plot(x_values, y_values, linewidth=1.2, alpha=0.8)

    plt.title(title)
    plt.xlabel("X")
    plt.ylabel("Y")
    plt.legend()
    plt.tight_layout()
    plt.savefig(f"{results_path}/{filename}", dpi=150)
    plt.close()
