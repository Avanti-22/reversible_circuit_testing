import re
import pandas as pd
import json
import os
from typing import List, Tuple, Dict, Any
from Organized.Utils.circuitParsingUtilityFunctions import *
import random
# from GAUtilityFunctions import *

def convert_integer_to_binary(input_vector, maxValue):
    # binaryVector = []
    # while (input_vector >= 1):
    #     # #print(input_vector)
    #     bit = input_vector % 2
    #     binaryVector.append(bit)
    #     input_vector = input_vector // 2

    # while (len(binaryVector) < maxValue):
    #     binaryVector.append(0)

    # binaryVector.reverse()

    # return binaryVector
    
    binaryVector = []
    vec = format(input_vector, f'0{maxValue}b')
    for bit in vec:
        binaryVector.append(int(bit))
        
    return binaryVector

def generate_random_vector(circuit):
    maxValue = circuit["No of Lines"]
    # inputVector= int(input("Enter the integer between 0-"+str(2**maxValue -1)+"for creating binary vector: "))

    inputVector = random.randint(0, 2**maxValue - 1)
    binaryVector = convert_integer_to_binary(inputVector, maxValue)
    # #print(binaryVector)
    return binaryVector

def simulate_circuit(circuit, binaryVector):
    # vector processing throught the circuit
    gates = circuit["Gates"]

    # create a circuit with variables replaced with input values
    indexVariableMap = {}
    for i in range(len(binaryVector)):
        indexVariableMap[circuit["Variables"][i]] = i

    # #print(indexVariableMap)

    intermediateVector = binaryVector.copy()

    # replace variables in gates with input values from binary vector
    count = 0
    for gate in gates:
        type = gate["gate"]
        gateParts = gate["vars"]

        # #print("For gate level: ",count)
        # #print("Input vector: ",intermediateVector)
        # ****WORKING FOR TOFFOLI GATE
        # process the vector for toffoli gate at current level
        if (type == "TOFFOLI"):

            if all(intermediateVector[indexVariableMap[gateParts[c]]] == 1 for c in range(len(gateParts)-1)):
                # #print("control activates the target bit")
                index = indexVariableMap[gateParts[-1]]
                intermediateVector[index] = 1 - intermediateVector[index]

            count += 1

        # process the vector for toffoli gate at current level
        elif (type == "FREDKIN"):
            if all(intermediateVector[indexVariableMap[gateParts[c]]] == 1 for c in range(len(gateParts)-2)):
                # #print("control activates the target bit")
                index1 = indexVariableMap[gateParts[-2]]
                index2 = indexVariableMap[gateParts[-1]]

                # swap the target bits
                intermediateVector[index1], intermediateVector[index2] = intermediateVector[index2], intermediateVector[index1]
            count += 1

        # process the vector for toffoli gate at current level
        if (type == "PERES"):

            # calculate the secondlast target bit
            secondLastIndex = indexVariableMap[gateParts[-2]]
            thirdLastIndex = indexVariableMap[gateParts[-3]]
            intermediateVector[secondLastIndex] = intermediateVector[thirdLastIndex] ^ intermediateVector[secondLastIndex]

            if all(intermediateVector[indexVariableMap[gateParts[c]]] == 1 for c in range(len(gateParts)-1)):
                lastIndex = indexVariableMap[gateParts[-1]]
                intermediateVector[lastIndex] = 1 - \
                    intermediateVector[lastIndex]

            count += 1

        # #print("after current gate, the intermediate vector: ",intermediateVector)
    # print("after processing through the circuit, final put vector: ",intermediateVector)
    return intermediateVector

def simulate_MBF_circuit(circuit, binaryVector, isFaulty=True):
    # vector processing throught the circuit
    gates = circuit["Gates"]

    # create a circuit with variables replaced with input values
    indexVariableMap = {}
    for i in range(len(binaryVector)):
        indexVariableMap[circuit["Variables"][i]] = i

    # print(indexVariableMap)

    intermediateVector = binaryVector.copy()

    def apply_bridging_fault(intermediateVector, fault):
        # fault tuple: (gate_index, wire1, wire2, mode)
        _, wire1, wire2, mode = fault
        idx1 = indexVariableMap[wire1]
        idx2 = indexVariableMap[wire2]
        if mode == "AND-wired":
            wired_val = intermediateVector[idx1] & intermediateVector[idx2]
        else:
            wired_val = intermediateVector[idx1] | intermediateVector[idx2]
        intermediateVector[idx1] = wired_val
        intermediateVector[idx2] = wired_val

    # replace variables in gates with input values from binary vector
    count = 0
    for gate in gates:
        type = gate["gate"]
        gateParts = gate["vars"]

        # print("For gate level: ",count)
        # print("Input vector: ",intermediateVector)

        if isFaulty:
            faultModel = circuit.get("Fault Model")
            faultPosition = circuit.get(
                "Fault Position", circuit.get("Fault Positions"))

            # apply multiple bridging faults at this level
            if faultModel in ["Multiple BF", "MBF"] and faultPosition is not None:
                for fault in faultPosition:
                    if count == fault[0]:
                        # print(f"Applying multiple bridging fault at level {count}: {fault[1]}-{fault[2]} {fault[3]}")
                        apply_bridging_fault(intermediateVector, fault)

        # ****WORKING FOR TOFFOLI GATE
        # process the vector for toffoli gate at current level
        if (type == "TOFFOLI"):

            if all(intermediateVector[indexVariableMap[gateParts[c]]] == 1 for c in range(len(gateParts)-1)):
                # #print("control activates the target bit")
                index = indexVariableMap[gateParts[-1]]
                intermediateVector[index] = 1 - intermediateVector[index]

            count += 1

        # process the vector for toffoli gate at current level
        elif (type == "FREDKIN"):
            if all(intermediateVector[indexVariableMap[gateParts[c]]] == 1 for c in range(len(gateParts)-2)):
                # #print("control activates the target bit")
                index1 = indexVariableMap[gateParts[-2]]
                index2 = indexVariableMap[gateParts[-1]]

                # swap the target bits
                intermediateVector[index1], intermediateVector[index2] = intermediateVector[index2], intermediateVector[index1]
            count += 1

        # process the vector for toffoli gate at current level
        if (type == "PERES"):

            # calculate the secondlast target bit
            secondLastIndex = indexVariableMap[gateParts[-2]]
            thirdLastIndex = indexVariableMap[gateParts[-3]]
            intermediateVector[secondLastIndex] = intermediateVector[thirdLastIndex] ^ intermediateVector[secondLastIndex]

            if all(intermediateVector[indexVariableMap[gateParts[c]]] == 1 for c in range(len(gateParts)-1)):
                lastIndex = indexVariableMap[gateParts[-1]]
                intermediateVector[lastIndex] = 1 - \
                    intermediateVector[lastIndex]

            count += 1

        # #print("after current gate, the intermediate vector: ",intermediateVector)
    # print("after processing through the circuit, final put vector: ",intermediateVector)
    return intermediateVector

