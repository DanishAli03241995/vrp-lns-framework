"""Runner for Case 3 hybrid supplier-customer Sweep LNS-SA."""

from lns_runner_utils import run_lns_case_runner


CASE_NAME = "Case_3_hybrid_supplier_customer"
STRUCTURE_NAME = "hybrid_supplier_customer"
VARIANT_NAME = "sweep"
STAGE_NAME = "lns_sa"
TARGET_MODULE = "experiments.lns.hybrid_supplier_customer.lns_sa_sweep_v1"
BASELINE_RESULTS_NAME = "hybrid_supplier_customer_sweep_v1"
ROUTE_SCOPE = "hybrid"
BATCH_CUSTOMER_COUNTS = [100, 150, 200]

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
    batch_customer_counts=BATCH_CUSTOMER_COUNTS,
)
