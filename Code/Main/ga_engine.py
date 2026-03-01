from concurrent.futures import ThreadPoolExecutor
import gc
import time
import numpy as np
import itertools
from fault_models import *
import random
from simulator import *
import logging
logger = logging.getLogger(__name__)


# class SimulationLoop:
#     def __init__(self, circuit, faultModel, population_size):
#         self.circuit = circuit
#         self.faultModel = faultModel
#         self.population_size = population_size

#     def stage_i_input_Parameter_extratcion(self):
#         self.n = self.circuit["No of Lines"]
#         self.N = self.circuit["No of Gates"]
#         self.max_no_of_TV = 2 ** self.n

#     def stage_ii_TV_selection(self):
#         return random.sample(range(self.max_no_of_TV), self.n)

#     def represent_the_vec_in_binary(self, testVector):
#         return [int(x) for x in format(testVector, f'0{self.n}b')]


#     def simulation_loop_timer(self, vector):

#         if vector in self.fault_cache:
#             return self.fault_cache[vector]

#         binary_vector = self.represent_the_vec_in_binary(vector)
#         # print(f"IP vector: {binary_vector}")

#         # start_time = time.time()
#         faultFreeOutput = simulate_fault_free(self.circuit, binary_vector)
#         # faultFreeOutputTime = round((time.time() - start_time), 3)
#         # print(f"Fault free OP: {faultFreeOutput}")
#         # faultFreeOutputTime

#         # start_time = time.time()
#         faultyOutputs = get_all_faulty_outputs(self.circuit, binary_vector, self.faultModel)
#         # faultyOutputsTime = round((time.time() - start_time), 3)
#         # print(f"Faulty OP: {faultyOutputs}")
#         self.cumulatedFaults = len(faultyOutputs)

#         # return faultFreeOutputTime, faultyOutputsTime

#     def simulation_loop_timer_for_population(self, population):

#         faultFreeTimes = []
#         faultyTimes = []
#         vector_map = {}
#         # print("here")
#         start_time = time.time()

#         for i, vec in enumerate(population):
#             # print("here")
#             self.simulation_loop_timer(vec)
#             vector_map[vec] = i
#         simulationTime = round((time.time() - start_time), 3)
#         return simulationTime, vector_map

#     def run_Loop(self):
#         self.stage_i_input_Parameter_extratcion()
#         init_population = self.stage_ii_TV_selection()
#         # print(f"init_population: {init_population}")
#         self.fault_cache = {}
#         # print("here")
#         simulationTime, vector_map = self.simulation_loop_timer_for_population(init_population)
#         # print("Here")
#         results = {
#             "Circuit Name": self.circuit["Circuit Name"],
#             "Fault Model": self.faultModel,
#             "No of Lines": self.circuit["No of Lines"],
#             "No of Gates": self.circuit["No of Gates"],
#             "Population Size": self.circuit["No of Lines"],
#             "Total Number of Possible Test Vectors": self.max_no_of_TV,
#             "Total Number of Faults": self.cumulatedFaults,
#             "Circuit Simulation Time for Population": simulationTime,
#             # "Vector Map": vector_map
#         }
#         return results


# class GeneticAlgorithm:

#     def __init__(self, 
#                  circuit: dict, 
#                  faultModel: str = "SMGF",
#                  population_size: int = None, 
#                  max_generations: int = 20,
#                  time_limit_seconds: float = None, 
#                  skip_minimization=None, 
#                  verbose=False, 
#                  sparse_logging=False):

#         self.verbose = verbose
#         self.sparse_logging = sparse_logging
#         self.circuit = circuit
#         self.faultModel = faultModel
#         self.threshold = 100.0
#         self.population_size = circuit['No of Lines']
#         self.max_generations = max_generations
#         self.time_limit_seconds = time_limit_seconds if time_limit_seconds else 300.0

#         if skip_minimization is None:
#             self.skip_minimization = circuit["No of Lines"] >= 12
#         else:
#             self.skip_minimization = skip_minimization

#         self.current_generation = 0
#         self.best_coverage = 0.0
#         self.best_vector_set = []
#         self.cumulatedFaults = None
#         self.detectedFaults = None
#         self.execution_time = 0.0

#         self._start_time = None
#         self._time_limit_exceeded = False

#         # ⭐ Cache for Stage III
#         self.fault_cache = {}

#     # --------------------------------------------------

#     def _start_timer(self):
#         self._start_time = time.monotonic()

