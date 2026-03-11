# experiment_runner.py

from posixpath import basename
from batch_parsing_functions import *
from ga_engine import *
from results_logger import *

import os
from os.path import basename


def get_files_from_path(path):
    if os.path.isfile(path):
        return [path]
    elif os.path.isdir(path):
        return [
            os.path.join(root, f)
            for root, _, files in os.walk(path)
            for f in files
        ]
    else:
        raise ValueError(f"Invalid path: {path}")


def _run_single_fault_model(circuit_dict, fault_model, filepath,
                             population_size, max_generations,
                             time_limit_seconds, skip_minimization,
                             verbose, sparse_logging):
    """Runs GA for a single fault model and saves results."""
    try:
        if verbose:
            print(f"  [{basename(filepath)}] Starting: {fault_model}")

        GA_object = GeneticAlgorithm(
            circuit_dict,
            faultModel=fault_model,
            verbose=verbose,
            sparse_logging=sparse_logging,
            population_size=population_size,
            max_generations=max_generations,
            time_limit_seconds=time_limit_seconds,
            skip_minimization=skip_minimization
        )

        results = GA_object.run()
        save_results_to_csv(results)

        if verbose:
            print(f"  [{basename(filepath)}] Done: {fault_model}")

        return fault_model, None

    except Exception as e:
        return fault_model, e


def run_pipeline(path,
                 fault_models: list,
                 population_size: int = None,
                 max_generations: int = 20,
                 time_limit_seconds: float = None,
                 skip_minimization=None,
                 verbose=True,
                 sparse_logging=False):
    """
    Runs GA sequentially across fault models — parallelism is handled
    inside each GA run (compute_fitness_for_population) for large circuits.
    """
    real_files = get_files_from_path(path)

    if verbose:
        print(f"Found {len(real_files)} file(s) to process.")
        print(f"Fault models: {fault_models}\n")

    for i, filepath in enumerate(real_files, 1):
        if verbose:
            print(f"[{i}/{len(real_files)}] Circuit: {basename(filepath)}")

        circuit_dict = parse_real_file(filepath)

        # ── Sequential: one fault model at a time ─────────────────────────────
        # Inner parallelism (population vectors) handles speedup for large circuits
        for fault_model in fault_models:
            fault_model, error = _run_single_fault_model(
                circuit_dict, fault_model, filepath,
                population_size, max_generations,
                time_limit_seconds, skip_minimization,
                verbose, sparse_logging
            )
            if error:
                print(f"  [ERROR] {basename(filepath)} | {fault_model}: {error}")

        del circuit_dict

        if verbose:
            print(f"  All fault models complete for: {basename(filepath)}\n")

    if verbose:
        print("Pipeline complete.")