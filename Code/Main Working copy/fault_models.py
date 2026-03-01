from simulator import *
import itertools
from itertools import combinations

def faulty_op_for_SMGF(circuit, input_state):
    """
    Optimized SMGF using compiled circuit and integer state.
    Compatible with your optimized fault-free simulator.
    """

    compiled_gates = circuit["Compiled Rep"]
    n = len(compiled_gates)

    # ---------------------------------
    # 1. Compute prefix states once
    # ---------------------------------
    states = [input_state]
    current = input_state

    for gate in compiled_gates:
        current = apply_gate(current, gate)
        states.append(current)

    # states[i] = state BEFORE gate i

    faulty_outputs = []

    # ---------------------------------
    # 2. For each missing gate
    # ---------------------------------
    for i in range(n):

        current = states[i]

        # apply only suffix
        for j in range(i + 1, n):
            current = apply_gate(current, compiled_gates[j])

        faulty_outputs.append(current)

    return faulty_outputs

from itertools import combinations






def faulty_op_for_MMGF(circuit, input_bits):
    """
    Generate outputs for all MMGF fault combinations.
    """

    total_gates = circuit["No of Gates"]
    faulty_outputs = []

    # Generate all possible missing-gate combinations
    # from 1 missing gate up to (total_gates - 1)
    for num_missing in range(1, total_gates):

        for faulty_subset in combinations(range(total_gates), num_missing):

            faulty_set = set(faulty_subset)

            faulty_output = simulate_MMGF_circuit(
                circuit,
                input_bits,
                faulty_set
            )

            faulty_outputs.append(faulty_output)

    return faulty_outputs



def faulty_op_for_PMGF(circuit, input_bits):

    faulty_outputs = []
    compiled_gates = circuit["Compiled Rep"]

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

                faulty_output = simulate_PMGF_circuit(
                    circuit,
                    input_bits,
                    faulty_gate_index=gate_index,
                    missing_control_bits_mask=missing_mask
                )

                faulty_outputs.append(faulty_output)

    return faulty_outputs


def faulty_op_for_SAF(circuit, input_bits, fault_model):
    """
    Generate all SAF faulty outputs.
    fault_model : "SA-0" or "SA-1"
    """

    faulty_outputs = []
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

            faulty_output = simulate_SAF_circuit(
                circuit,
                input_bits,
                faulty_gate_index=gate_index,
                faulty_wire_bit=wire_bit,
                stuck_at_value=stuck_value
            )

            faulty_outputs.append(faulty_output)

    return faulty_outputs

def faulty_op_for_RGF(circuit, input_bits, mode="Odd"):
    """
    Generate RGF faulty outputs.

    mode : "Odd" or "Even"
    """

    faulty_outputs = []
    total_gates = circuit["No of Gates"]

    for gate_index in range(total_gates):

        faulty_output = simulate_RGF_circuit(
            circuit,
            input_bits,
            faulty_gate_index=gate_index,
            repeat_mode=mode
        )

        faulty_outputs.append(faulty_output)

    return faulty_outputs

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

    faulty_outputs = []

    total_gates = circuit["No of Gates"]
    num_lines = circuit["No of Lines"]

    gate_library = build_gaf_gate_library(num_lines)

    # Try every possible insertion position
    for insertion_index in range(-1, total_gates):

        # Randomly choose one gate
        extra_gate = random.choice(gate_library)

        faulty_output = simulate_GAF_circuit(
            circuit,
            input_bits,
            insertion_index,
            extra_gate
        )

        faulty_outputs.append(faulty_output)

    return faulty_outputs


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

            faulty_output = simulate_CAF_circuit(
                circuit,
                input_bits,
                faulty_gate_index=gate_index,
                extra_control_bit=extra_control_bit
            )

            faulty_outputs.append(faulty_output)

    return faulty_outputs


def faulty_op_for_BF(circuit, input_bits):

    faulty_outputs = []

    total_gates = circuit["No of Gates"]
    num_lines = circuit["No of Lines"]

    for gate_index in range(total_gates):

        for wire1 in range(num_lines):
            for wire2 in range(wire1 + 1, num_lines):

                wire_bit_1 = 1 << wire1
                wire_bit_2 = 1 << wire2

                # AND-wired
                faulty_output = simulate_BF_circuit(
                    circuit,
                    input_bits,
                    faulty_gate_index=gate_index,
                    wire_bit_1=wire_bit_1,
                    wire_bit_2=wire_bit_2,
                    mode=0
                )
                faulty_outputs.append(faulty_output)

                # OR-wired
                faulty_output = simulate_BF_circuit(
                    circuit,
                    input_bits,
                    faulty_gate_index=gate_index,
                    wire_bit_1=wire_bit_1,
                    wire_bit_2=wire_bit_2,
                    mode=1
                )
                faulty_outputs.append(faulty_output)

    return faulty_outputs


def faulty_op_for_MBF(circuit,
                      input_bits,
                      max_faults_per_gate=2):

    faulty_outputs = []

    total_gates = circuit["No of Gates"]
    num_lines = circuit["No of Lines"]

    # -------------------------------------------------
    # Precompute all possible single bridging faults
    # -------------------------------------------------
    single_faults = []

    for wire1 in range(num_lines):
        for wire2 in range(wire1 + 1, num_lines):

            wire_bit_1 = 1 << wire1
            wire_bit_2 = 1 << wire2

            single_faults.append((wire_bit_1, wire_bit_2, 0))  # AND
            single_faults.append((wire_bit_1, wire_bit_2, 1))  # OR

    # Limit max faults per gate
    if max_faults_per_gate is None:
        max_faults = len(single_faults)
    else:
        max_faults = min(max_faults_per_gate, len(single_faults))

    # -------------------------------------------------
    # For each gate, generate multi-fault combinations
    # -------------------------------------------------
    for gate_index in range(total_gates):

        for set_size in range(2, max_faults + 1):

            for fault_subset in itertools.combinations(
                    single_faults, set_size):

                faulty_output = simulate_MBF_circuit(
                    circuit,
                    input_bits,
                    faulty_gate_index=gate_index,
                    fault_list=fault_subset
                )

                faulty_outputs.append(faulty_output)

    return faulty_outputs


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
        return faulty_op_for_MMGF(circuit, testVec)

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
        return faulty_op_for_MBF(circuit, testVec)

