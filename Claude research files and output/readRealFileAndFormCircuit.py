import re
import pandas as pd
import json
import os
from typing import List, Tuple, Dict, Any

class RealFileParser:
    """Parser for RevLib .real format files"""
    
    def __init__(self):
        self.reset()
    
    
    # lines === variables
    # gates === levels
    
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
        self.metadata = {}
    
    def parse_file(self, filepath: str) -> Dict[str, Any]:
        """
        Parse a .real file and return circuit information
        
        Args:
            filepath: Path to the .real file
            
        Returns:
            Dictionary containing circuit information compatible with your dataset format
        """
        self.reset()
        
        with open(filepath, 'r') as f:
            self.circuitName = os.path.splitext(os.path.basename(filepath))[0]
            print(self.circuitName)
            lines = f.readlines()
        
        in_circuit = False
        
        for line in lines:
            line = line.strip()
            
            if(self.circuitName is None):           
                if line.startswith("# Function:"):
                    self.circuitName = line.split(":")[1].strip()
                else:
                    self.circuitName = "None"
                    
            if line.startswith('# Used Library:'):
                # print(line)
                # print()
                # print(line.split("Used Library:")[1])
                self.type = line.split("Used Library:")[1].strip().split()[0]
                
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            
            # Parse header information          
            
            elif line.startswith('.version'):
                self.version = line.split()[1]
            
            elif line.startswith('.numvars'):
                self.noOfLines = int(line.split()[1])
            
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
                # Parse gate definition
        
                global libraries
                libraries = set()
                
                gate = self._parse_gate(line)
                if gate:
                    self.gates.append(gate)
                                
                if self.type == "":
                    if len(libraries) == 1:
                        self.type = libraries.pop()
                    elif len(libraries) > 1:
                        for lib in libraries:
                            self.type += lib + " "
                    print(self.type)  

            self.noOfGates = len(self.gates)
        return self._create_circuit_dict()
    
    def _parse_gate(self, gate_line: str) -> Dict[str, Any]:
        """
        Parse a single gate line
        
        Gate formats:
        - t1 a          → Toffoli with 0 controls (NOT gate)
        - t2 a b        → Toffoli with 1 control
        - t3 a b c      → Toffoli with 2 controls
        - t4 a b c d    → Toffoli with 3 controls
        - f2 a b c      → Fredkin with 0 controls
        - f3 a b c d    → Fredkin with 1 control
        """
        
        parts = gate_line.split()
        if not parts:
            return None
        gate_type = parts[0].lower()
        gate_vars = parts[1:]
        
        # Determine if Toffoli or Fredkin
        
        if gate_type.startswith('t'):
            libraries.add("MCT")
            # Toffoli gate
            num_lines = int(gate_type[1])  # t2 → 2 lines, t3 → 3 lines, etc.
            
            if num_lines == 1:
                # Single line = NOT gate (Toffoli with no controls)
                return {
                    "gate": "TOFFOLI",
                    "vars": gate_vars  # [target]
                }
            else:
                # Multiple lines: controls + target
                return {
                    "gate": "TOFFOLI",
                    "vars": gate_vars  # [control1, ..., target]
                }
        
        elif gate_type.startswith('f'):
            libraries.add("MCF")
            # Fredkin gate
            num_lines = int(gate_type[1])
            
            if num_lines == 2:
                # No controls, just swap
                return {
                    "gate": "FREDKIN",
                    "vars": gate_vars  # [swap1, swap2]
                }
            else:
                # With controls: controls + swap targets
                return {
                    "gate": "FREDKIN",
                    "vars": gate_vars  # [control1, ..., swap1, swap2]
                }

        elif gate_type.startswith('p'):
            libraries.add("P")
            # Peres gate with 2 controls and 1 target
            return {
                "gate": "PERES",
                "vars": gate_vars  # [control1, control2, target]
            }
        
        else:
            print(f"Warning: Unknown gate type '{gate_type}'")
            return None

        
        
    def _create_circuit_dict(self) -> Dict[str, Any]:
        """
        Create a dictionary compatible with your existing dataset format
        """
        # Extract circuit name from variables or use default
        # circuit_name = circuitName
        # circuit_name = f"circuit_{self.numvars}vars_{len(self.gates)}gates"
        
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
            # "num_gates": len(self.gates),
            "Metadata": {
                "Version": self.version,
                "format": "real"
            }
        }
    
    def to_internal_circuit(self, circuit_dict: Dict[str, Any]) -> List[Tuple]:
        """
        Convert parsed circuit to internal format used by your algorithm
        (Same as convert_dataset_gates function)
        """
        variables = circuit_dict["Variables"]
        gates = circuit_dict["Gates"]
        
        if isinstance(variables, str):
            import ast
            variables = ast.literal_eval(variables)
        
        var_map = {v: i for i, v in enumerate(variables)}
        circuit = []
        
        for g in gates:
            if not isinstance(g, dict) or "gate" not in g or "vars" not in g:
                continue
            
            gate_name = str(g["gate"]).upper()
            gate_vars = g["vars"]
            
            # Convert variable names to indices
            idxs = [var_map[n] for n in gate_vars if n in var_map]
            
            if len(idxs) == 0:
                continue
            
            if gate_name == "TOFFOLI":
                # Last variable is target, rest are controls
                if len(idxs) == 1:
                    controls, target = [], idxs[0]
                else:
                    controls, target = idxs[:-1], idxs[-1]
                circuit.append(("TOFFOLI", controls, target))
            
            elif gate_name == "FREDKIN":
                # Last two are swap targets, rest are controls
                if len(idxs) < 2:
                    continue
                if len(idxs) == 2:
                    controls, s1, s2 = [], idxs[0], idxs[1]
                else:
                    controls, s1, s2 = idxs[:-2], idxs[-2], idxs[-1]
                circuit.append(("FREDKIN", (controls, s1, s2)))
        
        return circuit


