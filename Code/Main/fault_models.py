from simulator import *
import itertools
import random
from itertools import combinations


# ═══════════════════════════════════════════════════════════════════════════════
#  DP PREFIX TABLE
#  Built ONCE per test vector in get_all_faulty_outputs().
#  Passed to every faulty_op_for_X so none of them re-simulate
#  gates 0..fault_index-1 from scratch.
#
#  State      :  prefix[i]   = circuit state just BEFORE gate i
#  Recurrence :  prefix[i+1] = apply_gate(prefix[i], gate[i])
#  Base case  :  prefix[0]   = input_vector
# ═══════════════════════════════════════════════════════════════════════════════

def build_prefix_table(circuit, input_vector):
    compiled_gates = circuit["Compiled Rep"]
    n = len(compiled_gates)

    prefix = [0] * (n + 1)
    prefix[0] = input_vector                          # base case

    for i, gate in enumerate(compiled_gates):
        prefix[i + 1] = apply_gate(prefix[i], gate)  # recurrence

    return prefix


# ═══════════════════════════════════════════════════════════════════════════════
#  SMGF
#  DP  : prefix[i] = state before gate i → only suffix needs simulation
# ═══════════════════════════════════════════════════════════════════════════════

def faulty_op_for_SMGF(circuit, input_state, prefix=None):

    compiled_gates = circuit["Compiled Rep"]
    n = len(compiled_gates)

    if prefix is None:
        prefix = build_prefix_table(circuit, input_state)

    faulty_outputs = []

    for i in range(n):

        current = prefix[i]           # DP: state before gate i (free)

        for j in range(i + 1, n):    # apply suffix only — gate i is missing
            current = apply_gate(current, compiled_gates[j])

        faulty_outputs.append(current)

    return faulty_outputs


# ═══════════════════════════════════════════════════════════════════════════════
#  MMGF
#  DP  : window [start, start+w) skipped → start from prefix[start]
#        apply only suffix gates from start+window_size onward
#
#  FIX : total_possible moved outside the while loop (was recomputed every iter)
# ═══════════════════════════════════════════════════════════════════════════════

def faulty_op_for_MMGF(circuit, input_bits, max_missing=2,
                        sample_limit=10000, prefix=None):
    """
    Generate outputs for MMGF faults — consecutive gates only.

    For small circuits (total_gates < 50):
        Exhaustively enumerates all consecutive windows of size 1..max_missing.
    For large circuits (total_gates >= 50):
        Randomly samples up to sample_limit consecutive windows.
    """

    compiled_gates = circuit["Compiled Rep"]
    total_gates = len(compiled_gates)

    if prefix is None:
        prefix = build_prefix_table(circuit, input_bits)

    max_missing = min(max_missing, total_gates)
    faulty_outputs = []

    # ── Small circuit: exhaustive consecutive windows ─────────────────────────
    if total_gates < 50:

        for window_size in range(1, max_missing + 1):

            for start in range(total_gates - window_size + 1):

                current = prefix[start]   # DP: skip prefix re-simulation

                # skip window entirely; apply only suffix
                for j in range(start + window_size, total_gates):
                    current = apply_gate(current, compiled_gates[j])

                faulty_outputs.append(current)

    # ── Large circuit: sampled consecutive windows ────────────────────────────
    else:

        seen = set()

        # FIX: compute total_possible ONCE outside the loop (it's a constant)
        total_possible = sum(
            total_gates - w + 1 for w in range(1, max_missing + 1)
        )

        while len(faulty_outputs) < sample_limit:

            window_size = random.randint(1, max_missing)
            max_start = total_gates - window_size
            if max_start < 0:
                continue

            start = random.randint(0, max_start)
            window_key = (start, window_size)
            if window_key in seen:
                continue
            seen.add(window_key)

            current = prefix[start]   # DP: skip prefix re-simulation

            for j in range(start + window_size, total_gates):
                current = apply_gate(current, compiled_gates[j])

            faulty_outputs.append(current)

            if len(seen) >= total_possible:
                break

    return faulty_outputs


# ═══════════════════════════════════════════════════════════════════════════════
#  PMGF
#  DP  : prefix[gate_index] shared by ALL missing-mask variants of gate i
#
#  FIX : filter structurally undetectable faults (output == fault-free output)
# ═══════════════════════════════════════════════════════════════════════════════

