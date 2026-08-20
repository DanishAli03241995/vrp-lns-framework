"""
Runner for Case 3 Hybrid KMeans fixed depot timing + split repair + LNS-SA.

LNS operator pair:
- Shaw-style Related Removal
- Regret-2 Insertion

Timing behavior:
- starts from the fixed timing split-repaired baseline;
- depot-side LNS is fixed-timing aware;
- supplier-direct LNS uses the standard related-regret LNS engine.
"""

import os
import sys


PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.dirname(__file__)
    )
)
sys.path.append(PROJECT_ROOT)
os.environ.setdefault("MPLCONFIGDIR", os.path.join(PROJECT_ROOT, ".matplotlib_cache"))

from experiments.runners.lns_runner_utils import run_lns_case_runner


CASE_NAME = "Case_3_hybrid_supplier_customer"
STRUCTURE_NAME = "hybrid_supplier_customer"
VARIANT_NAME = "kmeans_fixed_timing_split"
STAGE_NAME = "lns_timing_fixed_split_related_regret"
TARGET_MODULE = (
    "experiments.lns_timing_fixed_split_related_regret."
    "hybrid_supplier_customer."
    "lns_sa_kmeans_timing_fixed_split_related_regret_v1"
)
BASELINE_RESULTS_NAME = "hybrid_supplier_customer_kmeans_timing_fixed_split_v1"
LNS_RESULTS_NAME = "lns_timing_fixed_split_related_regret/case3_kmeans"
ROUTE_SCOPE = "hybrid"
BATCH_CUSTOMER_COUNTS = [20, 40, 60, 80, 100, 150, 200]

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
    batch_customer_counts=BATCH_CUSTOMER_COUNTS,
)