#     def _update_execution_time(self):
#         if self._start_time:
#             self.execution_time = time.monotonic() - self._start_time

#     def _check_time_limit(self):
#         self._update_execution_time()
#         if self.execution_time >= self.time_limit_seconds:
#             self._time_limit_exceeded = True
#             return True
#         return False

#     def stage_i_input_Parameter_extratcion(self):
#         self.n = self.circuit["No of Lines"]
#         self.N = self.circuit["No of Gates"]
#         self.max_no_of_TV = 2 ** self.n

#     def stage_ii_TV_selection(self, test_size=None):
#         if test_size is None:
#             test_size = self.n
#         return random.sample(range(self.max_no_of_TV), test_size)

#     def represent_the_vec_in_binary(self, testVector):
#         return [int(x) for x in format(testVector, f'0{self.n}b')]
    
#     def get_detected_faults_row(self, faultFreeOutput, faultyOutputs):
#         return np.array(
#             [faulty != faultFreeOutput for faulty in faultyOutputs],
#             dtype=bool
#         )

#     # --------------------------------------------------

#     def stage_iii_fitness_function_computation(self, vector):

#         if str(vector) in self.fault_cache:
#             return self.fault_cache[str(vector)]

#         # binary_vector = self.represent_the_vec_in_binary(vector)
#         # print(f"IP vector: {vector}")
#         faultFreeOutput = simulate_fault_free(self.circuit, vector)
#         # print(f"Fault free OP: {faultFreeOutput}")
#         faultyOutputs = get_all_faulty_outputs(self.circuit, vector, self.faultModel)
#         # print(f"Faulty OP: {faultyOutputs}")
#         self.cumulatedFaults = len(faultyOutputs)

#         detectedFaultArray = self.get_detected_faults_row(faultFreeOutput, faultyOutputs)

#         detected = np.sum(detectedFaultArray)
#         coverage = (detected / self.cumulatedFaults) * 100 if self.cumulatedFaults else 0

#         self.fault_cache[vector] = (coverage, detectedFaultArray)
#         return coverage, detectedFaultArray

#     # --------------------------------------------------

#     # def compute_fitness_for_population(self, population):

#     #     fitnesses = []
#     #     rows = []
#     #     vector_map = {}

#     #     for i, vec in enumerate(population):
#     #         coverage, detected_faults_row = self.stage_iii_fitness_function_computation(vec)
#     #         fitnesses.append(coverage)
#     #         rows.append(detected_faults_row)
#     #         vector_map[vec] = i

#     #         if coverage >= self.threshold:
#     #             break

#     #     # return fitnesses, np.vstack(rows), vector_map
#     #     return fitnesses, np.array(rows, dtype=bool), vector_map

#     def compute_fitness_for_population(self, population):
#         fitnesses = []
#         rows = []
#         vector_map = {}

#         # Split cached vs uncached
#         uncached = [v for v in population if v not in self.fault_cache]

#         # Compute uncached in parallel
#         if uncached:
#             with ThreadPoolExecutor() as executor:
#                 futures = {executor.submit(self.stage_iii_fitness_function_computation, v): v 
#                         for v in uncached}
#                 for future in as_completed(futures):
#                     future.result()  # just populates cache

#         # Now read everything from cache
#         for i, vec in enumerate(population):
#             coverage, detected_faults_row = self.fault_cache[vec]
#             fitnesses.append(coverage)
#             rows.append(detected_faults_row)
#             vector_map[vec] = i

#             if coverage >= self.threshold:
#                 break

#         return fitnesses, np.vstack(rows), vector_map
    
    
#     # --------------------------------------------------

#     def stage_iv_roulette_wheel_selection(self, fitnessFunction, population):

#         total_fitness = sum(fitnessFunction)
#         if total_fitness == 0:
#             probabilities = [1 / len(fitnessFunction)] * len(fitnessFunction)
#         else:
#             probabilities = [f / total_fitness for f in fitnessFunction]

#         parent_pairs = []
#         for _ in range(self.n):
#             p1 = random.choices(population, weights=probabilities)[0]
#             p2 = random.choices(population, weights=probabilities)[0]
#             parent_pairs.append((p1, p2))

#         return parent_pairs

#     # --------------------------------------------------

#     def represent_bin_in_int(self, bin_vec_list):
#         return int("".join(map(str, bin_vec_list)), 2)

#     # --------------------------------------------------

