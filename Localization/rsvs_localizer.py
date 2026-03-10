"""
rsvs_localizer.py
Main RSVS (Reversible Syndrome Vector Signature) fault localizer.

Pipeline:
  Phase 1 – Syndrome computation
  Phase 2 – Fault order classification
  Phase 3 – Dictionary lookup (SMGF fast path / MMGF XOR / PMGF mask)
  Phase 4 – Bidirectional verification
  Phase 5 – Equivalence class resolution (optional supplemental vector)
"""

from __future__ import annotations
import itertools
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

import numpy as np

from reversible_circuit import ReversibleCircuit, FaultSpec
from fault_dictionary import (FaultSyndromeDictionary,
                               compute_syndrome, ssv_to_key)


# ──────────────────────────────────────────────────────────────────────────────
# Result container
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class LocalizationResult:
    status          : str = ""      # 'located' | 'equiv_class' | 'no_match'
    primary         : Optional[FaultSpec] = None   # best single hypothesis
    equivalence_cls : List[FaultSpec] = field(default_factory=list)
    fault_order     : str  = ""     # 'SMGF' | 'MMGF' | 'PMGF' | 'unknown'
    confidence      : float = 0.0   # 0-1 score
    ssv             : Optional[np.ndarray] = None
    verification_ok : bool = False
    notes           : List[str] = field(default_factory=list)

    def __str__(self):
        lines = [
            "─" * 60,
            f"Localization Status  : {self.status}",
            f"Fault Order (class)  : {self.fault_order}",
            f"Confidence           : {self.confidence:.2%}",
            f"Verified             : {self.verification_ok}",
        ]
        if self.primary:
            lines.append(f"Primary hypothesis   : {self.primary}")
        if self.equivalence_cls:
            lines.append(f"Equivalence class    : "
                         f"({len(self.equivalence_cls)} members)")
            for f in self.equivalence_cls:
                lines.append(f"    {f}")
        for n in self.notes:
            lines.append(f"Note: {n}")
        lines.append("─" * 60)
        return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# Phase 2 helpers – fault order classification
# ──────────────────────────────────────────────────────────────────────────────

def _cluster_count(ssv: np.ndarray, n_lines: int) -> int:
    """
    Count contiguous error 'clusters' in the SSV when viewed as
    a 2-D grid (test_vectors × output_lines).
    A cluster is a connected component of 1-bits.
    """
    m   = len(ssv) // n_lines
    mat = ssv.reshape(m, n_lines)
    visited = np.zeros_like(mat, dtype=bool)
    clusters = 0

    def bfs(r, c):
        queue = [(r, c)]
        while queue:
            x, y = queue.pop()
            if x < 0 or x >= m or y < 0 or y >= n_lines:
                continue
            if visited[x, y] or mat[x, y] == 0:
                continue
            visited[x, y] = True
            for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                queue.append((x+dx, y+dy))

    for r in range(m):
        for c in range(n_lines):
            if mat[r, c] == 1 and not visited[r, c]:
                clusters += 1
                bfs(r, c)
    return clusters


def classify_fault_order(ssv: np.ndarray, n_lines: int,
                          smgf_ssv_map: Dict[int, np.ndarray]) -> str:
    """
    Heuristic classification of the fault order based on SSV properties.
    Returns 'SMGF', 'MMGF', 'PMGF', or 'unknown'.
    """
    hw      = int(np.sum(ssv))
    n_total = len(ssv)

    if hw == 0:
        return "no_fault"

    clusters  = _cluster_count(ssv, n_lines)
    density   = hw / n_total

    # ── check if SSV exactly matches any known SMGF ───────────────────────
    for gid, s in smgf_ssv_map.items():
        if np.array_equal(ssv, s):
            return "SMGF"

    # ── check if SSV can be expressed as XOR of two SMGF SSVs ─────────────
    gids = list(smgf_ssv_map.keys())
    for i, j in itertools.combinations(gids, 2):
        composed = smgf_ssv_map[i] ^ smgf_ssv_map[j]
        if np.array_equal(ssv, composed):
            return "MMGF"

    # ── heuristic rules ───────────────────────────────────────────────────
    if clusters >= 2:
        return "MMGF"   # multiple separated error regions → multiple faults

    if density < 0.25 and clusters == 1:
        return "PMGF"   # sparse, single cluster → partial gate fault

    if density >= 0.25 and clusters == 1:
        return "SMGF"   # dense, single cluster → complete single gate removal

    return "unknown"


