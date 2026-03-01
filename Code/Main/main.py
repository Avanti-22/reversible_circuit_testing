from experiment_runner import *


input_path = r"C:\Users\thale\OneDrive\Documents\Avanti\MTech\Dissertation\Benchmarks Used in Base Paper\Small\cnt3-5_180.real"
from concurrent.futures import ProcessPoolExecutor
import os

# Practical max
fault_models = ["SA-1", "SA-0", "MMGF", "SMGF", "PMGF", "GAF", "CAF", "RGF", "BF", "MBF"]


if __name__ == "__main__":
    run_pipeline(input_path, fault_models=fault_models, time_limit_seconds=300.0, verbose=False )
        
    