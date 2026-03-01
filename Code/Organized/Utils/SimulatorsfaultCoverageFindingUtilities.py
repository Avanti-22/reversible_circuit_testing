import random
from itertools import combinations
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Type alias
# CircuitState is a plain int used as a bitmask.
# Bit i is set ↔ line i carries value 1.
# This makes every gate operation (control check, target flip, swap)
# a single CPU-level bitwise instruction instead of O(n) list indexing.
# ---------------------------------------------------------------------------
CircuitState = int


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def convert_integer_to_binary(input_vector: int, max_value: int) -> List[int]:
    """Convert an integer to a zero-padded binary list of length `max_value`."""
    return [int(b) for b in format(input_vector, f'0{max_value}b')]


def generate_random_vector(circuit: Dict) -> List[int]:
    """Generate a random binary vector matching the circuit's line count."""
    n = circuit["No of Lines"]
    return convert_integer_to_binary(random.randint(0, 2 ** n - 1), n)


def build_index_map(circuit: Dict) -> Dict[str, int]:
    """Map each variable name to its index in the binary vector."""
    return {var: i for i, var in enumerate(circuit["Variables"])}


# ---------------------------------------------------------------------------
# List[int] ↔ CircuitState conversion
#
# Public API keeps List[int] for compatibility with callers.
# All internal simulation runs on CircuitState (int bitmask).
# Bit ordering: variable at index 0 → MSB (leftmost bit), matching
# the natural binary representation used by convert_integer_to_binary.
# ---------------------------------------------------------------------------

def _vec_to_state(vec: List[int], n: int) -> CircuitState:
    """Pack a List[int] of bits into a single integer (MSB = index 0)."""
    state = 0
    for bit in vec:
        state = (state << 1) | bit
    return state


def _state_to_vec(state: CircuitState, n: int) -> List[int]:
    """Unpack a CircuitState integer back to a List[int] of length n."""
    return [(state >> (n - 1 - i)) & 1 for i in range(n)]


def _bit(state: CircuitState, idx: int, n: int) -> int:
    """Read bit at variable index `idx` (index 0 = MSB)."""
    return (state >> (n - 1 - idx)) & 1


def _flip(state: CircuitState, idx: int, n: int) -> CircuitState:
    """Flip bit at variable index `idx`."""
    return state ^ (1 << (n - 1 - idx))


def _set_bit(state: CircuitState, idx: int, n: int, val: int) -> CircuitState:
    """Set bit at variable index `idx` to `val` (0 or 1)."""
    mask = 1 << (n - 1 - idx)
    return (state & ~mask) | (val * mask)


# ---------------------------------------------------------------------------
# Precomputed gate descriptors
#
# Each gate in circuit["Gates"] is parsed once into a compact descriptor
# tuple so the hot simulation loop never touches dicts or does string
# comparisons.
#
# Descriptor formats (all indices are already resolved to bit positions):
#   TOFFOLI : ("T", ctrl_mask, target_mask, target_bit)
#   FREDKIN : ("F", ctrl_mask, bit1, bit2, swap_mask)
#   PERES   : ("P", ctrl_mask, sl_bit, tl_bit, last_bit, target_mask)
#
# ctrl_mask  : bitmask — all control bits must be 1 for the gate to fire
# target_mask: bitmask of the target bit (1 << bit_pos)
# ---------------------------------------------------------------------------