#     def stage_v_crossover(self, parent_pairs):

#         children = []

#         for p1, p2 in parent_pairs:
#             b1 = self.represent_the_vec_in_binary(p1)
#             b2 = self.represent_the_vec_in_binary(p2)

#             cp = random.randint(1, self.n - 1)
#             child = self.represent_bin_in_int(b1[:cp] + b2[cp:])
#             children.append(child)

#         return children

#     # --------------------------------------------------

#     def stage_vi_mutation(self, children):

#         mutated = []

#         maxVal = (10 ** (self.current_generation + 1)) - 1

#         for child in children:
#             if random.randint(0, maxVal) < 10:

#                 cb = self.represent_the_vec_in_binary(child)
#                 flip = random.randint(0, self.n - 1)
#                 cb[flip] ^= 1

#                 mutated.append(self.represent_bin_in_int(cb))
#             else:
#                 mutated.append(child)

#         return mutated

#     # --------------------------------------------------

#     def build_fault_matrix(self, population):

#         rows = []
#         vector_map = {}

#         for i, vec in enumerate(population):
#             _, faults = self.stage_iii_fitness_function_computation(vec)
#             rows.append(faults)
#             vector_map[vec] = i

#         return np.vstack(rows), vector_map

#     # --------------------------------------------------

#     def stage_vii_test_population_generation(self, init_pop, child_pop):

#         combined_population = list(set(init_pop + child_pop))
#         combined_fitnesses, combined_fault_matrix, combined_vector_map = self.compute_fitness_for_population(combined_population)

#         if not combined_fitnesses:
#             return init_pop, [], {}

#         sorted_fitnesses, sorted_pop = zip(*sorted(zip(combined_fitnesses, combined_population), reverse=True))
#         return list(sorted_pop), sorted_fitnesses, combined_fault_matrix, combined_vector_map

#     # --------------------------------------------------

#     # def stage_viii_minimal_test_set(self, fin_pop, fault_matrix, vector_map, L=None):

#     #     if L is None:
#     #         L = max(2, self.n // 2)

#     #     best_cov = 0
#     #     best_set = []

#     #     while L <= self.n:

#     #         if self._check_time_limit():
#     #             break

#     #         for combo in itertools.combinations(fin_pop, L):

#     #             idx = [vector_map[v] for v in combo]

#     #             combined = np.any(fault_matrix[idx], axis=0)

#     #             detected = np.sum(combined)
#     #             coverage = (detected / self.cumulatedFaults) * 100

#     #             if coverage >= self.threshold:
#     #                 return list(combo), coverage

#     #             if coverage > best_cov:
#     #                 best_cov = coverage
#     #                 best_set = list(combo)

#     #         L += 1

#     #     return best_set, best_cov
    
#     def stage_viii_minimal_test_set(self, fin_pop, fault_matrix, vector_map, L=None):
#         """Greedy set cover instead of exhaustive combinatorial search."""
        
#         covered = np.zeros(self.cumulatedFaults, dtype=bool)
#         selected = []
#         remaining_pop = list(fin_pop)

#         while remaining_pop:
#             # Pick vector that covers the most NEW faults
#             best_vec = max(
#                 remaining_pop,
#                 key=lambda v: np.sum(fault_matrix[vector_map[v]] & ~covered)
#             )
            
#             new_coverage = fault_matrix[vector_map[best_vec]] & ~covered
#             if not np.any(new_coverage):
#                 break  # no more improvement possible

#             covered |= fault_matrix[vector_map[best_vec]]
#             selected.append(best_vec)
#             remaining_pop.remove(best_vec)

#             coverage_pct = (np.sum(covered) / self.cumulatedFaults) * 100
#             if coverage_pct >= self.threshold:
#                 break

#         final_coverage = (np.sum(covered) / self.cumulatedFaults) * 100
#         return selected, final_coverage

#     def run(self):
#         """
#         Run the genetic algorithm.

#         Args:
#             verbose   : If True, emit progress logs.
#             compaction: If True, use compact single-line logs per generation.
#                         If False, emit detailed per-stage logs.
#         """
#         verbose = getattr(self, 'verbose', False)
#         sparse_logging = getattr(self, 'sparse_logging', False)
        
#         log = logger.info if not self.verbose else print  # swap to logger.info throughout if preferred

#         def log_verbose(msg):
#             if verbose:
#                 log(msg)

#         def log_compact(msg):
#             if verbose and sparse_logging:
#                 log(msg)

