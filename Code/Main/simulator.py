import re
import pandas as pd
import json
import os
from typing import List, Tuple, Dict, Any
import random

def convert_integer_to_binary(input_vector, maxValue):

    binaryVector = []
    vec = format(input_vector, f'0{maxValue}b')
    for bit in vec:
        binaryVector.append(int(bit))

    return binaryVector

def generate_random_vector(circuit):
    maxValue = circuit["No of Lines"]

    inputVector = random.randint(0, 2**maxValue - 1)
    binaryVector = convert_integer_to_binary(inputVector, maxValue)
    return binaryVector



import cupy as cp

def apply_gate_gpu(current_bits, gate):
    """
    Applies a gate to a BATCH of input vectors on the GPU.
    current_bits: CuPy array of integers (test vectors).
    """
    gate_type = gate[0]

    if gate_type == "TOFFOLI":
        control_mask = gate[1]
        target_bit = gate[2]
        # Vectors meeting the control condition are identified as a boolean mask
        condition = (current_bits & control_mask) == control_mask
        current_bits ^= (condition.astype(cp.int32) * target_bit)

    elif gate_type == "FREDKIN":
        control_mask = gate[1]
        swap_bit_1 = gate[2]
        swap_bit_2 = gate[3]

        condition = (current_bits & control_mask) == control_mask
        bit1_set = (current_bits & swap_bit_1) > 0
        bit2_set = (current_bits & swap_bit_2) > 0
        
        # Swap logic: XOR bit1 and bit2 to find differences, then apply control condition
        to_swap = condition & (bit1_set ^ bit2_set)
        current_bits ^= (to_swap.astype(cp.int32) * swap_bit_1)
        current_bits ^= (to_swap.astype(cp.int32) * swap_bit_2)

    elif gate_type == "PERES":
        control_mask = gate[1]
        xor_mask = gate[2]
        target_bit = gate[3]

        condition = (current_bits & control_mask) == control_mask
        current_bits ^= xor_mask # b = a XOR b
        current_bits ^= (condition.astype(cp.int32) * target_bit) # c = c XOR (a AND b)

    return current_bits

def simulate_batch_gpu(circuit, input_vectors_gpu):
    """Simulates the entire compiled circuit for a batch of vectors on GPU."""
    gates = circuit["Compiled Rep"]
    for gate in gates:
        input_vectors_gpu = apply_gate_gpu(input_vectors_gpu, gate)
    return input_vectors_gpu


def apply_gate(current_bits, gate):

    # print(f"current bits before processing: {current_bits}")
    gate_type = gate[0]

    # -------------------------------------------------
    # TOFFOLI GATE
    # -------------------------------------------------
    # Flip target bit if all control bits are 1
    if gate_type == "TOFFOLI":

        control_bits_required = gate[1]
        target_bit = gate[2]

        # Check if all required control bits are 1
        if (current_bits & control_bits_required) == control_bits_required:
            current_bits ^= target_bit  # flip target bit

        return current_bits


    # -------------------------------------------------
    # FREDKIN GATE
    # -------------------------------------------------
    # Swap two bits if all control bits are 1
    elif gate_type == "FREDKIN":

        control_bits_required = gate[1]
        swap_bit_1 = gate[2]
        swap_bit_2 = gate[3]

        if (current_bits & control_bits_required) == control_bits_required:

            bit1_is_set = current_bits & swap_bit_1
            bit2_is_set = current_bits & swap_bit_2

            # Swap only if bits are different
            if bool(bit1_is_set) ^ bool(bit2_is_set):
                current_bits ^= swap_bit_1
                current_bits ^= swap_bit_2

        return current_bits


    # -------------------------------------------------
    # PERES GATE
    # -------------------------------------------------
    # Implements:
    #   b = a XOR b
    #   c = c XOR (a AND b_original)
    elif gate_type == "PERES":

        control_bits_required = gate[1]
        xor_bit_pair_mask = gate[2]
        target_bit = gate[3]

        # Check control condition BEFORE modifying bits
        control_condition_active = (
            (current_bits & control_bits_required)
            == control_bits_required
        )

        # First operation: XOR second wire with first
        current_bits ^= xor_bit_pair_mask

        # Second operation: controlled NOT on target
        if control_condition_active:
            current_bits ^= target_bit

        return current_bits
    # print(f"current bits after processing: {current_bits}")
    return current_bits


