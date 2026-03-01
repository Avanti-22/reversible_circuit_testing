
from parser import *

# =======================PARSE REAL FILE=========================
def parse_real_file(filepath: str) -> Dict[str, Any]:

    parser = RealFileParser()
    
    return parser.parse_file(filepath)

# ======================PARSE REAL DIRECTORY=========================
def parse_real_directory(directory: str, pattern: str = "*.real") -> List[Dict[str, Any]]:

    import glob
    import os

    parser = RealFileParser()
    circuits = []

    # Find all matching files
    search_path = os.path.join(directory, pattern)
    files = glob.glob(search_path)

    for filepath in sorted(files):
        try:

            circuit = parser.parse_file(filepath)
            circuits.append(circuit)
            
        except Exception as e:
            print(f"✗ Error parsing {filepath}: {e}")

    return circuits

# =====================CONVERT AND SAVE  CIRCUITS LIST TO DATAFRAME==========================
def real_circuits_to_dataframe(circuits: List[Dict[str, Any]]) -> pd.DataFrame:

    return pd.DataFrame(circuits)

# =====================CONVERT AND SAVE CIRCUITS LIST TO JSON==========================
def save_to_json(circuits: List[Dict[str, Any]], output_path: str):

    import json

    with open(output_path, 'w') as f:
        json.dump(circuits, f, indent=2)

# =====================CREATE AND SAVE THE CIRCUIT INFO SHEET TO CSV==========================
def create_circuit_info_sheet(circuits: List[Dict[str, Any]], output_path: str):

    df = real_circuits_to_dataframe(circuits)

    summary_df = df[["Circuit Name", "No of Lines", "No of Gates", "Library Type"]]
    summary_df.to_csv(output_path, index=False)
