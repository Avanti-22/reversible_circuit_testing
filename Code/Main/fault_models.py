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
#  FIX : was appending literal 1 instead of computed output
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

        faulty_outputs.append(current)   # BUG FIX: was append(1)

    return faulty_outputs


# ═══════════════════════════════════════════════════════════════════════════════
#  MMGF
#  DP  : window [start, start+w) skipped → start from prefix[start]
#        apply only suffix gates from start+window_size onward
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

            total_possible = sum(
                total_gates - w + 1 for w in range(1, max_missing + 1)
            )
            if len(seen) >= total_possible:
                break

    return faulty_outputs


# ═══════════════════════════════════════════════════════════════════════════════
#  PMGF
#  DP  : prefix[gate_index] shared by ALL missing-mask variants of gate i
#        previously each simulate_PMGF_circuit() call re-walked gates 0..i-1
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

                # ── DP: start from state before gate_index ────────────────
                # All mask variants of this gate share the same prefix[gate_index]
                # ── DP: start from state before gate_index ────────────────
                # All mask variants of this gate share the same prefix[gate_index]
                faulty_output = simulate_PMGF_circuit(
                    circuit,
                    prefix[gate_index],
                    faulty_gate_index=gate_index,
                    missing_control_bits_mask=missing_mask,
                    start_gate=gate_index          # ← skip prefix gates
                )
                faulty_outputs.append(faulty_output)

    return faulty_outputs


# ═══════════════════════════════════════════════════════════════════════════════
#  SAF
#  DP  : prefix[gate_index] = state before injection point
#        inject stuck-at, then simulate gate i onwards (suffix only)
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

            # ── DP: start from state before gate_index ────────────────────
            faulty_output = simulate_SAF_circuit(
                circuit,
                prefix[gate_index],
                faulty_gate_index=gate_index,
                faulty_wire_bit=wire_bit,
                stuck_at_value=stuck_value,
                start_gate=gate_index          # ← NEW: skip prefix gates
            )
            faulty_outputs.append(faulty_output)
            
    # Filter structurally undetectable faults (output == fault-free output)
    fault_free_output = simulate_fault_free(circuit, input_bits)
    faulty_outputs = [o for o in faulty_outputs if o != fault_free_output]

    return faulty_outputs

def faulty_op_for_SAF_combined(circuit, input_bits, prefix=None):
    """
    Generate ALL SAF faulty outputs for BOTH SA-0 and SA-1 combined.

    - Prefix table is built once and shared across both SA-0 and SA-1 calls.
    - Faults that produce the same output as fault-free are filtered out
      (they are structurally undetectable and inflate cumulatedFaults otherwise).
    """
    if prefix is None:
        prefix = build_prefix_table(circuit, input_bits)

    fault_free_output = simulate_fault_free(circuit, input_bits)

    outputs_sa0 = faulty_op_for_SAF(circuit, input_bits, "SA-0", prefix=prefix)
    outputs_sa1 = faulty_op_for_SAF(circuit, input_bits, "SA-1", prefix=prefix)

    all_outputs = outputs_sa0 + outputs_sa1

    # Remove faults that are identical to fault-free output — they are
    # undetectable regardless of test vector and only inflate fault count.
    detectable_outputs = [o for o in all_outputs if o != fault_free_output]

    return detectable_outputs

# ═══════════════════════════════════════════════════════════════════════════════
#  RGF
#  DP  : prefix[gate_index] → apply gate repeatedly → apply suffix
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

        # ── DP: start from state before gate_index ────────────────────────
        faulty_output = simulate_RGF_circuit(
            circuit,
            prefix[gate_index],
            faulty_gate_index=gate_index,
            repeat_mode=mode,
            start_gate=gate_index          # ← skip prefix gates
        )
        faulty_outputs.append(faulty_output)

    return faulty_outputs


# ═══════════════════════════════════════════════════════════════════════════════
#  GAF
#  DP  : insertion after gate k → start from prefix[k+1]
#        insertion before gate 0 → start from prefix[0]  (= input vector)
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


# def faulty_op_for_GAF(circuit, input_bits, prefix=None):
#     """
#     Generate outputs for all GAF faults.
#     Randomly picks one gate per insertion position (original behaviour).
#     """

