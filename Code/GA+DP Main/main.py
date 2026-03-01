from experiment_runner import *


input_path = r"C:\Users\thale\OneDrive\Documents\Avanti\MTech\Dissertation\Benchmarks Used in Base Paper\All Circuits\hwb6_57.real"
from concurrent.futures import ProcessPoolExecutor
import os

# Practical max
fault_models = ["SA-1"]


if __name__ == "__main__":
    run_pipeline(input_path, fault_models=fault_models, time_limit_seconds=300.0, verbose=True, sparse_logging=False)
        
    