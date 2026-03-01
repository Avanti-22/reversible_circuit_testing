import pandas as pd
from datetime import datetime
import os

MASTER_CSV_PATH = "master_results.csv"

def save_results_to_csv(results):
    """
    Appends results as a new record to the master CSV sheet.
    Creates the master sheet with headers if it doesn't exist yet.

    Args:
        results: dict of result fields for the current circuit.
    """
    now = datetime.now()
    results["date"] = now.strftime("%Y-%m-%d")
    results["time"] = now.strftime("%H:%M:%S")

    new_record = pd.DataFrame([results])

    if os.path.exists(MASTER_CSV_PATH):
        new_record.to_csv(MASTER_CSV_PATH, mode="a", header=False, index=False)
    else:
        new_record.to_csv(MASTER_CSV_PATH, mode="w", header=True, index=False)
        print(f"Master sheet created at: {os.path.abspath(MASTER_CSV_PATH)}")