def simulate_SMGF_circuit(circuit, binaryVector, isFaulty=True):
    # vector processing throught the circuit
    gates = circuit["Gates"]

    # create a circuit with variables replaced with input values
    indexVariableMap = {}
    for i in range(len(binaryVector)):
        indexVariableMap[circuit["Variables"][i]] = i

    # print(indexVariableMap)

    intermediateVector = binaryVector.copy()

    # replace variables in gates with input values from binary vector
    count = 0
    for gate in gates:
        type = gate["gate"]
        gateParts = gate["vars"]

        # print("For gate level: ",count)
        # print("Input vector: ",intermediateVector)

        if isFaulty:
            faultModel = circuit.get("Fault Model")
            faultPosition = circuit.get(
                "Fault Position", circuit.get("Fault Positions"))

            # check if current gate is faulty (single missing gate)
            if faultModel == "SMGF" and faultPosition is not None and count in faultPosition:
                # print(f"Skipping gate at level {count} due to SMGF fault")
                count += 1
                continue

        # ****WORKING FOR TOFFOLI GATE
        # process the vector for toffoli gate at current level
        if (type == "TOFFOLI"):

            if all(intermediateVector[indexVariableMap[gateParts[c]]] == 1 for c in range(len(gateParts)-1)):
                # #print("control activates the target bit")
                index = indexVariableMap[gateParts[-1]]
                intermediateVector[index] = 1 - intermediateVector[index]

            count += 1

        # process the vector for toffoli gate at current level
        elif (type == "FREDKIN"):
            if all(intermediateVector[indexVariableMap[gateParts[c]]] == 1 for c in range(len(gateParts)-2)):
                # #print("control activates the target bit")
                index1 = indexVariableMap[gateParts[-2]]
                index2 = indexVariableMap[gateParts[-1]]

                # swap the target bits
                intermediateVector[index1], intermediateVector[index2] = intermediateVector[index2], intermediateVector[index1]
            count += 1

        # process the vector for toffoli gate at current level
        if (type == "PERES"):

            # calculate the secondlast target bit
            secondLastIndex = indexVariableMap[gateParts[-2]]
            thirdLastIndex = indexVariableMap[gateParts[-3]]
            intermediateVector[secondLastIndex] = intermediateVector[thirdLastIndex] ^ intermediateVector[secondLastIndex]

            if all(intermediateVector[indexVariableMap[gateParts[c]]] == 1 for c in range(len(gateParts)-1)):
                lastIndex = indexVariableMap[gateParts[-1]]
                intermediateVector[lastIndex] = 1 - \
                    intermediateVector[lastIndex]

            count += 1

    #     print("after current gate, the intermediate vector: ",intermediateVector)
    # print("after processing through the circuit, final put vector: ",intermediateVector)
    return intermediateVector

def simulate_MMGF_circuit(circuit, binaryVector, isFaulty=True):
    # vector processing throught the circuit
    gates = circuit["Gates"]

    # create a circuit with variables replaced with input values
    indexVariableMap = {}
    for i in range(len(binaryVector)):
        indexVariableMap[circuit["Variables"][i]] = i

    # print(indexVariableMap)

    intermediateVector = binaryVector.copy()

    # replace variables in gates with input values from binary vector
    count = 0
    for gate in gates:
        type = gate["gate"]
        gateParts = gate["vars"]

        # print("For gate level: ",count)
        # print("Input vector: ",intermediateVector)

        if isFaulty:
            faultModel = circuit.get("Fault Model")
            faultPosition = circuit.get(
                "Fault Position", circuit.get("Fault Positions"))
            # print(faultPosition)
            # check if current gate is faulty (multiple missing gates)
            if faultModel == "MMGF" and faultPosition is not None and count in faultPosition:
                # print(f"Skipping gate at level {count} due to MMGF fault")                    
                count += 1
                continue

        # ****WORKING FOR TOFFOLI GATE
        # process the vector for toffoli gate at current level
        if (type == "TOFFOLI"):

            if all(intermediateVector[indexVariableMap[gateParts[c]]] == 1 for c in range(len(gateParts)-1)):
                # #print("control activates the target bit")
                index = indexVariableMap[gateParts[-1]]
                intermediateVector[index] = 1 - intermediateVector[index]

            count += 1

        # process the vector for toffoli gate at current level
        elif (type == "FREDKIN"):
            if all(intermediateVector[indexVariableMap[gateParts[c]]] == 1 for c in range(len(gateParts)-2)):
                # #print("control activates the target bit")
                index1 = indexVariableMap[gateParts[-2]]
                index2 = indexVariableMap[gateParts[-1]]

                # swap the target bits
                intermediateVector[index1], intermediateVector[index2] = intermediateVector[index2], intermediateVector[index1]
            count += 1

        # process the vector for toffoli gate at current level
        if (type == "PERES"):

            # calculate the secondlast target bit
            secondLastIndex = indexVariableMap[gateParts[-2]]
            thirdLastIndex = indexVariableMap[gateParts[-3]]
            intermediateVector[secondLastIndex] = intermediateVector[thirdLastIndex] ^ intermediateVector[secondLastIndex]

            if all(intermediateVector[indexVariableMap[gateParts[c]]] == 1 for c in range(len(gateParts)-1)):
                lastIndex = indexVariableMap[gateParts[-1]]
                intermediateVector[lastIndex] = 1 - \
                    intermediateVector[lastIndex]
            count += 1

        # #print("after current gate, the intermediate vector: ",intermediateVector)
    # print("after processing through the circuit, final put vector: ",intermediateVector)
    return intermediateVector

