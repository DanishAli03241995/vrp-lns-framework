"""
Runner for Case 3 Hybrid KMeans dispatch-wave timing + split repair + speed40 + LNS-SA.

LNS operator pair:
- Shaw-style Related Removal
- Regret-2 Insertion

Timing behavior:
- starts from the dispatch-wave speed40 split-repaired baseline;
- depot-side LNS is dispatch-wave aware;
- depot customers stay inside their assigned dispatch-wave bucket;
- supplier-direct LNS uses the standard related-regret LNS engine.
"""

import os
import sys


def find_project_root(start_path):
    """Find the project root robustly from either a runners folder or nested experiment folder."""
    current_path = os.path.abspath(start_path)

    for _ in range(8):
        has_experiments = os.path.isdir(os.path.join(current_path, "experiments"))
        has_metaheuristics = os.path.isdir(os.path.join(current_path, "metaheuristics"))

        if has_experiments and has_metaheuristics:
            return current_path

        parent_path = os.path.dirname(current_path)

        if parent_path == current_path:
            break

        current_path = parent_path

    raise RuntimeError("Could not locate project root from runner location.")


PROJECT_ROOT = find_project_root(os.path.dirname(__file__))
sys.path.append(PROJECT_ROOT)
os.environ.setdefault("MPLCONFIGDIR", os.path.join(PROJECT_ROOT, ".matplotlib_cache"))

from experiments.runners.lns_runner_utils import run_lns_case_runner


CASE_NAME = "Case_3_hybrid_supplier_customer"
STRUCTURE_NAME = "hybrid_supplier_customer"
VARIANT_NAME = "kmeans_dispatch_wave_split_speed40"
STAGE_NAME = "lns_waves_split_speed40_related_regret"
TARGET_MODULE = (
    "experiments.lns_timing_waves_split_speed40_related_regret."
    "hybrid_supplier_customer."
    "lns_sa_kmeans_waves_split_speed40_related_regret_v1"
)

def resolve_baseline_results_name():
    """Prefer the explicit speed40 folder, with a fallback to the generic folder."""
    candidate_names = [
        "hybrid_supplier_customer_kmeans_timing_waves_constructed_split_v1_40_speed",
        "hybrid_supplier_customer_kmeans_timing_waves_constructed_split_v1",
    ]

    for candidate_name in candidate_names:
        candidate_path = os.path.join(PROJECT_ROOT, "results", candidate_name)

        if os.path.isdir(candidate_path):
            return candidate_name

    return candidate_names[0]


BASELINE_RESULTS_NAME = resolve_baseline_results_name()

LNS_RESULTS_NAME = "lns_timing_waves_split_speed40_related_regret/case3_kmeans"
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
