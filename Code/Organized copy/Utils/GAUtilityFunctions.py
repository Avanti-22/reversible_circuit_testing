from typing import List, Tuple, Set
import time
import random
import itertools
import numpy as np
from .SimulatorsfaultCoverageFindingUtilities import *



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
            self.population_size = population_size or circuit.n
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
               
        def stage_ii_random_selection(self, size: int = None) -> List[int]:
            """
            Stage II: Test Vector Selection (Random Search)
            
            Args:
                size: Number of vectors to select (default: population_size)
                
            Returns:
                List of randomly selected unique vectors
            """
            if size is None:
                size = self.population_size
                
            # Randomly select unique vectors from [0, 2^n - 1]
            available_vectors = list(range(2**self.circuit["No of Lines"]))
            # print(len(available_vectors))
            selected = random.sample(available_vectors, min(size, len(available_vectors)))
            # print(len(selected))
            return selected
        
        def convert_to_binary_vec(self, input_vector, maxValue = None):
            
            if maxValue is None:
                maxValue = self.circuit["No of Lines"]
            
            binaryVector = []
            vec = format(input_vector, f'0{maxValue}b')
            for bit in vec:
                binaryVector.append(int(bit))
                
            return binaryVector
        
        def stage_iii_fitness_computation(self, vector: int) -> Tuple[float, int, Set[int]]:
            """
            Stage III: Fitness Function Computation
            
            Args:
                vector: Test vector (decimal)
                
            Returns:
                Tuple of (fault_coverage_percentage, set_of_detected_faults)
            """
            # Convert to binary for processing
            binary_vector = self.convert_to_binary_vec(vector)
            # binary_vector = format(vector, f'0{self.circuit.n}b')
            
            # Compute fault-free output
            # fault_free_output = simulate_circuit(binary_vector, vector)
            
            self.cumulatedFaults, detectedFaults = calculate_FC_for_fault_model(self.circuit, binary_vector, self.faultModel)
            
            detected_faults = set(detectedFaults)
            
            fault_coverage = (len(detected_faults)/self.cumulatedFaults)*100 if self.cumulatedFaults > 0 else 0
            
            
            
            # # Simulate CMGF: skip each gate one at a time
            # for gate_idx in range(self.circuit.N):
            #     faulty_output = self.circuit.compute_output(vector, skip_gate=gate_idx)
                
            #     # If outputs differ, fault is detected
            #     if faulty_output != fault_free_output:
            #         detected_faults.add(gate_idx)
            
            # # Calculate fault coverage
            # cumulated_fault = self.circuit.N
            # fault_coverage = (len(detected_faults) / cumulated_fault) * 100 if cumulated_fault > 0 else 0
            
            return fault_coverage, detected_faults
        
        def compute_population_fitness(self, population: List[int]) -> List[Tuple[int, float, Set[int]]]:
            """
            Compute fitness for entire population
            
            Returns:
                List of tuples (vector, fitness, detected_faults)
            """
            fitness_data = []
            for vector in population:
                self._check_time_limit()
                coverage, detected = self.stage_iii_fitness_computation(vector)
                fitness_data.append((vector, coverage, detected))
            
            return fitness_data
        
        def stage_iv_roulette_wheel_selection(self, fitness_data: List[Tuple[int, float, Set[int]]], 
                                            num_pairs: int = None) -> List[Tuple[int, int]]:
            """
            Stage IV: Roulette Wheel Selection
            
            Args:
                fitness_data: List of (vector, fitness, detected_faults)
                num_pairs: Number of parent pairs to select
                
            Returns:
                List of parent pairs
            """
            if num_pairs is None:
                num_pairs = len(fitness_data) // 2
            
            vectors = [item[0] for item in fitness_data]
            fitnesses = [item[1] for item in fitness_data]
            detected = [item[2] for item in fitness_data]
            
            # for i, item in enumerate (fitness_data):
            #     print(f"vector{i} => {item[0]}, detected: {item[2]}, fitness: {item[1]}")
            
            # Handle case where all fitnesses are zero
            total_fitness = sum(fitnesses)
            if total_fitness == 0:
                probabilities = [1.0 / len(fitnesses)] * len(fitnesses)
            else:
                probabilities = [f / total_fitness for f in fitnesses]
            
            parent_pairs = []
            for _ in range(num_pairs):
                parent1 = random.choices(vectors, weights=probabilities)[0]
                parent2 = random.choices(vectors, weights=probabilities)[0]
                parent_pairs.append((parent1, parent2))
            
            return parent_pairs
        
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
                bin1 = self.convert_to_binary_vec(parent1)
                bin2 = self.convert_to_binary_vec(parent2)
                
                # Random crossover point
                crossover_point = random.randint(1, self.circuit["No of Lines"] - 1)
                
                # Create child by combining parts
                child_bin = bin1[:crossover_point] + bin2[crossover_point:]
                
                bit_str= []
                for bit in child_bin:
                    bit_str.append(str(child_bin[bit]))
                
                child = int(("").join(bit_str), 2)
                
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
            mutation_prob = 0.3 * np.exp(-0.1 * self.current_generation)
            
            mutated_children = []
            
            for child in children:
                self._check_time_limit()
                if random.random() < mutation_prob:
                    # Convert to binary
                    child_bin = list(self.convert_to_binary_vec(child))
                    
                    # Flip a random bit
                    flip_position = random.randint(0, self.circuit["No of Lines"] - 1)
                    child_bin[flip_position] = 0 if child_bin[flip_position] == 1 else 1
                    
                    # Convert back to decimal
                    
                    bit_str= []
                    for bit in child_bin:
                        bit_str.append(str(child_bin[bit]))
                    
                    
                    mutated_child = int(''.join(bit_str), 2)
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
            # Stage I: Input Parameter Extraction (already done in __init__)
            if verbose:
                print(f"=== {self.faultModel} GA with Random Search ===")
                # print(f"Circuit: {self.circuit["Circuit Name"]}")
                # print(f"Input lines (n): {self.circuit["No of Lines"]}")
                # print(f"Gates (N): {self.circuit["No of Gates"]}")
                # print(f"Threshold: {self.threshold}%")
                # print(f"Max vectors: {self.circuit.max_vectors}\n")
            
            print("Stage 2")
            # Stage II: Random Search - Initial Population
            init_pop = self.stage_ii_random_selection()
            
            try:
                for generation in range(self.max_generations):
                    self._check_time_limit()
                    self.current_generation = generation
                    
                    if verbose:
                        print(f"Generation {generation + 1}:")
                        print(f"  InitPop: {init_pop}")
                    
                    print("Stage 3")
                    # Stage III: Fitness Computation
                    fitness_data = self.compute_population_fitness(init_pop)
                    
                    print("Stage 4")
                    # Stage IV: Roulette Wheel Selection
                    parent_pairs = self.stage_iv_roulette_wheel_selection(fitness_data)
                    
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
            
            
            
