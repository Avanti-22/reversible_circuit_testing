# # Genetic ALgorithm

# 1. initialize the population

# 2. calculate fitness

# 3. select the best individuals(parents) for next gen

# 4. crossover, mutation

# 5. repeat 2-4 until threshold value is not reached


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
                    time_limit_seconds: float = None, skip_minimization = None):
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
            self.time_limit_seconds = time_limit_seconds if time_limit_seconds is not None else 300.0
            
            # Auto-skip minimization for large circuits (n >= 12)
            if skip_minimization is None:
                self.skip_minimization = circuit["No of Lines"] >= 12
            else:
                self.skip_minimization = skip_minimization
            self.current_generation = None
            self.best_coverage = 0.0
            self.best_vector_set = []
            self.cumulatedFaults = None
            self.detectedFaults = []
            self.execution_time = 0.0
            self._start_time = None
            self._time_limit_exceeded = False

        def _start_timer(self):
            self._start_time = time.monotonic()

        def _update_execution_time(self):
            if self._start_time is not None:
                self.execution_time = time.monotonic() - self._start_time

        def _check_time_limit(self):
            self._update_execution_time()
            
            if self.execution_time >= self.time_limit_seconds:
                if not self._time_limit_exceeded:
                    self._time_limit_exceeded = True
                return True
            return False
        

        def stage_i_input_Parameter_extratcion(self):
            self.n = self.circuit["No of Lines"]
            self.N = self.circuit["No of Gates"]
            self.max_no_of_TV = 2**self.n
            
               
        def stage_ii_TV_selection(self, test_Size=None) -> List[int]:
            """
            Stage II: Test Vector Selection (Random Search)
            
            Args:
                size: Number of vectors to select (default: population_size)
                
            Returns:
                List of randomly selected unique vectors
            """
            
            if self._check_time_limit():
                return []
            
            
            if test_Size is None:
                test_Size = self.max_no_of_TV
                
            possible_valid_vectors = list(range(test_Size))
            
            initPop = random.sample(possible_valid_vectors, min(self.n, len(possible_valid_vectors)))
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
       
        
        def stage_iii_fitness_function_computation(self, vector: int):
            """
            Stage III: Fitness Function Computation
            
            Args:
                vector: Test vector (decimal)
                
            Returns:
                Tuple of (fault_coverage_percentage, set_of_detected_faults)
            """
            if self._check_time_limit():
                return 0.0, []
            
            # Convert to binary for processing
            binary_vector = self.represent_the_vec_in_binary(vector)
            
            # Compute fault-free output
            faultFreeOutput = simulate_circuit(self.circuit, binary_vector)
            faultyOutputs = []
            
            faultyOutputs = get_all_faulty_outputs(self.circuit, binary_vector, self.faultModel)
            
            self.cumulatedFaults = len(faultyOutputs)
            
            detectedFaultList = self.obtain_detected_fault_matrix(faultFreeOutput, faultyOutputs)
       
            detected = detectedFaultList .count(1)
    
            fault_coverage = (detected/self.cumulatedFaults)*100 if self.cumulatedFaults > 0 else 0
            
            return fault_coverage, detectedFaultList
        
        def compute_fitness_for_population(self, initPop):
            
            if self._check_time_limit():
                return [], {}
            
            fitnessFunction= []
            detectedFaultMatrix = {}

            for i in range(len(initPop)):

                if self._check_time_limit():
                    print("Fitness Calculation For Population")
                    break
                
                fault_coverage, detectedFaults = self.stage_iii_fitness_function_computation(initPop[i])
                detectedFaultMatrix[initPop[i]] = detectedFaults

                
                fitnessFunction.append(fault_coverage)
                if(fitnessFunction[i]>= self.threshold):
                    break
                    # display and exit
                    # pass
            
            return fitnessFunction , detectedFaultMatrix   
        
        def stage_iv_roulette_wheel_selection(self, fitnessFunction, population) -> List[Tuple[int, int]]:
            """
            Stage IV: Roulette Wheel Selection
            
            Args:
                fitness_data: List of (vector, fitness, detected_faults)
                num_pairs: Number of parent pairs to select
                
            Returns:
                List of parent pairs
            """

            if self._check_time_limit():
                return []
            
            parent_pairs = []
            
            # Handle case where all fitnesses are zero
            total_fitness = sum(fitnessFunction)
            if total_fitness == 0:
                probabilities = [1.0 / len(fitnessFunction)] * len(fitnessFunction)
            else:
                probabilities = [f / total_fitness for f in fitnessFunction]
            print(population, probabilities)
        
            for _ in range(self.n):
                if self._check_time_limit():
                    break
                parent1 = random.choices(population, weights=probabilities)[0]
                parent2 = random.choices(population, weights=probabilities)[0]
                parent_pairs.append((parent1, parent2))
            
            return parent_pairs
        
        def represent_bin_in_int(self, bin_vec_list):
            bit_str= []
            
            for bit in bin_vec_list:
                
                bit_str.append(str(bit))
                
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
            if self._check_time_limit():
                return []
            
            children = []
            
            for parent1, parent2 in parent_pairs:
                if self._check_time_limit():
                    break
                
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
            if self._check_time_limit():
                return children
            
            # Mutation probability decreases exponentially with generations
            maxVal = 10**(self.current_generation+1)-1
            # print(maxVal)           
            mutated_children = []
            
            for child in children:
                if self._check_time_limit():
                    mutated_children.extend(children[len(mutated_children):])
                    break
                
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
                    
                    # bit_str= []
                    # for bit in child_bin:
                    #     bit_str.append(child_bin[bit])
                    
                    
                    mutated_child = self.represent_bin_in_int(child_bin)
                    
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
            if self._check_time_limit():
                return init_pop
            
            combined_pop = list(set(init_pop + child_pop))  # Remove duplicates
            
            # Compute fitness for all
            fitnessFunct, detectedFaults = self.compute_fitness_for_population(combined_pop)
            
            if not fitnessFunct:
                return init_pop
            
            # Sort by fitness (descending)
            fitnessFunct, sorted_pop = zip(*sorted(zip(fitnessFunct, combined_pop),  reverse=True))
            
            return list(sorted_pop)
        
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
                L = max(2, self.n // 2)
            
            vectors = fin_pop
            
            # Try combinations of increasing size
            for combo_size in range(L, min(len(vectors) + 1, self.population_size + 1)):
                
                if self._check_time_limit():
                    print("TLE encountered in Minimization")
                    break
                
                for combo in itertools.combinations(vectors, combo_size):
                    if self._check_time_limit():
                        break
                    
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
            
            if self._check_time_limit():
                return 0.0, []
            
            
            all_detected = None
            
            for vector in test_set:
                if self._check_time_limit():
                    break
                
                fault_coverage, detectedFaults= self.stage_iii_fitness_function_computation(vector)
               
                if all_detected is None:
                    all_detected = detectedFaults
                else :   
                    for loc in range(len(detectedFaults)):
                        all_detected[loc] = all_detected[loc] or detectedFaults[loc]
            
            if all_detected is None:
                return 0.0, []
                
            self.detectedFaults = all_detected
            detected = all_detected.count(1)
            coverage = (detected / self.cumulatedFaults) * 100 if self.cumulatedFaults > 0 else 0
            return coverage, all_detected
        
        def find_best_combination(self, vectors: List[int]):
            """Find the best combination of vectors for maximum coverage"""
            
            if self._check_time_limit():
                coverage, detected = self.compute_combined_coverage(vectors[:self.population_size])
                return vectors[:self.population_size], coverage
            
            
            best_combo = []
            best_coverage = 0.0
            
            for size in range(1, min(len(vectors) + 1, self.n + 1)):
                
                if self._check_time_limit():
                    break
                
                for combo in itertools.combinations(vectors[:min(10, len(vectors))], size):
                    
                    if self._check_time_limit():
                        break
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
            
            if verbose is not None:
                self.verbose = verbose
            
            self._start_timer()
            
            print("Stage 1")
            # Stage I: Input Parameter Extraction
            self.stage_i_input_Parameter_extratcion()
    
            if verbose:
                print(f"=== {self.faultModel} GA with Random Search ===")
                print(f"Circuit: {self.circuit['Circuit Name']}")
                print(f"Threshold: {self.threshold}%")
                print(self.n)
                print(self.N)
                print(self.max_no_of_TV)
            
            print("Stage 2")
            # Stage II: Random Search - Initial Population
            populn = self.stage_ii_TV_selection()
            
            if not populn:
                return self.save_results()
            
            finPop = []
            finPop.extend(populn)
            
            
            # finFitness = []
            # print("stages 3 - 9")
            
            
            for generation in range(self.max_generations):
                if self._check_time_limit():
                    print("TLE after genertaion ", generation)
                    break
                    
                    
                self.current_generation = generation
                
                if verbose:
                    print(f"Generation {generation + 1}:")
                    print(f"Population: {populn}")
                
                print("Stage 3")
                # Stage III: Fitness Computation
                fitnessFunct, detectedFaults = self.compute_fitness_for_population(populn)
                # finFitness.extend(fitnessFunct)
                                
                if not fitnessFunct:
                    break
                
                max_fitness = max(fitnessFunct)
                avg_fitness = sum(fitnessFunct) / len(fitnessFunct)
                print(f"Population fitness - Max: {max_fitness:.2f}%, Avg: {avg_fitness:.2f}%")
                
                print("Stage 4")
                # Stage IV: Roulette Wheel Selection
                parent_pairs = self.stage_iv_roulette_wheel_selection(fitnessFunct, populn)
                
                if not parent_pairs:
                    break
                
                print("Stage 5")
                # Stage V: Crossover
                children = self.stage_v_crossover(parent_pairs)
                
                if not children:
                    break
                
                print("Stage 6")
                # Stage VI: Mutation
                mutated_children = self.stage_vi_mutation(children)
                
                
                print("Stage 7")
                # Stage VII: Test Population Generation
                fin_pop = self.stage_vii_test_population_generation(populn, mutated_children)
                
                if not fin_pop:
                    break                        
                
                
                if self.skip_minimization or  self._check_time_limit():
                    print("skipping minimization")
                # Just compute coverage for the current population
                coverage, detected = self.compute_combined_coverage(fin_pop[:self.population_size])
                print(f"Cov {coverage}, detected: {detected}")
                return fin_pop[:self.population_size], coverage
                
                print("Stage 8")
                # Stage VIII: Minimal Test Set Generation
                test_set, coverage  = self.stage_viii_minimal_test_set(finPop)
                
                
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
                
                if len(test_set) < self.population_size:
                    populn = test_set
                
                    # Fill remaining slots with random selection
                    remaining_slots = self.population_size - len(test_set)
                    random_vectors = self.stage_ii_TV_selection(remaining_slots)
                    populn.extend(random_vectors)  
                
                else:
                    populn = test_set[:self.population_size -1]
                    random_vector = self.stage_ii_TV_selection(1)
                    populn.extend(random_vector)

            if self._time_limit_exceeded:
                print("=== Algorithm Terminated: Time Limit Exceeded ===")
            else:
                print("=== Algorithm Terminated: Max Generations Reached ===")
               
                    
            
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
                "Max Generations": self.max_generations,
                "Actual Generations": self.current_generation + 1,
                "Threshold": self.threshold,
                "Total Faults": self.cumulatedFaults,
                "Detected Faults": self.detectedFaults.count(1),
                "Fault Coverage": self.best_coverage,
                "Minimal Vector Set": self.best_vector_set,
                "Test Set Size": len(self.best_vector_set),
                "Execution Time": self.execution_time,
                "Time Limit Exceeded": self._time_limit_exceeded,
                "Minimization Skipped": self.skip_minimization,
                "Detected Fault Locations": self.detectedFaults
            }
            # print(results)
            
            return results
            
            
            
