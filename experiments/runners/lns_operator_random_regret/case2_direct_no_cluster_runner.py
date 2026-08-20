"""Runner for Case 2 Direct No-Cluster LNS-SA with Random + Regret operators."""

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


CASE_NAME = "Case_2_supplier_customer_direct"
STRUCTURE_NAME = "supplier_customer_direct"
VARIANT_NAME = "no_cluster"
STAGE_NAME = "lns_operator_random_regret"
TARGET_MODULE = (
    "experiments.lns_operator_random_regret."
    "supplier_customer_direct.lns_sa_no_cluster_v1"
)
BASELINE_RESULTS_NAME = "supplier_customer_only_no_cluster_v1"
LNS_RESULTS_NAME = "lns_operator_random_regret/case2_no_cluster"
ROUTE_SCOPE = "direct"

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
)
