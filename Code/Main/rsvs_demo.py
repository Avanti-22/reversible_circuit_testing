"""
rsvs_demo.py
════════════════════════════════════════════════════════════════════════════════
End-to-end demo of the RSVS fault localizer integrated with your project.

Run from  Code/Main/  (same folder as simulator.py, fault_models.py, etc.):

    python rsvs_demo.py

The demo:
  1.  Builds a small synthetic 4-line circuit using your compiled-rep format
      (no .real file needed — works standalone)
  2.  Generates a complete test set (all 2^n vectors for small circuits)
  3.  Builds the offline fault dictionary
  4.  Runs four localization scenarios:
        a) No fault        (sanity check)
        b) SMGF — gate 2 missing
        c) MMGF — gates 1 and 4 missing simultaneously
        d) PMGF — gate 3 with one control line removed

To use with a REAL circuit from your project, see Section B below.
════════════════════════════════════════════════════════════════════════════════
"""

import sys
import os

# ── make sure we can import the project modules ───────────────────────────────
# If running from the repo root, adjust this path as needed:
# sys.path.insert(0, "Code/Main")

from simulator            import simulate_fault_free, simulate_MMGF_circuit, simulate_PMGF_circuit
from rsvs_fault_localizer import RSVSLocalizer


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION A — Synthetic circuit (no .real file needed)
# ══════════════════════════════════════════════════════════════════════════════

def build_synthetic_circuit() -> dict:
    """
    Build a small 4-line circuit in YOUR project's compiled-rep format.

    Lines (bit positions): 0, 1, 2, 3
    Bit masks:             1, 2, 4, 8

    Gate list:
      G0  TOFFOLI  ctrl=line0 (mask=1)      target=line1 (mask=2)
      G1  TOFFOLI  ctrl=line0,line1 (3)     target=line2 (mask=4)
      G2  TOFFOLI  ctrl=line1 (2)           target=line3 (mask=8)
      G3  TOFFOLI  ctrl=line2,line3 (12)    target=line0 (mask=1)
      G4  TOFFOLI  ctrl=line0 (1)           target=line2 (mask=4)
      G5  TOFFOLI  ctrl=line1,line2 (6)     target=line3 (mask=8)
    """
    compiled_rep = [
        ("TOFFOLI", 0b0001,  0b0010),   # G0: ctrl=0  → tgt=1
        ("TOFFOLI", 0b0011,  0b0100),   # G1: ctrl=0,1 → tgt=2
        ("TOFFOLI", 0b0010,  0b1000),   # G2: ctrl=1  → tgt=3
        ("TOFFOLI", 0b1100,  0b0001),   # G3: ctrl=2,3 → tgt=0
        ("TOFFOLI", 0b0001,  0b0100),   # G4: ctrl=0  → tgt=2
        ("TOFFOLI", 0b0110,  0b1000),   # G5: ctrl=1,2 → tgt=3
    ]
    return {
        "Circuit Name" : "synthetic_4line",
        "No of Lines"  : 4,
        "No of Gates"  : len(compiled_rep),
        "Variables"    : ["x0", "x1", "x2", "x3"],
        "Compiled Rep" : compiled_rep,
    }


def complete_test_set(n_lines: int):
    """All 2^n input patterns as integers (complete test set for small n)."""
    return list(range(2 ** n_lines))


def run_scenario(title, localizer, fault_type=None,
                 gate_ids=None, missing_mask=0):
    print(f"\n{'#'*65}")
    print(f"  SCENARIO: {title}")
    print(f"{'#'*65}")

    # Simulate the circuit-under-test (CUT) using the convenience helper
    actual_outputs = localizer.simulate_cut(
        fault_type  = fault_type or "NONE",
        gate_ids    = gate_ids   or [],
        missing_mask = missing_mask
    )

    result = localizer.localize(actual_outputs, verbose=True)

    # Ground-truth check
    if fault_type and fault_type != "NONE":
        if result.primary:
            gt_ids  = sorted(gate_ids)
            hyp_ids = sorted(result.primary.gate_ids)
            type_ok = result.primary.fault_type == fault_type
            ids_ok  = hyp_ids == gt_ids
            mask_ok = (fault_type != "PMGF" or
                       result.primary.missing_mask == missing_mask)
            correct = type_ok and ids_ok and mask_ok
        else:
            correct = False

        label = "✅ CORRECT" if correct else "❌ WRONG"
        print(f"\n  Ground truth : {fault_type}(gates={gate_ids}"
              + (f", mask=0b{missing_mask:b}" if fault_type == "PMGF" else "")
              + ")")
        print(f"  Result       : {label}")


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION B — Using a REAL circuit from your project
# ══════════════════════════════════════════════════════════════════════════════