def faulty_op_for_PMGF(circuit, input_bits, prefix=None):

    faulty_outputs = []
    compiled_gates = circuit["Compiled Rep"]
    n = len(compiled_gates)

    if prefix is None:
        prefix = build_prefix_table(circuit, input_bits)

    for gate_index, gate in enumerate(compiled_gates):

        gate_type = gate[0]

        if gate_type == "TOFFOLI":
            control_bits = gate[1]
        elif gate_type == "FREDKIN":
            control_bits = gate[1]
        elif gate_type == "PERES":
            control_bits = gate[1]
        else:
            continue

        # Decompose control mask into individual bits
        control_bit_list = []
        temp = control_bits
        bit_position = 0
        while temp:
            if temp & 1:
                control_bit_list.append(1 << bit_position)
            temp >>= 1
            bit_position += 1

        total_controls = len(control_bit_list)

        for num_missing in range(1, total_controls + 1):

            for subset in combinations(control_bit_list, num_missing):

                missing_mask = 0
                for bit in subset:
                    missing_mask |= bit

                # DP: start from state before gate_index
                faulty_output = simulate_PMGF_circuit(
                    circuit,
                    prefix[gate_index],
                    faulty_gate_index=gate_index,
                    missing_control_bits_mask=missing_mask,
                    start_gate=gate_index
                )
                faulty_outputs.append(faulty_output)

    # FIX: filter structurally undetectable faults
    fault_free_output = simulate_fault_free(circuit, input_bits)
    faulty_outputs = [o for o in faulty_outputs if o != fault_free_output]

    return faulty_outputs


# ═══════════════════════════════════════════════════════════════════════════════
#  SAF
#  DP  : prefix[gate_index] = state before injection point
#
#  FIX : faulty_op_for_SAF_combined deduplicates outputs across SA-0 and SA-1
# ═══════════════════════════════════════════════════════════════════════════════

def faulty_op_for_SAF(circuit, input_bits, fault_model, prefix=None):
    """
    Generate all SAF faulty outputs.
    fault_model : "SA-0" or "SA-1"
    """

    faulty_outputs = []
    compiled_gates = circuit["Compiled Rep"]

    if prefix is None:
        prefix = build_prefix_table(circuit, input_bits)

    stuck_value = 0 if fault_model == "SA-0" else 1

    for gate_index, gate in enumerate(compiled_gates):

        gate_type = gate[0]
        bits_in_gate = set()

        if gate_type == "TOFFOLI":
            bits_in_gate |= extract_individual_bits(gate[1])
            bits_in_gate.add(gate[2])
        elif gate_type == "FREDKIN":
            bits_in_gate |= extract_individual_bits(gate[1])
            bits_in_gate.add(gate[2])
            bits_in_gate.add(gate[3])
        elif gate_type == "PERES":
            bits_in_gate |= extract_individual_bits(gate[1])
            bits_in_gate |= extract_individual_bits(gate[2])
            bits_in_gate.add(gate[3])

        for wire_bit in bits_in_gate:

            # DP: start from state before gate_index
            faulty_output = simulate_SAF_circuit(
                circuit,
                prefix[gate_index],
                faulty_gate_index=gate_index,
                faulty_wire_bit=wire_bit,
                stuck_at_value=stuck_value,
                start_gate=gate_index
            )
            faulty_outputs.append(faulty_output)

    # Filter structurally undetectable faults
    fault_free_output = simulate_fault_free(circuit, input_bits)
    faulty_outputs = [o for o in faulty_outputs if o != fault_free_output]

    return faulty_outputs


def faulty_op_for_SAF_combined(circuit, input_bits, prefix=None):
    """
    Generate ALL SAF faulty outputs for BOTH SA-0 and SA-1 combined.

    - Prefix table is built once and shared across both SA-0 and SA-1 calls.
    - FIX: deduplicates outputs across SA-0 and SA-1 — the same faulty output
      reachable by both models was previously counted twice, inflating
      cumulatedFaults.
    """
    if prefix is None:
        prefix = build_prefix_table(circuit, input_bits)

    fault_free_output = simulate_fault_free(circuit, input_bits)

    outputs_sa0 = faulty_op_for_SAF(circuit, input_bits, "SA-0", prefix=prefix)
    outputs_sa1 = faulty_op_for_SAF(circuit, input_bits, "SA-1", prefix=prefix)

    # FIX: deduplicate across SA-0 and SA-1 (not just per-model)
    seen = set()
    detectable_outputs = []
    for o in outputs_sa0 + outputs_sa1:
        if o != fault_free_output and o not in seen:
            seen.add(o)
            detectable_outputs.append(o)

    return detectable_outputs


