# lns_batch_runner_v1.py
"""Batch runner for LNS-SA routing experiments.

Goals:
1. Run many instances automatically
2. Sweep multiple n_remove values
3. Store all results in ONE JSON file per instance
4. Keep only BEST plot / BEST route output
5. Track runtime + improvement statistics
"""

import os
import json
import time
from datetime import datetime

# =====================================================
# STEP 1 — Select experiment module
# =====================================================

from hybrid_supplier_customer_no_kmeans_cluster_lns_sa_v1 import (
    run_lns_sa_experiment
)


# =====================================================
# STEP 2 — Runner metadata
# =====================================================

ALGORITHM_NAME = "hybrid_supplier_customer_no_kmeans_cluster_lns_sa"

RUN_MODE = "batch"

EXPERIMENT_ID = (
    f"lns_batch_{datetime.now().strftime('%Y_%m_%d_%H%M%S')}"
)


# =====================================================
# STEP 3 — Test mode
# =====================================================

if RUN_MODE == "test":

    experiments = [
        {
            "instance_name": "20c_cap25",
            "n_iterations": 50,
            "seed": 42,
            "initial_temperature": 10.0,
            "cooling_rate": 0.95,
            "minimum_temperature": 0.01,
        }
    ]


# =====================================================
# STEP 4 — Batch mode
# =====================================================

elif RUN_MODE == "batch":

    experiments = []

    for n_customers in [20, 40, 60, 80]:

        for vehicle_capacity in [15, 25, 35]:

            experiments.append(
                {
                    "instance_name": (
                        f"{n_customers}c_cap{vehicle_capacity}"
                    ),
                    "n_customers": n_customers,
                    "n_iterations": 50,
                    "seed": 42,
                    "initial_temperature": 10.0,
                    "cooling_rate": 0.95,
                    "minimum_temperature": 0.01,
                }
            )


# =====================================================
# STEP 5 — Main execution loop
# =====================================================

