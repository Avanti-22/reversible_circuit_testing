# from Code.Main.parser import *
from posixpath import basename

from batch_parsing_functions import *
from ga_engine import *
from results_logger import *



import os
from os.path import basename
from concurrent.futures import ThreadPoolExecutor, as_completed


def get_files_from_path(path):
    """Returns a list of file paths from a file or folder path."""
    if os.path.isfile(path):
        return [path]
    elif os.path.isdir(path):
        return [
            os.path.join(root, f)
            for root, _, files in os.walk(path)
            for f in files
        ]
    else:
        raise ValueError(f"Invalid path: {path}")


def _run_single_fault_model(circuit_dict, fault_model, filepath,
                             population_size, max_generations,
                             time_limit_seconds, skip_minimization,
                             verbose, sparse_logging):
    """Runs GA for a single fault model and saves results."""
    try:
        if verbose:
            print(f"  [{basename(filepath)}] Starting: {fault_model}")

        GA_object = GeneticAlgorithm(
            circuit_dict,
            faultModel=fault_model,
            verbose=verbose,
            sparse_logging=sparse_logging,
            population_size=population_size,
            max_generations=max_generations,
            time_limit_seconds=time_limit_seconds,
            skip_minimization=skip_minimization
        )

        results = GA_object.run()
        save_results_to_csv(results)

        if verbose:
            print(f"  [{basename(filepath)}] Done: {fault_model}")

        return fault_model, None

    except Exception as e:
        return fault_model, e


def run_pipeline(path,
                 fault_models: list,
                 population_size: int = None,
                 max_generations: int = 20,
                 time_limit_seconds: float = None,
                 skip_minimization=None,
                 verbose=True,
                 sparse_logging=True,
                 max_workers: int = None):
    """
    Args:
        max_workers: Max parallel threads per circuit file.
                     Defaults to len(fault_models) if None.
    """
    real_files = get_files_from_path(path)
    # workers = max_workers or len(fault_models)
    workers = 4 or min(len(fault_models), os.cpu_count())

    if verbose:
        print(f"Found {len(real_files)} file(s) to process.")
        print(f"Fault models: {fault_models}")
        print(f"Parallel workers per circuit: {workers}\n")

    for i, filepath in enumerate(real_files, 1):
        if verbose:
            print(f"[{i}/{len(real_files)}] Circuit: {basename(filepath)}")

        circuit_dict = parse_real_file(filepath)

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(
                    _run_single_fault_model,
                    circuit_dict, fault_model, filepath,
                    population_size, max_generations,
                    time_limit_seconds, skip_minimization,
                    verbose, sparse_logging
                ): fault_model
                for fault_model in fault_models
            }

            for future in as_completed(futures):
                fault_model, error = future.result()
                if error:
                    print(f"  [ERROR] {basename(filepath)} | {fault_model}: {error}")

        del circuit_dict

        if verbose:
            print(f"  All fault models complete for: {basename(filepath)}\n")

    if verbose:
        print("Pipeline complete.")









# fault_cache = {}
# fault_cache = {"000000": 5, "111111": 10}

# vec = 000000
# print(fault_cache[vec])

# if vec in fault_cache:
#         print(f"Cache hit for {vec}: {fault_cache[vec]}")



# # print(circuit)
# # print(circuit["No of Lines"])
# GaForSMGF = GeneticAlgorithm(circuit, faultModel="SMGF")
# # stage1 = GaForSMGF.stage_i_input_Parameter_extratcion()
# # # print(stage1)

# # init_pop = GaForSMGF.stage_ii_TV_selection()
# # # print(stage2)

# # # stage3 = GaForSMGF.stage_iii_fitness_function_computation(stage2)
# # fitnesses, dfm, vec_map = GaForSMGF.compute_fitness_for_population(init_pop)
# # print(fitnesses, dfm, vec_map)

# # parents = GaForSMGF.stage_iv_roulette_wheel_selection(fitnesses, init_pop)
# # print(parents)

# # childern = GaForSMGF.stage_v_crossover(parents)
# # print(childern)

# # mutatedCh = GaForSMGF.stage_vi_mutation(childern)
# # print(mutatedCh)

# # fin_pop, fitnesses, cfm, cvm = GaForSMGF.stage_vii_test_population_generation(init_pop, mutatedCh)
# # print(fin_pop, fitnesses, cfm, cvm)


# # stage8 = GaForSMGF.stage_viii_minimal_test_set(fin_pop, cfm, cvm)
# # # print(stage8)


# result = GaForSMGF.run(verbose=False)
# print(result)




# ##Run GA for Input Folder


# def run_timer_for_all_files(circuits , faultModel = "SMGF", population_size=20,  output_path = None):

#     results = []

#     for circuit in circuits:
#         try:

#             print(circuit["Circuit Name"])
#             simulationResults = SimulationLoop(circuit, faultModel, population_size)
#             results.append(simulationResults.run_Loop())

#         except Exception as e:
#             circuit_name = None
#             try:
#                 circuit_name = circuit.get("Circuit Name") if circuit is not None else None
#             except Exception:
#                 circuit_name = None
#             print(f"Error processing circuit {circuit_name}: {e}")
#             continue
#         # print(results)
#         print("done for circuit this")
#     print("\n\nSaving the results\n\n")
#     save_results_to_csv(results, output_path)

#     print(f"saved to {output_path}")
#     table = pd.read_csv(output_path)
#     # table
#     return table




# import os


# def get_files_from_path(path):
#     """Returns a list of file paths from a file or folder path."""
#     if os.path.isfile(path):
#         return [path]
#     elif os.path.isdir(path):
#         return [
#             os.path.join(root, f)
#             for root, _, files in os.walk(path)
#             for f in files
#         ]
#     else:
#         raise ValueError(f"Invalid path: {path}")


# def run_pipeline(path, 
#                  fault_model, 
#                  population_size: int = None, 
#                  max_generations: int = 20,
#                  time_limit_seconds: float = None, 
#                  skip_minimization=None, 
#                  verbose =True, 
#                  sparse_logging=True):
        
        
#     real_files = get_files_from_path(path)

#     if verbose:
#         print(f"Found {len(real_files)} file(s) to process.")

#     for i, filepath in enumerate(real_files, 1):
#         if verbose:
#             print(f"[{i}/{len(real_files)}] Processing: {filepath}")

#         # Parse
#         circuit_dict = parse_real_file(filepath)

#         # Run GA directly
#         GA_object = GeneticAlgorithm(circuit_dict, 
#                                      faultModel=fault_model, 
#                                      verbose=verbose, 
#                                      sparse_logging=sparse_logging, 
#                                      population_size= population_size, 
#                                      max_generations = max_generations,
#                                      time_limit_seconds= time_limit_seconds, 
#                                      skip_minimization=skip_minimization )
#         results = GA_object.run()

#         # Save results immediately
#         save_results_to_csv(results)

#         if verbose:
#             print(f"  Results saved for: {basename(filepath)}")

#         # Delete large objects
#         del circuit_dict


#     if verbose:
#         print("Pipeline complete.")


