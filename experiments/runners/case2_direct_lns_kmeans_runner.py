"""Runner for Case 2 supplier-customer direct KMeans LNS-SA."""

from lns_runner_utils import run_lns_case_runner


CASE_NAME = "Case_2_supplier_customer_direct"
STRUCTURE_NAME = "supplier_customer_direct"
VARIANT_NAME = "kmeans"
STAGE_NAME = "lns_sa"
TARGET_MODULE = "experiments.lns.supplier_customer_direct.lns_sa_kmeans_v1"
BASELINE_RESULTS_NAME = "supplier_customer_only_baseline_kmeans_v1"
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
)