def _build_gate_descriptor(gate: Dict, idx_map: Dict[str, int], n: int) -> Tuple:
    """Convert a gate dict to a precomputed descriptor tuple."""
    parts = gate["vars"]
    gate_type = gate["gate"]

    if gate_type == "TOFFOLI":
        ctrl_mask = 0
        for c in parts[:-1]:
            ctrl_mask |= (1 << (n - 1 - idx_map[c]))
        t_idx = idx_map[parts[-1]]
        return ("T", ctrl_mask, 1 << (n - 1 - t_idx), t_idx)

    elif gate_type == "FREDKIN":
        ctrl_mask = 0
        for c in parts[:-2]:
            ctrl_mask |= (1 << (n - 1 - idx_map[c]))
        b1 = idx_map[parts[-2]]
        b2 = idx_map[parts[-1]]
        # swap_mask covers both swap bits; used to extract and re-insert
        return ("F", ctrl_mask, b1, b2, n)

    elif gate_type == "PERES":
        # Controls = all but last; XOR target = second-to-last; flip = last
        ctrl_mask = 0
        for c in parts[:-1]:
            ctrl_mask |= (1 << (n - 1 - idx_map[c]))
        sl_idx = idx_map[parts[-2]]
        tl_idx = idx_map[parts[-3]]
        last_idx = idx_map[parts[-1]]
        return ("P", ctrl_mask, sl_idx, tl_idx, last_idx, n)

    return None


def _precompute_descriptors(circuit: Dict, idx_map: Dict[str, int]) -> List[Tuple]:
    """Precompute all gate descriptors for a circuit."""
    n = circuit["No of Lines"]
    return [
        _build_gate_descriptor(gate, idx_map, n)
        for gate in circuit["Gates"]
    ]


# ---------------------------------------------------------------------------
# Gate application on CircuitState (bitmask)
# ---------------------------------------------------------------------------

def _apply_descriptor(state: CircuitState, desc: Tuple) -> CircuitState:
    """Apply a precomputed gate descriptor to a CircuitState. All O(1)."""
    kind = desc[0]

    if kind == "T":
        _, ctrl_mask, target_mask, _ = desc
        # Fire if all control bits are 1: (state & ctrl_mask) == ctrl_mask
        if (state & ctrl_mask) == ctrl_mask:
            state ^= target_mask          # flip target bit
        return state

    elif kind == "F":
        _, ctrl_mask, b1, b2, n = desc
        if (state & ctrl_mask) == ctrl_mask:
            v1 = _bit(state, b1, n)
            v2 = _bit(state, b2, n)
            if v1 != v2:                  # only act if bits differ (swap has effect)
                state = _flip(state, b1, n)
                state = _flip(state, b2, n)
        return state

    elif kind == "P":
        _, ctrl_mask, sl_idx, tl_idx, last_idx, n = desc
        tl_val = _bit(state, tl_idx, n)
        sl_val = _bit(state, sl_idx, n)
        state  = _set_bit(state, sl_idx, n, sl_val ^ tl_val)  # XOR step
        if (state & ctrl_mask) == ctrl_mask:
            state = _flip(state, last_idx, n)                  # conditional flip
        return state

    return state


# ---------------------------------------------------------------------------
# Core simulation (fault-free)
# ---------------------------------------------------------------------------

def simulate_circuit(circuit: Dict, binary_vector: List[int]) -> List[int]:
    """Simulate a circuit without any fault injection."""
    n       = circuit["No of Lines"]
    idx_map = build_index_map(circuit)
    descs   = _precompute_descriptors(circuit, idx_map)
    state   = _vec_to_state(binary_vector, n)

    for desc in descs:
        state = _apply_descriptor(state, desc)

    return _state_to_vec(state, n)


# ---------------------------------------------------------------------------
# Fault injection helpers (bitmask-native)
# ---------------------------------------------------------------------------

def _apply_bridging_fault(
    state: CircuitState, fault: Tuple, idx_map: Dict[str, int], n: int
) -> CircuitState:
    """Apply a single bridging fault (AND-wired or OR-wired). O(1)."""
    _, wire1, wire2, mode = fault
    i1, i2 = idx_map[wire1], idx_map[wire2]
    v1, v2 = _bit(state, i1, n), _bit(state, i2, n)
    wired = v1 & v2 if mode == "AND-wired" else v1 | v2
    state = _set_bit(state, i1, n, wired)
    state = _set_bit(state, i2, n, wired)
    return state