# ═══════════════════════════════════════════════════════════════════════════════
#  RGF
#  DP  : prefix[gate_index] → apply gate repeatedly → apply suffix
#
#  FIX : filter structurally undetectable faults (output == fault-free output)
# ═══════════════════════════════════════════════════════════════════════════════

def faulty_op_for_RGF(circuit, input_bits, mode="Odd", prefix=None):
    """
    Generate RGF faulty outputs.
    mode : "Odd" or "Even"
    """

    faulty_outputs = []
    total_gates = circuit["No of Gates"]

    if prefix is None:
        prefix = build_prefix_table(circuit, input_bits)

    for gate_index in range(total_gates):

        # DP: start from state before gate_index
        faulty_output = simulate_RGF_circuit(
            circuit,
            prefix[gate_index],
            faulty_gate_index=gate_index,
            repeat_mode=mode,
            start_gate=gate_index
        )
        faulty_outputs.append(faulty_output)

    # FIX: filter structurally undetectable faults
    fault_free_output = simulate_fault_free(circuit, input_bits)
    faulty_outputs = [o for o in faulty_outputs if o != fault_free_output]

    return faulty_outputs


# ═══════════════════════════════════════════════════════════════════════════════
#  GAF
#  FIX : fully deterministic (no random.choice); uses prefix table +
#        per-insertion suffix memoization for major speedup.
#
#  For insertion at position k:
#    state_before_extra = prefix[k+1]           O(1) lookup
#    apply extra gate   → mid_state             O(1)
#    apply suffix[k+1..N-1] to mid_state        O(N-k), memoized per mid_state
# ═══════════════════════════════════════════════════════════════════════════════

def build_gaf_gate_library(num_lines):

    gate_library = []

    for wire in range(num_lines):
        gate_library.append(("TOFFOLI", 0, 1 << wire))

    for control in range(num_lines):
        for target in range(num_lines):
            if control != target:
                gate_library.append(("TOFFOLI", 1 << control, 1 << target))

    for i in range(num_lines):
        for j in range(i + 1, num_lines):
            gate_library.append(("FREDKIN", 0, 1 << i, 1 << j))

    return gate_library


def faulty_op_for_GAF(circuit, input_bits, prefix=None):
    """
    Generate outputs for all GAF faults — fully deterministic with suffix memoization.

    For each insertion position k, all gates in the library that produce the
    same mid_state share a single suffix simulation (memoized per position).

    Complexity:
        Before : O(positions × lib_size × N)   — full re-walk every call
        After  : O(N) prefix + O(positions × lib_size) extra-gate applications
                 + O(unique_mid_states × avg_suffix_len) suffix simulations
    """

    faulty_outputs = []
    seen_outputs   = set()

    total_gates    = circuit["No of Gates"]
    num_lines      = circuit["No of Lines"]
    compiled_gates = circuit["Compiled Rep"]
    gate_library   = build_gaf_gate_library(num_lines)

    if prefix is None:
        prefix = build_prefix_table(circuit, input_bits)

    fault_free_output = simulate_fault_free(circuit, input_bits)

    # suffix_cache[insertion_index][mid_state] → final_output
    suffix_cache = {}

    def apply_suffix(insertion_index, mid_state):
        cache = suffix_cache.setdefault(insertion_index, {})
        if mid_state in cache:
            return cache[mid_state]
        current = mid_state
        for j in range(insertion_index + 1, total_gates):
            current = apply_gate(current, compiled_gates[j])
        cache[mid_state] = current
        return current

    for insertion_index in range(-1, total_gates):

        state_before_extra = prefix[insertion_index + 1]  # O(1)

        for extra_gate in gate_library:

            mid_state     = apply_gate(state_before_extra, extra_gate)   # O(1)
            faulty_output = apply_suffix(insertion_index, mid_state)     # memoized

            if faulty_output != fault_free_output and faulty_output not in seen_outputs:
                seen_outputs.add(faulty_output)
                faulty_outputs.append(faulty_output)

    return faulty_outputs


# ═══════════════════════════════════════════════════════════════════════════════
#  Utility
# ═══════════════════════════════════════════════════════════════════════════════

def extract_individual_bits(bit_mask):

    bits = set()
    position = 0

    while bit_mask:
        if bit_mask & 1:
            bits.add(1 << position)
        bit_mask >>= 1
        position += 1

    return bits