def simulate_PMGF_circuit(circuit, binaryVector, isFaulty=True):
    # vector processing throught the circuit
    gates = circuit["Gates"]

    # create a circuit with variables replaced with input values
    indexVariableMap = {}
    for i in range(len(binaryVector)):
        indexVariableMap[circuit["Variables"][i]] = i

    # print(indexVariableMap)

    intermediateVector = binaryVector.copy()

    # replace variables in gates with input values from binary vector
    count = 0
    for gate in gates:
        type = gate["gate"]
        gateParts = gate["vars"]

        # print("For gate level: ",count)
        # print("Input vector: ",intermediateVector)

        # PMGF: missing some control bits in the current gate
        pmgf_missing_controls = set()
        if isFaulty:
            faultModel = circuit.get("Fault Model")
            faultPosition = circuit.get("Fault Position")
            if faultModel == "PMGF" and faultPosition is not None and count == faultPosition[0]:
                pmgf_missing_controls = set(faultPosition[1])
                # print("fault at gate: ",
                #       faultPosition[0], "wire: ", pmgf_missing_controls)

        # ****WORKING FOR TOFFOLI GATE
        # process the vector for toffoli gate at current level
        if (type == "TOFFOLI"):
            controls = list(range(len(gateParts)-1))
            if pmgf_missing_controls:
                controls = [
                    c for c in controls if c not in pmgf_missing_controls]

            if all(intermediateVector[indexVariableMap[gateParts[c]]] == 1 for c in controls):
                # #print("control activates the target bit")
                index = indexVariableMap[gateParts[-1]]
                intermediateVector[index] = 1 - intermediateVector[index]

            count += 1

        # process the vector for toffoli gate at current level
        elif (type == "FREDKIN"):
            controls = list(range(len(gateParts)-2))
            if pmgf_missing_controls:
                controls = [
                    c for c in controls if c not in pmgf_missing_controls]

            if all(intermediateVector[indexVariableMap[gateParts[c]]] == 1 for c in controls):
                # #print("control activates the target bit")
                index1 = indexVariableMap[gateParts[-2]]
                index2 = indexVariableMap[gateParts[-1]]

                # swap the target bits
                intermediateVector[index1], intermediateVector[index2] = intermediateVector[index2], intermediateVector[index1]
            count += 1

        # process the vector for toffoli gate at current level
        if (type == "PERES"):

            # calculate the secondlast target bit
            secondLastIndex = indexVariableMap[gateParts[-2]]
            thirdLastIndex = indexVariableMap[gateParts[-3]]
            intermediateVector[secondLastIndex] = intermediateVector[thirdLastIndex] ^ intermediateVector[secondLastIndex]

            controls = list(range(len(gateParts)-1))
            if pmgf_missing_controls:
                controls = [
                    c for c in controls if c not in pmgf_missing_controls]

            if all(intermediateVector[indexVariableMap[gateParts[c]]] == 1 for c in controls):
                lastIndex = indexVariableMap[gateParts[-1]]
                intermediateVector[lastIndex] = 1 - \
                    intermediateVector[lastIndex]

            count += 1

        # #print("after current gate, the intermediate vector: ",intermediateVector)
    # print("after processing through the circuit, final put vector: ",intermediateVector)
    return intermediateVector

def simulate_SAF_circuit(circuit, binaryVector, isFaulty=True):
    # vector processing throught the circuit
    gates = circuit["Gates"]

    # create a circuit with variables replaced with input values
    indexVariableMap = {}
    for i in range(len(binaryVector)):
        indexVariableMap[circuit["Variables"][i]] = i

    # print(indexVariableMap)

    intermediateVector = binaryVector.copy()

    # replace variables in gates with input values from binary vector
    count = 0
    for gate in gates:
        type = gate["gate"]
        gateParts = gate["vars"]

        # print("For gate level: ",count)
        # print("Input vector: ",intermediateVector)

        if isFaulty:
            faultModel = circuit.get("Fault Model")
            faultPosition = circuit.get(
                "Fault Position", circuit.get("Fault Positions"))

            # check if current gate has a SAF fault
            if faultModel in ["SA-0", "SA-1"] and faultPosition is not None:
                for var in gateParts:
                    if (count, var) == faultPosition:
                        if faultModel == "SA-0":
                            # print(f"Stuck-at-0 fault at level {count} on variable {var}")
                            intermediateVector[indexVariableMap[var]] = 0
                        elif faultModel == "SA-1":
                            # print(f"Stuck-at-1 fault at level {count} on variable {var}")
                            intermediateVector[indexVariableMap[var]] = 1

        # ****WORKING FOR TOFFOLI GATE
        # process the vector for toffoli gate at current level
        if (type == "TOFFOLI"):

            if all(intermediateVector[indexVariableMap[gateParts[c]]] == 1 for c in range(len(gateParts)-1)):
                # #print("control activates the target bit")
                index = indexVariableMap[gateParts[-1]]
                intermediateVector[index] = 1 - intermediateVector[index]

            count += 1

        # process the vector for toffoli gate at current level
        elif (type == "FREDKIN"):
            if all(intermediateVector[indexVariableMap[gateParts[c]]] == 1 for c in range(len(gateParts)-2)):
                # #print("control activates the target bit")
                index1 = indexVariableMap[gateParts[-2]]
                index2 = indexVariableMap[gateParts[-1]]

                # swap the target bits
                intermediateVector[index1], intermediateVector[index2] = intermediateVector[index2], intermediateVector[index1]
            count += 1

        # process the vector for toffoli gate at current level
        if (type == "PERES"):

            # calculate the secondlast target bit
            secondLastIndex = indexVariableMap[gateParts[-2]]
            thirdLastIndex = indexVariableMap[gateParts[-3]]
            intermediateVector[secondLastIndex] = intermediateVector[thirdLastIndex] ^ intermediateVector[secondLastIndex]

            if all(intermediateVector[indexVariableMap[gateParts[c]]] == 1 for c in range(len(gateParts)-1)):
                lastIndex = indexVariableMap[gateParts[-1]]
                intermediateVector[lastIndex] = 1 - \
                    intermediateVector[lastIndex]

            count += 1

        # #print("after current gate, the intermediate vector: ",intermediateVector)
    # print("after processing through the circuit, final put vector: ",intermediateVector)
    return intermediateVector