#         def log_detailed(msg):
#             if verbose and not sparse_logging:
#                 log(msg)

#         log_verbose("\n===== GA RUN STARTED =====")
#         self._start_timer()

#         # ── Stage I ──────────────────────────────────────────────────────────────
#         log_detailed("Stage I: Input Parameter Extraction")
#         self.stage_i_input_Parameter_extratcion()
#         log_verbose(
#             f"Population size: {self.n} | Gates: {self.N} | Max TV: {self.max_no_of_TV}"
#         )

#         # ── Stage II ─────────────────────────────────────────────────────────────
#         log_detailed("Stage II: Initial Test Vector Selection")
#         init_population = self.stage_ii_TV_selection()
#         log_verbose(f"Initial Population Size: {len(init_population)}")
#         log_detailed(f"Initial Population: {init_population}")

#         # ── Generation Loop ───────────────────────────────────────────────────────
#         for gen in range(self.max_generations):

#             if self._check_time_limit():
#                 log_verbose("Terminated: Time limit reached.")
#                 break

#             self.current_generation = gen
#             log_detailed(f"\n========== Generation {gen} ==========")

#             # Fitness
#             log_detailed("Stage III: Fitness Evaluation")
#             init_fitnesses, init_detected_matrix, init_vector_map = \
#                 self.compute_fitness_for_population(init_population)

#             if not init_fitnesses:
#                 log_verbose("Terminated: Empty fitness list.")
#                 break

#             max_fit = max(init_fitnesses)
#             min_fit = min(init_fitnesses)
#             avg_fit = sum(init_fitnesses) / len(init_fitnesses)

#             log_detailed(
#                 f"Fitness — Max: {max_fit:.4f} | Min: {min_fit:.4f} | Avg: {avg_fit:.4f}"
#             )

#             # Selection
#             log_detailed("Stage IV: Roulette Wheel Selection")
#             parents = self.stage_iv_roulette_wheel_selection(init_fitnesses, init_population)
#             log_detailed(f"Selected Parents: {parents}")

#             # Crossover
#             log_detailed("Stage V: Crossover")
#             children = self.stage_v_crossover(parents)
#             log_detailed(f"Children: {children}")

#             # Mutation
#             log_detailed("Stage VI: Mutation")
#             mutated_children = self.stage_vi_mutation(children)
#             log_detailed(f"Mutated Children: {mutated_children}")

#             # Population update
#             log_detailed("Stage VII: Test Population Generation")
#             fin_sorted_population, fin_sorted_fitnesses, fin_detected_matrix, fin_vector_map = \
#                 self.stage_vii_test_population_generation(init_population, mutated_children)

#             log_detailed(f"Sorted Population: {fin_sorted_population}")
#             log_detailed(f"Sorted Fitnesses:  {fin_sorted_fitnesses}")

#             # Coverage
#             combined_detected_list = np.any(fin_detected_matrix, axis=0)
#             detected_faults = int(np.sum(combined_detected_list))
#             fault_coverage = (detected_faults / self.cumulatedFaults) * 100

#             log_detailed(
#                 f"Coverage — Detected: {detected_faults} / {self.cumulatedFaults}"
#                 f" = {fault_coverage:.2f}%"
#             )

#             # Minimization
#             if not self.skip_minimization:
#                 log_detailed("Stage VIII: Minimal Test Set Reduction")
#                 min_set, min_cov = self.stage_viii_minimal_test_set(
#                     fin_sorted_population, fin_detected_matrix, fin_vector_map
#                 )
#                 log_detailed(f"Minimal Set Coverage: {min_cov:.2f}%")

#                 if min_cov >= fault_coverage:
#                     fault_coverage = min_cov
#                     test_vectors = min_set
#                     log_detailed("Minimal set accepted.")
#                 else:
#                     test_vectors = fin_sorted_population
#                     log_detailed("Original sorted population retained.")
#             else:
#                 test_vectors = fin_sorted_population

#             # Best update
#             if fault_coverage > self.best_coverage:
#                 self.best_coverage = fault_coverage
#                 self.best_vector_set = test_vectors
#                 self.detectedFaults = combined_detected_list
#                 log_detailed(f"New best coverage: {self.best_coverage:.2f}%")

