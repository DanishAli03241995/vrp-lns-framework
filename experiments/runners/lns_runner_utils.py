"""Shared utilities for LNS-SA case runners."""

import ast
import importlib
import json
import os
import shutil
import sys
import time
from datetime import datetime


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(PROJECT_ROOT)
os.environ.setdefault("MPLCONFIGDIR", os.path.join(PROJECT_ROOT, ".matplotlib_cache"))


def get_latest_run_folder(instance_path):
    run_folders = []

    for folder in os.listdir(instance_path):
        full_path = os.path.join(instance_path, folder)

        if os.path.isdir(full_path) and folder.startswith("run_"):
            run_folders.append(folder)

    if not run_folders:
        raise FileNotFoundError(
            f"No run_* folders found under: {instance_path}"
        )

    run_folders.sort()
    return os.path.join(instance_path, run_folders[-1])


def count_route_customers(routes):
    customers = set()

    for route in routes:
        for node in route:
            if node != 0:
                customers.add(node)

    return len(customers)


def get_component_customer_counts(metrics, route_scope):
    component_counts = []

    if route_scope == "direct":
        for supplier_data in metrics["supplier_metrics"].values():
            component_counts.append(
                count_route_customers(
                    supplier_data["route_post_reloc_2opt"]
                )
            )

    elif route_scope == "hybrid":
        depot_routes = []

        for record in metrics["post_reloc_2opt_route_records"]:
            if record["origin_type"] == "depot":
                depot_routes.append(record["trip"])

        if depot_routes:
            component_counts.append(count_route_customers(depot_routes))

        for supplier_data in metrics["supplier_metrics"].values():
            component_counts.append(
                count_route_customers(
                    supplier_data["route_post_reloc_2opt"]
                )
            )

    else:
        raise ValueError(f"Unsupported route_scope: {route_scope}")

    return [count for count in component_counts if count > 0]


def get_dynamic_n_remove_values(
    baseline_results_name,
    instance_name,
    route_scope,
):
    instance_path = os.path.join(
        PROJECT_ROOT,
        "results",
        baseline_results_name,
        instance_name,
    )
    latest_run_path = get_latest_run_folder(instance_path)
    metrics_path = os.path.join(latest_run_path, "metrics.json")

    with open(metrics_path, "r") as file_handle:
        metrics = json.load(file_handle)

    component_counts = get_component_customer_counts(
        metrics,
        route_scope,
    )

    if not component_counts:
        return [2]

    local_customer_count = max(component_counts)
    max_remove = max(2, int(0.4 * local_customer_count))

    return list(range(2, max_remove + 1))


def build_instance_names(run_mode, batch_customer_counts=None):
    if run_mode == "test":
        return ["40c_cap25"]

    if run_mode == "batch":
        instance_names = []
        customer_counts = batch_customer_counts or [20, 40, 60, 80]

        for n_customers in customer_counts:
            for vehicle_capacity in [15, 25, 35]:
                instance_names.append(
                    f"{n_customers}c_cap{vehicle_capacity}"
                )

        return instance_names

    raise ValueError(f"Unsupported RUN_MODE: {run_mode}")


def write_batch_summary(
    run_path,
    summary_filename,
    summary_payload,
):
    summary_path = os.path.join(run_path, summary_filename)

    with open(summary_path, "w") as file_handle:
        json.dump(summary_payload, file_handle, indent=4)

    return summary_path


def create_lns_run_folder(
    baseline_results_name,
    instance_name,
    lns_results_name=None,
):
    if lns_results_name is None:
        lns_results_name = f"lns_{baseline_results_name}"

    run_folder_name = f"run_{datetime.now().strftime('%Y_%m_%d_%H%M%S')}"
    run_path = os.path.join(
        PROJECT_ROOT,
        "results",
        lns_results_name,
        instance_name,
        run_folder_name,
    )

    os.makedirs(run_path, exist_ok=True)

    return run_path


def copy_if_exists(source_path, target_path):
    if os.path.exists(source_path):
        shutil.copyfile(source_path, target_path)
        return target_path

    return None


def write_best_lns_solution_json(latest_run_path):
    route_path = os.path.join(latest_run_path, "route_lns_sa.txt")
    target_path = os.path.join(latest_run_path, "best_lns_solution.json")

    if not os.path.exists(route_path):
        return None

    with open(route_path, "r") as file_handle:
        route_text = file_handle.read()

    best_solution = ast.literal_eval(route_text)

    with open(target_path, "w") as file_handle:
        json.dump(best_solution, file_handle, indent=4)

    return target_path


def preserve_best_outputs(
    run_path,
):
    best_files = {}

    file_pairs = [
        ("route_lns_sa.txt", "route_lns_sa_best.txt"),
        (
            "route_lns_sa_records.json",
            "route_lns_sa_records_best.json",
        ),
        ("lns_sa_metrics.json", "lns_sa_metrics_best.json"),
        ("lns_sa_summary.json", "lns_sa_summary_best.json"),
        ("route_plot_lns_sa.png", "route_plot_lns_sa_best.png"),
        (
            "route_plot_lns_sa_plot_skipped.txt",
            "route_plot_lns_sa_best_plot_skipped.txt",
        ),
    ]

    for source_name, target_name in file_pairs:
        copied_path = copy_if_exists(
            os.path.join(run_path, source_name),
            os.path.join(run_path, target_name),
        )

        if copied_path is not None:
            best_files[target_name] = copied_path

    best_solution_path = write_best_lns_solution_json(run_path)

    if best_solution_path is not None:
        best_files["best_lns_solution.json"] = best_solution_path

    return best_files