# ============================================================================
# BATCH PROCESSING FUNCTIONS
# ============================================================================

def parse_real_file(filepath: str) -> Dict[str, Any]:
    """
    Convenience function to parse a single .real file
    
    Args:
        filepath: Path to .real file
        
    Returns:
        Circuit dictionary
    """
    parser = RealFileParser()
    return parser.parse_file(filepath)


def parse_real_directory(directory: str, pattern: str = "*.real") -> List[Dict[str, Any]]:
    """
    Parse all .real files in a directory
    
    Args:
        directory: Directory containing .real files
        pattern: Glob pattern for file matching
        
    Returns:
        List of circuit dictionaries
    """
    import glob
    import os
    
    parser = RealFileParser()
    circuits = []
    
    # Find all matching files
    search_path = os.path.join(directory, pattern)
    files = glob.glob(search_path)
    
    print(f"Found {len(files)} .real files in {directory}")
    
    for filepath in sorted(files):
        print()
        try:
            circuit = parser.parse_file(filepath)
            # Add filename to circuit info
            # circuit["circuit_name"] = os.path.splitext(os.path.basename(filepath))[0]
            circuits.append(circuit)
            # print(circuit)
            # print(f"✓ Parsed: {circuit['Circuit Name']} ({circuit['No of Lines']} lines, {circuit['No of Gates']} gates)")
        except Exception as e:
            print(f"✗ Error parsing {filepath}: {e}")
    
    return circuits


def real_circuits_to_dataframe(circuits: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Convert list of circuit dictionaries to pandas DataFrame
    
    Args:
        circuits: List of parsed circuit dictionaries
        
    Returns:
        DataFrame compatible with your existing code
    """
    return pd.DataFrame(circuits)


def save_to_json(circuits: List[Dict[str, Any]], output_path: str):
    """
    Save parsed circuits to JSON file (compatible with your data loading)
    
    Args:
        circuits: List of circuit dictionaries
        output_path: Path to save JSON file
    """
    import json
    
    with open(output_path, 'w') as f:
        json.dump(circuits, f, indent=2)
    
    print(f"Saved {len(circuits)} circuits to {output_path}")


def create_circuit_info_sheet(circuits: List[Dict[str, Any]], output_path: str):
    """
    Create a CSV sheet summarizing circuit information
    
    Args:
        circuits: List of parsed circuit dictionaries
        output_path: Path to save CSV file
    """
    df = real_circuits_to_dataframe(circuits)
    summary_df = df[["Circuit Name", "No of Lines", "No of Gates", "Library Type"]]
    summary_df.to_csv(output_path, index=False)
    print(f"Saved circuit info sheet to {output_path}")

# # Test with your example
# if __name__ == "__main__":

    
    # for single file test
    
    # Parse it
    # circuit = parse_real_file(r"benchmark circuits/urf2_277.real")
    # print(circuit)
    # parser = RealFileParser()
    # internal = parser.to_internal_circuit(circuit)
    # print("\nInternal Format:")
    # for gate in internal:
    #     print(gate)
    
    
    
    # # for directory test
    
    # circuits =parse_real_directory(r"C:\Users\thale\OneDrive\Documents\Avanti\MTech\Dissertation\Benchmarks Used in Base Paper\Large")

    # create_circuit_info_sheet(circuits, "largeCircuits.csv")
    # save_to_json(circuits, "largeCircuits.json")

    
    