#     faulty_outputs = []
#     total_gates = circuit["No of Gates"]
#     num_lines = circuit["No of Lines"]

#     if prefix is None:
#         prefix = build_prefix_table(circuit, input_bits)

#     gate_library = build_gaf_gate_library(num_lines)

#     # insertion_index = -1 → before gate 0   →  use prefix[0]
#     # insertion_index =  k → after  gate k   →  use prefix[k+1]
#     for insertion_index in range(-1, total_gates):

#         extra_gate = random.choice(gate_library)

#         # ── DP: state after gates 0..insertion_index = prefix[insertion_index+1]
#         faulty_output = simulate_GAF_circuit(
#             circuit,
#             prefix[insertion_index + 1],         # was: input_bits
#             insertion_index,
#             extra_gate
#         )
#         faulty_outputs.append(faulty_output)

#     return faulty_outputs

def faulty_op_for_GAF(circuit, input_bits, prefix=None):
    """
    Generate outputs for all GAF faults — fully deterministic.

    Strategy: for each insertion position, try ALL gates from the library
    and keep only UNIQUE faulty outputs. This avoids:
      - random.choice non-determinism
      - fault count varying between vectors (breaks fault matrix shape)
      - cumulatedFaults inflation from duplicate outputs
    
    Insertion positions: -1 (before gate 0) up to total_gates - 1 (after last gate)
    Total positions: total_gates + 1
    """

    faulty_outputs = []
    seen = set()

    total_gates = circuit["No of Gates"]
    num_lines   = circuit["No of Lines"]
    gate_library = build_gaf_gate_library(num_lines)

    if prefix is None:
        prefix = build_prefix_table(circuit, input_bits)

    fault_free_output = simulate_fault_free(circuit, input_bits)

    for insertion_index in range(-1, total_gates):

        for extra_gate in gate_library:

            faulty_output = simulate_GAF_circuit(
                circuit,
                input_bits,
                insertion_index,
                extra_gate
            )

            # Only keep unique, detectable outputs
            if faulty_output != fault_free_output and faulty_output not in seen:
                seen.add(faulty_output)
                faulty_outputs.append(faulty_output)

    return faulty_outputs


# ═══════════════════════════════════════════════════════════════════════════════
#  Utility (unchanged)
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

            # ── DP: all extra-wire variants of gate i share prefix[gate_index]
            faulty_output = simulate_CAF_circuit(
                circuit,
                prefix[gate_index],
                faulty_gate_index=gate_index,
                extra_control_bit=extra_control_bit,
                start_gate=gate_index          # ← skip prefix gates
            )
            faulty_outputs.append(faulty_output)

    return faulty_outputs


# ═══════════════════════════════════════════════════════════════════════════════
#  BF
#  DP  : prefix[gate_index] = state before bridging injection point
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

            # ── DP: start from state before gate_index ────────────────────

            # AND-bridging
            faulty_output = simulate_BF_circuit(
                circuit,
                prefix[gate_index],
                faulty_gate_index=gate_index,
                wire_bit_1=wire_bit_1,
                wire_bit_2=wire_bit_2,
                mode=0,
                start_gate=gate_index          # ← skip prefix gates
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
                start_gate=gate_index          # ← skip prefix gates
            )
            faulty_outputs.append(faulty_output)

    return faulty_outputs


# ═══════════════════════════════════════════════════════════════════════════════
#  BF / MBF helpers (unchanged)
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

                # ── DP: all fault-subset variants of gate i share prefix[gate_index]
                faulty_output = simulate_MBF_circuit(
                    circuit,
                    prefix[gate_index],
                    faulty_gate_index=gate_index,
                    fault_list=fault_subset,
                    start_gate=gate_index          # ← skip prefix gates
                )
                faulty_outputs.append(faulty_output)

    return faulty_outputs


# ═══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
#  Builds the DP prefix table ONCE for this test vector.
#  Passes it to every fault model — none of them rebuild it.
#
#  Cost before DP : O(F × N)        — each fault re-walks all N gates
#  Cost after  DP : O(N + F × N/2)  — table built once, each fault walks suffix
#                 ≈ 2× fewer gate applications overall
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