def simulate_RGF_circuit(circuit, binaryVector, isFaulty=True):
    # vector processing throught the circuit
    gates = circuit["Gates"]

    # create a circuit with variables replaced with input values
    indexVariableMap = {}
    for i in range(len(binaryVector)):
        indexVariableMap[circuit["Variables"][i]] = i

    # print(indexVariableMap)

    intermediateVector = binaryVector.copy()

    # replace variables in gates with input values from binary vector
    count = 0
    for gate in gates:
        type = gate["gate"]
        gateParts = gate["vars"]

        # print("For gate level: ",count)
        # print("Input vector: ",intermediateVector)

        repeat_gate = False
        if isFaulty:
            faultModel = circuit.get("Fault Model")
            faultPosition = circuit.get(
                "Fault Position", circuit.get("Fault Positions"))

            # check if current gate is faulty (repeated gate)
            if faultModel == "RGF-Odd" and faultPosition is not None and count == faultPosition:
                # print(f"Repeating gate at level {count} due to {faultModel} fault")
                repeat_gate = True
                
            elif faultModel == "RGF-Even" and faultPosition is not None and count == faultPosition:
                # print(f"Repeating gate at level {count} due to {faultModel} fault")
                repeat_gate = False

        # ****WORKING FOR TOFFOLI GATE
        # process the vector for toffoli gate at current level
        if (type == "TOFFOLI"):

            if all(intermediateVector[indexVariableMap[gateParts[c]]] == 1 for c in range(len(gateParts)-1)):
                # #print("control activates the target bit")
                index = indexVariableMap[gateParts[-1]]
                intermediateVector[index] = 1 - intermediateVector[index]

            if repeat_gate:
                if all(intermediateVector[indexVariableMap[gateParts[c]]] == 1 for c in range(len(gateParts)-1)):
                    index = indexVariableMap[gateParts[-1]]
                    intermediateVector[index] = 1 - \
                        intermediateVector[index]

            count += 1

        # process the vector for toffoli gate at current level
        elif (type == "FREDKIN"):
            if all(intermediateVector[indexVariableMap[gateParts[c]]] == 1 for c in range(len(gateParts)-2)):
                # #print("control activates the target bit")
                index1 = indexVariableMap[gateParts[-2]]
                index2 = indexVariableMap[gateParts[-1]]

                # swap the target bits
                intermediateVector[index1], intermediateVector[index2] = intermediateVector[index2], intermediateVector[index1]

            if repeat_gate:
                if all(intermediateVector[indexVariableMap[gateParts[c]]] == 1 for c in range(len(gateParts)-2)):
                    index1 = indexVariableMap[gateParts[-2]]
                    index2 = indexVariableMap[gateParts[-1]]
                    intermediateVector[index1], intermediateVector[index2] = intermediateVector[index2], intermediateVector[index1]
            count += 1

        # process the vector for toffoli gate at current level
        if (type == "PERES"):

            # calculate the secondlast target bit
            secondLastIndex = indexVariableMap[gateParts[-2]]
            thirdLastIndex = indexVariableMap[gateParts[-3]]
            intermediateVector[secondLastIndex] = intermediateVector[thirdLastIndex] ^ intermediateVector[secondLastIndex]

            if all(intermediateVector[indexVariableMap[gateParts[c]]] == 1 for c in range(len(gateParts)-1)):
                lastIndex = indexVariableMap[gateParts[-1]]
                intermediateVector[lastIndex] = 1 - \
                    intermediateVector[lastIndex]

            if repeat_gate:
                secondLastIndex = indexVariableMap[gateParts[-2]]
                thirdLastIndex = indexVariableMap[gateParts[-3]]
                intermediateVector[secondLastIndex] = intermediateVector[thirdLastIndex] ^ intermediateVector[secondLastIndex] 
                
                if all(intermediateVector[indexVariableMap[gateParts[c]]] == 1 for c in range(len(gateParts)-1)):
                    lastIndex = indexVariableMap[gateParts[-1]]
                    intermediateVector[lastIndex] = 1 - \
                    intermediateVector[lastIndex]

                count += 1

        # print("after current gate, the intermediate vector: ",intermediateVector)
    # print("after processing through the circuit, final put vector: ",intermediateVector)
    return intermediateVector

def simulate_GAF_circuit(circuit, binaryVector, isFaulty=True):
    # vector processing throught the circuit
    gates = circuit["Gates"]

    # create a circuit with variables replaced with input values
    indexVariableMap = {}
    for i in range(len(binaryVector)):
        indexVariableMap[circuit["Variables"][i]] = i

    # print(indexVariableMap)

    intermediateVector = binaryVector.copy()

    # build a working gate list with the extra gate inserted (if faulty)
    working_gates = gates
    if isFaulty and circuit.get("Fault Model") == "GAF":
        faultPosition = circuit.get(
            "Fault Position", circuit.get("Fault Positions"))
        faultGate = circuit.get("Fault Gate")

        # normalize insert index
        insert_at = None
        if isinstance(faultPosition, int):
            insert_at = max(0, min(faultPosition + 1, len(gates)))
        elif isinstance(faultPosition, (list, tuple)) and faultPosition:
            # if list/tuple of levels, pick first for insertion
            first_pos = faultPosition[0]
            if isinstance(first_pos, int):
                insert_at = max(0, min(first_pos + 1, len(gates)))

        # choose the extra gate: explicit Fault Gate if provided, else duplicate gate at insert-1
        extra_gate = None
        if isinstance(faultGate, dict):
            extra_gate = faultGate
        elif insert_at is not None and insert_at - 1 >= 0 and insert_at - 1 < len(gates):
            extra_gate = gates[insert_at - 1]

        if extra_gate is not None and insert_at is not None:
            # print(f"Inserting extra gate at level {insert_at} due to GAF fault")
            working_gates = gates[:insert_at] + \
                [extra_gate] + gates[insert_at:]

    # replace variables in gates with input values from binary vector
    count = 0
    for gate in working_gates:
        type = gate["gate"]
        gateParts = gate["vars"]

        # print("For gate level: ",count)
        # print("Input vector: ",intermediateVector)

        # ****WORKING FOR TOFFOLI GATE
        # process the vector for toffoli gate at current level
        if (type == "TOFFOLI"):

            if all(intermediateVector[indexVariableMap[gateParts[c]]] == 1 for c in range(len(gateParts)-1)):
                # #print("control activates the target bit")
                index = indexVariableMap[gateParts[-1]]
                intermediateVector[index] = 1 - intermediateVector[index]

            count += 1

        # process the vector for toffoli gate at current level
        elif (type == "FREDKIN"):
            if all(intermediateVector[indexVariableMap[gateParts[c]]] == 1 for c in range(len(gateParts)-2)):
                # #print("control activates the target bit")
                index1 = indexVariableMap[gateParts[-2]]
                index2 = indexVariableMap[gateParts[-1]]

                # swap the target bits
                intermediateVector[index1], intermediateVector[index2] = intermediateVector[index2], intermediateVector[index1]
            count += 1

        # process the vector for toffoli gate at current level
        if (type == "PERES"):

            # calculate the secondlast target bit
            secondLastIndex = indexVariableMap[gateParts[-2]]
            thirdLastIndex = indexVariableMap[gateParts[-3]]
            intermediateVector[secondLastIndex] = intermediateVector[thirdLastIndex] ^ intermediateVector[secondLastIndex]

            if all(intermediateVector[indexVariableMap[gateParts[c]]] == 1 for c in range(len(gateParts)-1)):
                lastIndex = indexVariableMap[gateParts[-1]]
                intermediateVector[lastIndex] = 1 - \
                    intermediateVector[lastIndex]

            count += 1

        # #print("after current gate, the intermediate vector: ",intermediateVector)
    # print("after processing through the circuit, final put vector: ",intermediateVector)
    return intermediateVector

