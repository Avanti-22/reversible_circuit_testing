from simulator import *
import itertools
from itertools import combinations

# def faulty_op_for_SMGF(circuit, input_state):
#     """
#     Optimized SMGF using compiled circuit and integer state.
#     Compatible with your optimized fault-free simulator.
#     """

#     compiled_gates = circuit["Compiled Rep"]
#     n = len(compiled_gates)

#     # ---------------------------------
#     # 1. Compute prefix states once
#     # ---------------------------------
#     states = [input_state]
#     current = input_state

#     for gate in compiled_gates:
#         current = apply_gate(current, gate)
#         states.append(current)

#     # states[i] = state BEFORE gate i

#     faulty_outputs = []

#     # ---------------------------------
#     # 2. For each missing gate
#     # ---------------------------------
#     for i in range(n):

#         current = states[i]

#         # apply only suffix
#         for j in range(i + 1, n):
#             current = apply_gate(current, compiled_gates[j])

#         faulty_outputs.append(current)

#     return faulty_outputs

def faulty_op_for_SMGF(circuit, input_state):
    compiled_gates = circuit["Compiled Rep"]
    n = len(compiled_gates)

    # Forward pass: prefix[i] = state just before gate i
    prefix = [input_state] * (n + 1)
    for i, gate in enumerate(compiled_gates):
        prefix[i + 1] = apply_gate(prefix[i], gate)

    # Backward pass: suffix[i] = state after applying gates i..n-1
    # We store what the output would be if we START from some state at position i
    # For missing gate i: output = apply gates [i+1..n-1] to prefix[i]
    # = suffix_from[i+1] applied to prefix[i]
    # This requires per-state suffix which can't be precomputed globally.
    # BUT: we can use the numpy approach — compute all at once:

    faulty_outputs = []
    fault_count = 0
    for i in range(n):
        current = prefix[i]           # state before gate i
        for j in range(i + 1, n):    # skip gate i, apply rest
            current = apply_gate(current, compiled_gates[j])
        # faulty_outputs.append(1)
        fault_count += 1

    return fault_count

from itertools import combinations


def faulty_op_for_MMGF(circuit, input_bits, max_missing=2, sample_limit=10000):
    """
    Generate outputs for all MMGF fault combinations.
    Capped at max_missing simultaneously missing gates to avoid 2^n blowup.
    """

    total_gates = circuit["No of Gates"]
    faulty_outputs = []

    max_missing = min(max_missing, total_gates - 1)
    fault_count = 0
    if total_gates < 50:
        for num_missing in range(1, max_missing + 1):

            for faulty_subset in combinations(range(total_gates), num_missing):

                # faulty_set = set(faulty_subset)

                # faulty_output = simulate_MMGF_circuit(
                #     circuit,
                #     input_bits,
                #     faulty_set
                # )
                fault_count += 1
                # faulty_outputs.append(1)

        return fault_count
    
    for _ in range(sample_limit):
        num_to_drop = random.randint(1, max_missing)
        faulty_subset = random.sample(range(total_gates), num_to_drop)
        # faulty_set = set(faulty_subset)

        # faulty_output = simulate_MMGF_circuit(
        #     circuit,
        #     input_bits,
        #     faulty_set
        # )
        fault_count += 1
        # faulty_outputs.append(1)
    return fault_count



def faulty_op_for_PMGF(circuit, input_bits):

    faulty_outputs = []
    compiled_gates = circuit["Compiled Rep"]

    fault_count = 0
    for gate_index, gate in enumerate(compiled_gates):

        gate_type = gate[0]

        # Extract original control bits
        if gate_type == "TOFFOLI":
            control_bits = gate[1]

        elif gate_type == "FREDKIN":
            control_bits = gate[1]

        elif gate_type == "PERES":
            control_bits = gate[1]

        else:
            continue

        # Convert control bitmask into list of individual bits
        control_bit_list = []
        temp = control_bits
        bit_position = 0

        while temp:
            if temp & 1:
                control_bit_list.append(1 << bit_position)
            temp >>= 1
            bit_position += 1

        total_controls = len(control_bit_list)

        # Generate all non-empty subsets
        for num_missing in range(1, total_controls + 1):

            for subset in combinations(control_bit_list, num_missing):

                missing_mask = 0
                for bit in subset:
                    missing_mask |= bit

                # faulty_output = simulate_PMGF_circuit(
                #     circuit,
                #     input_bits,
                #     faulty_gate_index=gate_index,
                #     missing_control_bits_mask=missing_mask
                # )

                fault_count += 1    

    return fault_count