# ═══════════════════════════════════════════════════════════════════════════════
#  CAF
#  DP  : prefix[gate_index] shared by ALL extra-wire variants of gate i
#
#  FIX : filter structurally undetectable faults (output == fault-free output)
# ═══════════════════════════════════════════════════════════════════════════════

def faulty_op_for_CAF(circuit, input_bits, prefix=None):

    faulty_outputs = []
    total_gates = circuit["No of Gates"]
    num_lines = circuit["No of Lines"]
    compiled_gates = circuit["Compiled Rep"]

    if prefix is None:
        prefix = build_prefix_table(circuit, input_bits)

    for gate_index, gate in enumerate(compiled_gates):

        gate_type = gate[0]
        bits_in_gate = set()

        if gate_type == "TOFFOLI":
            bits_in_gate |= extract_individual_bits(gate[1])
            bits_in_gate.add(gate[2])
        elif gate_type == "FREDKIN":
            bits_in_gate |= extract_individual_bits(gate[1])
            bits_in_gate.add(gate[2])
            bits_in_gate.add(gate[3])
        elif gate_type == "PERES":
            bits_in_gate |= extract_individual_bits(gate[1])
            bits_in_gate |= extract_individual_bits(gate[2])
            bits_in_gate.add(gate[3])

        for wire_position in range(num_lines):

            extra_control_bit = 1 << wire_position
            if extra_control_bit in bits_in_gate:
                continue

            # DP: all extra-wire variants of gate i share prefix[gate_index]
            faulty_output = simulate_CAF_circuit(
                circuit,
                prefix[gate_index],
                faulty_gate_index=gate_index,
                extra_control_bit=extra_control_bit,
                start_gate=gate_index
            )
            faulty_outputs.append(faulty_output)

    # FIX: filter structurally undetectable faults
    fault_free_output = simulate_fault_free(circuit, input_bits)
    faulty_outputs = [o for o in faulty_outputs if o != fault_free_output]

    return faulty_outputs


# ═══════════════════════════════════════════════════════════════════════════════
#  BF
#  DP  : prefix[gate_index] = state before bridging injection point
#
#  FIX : filter structurally undetectable faults (output == fault-free output)
# ═══════════════════════════════════════════════════════════════════════════════

def faulty_op_for_BF(circuit, input_bits, prefix=None):
    """
    Bridging Fault simulation — adjacent wires only.
    """

    faulty_outputs = []
    total_gates = circuit["No of Gates"]
    num_lines = circuit["No of Lines"]

    if prefix is None:
        prefix = build_prefix_table(circuit, input_bits)

    for gate_index in range(total_gates):

        for wire1 in range(num_lines - 1):

            wire2 = wire1 + 1
            wire_bit_1 = 1 << wire1
            wire_bit_2 = 1 << wire2

            # AND-bridging
            faulty_output = simulate_BF_circuit(
                circuit,
                prefix[gate_index],
                faulty_gate_index=gate_index,
                wire_bit_1=wire_bit_1,
                wire_bit_2=wire_bit_2,
                mode=0,
                start_gate=gate_index
            )
            faulty_outputs.append(faulty_output)

            # OR-bridging
            faulty_output = simulate_BF_circuit(
                circuit,
                prefix[gate_index],
                faulty_gate_index=gate_index,
                wire_bit_1=wire_bit_1,
                wire_bit_2=wire_bit_2,
                mode=1,
                start_gate=gate_index
            )
            faulty_outputs.append(faulty_output)

    # FIX: filter structurally undetectable faults
    fault_free_output = simulate_fault_free(circuit, input_bits)
    faulty_outputs = [o for o in faulty_outputs if o != fault_free_output]

    return faulty_outputs


# ═══════════════════════════════════════════════════════════════════════════════
#  BF / MBF helpers
# ═══════════════════════════════════════════════════════════════════════════════

def build_single_bridging_faults(num_lines):
    """
    Build list of single bridging faults — adjacent wires only.
    Each fault: (wire_bit_1, wire_bit_2, mode)   mode 0=AND  mode 1=OR
    Count: (num_lines - 1) * 2 faults
    """
    single_faults = []
    for i in range(num_lines - 1):
        wire_bit_1 = 1 << i
        wire_bit_2 = 1 << (i + 1)
        single_faults.append((wire_bit_1, wire_bit_2, 0))
        single_faults.append((wire_bit_1, wire_bit_2, 1))
    return single_faults


def are_non_overlapping(fault_a, fault_b):
    wires_a = {fault_a[0], fault_a[1]}
    wires_b = {fault_b[0], fault_b[1]}
    return wires_a.isdisjoint(wires_b)