def _get_fault_info(circuit: Dict) -> Tuple[Optional[str], Any]:
    """Return (fault_model, fault_position) from circuit dict."""
    return (
        circuit.get("Fault Model"),
        circuit.get("Fault Position", circuit.get("Fault Positions")),
    )


# ---------------------------------------------------------------------------
# Faulty simulators — all operate on CircuitState internally
# ---------------------------------------------------------------------------

def simulate_SAF_circuit(
    circuit: Dict, binary_vector: List[int], is_faulty: bool = True
) -> List[int]:
    """Simulate with Stuck-At-0 or Stuck-At-1 fault."""
    n       = circuit["No of Lines"]
    idx_map = build_index_map(circuit)
    state   = _vec_to_state(binary_vector, n)
    fault_model, fault_position = _get_fault_info(circuit)
    stuck_val = 0 if fault_model == "SA-0" else 1

    for count, gate in enumerate(circuit["Gates"]):
        if is_faulty and fault_model in ("SA-0", "SA-1") and fault_position is not None:
            for var in gate["vars"]:
                if (count, var) == fault_position:
                    state = _set_bit(state, idx_map[var], n, stuck_val)

        desc  = _build_gate_descriptor(gate, idx_map, n)
        state = _apply_descriptor(state, desc)

    return _state_to_vec(state, n)


def simulate_SMGF_circuit(
    circuit: Dict, binary_vector: List[int], is_faulty: bool = True
) -> List[int]:
    """Simulate with Single Missing Gate Fault."""
    n       = circuit["No of Lines"]
    idx_map = build_index_map(circuit)
    state   = _vec_to_state(binary_vector, n)
    fault_model, fault_position = _get_fault_info(circuit)

    for count, gate in enumerate(circuit["Gates"]):
        if is_faulty and fault_model == "SMGF" and fault_position and count in fault_position:
            continue
        state = _apply_descriptor(state, _build_gate_descriptor(gate, idx_map, n))

    return _state_to_vec(state, n)


def simulate_MMGF_circuit(
    circuit: Dict, binary_vector: List[int], is_faulty: bool = True
) -> List[int]:
    """Simulate with Multiple Missing Gate Fault."""
    n       = circuit["No of Lines"]
    idx_map = build_index_map(circuit)
    state   = _vec_to_state(binary_vector, n)
    fault_model, fault_position = _get_fault_info(circuit)

    for count, gate in enumerate(circuit["Gates"]):
        if is_faulty and fault_model == "MMGF" and fault_position and count in fault_position:
            continue
        state = _apply_descriptor(state, _build_gate_descriptor(gate, idx_map, n))

    return _state_to_vec(state, n)


def simulate_PMGF_circuit(
    circuit: Dict, binary_vector: List[int], is_faulty: bool = True
) -> List[int]:
    """Simulate with Partial Missing Gate Fault (missing some control bits)."""
    n       = circuit["No of Lines"]
    idx_map = build_index_map(circuit)
    state   = _vec_to_state(binary_vector, n)
    fault_model, fault_position = _get_fault_info(circuit)

    for count, gate in enumerate(circuit["Gates"]):
        gate_type = gate["gate"]
        parts     = gate["vars"]

        missing = set()
        if is_faulty and fault_model == "PMGF" and fault_position and count == fault_position[0]:
            missing = set(fault_position[1])

        if not missing:
            state = _apply_descriptor(state, _build_gate_descriptor(gate, idx_map, n))
        else:
            # Rebuild descriptor with only the active control indices
            n_controls = len(parts) - 1 if gate_type != "FREDKIN" else len(parts) - 2
            active_controls = [parts[c] for c in range(n_controls) if c not in missing]

            partial_gate = {
                "gate": gate_type,
                "vars": active_controls + (parts[-2:] if gate_type == "FREDKIN" else parts[-1:]),
            }
            state = _apply_descriptor(state, _build_gate_descriptor(partial_gate, idx_map, n))

    return _state_to_vec(state, n)


