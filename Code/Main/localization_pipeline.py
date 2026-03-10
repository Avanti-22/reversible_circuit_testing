

from __future__ import annotations

import ast
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from os.path import basename
from typing import List, Optional

import pandas as pd
import numpy as np

# filelock: used for thread-safe CSV writes (same as results_logger.py)
try:
    from filelock import FileLock as _FileLock
except ImportError:
    import threading
    class _FileLock:                          # noqa: E302  (fallback stub)
        """Fallback in-process lock when filelock package is absent."""
        _locks: dict = {}
        _meta  = threading.Lock()
        def __init__(self, path):
            with _FileLock._meta:
                if path not in _FileLock._locks:
                    _FileLock._locks[path] = threading.Lock()
            self._lock = _FileLock._locks[path]
        def __enter__(self):  self._lock.acquire(); return self
        def __exit__(self, *_): self._lock.release()

# pytz: optional — falls back to local time
try:
    import pytz as _pytz
    _IST = _pytz.timezone("Asia/Kolkata")
    def _now_isodate() -> tuple:
        n = datetime.now(_IST); return n.strftime("%Y-%m-%d"), n.strftime("%H:%M:%S")
except ImportError:
    _IST = None
    def _now_isodate() -> tuple:
        n = datetime.now(); return n.strftime("%Y-%m-%d"), n.strftime("%H:%M:%S")

from batch_parsing_functions import parse_real_file
from rsvs_fault_localizer    import RSVSLocalizer

# ── Output settings (mirrors results_logger.py) ───────────────────────────────
OUTPUT_DIR = r"Code\Main\Output"


# ══════════════════════════════════════════════════════════════════════════════
#  CSV helpers
# ══════════════════════════════════════════════════════════════════════════════

def _save_localization_row(row: dict, output_dir: str = OUTPUT_DIR):
    """
    Thread-safe append of one result row to RSVS_Localization.csv.
    Same pattern as results_logger.save_results_to_csv.
    """
    os.makedirs(output_dir, exist_ok=True)
    csv_path  = os.path.join(output_dir, "RSVS_Localization.csv")
    lock_path = os.path.join(output_dir, "RSVS_Localization.lock")

    date_str, time_str = _now_isodate()
    row["date"] = date_str
    row["time"] = time_str

    record = pd.DataFrame([row])

    with _FileLock(lock_path):
        if os.path.exists(csv_path):
            record.to_csv(csv_path, mode="a", header=False,
                          index=False, lineterminator="\n")
        else:
            record.to_csv(csv_path, mode="w", header=True,
                          index=False, lineterminator="\n")
            print(f"  Localization sheet created at: {os.path.abspath(csv_path)}")


def _load_detection_sheet(detection_csv: str) -> pd.DataFrame:
    """Load and validate the GA detection results CSV."""
    if not os.path.exists(detection_csv):
        raise FileNotFoundError(f"Detection sheet not found: {detection_csv}")

    df = pd.read_csv(detection_csv)

    required = {"Circuit Name", "Fault Model", "Best Vector Set",
                "No of Lines", "No of Gates"}
    missing  = required - set(df.columns)
    if missing:
        raise ValueError(
            f"Detection sheet is missing columns: {missing}\n"
            f"Available columns: {list(df.columns)}\n"
            f"Ensure your GA pipeline saves 'Best Vector Set' in save_results()."
        )
    return df


def _parse_vector_set(raw) -> Optional[List[int]]:
    """
    Safely parse the 'Best Vector Set' column.
    The GA saves it as a Python list repr string e.g. "[3, 7, 12, 15]".
    Returns list[int] or None on failure.
    """
    if raw is None or (isinstance(raw, float) and np.isnan(raw)):
        return None
    if isinstance(raw, list):
        return [int(v) for v in raw]
    try:
        parsed = ast.literal_eval(str(raw))
        if isinstance(parsed, (list, tuple)):
            return [int(v) for v in parsed]
    except (ValueError, SyntaxError):
        pass
    return None


# ══════════════════════════════════════════════════════════════════════════════
#  File finder  (same as experiment_runner.get_files_from_path)
# ══════════════════════════════════════════════════════════════════════════════

