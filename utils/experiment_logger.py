"""Experiment result-folder helpers."""

from datetime import datetime
from pathlib import Path


def create_experiment_folder(algorithm_name, instance_name, base_dir="results"):
    timestamp = datetime.now().strftime("run_%Y_%m_%d_%H%M%S")
    results_path = Path(base_dir) / algorithm_name / instance_name / timestamp
    results_path.mkdir(parents=True, exist_ok=True)

    return str(results_path)