def simulate_CAF_circuit(circuit, binaryVector, isFaulty=True):
    # vector processing throught the circuit
    gates = circuit["Gates"]

    # create a circuit with variables replaced with input values
    indexVariableMap = {}
    for i in range(len(binaryVector)):
        indexVariableMap[circuit["Variables"][i]] = i

    # print(indexVariableMap)

    intermediateVector = binaryVector.copy()

    # replace variables in gates with input values from binary vector
    count = 0
    for gate in gates:
        type = gate["gate"]
        gateParts = gate["vars"].copy()

        # print("For gate level: ",count)
        # print("Input vector: ",intermediateVector)

        # CAF: add extra control variable to a gate (if available)
        if isFaulty:
            faultModel = circuit.get("Fault Model")
            faultPosition = circuit.get(
                "Fault Position", circuit.get("Fault Positions"))

            if faultModel == "CAF" and faultPosition is not None and count == faultPosition[0]:
                extra_control = faultPosition[1]
                # only add if this gate has fewer vars than total lines and var not already present
                if extra_control not in gateParts and len(gateParts) < circuit["No of Lines"]:
                    # print(f"Adding extra control {extra_control} to gate at level {count}")
                    # insert extra control before target(s)
                    if type == "FREDKIN":
                        gateParts = gateParts[:-2] + \
                            [extra_control] + gateParts[-2:]
                    else:
                        gateParts = gateParts[:-1] + \
                            [extra_control] + gateParts[-1:]

        # ****WORKING FOR TOFFOLI GATE
        # process the vector for toffoli gate at current level
        if (type == "TOFFOLI"):

            if all(intermediateVector[indexVariableMap[gateParts[c]]] == 1 for c in range(len(gateParts)-1)):
                # #print("control activates the target bit")
                index = indexVariableMap[gateParts[-1]]
                intermediateVector[index] = 1 - intermediateVector[index]

            count += 1

        # process the vector for toffoli gate at current level
        elif (type == "FREDKIN"):
            if all(intermediateVector[indexVariableMap[gateParts[c]]] == 1 for c in range(len(gateParts)-2)):
                # #print("control activates the target bit")
                index1 = indexVariableMap[gateParts[-2]]
                index2 = indexVariableMap[gateParts[-1]]

                # swap the target bits
                intermediateVector[index1], intermediateVector[index2] = intermediateVector[index2], intermediateVector[index1]
            count += 1

        # process the vector for toffoli gate at current level
        if (type == "PERES"):

            # calculate the secondlast target bit
            secondLastIndex = indexVariableMap[gateParts[-2]]
            thirdLastIndex = indexVariableMap[gateParts[-3]]
            intermediateVector[secondLastIndex] = intermediateVector[thirdLastIndex] ^ intermediateVector[secondLastIndex]

            if all(intermediateVector[indexVariableMap[gateParts[c]]] == 1 for c in range(len(gateParts)-1)):
                lastIndex = indexVariableMap[gateParts[-1]]
                intermediateVector[lastIndex] = 1 - \
                    intermediateVector[lastIndex]

            count += 1

        # print("after current gate, the intermediate vector: ",intermediateVector)
    # print("after processing through the circuit, final put vector: ",intermediateVector)
    return intermediateVector