def demo_with_real_file(real_filepath: str,
                        fault_model: str = "SMGF"):
    """
    Full pipeline using a parsed .real circuit.

    Replace the test_set below with the output of your GA engine.

    Example:
        from batch_parsing_functions import parse_real_file
        circuit  = parse_real_file("Benchmarks Used in Base Paper/All Circuits/rd84_313.real")
        # GA produces the complete test set as a list of integers:
        test_set = ga_result["best_vector_set"]   # list[int]
        demo_with_real_file(circuit, test_set, fault_model="SMGF")
    """
    try:
        # Import your parser
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from batch_parsing_functions import parse_real_file

        circuit  = parse_real_file(real_filepath)
        n        = circuit["No of Lines"]
        print(f"\nLoaded: {circuit['Circuit Name']}  "
              f"({n} lines, {circuit['No of Gates']} gates)")

        # Use complete test set if n is small enough, else random sample
        if n <= 14:
            test_set = list(range(2 ** n))
            print(f"Using complete test set: {len(test_set)} vectors")
        else:
            import random
            test_set = random.sample(range(2 ** n), min(500, 2 ** n))
            print(f"Using random sample test set: {len(test_set)} vectors")

        localizer = RSVSLocalizer(circuit, test_set, fault_model=fault_model)
        localizer.build_dictionary(max_mmgf_order=2)

        # Inject a test fault and localize
        print("\n--- Injecting SMGF on gate 0 ---")
        actual = localizer.simulate_cut("SMGF", [0])
        result = localizer.localize(actual, verbose=True)
        return result

    except ImportError as e:
        print(f"(Real file demo skipped — could not import parser: {e})")
        return None


# ══════════════════════════════════════════════════════════════════════════════
#  Main
# ══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 65)
    print("  RSVS Fault Localizer — Project Integration Demo")
    print("=" * 65)

    # ── Build synthetic circuit ───────────────────────────────────────────────
    circuit  = build_synthetic_circuit()
    test_set = complete_test_set(circuit["No of Lines"])

    print(f"\nCircuit  : {circuit['Circuit Name']}")
    print(f"Lines    : {circuit['No of Lines']}")
    print(f"Gates    : {circuit['No of Gates']}")
    print(f"Test set : {len(test_set)} vectors (complete)")

    # ── Build offline fault dictionary ────────────────────────────────────────
    localizer = RSVSLocalizer(circuit, test_set, fault_model="ALL")
    localizer.build_dictionary(max_mmgf_order=2)

    # ── Scenario 1: No fault ──────────────────────────────────────────────────
    run_scenario("No fault (golden circuit)", localizer)

    # ── Scenario 2: SMGF — gate 2 missing ────────────────────────────────────
    run_scenario("SMGF — Gate 2 (TOFFOLI ctrl=1 → tgt=3) missing",
                 localizer, fault_type="SMGF", gate_ids=[2])

    # ── Scenario 3: MMGF — gates 1 and 4 missing ─────────────────────────────
    run_scenario("MMGF — Gates 1 and 4 both missing",
                 localizer, fault_type="MMGF", gate_ids=[1, 4])

    # ── Scenario 4: PMGF — gate 3 with ctrl line bit-mask 0b0100 (line 2) removed
    # Gate 3 is: TOFFOLI ctrl=line2,line3 (mask=0b1100) → tgt=line0
    # Removing line2 means missing_mask = 0b0100 = 4
    run_scenario("PMGF — Gate 3 with control line 2 (mask=0b0100) removed",
                 localizer, fault_type="PMGF", gate_ids=[3],
                 missing_mask=0b0100)

    print("\n" + "=" * 65)
    print("  Demo complete.")
    print("=" * 65)

    # ── Optional: run with a real .real file ──────────────────────────────────
    # Uncomment and adjust path:
    # demo_with_real_file(
    #     "../../Benchmarks Used in Base Paper/All Circuits/rd84_313.real",
    #     fault_model="SMGF"
    # )


if __name__ == "__main__":
    main()