def simulate_RGF_circuit(
    circuit: Dict, binary_vector: List[int], is_faulty: bool = True
) -> List[int]:
    """Simulate with Repeated Gate Fault (Odd repeats the gate; Even is a no-op)."""
    n       = circuit["No of Lines"]
    idx_map = build_index_map(circuit)
    state   = _vec_to_state(binary_vector, n)
    fault_model, fault_position = _get_fault_info(circuit)

    for count, gate in enumerate(circuit["Gates"]):
        desc  = _build_gate_descriptor(gate, idx_map, n)
        state = _apply_descriptor(state, desc)

        if is_faulty and count == fault_position and fault_model == "RGF-Odd":
            state = _apply_descriptor(state, desc)   # apply second time

    return _state_to_vec(state, n)


def simulate_GAF_circuit(
    circuit: Dict, binary_vector: List[int], is_faulty: bool = True
) -> List[int]:
    """Simulate with Ghost/Added Gate Fault (an extra gate inserted after a position)."""
    n       = circuit["No of Lines"]
    idx_map = build_index_map(circuit)
    gates   = circuit["Gates"]
    working_gates = gates

    if is_faulty and circuit.get("Fault Model") == "GAF":
        fault_position = circuit.get("Fault Position", circuit.get("Fault Positions"))
        fault_gate     = circuit.get("Fault Gate")

        insert_at = None
        if isinstance(fault_position, int):
            insert_at = max(0, min(fault_position + 1, len(gates)))
        elif isinstance(fault_position, (list, tuple)) and fault_position:
            first = fault_position[0]
            if isinstance(first, int):
                insert_at = max(0, min(first + 1, len(gates)))

        extra_gate = None
        if isinstance(fault_gate, dict):
            extra_gate = fault_gate
        elif insert_at is not None and 0 <= insert_at - 1 < len(gates):
            extra_gate = gates[insert_at - 1]

        if extra_gate is not None and insert_at is not None:
            working_gates = gates[:insert_at] + [extra_gate] + gates[insert_at:]

    state = _vec_to_state(binary_vector, n)
    for gate in working_gates:
        state = _apply_descriptor(state, _build_gate_descriptor(gate, idx_map, n))

    return _state_to_vec(state, n)


def simulate_CAF_circuit(
    circuit: Dict, binary_vector: List[int], is_faulty: bool = True
) -> List[int]:
    """Simulate with Control Added Fault (extra control line injected into a gate)."""
    n       = circuit["No of Lines"]
    idx_map = build_index_map(circuit)
    state   = _vec_to_state(binary_vector, n)
    fault_model, fault_position = _get_fault_info(circuit)

    for count, gate in enumerate(circuit["Gates"]):
        gate_type = gate["gate"]
        parts     = gate["vars"].copy()

        if (
            is_faulty
            and fault_model == "CAF"
            and fault_position is not None
            and count == fault_position[0]
        ):
            extra_ctrl = fault_position[1]
            if extra_ctrl not in parts and len(parts) < circuit["No of Lines"]:
                if gate_type == "FREDKIN":
                    parts = parts[:-2] + [extra_ctrl] + parts[-2:]
                else:
                    parts = parts[:-1] + [extra_ctrl] + parts[-1:]

        modified_gate = {"gate": gate_type, "vars": parts}
        state = _apply_descriptor(state, _build_gate_descriptor(modified_gate, idx_map, n))

    return _state_to_vec(state, n)