def simulate_BF_circuit(circuit, binaryVector, isFaulty=True):
    # vector processing throught the circuit
    gates = circuit["Gates"]

    # create a circuit with variables replaced with input values
    indexVariableMap = {}
    for i in range(len(binaryVector)):
        indexVariableMap[circuit["Variables"][i]] = i

    # print(indexVariableMap)

    intermediateVector = binaryVector.copy()

    def apply_bridging_fault(intermediateVector, fault):
        # fault tuple: (gate_index, wire1, wire2, mode)
        _, wire1, wire2, mode = fault
        idx1 = indexVariableMap[wire1]
        idx2 = indexVariableMap[wire2]
        if mode == "AND-wired":
            wired_val = intermediateVector[idx1] & intermediateVector[idx2]
        else:
            wired_val = intermediateVector[idx1] | intermediateVector[idx2]
        intermediateVector[idx1] = wired_val
        intermediateVector[idx2] = wired_val

    # replace variables in gates with input values from binary vector
    count = 0
    for gate in gates:
        type = gate["gate"]
        gateParts = gate["vars"]

        # print("For gate level: ",count)
        # print("Input vector: ",intermediateVector)

        if isFaulty:
            faultModel = circuit.get("Fault Model")
            faultPosition = circuit.get(
                "Fault Position", circuit.get("Fault Positions"))

            # apply bridging fault at this level
            if faultModel == "BF" and faultPosition is not None and count == faultPosition[0]:
                # print(f"Applying bridging fault at level {count}: {faultPosition[1]}-{faultPosition[2]} {faultPosition[3]}")
                apply_bridging_fault(intermediateVector, faultPosition)

        # ****WORKING FOR TOFFOLI GATE
        # process the vector for toffoli gate at current level
        if (type == "TOFFOLI"):

            if all(intermediateVector[indexVariableMap[gateParts[c]]] == 1 for c in range(len(gateParts)-1)):
                # #print("control activates the target bit")
                index = indexVariableMap[gateParts[-1]]
                intermediateVector[index] = 1 - intermediateVector[index]

            count += 1

        # process the vector for toffoli gate at current level
        elif (type == "FREDKIN"):
            if all(intermediateVector[indexVariableMap[gateParts[c]]] == 1 for c in range(len(gateParts)-2)):
                # #print("control activates the target bit")
                index1 = indexVariableMap[gateParts[-2]]
                index2 = indexVariableMap[gateParts[-1]]

                # swap the target bits
                intermediateVector[index1], intermediateVector[index2] = intermediateVector[index2], intermediateVector[index1]
            count += 1

        # process the vector for toffoli gate at current level
        if (type == "PERES"):

            # calculate the secondlast target bit
            secondLastIndex = indexVariableMap[gateParts[-2]]
            thirdLastIndex = indexVariableMap[gateParts[-3]]
            intermediateVector[secondLastIndex] = intermediateVector[thirdLastIndex] ^ intermediateVector[secondLastIndex]

            if all(intermediateVector[indexVariableMap[gateParts[c]]] == 1 for c in range(len(gateParts)-1)):
                lastIndex = indexVariableMap[gateParts[-1]]
                intermediateVector[lastIndex] = 1 - \
                    intermediateVector[lastIndex]

            count += 1

        # #print("after current gate, the intermediate vector: ",intermediateVector)
    # print("after processing through the circuit, final put vector: ",intermediateVector)
    return intermediateVector

    # taking vector input and converting integer to binary

    # def print_circuit_representation(circuit, isFaulty=False):
    #     if isFaulty:
    #         faultPosition = circuit["Fault Position"]
    #         faultModel = circuit["Fault Model"]

    #         for i, gate in enumerate(circuit["Gates"]):
    #             print(f"Gate {i}: ", end=" ")
    #             for j, var in enumerate(gate["vars"]):
    #                 if (i, var) == faultPosition:
    #                     if faultModel == "SA0":
    #                         print(f"{var}(0)", end=" ")
    #                     elif faultModel == "SA1":
    #                         print(f"{var}(1)", end=" ")
    #                 else:
    #                     print(f"{var}", end=" ")
    #             print()

def faultCov_for_SAF(circuit, inputVec, fault_model):
    # for each gate in gates
    # for each control point(var in vars)
    level = None
    wire = None
    faultPosition = (level, wire)
    faultyCircuit = circuit.copy()
    
    cumulatedFaults = 0
    detectedFaults = []
    
    faultyCircuit["Fault Model"] = fault_model

    faultFreeOutput = simulate_circuit(circuit, inputVec)
    
    
    for i, gate in enumerate(circuit["Gates"]):
        # #print(gate)
        for j, var in enumerate(gate["vars"]):
            # #print(var)
            faultPosition = (i, var)
            cumulatedFaults += 1
            # print("SA-0 at level(Gate)", i,"wire(variable)", j,"(", var,")")
            faultyCircuit["Fault Position"] = faultPosition
            
            faultyOutput = simulate_SAF_circuit(
                faultyCircuit, inputVec, True)
            if faultyOutput != faultFreeOutput:
                detectedFaults.append(f"Level_{i}_Wire_{j}")

    return cumulatedFaults, detectedFaults 

def faultCov_for_SMGF(circuit, inputVec):

    # for each gate in gates
    # for each control point(var in vars)
    level = None
    faultyCircuit = circuit.copy()
    faultyCircuit["Fault Model"] = "SMGF"
    cumulatedFaults = 0
    detectedFaults = []

    faultFreeOutput = simulate_circuit(circuit, inputVec)

    
    for i, gate in enumerate(circuit["Gates"]):
        # skip gate
        faultPosition = []
        faultPosition.append(i)
        faultyCircuit["Fault Position"] = faultPosition
        # print("SMGF at level(Gate)", i)
        
        cumulatedFaults += 1
        
        faultyOutput = simulate_SMGF_circuit(faultyCircuit, inputVec, True)
        
        if faultyOutput != faultFreeOutput:
            detectedFaults.append(f'Level_{i}')

    return cumulatedFaults, detectedFaults

def faultCov_for_MMGF(circuit, inputVec):

    # for each gate in gates
    # for each control point(var in vars)
    faultPositions = []
    faultyCircuit = circuit.copy()
    faultyCircuit["Fault Model"] = "MMGF"
    
    cumulatedFaults = 0
    detectedFaults = []
    
    # for different no of missing gates starting from single missing, double missing to n-1 missing
    noLevels = circuit["No of Gates"]
    maxFaults = circuit["No of Gates"]-1
    # maxFaults = 5
    # singleton sets

    answer = []
    elementCount = 0
    
    faultFreeOutput = simulate_circuit(circuit, inputVec)
    
    
    for setSize in range(maxFaults):

        mset = answer.copy()

        while elementCount <= setSize:

            if not mset:
                for index in range(noLevels):
                    iset = []
                    iset.append(index)
                    mset.append(iset)
                    faultyCircuit["Fault Position"] = iset
                    # print("MMGF faults at levels(Gate)",faultyCircuit["Fault Position"])
                    cumulatedFaults += 1

                    faultyOutput = simulate_MMGF_circuit(
                        faultyCircuit, inputVec, True)
                    if faultyOutput != faultFreeOutput:
                        detectedFaults.append(f"Gates_{iset}")

            elif mset:
                for index, subset in enumerate(mset):
                    if (len(subset) == setSize):

                        nextIndex = subset[-1]
                        for i in range(nextIndex+1, noLevels):
                            iset = subset.copy()
                            iset.append(i)
                            mset.append(iset)
                            faultyCircuit["Fault Position"] = iset
                            # print("MMGF faults at levels(Gate)",faultyCircuit["Fault Position"])
                            cumulatedFaults += 1

                            
                            faultyOutput = simulate_MMGF_circuit(
                                faultyCircuit, inputVec, True)
                            if faultyOutput != faultFreeOutput:
                                detectedFaults.append(f"Gates_{iset}")
            elementCount += 1
        setSize += 1
        answer = mset.copy()
        
    return cumulatedFaults, detectedFaults

