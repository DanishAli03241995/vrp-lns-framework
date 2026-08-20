"""Runner for supplier-customer-only sweep experiments."""

# ========================================
# STEP 1 — Add import
# ========================================

from supplier_customer_only_baseline_sweep_v1 import run_experiment

ALGORITHM_NAME = "supplier_customer_sweep"

# ALGORITHM_NAME = "supplier_customer_kmeans"

# ========================================
# STEP 2 — Select run mode
# ========================================

RUN_MODE = "test"

# RUN_MODE = "batch"

# ========================================
# STEP 3 — Define test-mode configurations
# ========================================

if RUN_MODE == "test":

    # ========================================
    # STEP 3.1 — Scale spatial region size
    # ========================================

    n_customers = 40

    if n_customers == 20:
        grid_size = 10

    elif n_customers == 40:
        grid_size = 20

    elif n_customers == 60:
        grid_size = 30

    elif n_customers == 80:
        grid_size = 40

    experiments = [
        {
            "n_customers": n_customers,
            "vehicle_capacity": 25,
            "n_suppliers": 3,
            "seed": 42,

            # "direct_delivery_threshold": 5,

            "grid_size": grid_size,
        }
    ]

# ========================================
# STEP 4 — Define batch-mode configurations
# ========================================

elif RUN_MODE == "batch":

    experiments = []

    for n_customers in [20, 40, 60, 80]:

        # ========================================
        # STEP 4.1 — Scale spatial region size
        # ========================================

        if n_customers == 20:
            grid_size = 10

        elif n_customers == 40:
            grid_size = 20

        elif n_customers == 60:
            grid_size = 30

        elif n_customers == 80:
            grid_size = 40

        for vehicle_capacity in [15, 25, 35]:

            experiments.append(
                {
                    "n_customers": n_customers,
                    "vehicle_capacity": vehicle_capacity,
                    "n_suppliers": 3,
                    "seed": 42,

                    # "direct_delivery_threshold": 5,

                    "grid_size": grid_size,
                }
            )

# ========================================
# STEP 5 — Execute configurations
# ========================================

for config in experiments:

    config["algorithm"] = ALGORITHM_NAME

    config["experiment_name"] = (
        f"{config['n_customers']}c_cap{config['vehicle_capacity']}"
    )

    print("\n===================================")
    print("Running experiment:")
    print(config)
    print("===================================\n")

    run_experiment(config)