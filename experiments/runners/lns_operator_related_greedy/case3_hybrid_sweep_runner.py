"""Runner for Case 3 Hybrid Sweep LNS-SA with Related + Greedy operators."""

import os
import sys


PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(__file__)
        )
    )
)
sys.path.append(PROJECT_ROOT)

from experiments.runners.lns_runner_utils import run_lns_case_runner


CASE_NAME = "Case_3_hybrid_supplier_customer"
STRUCTURE_NAME = "hybrid_supplier_customer"
VARIANT_NAME = "sweep"
STAGE_NAME = "lns_operator_related_greedy"
TARGET_MODULE = (
    "experiments.lns_operator_related_greedy."
    "hybrid_supplier_customer.lns_sa_sweep_v1"
)
BASELINE_RESULTS_NAME = "hybrid_supplier_customer_sweep_v1"
LNS_RESULTS_NAME = "lns_operator_related_greedy/case3_sweep"
ROUTE_SCOPE = "hybrid"

# RUN_MODE = "test"
RUN_MODE = "batch"


run_lns_case_runner(
    case_name=CASE_NAME,
    structure_name=STRUCTURE_NAME,
    variant_name=VARIANT_NAME,
    stage_name=STAGE_NAME,
    target_module=TARGET_MODULE,
    baseline_results_name=BASELINE_RESULTS_NAME,
    route_scope=ROUTE_SCOPE,
    run_mode=RUN_MODE,
    lns_results_name=LNS_RESULTS_NAME,
    batch_customer_counts=[100, 150, 200],
)