# ──────────────────────────────────────────────────────────────────────────────
# Phase 4 – Bidirectional verification
# ──────────────────────────────────────────────────────────────────────────────

def bidirectional_verify(circuit: ReversibleCircuit,
                          test_set: List[List[int]],
                          actual_outputs: List[List[int]],
                          hypothesis: FaultSpec,
                          n_verify: int = 3) -> bool:
    """
    For up to n_verify test vectors where a syndrome exists:
      1. Simulate the hypothesis-faulty circuit forward to gate boundary
      2. Simulate the golden circuit backward from the actual output
      3. Check that intermediate states match at the hypothesised gate boundary.

    Returns True if all checked vectors are consistent with the hypothesis.
    """
    # Find gate boundary (the first faulty gate position)
    boundary = min(hypothesis.gate_ids)
    verified_count = 0
    checked = 0

    golden_outputs = [circuit.simulate(tv) for tv in test_set]

    for idx, tv in enumerate(test_set):
        # Only verify on vectors that show a syndrome
        syn = [a ^ g for a, g in zip(actual_outputs[idx], golden_outputs[idx])]
        if all(b == 0 for b in syn):
            continue
        if checked >= n_verify:
            break
        checked += 1

        # Forward: simulate (golden) up to but not including the boundary gate
        state_fwd = list(tv)
        for gate in circuit.gates:
            if gate.gate_id >= boundary:
                break
            state_fwd = gate.apply(state_fwd)

        # Backward: apply golden inverse from golden output, undoing all gates
        # strictly AFTER the boundary, so we meet at the boundary signal
        golden_out = circuit.simulate(tv)
        state_bwd  = list(golden_out)
        for gate in reversed(circuit.gates):
            if gate.gate_id <= boundary:
                break
            state_bwd = gate.apply_inverse(state_bwd)

        if state_fwd == state_bwd:
            verified_count += 1

    return verified_count == checked and checked > 0


# ──────────────────────────────────────────────────────────────────────────────
# Phase 5 – Equivalence class resolution
# ──────────────────────────────────────────────────────────────────────────────

def find_discriminating_vector(circuit: ReversibleCircuit,
                                equiv_class: List[FaultSpec],
                                existing_test_set: List[List[int]]) -> Optional[List[int]]:
    """
    Search for a supplemental test vector that maximally discriminates
    between members of an equivalence class.

    Tries all 2^n input vectors (feasible for n ≤ 16).
    Returns the best discriminating vector, or None if n too large.
    """
    n = circuit.n_lines
    if n > 16:
        return None   # too expensive; caller should use random sampling

    best_vec  = None
    best_div  = -1

    for val in range(2 ** n):
        tv = [(val >> bit) & 1 for bit in range(n)]
        if tv in existing_test_set:
            continue

        outputs = {}
        for fault in equiv_class:
            out = tuple(circuit.simulate(tv, fault=fault))
            outputs[id(fault)] = out

        # diversity = number of distinct output values
        diversity = len(set(outputs.values()))
        if diversity > best_div:
            best_div  = diversity
            best_vec  = tv

    return best_vec


# ──────────────────────────────────────────────────────────────────────────────
# Main localizer
# ──────────────────────────────────────────────────────────────────────────────

