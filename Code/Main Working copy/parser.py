import re
import pandas as pd
import json
import os
from typing import List, Tuple, Dict, Any


# circuit parser class

class RealFileParser:
    """Parser for RevLib .real format files"""
   
    def __init__(self):
        self.reset()

    # ==============================
    # RESET PARSER STATE
    # ==============================
    def reset(self):
        """Reset parser state"""
     
        self.type = ""
        self.circuitName =""
        self.version = None
        self.noOfLines = 0
        self.noOfGates = 0
        self.variables = []
        self.inputs = []
        self.outputs = []
        self.constants = []
        self.garbage = []
        self.gates = []
        self.compiled_representation = []
        self.metadata = {}

    # ==============================
    # FILE PARSER
    # ==============================
    def parse_file(self, filepath: str) -> Dict[str, Any]:

        self.reset()

        self.circuitName = os.path.splitext(os.path.basename(filepath))[0]

        with open(filepath, "r") as f:
            lines = f.readlines()

        in_circuit = False
        detected_libraries = set()

        for line in lines:
            line = line.strip()

            if not line:
                continue

            # --------------------------
            # Comments
            # --------------------------
            if line.startswith("#"):
                if line.startswith("# Used Library:"):
                    self.type = line.split("Used Library:")[1].strip().split()[0]
                continue

            # --------------------------
            # Header Parsing
            # --------------------------
            if line.startswith(".version"):
                self.version = line.split()[1]

            elif line.startswith(".numvars"):
                self.noOfLines = int(line.split()[1])

            elif line.startswith(".variables"):
                self.variables = line.split()[1:]

            elif line.startswith(".inputs"):
                self.inputs = line.split()[1:]

            elif line.startswith(".outputs"):
                self.outputs = line.split()[1:]

            elif line.startswith(".constants"):
                self.constants = line.split()[1:]

            elif line.startswith(".garbage"):
                self.garbage = line.split()[1:]

            elif line.startswith(".begin"):
                in_circuit = True

            elif line.startswith(".end"):
                in_circuit = False

            # --------------------------
            # Gate Parsing
            # --------------------------
            elif in_circuit:
                gate, lib = self._parse_gate(line)
                if gate:
                    self.gates.append(gate)
                if lib:
                    detected_libraries.add(lib)

        self.noOfGates = len(self.gates)

        # Auto-detect library if not given
        if not self.type and detected_libraries:
            self.type = " ".join(sorted(detected_libraries))

        # create bitmask compiled representation of circuit
        var_index = {v: i for i, v in enumerate(self.variables)}

        for g in self.gates:

            idxs = [var_index[v] for v in g["vars"]]
            bits = [1 << i for i in idxs]

            if g["gate"] == "TOFFOLI":
                control_mask = 0
                for b in bits[:-1]:
                    control_mask |= b
                target_bit = bits[-1]
                self.compiled_representation.append(("TOFFOLI", control_mask, target_bit))

            elif g["gate"] == "FREDKIN":
                control_mask = 0
                for b in bits[:-2]:
                    control_mask |= b
                swap_mask = bits[-2] | bits[-1]
                self.compiled_representation.append(("FREDKIN", control_mask, swap_mask))

            elif g["gate"] == "PERES":
                self.compiled_representation.append(("PERES", bits[0], bits[1], bits[2]))
        
        
        return self._create_circuit_dict()

    # ==============================
    # GATE PARSER
    # ==============================
    def _parse_gate(self, gate_line: str):

        parts = gate_line.split()
        if not parts:
            return None, None

        gate_type = parts[0].lower()
        gate_vars = parts[1:]

        # --------------------------
        # TOFFOLI
        # --------------------------
        if gate_type.startswith("t"):
            return (
                {"gate": "TOFFOLI", "vars": gate_vars},
                "MCT"
            )

        # --------------------------
        # FREDKIN
        # --------------------------
        elif gate_type.startswith("f"):
            return (
                {"gate": "FREDKIN", "vars": gate_vars},
                "MCF"
            )


        # --------------------------
        # PERES
        # --------------------------
        elif gate_type.startswith("p"):
            return (
                {"gate": "PERES", "vars": gate_vars},
                "P"
            )

        return None, None

    # ==============================
    # ORIGINAL DICTIONARY FORMAT
    # ==============================
    def _create_circuit_dict(self) -> Dict[str, Any]:
        """
        Create a dictionary compatible with your existing dataset format
        """
      
        return {
            "Library Type": self.type,
            "Circuit Name": self.circuitName,
            "No of Lines": self.noOfLines,
            "No of Gates": self.noOfGates,
            "Variables": self.variables,
            "Inputs": self.inputs,
            "Outputs": self.outputs,
            "Constants": self.constants,
            "Garbage": self.garbage,
            "Gates": self.gates,
            "Compiled Rep": self.compiled_representation,
            "Metadata": {
                "Version": self.version,
                "format": "real"
            }
        }

    # ==============================
    # INTERNAL TUPLE FORMAT
    # ==============================
    # def to_internal_circuit(self, circuit_dict: Dict[str, Any]) -> List[Tuple]:
    #     """
    #     Convert parsed circuit to internal format used by your algorithm
    #     (Same as convert_dataset_gates function)
    #     """
        
    #     variables = circuit_dict["Variables"]
    #     gates = circuit_dict["Gates"]

    #     var_map = {v: i for i, v in enumerate(variables)}
    #     circuit = []

    #     for g in gates:
    #         gate_name = g["gate"]
    #         idxs = [var_map[n] for n in g["vars"]]

    #         if not idxs:
    #             continue

    #         if gate_name == "TOFFOLI":
    #             controls = idxs[:-1]
    #             target = idxs[-1]
    #             circuit.append(("TOFFOLI", controls, target))

    #         elif gate_name == "FREDKIN":
    #             controls = idxs[:-2]
    #             s1 = idxs[-2]
    #             s2 = idxs[-1]
    #             circuit.append(("FREDKIN", controls, s1, s2))

    #         elif gate_name == "PERES":
    #             controls = idxs[:-1]
    #             target = idxs[-1]
    #             circuit.append(("PERES", controls, target))


    #     return circuit
    
    # # ==============================
    # # 🚀 HIGH PERFORMANCE BITMASK COMPILER
    # # ==============================
    # def compile_to_bitmask(self, circuit_dict: Dict[str, Any]):

    #     variables = circuit_dict["Variables"]
    #     gates = circuit_dict["Gates"]

    #     var_index = {v: i for i, v in enumerate(variables)}

    #     compiled = []
    #     n_lines = len(variables)

    #     for g in gates:

    #         idxs = [var_index[v] for v in g["vars"]]
    #         bits = [1 << i for i in idxs]

    #         if g["gate"] == "TOFFOLI":
    #             control_mask = 0
    #             for b in bits[:-1]:
    #                 control_mask |= b
    #             target_bit = bits[-1]
    #             compiled.append(("T", control_mask, target_bit))

    #         elif g["gate"] == "FREDKIN":
    #             control_mask = 0
    #             for b in bits[:-2]:
    #                 control_mask |= b
    #             swap_mask = bits[-2] | bits[-1]
    #             compiled.append(("F", control_mask, swap_mask))

    #         elif g["gate"] == "PERES":
    #             compiled.append(("P", bits[0], bits[1], bits[2]))

    #     return compiled


