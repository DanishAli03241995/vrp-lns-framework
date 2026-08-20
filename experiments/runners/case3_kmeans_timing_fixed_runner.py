"""Runner for Case 3 hybrid supplier-customer KMeans with fixed depot timing."""

import importlib
import os
import sys


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(PROJECT_ROOT)
os.environ.setdefault("MPLCONFIGDIR", os.path.join(PROJECT_ROOT, ".matplotlib_cache"))


experiment_module = importlib.import_module(
    "experiments.Case_3_hybrid_supplier_customer.baseline_kmeans_timing_fixed_v1"
)

run_experiment = experiment_module.run_experiment


ALGORITHM_NAME = "hybrid_supplier_customer_kmeans_timing_fixed_v1"

# RUN_MODE = "test"
RUN_MODE = "batch"

BATCH_CUSTOMER_COUNTS = [20, 40, 60, 80, 100, 150, 200]
BATCH_VEHICLE_CAPACITIES = [15, 25, 35]


def get_grid_size(n_customers):
    if n_customers == 20:
        return 10
    if n_customers == 40:
        return 20
    if n_customers == 60:
        return 30
    if n_customers == 80:
        return 40
    return max(10, n_customers // 2)


def build_config(n_customers, vehicle_capacity):
    return {
        "n_customers": n_customers,
        "vehicle_capacity": vehicle_capacity,
        "n_suppliers": 3,
        "seed": 42,
        "direct_delivery_threshold": 5,
        "grid_size": get_grid_size(n_customers),

        # Fixed depot timing parameters.
        # Times are decimal hours: 9.0 = 09:00, 18.0 = 18:00.
        "fixed_depot_ready_time": 9.0,
        "working_day_end_time": 18.0,
    }


if RUN_MODE == "test":
    experiments = [build_config(n_customers=40, vehicle_capacity=25)]

elif RUN_MODE == "batch":
    experiments = []

    for n_customers in BATCH_CUSTOMER_COUNTS:
        for vehicle_capacity in BATCH_VEHICLE_CAPACITIES:
            experiments.append(build_config(n_customers, vehicle_capacity))

else:
    raise ValueError(f"Unsupported RUN_MODE: {RUN_MODE}")


for config in experiments:
    config["algorithm"] = ALGORITHM_NAME
    config["experiment_name"] = (
        f"{config['n_customers']}c_cap{config['vehicle_capacity']}"
    )

    print("\n===================================")
    print("Running Case 3 KMeans fixed depot timing experiment:")
    print(config)
    print("===================================\n")

    run_experiment(config)