#             # Compact per-generation summary (always shown when compaction=True)
#             log_compact(
#                 f"Gen {gen:03d} | "
#                 f"MaxFit: {max_fit:.4f} | "
#                 f"AvgFit: {avg_fit:.4f} | "
#                 f"Cov: {fault_coverage:6.2f}% | "
#                 f"Best: {self.best_coverage:6.2f}% | "
#                 f"Pop: {len(test_vectors)}"
#             )

#             # Threshold check
#             if fault_coverage >= self.threshold:
#                 log_verbose("Terminated: Coverage threshold reached.")
#                 break

#             log_detailed(f"Next Generation Population: {test_vectors}")
#             init_population = test_vectors[:self.population_size]
#             log_detailed(f"Trimmed to population size: {len(init_population)}")

#             gc.collect()

#         # ── Summary ───────────────────────────────────────────────────────────────
#         log_verbose(f"===== GA RUN COMPLETED — Best Coverage: {self.best_coverage:.2f}% =====")
#         log_detailed(f"Final Best Vector Set: {self.best_vector_set}")

#         return self.save_results()

#     # --------------------------------------------------

# #     def save_results(self):

#         self._update_execution_time()

# #         return {
#             "Circuit Name": self.circuit["Circuit Name"],
#             "No of Lines": self.circuit["No of Lines"],
#             "No of Gates": self.circuit["No of Gates"],
#             "Fault Model": self.faultModel,
#             # "Population Size": self.population_size,
#             # "Max Generations": self.max_generations,
#             "Actual Generations": self.current_generation + 1,
#             # "Threshold": self.threshold,
#             "Total Faults": self.cumulatedFaults,
#             "Detected Faults": int(np.sum(self.detectedFaults)) if self.detectedFaults is not None else 0,
#             "Fault Coverage": self.best_coverage,
#             # "Minimal Vector Set": self.best_vector_set,
#             "Test Set Size": len(self.best_vector_set),
#             "Execution Time": self.execution_time,
#             "Time Limit Exceeded": self._time_limit_exceeded,
#             "Minimization Skipped": self.skip_minimization,
#             # "Detected Faults List": self.detectedFaults.tolist() if self.detectedFaults is not None else []
#         }





import gc
import time
import numpy as np
import logging
import random

from fault_models import *
from simulator import *

logger = logging.getLogger(__name__)


