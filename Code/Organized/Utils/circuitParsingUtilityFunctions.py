import os
import glob
import json
import ast
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_GATE_LIBRARY_MAP = {
    't': 'MCT',
    'f': 'MCF',
    'p': 'P',
}

_GATE_TYPE_MAP = {
    't': 'TOFFOLI',
    'f': 'FREDKIN',
    'p': 'PERES',
}


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class RealFileParser:
    """Parser for RevLib .real format circuit files."""

    def __init__(self):
        self._reset()

    def _reset(self) -> None:
        """Reset all parser state before processing a new file."""
        self.type: str = ""
        self.circuit_name: str = ""
        self.version: Optional[str] = None
        self.no_of_lines: int = 0
        self.no_of_gates: int = 0
        self.variables: List[str] = []
        self.inputs: List[str] = []
        self.outputs: List[str] = []
        self.constants: str = ""
        self.garbage: str = ""
        self.gates: List[Dict[str, Any]] = []
        self._libraries: set = set()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse_file(self, filepath: str) -> Dict[str, Any]:
        """
        Parse a .real file and return a circuit dictionary.

        Args:
            filepath: Path to the .real file.

        Returns:
            Dictionary containing circuit information.
        """
        self._reset()
        self.circuit_name = os.path.splitext(os.path.basename(filepath))[0]

        with open(filepath, 'r') as f:
            lines = f.readlines()

        in_circuit = False

        for line in lines:
            line = line.strip()

            if line.startswith('# Used Library:'):
                self.type = line.split("Used Library:")[1].strip().split()[0]
                continue

            if not line or line.startswith('#'):
                continue

            if line.startswith('.version'):
                self.version = line.split()[1]
            elif line.startswith('.numvars'):
                self.no_of_lines = int(line.split()[1])
            elif line.startswith('.variables'):
                self.variables = line.split()[1:]
            elif line.startswith('.inputs'):
                self.inputs = line.split()[1:]
            elif line.startswith('.outputs'):
                self.outputs = line.split()[1:]
            elif line.startswith('.constants'):
                self.constants = line.split()[1]
            elif line.startswith('.garbage'):
                self.garbage = line.split()[1]
            elif line.startswith('.begin'):
                in_circuit = True
            elif line.startswith('.end'):
                in_circuit = False
            elif in_circuit:
                gate = self._parse_gate(line)
                if gate:
                    self.gates.append(gate)

        self.no_of_gates = len(self.gates)

        # Infer library type from observed gate types if not declared in header
        if not self.type and self._libraries:
            self.type = " ".join(sorted(self._libraries))

        return self._build_circuit_dict()

    def to_internal_circuit(self, circuit_dict: Dict[str, Any]) -> List[Tuple]:
        """
        Convert a parsed circuit dict to the internal tuple-based format.

        Args:
            circuit_dict: Output of parse_file().

        Returns:
            List of gate tuples: ("TOFFOLI", controls, target) or
            ("FREDKIN", (controls, swap1, swap2)).
        """
        variables = circuit_dict["Variables"]
        if isinstance(variables, str):
            variables = ast.literal_eval(variables)

        var_map = {v: i for i, v in enumerate(variables)}
        circuit = []

        for g in circuit_dict["Gates"]:
            if not isinstance(g, dict) or "gate" not in g or "vars" not in g:
                continue

            gate_name = g["gate"].upper()
            idxs = [var_map[n] for n in g["vars"] if n in var_map]

            if not idxs:
                continue

            if gate_name == "TOFFOLI":
                controls = idxs[:-1]
                target = idxs[-1]
                circuit.append(("TOFFOLI", controls, target))

            elif gate_name == "FREDKIN":
                if len(idxs) < 2:
                    continue
                controls = idxs[:-2]
                circuit.append(("FREDKIN", (controls, idxs[-2], idxs[-1])))

        return circuit

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _parse_gate(self, gate_line: str) -> Optional[Dict[str, Any]]:
        """
        Parse a single gate line into a gate dictionary.

        Supported formats:
            t<n> var1 [var2 ...]  → Toffoli (MCT)
            f<n> var1 [var2 ...]  → Fredkin (MCF)
            p<n> var1 var2 var3   → Peres
        """
        parts = gate_line.split()
        if not parts:
            return None

        prefix = parts[0][0].lower()
        gate_type = _GATE_TYPE_MAP.get(prefix)

        if gate_type is None:
            return None

        self._libraries.add(_GATE_LIBRARY_MAP[prefix])
        return {"gate": gate_type, "vars": parts[1:]}

    def _build_circuit_dict(self) -> Dict[str, Any]:
        """Assemble the final circuit dictionary from parsed state."""
        return {
            "Library Type": self.type,
            "Circuit Name": self.circuit_name,
            "No of Lines": self.no_of_lines,
            "No of Gates": self.no_of_gates,
            "Variables": self.variables,
            "Inputs": self.inputs,
            "Outputs": self.outputs,
            "Constants": self.constants,
            "Garbage": self.garbage,
            "Gates": self.gates,
            "Metadata": {
                "Version": self.version,
                "format": "real",
            },
        }


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------

def parse_real_file(filepath: str) -> Dict[str, Any]:
    """
    Parse a single .real file.

    Args:
        filepath: Path to the .real file.

    Returns:
        Circuit dictionary.
    """
    return RealFileParser().parse_file(filepath)


def parse_real_directory(
    directory: str, pattern: str = "*.real"
) -> List[Dict[str, Any]]:
    """
    Parse all .real files in a directory matching `pattern`.

    Args:
        directory: Directory containing .real files.
        pattern:   Glob pattern for file matching.

    Returns:
        List of circuit dictionaries (files that fail are skipped with a warning).
    """
    parser = RealFileParser()
    circuits = []

    for filepath in sorted(glob.glob(os.path.join(directory, pattern))):
        try:
            circuits.append(parser.parse_file(filepath))
        except Exception as exc:
            print(f"✗ Error parsing {filepath}: {exc}")

    return circuits


def real_circuits_to_dataframe(circuits: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Convert a list of circuit dictionaries to a pandas DataFrame.

    Args:
        circuits: List of parsed circuit dictionaries.

    Returns:
        DataFrame with one row per circuit.
    """
    return pd.DataFrame(circuits)


def save_to_json(circuits: List[Dict[str, Any]], output_path: str) -> None:
    """
    Serialise parsed circuits to a JSON file.

    Args:
        circuits:    List of circuit dictionaries.
        output_path: Destination file path.
    """
    with open(output_path, 'w') as f:
        json.dump(circuits, f, indent=2)


def create_circuit_info_sheet(
    circuits: List[Dict[str, Any]], output_path: str
) -> None:
    """
    Write a CSV summary of circuit metadata (name, lines, gates, library).

    Args:
        circuits:    List of circuit dictionaries.
        output_path: Destination CSV file path.
    """
    df = real_circuits_to_dataframe(circuits)
    df[["Circuit Name", "No of Lines", "No of Gates", "Library Type"]].to_csv(
        output_path, index=False
    )