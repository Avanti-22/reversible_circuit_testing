"""
reversible_circuit.py
Core data structures for reversible circuit simulation.
Supports NOT, CNOT, Toffoli (k-CNOT), and Fredkin gates.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import numpy as np


# ──────────────────────────────────────────────────────────────────────────────
# Gate definitions
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class Gate:
    """
    A single reversible gate.

    gate_type : 'NOT' | 'CNOT' | 'TOFFOLI' | 'FREDKIN'
    controls  : list of control-line indices (0-based)
    target    : target-line index  (or [target1, target2] for FREDKIN)
    gate_id   : unique position index in the cascade (0 = first gate)
    """
    gate_type : str
    controls  : List[int]
    target    : int          # for FREDKIN this is target1; target2 stored in controls[-1]
    gate_id   : int = 0
    label     : str = ""

    def __post_init__(self):
        if not self.label:
            self.label = f"G{self.gate_id}"

    # ── apply this gate to a state vector (list/array of bits) ──────────────
    def apply(self, state: List[int]) -> List[int]:
        s = list(state)
        if self.gate_type == "NOT":
            s[self.target] ^= 1

        elif self.gate_type in ("CNOT", "TOFFOLI"):
            if all(s[c] == 1 for c in self.controls):
                s[self.target] ^= 1

        elif self.gate_type == "FREDKIN":
            # controls[-1] is target2; self.target is target1
            ctrl_lines = self.controls[:-1]
            t1, t2 = self.target, self.controls[-1]
            if all(s[c] == 1 for c in ctrl_lines):
                s[t1], s[t2] = s[t2], s[t1]

        return s

    # ── inverse (reversible gates are self-inverse except Fredkin; same here) ──
    def apply_inverse(self, state: List[int]) -> List[int]:
        return self.apply(state)   # all gates here are self-inverse

    def __repr__(self):
        return (f"{self.label}({self.gate_type} ctrl={self.controls} "
                f"tgt={self.target})")


# ──────────────────────────────────────────────────────────────────────────────
# Fault model
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class FaultSpec:
    """
    Describes a single fault injected into the circuit.

    fault_type : 'SMGF'  – gate completely missing
                 'MMGF'  – multiple gates missing  (gate_ids lists them)
                 'PMGF'  – partial missing: some control lines removed
    gate_ids   : affected gate indices
    missing_controls : for PMGF, which control indices are dropped
    """
    fault_type       : str
    gate_ids         : List[int]
    missing_controls : List[int] = field(default_factory=list)

    def __repr__(self):
        if self.fault_type == "PMGF":
            return (f"PMGF(gates={self.gate_ids}, "
                    f"missing_ctrl={self.missing_controls})")
        return f"{self.fault_type}(gates={self.gate_ids})"


# ──────────────────────────────────────────────────────────────────────────────
# Reversible Circuit
# ──────────────────────────────────────────────────────────────────────────────

class ReversibleCircuit:
    """
    A cascade of reversible gates over `n_lines` wires.
    """

    def __init__(self, n_lines: int):
        self.n_lines = n_lines
        self.gates   : List[Gate] = []

    # ── gate builders ─────────────────────────────────────────────────────────
    def add_not(self, target: int) -> "ReversibleCircuit":
        g = Gate("NOT", [], target, gate_id=len(self.gates))
        self.gates.append(g)
        return self

    def add_cnot(self, control: int, target: int) -> "ReversibleCircuit":
        g = Gate("CNOT", [control], target, gate_id=len(self.gates))
        self.gates.append(g)
        return self

    def add_toffoli(self, controls: List[int], target: int) -> "ReversibleCircuit":
        g = Gate("TOFFOLI", list(controls), target, gate_id=len(self.gates))
        self.gates.append(g)
        return self

    def add_fredkin(self, controls: List[int],
                    target1: int, target2: int) -> "ReversibleCircuit":
        # target2 stored as last element of controls list (convention)
        g = Gate("FREDKIN", list(controls) + [target2], target1,
                 gate_id=len(self.gates))
        self.gates.append(g)
        return self

    # ── simulation ────────────────────────────────────────────────────────────
    def simulate(self, input_vec: List[int],
                 fault: Optional[FaultSpec] = None) -> List[int]:
        """
        Simulate the circuit on `input_vec`.
        If `fault` is given, the faulty version is simulated.
        Returns the output as a list of bits.
        """
        state = list(input_vec)
        faulty_ids = set(fault.gate_ids) if fault else set()

        for gate in self.gates:
            # ── SMGF / MMGF: skip the gate entirely ──────────────────────────
            if fault and fault.fault_type in ("SMGF", "MMGF"):
                if gate.gate_id in faulty_ids:
                    continue

            # ── PMGF: apply gate with reduced control set ─────────────────────
            elif fault and fault.fault_type == "PMGF":
                if gate.gate_id in faulty_ids:
                    # build a modified gate with missing controls removed
                    reduced_ctrl = [c for c in gate.controls
                                    if c not in fault.missing_controls]
                    modified = Gate(gate.gate_type, reduced_ctrl,
                                    gate.target, gate.gate_id)
                    state = modified.apply(state)
                    continue

            state = gate.apply(state)

        return state

    # ── inverse simulation (right-to-left) ───────────────────────────────────
    def simulate_inverse(self, output_vec: List[int],
                         fault: Optional[FaultSpec] = None) -> List[int]:
        state = list(output_vec)
        faulty_ids = set(fault.gate_ids) if fault else set()

        for gate in reversed(self.gates):
            if fault and fault.fault_type in ("SMGF", "MMGF"):
                if gate.gate_id in faulty_ids:
                    continue
            elif fault and fault.fault_type == "PMGF":
                if gate.gate_id in faulty_ids:
                    reduced_ctrl = [c for c in gate.controls
                                    if c not in fault.missing_controls]
                    modified = Gate(gate.gate_type, reduced_ctrl,
                                    gate.target, gate.gate_id)
                    state = modified.apply_inverse(state)
                    continue
            state = gate.apply_inverse(state)

        return state

    def depth(self) -> int:
        return len(self.gates)

    def __repr__(self):
        lines = [f"ReversibleCircuit({self.n_lines} lines, "
                 f"{len(self.gates)} gates)"]
        for g in self.gates:
            lines.append(f"  {g}")
        return "\n".join(lines)