def _get_real_files(path: str) -> List[str]:
    if os.path.isfile(path):
        return [path]
    elif os.path.isdir(path):
        return [
            os.path.join(root, f)
            for root, _, files in os.walk(path)
            for f in files
            if f.endswith(".real")
        ]
    raise ValueError(f"Invalid path: {path}")


# ══════════════════════════════════════════════════════════════════════════════
#  Single-circuit, single-fault-model worker
# ══════════════════════════════════════════════════════════════════════════════

def _run_single_localization(
        circuit_dict : dict,
        fault_model  : str,
        test_set     : List[int],
        filepath     : str,
        max_mmgf_order: int,
        verbose      : bool,
        output_dir   : str) -> tuple:
    """
    Builds the RSVS dictionary for one (circuit, fault_model, test_set)
    combination, then localises every detectable fault and saves results.

    Returns (fault_model, error_or_None).
    """
    circuit_name = circuit_dict.get("Circuit Name", basename(filepath))

    try:
        if verbose:
            print(f"  [{circuit_name}] Localizing: {fault_model}  "
                  f"({len(test_set)} test vectors)")

        t_start = time.perf_counter()

        # ── Build offline dictionary ──────────────────────────────────────────
        localizer = RSVSLocalizer(
            circuit_dict,
            test_set,
            fault_model=fault_model
        )
        localizer.build_dictionary(max_mmgf_order=max_mmgf_order)

        # ── Enumerate all fault hypotheses covered by this fault model ────────
        fault_hypotheses = _enumerate_hypotheses(
            circuit_dict, fault_model, max_mmgf_order)

        n_total    = len(fault_hypotheses)
        n_located  = 0
        n_equiv    = 0
        n_no_match = 0

        # ── Localize each fault ───────────────────────────────────────────────
        for hyp_type, hyp_gate_ids, hyp_missing_mask in fault_hypotheses:

            # Simulate CUT with injected fault → get actual outputs
            actual_outputs = localizer.simulate_cut(
                fault_type   = hyp_type,
                gate_ids     = hyp_gate_ids,
                missing_mask = hyp_missing_mask
            )

            # Run RSVS localizer
            result = localizer.localize(actual_outputs,
                                        resolve_equiv=True,
                                        verbose=False)

            # ── Determine if localization matched the injected fault ──────────
            if result.status == "no_fault":
                # test set didn't detect this fault — skip (detection job's responsibility)
                continue

            located_correctly = False
            if result.primary:
                type_match = result.primary.fault_type == hyp_type
                ids_match  = sorted(result.primary.gate_ids) == sorted(hyp_gate_ids)
                mask_match = (hyp_type != "PMGF" or
                              result.primary.missing_mask == hyp_missing_mask)
                located_correctly = type_match and ids_match and mask_match

            if result.status == "located":
                n_located += 1 if located_correctly else 0
            elif result.status == "equiv_class":
                n_equiv += 1
            else:
                n_no_match += 1

            # ── Save per-fault row ────────────────────────────────────────────
            row = {
                "Circuit Name"        : circuit_name,
                "No of Lines"         : circuit_dict["No of Lines"],
                "No of Gates"         : circuit_dict["No of Gates"],
                "Fault Model"         : fault_model,
                "Injected Fault Type" : hyp_type,
                "Injected Gate IDs"   : str(hyp_gate_ids),
                "Injected Missing Mask": hyp_missing_mask,
                "Localization Status" : result.status,
                "Located Fault Type"  : result.primary.fault_type if result.primary else "",
                "Located Gate IDs"    : str(result.primary.gate_ids) if result.primary else "",
                "Located Missing Mask": result.primary.missing_mask if result.primary else "",
                "Correctly Located"   : located_correctly,
                "Confidence"          : result.primary.confidence if result.primary else 0.0,
                "Verified"            : result.primary.verified if result.primary else False,
                "Equiv Class Size"    : len(result.equivalence_cls),
                "Discriminating Vec"  : result.discriminating_vector,
                "Fault Order Detected": result.fault_order,
                "SSV Hamming Weight"  : int(np.sum(result.ssv)) if result.ssv is not None else 0,
                "Notes"               : " | ".join(result.notes),
            }
            _save_localization_row(row, output_dir)

        elapsed = round(time.perf_counter() - t_start, 4)

        # ── Save summary row for this (circuit, fault_model) ─────────────────
        summary_row = {
            "Circuit Name"        : circuit_name,
            "No of Lines"         : circuit_dict["No of Lines"],
            "No of Gates"         : circuit_dict["No of Gates"],
            "Fault Model"         : fault_model,
            "Injected Fault Type" : "SUMMARY",
            "Injected Gate IDs"   : "",
            "Injected Missing Mask": "",
            "Localization Status" : "summary",
            "Located Fault Type"  : "",
            "Located Gate IDs"    : "",
            "Located Missing Mask": "",
            "Correctly Located"   : n_located,
            "Confidence"          : "",
            "Verified"            : "",
            "Equiv Class Size"    : n_equiv,
            "Discriminating Vec"  : "",
            "Fault Order Detected": "",
            "SSV Hamming Weight"  : "",
            "Notes"               : (
                f"Total={n_total} Located={n_located} "
                f"EquivClass={n_equiv} NoMatch={n_no_match} "
                f"Time={elapsed}s"
            ),
        }
        _save_localization_row(summary_row, output_dir)

        if verbose:
            acc = f"{n_located}/{n_total}" if n_total else "0/0"
            print(f"  [{circuit_name}] {fault_model} done — "
                  f"Located: {acc}  Equiv: {n_equiv}  "
                  f"NoMatch: {n_no_match}  ({elapsed}s)")

        return fault_model, None

    except Exception as e:
        import traceback
        return fault_model, e


