"""
rsvs_fault_localizer.py
═══════════════════════════════════════════════════════════════════════════════
RSVS — Reversible Syndrome Vector Signature Fault Localizer
Integrated with your existing reversible circuit testing project.

DROP THIS FILE into  Code/Main/  alongside simulator.py, fault_models.py etc.

Usage
─────
    from rsvs_fault_localizer import RSVSLocalizer

    # 1. Parse circuit the way you already do
    circuit = parse_real_file("path/to/circuit.real")

    # 2. Supply your already-generated complete test set (list of ints)
    test_set = [0, 3, 5, 7, 12, ...]          # integers, one per test vector

    # 3. Build the offline fault dictionary  (do once, re-use many times)
    localizer = RSVSLocalizer(circuit, test_set, fault_model="SMGF")
    localizer.build_dictionary()

    # 4. Collect actual outputs from the circuit under test (CUT)
    #    – if you already have them as integers just pass them in
    actual_outputs = [...]                     # same order as test_set

    # 5. Localize
    result = localizer.localize(actual_outputs)
    print(result)

Supported fault models
──────────────────────
    "SMGF"   Single Missing Gate Fault
    "MMGF"   Multiple Missing Gate Faults  (pairs by default)
    "PMGF"   Partial Missing Gate Fault    (one or more control lines missing)
    "ALL"    Build dictionary for all three simultaneously
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import itertools
import time
from dataclasses import dataclass, field
from itertools import combinations
from typing import Dict, List, Optional, Set, Tuple

import numpy as np

# ── import from your existing project ─────────────────────────────────────────
from simulator import simulate_fault_free, simulate_MMGF_circuit, simulate_PMGF_circuit, apply_gate


# ══════════════════════════════════════════════════════════════════════════════
#  Internal helpers — bitmask aware
# ══════════════════════════════════════════════════════════════════════════════

def _int_to_bits(value: int, n_lines: int) -> List[int]:
    """Convert integer state → list of n_lines bits (LSB first)."""
    return [(value >> i) & 1 for i in range(n_lines)]


def _bits_to_int(bits: List[int]) -> int:
    """Convert list of bits (LSB first) → integer."""
    result = 0
    for i, b in enumerate(bits):
        if b:
            result |= (1 << i)
    return result


def _extract_control_bits(gate) -> List[int]:
    """
    Return a list of individual control bit-masks from a compiled gate tuple.
    Works for TOFFOLI, FREDKIN, PERES (all store control_mask as gate[1]).
    """
    gate_type  = gate[0]
    if gate_type not in ("TOFFOLI", "FREDKIN", "PERES"):
        return []

    control_mask = gate[1]
    bits = []
    pos  = 0
    tmp  = control_mask
    while tmp:
        if tmp & 1:
            bits.append(1 << pos)
        tmp >>= 1
        pos  += 1
    return bits


def _simulate_smgf(circuit: dict, input_bits: int, gate_index: int) -> int:
    """Run circuit with gate `gate_index` completely skipped."""
    return simulate_MMGF_circuit(circuit, input_bits,
                                  faulty_gate_indices={gate_index})


def _simulate_mmgf(circuit: dict, input_bits: int, gate_indices: List[int]) -> int:
    """Run circuit with all gates in `gate_indices` skipped."""
    return simulate_MMGF_circuit(circuit, input_bits,
                                  faulty_gate_indices=set(gate_indices))


def _simulate_pmgf(circuit: dict, input_bits: int,
                   gate_index: int, missing_mask: int) -> int:
    """Run circuit with partial control lines removed from `gate_index`."""
    return simulate_PMGF_circuit(circuit, input_bits,
                                  faulty_gate_index=gate_index,
                                  missing_control_bits_mask=missing_mask)


def _apply_gate_inverse(current_bits: int, gate) -> int:
    """
    All reversible gates in your project are self-inverse  (TOFFOLI, FREDKIN,
    PERES are all involutions), so inverse == forward application.
    """
    return apply_gate(current_bits, gate)


# ══════════════════════════════════════════════════════════════════════════════
#  Syndrome helpers
# ══════════════════════════════════════════════════════════════════════════════

def _compute_ssv(golden_outputs: List[int],
                 actual_outputs:  List[int],
                 n_lines: int) -> np.ndarray:
    """
    Build the Syndrome Signature Vector (SSV).

    For each test vector i, we XOR golden output with actual output bit-by-bit.
    Result shape: (m * n_lines,)  with dtype int8.
    """
    parts = []
    for g, a in zip(golden_outputs, actual_outputs):
        diff = g ^ a                          # integer XOR
        parts.extend(_int_to_bits(diff, n_lines))
    return np.array(parts, dtype=np.int8)


def _ssv_key(ssv: np.ndarray) -> bytes:
    return ssv.tobytes()


# ══════════════════════════════════════════════════════════════════════════════
#  Fault hypothesis dataclass
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class FaultHypothesis:
    """
    Describes one fault hypothesis produced by the localizer.

    fault_type      : "SMGF" | "MMGF" | "PMGF"
    gate_ids        : list of affected gate indices (0-based)
    missing_mask    : for PMGF — bitmask of control lines that are absent
    confidence      : 0.0 – 1.0
    verified        : True if bidirectional check passed
    """
    fault_type   : str
    gate_ids     : List[int]
    missing_mask : int   = 0       # only used for PMGF
    confidence   : float = 0.0
    verified     : bool  = False

    def __str__(self):
        base = f"{self.fault_type}(gates={self.gate_ids}"
        if self.fault_type == "PMGF":
            base += f", missing_ctrl_mask=0b{self.missing_mask:b}"
        base += f", conf={self.confidence:.0%}, verified={self.verified})"
        return base

    def __eq__(self, other):
        return (self.fault_type == other.fault_type and
                sorted(self.gate_ids) == sorted(other.gate_ids) and
                self.missing_mask == other.missing_mask)


# ══════════════════════════════════════════════════════════════════════════════
#  Localization result
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class LocalizationResult:
    """Returned by RSVSLocalizer.localize()."""
    status           : str = ""          # "located" | "equiv_class" | "no_fault" | "no_match"
    fault_order      : str = ""          # "SMGF" | "MMGF" | "PMGF" | "none" | "unknown"
    primary          : Optional[FaultHypothesis] = None
    equivalence_cls  : List[FaultHypothesis]     = field(default_factory=list)
    ssv              : Optional[np.ndarray]       = None
    notes            : List[str]                  = field(default_factory=list)
    # Suggested extra vector to split an equivalence class (integer)
    discriminating_vector : Optional[int]         = None

    def __str__(self):
        sep = "─" * 65
        lines = [
            sep,
            f"  Localization Status   : {self.status}",
            f"  Fault Order           : {self.fault_order}",
        ]
        if self.primary:
            lines.append(f"  Primary Hypothesis    : {self.primary}")
        if self.equivalence_cls:
            lines.append(
                f"  Equivalence Class     : {len(self.equivalence_cls)} member(s)")
            for h in self.equivalence_cls:
                lines.append(f"      {h}")
        if self.discriminating_vector is not None:
            lines.append(
                f"  Discriminating Vector : {self.discriminating_vector} "
                f"(0b{self.discriminating_vector:b})")
        for n in self.notes:
            lines.append(f"  Note: {n}")
        lines.append(sep)
        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
#  Fault Syndrome Dictionary  (offline phase)
# ══════════════════════════════════════════════════════════════════════════════

class _FaultSyndromeDictionary:
    """
    Pre-computes SSV for every fault hypothesis and stores them in a
    hash table for O(1) exact lookup online.

    Internally everything uses YOUR project's integer bitmask convention.
    """

    def __init__(self, circuit: dict, test_set: List[int],
                 golden_outputs: List[int]):
        self.circuit         = circuit
        self.test_set        = test_set
        self.golden_outputs  = golden_outputs
        self.n_lines         = circuit["No of Lines"]
        self.n_gates         = circuit["No of Gates"]
        self.compiled_gates  = circuit["Compiled Rep"]

        # SMGF:  gate_id  → ssv
        self.smgf_ssv: Dict[int, np.ndarray] = {}
        # PMGF:  (gate_id, missing_mask) → ssv
        self.pmgf_ssv: Dict[Tuple[int, int], np.ndarray] = {}
        # Hash lookup:  ssv_bytes → list[FaultHypothesis]
        self.hash_table: Dict[bytes, List[FaultHypothesis]] = {}

    # ── helpers ───────────────────────────────────────────────────────────────

    def _ssv_for_smgf(self, gate_id: int) -> np.ndarray:
        actual = [_simulate_smgf(self.circuit, tv, gate_id)
                  for tv in self.test_set]
        return _compute_ssv(self.golden_outputs, actual, self.n_lines)

    def _ssv_for_mmgf(self, gate_ids: List[int]) -> np.ndarray:
        actual = [_simulate_mmgf(self.circuit, tv, gate_ids)
                  for tv in self.test_set]
        return _compute_ssv(self.golden_outputs, actual, self.n_lines)

    def _ssv_for_pmgf(self, gate_id: int, missing_mask: int) -> np.ndarray:
        actual = [_simulate_pmgf(self.circuit, tv, gate_id, missing_mask)
                  for tv in self.test_set]
        return _compute_ssv(self.golden_outputs, actual, self.n_lines)

    def _register(self, ssv: np.ndarray, hyp: FaultHypothesis):
        key = _ssv_key(ssv)
        self.hash_table.setdefault(key, []).append(hyp)

    # ── build ─────────────────────────────────────────────────────────────────

    def build(self, fault_model: str = "ALL",
              max_mmgf_order: int = 2) -> "_FaultSyndromeDictionary":

        t0 = time.perf_counter()

        # ── 1. SMGF ──────────────────────────────────────────────────────────
        if fault_model in ("SMGF", "MMGF", "ALL"):
            print(f"  [SMGF]  computing {self.n_gates} gate entries …")
            for gid in range(self.n_gates):
                ssv = self._ssv_for_smgf(gid)
                self.smgf_ssv[gid] = ssv
                self._register(ssv, FaultHypothesis("SMGF", [gid]))

        # ── 2. MMGF ───────────────────────────────────────────────────────────
        if fault_model in ("MMGF", "ALL"):
            for order in range(2, max_mmgf_order + 1):
                combos = list(combinations(range(self.n_gates), order))
                print(f"  [MMGF order={order}]  {len(combos)} combinations …")
                for combo in combos:
                    ssv = self._ssv_for_mmgf(list(combo))
                    self._register(ssv, FaultHypothesis("MMGF", list(combo)))

        # ── 3. PMGF ───────────────────────────────────────────────────────────
        if fault_model in ("PMGF", "ALL"):
            pmgf_count = 0
            for gid, gate in enumerate(self.compiled_gates):
                ctrl_bits = _extract_control_bits(gate)
                if not ctrl_bits:
                    continue
                for r in range(1, len(ctrl_bits)):        # ≥1 missing, not all
                    for subset in combinations(ctrl_bits, r):
                        missing_mask = 0
                        for b in subset:
                            missing_mask |= b
                        ssv = self._ssv_for_pmgf(gid, missing_mask)
                        self.pmgf_ssv[(gid, missing_mask)] = ssv
                        self._register(
                            ssv,
                            FaultHypothesis("PMGF", [gid],
                                            missing_mask=missing_mask))
                        pmgf_count += 1
            print(f"  [PMGF]  {pmgf_count} partial-control entries …")

        elapsed = time.perf_counter() - t0
        total = sum(len(v) for v in self.hash_table.values())
        distinct = len(self.hash_table)
        print(f"  Done in {elapsed:.2f}s — "
              f"{total} hypotheses across {distinct} distinct syndromes.\n")
        return self

    # ── lookup ────────────────────────────────────────────────────────────────

    def exact_lookup(self, ssv: np.ndarray) -> List[FaultHypothesis]:
        return self.hash_table.get(_ssv_key(ssv), [])

    def mmgf_approx_lookup(self, ssv: np.ndarray,
                           top_k: int = 5) -> List[Tuple[int, FaultHypothesis]]:
        """
        Use XOR composability: SSV(MMGF[i,j]) ≈ SSV(SMGF[i]) XOR SSV(SMGF[j]).
        Rank by Hamming distance to observed SSV.
        """
        results = []
        gids = list(self.smgf_ssv)
        for i, j in combinations(gids, 2):
            composed = self.smgf_ssv[i] ^ self.smgf_ssv[j]
            dist = int(np.sum(ssv != composed))
            results.append((dist, FaultHypothesis("MMGF", [i, j])))
        results.sort(key=lambda x: x[0])
        return results[:top_k]

    def pmgf_approx_lookup(self, ssv: np.ndarray,
                           top_k: int = 5) -> List[Tuple[int, FaultHypothesis]]:
        """Rank all PMGF entries by Hamming distance."""
        results = []
        for (gid, mask), stored in self.pmgf_ssv.items():
            dist = int(np.sum(ssv != stored))
            results.append((dist,
                             FaultHypothesis("PMGF", [gid], missing_mask=mask)))
        results.sort(key=lambda x: x[0])
        return results[:top_k]

    def summary(self) -> str:
        return (
            f"FaultSyndromeDictionary — "
            f"SMGF:{len(self.smgf_ssv)}  "
            f"PMGF:{len(self.pmgf_ssv)}  "
            f"Total:{sum(len(v) for v in self.hash_table.values())}  "
            f"DistinctSSVs:{len(self.hash_table)}"
        )


# ══════════════════════════════════════════════════════════════════════════════
#  Phase 2 — Fault order classifier
# ══════════════════════════════════════════════════════════════════════════════

def _classify_fault_order(ssv: np.ndarray,
                          n_lines: int,
                          smgf_ssv_map: Dict[int, np.ndarray]) -> str:
    """Heuristic classification: SMGF / MMGF / PMGF / unknown."""

    hw = int(np.sum(ssv))
    if hw == 0:
        return "none"

    # ── exact SMGF match ─────────────────────────────────────────────────────
    for s in smgf_ssv_map.values():
        if np.array_equal(ssv, s):
            return "SMGF"

    # ── exact XOR of two SMGFs ────────────────────────────────────────────────
    gids = list(smgf_ssv_map)
    for i, j in combinations(gids, 2):
        if np.array_equal(ssv, smgf_ssv_map[i] ^ smgf_ssv_map[j]):
            return "MMGF"

    # ── cluster analysis in the SSV 2-D grid ─────────────────────────────────
    m   = len(ssv) // n_lines
    if m == 0:
        return "unknown"
    mat = ssv.reshape(m, n_lines)
    clusters = _count_clusters(mat)
    density  = hw / len(ssv)

    if clusters >= 2:
        return "MMGF"
    if density < 0.25:
        return "PMGF"
    return "SMGF"


def _count_clusters(mat: np.ndarray) -> int:
    """Count connected components of 1-bits in a 2-D binary matrix."""
    rows, cols = mat.shape
    visited    = np.zeros((rows, cols), dtype=bool)
    clusters   = 0

    def bfs(r, c):
        stack = [(r, c)]
        while stack:
            x, y = stack.pop()
            if x < 0 or x >= rows or y < 0 or y >= cols:
                continue
            if visited[x, y] or mat[x, y] == 0:
                continue
            visited[x, y] = True
            stack += [(x-1,y),(x+1,y),(x,y-1),(x,y+1)]

    for r in range(rows):
        for c in range(cols):
            if mat[r, c] == 1 and not visited[r, c]:
                clusters += 1
                bfs(r, c)
    return clusters


# ══════════════════════════════════════════════════════════════════════════════
#  Phase 4 — Bidirectional verification
# ══════════════════════════════════════════════════════════════════════════════

def _bidirectional_verify(circuit: dict,
                           test_set: List[int],
                           golden_outputs: List[int],
                           hypothesis: FaultHypothesis,
                           n_verify: int = 3) -> bool:
    """
    For vectors where a syndrome exists, run:
      • Forward (golden): apply gates 0 … boundary-1
      • Backward (golden inverse): un-apply gates depth-1 … boundary+1

    Both should reach the same intermediate state at the boundary if the
    hypothesis is correct.  Reversible gates are self-inverse, so the
    inverse is just forward application in reverse order.
    """
    compiled_gates = circuit["Compiled Rep"]
    boundary = min(hypothesis.gate_ids)
    checked = passed = 0

    for tv, go in zip(test_set, golden_outputs):
        if tv ^ go == 0:           # no syndrome on this vector, skip
            continue
        if checked >= n_verify:
            break
        checked += 1

        # Forward to boundary
        state_fwd = tv
        for idx, gate in enumerate(compiled_gates):
            if idx >= boundary:
                break
            state_fwd = apply_gate(state_fwd, gate)

        # Backward from golden output to just past boundary
        state_bwd = go
        for idx in range(len(compiled_gates) - 1, boundary, -1):
            state_bwd = _apply_gate_inverse(state_bwd, compiled_gates[idx])

        if state_fwd == state_bwd:
            passed += 1

    return checked > 0 and passed == checked


# ══════════════════════════════════════════════════════════════════════════════
#  Phase 5 — Equivalence class resolution
# ══════════════════════════════════════════════════════════════════════════════

def _find_discriminating_vector(circuit: dict,
                                 hypotheses: List[FaultHypothesis],
                                 existing_test_set: Set[int]) -> Optional[int]:
    """
    Search 2^n_lines inputs for one that produces different outputs under
    different fault hypotheses → use it to split the equivalence class.

    Exhaustive for n_lines ≤ 16; otherwise returns None (use random sampling).
    """
    n = circuit["No of Lines"]
    if n > 16:
        return None

    best_vec   = None
    best_score = -1

    for val in range(2 ** n):
        if val in existing_test_set:
            continue

        outputs = set()
        for hyp in hypotheses:
            if hyp.fault_type == "SMGF":
                out = _simulate_smgf(circuit, val, hyp.gate_ids[0])
            elif hyp.fault_type == "MMGF":
                out = _simulate_mmgf(circuit, val, hyp.gate_ids)
            else:  # PMGF
                out = _simulate_pmgf(circuit, val,
                                     hyp.gate_ids[0], hyp.missing_mask)
            outputs.add(out)

        diversity = len(outputs)
        if diversity > best_score:
            best_score = diversity
            best_vec   = val
            if diversity == len(hypotheses):  # perfect discrimination
                break

    return best_vec


# ══════════════════════════════════════════════════════════════════════════════
#  Main Localizer Class
# ══════════════════════════════════════════════════════════════════════════════

class RSVSLocalizer:
    """
    RSVS Fault Localizer — drop-in integration with your project.

    Parameters
    ──────────
    circuit     : dict produced by RealFileParser.parse_file()
                  Must contain "Compiled Rep", "No of Lines", "No of Gates".

    test_set    : list[int] — your complete test set, each element is an
                  integer bitmask (same convention as simulate_fault_free).

    fault_model : "SMGF" | "MMGF" | "PMGF" | "ALL"
                  Controls which fault types the offline dictionary builds.
    """

    def __init__(self, circuit: dict,
                 test_set: List[int],
                 fault_model: str = "ALL"):
        self.circuit       = circuit
        self.test_set      = test_set
        self.fault_model   = fault_model
        self.n_lines       = circuit["No of Lines"]
        self.n_gates       = circuit["No of Gates"]

        # Pre-compute golden outputs once (reused by both offline and online)
        print("Computing golden outputs …")
        self.golden_outputs: List[int] = [
            simulate_fault_free(circuit, tv) for tv in test_set
        ]

        self._fsd: Optional[_FaultSyndromeDictionary] = None

    # ── offline ───────────────────────────────────────────────────────────────

    def build_dictionary(self, max_mmgf_order: int = 2) -> "RSVSLocalizer":
        """
        OFFLINE PHASE — call once before any localize() calls.

        max_mmgf_order : maximum number of simultaneously missing gates to
                         enumerate for MMGF (default 2 = pairs).
        """
        print(f"\n{'='*65}")
        print(f"  Building Fault Syndrome Dictionary")
        print(f"  Circuit : {self.circuit.get('Circuit Name', '?')}  "
              f"({self.n_lines} lines, {self.n_gates} gates)")
        print(f"  Test Set: {len(self.test_set)} vectors")
        print(f"  Model   : {self.fault_model}")
        print(f"{'='*65}")

        self._fsd = _FaultSyndromeDictionary(
            self.circuit, self.test_set, self.golden_outputs
        )
        self._fsd.build(fault_model=self.fault_model,
                        max_mmgf_order=max_mmgf_order)
        print(self._fsd.summary())
        return self

    # ── online ────────────────────────────────────────────────────────────────

    def localize(self,
                 actual_outputs: List[int],
                 resolve_equiv: bool = True,
                 verbose: bool = True) -> LocalizationResult:
        """
        ONLINE PHASE — given actual integer outputs from the CUT,
        return a LocalizationResult.

        actual_outputs : list[int] — one integer per test vector, same order
                         as self.test_set.  Each integer is the output bitmask
                         exactly as returned by simulate_fault_free().
        """
        assert self._fsd is not None, \
            "Call build_dictionary() before localize()."

        result = LocalizationResult()

        # ── Phase 1: compute SSV ──────────────────────────────────────────────
        ssv = _compute_ssv(self.golden_outputs, actual_outputs, self.n_lines)
        result.ssv = ssv
        hw = int(np.sum(ssv))

        if verbose:
            print(f"\n{'='*65}")
            print(f"  Phase 1 — Syndrome  (Hamming weight = {hw})")

        if hw == 0:
            result.status     = "no_fault"
            result.fault_order = "none"
            result.notes.append("All test vectors passed — circuit is fault-free.")
            if verbose:
                print(result)
            return result

        # ── Phase 2: classify fault order ─────────────────────────────────────
        fault_order = _classify_fault_order(
            ssv, self.n_lines, self._fsd.smgf_ssv)
        result.fault_order = fault_order
        if verbose:
            print(f"  Phase 2 — Fault order: {fault_order}")

        # ── Phase 3: dictionary lookup ────────────────────────────────────────
        if verbose:
            print("  Phase 3 — Dictionary lookup …")

        candidates: List[FaultHypothesis] = []

        # Fast O(1) exact hash match first — covers any pre-computed entry
        exact = self._fsd.exact_lookup(ssv)
        if exact:
            candidates = exact
            if verbose:
                print(f"    Exact hash match: {len(candidates)} hypothesis(es)")

        # No exact match → approximate fallback
        if not candidates:
            if fault_order in ("MMGF", "unknown"):
                approx = self._fsd.mmgf_approx_lookup(ssv, top_k=5)
                if verbose:
                    print(f"    MMGF XOR-approx top-5: "
                          f"{[(d, str(h)) for d, h in approx]}")
                if approx:
                    d0 = approx[0][0]
                    if d0 == 0:
                        candidates = [approx[0][1]]
                    else:
                        candidates = [h for d, h in approx if d <= d0 + 2]
                        result.notes.append(
                            f"MMGF approx — best XOR-distance = {d0}")

            if fault_order in ("PMGF", "unknown") and not candidates:
                approx = self._fsd.pmgf_approx_lookup(ssv, top_k=5)
                if verbose:
                    print(f"    PMGF mask-approx top-5: "
                          f"{[(d, str(h)) for d, h in approx]}")
                if approx:
                    d0 = approx[0][0]
                    if d0 == 0:
                        candidates = [approx[0][1]]
                    else:
                        candidates = [h for d, h in approx if d <= d0 + 2]
                        result.notes.append(
                            f"PMGF approx — best mask-distance = {d0}")

        if not candidates:
            result.status = "no_match"
            result.notes.append(
                "No matching hypothesis found. "
                "Consider re-building dictionary with larger max_mmgf_order "
                "or ensure fault_model covers the fault type present.")
            if verbose:
                print(result)
            return result

        # ── Phase 4: bidirectional verification ───────────────────────────────
        if verbose:
            print("  Phase 4 — Bidirectional verification …")

        verified: List[FaultHypothesis] = []
        for hyp in candidates:
            ok = _bidirectional_verify(
                self.circuit, self.test_set, self.golden_outputs,
                hyp, n_verify=3)
            hyp.verified = ok
            if ok:
                verified.append(hyp)
            if verbose:
                mark = "✓" if ok else "✗"
                print(f"    {mark}  {hyp}")

        # Prefer verified hypotheses; fall back to all if none verified
        if verified:
            candidates = verified

        # ── Phase 5: pick result / equivalence class ──────────────────────────
        if len(candidates) == 1:
            h = candidates[0]
            h.confidence   = 1.0 if h.verified else 0.8
            result.status  = "located"
            result.primary = h

        else:
            # Assign confidence inversely proportional to class size
            for h in candidates:
                h.confidence = round(0.6 / len(candidates), 3)
            result.status         = "equiv_class"
            result.primary        = candidates[0]
            result.equivalence_cls = candidates
            result.notes.append(
                f"Equivalence class of {len(candidates)} indistinguishable "
                f"fault(s). Run the suggested discriminating vector to resolve.")

            if resolve_equiv:
                if verbose:
                    print("  Phase 5 — Finding discriminating vector …")
                disc = _find_discriminating_vector(
                    self.circuit, candidates,
                    existing_test_set=set(self.test_set))
                if disc is not None:
                    result.discriminating_vector = disc
                    if verbose:
                        print(f"    → Suggested: {disc}  (0b{disc:b})")
                else:
                    result.notes.append(
                        "Circuit has >16 lines — use random sampling to find "
                        "a discriminating vector.")

        if verbose:
            print(result)

        return result

    # ── convenience: simulate CUT with an injected fault ─────────────────────

    def simulate_cut(self, fault_type: str,
                     gate_ids: List[int],
                     missing_mask: int = 0) -> List[int]:
        """
        Convenience method: simulate the full test set under a given injected
        fault and return actual_outputs ready to pass into localize().

        Useful for rapid testing / validation.
        """
        results = []
        for tv in self.test_set:
            if fault_type == "SMGF":
                out = _simulate_smgf(self.circuit, tv, gate_ids[0])
            elif fault_type == "MMGF":
                out = _simulate_mmgf(self.circuit, tv, gate_ids)
            elif fault_type == "PMGF":
                out = _simulate_pmgf(self.circuit, tv, gate_ids[0], missing_mask)
            else:
                out = simulate_fault_free(self.circuit, tv)
            results.append(out)
        return results
