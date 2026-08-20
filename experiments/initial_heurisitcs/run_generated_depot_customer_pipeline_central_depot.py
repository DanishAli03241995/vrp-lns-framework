"""Run generated depot-customer initial pipeline with the depot at map center."""

import os
import sys


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(PROJECT_ROOT)


from experiments.initial_heurisitcs import run_generated_depot_customer_pipeline as base
from instances.generate_depot_customer_instance import get_grid_size


base.ALGORITHM_NAME = "generated_depot_customer_initial_pipeline_central_depot"

# RUN_MODE = "test"
RUN_MODE = "batch"


def build_config(n_customers, vehicle_capacity):
    grid_size = get_grid_size(n_customers)
    return {
        "n_customers": n_customers,
        "vehicle_capacity": vehicle_capacity,
        "seed": 42,
        "depot_cord": (grid_size / 2, grid_size / 2),
    }


def build_experiments():
    if RUN_MODE == "test":
        return [build_config(n_customers=40, vehicle_capacity=25)]

    if RUN_MODE == "batch":
        experiments = []
        for n_customers in [20, 40, 60, 80]:
            for vehicle_capacity in [15, 25, 35]:
                experiments.append(build_config(n_customers, vehicle_capacity))
        return experiments

    raise ValueError(f"Unsupported RUN_MODE: {RUN_MODE}")


if __name__ == "__main__":
    for experiment_config in build_experiments():
        print("\n===================================")
        print("Running generated central-depot experiment:")
        print(experiment_config)
        print("===================================\n")
        base.run_experiment(experiment_config)