class RSVSLocalizer:
    """
    RSVS Fault Localizer.

    Usage
    -----
    localizer = RSVSLocalizer(circuit, test_set)
    localizer.build_dictionary()                       # offline phase
    result = localizer.localize(actual_outputs)        # online phase
    print(result)
    """

    def __init__(self, circuit: ReversibleCircuit,
                 test_set: List[List[int]]):
        self.circuit  = circuit
        self.test_set = test_set
        self.fsd: Optional[FaultSyndromeDictionary] = None
        self._golden_outputs = [circuit.simulate(tv) for tv in test_set]

    # ── offline ───────────────────────────────────────────────────────────────
    def build_dictionary(self, max_mmgf_order: int = 2,
                          build_pmgf: bool = True) -> "RSVSLocalizer":
        self.fsd = FaultSyndromeDictionary(self.circuit, self.test_set)
        self.fsd.build(max_mmgf_order=max_mmgf_order,
                       build_pmgf=build_pmgf)
        return self

    # ── online ────────────────────────────────────────────────────────────────
    def localize(self, actual_outputs: List[List[int]],
                 resolve_equiv: bool = True,
                 verbose: bool = True) -> LocalizationResult:
        """
        Main entry point.

        actual_outputs : list of n-bit outputs from the circuit-under-test,
                         one per test vector in test_set.
        resolve_equiv  : attempt to resolve equivalence classes with a
                         supplemental test vector.
        """
        assert self.fsd is not None, "Call build_dictionary() first."

        result = LocalizationResult()

        # ── Phase 1: compute observed SSV ─────────────────────────────────
        ssv_parts = []
        for i, ao in enumerate(actual_outputs):
            go = self._golden_outputs[i]
            ssv_parts.extend([a ^ g for a, g in zip(ao, go)])
        ssv = np.array(ssv_parts, dtype=np.int8)
        result.ssv = ssv

        hw = int(np.sum(ssv))
        if verbose:
            print(f"\n{'='*60}")
            print(f"Phase 1 – Syndrome computed  (Hamming weight = {hw})")

        if hw == 0:
            result.status = 'no_fault'
            result.fault_order = 'none'
            result.confidence  = 1.0
            result.notes.append("All test vectors passed – no fault detected.")
            return result

        # ── Phase 2: classify fault order ─────────────────────────────────
        fault_order = classify_fault_order(ssv, self.circuit.n_lines,
                                           self.fsd.smgf_ssv)
        result.fault_order = fault_order
        if verbose:
            print(f"Phase 2 – Fault order classified as: {fault_order}")

        # ── Phase 3: lookup ───────────────────────────────────────────────
        if verbose:
            print("Phase 3 – Dictionary lookup …")

        candidates: List[FaultSpec] = []

        # Fast exact hash lookup (covers SMGF perfectly, and any MMGF/PMGF
        # already in the hash table)
        exact = self.fsd.lookup_exact(ssv)
        if exact:
            candidates = exact
            if verbose:
                print(f"  Exact hash match: {len(candidates)} candidate(s)")

        # If no exact match, use approximate strategies
        if not candidates:
            if fault_order in ("MMGF", "unknown"):
                approx = self.fsd.lookup_mmgf_approx(ssv, top_k=5)
                if approx and approx[0][0] == 0:
                    candidates = [approx[0][1]]
                elif approx:
                    dist0 = approx[0][0]
                    candidates = [f for d, f in approx if d <= dist0 + 2]
                    result.notes.append(
                        f"MMGF approx: best XOR-distance={dist0}")
                if verbose:
                    print(f"  MMGF approx top-5: "
                          f"{[(d,str(f)) for d,f in approx]}")

            if fault_order in ("PMGF", "unknown") and not candidates:
                approx = self.fsd.lookup_pmgf_approx(ssv, top_k=5)
                if approx and approx[0][0] == 0:
                    candidates = [approx[0][1]]
                elif approx:
                    dist0 = approx[0][0]
                    candidates = [f for d, f in approx if d <= dist0 + 2]
                    result.notes.append(
                        f"PMGF approx: best mask-distance={dist0}")
                if verbose:
                    print(f"  PMGF approx top-5: "
                          f"{[(d,str(f)) for d,f in approx]}")

        if not candidates:
            result.status     = 'no_match'
            result.confidence = 0.0
            result.notes.append("No matching fault hypothesis found.")
            return result

        # ── Phase 4: bidirectional verification ───────────────────────────
        if verbose:
            print("Phase 4 – Bidirectional verification …")

        verified = []
        for cand in candidates:
            ok = bidirectional_verify(self.circuit, self.test_set,
                                       actual_outputs, cand)
            if ok:
                verified.append(cand)
            if verbose:
                print(f"  {cand}  →  {'✓ verified' if ok else '✗ failed'}")

        if verified:
            candidates = verified

        # ── Phase 5: equivalence class handling ───────────────────────────
        if len(candidates) == 1:
            result.status         = 'located'
            result.primary        = candidates[0]
            result.confidence     = 1.0 if verified else 0.8
            result.verification_ok = bool(verified)
        else:
            result.equivalence_cls = candidates
            result.primary         = candidates[0]
            result.confidence      = 0.6
            result.status          = 'equiv_class'
            result.notes.append(
                f"Equivalence class: {len(candidates)} indistinguishable faults.")

            if resolve_equiv:
                if verbose:
                    print("Phase 5 – Resolving equivalence class …")
                disc_vec = find_discriminating_vector(
                    self.circuit, candidates, self.test_set)
                if disc_vec is not None:
                    result.notes.append(
                        f"Suggested discriminating vector: {disc_vec}")
                    if verbose:
                        print(f"  Suggested supplemental test vector: {disc_vec}")
                else:
                    result.notes.append(
                        "Circuit too large for exhaustive discrimination; "
                        "use random sampling.")

        if verbose:
            print(f"\nResult:\n{result}")

        return result