def run_lns_case_runner(
    case_name,
    structure_name,
    variant_name,
    stage_name,
    target_module,
    baseline_results_name,
    route_scope,
    run_mode="test",
    test_n_remove_values=None,
    n_iterations=50,
    seed=42,
    initial_temperature=10.0,
    cooling_rate=0.95,
    minimum_temperature=0.01,
    lns_results_name=None,
    batch_customer_counts=None,
):
    experiment_id = (
        f"{case_name}_{variant_name}_{stage_name}_"
        f"{datetime.now().strftime('%Y_%m_%d_%H%M%S')}"
    )

    module = importlib.import_module(target_module)
    run_lns_sa_experiment = module.run_lns_sa_experiment

    instance_names = build_instance_names(
        run_mode,
        batch_customer_counts=batch_customer_counts,
    )

    for instance_name in instance_names:
        lns_run_path = create_lns_run_folder(
            baseline_results_name,
            instance_name,
            lns_results_name=lns_results_name,
        )

        if run_mode == "test":
            n_remove_values = test_n_remove_values or [2]
        else:
            n_remove_values = get_dynamic_n_remove_values(
                baseline_results_name,
                instance_name,
                route_scope,
            )

        print("\n===================================")
        print("LNS RUNNER TARGET")
        print("===================================")
        print("case:", case_name)
        print("structure:", structure_name)
        print("variant:", variant_name)
        print("stage:", stage_name)
        print("target_module:", target_module)
        print("instance:", instance_name)
        print("n_remove_values:", n_remove_values)
        print("lns_output_path:", lns_run_path)

        all_runs = []
        best_result = None
        best_distance = float("inf")

        for n_remove in n_remove_values:
            print("\n-----------------------------------")
            print(f"Running n_remove = {n_remove}")
            print("-----------------------------------")

            start_time = time.time()

            result = run_lns_sa_experiment(
                instance_name=instance_name,
                n_iterations=n_iterations,
                n_remove=n_remove,
                seed=seed,
                initial_temperature=initial_temperature,
                cooling_rate=cooling_rate,
                minimum_temperature=minimum_temperature,
                output_path=lns_run_path,
            )

            runtime_seconds = time.time() - start_time

            distance = result["total_lns_distance"]

            run_entry = {
                "experiment_id": experiment_id,
                "timestamp": datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "case": case_name,
                "structure": structure_name,
                "variant": variant_name,
                "stage": stage_name,
                "target_module": target_module,
                "instance": instance_name,
                "n_iterations": n_iterations,
                "n_remove": n_remove,
                "seed": seed,
                "initial_temperature": initial_temperature,
                "cooling_rate": cooling_rate,
                "minimum_temperature": minimum_temperature,
                "baseline_reference_distance": result[
                    "baseline_reference_distance"
                ],
                "total_lns_distance": distance,
                "improvement_distance": result[
                    "improvement_distance"
                ],
                "improvement_percent": result[
                    "improvement_percent"
                ],
                "n_routes": result["n_routes"],
                "runtime_seconds": runtime_seconds,
            }

            all_runs.append(run_entry)

            if distance < best_distance:
                best_distance = distance
                best_result = {
                    "run": run_entry,
                    "full_result": result,
                }

        if best_result is not None:
            best_n_remove = best_result["run"]["n_remove"]
            last_n_remove = n_remove_values[-1]

            if best_n_remove != last_n_remove:
                print("\n===================================")
                print("Re-running best n_remove so saved route/plot files match best run")
                print("===================================")
                print("best_n_remove:", best_n_remove)

                run_lns_sa_experiment(
                    instance_name=instance_name,
                    n_iterations=n_iterations,
                    n_remove=best_n_remove,
                    seed=seed,
                    initial_temperature=initial_temperature,
                    cooling_rate=cooling_rate,
                    minimum_temperature=minimum_temperature,
                    output_path=lns_run_path,
                )

            best_output_files = preserve_best_outputs(lns_run_path)
        else:
            best_output_files = {}

        summary_payload = {
            "experiment_id": experiment_id,
            "case": case_name,
            "structure": structure_name,
            "variant": variant_name,
            "stage": stage_name,
            "target_module": target_module,
            "baseline_results_name": baseline_results_name,
            "lns_results_name": (
                lns_results_name
                if lns_results_name is not None
                else f"lns_{baseline_results_name}"
            ),
            "lns_run_path": lns_run_path,
            "route_scope": route_scope,
            "run_mode": run_mode,
            "instance": instance_name,
            "n_remove_values": n_remove_values,
            "runs": all_runs,
            "best_run": best_result,
            "best_output_files": best_output_files,
        }

        summary_path = write_batch_summary(
            lns_run_path,
            "lns_sa_runner_summary.json",
            summary_payload,
        )

        print("\n===================================")
        print("LNS RUNNER SUMMARY SAVED")
        print("===================================")
        print(summary_path)
