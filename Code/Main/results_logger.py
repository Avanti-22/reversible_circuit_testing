# import pandas as pd
# from datetime import datetime
# import os

# MASTER_CSV_PATH = "master_results.csv"

# def save_results_to_csv(results):
#     """
#     Appends results as a new record to the master CSV sheet.
#     Creates the master sheet with headers if it doesn't exist yet.

#     Args:
#         results: dict of result fields for the current circuit.
#     """
#     now = datetime.now()
#     results["date"] = now.strftime("%Y-%m-%d")
#     results["time"] = now.strftime("%H:%M:%S")

#     new_record = pd.DataFrame([results])

#     if os.path.exists(MASTER_CSV_PATH):
#         new_record.to_csv(MASTER_CSV_PATH, mode="a", header=False, index=False)
#     else:
#         new_record.to_csv(MASTER_CSV_PATH, mode="w", header=True, index=False)
#         print(f"Master sheet created at: {os.path.abspath(MASTER_CSV_PATH)}")

import pandas as pd
from datetime import datetime
import os
from filelock import FileLock
from datetime import timezone
import pytz

output_path=r"Code\Main\Output"


def save_results_to_csv(results, output_dir=output_path):
    # output_dir = os.path.dirname(os.path.abspath(source_filepath))
    master_csv_path = os.path.join(output_dir, "no_of_faults.csv")
    lock_path = os.path.join(output_dir, "no_of_faults.lock")

    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    results["date"] = now.strftime("%Y-%m-%d")
    results["time"] = now.strftime("%H:%M:%S")

    new_record = pd.DataFrame([results])

    with FileLock(lock_path):  # Auto-acquires and releases
        if os.path.exists(master_csv_path):
            new_record.to_csv(master_csv_path, mode="a", header=False, index=False, lineterminator="\n")
        else:
            new_record.to_csv(master_csv_path, mode="w", header=True, index=False, lineterminator="\n")
            print(f"Master sheet created at: {master_csv_path}")