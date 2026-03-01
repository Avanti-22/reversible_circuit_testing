from typing import List, Tuple, Set
import time
import random
import itertools
import numpy as np
import gc
from Utils.SimulatorsfaultCoverageFindingUtilities import *
# from SimulatorsfaultCoverageFindingUtilities import *

class TimeLimitExceeded(Exception):
    pass


class GeneticAlgorithm:

    def __init__(self, circuit: dict, faultModel: str = "SMGF",
                 population_size: int = None, max_generations: int = 100, threshold: float = 100.0,
                 time_limit_seconds: float = None, skip_minimization=None):

        self.circuit = circuit
        self.faultModel = faultModel
        self.threshold = threshold
        self.population_size = circuit["No of Lines"]
        self.max_generations = max_generations
        self.time_limit_seconds = time_limit_seconds if time_limit_seconds else 300.0

        if skip_minimization is None:
            self.skip_minimization = circuit["No of Lines"] >= 12
        else:
            self.skip_minimization = skip_minimization

        self.current_generation = None
        self.best_coverage = 0.0
        self.best_vector_set = []
        self.cumulatedFaults = None
        self.detectedFaults = None
        self.execution_time = 0.0

        self._start_time = None
        self._time_limit_exceeded = False

        # ⭐ Cache for Stage III
        self.fault_cache = {}

    # --------------------------------------------------

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

    # --------------------------------------------------

    def stage_i_input_Parameter_extratcion(self):
        self.n = self.circuit["No of Lines"]
        self.N = self.circuit["No of Gates"]
        self.max_no_of_TV = 2 ** self.n

    # --------------------------------------------------

    def stage_ii_TV_selection(self, test_Size=None):

        if test_Size is None:
            test_Size = self.n

        return random.sample(range(self.max_no_of_TV), test_Size)

    # --------------------------------------------------

    def represent_the_vec_in_binary(self, testVector):
        return [int(x) for x in format(testVector, f'0{self.n}b')]

    # --------------------------------------------------

    def get_detected_faults_row(self, faultFreeOutput, faultyOutputs):
        return np.array(
            [faulty != faultFreeOutput for faulty in faultyOutputs],
            dtype=bool
        )

    # --------------------------------------------------

    def stage_iii_fitness_function_computation(self, vector):

        if vector in self.fault_cache:
            return self.fault_cache[vector]

        binary_vector = self.represent_the_vec_in_binary(vector)

        faultFreeOutput = simulate_circuit(self.circuit, binary_vector)
        faultyOutputs = get_all_faulty_outputs(self.circuit, binary_vector, self.faultModel)

        self.cumulatedFaults = len(faultyOutputs)

        detectedFaultArray = self.get_detected_faults_row(faultFreeOutput, faultyOutputs)

        detected = np.sum(detectedFaultArray)
        coverage = (detected / self.cumulatedFaults) * 100 if self.cumulatedFaults else 0

        self.fault_cache[vector] = (coverage, detectedFaultArray)
        return coverage, detectedFaultArray

    # --------------------------------------------------

    def compute_fitness_for_population(self, population):

        fitnesses = []
        rows = []
        vector_map = {}

        for i, vec in enumerate(population):
            coverage, detected_faults_row = self.stage_iii_fitness_function_computation(vec)
            fitnesses.append(coverage)
            rows.append(detected_faults_row)
            vector_map[vec] = i

            if coverage >= self.threshold:
                break

        return fitnesses, np.vstack(rows), vector_map

    # --------------------------------------------------

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

    # --------------------------------------------------

    def represent_bin_in_int(self, bin_vec_list):
        return int("".join(map(str, bin_vec_list)), 2)

    # --------------------------------------------------

    def stage_v_crossover(self, parent_pairs):

        children = []

        for p1, p2 in parent_pairs:
            b1 = self.represent_the_vec_in_binary(p1)
            b2 = self.represent_the_vec_in_binary(p2)

            cp = random.randint(1, self.n - 1)
            child = self.represent_bin_in_int(b1[:cp] + b2[cp:])
            children.append(child)

        return children

    # --------------------------------------------------

    def stage_vi_mutation(self, children):

        mutated = []

        maxVal = (10 ** (self.current_generation + 1)) - 1

        for child in children:
            if random.randint(0, maxVal) < 10:

                cb = self.represent_the_vec_in_binary(child)
                flip = random.randint(0, self.n - 1)
                cb[flip] ^= 1

                mutated.append(self.represent_bin_in_int(cb))
            else:
                mutated.append(child)

        return mutated

    # --------------------------------------------------

    def build_fault_matrix(self, population):

        rows = []
        vector_map = {}

        for i, vec in enumerate(population):
            _, faults = self.stage_iii_fitness_function_computation(vec)
            rows.append(faults)
            vector_map[vec] = i

        return np.vstack(rows), vector_map

    # --------------------------------------------------

    def stage_vii_test_population_generation(self, init_pop, child_pop):

        combined_population = list(set(init_pop + child_pop))
        combined_fitnesses, combined_fault_matrix, combined_vector_map = self.compute_fitness_for_population(combined_population)

        if not combined_fitnesses:
            return init_pop, [], {}

        sorted_fitnesses, sorted_pop = zip(*sorted(zip(combined_fitnesses, combined_population), reverse=True))
        return list(sorted_pop), sorted_fitnesses, combined_fault_matrix, combined_vector_map

    # --------------------------------------------------

    def stage_viii_minimal_test_set(self, fin_pop, fault_matrix, vector_map, L=None):

        if L is None:
            L = max(2, self.n // 2)

        best_cov = 0
        best_set = []

        while L <= self.n:

            if self._check_time_limit():
                break

            for combo in itertools.combinations(fin_pop, L):

                idx = [vector_map[v] for v in combo]

                combined = np.any(fault_matrix[idx], axis=0)

                detected = np.sum(combined)
                coverage = (detected / self.cumulatedFaults) * 100

                if coverage >= self.threshold:
                    return list(combo), coverage

                if coverage > best_cov:
                    best_cov = coverage
                    best_set = list(combo)

            L += 1

        return best_set, best_cov

    # --------------------------------------------------

    def run(self, verbose=True, compaction = False):

        if compaction:

            if verbose:
                print("\n===== GA RUN STARTED =====")

            self._start_timer()
            self.stage_i_input_Parameter_extratcion()
            init_population = self.stage_ii_TV_selection()

            if verbose:
                print(f"Initial Population Size: {len(init_population)}")

            for gen in range(self.max_generations):

                if self._check_time_limit():
                    if verbose:
                        print("Terminated: Time limit reached.")
                    break

                self.current_generation = gen

                # ---- Fitness ----
                init_fitnesses, init_detected_matrix, init_vector_map = \
                    self.compute_fitness_for_population(init_population)

                if not init_fitnesses:
                    if verbose:
                        print("Terminated: Empty fitness list.")
                    break

                max_fit = max(init_fitnesses)
                avg_fit = sum(init_fitnesses) / len(init_fitnesses)

                # ---- GA Operators ----
                parents = self.stage_iv_roulette_wheel_selection(
                    init_fitnesses, init_population
                )

                children = self.stage_v_crossover(parents)
                mutated_children = self.stage_vi_mutation(children)

                fin_sorted_population, fin_sorted_fitnesses, \
                fin_detected_matrix, fin_vector_map = \
                    self.stage_vii_test_population_generation(
                        init_population, mutated_children
                    )

                # ---- Coverage ----
                combined_detected_list = np.any(fin_detected_matrix, axis=0)
                detectedFaults = np.sum(combined_detected_list)
                faultCoverage = (detectedFaults / self.cumulatedFaults) * 100

                # ---- Minimization ----
                if not self.skip_minimization:
                    min_set, min_cov = self.stage_viii_minimal_test_set(
                        fin_sorted_population,
                        fin_detected_matrix,
                        fin_vector_map
                    )

                    if min_cov > faultCoverage:
                        faultCoverage = min_cov
                        testVectors = min_set
                    else:
                        testVectors = fin_sorted_population
                else:
                    testVectors = fin_sorted_population

                # ---- Best Update ----
                if faultCoverage > self.best_coverage:
                    self.best_coverage = faultCoverage
                    self.best_vector_set = testVectors
                    self.detectedFaults = combined_detected_list

                # ---- Compact Log Line ----
                if verbose:
                    print(
                        f"Gen {gen:03d} | "
                        f"MaxFit: {max_fit:.4f} | "
                        f"AvgFit: {avg_fit:.4f} | "
                        f"Cov: {faultCoverage:6.2f}% | "
                        f"Best: {self.best_coverage:6.2f}% | "
                        f"Pop: {len(testVectors)}"
                    )

                # ---- Threshold ----
                if faultCoverage >= self.threshold:
                    if verbose:
                        print("Terminated: Threshold reached.")
                    break

                init_population = testVectors[:self.population_size]
                gc.collect()

            if verbose:
                print("===== GA RUN COMPLETED =====")
                print(f"Final Best Coverage: {self.best_coverage:.2f}%\n")

            return self.save_results()
            
        
        else:
            
            if verbose:
                print("\n========== GA RUN STARTED ==========\n")

            self._start_timer()

            if verbose:
                print("Stage I: Input Parameter Extraction")
            self.stage_i_input_Parameter_extratcion()

            if verbose:
                print("Stage II: Initial Test Vector Selection")
            init_population = self.stage_ii_TV_selection()

            if verbose:
                print(f"Initial Population Size: {len(init_population)}")
                print(f"Initial Population: {init_population}\n")

            for gen in range(self.max_generations):

                if self._check_time_limit():
                    if verbose:
                        print("Time limit reached. Terminating GA.")
                    break

                self.current_generation = gen

                if verbose:
                    print(f"\n========== Generation {gen} ==========")

                # -------- Fitness Computation --------
                if verbose:
                    print("Stage III: Fitness Evaluation")

                init_fitnesses, init_detected_matrix, init_vector_map = \
                    self.compute_fitness_for_population(init_population)

                if not init_fitnesses:
                    if verbose:
                        print("Fitness list empty. Terminating.")
                    break

                if verbose:
                    print(f"Fitness Values: {init_fitnesses}")
                    print(f"Max Fitness: {max(init_fitnesses)}")
                    print(f"Min Fitness: {min(init_fitnesses)}")
                    print(f"Avg Fitness: {sum(init_fitnesses)/len(init_fitnesses)}")

                # -------- Selection --------
                if verbose:
                    print("\nStage IV: Roulette Wheel Selection")

                parents = self.stage_iv_roulette_wheel_selection(
                    init_fitnesses, init_population
                )

                if verbose:
                    print(f"Selected Parents: {parents}")

                # -------- Crossover --------
                if verbose:
                    print("\nStage V: Crossover")

                children = self.stage_v_crossover(parents)

                if verbose:
                    print(f"Children: {children}")

                # -------- Mutation --------
                if verbose:
                    print("\nStage VI: Mutation")

                mutated_children = self.stage_vi_mutation(children)

                if verbose:
                    print(f"Mutated Children: {mutated_children}")

                # -------- Population Update --------
                if verbose:
                    print("\nStage VII: Test Population Generation")

                fin_sorted_population, fin_sorted_fitnesses, \
                fin_detected_matrix, fin_vector_map = \
                    self.stage_vii_test_population_generation(
                        init_population, mutated_children
                    )

                if verbose:
                    print(f"Sorted Population: {fin_sorted_population}")
                    print(f"Sorted Fitnesses: {fin_sorted_fitnesses}")

                # -------- Coverage Computation --------
                combined_detected_list = np.any(fin_detected_matrix, axis=0)
                detectedFaults = np.sum(combined_detected_list)
                faultCoverage = (detectedFaults / self.cumulatedFaults) * 100

                if verbose:
                    print("\nCoverage Computation:")
                    print(f"Detected Faults: {detectedFaults}")
                    print(f"Total Faults: {self.cumulatedFaults}")
                    print(f"Fault Coverage: {faultCoverage:.2f}%")

                # -------- Minimization --------
                if not self.skip_minimization:
                    if verbose:
                        print("\nStage VIII: Minimal Test Set Reduction")

                    min_set, min_cov = self.stage_viii_minimal_test_set(
                        fin_sorted_population,
                        fin_detected_matrix,
                        fin_vector_map
                    )

                    if verbose:
                        print(f"Minimal Set Coverage: {min_cov:.2f}%")
                        print(f"Minimal Set: {min_set}")

                    if min_cov >= faultCoverage:
                        faultCoverage = min_cov
                        testVectors = min_set
                        if verbose:
                            print("Minimal set accepted (better or equal coverage).")
                    else:
                        testVectors = fin_sorted_population
                        if verbose:
                            print("Original sorted population retained.")
                else:
                    testVectors = fin_sorted_population

                # -------- Best Coverage Update --------
                if faultCoverage > self.best_coverage:
                    self.best_coverage = faultCoverage
                    self.best_vector_set = testVectors
                    self.detectedFaults = combined_detected_list

                    if verbose:
                        print("\nNew Best Coverage Achieved!")
                        print(f"Best Coverage Updated To: {self.best_coverage:.2f}%")
                        print(f"Best Vector Set: {self.best_vector_set}")

                # -------- Threshold Check --------
                if faultCoverage >= self.threshold:
                    if verbose:
                        print("\nThreshold reached. Terminating GA.")
                    break

                if verbose:
                    print(f"\nTest Vectors for Next Generation: {testVectors}")

                init_population = testVectors[:self.population_size]

                if verbose:
                    print(f"Next Generation Population (trimmed): {init_population}")

                gc.collect()

            if verbose:
                print("\n========== GA RUN COMPLETED ==========")
                print(f"Final Best Coverage: {self.best_coverage:.2f}%")
                print(f"Final Best Vector Set: {self.best_vector_set}\n")

            return self.save_results()

    # --------------------------------------------------

    def save_results(self):

        self._update_execution_time()

        return {
            "Circuit Name": self.circuit["Circuit Name"],
            "No of Lines": self.circuit["No of Lines"],
            "No of Gates": self.circuit["No of Gates"],
            "Fault Model": self.faultModel,
            # "Population Size": self.population_size,
            # "Max Generations": self.max_generations,
            "Actual Generations": self.current_generation + 1,
            # "Threshold": self.threshold,
            "Total Faults": self.cumulatedFaults,
            "Detected Faults": int(np.sum(self.detectedFaults)) if self.detectedFaults is not None else 0,
            "Fault Coverage": self.best_coverage,
            "Minimal Vector Set": self.best_vector_set,
            "Test Set Size": len(self.best_vector_set),
            "Execution Time": self.execution_time,
            "Time Limit Exceeded": self._time_limit_exceeded,
            "Minimization Skipped": self.skip_minimization,
            "Detected Faults List": self.detectedFaults.tolist() if self.detectedFaults is not None else [] 
        }