class GeneticAlgorithm:

    def __init__(self,
                 circuit: dict,
                 faultModel: str = "SMGF",
                 population_size: int = None,
                 max_generations: int = 20,
                 time_limit_seconds: float = None,
                 skip_minimization=None,
                 verbose=False,
                 sparse_logging=False):
        """
        mmgf_time_budget : only used when faultModel="MMGF"
            "fast"      → depth 1 only  (linear,    N combos)
            "balanced"  → depth 1-2     (quadratic, N²/2 combos)  ← default
            "thorough"  → depth 1-3     (cubic,     N³/6 combos)
            "full"      → no cap        (exponential, original behaviour)
        """
        self.verbose = verbose
        self.sparse_logging = sparse_logging
        self.circuit = circuit
        self.faultModel = faultModel
        self.threshold = 100.0
        self.population_size = population_size or circuit['No of Lines']
        self.max_generations = max_generations
        self.time_limit_seconds = time_limit_seconds if time_limit_seconds else 300.0

        if skip_minimization is None:
            self.skip_minimization = circuit["No of Lines"] >= 12
        else:
            self.skip_minimization = skip_minimization

        self.current_generation = 0
        self.best_coverage = 0.0
        self.best_vector_set = []
        self.cumulatedFaults = None
        self.detectedFaults = None
        self.execution_time = 0.0

        self._start_time = None
        self._time_limit_exceeded = False

        # int key cache — avoids str(vector) overhead on every lookup
        self.fault_cache: dict[int, tuple] = {}

    # ── Logging Helpers ──────────────────────────────────────────────────────

    def _log(self, msg):
        if self.verbose:
            print(msg)

    def _log_detail(self, msg):
        if self.verbose and not self.sparse_logging:
            print(msg)

    def _log_compact(self, msg):
        if self.verbose and self.sparse_logging:
            print(msg)

    # ── Timer ────────────────────────────────────────────────────────────────

    def _start_timer(self):
        self._start_time = time.monotonic()

    def _update_execution_time(self):
        if self._start_time:
            self.execution_time = time.monotonic() - self._start_time

    def _check_time_limit(self):
        self._update_execution_time()
        if self.execution_time >= self.time_limit_seconds:
            self._time_limit_exceeded = True
            return True
        return False

    # ── Stage I ──────────────────────────────────────────────────────────────

    def stage_i_input_Parameter_extratcion(self):
        self.n = self.circuit["No of Lines"]
        self.N = self.circuit["No of Gates"]
        self.max_no_of_TV = 2 ** self.n

    # ── Stage II ─────────────────────────────────────────────────────────────

    def stage_ii_TV_selection(self, test_size=None):
        if test_size is None:
            test_size = self.n
        return random.sample(range(self.max_no_of_TV), test_size)

    # ── Utilities ────────────────────────────────────────────────────────────

    def represent_the_vec_in_binary(self, testVector):
        return [int(x) for x in format(testVector, f'0{self.n}b')]

    def represent_bin_in_int(self, bin_vec_list):
        return int("".join(map(str, bin_vec_list)), 2)

    def get_detected_faults_row(self, faultFreeOutput, faultyOutputs):
        return np.array(
            [faulty != faultFreeOutput for faulty in faultyOutputs],
            dtype=bool
        )

    # ── Stage III ────────────────────────────────────────────────────────────
    # Sequential — NO thread pool.
    # Thread pool overhead (executor spinup ~10s) far exceeds benefit for
    # small-to-medium workloads. Cache hits are O(1) int lookup anyway.

    def stage_iii_fitness_function_computation(self, vector: int):
        if vector in self.fault_cache:
            return self.fault_cache[vector]

        fault_free_output = simulate_fault_free(self.circuit, vector)
        faulty_outputs = get_all_faulty_outputs(
            self.circuit, vector, self.faultModel)
        self.cumulatedFaults = len(faulty_outputs)

        detected_fault_array = self.get_detected_faults_row(fault_free_output, faulty_outputs)
        detected = int(np.sum(detected_fault_array))
        coverage = (detected / self.cumulatedFaults) * 100 if self.cumulatedFaults else 0

        self.fault_cache[vector] = (coverage, detected_fault_array)
        return coverage, detected_fault_array

    # ── Fitness for Population ────────────────────────────────────────────────

    def compute_fitness_for_population(self, population):
        fitnesses = []
        rows = []
        vector_map = {}

        for i, vec in enumerate(population):
            if self._check_time_limit():
              self._log("TLE hit during fitness computation — aborting population eval.")
              break
              
            coverage, detected_faults_row = self.stage_iii_fitness_function_computation(vec)
            fitnesses.append(coverage)
            rows.append(detected_faults_row)
            vector_map[vec] = i

            if coverage >= self.threshold:
                self._log_detail(f"Singleton vector {vec} achieves 100% — early exit.")
                return fitnesses, np.array(rows, dtype=bool), vector_map, True  # ← singleton flag
                # break

        return fitnesses, np.array(rows, dtype=bool), vector_map, False

    # ── Stage IV ─────────────────────────────────────────────────────────────

    def stage_iv_roulette_wheel_selection(self, fitnessFunction, population):
        total_fitness = sum(fitnessFunction)
        if total_fitness == 0:
            probabilities = [1 / len(fitnessFunction)] * len(fitnessFunction)
        else:
            probabilities = [f / total_fitness for f in fitnessFunction]

        parent_pairs = []
        for _ in range(self.n):
            p1 = random.choices(population, weights=probabilities)[0]
            p2 = random.choices(population, weights=probabilities)[0]
            parent_pairs.append((p1, p2))

        return parent_pairs

    # ── Stage V ──────────────────────────────────────────────────────────────

    def stage_v_crossover(self, parent_pairs):
        children = []
        for p1, p2 in parent_pairs:
            b1 = self.represent_the_vec_in_binary(p1)
            b2 = self.represent_the_vec_in_binary(p2)
            cp = random.randint(1, self.n - 1)
            child = self.represent_bin_in_int(b1[:cp] + b2[cp:])
            children.append(child)
        return children

    # ── Stage VI ─────────────────────────────────────────────────────────────

    def stage_vi_mutation(self, children):
        mutated = []
        max_val = (10 ** (self.current_generation + 1)) - 1

        for child in children:
            if random.randint(0, max_val) < 10:
                cb = self.represent_the_vec_in_binary(child)
                flip = random.randint(0, self.n - 1)
                cb[flip] ^= 1
                mutated.append(self.represent_bin_in_int(cb))
            else:
                mutated.append(child)

        return mutated

    # ── Stage VII ────────────────────────────────────────────────────────────

    # def stage_vii_test_population_generation(self, init_pop, child_pop):
    #     combined_population = list(set(init_pop + child_pop))
    #     combined_fitnesses, combined_fault_matrix, combined_vector_map = \
    #         self.compute_fitness_for_population(combined_population)

    #     if not combined_fitnesses:
    #         return init_pop, [], np.array([]), {}

    #     sorted_pairs = sorted(
    #         zip(combined_fitnesses, combined_population),
    #         reverse=True
    #     )
    #     sorted_fitnesses, sorted_pop = zip(*sorted_pairs)

    #     return list(sorted_pop), sorted_fitnesses, combined_fault_matrix, combined_vector_map


    def stage_vii_test_population_generation(self, init_pop, child_pop):
    
        # Preserves order AND deduplicates — unlike set()
        seen = set()
        combined_population = []
        for v in init_pop + child_pop:
            if v not in seen:
                seen.add(v)
                combined_population.append(v)

        combined_fitnesses, combined_fault_matrix, combined_vector_map, singleton_hit  = \
            self.compute_fitness_for_population(combined_population)


        if singleton_hit:
            winning_vec = list(combined_vector_map.keys())[-1]
            return [winning_vec], [combined_fitnesses[-1]], combined_fault_matrix, combined_vector_map
        
        if not combined_fitnesses:
            return init_pop, [], np.array([]), {}

        sorted_pairs = sorted(
            zip(combined_fitnesses, combined_population),
            reverse=True
        )
        sorted_fitnesses, sorted_pop = zip(*sorted_pairs)

        return list(sorted_pop), sorted_fitnesses, combined_fault_matrix, combined_vector_map


    # ── Stage VIII ───────────────────────────────────────────────────────────
    # Greedy set cover: O(n²) vs original exhaustive O(C(n,k) * k)
    # For n=14: original tries thousands of combos; greedy picks best in n passes

    def stage_viii_minimal_test_set(self, fin_pop, fault_matrix, vector_map):
        if not fin_pop or self.cumulatedFaults == 0:
            return [], 0.0

        covered = np.zeros(self.cumulatedFaults, dtype=bool)
        selected = []
        remaining = list(fin_pop)

        while remaining:
            if self._check_time_limit():
                break

            # Pick vector covering the most NEW faults
            best_vec = max(
                remaining,
                key=lambda v: int(np.sum(fault_matrix[vector_map[v]] & ~covered))
            )

            new_faults = fault_matrix[vector_map[best_vec]] & ~covered
            if not np.any(new_faults):
                break

            covered |= fault_matrix[vector_map[best_vec]]
            selected.append(best_vec)
            remaining.remove(best_vec)

            if (int(np.sum(covered)) / self.cumulatedFaults) * 100 >= self.threshold:
                break

        final_coverage = (int(np.sum(covered)) / self.cumulatedFaults) * 100
        return selected, final_coverage

    # ── Main Run ─────────────────────────────────────────────────────────────

    def run(self):
        self._log("\n===== GA RUN STARTED =====")
        self._start_timer()

        self._log_detail("Stage I: Input Parameter Extraction")
        self.stage_i_input_Parameter_extratcion()
        self._log(f"Population size: {self.n} | Gates: {self.N} | Max TV: {self.max_no_of_TV}")

        self._log_detail("Stage II: Initial Test Vector Selection")
        init_population = self.stage_ii_TV_selection()
        self._log(f"Initial Population Size: {len(init_population)}")
        self._log_detail(f"Initial Population: {init_population}")

        for gen in range(self.max_generations):

            if self._check_time_limit():
                self._log("Terminated: Time limit reached.")
                break

            self.current_generation = gen
            self._log_detail(f"\n========== Generation {gen} ==========")

            # Fitness
            self._log_detail("Stage III: Fitness Evaluation")
            init_fitnesses, init_detected_matrix, init_vector_map, singleton_hit = \
                self.compute_fitness_for_population(init_population)

            if singleton_hit:
                self._log("Terminated: Single vector achieves 100% coverage.")
                self.best_coverage = 100.0
                self.best_vector_set = [list(init_vector_map.keys())[-1]]  # the winning vector
                self.detectedFaults = init_detected_matrix[-1]
                break

            # ── TLE or empty — abort generation immediately ───────────────────────
            if self._time_limit_exceeded or not init_fitnesses:
                self._log("Terminated: TLE or empty fitness — skipping remaining generations.")
                break

            max_fit = max(init_fitnesses)
            min_fit = min(init_fitnesses)
            avg_fit = sum(init_fitnesses) / len(init_fitnesses)
            self._log_detail(
                f"Fitness — Max: {max_fit:.4f} | Min: {min_fit:.4f} | Avg: {avg_fit:.4f}"
            )

            # Selection
            self._log_detail("Stage IV: Roulette Wheel Selection")
            parents = self.stage_iv_roulette_wheel_selection(init_fitnesses, init_population)
            self._log_detail(f"Selected Parents: {parents}")

            # Crossover
            self._log_detail("Stage V: Crossover")
            children = self.stage_v_crossover(parents)
            self._log_detail(f"Children: {children}")

            # Mutation
            self._log_detail("Stage VI: Mutation")
            mutated_children = self.stage_vi_mutation(children)
            self._log_detail(f"Mutated Children: {mutated_children}")

            # Population Update
            self._log_detail("Stage VII: Test Population Generation")
            fin_sorted_population, fin_sorted_fitnesses, \
            fin_detected_matrix, fin_vector_map = \
                self.stage_vii_test_population_generation(init_population, mutated_children)

            self._log_detail(f"Sorted Population: {fin_sorted_population}")
            self._log_detail(f"Sorted Fitnesses:  {fin_sorted_fitnesses}")

            # Coverage
            combined_detected_list = np.any(fin_detected_matrix, axis=0)
            detected_faults = int(np.sum(combined_detected_list))
            fault_coverage = (detected_faults / self.cumulatedFaults) * 100
            self._log_detail(
                f"Coverage — Detected: {detected_faults} / {self.cumulatedFaults}"
                f" = {fault_coverage:.2f}%"
            )

            # Minimization
            if not self.skip_minimization:
                self._log_detail("Stage VIII: Minimal Test Set Reduction (Greedy)")
                min_set, min_cov = self.stage_viii_minimal_test_set(
                    fin_sorted_population, fin_detected_matrix, fin_vector_map
                )
                self._log_detail(f"Minimal Set Coverage: {min_cov:.2f}%")

                if min_cov >= fault_coverage:
                    fault_coverage = min_cov
                    test_vectors = min_set
                    self._log_detail("Minimal set accepted.")
                else:
                    test_vectors = fin_sorted_population
                    self._log_detail("Original sorted population retained.")
            else:
                test_vectors = fin_sorted_population

            # Best Update
            if fault_coverage > self.best_coverage:
                self.best_coverage = fault_coverage
                self.best_vector_set = test_vectors
                self.detectedFaults = combined_detected_list
                self._log_detail(f"New best coverage: {self.best_coverage:.2f}%")

            # Compact Log
            self._log_compact(
                f"Gen {gen:03d} | "
                f"MaxFit: {max_fit:.4f} | "
                f"AvgFit: {avg_fit:.4f} | "
                f"Cov: {fault_coverage:6.2f}% | "
                f"Best: {self.best_coverage:6.2f}% | "
                f"Pop: {len(test_vectors)}"
            )

            # Threshold Check
            if fault_coverage >= self.threshold:
                self._log("Terminated: Coverage threshold reached.")
                break

            init_population = test_vectors[:self.population_size]
            self._log_detail(f"Next gen population (trimmed): {len(init_population)}")

            gc.collect()

        self._log(f"===== GA RUN COMPLETED — Best Coverage: {self.best_coverage:.2f}% =====")
        self._log_detail(f"Final Best Vector Set: {self.best_vector_set}")

        return self.save_results()

    # ── Save Results ─────────────────────────────────────────────────────────

    def save_results(self):
        self._update_execution_time()

        return {
            "Circuit Name":         self.circuit["Circuit Name"],
            "No of Lines":          self.circuit["No of Lines"],
            "No of Gates":          self.circuit["No of Gates"],
            "Fault Model":          self.faultModel,
            "Actual Generations":   self.current_generation + 1,
            "Total Faults":         self.cumulatedFaults,
            "Detected Faults":      int(np.sum(self.detectedFaults)) if self.detectedFaults is not None else 0,
            "Fault Coverage":       self.best_coverage,
            "Test Set Size":        len(self.best_vector_set),
            "Execution Time":       round(self.execution_time, 4),
            "Time Limit Exceeded":  self._time_limit_exceeded,
            "Minimization Skipped": self.skip_minimization,
        }