"""Runner for Case 1 supplier-depot-customer KMeans baseline."""

import importlib
import os
import sys


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(PROJECT_ROOT)
os.environ.setdefault("MPLCONFIGDIR", os.path.join(PROJECT_ROOT, ".matplotlib_cache"))


experiment_module = importlib.import_module(
    "experiments.Case_1_supplier_depot_customer.baseline_kmeans_v1"
)

run_experiment = experiment_module.run_experiment


ALGORITHM_NAME = "supplier_depot_customer_baseline_kmeans_v1"

# RUN_MODE = "test"
RUN_MODE = "batch"


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


if RUN_MODE == "test":
    n_customers = 40
    experiments = [
        {
            "n_customers": n_customers,
            "vehicle_capacity": 25,
            "n_suppliers": 3,
            "seed": 42,
            "grid_size": get_grid_size(n_customers),
        }
    ]

elif RUN_MODE == "batch":
    experiments = []

    for n_customers in [20, 40, 60, 80]:
        for vehicle_capacity in [15, 25, 35]:
            experiments.append(
                {
                    "n_customers": n_customers,
                    "vehicle_capacity": vehicle_capacity,
                    "n_suppliers": 3,
                    "seed": 42,
                    "grid_size": get_grid_size(n_customers),
                }
            )

else:
    raise ValueError(f"Unsupported RUN_MODE: {RUN_MODE}")


for config in experiments:
    config["algorithm"] = ALGORITHM_NAME
    config["experiment_name"] = (
        f"{config['n_customers']}c_cap{config['vehicle_capacity']}"
    )

    print("\n===================================")
    print("Running Case 1 KMeans experiment:")
    print(config)
    print("===================================\n")

    run_experiment(config)