# ══════════════════════════════════════════════════════════════════════════════
#  Fault hypothesis enumerator
# ══════════════════════════════════════════════════════════════════════════════

def _enumerate_hypotheses(circuit_dict: dict,
                           fault_model: str,
                           max_mmgf_order: int = 2) -> list:
    """
    Return all (fault_type, gate_ids, missing_mask) tuples for the given model.
    Mirrors the enumeration done inside _FaultSyndromeDictionary.build().
    """
    from itertools import combinations
    compiled_gates = circuit_dict["Compiled Rep"]
    n_gates        = circuit_dict["No of Gates"]
    hypotheses     = []

    if fault_model in ("SMGF", "ALL"):
        for gid in range(n_gates):
            hypotheses.append(("SMGF", [gid], 0))

    if fault_model in ("MMGF", "ALL"):
        for order in range(2, max_mmgf_order + 1):
            for combo in combinations(range(n_gates), order):
                hypotheses.append(("MMGF", list(combo), 0))

    if fault_model in ("PMGF", "ALL"):
        for gid, gate in enumerate(compiled_gates):
            gate_type = gate[0]
            if gate_type not in ("TOFFOLI", "FREDKIN", "PERES"):
                continue
            ctrl_mask = gate[1]
            # decompose into individual control bits
            ctrl_bits = []
            tmp, pos = ctrl_mask, 0
            while tmp:
                if tmp & 1:
                    ctrl_bits.append(1 << pos)
                tmp >>= 1
                pos  += 1
            for r in range(1, len(ctrl_bits)):
                for subset in combinations(ctrl_bits, r):
                    missing_mask = 0
                    for b in subset:
                        missing_mask |= b
                    hypotheses.append(("PMGF", [gid], missing_mask))

    return hypotheses


# ══════════════════════════════════════════════════════════════════════════════
#  Main pipeline
# ══════════════════════════════════════════════════════════════════════════════

