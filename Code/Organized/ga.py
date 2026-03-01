from typing import List, Tuple, Set
import time
import random
import itertools
import numpy as np
from Utils.SimulatorsfaultCoverageFindingUtilities import *


class TimeLimitExceeded(Exception):
    pass


class GeneticAlgorithm:
        """Genetic Algorithm for CMGF Test Generation using Random Search"""
        
        def __init__(self, circuit: dict, faultModel: str = "SMGF", 
                    population_size: int = None, max_generations: int = 100, threshold: float = 100.0,
                    time_limit_seconds: float = None):
            """
            Initialize the GA
            
            Args:
                circuit: ReversibleCircuit object
                threshold: Desired fault coverage percentage
                population_size: Size of population (default: n)
                max_generations: Maximum number of generations
            """
            self.circuit = circuit
            self.faultModel = faultModel
            self.threshold = threshold
            self.population_size = population_size or circuit["No of Lines"]
            self.max_generations = max_generations
            self.time_limit_seconds = time_limit_seconds
            self.current_generation = None
            self.best_coverage = 0.0
            self.best_vector_set = []
            self.cumulatedFaults = None
            self.detectedFaults = []
            self.execution_time = 0.0
            self._start_time = None

        def _start_timer(self):
            self._start_time = time.monotonic()

        def _update_execution_time(self):
            if self._start_time is not None:
                self.execution_time = time.monotonic() - self._start_time

        def _check_time_limit(self):
            if self.time_limit_seconds is None:
                return
            self._update_execution_time()
            if self.execution_time >= self.time_limit_seconds:
                raise TimeLimitExceeded()
        
        
        def stage_i_input_Parameter_extratcion(self):
            self.n = self.circuit["No of Lines"]
            self.N = self.circuit["No of Gates"]
            self.max_no_of_TV = 2**self.n
            
        
            
               
        def stage_ii_TV_selection(self) -> List[int]:
            """
            Stage II: Test Vector Selection (Random Search)
            
            Args:
                size: Number of vectors to select (default: population_size)
                
            Returns:
                List of randomly selected unique vectors
            """
                
            possible_valid_vectors = list(range(self.max_no_of_TV))
            
            initPop = random.sample(possible_valid_vectors, self.n)
            self.current_generation = 0
            return initPop
        
        def represent_the_vec_in_binary(self, testVector):
            
            binaryVector = []
            vec = format(testVector, f'0{self.n}b')
            for bit in vec:
                binaryVector.append(int(bit))
                
            return binaryVector
        
        
        def obtain_detected_fault_matrix(self, faultFreeOutput, faultyOutputs):
            
            detectedFaultsForCurrentTV= []
            for i in range(len(faultyOutputs)):
                
                if(faultyOutputs[i] != faultFreeOutput):
                    detectedFaultsForCurrentTV.append(1)
                else:
                    detectedFaultsForCurrentTV.append(0)
            return detectedFaultsForCurrentTV
        
        
        # def get_all_faulty_outputs()
        
        
        def stage_iii_fitness_function_computation(self, vector: int):
            """
            Stage III: Fitness Function Computation
            
            Args:
                vector: Test vector (decimal)
                
            Returns:
                Tuple of (fault_coverage_percentage, set_of_detected_faults)
            """
            # Convert to binary for processing
            binary_vector = self.represent_the_vec_in_binary(vector)
            
            # Compute fault-free output
            faultFreeOutput = simulate_circuit(self.circuit, binary_vector)
            faultyOutputs = []
            
            faultyOutputs = get_all_faulty_outputs(self.circuit, binary_vector, self.faultModel)
            
            self.cumulatedFaults = len(faultyOutputs)
            
            detectedFaultMatrix = [[]]
            detectedFaultList = self.obtain_detected_fault_matrix(faultFreeOutput, faultyOutputs)
            detectedFaultMatrix.append(detectedFaultList)
            
            detected = detectedFaultList .count(1)
            
            fault_coverage = (detected/self.cumulatedFaults)*100 if self.cumulatedFaults > 0 else 0
            
            return fault_coverage
        
        def compute_fitness_for_population(self, initPop):
            
            fitnessFunction= []
            
            for i in range(len(initPop)):

                fitnessFunction.append(self.stage_iii_fitness_function_computation(initPop[i]))
    
                if(fitnessFunction[i]>= self.threshold):
                    # display and exit
                    pass
            
            return fitnessFunction    
        
        def stage_iv_roulette_wheel_selection(self, fitnessFunction, population) -> List[Tuple[int, int]]:
            """
            Stage IV: Roulette Wheel Selection
            
            Args:
                fitness_data: List of (vector, fitness, detected_faults)
                num_pairs: Number of parent pairs to select
                
            Returns:
                List of parent pairs
            """

            
            parent_pairs = []
            
            # Handle case where all fitnesses are zero
            total_fitness = sum(fitnessFunction)
            if total_fitness == 0:
                probabilities = [1.0 / len(fitnessFunction)] * len(fitnessFunction)
            else:
                probabilities = [f / total_fitness for f in fitnessFunction]
            
        
            for _ in range(self.n):
                parent1 = random.choices(population, weights=probabilities)[0]
                parent2 = random.choices(population, weights=probabilities)[0]
                parent_pairs.append((parent1, parent2))
            
            return parent_pairs
        
        def represent_bin_in_int(self, bin_vec_list):
            bit_str= []
            
            for bit in bin_vec_list:
                
                bit_str.append(str(bin_vec_list[bit]))
                
            child = int(("").join(bit_str), 2)
            
            return child
        
        
        def stage_v_crossover(self, parent_pairs: List[Tuple[int, int]]) -> List[int]:
            """
            Stage V: Reproduction and Cross-Over
            
            Args:
                parent_pairs: List of (parent1, parent2) tuples
                
            Returns:
                List of child vectors
            """
            children = []
            
            for parent1, parent2 in parent_pairs:
                self._check_time_limit()
                # Convert to binary
                bin1 = self.represent_the_vec_in_binary(parent1)
                bin2 = self.represent_the_vec_in_binary(parent2)
                
                # Random crossover point
                crossover_point = random.randint(1, self.n - 1)
                
                # Create child by combining parts
                child_bin = bin1[:crossover_point] + bin2[crossover_point:]
                
                child = self.represent_bin_in_int(child_bin)
                children.append(child)
                
            return children
        
        def stage_vi_mutation(self, children: List[int]) -> List[int]:
            """
            Stage VI: Mutation
            
            Args:
                children: List of child vectors
                
            Returns:
                Mutated children
            """
            # Mutation probability decreases exponentially with generations
            maxVal = 10**(self.current_generation+1)-1
            # print(maxVal)           
            mutated_children = []
            
            for child in children:
                self._check_time_limit()

                num = random.randint(0, maxVal)
                # print(num)
                if num < 10:
        
                    # Convert to binary
                    child_bin = self.represent_the_vec_in_binary(child)
                    # print(child_bin)
                    # Flip a random bit
                    flip_position = random.randint(0, self.n - 1)
                    child_bin[flip_position] = 0 if child_bin[flip_position] == 1 else 1
                    
                    # Convert back to decimal
                    
                    bit_str= []
                    for bit in child_bin:
                        bit_str.append(child_bin[bit])
                    
                    
                    mutated_child = self.represent_bin_in_int(bit_str)
                    
                    mutated_children.append(mutated_child)
                else:
                    mutated_children.append(child)
            
            return mutated_children
        
        def stage_vii_test_population_generation(self, init_pop: List[int], 
                                                child_pop: List[int]) -> List[Tuple[int, float, Set[int]]]:
            """
            Stage VII: Test Population Generation
            
            Args:
                init_pop: Initial population
                child_pop: Child population
                
            Returns:
                Final population sorted by fitness (descending)
            """
            # Combine populations
            combined_pop = list(set(init_pop + child_pop))  # Remove duplicates
            
            # Compute fitness for all
            fitness_data = self.compute_population_fitness(combined_pop)
            
            # Sort by fitness (descending)
            sorted_pop = sorted(fitness_data, key=lambda x: x[1], reverse=True)
            
            return sorted_pop
        
        def stage_viii_minimal_test_set(self, fin_pop: List[Tuple[int, float, Set[int]]], 
                                        L: int = None):
            """
            Stage VIII: Minimal Test Set Generation
            
            Args:
                fin_pop: Final population with fitness data
                L: Initial combination size
                
            Returns:
                Tuple of (test_set, coverage_percentage)
            """
            if L is None:
                L = max(1, self.circuit["No of Lines"] // 2)
            
            vectors = [item[0] for item in fin_pop]
            
            # Try combinations of increasing size
            for combo_size in range(L, len(vectors) + 1):
                self._check_time_limit()
                for combo in itertools.combinations(vectors, combo_size):
                    self._check_time_limit()
                    coverage, _ = self.compute_combined_coverage(list(combo))
                    
                    if coverage >= self.threshold:
                        return list(combo), coverage
            
            # If no combination meets threshold, return best so far
            best_combo, best_cov = self.find_best_combination(vectors)
            return best_combo, best_cov
        
        def compute_combined_coverage(self, test_set: List[int]) -> Tuple[float, Set[int]]:
            """
            Compute combined fault coverage for a set of test vectors
            
            Args:
                test_set: List of test vectors
                
            Returns:
                Tuple of (coverage_percentage, all_detected_faults)
            """
            all_detected = set()
            
            for vector in test_set:
                self._check_time_limit()
                _, detected = self.stage_iii_fitness_computation(vector)
                all_detected.update(detected)
            self.detectedFaults = all_detected
            coverage = (len(all_detected) / self.cumulatedFaults) * 100 if self.cumulatedFaults > 0 else 0
            return coverage, all_detected
        
        def find_best_combination(self, vectors: List[int]):
            """Find the best combination of vectors for maximum coverage"""
            best_combo = []
            best_coverage = 0.0
            
            for size in range(1, min(len(vectors) + 1, self.circuit["No of Lines"] + 1)):
                self._check_time_limit()
                for combo in itertools.combinations(vectors[:min(10, len(vectors))], size):
                    self._check_time_limit()
                    coverage, _ = self.compute_combined_coverage(list(combo))
                    if coverage > self.best_coverage:
                        best_coverage = coverage
                        best_combo = list(combo)
                        
            return best_combo, best_coverage            
        
        
        def MULTIPLY(self, populn, FitnessFunction):
            for i in range (self.n):
                               
                print("Stage 4")
                # Stage IV: Roulette Wheel Selection
                parent_pairs = self.stage_iv_roulette_wheel_selection(FitnessFunction, populn)
                
                print("Stage 5")
                # Stage V: Crossover
                children = self.stage_v_crossover(parent_pairs)
                
                print("Stage 6")
                # Stage VI: Mutation
                mutated_children = self.stage_vi_mutation(children)
                
                #  remove the repeated children and find fitness
                uniqueChildren = list(set(mutated_children))
                print(uniqueChildren)
                
                print("Stage 3")
                # Stage III: Fitness Computation
                FitnessFunction, detected = self.compute_fitness_for_population(uniqueChildren)
                
                self.MULTIPLY(uniqueChildren, FitnessFunction)

        
        def run(self, verbose: bool = True) -> Tuple[List[int], float]:
            """
            Run the complete GA algorithm
            
            Args:
                verbose: Print progress information
                
            Returns:
                Tuple of (final_test_set, fault_coverage_percentage)
            """
            self._start_timer()
            
            print("Stage 1")
            # Stage I: Input Parameter Extraction
            self.stage_i_input_Parameter_extratcion()
    
            if verbose:
                print(f"=== {self.faultModel} GA with Random Search ===")
                print(f"Circuit: {self.circuit["Circuit Name"]}")
                print(f"Threshold: {self.threshold}%")
                print(self.n)
                print(self.N)
                print(self.max_no_of_TV)
            
            print("Stage 2")
            # Stage II: Random Search - Initial Population
            populn = self.stage_ii_TV_selection()

            
            print("stages 3 - 9")
            try:
                for generation in range(self.max_generations):
                    self._check_time_limit()
                    self.current_generation = generation
                    
                    if verbose:
                        print(f"Generation {generation + 1}:")
                        print(f"  InitPop: {populn}")
                    
                    print("Stage 3")
                    # Stage III: Fitness Computation
                    fitnessFunct = self.compute_fitness_for_population(populn)
                    
                    print("Stage 4")
                    # Stage IV: Roulette Wheel Selection
                    parent_pairs = self.stage_iv_roulette_wheel_selection(fitnessFunct, populn)
                    
                    print("Stage 5")
                    # Stage V: Crossover
                    children = self.stage_v_crossover(parent_pairs)
                    
                    print("Stage 6")
                    # Stage VI: Mutation
                    mutated_children = self.stage_vi_mutation(children)
                    
                    print("Stage 7")
                    # Stage VII: Test Population Generation
                    fin_pop = self.stage_vii_test_population_generation(init_pop, mutated_children)
                    
                    if verbose:
                        print(f"  FinPop (top 5): {[item[0] for item in fin_pop[:5]]}")
                        print(f"  Best fitness: {fin_pop[0][1]:.2f}%")
                    
                    print("Stage 8")
                    # Stage VIII: Minimal Test Set Generation
                    test_set, coverage  = self.stage_viii_minimal_test_set(fin_pop)
                    
                    
                    if verbose:
                        print(f"  Test Set: {test_set}")
                        print(f"  Coverage: {coverage:.2f}%\n")
                    
                    # Update best coverage
                    if coverage > self.best_coverage:
                        self.best_coverage = coverage
                        self.best_vector_set = test_set
                    
                        
                    # Check if threshold met
                    if coverage >= self.threshold:
                        if verbose:
                            print(f"=== Threshold Met in Generation {generation + 1} ===")
                            print(f"Final Test Set: {self.best_vector_set}")
                            print(f"Fault Coverage: {self.best_coverage:.2f}%")
                        return self.save_results()
                    
                    print("Stage 9")
                    # Stage IX: Filial Generation (prepare next generation)
                    # Use best vectors and fill remaining with random selection
                    num_best = max(1, self.population_size // 2)
                    best_vectors = [item[0] for item in fin_pop[:num_best]]
                    
                    # Fill remaining slots with random selection
                    remaining_slots = self.population_size - len(best_vectors)
                    if remaining_slots > 0:
                        random_vectors = self.stage_ii_random_selection(remaining_slots)
                        init_pop = best_vectors + random_vectors
                    else:
                        init_pop = best_vectors
                        
                        
            except TimeLimitExceeded:
                if verbose:
                    print("=== Time Limit Exceeded ===")
                    print(f"Final Test Set: {self.best_vector_set}")
                    print(f"Fault Coverage: {self.best_coverage:.2f}%")
                return self.save_results()
            
            # If max generations reached without meeting threshold
            if verbose:
                print(f"=== Max Generations Reached ===")
                print(f"Final Test Set: {self.best_vector_set}")
                print(f"Fault Coverage: {self.best_coverage:.2f}%")
                    
            
            return self.save_results()
            
        
        def save_results(self):
            self._update_execution_time()
            results =  {
                "Circuit Name": self.circuit["Circuit Name"],
                "No of Lines": self.circuit["No of Lines"],
                "No of Gates": self.circuit["No of Gates"],
                "Library": self.circuit["Library Type"],
                "Fault Model": self.faultModel,
                "Population Size": self.population_size,
                "Threshold": self.threshold,
                "Total Faults": self.cumulatedFaults,
                "Detected Faults": len(self.detectedFaults),
                "Fault Coverage": self.best_coverage,
                "Minimal Vector Set": self.best_vector_set,
                "Execution Time": self.execution_time,
                "Detected Fault Locations": self.detectedFaults
            }
            # print(results)
            
            return results
            
            
            