def faulty_op_for_SAF(circuit, input_bits, fault_model):
    """
    Generate all SAF faulty outputs.
    fault_model : "SA-0" or "SA-1"
    """

    faulty_outputs = []
    fault_count = 0
    compiled_gates = circuit["Compiled Rep"]

    stuck_value = 0 if fault_model == "SA-0" else 1

    for gate_index, gate in enumerate(compiled_gates):

        gate_type = gate[0]

        # Collect all bits involved in this gate
        bits_in_gate = set()

        if gate_type == "TOFFOLI":
            control_bits = gate[1]
            target_bit = gate[2]
            bits_in_gate |= extract_individual_bits(control_bits)
            bits_in_gate.add(target_bit)

        elif gate_type == "FREDKIN":
            control_bits = gate[1]
            swap_bit_1 = gate[2]
            swap_bit_2 = gate[3]
            bits_in_gate |= extract_individual_bits(control_bits)
            bits_in_gate.add(swap_bit_1)
            bits_in_gate.add(swap_bit_2)

        elif gate_type == "PERES":
            control_bits = gate[1]
            xor_bit_mask = gate[2]
            target_bit = gate[3]
            bits_in_gate |= extract_individual_bits(control_bits)
            bits_in_gate |= extract_individual_bits(xor_bit_mask)
            bits_in_gate.add(target_bit)

        # Generate SAF for each bit
        for wire_bit in bits_in_gate:
            
            # faulty_output = simulate_SAF_circuit(
            #     circuit,
            #     input_bits,
            #     faulty_gate_index=gate_index,
            #     faulty_wire_bit=wire_bit,
            #     stuck_at_value=stuck_value
            # )

            # faulty_outputs.append(1)
            fault_count += 1
    return fault_count

def faulty_op_for_RGF(circuit, input_bits, mode="Odd"):
    """
    Generate RGF faulty outputs.

    mode : "Odd" or "Even"
    """

    faulty_outputs = []
    fault_count = 0
    total_gates = circuit["No of Gates"]

    for gate_index in range(total_gates):

        # faulty_output = simulate_RGF_circuit(
        #     circuit,
        #     input_bits,
        #     faulty_gate_index=gate_index,
        #     repeat_mode=mode
        # )

        # faulty_outputs.append(1)
        fault_count += 1

    return fault_count

def build_gaf_gate_library(num_lines):

    gate_library = []

    # NOT gates
    for wire in range(num_lines):
        target_bit = 1 << wire
        gate_library.append(("TOFFOLI", 0, target_bit))

    # Single-control CNOT gates
    for control in range(num_lines):
        for target in range(num_lines):
            if control != target:
                control_bit = 1 << control
                target_bit = 1 << target
                gate_library.append(("TOFFOLI", control_bit, target_bit))

    # SWAP gates
    for i in range(num_lines):
        for j in range(i + 1, num_lines):
            bit1 = 1 << i
            bit2 = 1 << j
            gate_library.append(("FREDKIN", 0, bit1, bit2))

    return gate_library


def faulty_op_for_GAF(circuit, input_bits):
    """
    Generate outputs for all GAF faults.
    Exhaustively iterates over all insertion positions and all possible gates
    from the library — no randomness.
    """

    faulty_outputs = []
    fault_count = 0
    total_gates = circuit["No of Gates"]
    num_lines = circuit["No of Lines"]

    gate_library = build_gaf_gate_library(num_lines)

    # insertion_index = -1 means before gate 0
    # insertion_index =  k means after gate k
    # so valid range is -1 to total_gates - 1  →  n+1 positions total
    for insertion_index in range(-1, total_gates):

        # for extra_gate in gate_library:

        #     # faulty_output = simulate_GAF_circuit(
        #     #     circuit,
        #     #     input_bits,
        #     #     insertion_index,
        #     #     extra_gate
        #     # )
        #     fault_count += 1
        #     # faulty_outputs.append(1)
        # Randomly choose one gate
        extra_gate = random.choice(gate_library)

        # faulty_output = simulate_GAF_circuit(
        #     circuit,
        #     input_bits,
        #     insertion_index,
        #     extra_gate
        # )

        # faulty_outputs.append(faulty_output)
        fault_count += 1
        

    return fault_count