# ==============================FAULT-FREE SIMULATION==============================
def simulate_fault_free(circuit: dict, input_vector: int) -> int:

    signals = input_vector
    gates = circuit["Compiled Rep"]
    # print(gates, signals)
    for gate in gates:
        signals = apply_gate(signals, gate)

    return signals

# ==============================FAULTY SIMULATION==============================
# ------------------------------SMGF SIMULATION------------------------------


def simulate_MMGF_circuit(circuit, input_bits, faulty_gate_indices=None):
    """
    Simulate circuit with Multiple Missing Gate Fault (MMGF).

    circuit     : circuit with compiled gates
    input_bits           : integer input vector
    faulty_gate_indices  : set of gate indices to skip
    """

    current_bits = input_bits
    compiled_gates = circuit["Compiled Rep"]

    # If no faults, just normal simulation
    if not faulty_gate_indices:
        for gate in compiled_gates:
            current_bits = apply_gate(current_bits, gate)
        return current_bits

    # With faults (skip faulty gates)
    for gate_index, gate in enumerate(compiled_gates):

        if gate_index in faulty_gate_indices:
            continue

        current_bits = apply_gate(current_bits, gate)

    return current_bits

def simulate_PMGF_circuit(circuit,
                          input_bits,
                          faulty_gate_index=None,
                          missing_control_bits_mask=None,
                          start_gate=None):
    """
    faulty_gate_index         : gate level where PMGF occurs
    missing_control_bits_mask : bitmask of control bits that are missing
    start_gate                : if provided, only simulate gates from this index onward.
                                Used with DP prefix table — caller passes prefix[gate_index]
                                as input_bits and start_gate=gate_index so prefix gates
                                are not re-walked and double-applied.
    """

    current_bits = input_bits
    compiled_gates = circuit["Compiled Rep"]

    gate_range = range(
        start_gate if start_gate is not None else 0,
        len(compiled_gates)
    )

    for gate_index in gate_range:
        gate = compiled_gates[gate_index]

        gate_type = gate[0]

        # -------------------------------------------------
        # If this is NOT the faulty gate → normal apply
        # -------------------------------------------------
        if gate_index != faulty_gate_index:
            current_bits = apply_gate(current_bits, gate)
            continue

        # -------------------------------------------------
        # Faulty Gate (PMGF applied here)
        # -------------------------------------------------

        if gate_type == "TOFFOLI":

            original_control_bits = gate[1]
            target_bit = gate[2]

            effective_control_bits = (
                original_control_bits & ~missing_control_bits_mask
            )

            # effective_control_bits == 0 means ALL controls removed
            # gate fires unconditionally → always flip target
            if effective_control_bits == 0 or \
               (current_bits & effective_control_bits) == effective_control_bits:
                current_bits ^= target_bit

        elif gate_type == "FREDKIN":

            original_control_bits = gate[1]
            swap_bit_1 = gate[2]
            swap_bit_2 = gate[3]

            effective_control_bits = (
                original_control_bits & ~missing_control_bits_mask
            )

            if effective_control_bits == 0 or \
               (current_bits & effective_control_bits) == effective_control_bits:

                bit1 = current_bits & swap_bit_1
                bit2 = current_bits & swap_bit_2

                if bool(bit1) ^ bool(bit2):
                    current_bits ^= swap_bit_1
                    current_bits ^= swap_bit_2

        elif gate_type == "PERES":

            original_control_bits = gate[1]
            xor_bit_pair_mask = gate[2]
            target_bit = gate[3]

            effective_control_bits = (
                original_control_bits & ~missing_control_bits_mask
            )

            control_active = (
                effective_control_bits == 0 or
                (current_bits & effective_control_bits) == effective_control_bits
            )

            current_bits ^= xor_bit_pair_mask

            if control_active:
                current_bits ^= target_bit

    return current_bits


