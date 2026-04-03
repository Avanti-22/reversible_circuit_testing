# experiment_runner.py

from posixpath import basename
from batch_parsing_functions import *
from ga_engine import *
from results_logger import *
from directed_init_patch import *
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


def _normalize_jobs(fault_models) -> list:
    """
    Normalise fault_models into a flat list of jobs.

    Each job is either:
      - str        → individual run   e.g. "SMGF"
      - list[str]  → combined run     e.g. ["SMGF", "SAF"]

    Accepted input shapes:
      "SMGF"                        → [("SMGF")]
      ["SMGF", "SAF"]               → ["SMGF", "SAF"]      (two individual jobs)
      [["SMGF", "SAF"]]             → [["SMGF", "SAF"]]    (one combined job)
      ["SMGF", ["SMGF", "SAF"]]     → mixed
    """
    if isinstance(fault_models, str):
        return [fault_models]

    if isinstance(fault_models, list):
        jobs = []
        for item in fault_models:
            if isinstance(item, str):
                jobs.append(item)           # individual
            elif isinstance(item, list):
                if len(item) == 0:
                    raise ValueError("Empty list found inside fault_models.")
                if len(item) == 1:
                    jobs.append(item[0])    # single-element list → treat as individual
                else:
                    jobs.append(item)       # combined
            else:
                raise ValueError(f"Unexpected type in fault_models: {type(item)}")
        return jobs

    raise ValueError(f"fault_models must be a str or list, got {type(fault_models)}")


def _job_label(job) -> str:
    return "+".join(job) if isinstance(job, list) else job


def _run_single_job(circuit_dict, ga_approach, job, filepath,
                    population_size, max_generations,
                    time_limit_seconds, skip_minimization,
                    verbose, sparse_logging):
    """
    Runs GA for one job.

    job : str   → single fault model  e.g. "SMGF"
          list  → combined fault models e.g. ["SMGF", "SAF"]
    """
    label = _job_label(job)

    try:
        if verbose:
            print(f"  [{basename(filepath)}] Starting: {label}")

        if ga_approach == "Directed":
            patch_ga_with_directed_init(GeneticAlgorithm)

        GA_object = GeneticAlgorithm(
            circuit_dict,
            faultModel=job,                  # GA __init__ handles str or list
            verbose=verbose,
            sparse_logging=sparse_logging,
            population_size=population_size,
            max_generations=max_generations,
            time_limit_seconds=time_limit_seconds,
            skip_minimization=skip_minimization,
        )

        results = GA_object.run()
        save_results_to_csv(results)

        if verbose:
            print(f"  [{basename(filepath)}] Done: {label} | "
                  f"Coverage: {results['Fault Coverage']:.2f}%")

        return label, None

    except Exception as e:
        return label, e


def run_pipeline(path,
                 ga_approach,
                 fault_models,
                 population_size: int = None,
                 max_generations: int = 20,
                 time_limit_seconds: float = None,
                 skip_minimization=None,
                 verbose=True,
                 sparse_logging=False):
    """
    Runs the GA pipeline across circuits and fault models.

    fault_models examples
    ─────────────────────
    Individual runs:
        ["SMGF", "SAF", "MMGF"]
        → 3 separate GA runs, one per model

    Combined run:
        [["SMGF", "SAF", "MMGF"]]
        → 1 GA run with all models fused, saved as "SMGF+SAF+MMGF"

    Mix of both:
        ["SMGF", ["SMGF", "SAF"]]
        → "SMGF" individual + "SMGF+SAF" combined
    """
    real_files = get_files_from_path(path)
    jobs = _normalize_jobs(fault_models)

    if verbose:
        print(f"Found {len(real_files)} file(s) to process.")
        print(f"GA Approach : {ga_approach}")
        print(f"Jobs        : {[_job_label(j) for j in jobs]}\n")

    for i, filepath in enumerate(real_files, 1):
        if verbose:
            print(f"[{i}/{len(real_files)}] Circuit: {basename(filepath)}")

        circuit_dict = parse_real_file(filepath)

        for job in jobs:
            label, error = _run_single_job(
                circuit_dict, ga_approach, job, filepath,
                population_size, max_generations,
                time_limit_seconds, skip_minimization,
                verbose, sparse_logging,
            )
            if error:
                print(f"  [ERROR] {basename(filepath)} | {label}: {error}")

        del circuit_dict

        if verbose:
            print(f"  All jobs complete for: {basename(filepath)}\n")

    if verbose:
        print("Pipeline complete.")