def faultCov_for_PMGF(circuit, inputVec):

    level = None
    wires = []
    faultyCircuit = circuit.copy()
    faultyCircuit["Fault Model"] = "PMGF"
    noLines = circuit["No of Lines"]
    maxFaults = circuit["No of Lines"]-1
    cumulatedFaults = 0

    faultFreeOutput = simulate_circuit(circuit, inputVec)
    
    # outer for loop for iterating through the gates
    for i, gate in enumerate(circuit["Gates"]):
        # inner for loop to miss the partial control bits with all the possible combinations
        
        detectedFaults = []
        # for different no of missing gates starting from single missing, double missing to n-1 missing
        answer = []
        elementCount = 0

        for setSize in range(maxFaults):

            mset = answer.copy()
            while elementCount <= setSize:

                if not mset:
                    for wire, var in enumerate(gate["vars"]):
                        iset = []
                        iset.append(wire)
                        mset.append(iset)
                        wires = iset
                        level = i

                        faultyCircuit["Fault Position"] = (level, wires)
                        # print("PMGF faults for gate (", level,
                        #       ") at control(var) ", wires)
                        cumulatedFaults += 1

                        
                        faultyOutput = simulate_PMGF_circuit(
                            faultyCircuit, inputVec, True)
                        if faultyOutput != faultFreeOutput:
                            detectedFaults.append(f"Level_{level}_Wires_{wires}")

                elif mset:
                    for index, subset in enumerate(mset):
                        if (len(subset) == setSize):

                            nextIndex = subset[-1]
                            for i in range(nextIndex+1, len(gate["vars"])):
                                iset = subset.copy()
                                iset.append(i)
                                mset.append(iset)
                                wires = iset
                                level = i

                                faultyCircuit["Fault Position"] = (
                                    level, wires)
                                # print("PMGF faults for gate (", level,
                                #       ") at control(var) ", wires)
                                cumulatedFaults += 1

                                if faultyOutput != faultFreeOutput:
                                    detectedFaults.append(f"Level_{level}_Wires_{wires}")

                elementCount += 1
            setSize += 1
            answer = mset.copy()
            
    return cumulatedFaults, detectedFaults

def faultCov_for_RGF(circuit, inputVec, n="Odd"):
    # for each gate in gates repeate the gates
    level = None
    faultyCircuit = circuit.copy()
    faultyCircuit["Fault Model"] = "RGF-Even" if n == "Even" else "RGF-Odd"
    cumulatedFaults = 0
    detectedFaults = []
    
    faultFreeOutput = simulate_circuit(circuit, inputVec)
    
    
    for i, gate in enumerate(circuit["Gates"]):
        # skip gate
        faultyCircuit["Fault Position"] = i
        # print("RGF at level(Gate)", i)
        cumulatedFaults += 1

        
        faultyOutput = simulate_RGF_circuit(faultyCircuit, inputVec, True)
        if faultyOutput != faultFreeOutput:
            detectedFaults.append(f"Gate_{i}_{n}")

    return cumulatedFaults, detectedFaults

def faultCov_for_GAF(circuit, inputVec):
    # add extra gate after any one gate in the circuit
    level = None
    faultyCircuit = circuit.copy()
    faultyCircuit["Fault Model"] = "GAF"
    
    cumulatedFaults = 0
    detectedFaults = []
    
    faultFreeOutput = simulate_circuit(circuit, inputVec)
    
    
    for i in range(len(circuit["Gates"])+1):
        # add gate
        faultyCircuit["Fault Position"] = i-1
        # print("GAF at level(Gate)", i-1)
        cumulatedFaults += 1

        
        faultyOutput = simulate_GAF_circuit(faultyCircuit, inputVec, True)
        if faultyOutput != faultFreeOutput:
            detectedFaults.append(f"Level_{i}")

    return cumulatedFaults, detectedFaults


# here control can occur even if the gate is already full
def faultCov_for_CAF(circuit, inputVec):
    # add extra control in any one gate in the circuit
    level = None
    wire = None
    faultPosition = (level, wire)
    faultyCircuit = circuit.copy()
    faultyCircuit["Fault Model"] = "CAF"
    cumulatedFaults = 0
    detectedFaults= []
    
    faultFreeOutput = simulate_circuit(circuit, inputVec)
    
    

    for i, gate in enumerate(circuit["Gates"]):
        for j, var in enumerate(circuit["Variables"]):
            # skip gate
            if var in gate["vars"]:
                continue
            faultPosition = (i, var)
            faultyCircuit["Fault Position"] = faultPosition
            # print("CAF at level(Gate)",
            #       faultPosition[0], "wire(variable)", faultPosition[1])
            cumulatedFaults += 1

            
            faultyOutput = simulate_CAF_circuit(
                faultyCircuit, inputVec, True)
            if faultyOutput != faultFreeOutput:
                detectedFaults.append(f"Gate_{i}_Wire_{j}")

    return cumulatedFaults, detectedFaults


def faultCov_for_BF(circuit, inputVec):
    # for each gate in gates
    # for each pair of wires
    # induce "AND-wired" and "OR-wired" bridging faults
    faultyCircuit = circuit.copy()
    faultyCircuit["Fault Model"] = "BF"
    
    cumulatedFaults = 0
    detectedFaults = []
    
    faultFreeOutput = simulate_circuit(circuit, inputVec)
    
    
    variables = circuit["Variables"]
    for i, gate in enumerate(circuit["Gates"]):
        for j in range(len(variables)):
            for k in range(j+1, len(variables)):
                wire1 = variables[j]
                wire2 = variables[k]

                # AND-wired bridging fault
                faultPosition = (i, wire1, wire2, "AND-wired")
                faultyCircuit["Fault Position"] = faultPosition
                # print("Bridging Fault (AND-wired) at level(Gate)", faultPosition[0],"between wires(variables)", faultPosition[1], "and", faultPosition[2])
                cumulatedFaults += 1
                
                faultyOutput = simulate_BF_circuit(
                    faultyCircuit, inputVec, True)
                if faultyOutput != faultFreeOutput:
                    detectedFaults.append(f"Level_{i}_AND_Wires_{wire1}_{wire2}")

                # OR-wired bridging fault
                faultPosition = (i, wire1, wire2, "OR-wired")
                faultyCircuit["Fault Position"] = faultPosition
                # print("Bridging Fault (OR-wired) at level(Gate)", faultPosition[0],"between wires(variables)", faultPosition[1], "and", faultPosition[2])
                cumulatedFaults += 1

                faultyOutput = simulate_BF_circuit(
                    faultyCircuit, inputVec, True)
                if faultyOutput != faultFreeOutput:
                    detectedFaults.append(f"Level_{i}_OR_Wires_{wire1}_{wire2}")

    # print("BF count:", faultCount, "Detected Faults:", cumulativeFaults)
    # print("Fault Cov for BF==>", (cumulativeFaults/faultCount)*100)
    return cumulatedFaults, detectedFaults