def simulate_BF_circuit(
    circuit: Dict, binary_vector: List[int], is_faulty: bool = True
) -> List[int]:
    """Simulate with a single Bridging Fault."""
    n       = circuit["No of Lines"]
    idx_map = build_index_map(circuit)
    state   = _vec_to_state(binary_vector, n)
    fault_model, fault_position = _get_fault_info(circuit)

    for count, gate in enumerate(circuit["Gates"]):
        if (
            is_faulty
            and fault_model == "BF"
            and fault_position is not None
            and count == fault_position[0]
        ):
            state = _apply_bridging_fault(state, fault_position, idx_map, n)

        state = _apply_descriptor(state, _build_gate_descriptor(gate, idx_map, n))

    return _state_to_vec(state, n)


def simulate_MBF_circuit(
    circuit: Dict, binary_vector: List[int], is_faulty: bool = True
) -> List[int]:
    """Simulate with Multiple Bridging Faults."""
    n       = circuit["No of Lines"]
    idx_map = build_index_map(circuit)
    state   = _vec_to_state(binary_vector, n)
    fault_model, fault_position = _get_fault_info(circuit)

    for count, gate in enumerate(circuit["Gates"]):
        if is_faulty and fault_model in ("Multiple BF", "MBF") and fault_position:
            for fault in fault_position:
                if count == fault[0]:
                    state = _apply_bridging_fault(state, fault, idx_map, n)

        state = _apply_descriptor(state, _build_gate_descriptor(gate, idx_map, n))

    return _state_to_vec(state, n)


# ---------------------------------------------------------------------------
# Fault enumeration helpers
# ---------------------------------------------------------------------------

def _subsets(items: List, size: int):
    """Yield all subsets of `items` with exactly `size` elements."""
    if size == 0:
        yield []
        return
    for i, item in enumerate(items):
        for rest in _subsets(items[i + 1:], size - 1):
            yield [item] + rest


def faulty_op_for_SAF(
    circuit: Dict, input_vec: List[int], fault_model: str
) -> List[List[int]]:
    faulty_circuit = {**circuit, "Fault Model": fault_model}
    outputs = []
    for i, gate in enumerate(circuit["Gates"]):
        for var in gate["vars"]:
            faulty_circuit["Fault Position"] = (i, var)
            outputs.append(simulate_SAF_circuit(faulty_circuit, input_vec, True))
    return outputs


def faulty_op_for_SMGF(circuit: Dict, input_vec: List[int]) -> List[List[int]]:
    faulty_circuit = {**circuit, "Fault Model": "SMGF"}
    return [
        simulate_SMGF_circuit({**faulty_circuit, "Fault Position": [i]}, input_vec, True)
        for i in range(len(circuit["Gates"]))
    ]


def faulty_op_for_MMGF(circuit: Dict, input_vec: List[int]) -> List[List[int]]:
    n_gates     = circuit["No of Gates"]
    gate_indices = list(range(n_gates))
    faulty_circuit = {**circuit, "Fault Model": "MMGF"}
    outputs = []

    for size in range(1, n_gates):
        for subset in _subsets(gate_indices, size):
            faulty_circuit["Fault Position"] = subset
            outputs.append(simulate_MMGF_circuit(faulty_circuit, input_vec, True))

    return outputs


def faulty_op_for_PMGF(circuit: Dict, input_vec: List[int]) -> List[List[int]]:
    faulty_circuit = {**circuit, "Fault Model": "PMGF"}
    outputs  = []
    n_lines  = circuit["No of Lines"]

    for i, gate in enumerate(circuit["Gates"]):
        wire_indices = list(range(len(gate["vars"])))
        for size in range(1, n_lines):
            for subset in _subsets(wire_indices, size):
                faulty_circuit["Fault Position"] = (i, subset)
                outputs.append(simulate_PMGF_circuit(faulty_circuit, input_vec, True))

    return outputs


def faulty_op_for_RGF(
    circuit: Dict, input_vec: List[int], n: str = "Odd"
) -> List[List[int]]:
    fault_model    = "RGF-Even" if n == "Even" else "RGF-Odd"
    faulty_circuit = {**circuit, "Fault Model": fault_model}
    return [
        simulate_RGF_circuit({**faulty_circuit, "Fault Position": i}, input_vec, True)
        for i in range(len(circuit["Gates"]))
    ]


