"""
demo.py
End-to-end demonstration of the RSVS fault localizer.

Runs four scenarios on a 4-line Toffoli cascade:
  1. No fault           (sanity check)
  2. SMGF               (single missing gate)
  3. MMGF               (two missing gates)
  4. PMGF               (partial missing gate – one control removed)
"""

import sys
import numpy as np

from reversible_circuit import ReversibleCircuit, FaultSpec
from rsvs_localizer     import RSVSLocalizer


# ──────────────────────────────────────────────────────────────────────────────
# Build example circuit  (4 lines, 6 gates)
# ──────────────────────────────────────────────────────────────────────────────
#
#  Lines: 0, 1, 2, 3
#
#  G0: CNOT    ctrl=[0]      tgt=1
#  G1: TOFFOLI ctrl=[0,1]    tgt=2
#  G2: CNOT    ctrl=[1]      tgt=3
#  G3: TOFFOLI ctrl=[2,3]    tgt=0
#  G4: CNOT    ctrl=[0]      tgt=2
#  G5: TOFFOLI ctrl=[1,2]    tgt=3
#

def build_circuit() -> ReversibleCircuit:
    c = ReversibleCircuit(n_lines=4)
    c.add_cnot(0, 1)               # G0
    c.add_toffoli([0, 1], 2)       # G1
    c.add_cnot(1, 3)               # G2
    c.add_toffoli([2, 3], 0)       # G3
    c.add_cnot(0, 2)               # G4
    c.add_toffoli([1, 2], 3)       # G5
    return c


# ──────────────────────────────────────────────────────────────────────────────
# Complete test set for a 4-line circuit (all 16 input patterns)
# A complete test set must detect all SMGFs; using the full input space
# guarantees this for any cascade of k-CNOT gates.
# ──────────────────────────────────────────────────────────────────────────────

def all_input_vectors(n: int):
    vecs = []
    for val in range(2 ** n):
        vecs.append([(val >> bit) & 1 for bit in range(n)])
    return vecs


# ──────────────────────────────────────────────────────────────────────────────
# Helper to run a scenario
# ──────────────────────────────────────────────────────────────────────────────

def run_scenario(title: str,
                 circuit: ReversibleCircuit,
                 test_set,
                 localizer: RSVSLocalizer,
                 injected_fault=None):
    print(f"\n{'#'*60}")
    print(f"  SCENARIO: {title}")
    print(f"{'#'*60}")

    # Collect actual outputs from the "circuit under test"
    actual_outputs = [circuit.simulate(tv, fault=injected_fault)
                      for tv in test_set]

    result = localizer.localize(actual_outputs, resolve_equiv=True, verbose=True)

    if injected_fault:
        print(f"\n  ★ GROUND TRUTH (injected fault): {injected_fault}")
        if result.primary:
            match = (result.primary.fault_type == injected_fault.fault_type and
                     sorted(result.primary.gate_ids) == sorted(injected_fault.gate_ids))
            print(f"  ★ LOCALIZATION CORRECT: {match}")


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  RSVS — Reversible Syndrome Vector Signature")
    print("  Fault Localizer Demo")
    print("=" * 60)

    circuit  = build_circuit()
    print(f"\nCircuit:\n{circuit}\n")

    test_set = all_input_vectors(circuit.n_lines)
    print(f"Test set size: {len(test_set)} vectors (complete for 4-line circuit)")

    # ── Offline: build fault dictionary ──────────────────────────────────────
    localizer = RSVSLocalizer(circuit, test_set)
    localizer.build_dictionary(max_mmgf_order=2, build_pmgf=True)
    print(localizer.fsd.summary())

    # ── Scenario 1: No fault ─────────────────────────────────────────────────
    run_scenario("No fault (golden circuit)", circuit, test_set,
                 localizer, injected_fault=None)

    # ── Scenario 2: SMGF – G2 missing ────────────────────────────────────────
    smgf = FaultSpec("SMGF", [2])
    run_scenario("SMGF – Gate G2 (CNOT ctrl=1, tgt=3) missing",
                 circuit, test_set, localizer, injected_fault=smgf)

    # ── Scenario 3: MMGF – G1 and G4 missing ─────────────────────────────────
    mmgf = FaultSpec("MMGF", [1, 4])
    run_scenario("MMGF – Gates G1 and G4 both missing",
                 circuit, test_set, localizer, injected_fault=mmgf)

    # ── Scenario 4: PMGF – G3 with one control line (line 2) removed ─────────
    pmgf = FaultSpec("PMGF", [3], missing_controls=[2])
    run_scenario("PMGF – Gate G3 (TOFFOLI ctrl=[2,3]→0) with ctrl line 2 missing",
                 circuit, test_set, localizer, injected_fault=pmgf)

    print("\n" + "="*60)
    print("  Demo complete.")
    print("="*60)


if __name__ == "__main__":
    main()