def run_localization_pipeline(
        path          : str,
        detection_csv : str,
        fault_models  : List[str]  = None,
        max_mmgf_order: int        = 2,
        max_workers   : int        = 4,
        output_dir    : str        = OUTPUT_DIR,
        verbose       : bool       = True):
    """
    Main entry point — mirrors run_pipeline() in experiment_runner.py.

    Parameters
    ──────────
    path           : path to .real circuit file or folder
                     (same input as run_pipeline)

    detection_csv  : path to the GA_DP.csv detection results sheet.
                     Must have columns produced by GeneticAlgorithm.save_results():
                       Circuit Name, Fault Model, Best Vector Set,
                       No of Lines, No of Gates

    fault_models   : list of fault models to localize.
                     If None, uses all models found in detection_csv.
                     Supported: "SMGF", "MMGF", "PMGF"

    max_mmgf_order : max number of simultaneously missing gates for MMGF
                     (default 2 = pairs)

    max_workers    : parallel threads per circuit (mirrors experiment_runner)

    output_dir     : directory for RSVS_Localization.csv output

    verbose        : print progress
    """

    # ── Load detection sheet ──────────────────────────────────────────────────
    detection_df = _load_detection_sheet(detection_csv)

    # Filter to only SMGF/MMGF/PMGF rows (localization-applicable models)
    localizable = {"SMGF", "MMGF", "PMGF"}
    detection_df = detection_df[detection_df["Fault Model"].isin(localizable)]

    if fault_models:
        detection_df = detection_df[detection_df["Fault Model"].isin(fault_models)]

    if detection_df.empty:
        print("No localizable fault model rows found in detection sheet. "
              "Ensure GA_DP.csv contains SMGF / MMGF / PMGF rows.")
        return

    # ── Discover .real files ──────────────────────────────────────────────────
    real_files = _get_real_files(path)
    # Build lookup: circuit_name (no extension) → filepath
    name_to_path = {
        os.path.splitext(basename(fp))[0]: fp
        for fp in real_files
    }

    if verbose:
        print(f"\n{'='*65}")
        print(f"  RSVS Localization Pipeline")
        print(f"  Circuits found   : {len(real_files)}")
        print(f"  Detection rows   : {len(detection_df)}")
        print(f"  Fault models     : {detection_df['Fault Model'].unique().tolist()}")
        print(f"  Output           : {os.path.abspath(output_dir)}")
        print(f"  Max MMGF order   : {max_mmgf_order}")
        print(f"  Workers/circuit  : {max_workers}")
        print(f"{'='*65}\n")

    os.makedirs(output_dir, exist_ok=True)

    # ── Group detection rows by circuit name ──────────────────────────────────
    grouped = detection_df.groupby("Circuit Name")

    for circuit_idx, (circuit_name, group) in enumerate(grouped, 1):

        # Find the .real file for this circuit
        filepath = name_to_path.get(circuit_name)
        if filepath is None:
            if verbose:
                print(f"[{circuit_idx}] SKIP — .real file not found for: "
                      f"{circuit_name}")
            continue

        if verbose:
            print(f"[{circuit_idx}/{len(grouped)}] Circuit: {circuit_name}")

        # Parse circuit once and share across fault models
        try:
            circuit_dict = parse_real_file(filepath)
        except Exception as e:
            print(f"  [ERROR] Could not parse {filepath}: {e}")
            continue

        # ── Build (fault_model → test_set) map for this circuit ───────────────
        model_test_sets = {}
        for _, row in group.iterrows():
            fm  = row["Fault Model"]
            tvs = _parse_vector_set(row.get("Best Vector Set"))
            if tvs is None or len(tvs) == 0:
                if verbose:
                    print(f"  [WARN] No valid test set for {circuit_name} / {fm} "
                          f"— skipping")
                continue
            model_test_sets[fm] = tvs

        if not model_test_sets:
            if verbose:
                print(f"  No usable test sets found — skipping {circuit_name}")
            continue

        # ── Run localization for each fault model in parallel ─────────────────
        workers = min(max_workers, len(model_test_sets))

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(
                    _run_single_localization,
                    circuit_dict,
                    fm,
                    ts,
                    filepath,
                    max_mmgf_order,
                    verbose,
                    output_dir
                ): fm
                for fm, ts in model_test_sets.items()
            }

            for future in as_completed(futures):
                fm, error = future.result()
                if error:
                    import traceback
                    print(f"  [ERROR] {circuit_name} | {fm}: {error}")
                    traceback.print_exc()

        del circuit_dict

        if verbose:
            print(f"  All models complete for: {circuit_name}\n")

    if verbose:
        print("Localization pipeline complete.")
        print(f"Results saved to: {os.path.abspath(os.path.join(output_dir, 'RSVS_Localization.csv'))}")