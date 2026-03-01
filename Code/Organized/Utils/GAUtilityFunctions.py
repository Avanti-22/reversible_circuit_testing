import os
import time
import random
import numpy as np
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Set, Tuple

from .SimulatorsfaultCoverageFindingUtilities import (
    simulate_circuit,
    get_all_faulty_outputs,
)

# ---------------------------------------------------------------------------
# Type alias
# Fault sets are stored as plain Python ints used as bitmasks.
# Bit i is set ↔ fault index i is detected.
# This makes union (|), intersection (&), difference (&~), and
# popcount (bit_count / bin().count) single CPU instructions rather
# than O(k) Python-object operations on frozensets.
# ---------------------------------------------------------------------------
FaultMask = int   # bitmask over fault indices


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class TimeLimitExceeded(Exception):
    pass


# ---------------------------------------------------------------------------
# Module-level worker (must be top-level to be picklable by multiprocessing)
# ---------------------------------------------------------------------------

def _vector_fault_worker(args: Tuple) -> Tuple[int, int, FaultMask]:
    """
    Compute fault detection for a single test vector.

    Args:
        args: (circuit, binary_vector, fault_model, vector_int)

    Returns:
        (vector_int, cumulated_fault_count, fault_bitmask)
        where bit i of fault_bitmask is set iff fault i is detected.
    """
    circuit, binary_vector, fault_model, vector = args

    fault_free     = simulate_circuit(circuit, binary_vector)
    faulty_outputs = get_all_faulty_outputs(circuit, binary_vector, fault_model)

    mask = 0
    for i, out in enumerate(faulty_outputs):
        if out != fault_free:
            mask |= (1 << i)

    return vector, len(faulty_outputs), mask


# ---------------------------------------------------------------------------
# Genetic Algorithm
# ---------------------------------------------------------------------------