for experiment_config in experiments:

    print("\n===================================")
    print("RUNNING INSTANCE")
    print("===================================")

    print(experiment_config)

    instance_name = experiment_config[
        "instance_name"
    ]

    n_customers = experiment_config[
        "n_customers"
    ]

    # =====================================================
    # STEP 5.1 — Dynamic destroy range
    # =====================================================

    max_remove = max(
        3,
        int(0.4 * n_customers)
    )

    n_remove_values = list(
        range(2, max_remove + 1)
    )

    print("\nN_REMOVE RANGE:")
    print(n_remove_values)

    # =====================================================
    # STEP 5.2 — Tracking structures
    # =====================================================

    all_results = []

    best_distance_so_far = float("inf")

    best_result = None

    overall_start_time = time.time()

    # =====================================================
    # STEP 5.3 — Sweep destroy sizes
    # =====================================================

    for n_remove in n_remove_values:

        print("\n-----------------------------------")
        print(f"RUNNING n_remove = {n_remove}")
        print("-----------------------------------")

        run_start_time = time.time()

        # =====================================================
        # STEP 5.4 — Run experiment
        # =====================================================

        result = run_lns_sa_experiment(

            instance_name=instance_name,

            n_iterations=experiment_config[
                "n_iterations"
            ],

            n_remove=n_remove,

            seed=experiment_config[
                "seed"
            ],

            initial_temperature=experiment_config[
                "initial_temperature"
            ],

            cooling_rate=experiment_config[
                "cooling_rate"
            ],

            minimum_temperature=experiment_config[
                "minimum_temperature"
            ],

            save_plot=False,
            save_routes=False,
        )

        run_end_time = time.time()

        runtime_seconds = (
            run_end_time - run_start_time
        )

        # =====================================================
        # STEP 5.5 — Build result entry
        # =====================================================

        result_entry = {

            "experiment_id": EXPERIMENT_ID,

            "timestamp": datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),

            "algorithm": ALGORITHM_NAME,

            "instance_name": instance_name,

            "n_customers": n_customers,

            "n_remove": n_remove,

            "n_iterations": experiment_config[
                "n_iterations"
            ],

            "seed": experiment_config[
                "seed"
            ],

            "initial_temperature": experiment_config[
                "initial_temperature"
            ],

            "cooling_rate": experiment_config[
                "cooling_rate"
            ],

            "minimum_temperature": experiment_config[
                "minimum_temperature"
            ],

            "baseline_reference_distance": result[
                "baseline_reference_distance"
            ],

            "best_distance": result[
                "best_distance"
            ],

            "improvement_distance": result[
                "improvement_distance"
            ],

            "improvement_percent": result[
                "improvement_percent"
            ],

            "n_routes": result[
                "n_routes"
            ],

            "runtime_seconds": runtime_seconds,

            "best_solution": result[
                "best_solution"
            ],
        }

        all_results.append(result_entry)

        # =====================================================
        # STEP 5.6 — Update best run
        # =====================================================

        if result[
            "best_distance"
        ] < best_distance_so_far:

            best_distance_so_far = result[
                "best_distance"
            ]

            best_result = result

            print("\nNEW GLOBAL BEST FOUND")

            print(
                f"Distance: {best_distance_so_far}"
            )

    # =====================================================
    # STEP 5.7 — Final runtime
    # =====================================================

    overall_end_time = time.time()

    total_runtime = (
        overall_end_time - overall_start_time
    )

    # =====================================================
    # STEP 5.8 — Save aggregated JSON
    # =====================================================

    results_folder = os.path.join(
        "results",
        ALGORITHM_NAME,
        instance_name,
    )

    os.makedirs(
        results_folder,
        exist_ok=True,
    )

    aggregated_results = {

        "experiment_id": EXPERIMENT_ID,

        "algorithm": ALGORITHM_NAME,

        "instance_name": instance_name,

        "total_runtime_seconds": total_runtime,

        "n_remove_values": n_remove_values,

        "best_overall_distance": (
            best_distance_so_far
        ),

        "best_overall_n_remove": (
            best_result["n_remove"]
        ),

        "all_runs": all_results,
    }

    aggregated_json_path = os.path.join(
        results_folder,
        "lns_batch_results.json"
    )

    with open(
        aggregated_json_path,
        "w"
    ) as f:

        json.dump(
            aggregated_results,
            f,
            indent=4,
        )

    # =====================================================
    # STEP 5.9 — Save ONLY BEST outputs
    # =====================================================

    best_solution_path = os.path.join(
        results_folder,
        "best_lns_solution.json"
    )

    with open(
        best_solution_path,
        "w"
    ) as f:

        json.dump(
            best_result["best_solution"],
            f,
            indent=4,
        )

    # =====================================================
    # STEP 5.10 — Regenerate best plot
    # =====================================================

    run_lns_sa_experiment(

        instance_name=instance_name,

        n_iterations=experiment_config[
            "n_iterations"
        ],

        n_remove=best_result[
            "n_remove"
        ],

        seed=experiment_config[
            "seed"
        ],

        initial_temperature=experiment_config[
            "initial_temperature"
        ],

        cooling_rate=experiment_config[
            "cooling_rate"
        ],

        minimum_temperature=experiment_config[
            "minimum_temperature"
        ],

        save_plot=True,
        save_routes=True,
    )

    # =====================================================
    # STEP 5.11 — Final summary
    # =====================================================

    print("\n===================================")
    print("INSTANCE COMPLETE")
    print("===================================")

    print(f"Instance: {instance_name}")

    print(
        f"Best Distance: {best_distance_so_far}"
    )

    print(
        f"Best n_remove: {best_result['n_remove']}"
    )

    print(
        f"Runtime: {total_runtime:.2f} sec"
    )




# IMPORTANT SMALL CHANGE REQUIRED

Your current LNS experiment files should eventually return a structured dictionary like:


return {
    "best_solution": best_solution,
    "best_distance": total_lns_distance,
    "baseline_reference_distance": baseline_reference_distance,
    "improvement_distance": improvement_distance,
    "improvement_percent": improvement_percent,
    "n_routes": n_routes,
    "n_remove": n_remove,
}
```

instead of only printing values.

That is the only important architectural addition needed for the runner.