def simulate_SAF_circuit(circuit,
                         input_bits,
                         faulty_gate_index=None,
                         faulty_wire_bit=None,
                         stuck_at_value=None,
                         start_gate=None):        # ← NEW
    """
    start_gate : if provided, only simulate gates from this index onward.
                 Used with DP prefix table — caller passes prefix[gate_index]
                 and start_gate=gate_index so prefix gates are not re-walked.
    """

    current_bits = input_bits
    compiled_gates = circuit["Compiled Rep"]

    gate_range = range(start_gate if start_gate is not None else 0,
                       len(compiled_gates))       # ← only suffix

    for gate_index in gate_range:
        gate = compiled_gates[gate_index]

        if gate_index == faulty_gate_index and faulty_wire_bit is not None:
            if stuck_at_value == 0:
                current_bits &= ~faulty_wire_bit
            elif stuck_at_value == 1:
                current_bits |= faulty_wire_bit

        current_bits = apply_gate(current_bits, gate)

    return current_bits

def simulate_RGF_circuit(circuit,
                         input_bits,
                         faulty_gate_index=None,
                         repeat_mode="Odd",
                         start_gate=None):
    """
    Simulate circuit under Repeated Gate Fault (RGF).

    faulty_gate_index : gate to repeat
    repeat_mode       : "Odd" or "Even"
    start_gate        : if provided, only simulate gates from this index onward.
                        Used with DP prefix table — caller passes prefix[gate_index]
                        as input_bits and start_gate=gate_index so prefix gates
                        are not re-walked and double-applied.
    """

    current_bits = input_bits
    compiled_gates = circuit["Compiled Rep"]

    gate_range = range(
        start_gate if start_gate is not None else 0,
        len(compiled_gates)
    )

    for gate_index in gate_range:
        gate = compiled_gates[gate_index]

        # Apply gate normally
        current_bits = apply_gate(current_bits, gate)

        # If this is the faulty gate, repeat it
        if gate_index == faulty_gate_index:

            if repeat_mode == "Odd":
                # Apply once more (total 2 applications)
                current_bits = apply_gate(current_bits, gate)

            elif repeat_mode == "Even":
                # Apply twice more (total 3 applications)
                current_bits = apply_gate(current_bits, gate)
                current_bits = apply_gate(current_bits, gate)

    return current_bits

def simulate_GAF_circuit(circuit,
                         input_bits,
                         insertion_index,
                         extra_gate):

    current_bits = input_bits
    compiled_gates = circuit["Compiled Rep"]

    # Insert before first gate
    if insertion_index == -1:
        current_bits = apply_gate(current_bits, extra_gate)

    for gate_index, gate in enumerate(compiled_gates):

        current_bits = apply_gate(current_bits, gate)

        if gate_index == insertion_index:
            current_bits = apply_gate(current_bits, extra_gate)

    return current_bits


def simulate_CAF_circuit(circuit,
                         input_bits,
                         faulty_gate_index=None,
                         extra_control_bit=None,
                         start_gate=None):
    """
    Simulate circuit under Control Addition Fault (CAF).

    faulty_gate_index : gate where extra control is added
    extra_control_bit : the extra control wire being added as a bitmask
    start_gate        : if provided, only simulate gates from this index onward.
                        Used with DP prefix table — caller passes prefix[gate_index]
                        as input_bits and start_gate=gate_index so prefix gates
                        are not re-walked and double-applied.
    """

    current_bits = input_bits
    compiled_gates = circuit["Compiled Rep"]

    gate_range = range(
        start_gate if start_gate is not None else 0,
        len(compiled_gates)
    )

    for gate_index in gate_range:
        gate = compiled_gates[gate_index]

        # -------------------------------------------------
        # Normal gate — not the faulty one
        # -------------------------------------------------
        if gate_index != faulty_gate_index:
            current_bits = apply_gate(current_bits, gate)
            continue

        # -------------------------------------------------
        # Faulty gate — extra control bit added
        # -------------------------------------------------
        gate_type = gate[0]

        if gate_type == "TOFFOLI":
            control_bits = gate[1]
            target_bit = gate[2]

            new_control_bits = control_bits | extra_control_bit

            if (current_bits & new_control_bits) == new_control_bits:
                current_bits ^= target_bit

        elif gate_type == "FREDKIN":
            control_bits = gate[1]
            swap_bit_1 = gate[2]
            swap_bit_2 = gate[3]

            new_control_bits = control_bits | extra_control_bit

            if (current_bits & new_control_bits) == new_control_bits:
                bit1 = current_bits & swap_bit_1
                bit2 = current_bits & swap_bit_2

                if bool(bit1) ^ bool(bit2):
                    current_bits ^= swap_bit_1
                    current_bits ^= swap_bit_2

        elif gate_type == "PERES":
            control_bits = gate[1]
            xor_bit_mask = gate[2]
            target_bit = gate[3]

            new_control_bits = control_bits | extra_control_bit

            control_active = (
                (current_bits & new_control_bits) == new_control_bits
            )

            current_bits ^= xor_bit_mask

            if control_active:
                current_bits ^= target_bit

    return current_bits