def extract_individual_bits(bit_mask):

    bits = set()
    position = 0

    while bit_mask:
        if bit_mask & 1:
            bits.add(1 << position)
        bit_mask >>= 1
        position += 1

    return bits


def faulty_op_for_CAF(circuit, input_bits):

    faulty_outputs = []
    fault_count = 0
    total_gates = circuit["No of Gates"]
    num_lines = circuit["No of Lines"]
    compiled_gates = circuit["Compiled Rep"]

    for gate_index, gate in enumerate(compiled_gates):

        gate_type = gate[0]

        # Collect all bits already used in this gate
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

        # Try adding every other wire as extra control
        for wire_position in range(num_lines):

            extra_control_bit = 1 << wire_position

            if extra_control_bit in bits_in_gate:
                continue

            # faulty_output = simulate_CAF_circuit(
            #     circuit,
            #     input_bits,
            #     faulty_gate_index=gate_index,
            #     extra_control_bit=extra_control_bit
            # )

            fault_count += 1

    return fault_count


def faulty_op_for_BF(circuit, input_bits):

    faulty_outputs = []
    fault_count = 0
    total_gates = circuit["No of Gates"]
    num_lines = circuit["No of Lines"]

    for gate_index in range(total_gates):

        for wire1 in range(num_lines):
            for wire2 in range(wire1 + 1, num_lines):

                wire_bit_1 = 1 << wire1
                wire_bit_2 = 1 << wire2

                # AND-wired
                # faulty_output = simulate_BF_circuit(
                #     circuit,
                #     input_bits,
                #     faulty_gate_index=gate_index,
                #     wire_bit_1=wire_bit_1,
                #     wire_bit_2=wire_bit_2,
                #     mode=0
                # )
                fault_count += 1
                # faulty_outputs.append(1)

                # # OR-wired
                # faulty_output = simulate_BF_circuit(
                #     circuit,
                #     input_bits,
                #     faulty_gate_index=gate_index,
                #     wire_bit_1=wire_bit_1,
                #     wire_bit_2=wire_bit_2,
                #     mode=1
                # )
                fault_count += 1
                # faulty_outputs.append(1)

    return fault_count

def build_single_bridging_faults(num_lines, adjacency_mode="all"):
    """
    Build list of single bridging faults based on adjacency mode.

    adjacency_mode:
        "all"       — all wire pairs (original behavior)
        "adjacent"  — only physically adjacent wires (wire i and i+1)
        "shared"    — only pairs that share at least one wire index
                      (i.e., overlapping pairs: (0,1),(1,2) share wire 1)
    
    Each fault is a tuple: (wire_bit_1, wire_bit_2, mode)
        mode 0 = AND-bridging
        mode 1 = OR-bridging
    """

    single_faults = []

    if adjacency_mode == "adjacent":
        # Only physically neighboring wires: (0,1), (1,2), (2,3), ...
        pairs = [(i, i + 1) for i in range(num_lines - 1)]

    elif adjacency_mode == "shared":
        # Pairs that share a wire with another pair
        # i.e., consecutive pairs (i, i+1) and (i+1, i+2) share wire i+1
        # Here we collect all pairs (i, j) where |i - j| <= 2
        # to capture "near-neighbor" sharing
        pairs = [
            (i, j)
            for i in range(num_lines)
            for j in range(i + 1, num_lines)
            if j - i <= 2
        ]

    else:  # "all"
        pairs = [
            (i, j)
            for i in range(num_lines)
            for j in range(i + 1, num_lines)
        ]

    for wire1, wire2 in pairs:
        wire_bit_1 = 1 << wire1
        wire_bit_2 = 1 << wire2
        single_faults.append((wire_bit_1, wire_bit_2, 0))  # AND
        single_faults.append((wire_bit_1, wire_bit_2, 1))  # OR

    return single_faults


def filter_physically_realistic_combinations(fault_subset):
    """
    Filter out physically unrealistic multi-fault combinations.

    A combination is considered unrealistic if:
    - It mixes AND and OR bridging modes across different wire pairs
      simultaneously on the same gate (mixed-mode bridging is physically
      unlikely — a bridging fault is typically either a short to GND (AND)
      or short to VDD (OR), not both at once on different pairs).

    Returns True  → combination is realistic, keep it
    Returns False → combination is unrealistic, discard it
    """

    modes_present = set(fault[2] for fault in fault_subset)

    # If both AND (0) and OR (1) modes appear together → unrealistic
    if 0 in modes_present and 1 in modes_present:
        return False

    return True


