"""
fault_dictionary.py
Pre-computes the Fault Syndrome Dictionary (FSD) offline.
Covers SMGF, MMGF (via XOR composability), and PMGF.
"""

from __future__ import annotations
import itertools
from typing import Dict, List, Tuple, Optional

import numpy as np

from reversible_circuit import ReversibleCircuit, FaultSpec


# ──────────────────────────────────────────────────────────────────────────────
# Syndrome helpers
# ──────────────────────────────────────────────────────────────────────────────

def compute_syndrome(circuit: ReversibleCircuit,
                     test_set: List[List[int]],
                     fault: Optional[FaultSpec] = None) -> np.ndarray:
    """
    Run every test vector through the (possibly faulty) circuit.
    Returns SSV: binary array of shape (m * n,)  where m = |test_set|, n = n_lines.
    """
    n = circuit.n_lines
    golden_outputs = [circuit.simulate(tv) for tv in test_set]

    if fault is None:
        return np.zeros(len(test_set) * n, dtype=np.int8)

    syndromes = []
    for i, tv in enumerate(test_set):
        faulty_out = circuit.simulate(tv, fault=fault)
        s = [fo ^ go for fo, go in zip(faulty_out, golden_outputs[i])]
        syndromes.extend(s)

    return np.array(syndromes, dtype=np.int8)


def ssv_to_key(ssv: np.ndarray) -> bytes:
    """Convert SSV to a hashable key (bytes)."""
    return ssv.tobytes()


# ──────────────────────────────────────────────────────────────────────────────
# Fault Syndrome Dictionary
# ──────────────────────────────────────────────────────────────────────────────