def faultCov_for_MBF(circuit, inputVec, max_faults_per_gate=2):
    # for each gate in gates
    # consider multiple simultaneous bridging faults
    # induce "AND-wired" and "OR-wired" bridging faults

    faultyCircuit = circuit.copy()
    faultyCircuit["Fault Model"] = "Multiple BF"
    cumulatedFaults = 0
    detectedFaults = []
    
    
    faultFreeOutput = simulate_circuit(
                                circuit, inputVec)
    
    variables = circuit["Variables"]
    for i, gate in enumerate(circuit["Gates"]):
        # build all possible single bridging faults first
        single_faults = []
        for j in range(len(variables)):
            for k in range(j+1, len(variables)):
                wire1 = variables[j]
                wire2 = variables[k]
                single_faults.append((wire1, wire2, "AND-wired"))
                single_faults.append((wire1, wire2, "OR-wired"))

        # cap to avoid combinational explosion unless user asks otherwise
        if max_faults_per_gate is None:
            max_faults = len(single_faults)
        else:
            max_faults = min(max_faults_per_gate, len(single_faults))

        # generate combinations of multiple faults (size 2..max_faults)
        for set_size in range(2, max_faults + 1):
            answer = []
            elementCount = 0
            mset = []

            while elementCount <= set_size:
                if not mset:
                    for index in range(len(single_faults)):
                        iset = []
                        iset.append(index)
                        mset.append(iset)
                        if len(iset) == set_size:
                            faultPosition = [(i, *single_faults[x])
                                             for x in iset]
                            faultyCircuit["Fault Position"] = faultPosition
                            # print("Multiple BF at level(Gate)", i, "faults", faultPosition)
                            cumulatedFaults += 1

                            
                            faultyOutput = simulate_BF_circuit(
                                faultyCircuit, inputVec, True)
                            if faultyOutput != faultFreeOutput:
                                detectedFaults.append(f"Level_{i}_OR_Wires_{iset}")

                else:
                    for subset in mset:
                        if len(subset) == set_size:
                            continue
                        nextIndex = subset[-1]
                        for idx in range(nextIndex+1, len(single_faults)):
                            iset = subset.copy()
                            iset.append(idx)
                            if len(iset) == set_size:
                                faultPosition = [
                                    (i, *single_faults[x]) for x in iset]
                                faultyCircuit["Fault Position"] = faultPosition
                                # print("Multiple BF at level(Gate)", i, "faults", faultPosition)
                                cumulatedFaults += 1

                            
                                faultyOutput = simulate_MBF_circuit(
                                    faultyCircuit, inputVec, True)
                                if faultyOutput != faultFreeOutput:
                                    detectedFaults.append(f"Level_{i}_OR_Wires_{iset}")

                            mset.append(iset)
                elementCount += 1
                
    return cumulatedFaults, detectedFaults

    # return (cumulativeFaults/faultCount)*100

def calculate_FC_for_fault_model(circuit, testVec, fault_model):
    # can the following loop for all the vectors in the population
    # testVec = generate_random_vector(circuit)
    # SAF
    if fault_model in ["SA-0", "SA-1"]:
        return faultCov_for_SAF(circuit, testVec, fault_model)

    # SMGF FAULT
    elif fault_model == "SMGF":
        return faultCov_for_SMGF(circuit, testVec)

    # PMGF FAULT
    elif fault_model == "PMGF":
        return faultCov_for_PMGF(circuit, testVec)

    # MMGF FAULT
    elif fault_model == "MMGF":
        return faultCov_for_MMGF(circuit, testVec)

    # RGF FAULT
    elif fault_model == "RGF":
        return faultCov_for_RGF(circuit, testVec, "Odd")

    # GAF FAULT
    elif fault_model == "GAF":
        return faultCov_for_GAF(circuit, testVec)

    # CAF FAULT
    elif fault_model == "CAF":
        return faultCov_for_CAF(circuit, testVec)

    # BF FAULT
    elif fault_model == "BF":
        return faultCov_for_BF(circuit, testVec)

    # MBF Fault
    elif fault_model == "MBF":
        return faultCov_for_MBF(circuit, testVec)


def get_all_faulty_outputs(circuit, testVec, fault_model):
    
    faultyOutputs = []
    # faulty op for fault at loc i
    
    if fault_model in ["SA-0", "SA-1"]:
        return faultCov_for_SAF(circuit, testVec, fault_model)

    # SMGF FAULT
    elif fault_model == "SMGF":
        return faultCov_for_SMGF(circuit, testVec)

    # PMGF FAULT
    elif fault_model == "PMGF":
        return faultCov_for_PMGF(circuit, testVec)

    # MMGF FAULT
    elif fault_model == "MMGF":
        return faultCov_for_MMGF(circuit, testVec)

    # RGF FAULT
    elif fault_model == "RGF":
        return faultCov_for_RGF(circuit, testVec, "Odd")

    # GAF FAULT
    elif fault_model == "GAF":
        return faultCov_for_GAF(circuit, testVec)

    # CAF FAULT
    elif fault_model == "CAF":
        return faultCov_for_CAF(circuit, testVec)

    # BF FAULT
    elif fault_model == "BF":
        return faultCov_for_BF(circuit, testVec)

    # MBF Fault
    elif fault_model == "MBF":
        return faultCov_for_MBF(circuit, testVec)
    
    
    
    return faultyOutputs


# GAforSMGF = GeneticAlgorithm()

# GeneticAlgorithm.stage_ii_random_selection()