def faulty_op_for_GAF(circuit: Dict, input_vec: List[int]) -> List[List[int]]:
    faulty_circuit = {**circuit, "Fault Model": "GAF"}
    return [
        simulate_GAF_circuit({**faulty_circuit, "Fault Position": i - 1}, input_vec, True)
        for i in range(len(circuit["Gates"]) + 1)
    ]


def faulty_op_for_CAF(circuit: Dict, input_vec: List[int]) -> List[List[int]]:
    faulty_circuit = {**circuit, "Fault Model": "CAF"}
    outputs = []
    for i, gate in enumerate(circuit["Gates"]):
        for var in circuit["Variables"]:
            if var in gate["vars"]:
                continue
            faulty_circuit["Fault Position"] = (i, var)
            outputs.append(simulate_CAF_circuit(faulty_circuit, input_vec, True))
    return outputs


def faulty_op_for_BF(circuit: Dict, input_vec: List[int]) -> List[List[int]]:
    faulty_circuit = {**circuit, "Fault Model": "BF"}
    variables = circuit["Variables"]
    outputs   = []

    for i in range(len(circuit["Gates"])):
        for j in range(len(variables)):
            for k in range(j + 1, len(variables)):
                w1, w2 = variables[j], variables[k]
                for mode in ("AND-wired", "OR-wired"):
                    faulty_circuit["Fault Position"] = (i, w1, w2, mode)
                    outputs.append(simulate_BF_circuit(faulty_circuit, input_vec, True))

    return outputs


def faulty_op_for_MBF(
    circuit: Dict, input_vec: List[int], max_faults_per_gate: int = 2
) -> List[List[int]]:
    faulty_circuit = {**circuit, "Fault Model": "Multiple BF"}
    variables = circuit["Variables"]
    outputs   = []

    for i in range(len(circuit["Gates"])):
        single_faults = [
            (variables[j], variables[k], mode)
            for j in range(len(variables))
            for k in range(j + 1, len(variables))
            for mode in ("AND-wired", "OR-wired")
        ]
        max_size = min(max_faults_per_gate, len(single_faults)) if max_faults_per_gate else len(single_faults)

        for size in range(2, max_size + 1):
            for subset in _subsets(list(range(len(single_faults))), size):
                fault_position = [(i, *single_faults[x]) for x in subset]
                faulty_circuit["Fault Position"] = fault_position
                outputs.append(simulate_MBF_circuit(faulty_circuit, input_vec, True))

    return outputs


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

_FAULT_DISPATCH = {
    "SA-0": lambda c, v: faulty_op_for_SAF(c, v, "SA-0"),
    "SA-1": lambda c, v: faulty_op_for_SAF(c, v, "SA-1"),
    "SMGF": lambda c, v: faulty_op_for_SMGF(c, v),
    "PMGF": lambda c, v: faulty_op_for_PMGF(c, v),
    "MMGF": lambda c, v: faulty_op_for_MMGF(c, v),
    "RGF":  lambda c, v: faulty_op_for_RGF(c, v, "Odd"),
    "GAF":  lambda c, v: faulty_op_for_GAF(c, v),
    "CAF":  lambda c, v: faulty_op_for_CAF(c, v),
    "BF":   lambda c, v: faulty_op_for_BF(c, v),
    "MBF":  lambda c, v: faulty_op_for_MBF(c, v),
}


def get_all_faulty_outputs(
    circuit: Dict, test_vec: List[int], fault_model: str
) -> List[List[int]]:
    """Return all faulty output vectors for the given fault model."""
    handler = _FAULT_DISPATCH.get(fault_model)
    if handler is None:
        raise ValueError(f"Unknown fault model: {fault_model!r}")
    return handler(circuit, test_vec)