"""Generate comparison rows with best LNS-SA fields only."""

import csv
import json
import os
import sys


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(PROJECT_ROOT)


CASE_CONFIGS = [
    {
        "case": "Case_2_supplier_customer_direct",
        "structure": "supplier_customer_direct",
        "variant": "sweep",
        "baseline_results_name": "supplier_customer_only_baseline_sweep_v1",
    },
    {
        "case": "Case_2_supplier_customer_direct",
        "structure": "supplier_customer_direct",
        "variant": "kmeans",
        "baseline_results_name": "supplier_customer_only_baseline_kmeans_v1",
    },
    {
        "case": "Case_2_supplier_customer_direct",
        "structure": "supplier_customer_direct",
        "variant": "no_cluster",
        "baseline_results_name": "supplier_customer_only_no_cluster_v1",
    },
    {
        "case": "Case_3_hybrid_supplier_customer",
        "structure": "hybrid_supplier_customer",
        "variant": "sweep",
        "baseline_results_name": "hybrid_supplier_customer_sweep_v1",
    },
    {
        "case": "Case_3_hybrid_supplier_customer",
        "structure": "hybrid_supplier_customer",
        "variant": "kmeans",
        "baseline_results_name": "hybrid_supplier_customer_kmeans_v1",
    },
    {
        "case": "Case_3_hybrid_supplier_customer",
        "structure": "hybrid_supplier_customer",
        "variant": "no_cluster",
        "baseline_results_name": "hybrid_supplier_customer_no_cluster_v1",
    },
]


OUTPUT_JSON = os.path.join(
    PROJECT_ROOT,
    "results",
    "lns_comparison_table.json",
)

OUTPUT_CSV = os.path.join(
    PROJECT_ROOT,
    "results",
    "lns_comparison_table.csv",
)


def get_latest_run_folder(instance_path):
    run_folders = []

    for folder in os.listdir(instance_path):
        full_path = os.path.join(instance_path, folder)

        if os.path.isdir(full_path) and folder.startswith("run_"):
            run_folders.append(folder)

    if not run_folders:
        return None

    run_folders.sort()
    return os.path.join(instance_path, run_folders[-1])


def load_json_if_exists(path):
    if not os.path.exists(path):
        return None

    with open(path, "r") as file_handle:
        return json.load(file_handle)


def iter_instance_paths(baseline_results_name):
    results_root = os.path.join(
        PROJECT_ROOT,
        "results",
        baseline_results_name,
    )

    if not os.path.isdir(results_root):
        return

    for instance_name in sorted(os.listdir(results_root)):
        instance_path = os.path.join(results_root, instance_name)

        if os.path.isdir(instance_path):
            yield instance_name, instance_path


def extract_best_lns_fields(run_path):
    runner_summary = load_json_if_exists(
        os.path.join(run_path, "lns_sa_runner_summary.json")
    )

    if runner_summary is not None and runner_summary.get("best_run"):
        best_run = runner_summary["best_run"]["run"]

        return {
            "lns_best_distance": best_run["total_lns_distance"],
            "lns_best_n_remove": best_run["n_remove"],
            "lns_improvement_distance": best_run[
                "improvement_distance"
            ],
            "lns_improvement_percent": best_run[
                "improvement_percent"
            ],
            "lns_runtime_seconds": best_run["runtime_seconds"],
            "lns_runs_tested": len(runner_summary.get("runs", [])),
            "lns_experiment_id": runner_summary["experiment_id"],
            "lns_source": "lns_sa_runner_summary.json",
        }

    lns_summary = load_json_if_exists(
        os.path.join(run_path, "lns_sa_summary.json")
    )

    if lns_summary is not None:
        return {
            "lns_best_distance": lns_summary["final_distance"],
            "lns_best_n_remove": lns_summary["n_remove"],
            "lns_improvement_distance": lns_summary[
                "improvement_distance"
            ],
            "lns_improvement_percent": lns_summary[
                "improvement_percent"
            ],
            "lns_runtime_seconds": None,
            "lns_runs_tested": 1,
            "lns_experiment_id": None,
            "lns_source": "lns_sa_summary.json",
        }

    return {
        "lns_best_distance": None,
        "lns_best_n_remove": None,
        "lns_improvement_distance": None,
        "lns_improvement_percent": None,
        "lns_runtime_seconds": None,
        "lns_runs_tested": 0,
        "lns_experiment_id": None,
        "lns_source": None,
    }


def build_row(case_config, instance_name, run_path):
    baseline_summary = load_json_if_exists(
        os.path.join(run_path, "summary.json")
    )
    baseline_metrics = load_json_if_exists(
        os.path.join(run_path, "metrics.json")
    )

    if baseline_summary is None:
        baseline_summary = {}

    if baseline_metrics is None:
        baseline_metrics = {}

    lns_fields = extract_best_lns_fields(run_path)

    row = {
        "case": case_config["case"],
        "structure": case_config["structure"],
        "variant": case_config["variant"],
        "baseline_results_name": case_config[
            "baseline_results_name"
        ],
        "instance": instance_name,
        "run_folder": run_path,
        "baseline_algorithm": baseline_summary.get(
            "algorithm",
            baseline_metrics.get("algorithm"),
        ),
        "n_customers": baseline_summary.get(
            "n_customers",
            baseline_metrics.get("n_customers"),
        ),
        "vehicle_capacity": baseline_summary.get(
            "vehicle_capacity",
            baseline_metrics.get("vehicle_capacity"),
        ),
        "baseline_distance": baseline_summary.get(
            "baseline_distance",
            baseline_metrics.get("baseline_distance"),
        ),
        "baseline_final_distance": baseline_summary.get(
            "final_distance",
            baseline_metrics.get("post_reloc_2opt_distance"),
        ),
        "baseline_improvement_distance": baseline_summary.get(
            "improvement_distance"
        ),
        "baseline_improvement_percent": baseline_summary.get(
            "improvement_percent"
        ),
        "trips": baseline_summary.get(
            "trips",
            baseline_metrics.get("trips"),
        ),
        "avg_utilization": baseline_summary.get(
            "avg_utilization",
            baseline_metrics.get("post_reloc_2opt_avg_utilization"),
        ),
        "feasible": baseline_summary.get(
            "feasible",
            baseline_metrics.get("capacity_feasibility"),
        ),
        "structural_validity": baseline_summary.get(
            "structural_validity",
            baseline_metrics.get("structural_validity"),
        ),
        "customers_served": baseline_summary.get(
            "customers_served",
            baseline_metrics.get("all_customers_served"),
        ),
    }

    row.update(lns_fields)

    return row


def build_lns_comparison_table():
    rows = []

    for case_config in CASE_CONFIGS:
        for instance_name, instance_path in iter_instance_paths(
            case_config["baseline_results_name"]
        ):
            latest_run_path = get_latest_run_folder(instance_path)

            if latest_run_path is None:
                continue

            rows.append(
                build_row(
                    case_config,
                    instance_name,
                    latest_run_path,
                )
            )

    return rows


def write_outputs(rows):
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)

    with open(OUTPUT_JSON, "w") as file_handle:
        json.dump(rows, file_handle, indent=4)

    if not rows:
        return

    fieldnames = list(rows[0].keys())

    with open(OUTPUT_CSV, "w", newline="") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    comparison_rows = build_lns_comparison_table()
    write_outputs(comparison_rows)

    print("\n===================================")
    print("LNS COMPARISON TABLE GENERATED")
    print("===================================")
    print("Rows:", len(comparison_rows))
    print("JSON:", OUTPUT_JSON)
    print("CSV:", OUTPUT_CSV)