def filter_MBF_combination(fault_subset, filter_mixed_mode, filter_overlapping):
    if filter_mixed_mode:
        modes = set(f[2] for f in fault_subset)
        if 0 in modes and 1 in modes:
            return False
    if filter_overlapping and len(fault_subset) > 1:
        for fa, fb in itertools.combinations(fault_subset, 2):
            if not are_non_overlapping(fa, fb):
                return False
    return True


# ═══════════════════════════════════════════════════════════════════════════════
#  MBF
#  DP  : prefix[gate_index] shared by ALL fault-subset variants of gate i
#
#  FIX : filter structurally undetectable faults (output == fault-free output)
# ═══════════════════════════════════════════════════════════════════════════════

def faulty_op_for_MBF(circuit,
                      input_bits,
                      max_faults_per_gate=2,
                      start_from_single=False,
                      filter_mixed_mode=True,
                      filter_overlapping=True,
                      prefix=None):
    """
    Generate MBF faulty outputs — adjacent wires only.

    max_faults_per_gate : max simultaneous bridging faults per gate. Default 2.
    start_from_single   : False → set_size starts at 2 (BF run separately).
                          True  → set_size starts at 1 (MBF subsumes BF).
    filter_mixed_mode   : discard combos mixing AND and OR modes.
    filter_overlapping  : discard combos where any two faults share a wire.
    """

    faulty_outputs = []
    total_gates = circuit["No of Gates"]
    num_lines = circuit["No of Lines"]

    if prefix is None:
        prefix = build_prefix_table(circuit, input_bits)

    single_faults = build_single_bridging_faults(num_lines)
    if not single_faults:
        return faulty_outputs

    max_faults = min(max_faults_per_gate, len(single_faults)) \
        if max_faults_per_gate is not None else len(single_faults)
    min_set_size = 1 if start_from_single else 2

    for gate_index in range(total_gates):

        for set_size in range(min_set_size, max_faults + 1):

            for fault_subset in itertools.combinations(single_faults, set_size):

                if not filter_MBF_combination(
                    fault_subset, filter_mixed_mode, filter_overlapping
                ):
                    continue

                # DP: all fault-subset variants of gate i share prefix[gate_index]
                faulty_output = simulate_MBF_circuit(
                    circuit,
                    prefix[gate_index],
                    faulty_gate_index=gate_index,
                    fault_list=fault_subset,
                    start_gate=gate_index
                )
                faulty_outputs.append(faulty_output)

    # FIX: filter structurally undetectable faults
    fault_free_output = simulate_fault_free(circuit, input_bits)
    faulty_outputs = [o for o in faulty_outputs if o != fault_free_output]

    return faulty_outputs


# ═══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
#  Builds the DP prefix table ONCE for this test vector.
#  Passes it to every fault model — none of them rebuild it.
# ═══════════════════════════════════════════════════════════════════════════════

def get_all_faulty_outputs(circuit, testVec, fault_model):

    # Build prefix table ONCE for this test vector
    prefix = build_prefix_table(circuit, testVec)

    if fault_model in ["SA-0", "SA-1"]:
        return faulty_op_for_SAF(circuit, testVec, fault_model, prefix=prefix)

    elif fault_model == "SAF":
        return faulty_op_for_SAF_combined(circuit, testVec, prefix=prefix)

    elif fault_model == "SMGF":
        return faulty_op_for_SMGF(circuit, testVec, prefix=prefix)

    elif fault_model == "PMGF":
        return faulty_op_for_PMGF(circuit, testVec, prefix=prefix)

    elif fault_model == "MMGF":
        return faulty_op_for_MMGF(circuit, testVec, max_missing=2, prefix=prefix)

    elif fault_model == "RGF":
        return faulty_op_for_RGF(circuit, testVec, "Odd", prefix=prefix)

    elif fault_model == "GAF":
        return faulty_op_for_GAF(circuit, testVec, prefix=prefix)

    elif fault_model == "CAF":
        return faulty_op_for_CAF(circuit, testVec, prefix=prefix)

    elif fault_model == "BF":
        return faulty_op_for_BF(circuit, testVec, prefix=prefix)

    elif fault_model == "MBF":
        return faulty_op_for_MBF(circuit, testVec,
                                 max_faults_per_gate=2,
                                 start_from_single=False,
                                 filter_mixed_mode=True,
                                 filter_overlapping=True,
                                 prefix=prefix)