class GeneticAlgorithm:
    """
    Genetic Algorithm for minimal test vector set generation.

    Integrates:
      - Bitmask fault storage (fault sets as ints, O(1) union/diff/popcount)
      - DP fault cache (each vector simulated at most once across all generations)
      - Greedy set-cover for Stage VIII (O(k×n) vs brute-force O(2^n))
      - CPU parallelism for fitness computation, crossover, and mutation
    """

    def __init__(
        self,
        circuit: Dict,
        fault_model: str = "SMGF",
        population_size: int = None,
        max_generations: int = 100,
        threshold: float = 100.0,
        time_limit_seconds: float = None,
        n_workers: int = None,
    ):
        self.circuit = circuit
        self.fault_model = fault_model
        self.threshold = threshold
        self.population_size = population_size or circuit["No of Lines"]
        self.max_generations = max_generations
        self.time_limit_seconds = time_limit_seconds
        self.n_workers = n_workers or max(1, os.cpu_count() - 1)

        # DP cache — persists across all generations.
        # Maps vector (int) → FaultMask (int bitmask).
        # Bit i set ↔ fault i detected by this vector.
        self._fault_cache: Dict[int, FaultMask] = {}

        self.current_generation: int = 0
        self.cumulated_faults: Optional[int] = None
        self.best_coverage: float = 0.0
        self.best_vector_set: List[int] = []
        self.detected_faults: FaultMask = 0
        self.execution_time: float = 0.0
        self._start_time: Optional[float] = None

    # ------------------------------------------------------------------
    # Timer
    # ------------------------------------------------------------------

    def _start_timer(self) -> None:
        self._start_time = time.monotonic()

    def _update_execution_time(self) -> None:
        if self._start_time is not None:
            self.execution_time = time.monotonic() - self._start_time

    def _check_time_limit(self) -> None:
        if self.time_limit_seconds is None:
            return
        self._update_execution_time()
        if self.execution_time >= self.time_limit_seconds:
            raise TimeLimitExceeded()

    # ------------------------------------------------------------------
    # Vector conversion helpers
    # ------------------------------------------------------------------

    def _to_binary(self, vector: int) -> List[int]:
        n = self.circuit["No of Lines"]
        return [int(b) for b in format(vector, f'0{n}b')]

    def _to_int(self, binary: List[int]) -> int:
        return int("".join(str(b) for b in binary), 2)

    # ------------------------------------------------------------------
    # DP fault cache
    # ------------------------------------------------------------------

    def _get_detected_faults(self, vector: int) -> FaultMask:
        """
        Return the fault bitmask for `vector`.
        Simulates only on the first call; all subsequent calls are O(1) dict lookup.
        """
        if vector not in self._fault_cache:
            binary         = self._to_binary(vector)
            fault_free     = simulate_circuit(self.circuit, binary)
            faulty_outputs = get_all_faulty_outputs(self.circuit, binary, self.fault_model)

            mask = 0
            for i, out in enumerate(faulty_outputs):
                if out != fault_free:
                    mask |= (1 << i)

            # cumulated_faults depends only on circuit + fault model, not the input
            self.cumulated_faults    = len(faulty_outputs)
            self._fault_cache[vector] = mask

        return self._fault_cache[vector]

    def _coverage_from_mask(self, mask: FaultMask) -> float:
        """Fault coverage % from a bitmask. popcount is O(1)."""
        if not self.cumulated_faults:
            return 0.0
        return mask.bit_count() / self.cumulated_faults * 100

    # ------------------------------------------------------------------
    # Stage II — Random initial population
    # ------------------------------------------------------------------

    def stage_ii_random_selection(self, size: int = None) -> List[int]:
        """Randomly select `size` unique vectors from the full input space."""
        if size is None:
            size = min( self.circuit["No of Lines"], self.population_size)
        # size = size or self.population_size
        available = list(range(2 ** self.circuit["No of Lines"]))
        return random.sample(available, min(size, len(available)))

    # ------------------------------------------------------------------
    # Stage III — Per-vector fitness (uses cache)
    # ------------------------------------------------------------------

    def stage_iii_fitness_computation(self, vector: int) -> Tuple[float, FaultMask]:
        """
        Return (fault_coverage_%, fault_bitmask) for one vector.
        O(1) after the first call for that vector.
        """
        mask = self._get_detected_faults(vector)
        return self._coverage_from_mask(mask), mask

    # ------------------------------------------------------------------
    # Population fitness — parallel with cache bypass
    # ------------------------------------------------------------------

    def compute_population_fitness(
        self, population: List[int]
    ) -> List[Tuple[int, float, FaultMask]]:
        """
        Compute fitness for the entire population.

        Vectors already in cache are resolved instantly (O(1) dict lookup).
        Uncached vectors are simulated in parallel via ProcessPoolExecutor.
        """
        self._check_time_limit()

        cached   = [v for v in population if v in self._fault_cache]
        uncached = [v for v in population if v not in self._fault_cache]

        # Instant resolution for cached vectors
        results: Dict[int, Tuple[int, float, FaultMask]] = {
            v: (v, self._coverage_from_mask(self._fault_cache[v]), self._fault_cache[v])
            for v in cached
        }

        # Parallel simulation for uncached vectors
        if uncached:
            worker_args = [
                (self.circuit, self._to_binary(v), self.fault_model, v)
                for v in uncached
            ]
            with ProcessPoolExecutor(max_workers=self.n_workers) as executor:
                futures = {
                    executor.submit(_vector_fault_worker, a): a[-1]
                    for a in worker_args
                }
                for future in as_completed(futures):
                    self._check_time_limit()
                    vector, cumulated, mask = future.result()
                    self.cumulated_faults    = cumulated
                    self._fault_cache[vector] = mask
                    results[vector] = (vector, self._coverage_from_mask(mask), mask)

        return [results[v] for v in population]

    # ------------------------------------------------------------------
    # Stage IV — Roulette wheel selection
    # ------------------------------------------------------------------

    def stage_iv_roulette_wheel_selection(
        self,
        fitness_data: List[Tuple[int, float, FaultMask]],
        num_pairs: int = None,
    ) -> List[Tuple[int, int]]:
        num_pairs = num_pairs or len(fitness_data) // 2
        vectors   = [item[0] for item in fitness_data]
        fitnesses = [item[1] for item in fitness_data]

        total = sum(fitnesses)
        probs = (
            [f / total for f in fitnesses]
            if total > 0
            else [1.0 / len(fitnesses)] * len(fitnesses)
        )

        return [
            (
                random.choices(vectors, weights=probs)[0],
                random.choices(vectors, weights=probs)[0],
            )
            for _ in range(num_pairs)
        ]

    # ------------------------------------------------------------------
    # Stage V — Crossover (parallel, pairs are independent)
    # ------------------------------------------------------------------

    def _crossover_pair(self, pair: Tuple[int, int]) -> int:
        p1 = self._to_binary(pair[0])
        p2 = self._to_binary(pair[1])
        point = random.randint(1, self.circuit["No of Lines"] - 1)
        return self._to_int(p1[:point] + p2[point:])

    def stage_v_crossover(self, parent_pairs: List[Tuple[int, int]]) -> List[int]:
        """Parallel crossover — each pair is independent."""
        with ThreadPoolExecutor(max_workers=self.n_workers) as executor:
            return list(executor.map(self._crossover_pair, parent_pairs))

    # ------------------------------------------------------------------
    # Stage VI — Mutation (parallel, children are independent)
    # ------------------------------------------------------------------

    def _mutate_child(self, args: Tuple[int, float]) -> int:
        child, prob = args
        if random.random() < prob:
            bits = self._to_binary(child)
            pos = random.randint(0, len(bits) - 1)
            bits[pos] ^= 1
            return self._to_int(bits)
        return child

    def stage_vi_mutation(self, children: List[int]) -> List[int]:
        """Parallel mutation — mutation probability decays over generations."""
        prob = 0.3 * np.exp(-0.1 * self.current_generation)
        with ThreadPoolExecutor(max_workers=self.n_workers) as executor:
            return list(executor.map(self._mutate_child, [(c, prob) for c in children]))

    # ------------------------------------------------------------------
    # Stage VII — Combine and rank populations
    # ------------------------------------------------------------------

    def stage_vii_test_population_generation(
        self, init_pop: List[int], child_pop: List[int]
    ) -> List[Tuple[int, float, FaultMask]]:
        combined = list(set(init_pop + child_pop))
        fitness_data = self.compute_population_fitness(combined)
        return sorted(fitness_data, key=lambda x: x[1], reverse=True)

    # ------------------------------------------------------------------
    # Stage VIII — Greedy set-cover (O(k×n), replaces brute-force O(2^n))
    # ------------------------------------------------------------------

    def stage_viii_minimal_test_set(
        self, fin_pop: List[Tuple[int, float, FaultMask]]
    ) -> Tuple[List[int], float]:
        """
        Find the minimal test set using greedy set-cover with bitmask operations.

        All set operations (union, difference, popcount) are O(1) integer ops:
          - union:      covered | mask
          - difference: mask & ~covered   (new faults this vector would add)
          - popcount:   mask.bit_count()

        O(k × n) where k = result set size, n = population size.
        All fault masks come from cache — no redundant simulation.
        """
        vectors = [item[0] for item in fin_pop]

        # All vectors already cached by compute_population_fitness
        fault_masks = {v: self._fault_cache[v] for v in vectors}

        covered   = 0      # bitmask of all faults detected so far
        full_mask = (1 << self.cumulated_faults) - 1   # all-ones mask
        test_set  = []
        remaining = list(vectors)

        while remaining:
            self._check_time_limit()

            if self._coverage_from_mask(covered) >= self.threshold:
                break

            # Pick vector adding the most new faults — O(n) with O(1) per vector
            best      = max(remaining, key=lambda v: (fault_masks[v] & ~covered).bit_count())
            new_faults = fault_masks[best] & ~covered

            if not new_faults:
                break  # No remaining vector can improve coverage

            covered  |= new_faults
            test_set.append(best)
            remaining.remove(best)

        self.detected_faults = covered
        return test_set, self._coverage_from_mask(covered)

    # ------------------------------------------------------------------
    # Combined coverage (used externally if needed)
    # ------------------------------------------------------------------

    def compute_combined_coverage(
        self, test_set: List[int]
    ) -> Tuple[float, FaultMask]:
        """
        Compute union fault coverage for an arbitrary set of vectors.
        Union is a single OR per vector — O(|test_set|).
        """
        combined_mask = 0
        for v in test_set:
            combined_mask |= self._get_detected_faults(v)

        self.detected_faults = combined_mask
        return self._coverage_from_mask(combined_mask), combined_mask

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self, verbose: bool = False) -> Dict:
        """
        Execute the full GA pipeline.

        Returns:
            Results dictionary (same schema as save_results).
        """
        self._start_timer()

        if verbose:
            print(f"=== {self.fault_model} GA | workers={self.n_workers} ===")
            print(f"Circuit : {self.circuit['Circuit Name']}")
            print(f"Lines   : {self.circuit['No of Lines']}")
            print(f"Gates   : {self.circuit['No of Gates']}")
            print(f"Threshold: {self.threshold}%\n")

        # Stage I: parameters already set in __init__
        # Stage II: initial random population
        init_pop = self.stage_ii_random_selection()

        try:
            for generation in range(self.max_generations):
                self._check_time_limit()
                self.current_generation = generation

                # Stage III: fitness
                fitness_data = self.compute_population_fitness(init_pop)

                # Stage IV: selection
                parent_pairs = self.stage_iv_roulette_wheel_selection(fitness_data)

                # Stage V: crossover
                children = self.stage_v_crossover(parent_pairs)

                # Stage VI: mutation
                mutated = self.stage_vi_mutation(children)

                # Stage VII: merge + rank
                fin_pop = self.stage_vii_test_population_generation(init_pop, mutated)

                # Stage VIII: minimal test set via greedy set-cover
                test_set, coverage = self.stage_viii_minimal_test_set(fin_pop)

                if verbose:
                    print(
                        f"  Gen {generation + 1:3d} | "
                        f"coverage={coverage:.2f}% | "
                        f"set_size={len(test_set)} | "
                        f"set={test_set}"
                    )

                if coverage > self.best_coverage:
                    self.best_coverage   = coverage
                    self.best_vector_set = test_set

                if coverage >= self.threshold:
                    if verbose:
                        print(f"\n  ✓ Threshold met at generation {generation + 1}")
                    return self.save_results()

                # Stage IX: filial generation — keep best half, refill with random
                num_best     = max(1, self.population_size // 2)
                best_vectors = [item[0] for item in fin_pop[:num_best]]
                random_fill  = self.stage_ii_random_selection(
                    self.population_size - len(best_vectors)
                )
                init_pop = best_vectors + random_fill

        except TimeLimitExceeded:
            if verbose:
                print("\n  ⏱ Time limit exceeded")

        if verbose:
            print(f"\n  Max generations reached.")
            print(f"  Best coverage: {self.best_coverage:.2f}%")
            print(f"  Best set: {self.best_vector_set}")

        return self.save_results()

    # ------------------------------------------------------------------
    # Results
    # ------------------------------------------------------------------

    def save_results(self) -> Dict:
        self._update_execution_time()

        # Convert bitmask back to a sorted list of fault indices for the output,
        # so callers get a human-readable format rather than a raw integer.
        detected_locations = [
            i for i in range(self.cumulated_faults or 0)
            if self.detected_faults & (1 << i)
        ]

        return {
            "Circuit Name":             self.circuit["Circuit Name"],
            "No of Lines":              self.circuit["No of Lines"],
            "No of Gates":              self.circuit["No of Gates"],
            "Library":                  self.circuit["Library Type"],
            "Fault Model":              self.fault_model,
            "Population Size":          self.population_size,
            "Threshold":                self.threshold,
            "Total Faults":             self.cumulated_faults,
            "Detected Faults":          self.detected_faults.bit_count() if self.cumulated_faults else 0,
            "Fault Coverage":           self.best_coverage,
            "Minimal Vector Set":       self.best_vector_set,
            "Execution Time":           self.execution_time,
            "Detected Fault Locations": detected_locations,
        }