def faulty_op_for_MBF(circuit,
                      input_bits,
                      max_faults_per_gate=2,
                      start_from_single=True,
                      adjacency_mode="all",
                      filter_mixed_mode=True):
    """
    Generate MBF faulty outputs.

    Parameters
    ----------
    max_faults_per_gate : int
        Maximum number of simultaneous bridging faults per gate.
        Default is 2 (pairs only). Raise carefully — combinations
        grow as C(|single_faults|, k) per gate.
        With num_lines=4: 12 single faults → C(12,2)=66 pairs per gate.
        With num_lines=8: 56 single faults → C(56,2)=1540 pairs per gate.

    start_from_single : bool
        If True  → set_size starts at 1, so MBF fully subsumes BF.
                   Use this when NOT running BF separately.
        If False → set_size starts at 2 (skip single faults).
                   Use this when BF is always run separately first
                   to avoid duplicate computation.
        Default: True

    adjacency_mode : str
        Controls which wire pairs are considered for bridging:
        "all"      → all C(num_lines, 2) pairs (original, most permissive)
        "adjacent" → only physically neighboring wires (i, i+1)
                     most restrictive, most physically realistic
        "shared"   → pairs within distance 2: (i,j) where j-i <= 2
                     middle ground

    filter_mixed_mode : bool
        If True → discard combinations that simultaneously apply both
                  AND-bridging and OR-bridging faults on the same gate,
                  as this is physically unrealistic.
        If False → allow all combinations (original behavior).
        Default: True
    """

    faulty_outputs = []
    fault_count = 0
    total_gates = circuit["No of Gates"]
    num_lines = circuit["No of Lines"]

    # Build single faults based on chosen adjacency model
    single_faults = build_single_bridging_faults(num_lines, adjacency_mode)

    if not single_faults:
        return faulty_outputs

    if max_faults_per_gate is None:
        max_faults = len(single_faults)
    else:
        max_faults = min(max_faults_per_gate, len(single_faults))

    # Determine starting set size
    min_set_size = 1 if start_from_single else 2

    for gate_index in range(total_gates):

        for set_size in range(min_set_size, max_faults + 1):

            for fault_subset in itertools.combinations(single_faults, set_size):

                # Skip physically unrealistic mixed-mode combinations
                if filter_mixed_mode and not filter_physically_realistic_combinations(fault_subset):
                    continue

                # faulty_output = simulate_MBF_circuit(
                #     circuit,
                #     input_bits,
                #     faulty_gate_index=gate_index,
                #     fault_list=fault_subset
                # )
                fault_count += 1
                # faulty_outputs.append(1)

    return fault_count


def get_all_faulty_outputs(circuit, testVec, fault_model):

    faultyOutputs = []
    # faulty op for fault at loc i
   
    if fault_model in ["SA-0", "SA-1"]:
        return faulty_op_for_SAF(circuit, testVec, fault_model)

    # SMGF FAULT
    elif fault_model == "SMGF":
        return faulty_op_for_SMGF(circuit, testVec)

    # PMGF FAULT
    elif fault_model == "PMGF":
        return faulty_op_for_PMGF(circuit, testVec)

    # MMGF FAULT
    elif fault_model == "MMGF":
        return faulty_op_for_MMGF(circuit, testVec, max_missing=3)

    # RGF FAULT
    elif fault_model == "RGF":
        return faulty_op_for_RGF(circuit, testVec, "Odd")

    # GAF FAULT
    elif fault_model == "GAF":
        return faulty_op_for_GAF(circuit, testVec)

    # CAF FAULT
    elif fault_model == "CAF":
        return faulty_op_for_CAF(circuit, testVec)

    # BF FAULT
    elif fault_model == "BF":
        return faulty_op_for_BF(circuit, testVec)

    # MBF Fault
    elif fault_model == "MBF":
        return faulty_op_for_MBF(circuit, testVec, 
                                 max_faults_per_gate=2,    # pairs only — raise carefully
                                 start_from_single=True,   # subsumes BF
                                 adjacency_mode="all",     # or "adjacent" / "shared"
                                 filter_mixed_mode=True    # discard AND+OR mixed combos
                                )