def apply_bridging_fault(current_bits,
                         wire_bit_1,
                         wire_bit_2,
                         mode):
    """
    mode = 0 → AND-wired
    mode = 1 → OR-wired
    """

    bit1 = 1 if (current_bits & wire_bit_1) else 0
    bit2 = 1 if (current_bits & wire_bit_2) else 0

    if mode == 0:      # AND-wired
        new_value = bit1 & bit2
    else:              # OR-wired
        new_value = bit1 | bit2

    # Clear both bits
    current_bits &= ~wire_bit_1
    current_bits &= ~wire_bit_2

    # Set them to new_value
    if new_value:
        current_bits |= wire_bit_1
        current_bits |= wire_bit_2

    return current_bits

def simulate_BF_circuit(circuit,
                        input_bits,
                        faulty_gate_index=None,
                        wire_bit_1=None,
                        wire_bit_2=None,
                        mode=0,
                        start_gate=None):
    """
    Simulate circuit under Bridging Fault (BF).

    faulty_gate_index : gate before which bridging is applied
    wire_bit_1        : first wire bitmask
    wire_bit_2        : second wire bitmask
    mode              : 0 = AND bridging, 1 = OR bridging
    start_gate        : if provided, only simulate gates from this index onward.
                        Used with DP prefix table — caller passes prefix[gate_index]
                        as input_bits and start_gate=gate_index so prefix gates
                        are not re-walked and double-applied.
    """

    current_bits = input_bits
    compiled_gates = circuit["Compiled Rep"]

    gate_range = range(
        start_gate if start_gate is not None else 0,
        len(compiled_gates)
    )

    for gate_index in gate_range:
        gate = compiled_gates[gate_index]

        # -------------------------------------------------
        # Apply bridging fault BEFORE executing faulty gate
        # -------------------------------------------------
        if gate_index == faulty_gate_index:

            if mode == 0:
                # AND bridging — both wires take AND of their values
                and_val = (current_bits & wire_bit_1) and (current_bits & wire_bit_2)
                if and_val:
                    current_bits |= wire_bit_1
                    current_bits |= wire_bit_2
                else:
                    current_bits &= ~wire_bit_1
                    current_bits &= ~wire_bit_2

            elif mode == 1:
                # OR bridging — both wires take OR of their values
                or_val = (current_bits & wire_bit_1) | (current_bits & wire_bit_2)
                if or_val:
                    current_bits |= wire_bit_1
                    current_bits |= wire_bit_2
                else:
                    current_bits &= ~wire_bit_1
                    current_bits &= ~wire_bit_2

        current_bits = apply_gate(current_bits, gate)

    return current_bits


def apply_multiple_bridging_faults(current_bits,
                                   fault_list):
    """
    fault_list = list of tuples:
        (wire_bit_1, wire_bit_2, mode)
    """

    for wire_bit_1, wire_bit_2, mode in fault_list:
        current_bits = apply_bridging_fault(
            current_bits,
            wire_bit_1,
            wire_bit_2,
            mode
        )

    return current_bits

def simulate_MBF_circuit(circuit,
                         input_bits,
                         faulty_gate_index=None,
                         fault_list=None):
    """
    fault_list = list of (wire_bit_1, wire_bit_2, mode)
    """

    current_bits = input_bits
    compiled_gates = circuit["Compiled Rep"]

    for gate_index, gate in enumerate(compiled_gates):

        if gate_index == faulty_gate_index and fault_list:
            current_bits = apply_multiple_bridging_faults(
                current_bits,
                fault_list
            )

        current_bits = apply_gate(current_bits, gate)

    return current_bits