class FaultSyndromeDictionary:
    """
    Offline pre-computation of all fault → SSV mappings.

    After build(), provides O(1) lookup for SMGF,
    O(d²) XOR-based lookup for MMGF,
    and activation-mask lookup for PMGF.
    """

    def __init__(self, circuit: ReversibleCircuit, test_set: List[List[int]]):
        self.circuit  = circuit
        self.test_set = test_set
        self.n_lines  = circuit.n_lines
        self.depth    = circuit.depth()

        # SMGF dict: gate_id → SSV
        self.smgf_ssv: Dict[int, np.ndarray] = {}
        # Reverse hash: ssv_key → list[FaultSpec]
        self.hash_to_faults: Dict[bytes, List[FaultSpec]] = {}
        # PMGF entries: (gate_id, frozenset(missing_ctrl)) → SSV
        self.pmgf_ssv: Dict[Tuple, np.ndarray] = {}

        self._built = False

    # ── build ─────────────────────────────────────────────────────────────────
    def build(self, max_mmgf_order: int = 2,
              build_pmgf: bool = True) -> "FaultSyndromeDictionary":
        """
        Compute syndromes for all fault hypotheses.

        max_mmgf_order : maximum number of simultaneously missing gates
                         (2 covers pairs, 3 covers triples, etc.)
        build_pmgf     : whether to enumerate PMGF hypotheses
        """
        print("Building Fault Syndrome Dictionary …")

        # ── 1. SMGF ──────────────────────────────────────────────────────────
        print(f"  [1/3] SMGF  ({self.depth} gates)")
        for gid in range(self.depth):
            fault  = FaultSpec("SMGF", [gid])
            ssv    = compute_syndrome(self.circuit, self.test_set, fault)
            self.smgf_ssv[gid] = ssv
            key    = ssv_to_key(ssv)
            self.hash_to_faults.setdefault(key, []).append(fault)

        # ── 2. MMGF (stored implicitly; we also store explicit SSV for
        #            small orders and add to hash table) ─────────────────────
        if max_mmgf_order >= 2:
            n_combos = sum(
                len(list(itertools.combinations(range(self.depth), r)))
                for r in range(2, max_mmgf_order + 1)
            )
            print(f"  [2/3] MMGF  (order ≤ {max_mmgf_order}, "
                  f"{n_combos} combinations)")

            for order in range(2, max_mmgf_order + 1):
                for combo in itertools.combinations(range(self.depth), order):
                    fault = FaultSpec("MMGF", list(combo))
                    # Use XOR composability as approximation; also compute exact
                    exact_ssv = compute_syndrome(self.circuit,
                                                 self.test_set, fault)
                    key = ssv_to_key(exact_ssv)
                    self.hash_to_faults.setdefault(key, []).append(fault)

        # ── 3. PMGF ──────────────────────────────────────────────────────────
        if build_pmgf:
            pmgf_count = 0
            for gate in self.circuit.gates:
                gid = gate.gate_id
                ctrl = gate.controls
                if not ctrl:
                    continue  # NOT gate — no controls to remove
                # enumerate all non-empty proper subsets of controls to remove
                for r in range(1, len(ctrl)):
                    for missing in itertools.combinations(ctrl, r):
                        key_pmgf = (gid, frozenset(missing))
                        fault = FaultSpec("PMGF", [gid],
                                          missing_controls=list(missing))
                        ssv   = compute_syndrome(self.circuit,
                                                 self.test_set, fault)
                        self.pmgf_ssv[key_pmgf] = ssv
                        key   = ssv_to_key(ssv)
                        self.hash_to_faults.setdefault(key, []).append(fault)
                        pmgf_count += 1
            print(f"  [3/3] PMGF  ({pmgf_count} partial-control variants)")

        self._built = True
        total = sum(len(v) for v in self.hash_to_faults.values())
        print(f"  Done. Dictionary contains {total} fault entries "
              f"across {len(self.hash_to_faults)} distinct syndromes.\n")
        return self

    # ── fast exact lookup ─────────────────────────────────────────────────────
    def lookup_exact(self, ssv: np.ndarray) -> List[FaultSpec]:
        """Return all faults whose pre-computed SSV exactly matches."""
        assert self._built, "Call build() first."
        return self.hash_to_faults.get(ssv_to_key(ssv), [])

    # ── approximate MMGF lookup via XOR composability ─────────────────────────
    def lookup_mmgf_approx(self, ssv: np.ndarray,
                           top_k: int = 5) -> List[Tuple[float, FaultSpec]]:
        """
        For each pair (i, j) of SMGF entries, compute the XOR-composed SSV
        and rank by Hamming distance to the observed SSV.
        Returns top_k (distance, FaultSpec) tuples, sorted ascending.
        """
        assert self._built
        results = []
        gids = list(self.smgf_ssv.keys())
        for i, j in itertools.combinations(gids, 2):
            composed = self.smgf_ssv[i] ^ self.smgf_ssv[j]
            dist     = int(np.sum(ssv != composed))
            results.append((dist, FaultSpec("MMGF", [i, j])))
        results.sort(key=lambda x: x[0])
        return results[:top_k]

    # ── PMGF activation-mask lookup ───────────────────────────────────────────
    def lookup_pmgf_approx(self, ssv: np.ndarray,
                           top_k: int = 5) -> List[Tuple[float, FaultSpec]]:
        """
        Rank all PMGF hypotheses by Hamming distance to observed SSV.
        """
        assert self._built
        results = []
        for (gid, missing_ctrl), stored_ssv in self.pmgf_ssv.items():
            dist = int(np.sum(ssv != stored_ssv))
            results.append((dist, FaultSpec("PMGF", [gid],
                                            missing_controls=list(missing_ctrl))))
        results.sort(key=lambda x: x[0])
        return results[:top_k]

    def summary(self) -> str:
        lines = [
            "FaultSyndromeDictionary summary",
            f"  SMGF entries : {len(self.smgf_ssv)}",
            f"  PMGF entries : {len(self.pmgf_ssv)}",
            f"  Total hashed : {sum(len(v) for v in self.hash_to_faults.values())}",
            f"  Distinct SSVs: {len(self.hash_to_faults)}",
        ]
        return "\n".join(lines)
