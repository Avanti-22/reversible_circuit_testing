from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import gc
import time
import numpy as np
import itertools
from fault_models import *
import random
from simulator import *
import logging
logger = logging.getLogger(__name__)
from fault_models import build_gaf_gate_library
import os

import gc
import time
import numpy as np
import logging
import random

from fault_models import *
from simulator import *

logger = logging.getLogger(__name__)

_DP_FAULT_LIMIT = 20

DEBUG = True


# def _compress_fault_matrix(fault_matrix, vector_map, fin_pop):
#     """Convert boolean fault_matrix rows → integer bitmasks, one per vector."""
#     n_faults = fault_matrix.shape[1]
#     coverage_masks = []
#     for vec in fin_pop:
#         row  = fault_matrix[vector_map[vec]]
#         mask = 0
#         for bit_idx, detected in enumerate(row):
#             if detected:
#                 mask |= (1 << bit_idx)
#         coverage_masks.append(mask)
#     return coverage_masks, n_faults

def _compress_fault_matrix(fault_matrix, fin_pop):
    """
    Order-invariant compression:
    - ignores vector_map completely
    - uses direct population indexing
    """
    n_faults = fault_matrix.shape[1]

    # map vector → its row by recomputing position safely
    # (assumes fault_matrix rows are aligned with fin_pop order)
    coverage_masks = []

    for i, vec in enumerate(fin_pop):
        row = fault_matrix[i]   # <-- NO vector_map usage
        mask = 0
        for bit_idx, detected in enumerate(row):
            if detected:
                mask |= (1 << bit_idx)
        coverage_masks.append(mask)

    return coverage_masks, n_faults

# def _dp_set_cover(coverage_masks, n_faults, fin_pop, time_check_fn):
#     """
#     Bitmask DP — finds the OPTIMAL (minimum-size) test set.

#     dp[S] = minimum vectors to cover the fault-set encoded by bitmask S.
#     Parent pointers allow full solution reconstruction.
#     """
#     full_mask   = (1 << n_faults) - 1
#     INF         = 10 ** 9

#     dp          = [INF] * (full_mask + 1)
#     parent_vec  = [-1]  * (full_mask + 1)   # which vector index was added
#     parent_prev = [-1]  * (full_mask + 1)   # previous DP state

#     dp[0] = 0                               # base case

#     for state in range(full_mask + 1):
#         if dp[state] == INF:
#             continue                        # unreachable state — skip
#         if time_check_fn():
#             break                           # respect GA global time limit

#         for vec_idx, mask in enumerate(coverage_masks):
#             new_state = state | mask
#             if dp[new_state] > dp[state] + 1:
#                 dp[new_state]          = dp[state] + 1
#                 parent_vec[new_state]  = vec_idx
#                 parent_prev[new_state] = state

#     # Find best reachable state (prefer full coverage; else most faults covered)
#     if dp[full_mask] < INF:
#         best_state = full_mask
#     else:
#         best_state = max(
#             range(full_mask + 1),
#             key=lambda s: (bin(s).count('1'), -dp[s] if dp[s] < INF else -(10**9))
#         )

#     if dp[best_state] == INF:
#         return [], 0.0

#     # Reconstruct solution via parent pointers
#     selected_indices = []
#     cur = best_state
#     while cur != 0 and parent_vec[cur] != -1:
#         selected_indices.append(parent_vec[cur])
#         cur = parent_prev[cur]

#     selected_vecs = [fin_pop[i] for i in selected_indices]
#     coverage_pct  = (bin(best_state).count('1') / n_faults) * 100
#     return selected_vecs, coverage_pct

def _dp_set_cover(coverage_masks, n_faults, fin_pop, time_check_fn):

    full_mask = (1 << n_faults) - 1
    INF = 10**9

    dp = [INF] * (full_mask + 1)
    parent_vec = [-1] * (full_mask + 1)
    parent_prev = [-1] * (full_mask + 1)

    dp[0] = 0

    for state in range(full_mask + 1):

        if dp[state] == INF:
            continue

        if time_check_fn():
            break

        for vec_idx, mask in enumerate(coverage_masks):
            new_state = state | mask

            if dp[new_state] > dp[state] + 1:
                dp[new_state] = dp[state] + 1
                parent_vec[new_state] = vec_idx
                parent_prev[new_state] = state

    # choose best reachable state
    best_state = full_mask if dp[full_mask] < INF else max(
        range(full_mask + 1),
        key=lambda s: (bin(s).count("1"), -dp[s])
    )

    if dp[best_state] == INF:
        return [], 0.0

    # reconstruct (order-independent now)
    selected = []
    cur = best_state

    while cur != 0 and parent_vec[cur] != -1:
        idx = parent_vec[cur]
        selected.append(fin_pop[idx])
        cur = parent_prev[cur]

    coverage_pct = (bin(best_state).count("1") / n_faults) * 100

    return selected, coverage_pct


def _greedy_set_cover(coverage_masks, n_faults, fin_pop, time_check_fn):
    """
    Greedy set-cover fallback — O(V × F).
    Used only when n_faults > _DP_FAULT_LIMIT.
    Equivalent to the original stage_viii logic.
    """
    covered   = 0
    full_mask = (1 << n_faults) - 1
    selected  = []
    remaining = list(range(len(fin_pop)))

    while remaining:
        if time_check_fn():
            break
        best_idx = max(
            remaining,
            key=lambda i: bin(coverage_masks[i] & ~covered).count('1')
        )
        new_bits = coverage_masks[best_idx] & ~covered
        if new_bits == 0:
            break
        covered |= coverage_masks[best_idx]
        selected.append(fin_pop[best_idx])
        remaining.remove(best_idx)
        if covered == full_mask:
            break

    coverage_pct = (bin(covered).count('1') / n_faults) * 100
    return selected, coverage_pct

# def _eval_vector_worker(args):
#     """ProcessPoolExecutor worker — module-level so it's picklable."""
#     circuit, fault_model, vector = args
#     from fault_models import get_all_faulty_outputs
#     from simulator import simulate_fault_free
#     import numpy as np

#     fault_free = simulate_fault_free(circuit, vector)
#     faulty_outputs = get_all_faulty_outputs(circuit, vector, fault_model)
#     n_faults = len(faulty_outputs)
#     if n_faults == 0:
#         return vector, 0.0, np.array([], dtype=bool), 0

#     detected = np.array([f != fault_free for f in faulty_outputs], dtype=bool)
#     coverage = float(np.sum(detected)) / n_faults * 100
#     return vector, coverage, detected, n_faults

def _eval_vector_worker(args):
    circuit, fault_models, vector = args

    from fault_models import get_all_faulty_outputs
    from simulator import simulate_fault_free
    import numpy as np

    fault_free = simulate_fault_free(circuit, vector)

    all_faulty_outputs = []
    for model in fault_models:
        faulty_outputs = get_all_faulty_outputs(circuit, vector, model)
        all_faulty_outputs.extend(faulty_outputs)
    result = (f"vec: {vector}, yff: {fault_free}, faulty: {all_faulty_outputs}")

    n_faults = len(all_faulty_outputs)

    if n_faults == 0:
        return vector, 0.0, np.array([], dtype=bool), 0

    detected = np.array([f != fault_free for f in all_faulty_outputs], dtype=bool)
    coverage = float(np.sum(detected)) / n_faults * 100

    return vector, coverage, detected, n_faults, result



# ── Threshold: tune this based on your benchmarks ────────────────────────────
_PARALLEL_GATE_THRESHOLD = 50   # gates — mirrors the MMGF large/small split




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
        self.approach = "Random"
        if isinstance(faultModel, str):
            self.fault_models = [faultModel]
        else:
            self.fault_models = faultModel

        self.threshold = 100.0
        self.population_size = population_size or circuit['No of Lines']
        self.max_generations = max_generations if max_generations else 20
        self.time_limit_seconds = time_limit_seconds if time_limit_seconds else 300.0
        self.gaf_insertion_gates = None
        if skip_minimization is None:
            self.skip_minimization = circuit["No of Lines"] >= 12
        else:
            self.skip_minimization = skip_minimization

        self.current_generation = 0
        self.best_coverage = 0.0
        self.best_vector_set = []
        self.cumulatedFaults = 0
        self.detectedFaults = None
        self.execution_time = 0.0

        self._start_time = None
        self._time_limit_exceeded = False

        # int key cache — avoids str(vector) overhead on every lookup
        self.fault_cache: dict[int, tuple] = {}

    # ── Logging Helpers ──────────────────────────────────────────────────────

    def _debug(self, msg):
        if DEBUG:
            print(msg)
    
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
        self.max_no_of_TV = 2 ** self.n if self.n < 20 else 2 ** 20  # cap at 1M for sanity
        if self.fault_models == "GAF":
            gate_library = build_gaf_gate_library(self.circuit["No of Lines"])
            total_gates  = self.circuit["No of Gates"]
            self.gaf_insertion_gates = {
                k: random.choice(gate_library)
                for k in range(-1, total_gates)
            }
            self._log(f"GAF: pre-selected {len(self.gaf_insertion_gates)} insertion gates (fixed for this run)")
            
        self._debug(f"\n[Stage I] Parameters:")
        self._debug(f"  Lines (n): {self.n}")
        self._debug(f"  Gates (N): {self.N}")
        self._debug(f"  Max TV: {self.max_no_of_TV}")    
                
        
    # ── Stage II ─────────────────────────────────────────────────────────────

    def stage_ii_TV_selection(self, test_size=None):
        if test_size is None:
            test_size = self.n
        if self.max_no_of_TV <= 2000:  # small circuits: unique sampling for better initial diversity
            return random.sample(range(self.max_no_of_TV), test_size)
        else:
            return [random.randrange(0, self.max_no_of_TV) for _ in range(test_size)]

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

    # def stage_iii_fitness_function_computation(self, vector: int):
    #     if vector in self.fault_cache:
    #         return self.fault_cache[vector]

    #     fault_free_output = simulate_fault_free(self.circuit, vector)
    #     faulty_outputs = get_all_faulty_outputs(
    #         self.circuit, vector, self.faultModel,
    #         gaf_insertion_gates=self.gaf_insertion_gates   # None for non-GAF models
    #     )

    #     n_faults = len(faulty_outputs)

    #     # Set cumulatedFaults only ONCE on first evaluation.
    #     # After that, assert consistency — if fault count changes between vectors,
    #     # it signals a non-deterministic fault model (e.g. GAF with random.choice).
    #     if self.cumulatedFaults == 0:
    #         self.cumulatedFaults = n_faults
    #     elif n_faults != self.cumulatedFaults:
    #         # Log the inconsistency but do not crash — use the established count
    #         self._log(
    #             f"[WARN] Fault count mismatch: expected {self.cumulatedFaults}, "
    #             f"got {n_faults} for vector {vector}. "
    #             f"Fault model '{self.faultModel}' may be non-deterministic."
    #         )

    #     detected_fault_array = self.get_detected_faults_row(fault_free_output, faulty_outputs)
    #     detected = int(np.sum(detected_fault_array))
    #     coverage = (detected / self.cumulatedFaults) * 100 if self.cumulatedFaults else 0

    #     self.fault_cache[vector] = (coverage, detected_fault_array)
    #     return coverage, detected_fault_array
            
    def stage_iii_fitness_function_computation(self, vector: int):
        self._debug(f"\n[Stage III] Evaluating Vector: {vector} ({self.represent_the_vec_in_binary(vector)})")
        if vector in self.fault_cache:
            self._debug("  → Cache HIT")
            return self.fault_cache[vector]

        fault_free_output = simulate_fault_free(self.circuit, vector)
        self._debug(f"  Fault-free output: {fault_free_output}")
        all_faulty_outputs = []

        # ── Combine faults from ALL models ─────────────────────────────
        for model in self.fault_models:
            faulty_outputs = get_all_faulty_outputs(
                self.circuit,
                vector,
                model,
                gaf_insertion_gates=self.gaf_insertion_gates if model == "GAF" else None
            )
            all_faulty_outputs.extend(faulty_outputs)
        result = (f"vec: {vector}, yff: {fault_free_output}, faulty: {all_faulty_outputs}")
        n_faults = len(all_faulty_outputs)

        # Initialize fault count once
        if self.cumulatedFaults == 0:
            self.cumulatedFaults = n_faults
        elif n_faults != self.cumulatedFaults:
            self._log(
                f"[WARN] Fault count mismatch: expected {self.cumulatedFaults}, got {n_faults}"
            )

        if n_faults == 0:
            detected_array = np.array([], dtype=bool)
            coverage = 0.0
        else:
            detected_array = np.array(
                [f != fault_free_output for f in all_faulty_outputs],
                dtype=bool
            )
            detected = int(np.sum(detected_array))
            coverage = (detected / self.cumulatedFaults) * 100

        self.fault_cache[vector] = (coverage, detected_array)
        self._debug(f"  Total Faults: {n_faults}")
        self._debug(f"  Detected Array: {detected_array}")
        self._debug(f"  Coverage: {coverage:.2f}%")
        return coverage, detected_array, result


        
    
    # ── Fitness for Population ────────────────────────────────────────────────

    # def compute_fitness_for_population(self, population):
    #     fitnesses = []
    #     rows = []
    #     vector_map = {}

    #     for i, vec in enumerate(population):
    #         if self._check_time_limit():
    #           self._log("TLE hit during fitness computation — aborting population eval.")
    #           break
    #         coverage, detected_faults_row = self.stage_iii_fitness_function_computation(vec)
    #         fitnesses.append(coverage)
    #         rows.append(detected_faults_row)
    #         vector_map[vec] = i

    #         if coverage >= self.threshold:
    #             self._log_detail(f"Singleton vector {vec} achieves 100% — early exit.")
    #             return fitnesses, np.array(rows, dtype=bool), vector_map, True  # ← singleton flag
    #             # break

    #     return fitnesses, np.array(rows, dtype=bool), vector_map, False

    
    def compute_fitness_for_population(self, population):
        self._debug(f"\n[Stage III - Population] Evaluating Population: {population}")
        fitnesses, rows, vector_map = [], [], {}

        use_parallel = (
            self.circuit["No of Gates"] >= _PARALLEL_GATE_THRESHOLD
            and len(population) > 1
        )

        if use_parallel:
            # Only evaluate uncached vectors in parallel
            uncached = [v for v in population if v not in self.fault_cache]

            if uncached:
                args = [(self.circuit, self.fault_models, v) for v in uncached]
                n_workers = min(len(uncached), os.cpu_count())

                with ProcessPoolExecutor(max_workers=n_workers) as executor:
                    for vec, cov, det_row, n_faults, result in executor.map(
                        _eval_vector_worker, args, chunksize=1
                    ):
                        self.fault_cache[vec] = (cov, det_row)
                        self.cumulatedFaults = n_faults
                        print(result)

        # Assemble from cache (sequential — just dict lookups)
        for i, vec in enumerate(population):
            if self._check_time_limit():
                self._log("TLE hit during fitness computation.")
                break

            if vec not in self.fault_cache:
                # small circuit path — compute inline
                cov, det_row, result = self.stage_iii_fitness_function_computation(vec)
            else:
                cov, det_row, result = self.fault_cache[vec]
            print(result)
            fitnesses.append(cov)
            rows.append(det_row)
            vector_map[vec] = i

            if cov >= self.threshold:                                                                  
                return fitnesses, np.array(rows, dtype=bool), vector_map, True
        self._debug(f"  Fitnesses: {fitnesses}")
        return fitnesses, np.array(rows, dtype=bool), vector_map, False
    
    
    # ── Stage IV ─────────────────────────────────────────────────────────────

    def stage_iv_roulette_wheel_selection(self, fitnessFunction, population):
        self._debug("\n[Stage IV] Selection Probabilities:")
        total_fitness = sum(fitnessFunction)
        if total_fitness == 0:
            probabilities = [1 / len(fitnessFunction)] * len(fitnessFunction)
        else:
            probabilities = [f / total_fitness for f in fitnessFunction]
        
        for vec, prob in zip(population, probabilities):
            self._debug(f"  Vector: {vec} | Fitness: {fitnessFunction[population.index(vec)]:.4f} | Probability: {prob:.4f}")
        parent_pairs = []
        for _ in range(self.n):
            p1 = random.choices(population, weights=probabilities)[0]
            p2 = random.choices(population, weights=probabilities)[0]
            parent_pairs.append((p1, p2))
        self._debug(f"  Selected Parents: {parent_pairs}")
        return parent_pairs

    # # ── Stage V ──────────────────────────────────────────────────────────────

    def stage_v_crossover(self, parent_pairs):
        self._debug("\n[Stage V] Crossover:")
        children = []
        for p1, p2 in parent_pairs:
            b1 = self.represent_the_vec_in_binary(p1)
            b2 = self.represent_the_vec_in_binary(p2)
            cp = random.randint(1, self.n - 1)
            child = self.represent_bin_in_int(b1[:cp] + b2[cp:])
            children.append(child)
            
            self._debug(f"  Parents: {p1} ({b1}), {p2} ({b2})")
            self._debug(f"  Crossover Point: {cp}")
        return children

    # # ── Stage VI ─────────────────────────────────────────────────────────────

    # def stage_vi_mutation(self, children):
    #     mutated = []
    #     max_val = (10 ** (self.current_generation + 1)) - 1

    #     for child in children:
    #         if random.randint(0, max_val) < 10:
    #             cb = self.represent_the_vec_in_binary(child)
    #             flip = random.randint(0, self.n - 1)
    #             cb[flip] ^= 1
    #             mutated.append(self.represent_bin_in_int(cb))
    #         else:
    #             mutated.append(child)
    def stage_vi_mutation(self, children):
        """
        Adaptive mutation:
        - High mutation when coverage is low (exploration)
        - Low mutation when near convergence (exploitation)
        - Never drops below a safe minimum
        """

        self._debug("\n[Stage VI] Mutation:")
        # ── Adaptive mutation rate based on progress ─────────────────────
        if self.best_coverage < 70:
            mutation_rate = 0.30   # strong exploration
        elif self.best_coverage < 90:
            mutation_rate = 0.15   # balanced
        elif self.best_coverage < 100:
            mutation_rate = 0.05   # fine tuning
        else:
            mutation_rate = 0.01   # almost done
    
        mutated = []
    
        for child in children:
            if random.random() < mutation_rate:
                cb = self.represent_the_vec_in_binary(child)
    
                # Flip 1 bit (you can extend this if needed)
                flip_idx = random.randint(0, self.n - 1)
                cb[flip_idx] ^= 1
                self._debug(f"  {child} → {cb} (bit flipped at {flip_idx})")
                mutated.append(self.represent_bin_in_int(cb))
            else:
                self._debug(f"  {child} → No mutation")
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

        self._debug("\n[Stage VII] Combined Population:")
        self._debug(f"  {combined_population}")
        
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
        
        sorted_population = list(sorted_pop)

        # rebuild fault matrix in sorted order
        sorted_fault_matrix = np.array([
            combined_fault_matrix[combined_vector_map[v]]
            for v in sorted_population
        ], dtype=bool)

        # rebuild vector map
        sorted_vector_map = {v: i for i, v in enumerate(sorted_population)}
        self._debug(f"  Sorted Population: {sorted_pop}")
        self._debug(f"  Sorted Fitness: {sorted_fitnesses}")

        return sorted_population, sorted_fitnesses, sorted_fault_matrix, sorted_vector_map
        
        
  
        # return list(sorted_pop), sorted_fitnesses, combined_fault_matrix, combined_vector_map


    # ── Stage VIII ───────────────────────────────────────────────────────────
    # Greedy set cover: O(n²) vs original exhaustive O(C(n,k) * k)
    # For n=14: original tries thousands of combos; greedy picks best in n passes

    # def stage_viii_minimal_test_set(self, fin_pop, fault_matrix, vector_map):
    #     """
    #     Stage VIII — Minimal Test Set via Dynamic Programming (+ greedy fallback).

    #     For F ≤ _DP_FAULT_LIMIT faults the bitmask DP finds the PROVABLY OPTIMAL
    #     (minimum-cardinality) test set.  For F > _DP_FAULT_LIMIT the greedy
    #     O(V×F) fallback is used and disclosed in the log.

    #     Dynamic Programming formulation
    #     ────────────────────────────────
    #     State      : S  — bitmask of faults detected by vectors chosen so far
    #     Value      : dp[S] = min vectors needed to reach state S
    #     Recurrence : dp[S | cov(v)] = min(dp[S | cov(v)],  dp[S] + 1)
    #     Base case  : dp[0] = 0
    #     Answer     : reconstruct path to the state with maximum popcount

    #     Parameters  (unchanged — fully backward-compatible)
    #     ──────────
    #     fin_pop      : list[int]        — test vectors (integer bitmasks)
    #     fault_matrix : np.ndarray[bool] — shape (len(fin_pop), cumulatedFaults)
    #     vector_map   : dict[int, int]   — maps vector → row index in fault_matrix

    #     Returns     (unchanged)
    #     ───────
    #     selected : list[int]   — minimal / near-minimal set of test vectors
    #     coverage : float       — fault coverage % achieved by selected set
    #     """
    #     if not fin_pop or self.cumulatedFaults == 0:
    #         return [], 0.0
    #     self._debug("\n[Stage VIII] Fault Matrix:")
    #     self._debug(f"{fault_matrix}")
    #     # Convert boolean matrix rows → integer bitmasks
    #     coverage_masks, n_faults = _compress_fault_matrix(
    #         fault_matrix, vector_map, fin_pop
    #     )
    #     self._debug("Coverage Masks:")
    #     for vec, mask in zip(fin_pop, coverage_masks):
    #         print(f"Vector {vec} → Mask {mask} ({bin(mask)})")
    #     # Route: DP (optimal) or greedy (approximate) based on fault count
    #     if n_faults <= _DP_FAULT_LIMIT:
    #         self._log_detail(
    #             f"Stage VIII [DP]     : {n_faults} faults ≤ {_DP_FAULT_LIMIT}"
    #             f" → Bitmask DP  (provably optimal)"
    #         )
    #         selected, coverage = _dp_set_cover(
    #             coverage_masks, n_faults, fin_pop, self._check_time_limit
    #         )
    #         method = f"DP-optimal (F={n_faults})"
    #     else:
    #         self._log_detail(
    #             f"Stage VIII [Greedy] : {n_faults} faults > {_DP_FAULT_LIMIT}"
    #             f" → Greedy fallback (approximate)"
    #         )
    #         selected, coverage = _greedy_set_cover(
    #             coverage_masks, n_faults, fin_pop, self._check_time_limit
    #         )
    #         method = f"Greedy-approx (F={n_faults})"

    #     self._log_detail(
    #         f"Stage VIII result   : {len(selected)} vector(s),"
    #         f" {coverage:.2f}% coverage  [{method}]"
    #     )
    #     self._debug(f"Selected Vectors: {selected}")
    #     self._debug(f"Coverage Achieved: {coverage:.2f}%")
    #     return selected, coverage
    
    def stage_viii_minimal_test_set(self, fin_pop, fault_matrix, vector_map=None):
        """
        Fully order-invariant Stage VIII
        """

        if not fin_pop or self.cumulatedFaults == 0:
            return [], 0.0

        self._debug("\n[Stage VIII] Fault Matrix:")
        self._debug(f"{fault_matrix}")

        # ❌ NO vector_map USED ANYWHERE
        coverage_masks, n_faults = _compress_fault_matrix(
            fault_matrix,
            fin_pop
        )

        if n_faults <= _DP_FAULT_LIMIT:
            selected, coverage = _dp_set_cover(
                coverage_masks,
                n_faults,
                fin_pop,
                self._check_time_limit
            )
            method = f"DP-optimal (F={n_faults})"
        else:
            selected, coverage = _greedy_set_cover(
                coverage_masks,
                n_faults,
                fin_pop,
                self._check_time_limit
            )
            method = f"Greedy-approx (F={n_faults})"

        self._log_detail(
            f"Stage VIII result: {len(selected)} vectors, "
            f"{coverage:.2f}% [{method}]"
        )

        self._debug(f"Selected Vectors: {selected}")
        self._debug(f"Coverage Achieved: {coverage:.2f}%")

        return selected, coverage
        
        
    # ── Main Run ─────────────────────────────────────────────────────────────

    # def run(self):
    #     self._log("\n===== GA RUN STARTED =====")
    #     self._start_timer()

    #     self._log_detail("Stage I: Input Parameter Extraction")
    #     self.stage_i_input_Parameter_extratcion()
    #     self._log(f"Population size: {self.n} | Gates: {self.N} | Max TV: {self.max_no_of_TV}")

    #     self._log_detail("Stage II: Initial Test Vector Selection")
    #     init_population = self.stage_ii_TV_selection()
    #     self._log(f"Initial Population Size: {len(init_population)}")
    #     self._log_detail(f"Initial Population: {init_population}")

    #     for gen in range(self.max_generations):

    #         if self._check_time_limit():
    #             self._log("Terminated: Time limit reached.")
    #             break

    #         self.current_generation = gen
    #         self._log_detail(f"\n========== Generation {gen} ==========")

    #         # Fitness
    #         self._log_detail("Stage III: Fitness Evaluation")
    #         init_fitnesses, init_detected_matrix, init_vector_map, singleton_hit = \
    #             self.compute_fitness_for_population(init_population)
    #         if singleton_hit:
    #             self._log("Terminated: Single vector achieves 100% coverage.")
    #             self.best_coverage = 100.0
    #             self.best_vector_set = [list(init_vector_map.keys())[-1]]  # the winning vector
    #             self.detectedFaults = init_detected_matrix[-1]
    #             break

    #         # ── TLE or empty — abort generation immediately ───────────────────────
    #         if self._time_limit_exceeded or not init_fitnesses:
    #             self._log("Terminated: TLE or empty fitness — skipping remaining generations.")
    #             break

    #         max_fit = max(init_fitnesses)
    #         min_fit = min(init_fitnesses)
    #         avg_fit = sum(init_fitnesses) / len(init_fitnesses)
    #         self._log_detail(
    #             f"Fitness — Max: {max_fit:.4f} | Min: {min_fit:.4f} | Avg: {avg_fit:.4f}"
    #         )

    #         # Selection
    #         self._log_detail("Stage IV: Roulette Wheel Selection")
    #         parents = self.stage_iv_roulette_wheel_selection(init_fitnesses, init_population)
    #         self._log_detail(f"Selected Parents: {parents}")

    #         # Crossover
    #         self._log_detail("Stage V: Crossover")
    #         children = self.stage_v_crossover(parents)
    #         self._log_detail(f"Children: {children}")

    #         # Mutation
    #         self._log_detail("Stage VI: Mutation")
    #         mutated_children = self.stage_vi_mutation(children)
    #         self._log_detail(f"Mutated Children: {mutated_children}")

    #         # Population Update
    #         self._log_detail("Stage VII: Test Population Generation")
    #         fin_sorted_population, fin_sorted_fitnesses, \
    #         fin_detected_matrix, fin_vector_map = \
    #             self.stage_vii_test_population_generation(init_population, mutated_children)

    #         self._log_detail(f"Sorted Population: {fin_sorted_population}")
    #         self._log_detail(f"Sorted Fitnesses:  {fin_sorted_fitnesses}")

    #         # Coverage
    #         combined_detected_list = np.any(fin_detected_matrix, axis=0)
    #         detected_faults = int(np.sum(combined_detected_list))
    #         fault_coverage = (detected_faults / self.cumulatedFaults) * 100
    #         self._log_detail(
    #             f"Coverage — Detected: {detected_faults} / {self.cumulatedFaults}"
    #             f" = {fault_coverage:.2f}%"
    #         )

    #         # Minimization
    #         if not self.skip_minimization:
    #             self._log_detail("Stage VIII: Minimal Test Set Reduction (Greedy)")
    #             min_set, min_cov = self.stage_viii_minimal_test_set(
    #                 fin_sorted_population, fin_detected_matrix, fin_vector_map
    #             )
    #             self._log_detail(f"Minimal Set Coverage: {min_cov:.2f}%")

    #             if min_cov >= fault_coverage:
    #                 fault_coverage = min_cov
    #                 test_vectors = min_set
    #                 self._log_detail("Minimal set accepted.")
    #             else:
    #                 test_vectors = fin_sorted_population
    #                 self._log_detail("Original sorted population retained.")
    #         else:
    #             test_vectors = fin_sorted_population

    #         # Best Update
    #         if fault_coverage > self.best_coverage:
    #             self.best_coverage = fault_coverage
    #             self.best_vector_set = test_vectors
    #             self.detectedFaults = combined_detected_list
    #             self._log_detail(f"New best coverage: {self.best_coverage:.2f}%")

    #         # Compact Log
    #         self._log_compact(
    #             f"Gen {gen:03d} | "
    #             f"MaxFit: {max_fit:.4f} | "
    #             f"AvgFit: {avg_fit:.4f} | "
    #             f"Cov: {fault_coverage:6.2f}% | "
    #             f"Best: {self.best_coverage:6.2f}% | "
    #             f"Pop: {len(test_vectors)}"
    #         )

    #         # Threshold Check
    #         if fault_coverage >= self.threshold:
    #             self._log("Terminated: Coverage threshold reached.")
    #             break

    #         init_population = test_vectors[:self.population_size]
    #         self._log_detail(f"Next gen population (trimmed): {len(init_population)}")

    #         gc.collect()

    #     self._log(f"===== GA RUN COMPLETED — Best Coverage: {self.best_coverage:.2f}% =====")
    #     self._log_detail(f"Final Best Vector Set: {self.best_vector_set}")

    #     return self.save_results()
    def run(self):
        MAX_RUNS = 5
        final_result = None
    
        for attempt in range(1, MAX_RUNS + 1):
    
            # Reset state for each run
            self.current_generation = 0
            self.best_coverage = 0.0
            self.best_vector_set = []
            self.cumulatedFaults = 0
            self.detectedFaults = None
            self.execution_time = 0.0
            self._time_limit_exceeded = False
            self.fault_cache.clear()
    
            self._log(f"\n===== GA RUN STARTED (Attempt {attempt}) =====")
            self._start_timer()
    
            # ── Stage I ─────────────────────────────────────────────
            self.stage_i_input_Parameter_extratcion()
            self._log(f"Population size: {self.n} | Gates: {self.N} | Max TV: {self.max_no_of_TV}")
    
            # ── Stage II ────────────────────────────────────────────
            init_population = self.stage_ii_TV_selection()
            self._debug(f"\n[Stage II] Initial Population: {init_population}")
            # ── MAIN GA LOOP ────────────────────────────────────────
            for gen in range(self.max_generations):
                self._debug(f"\n========== Generation {gen} ==========")
                self._debug(f"Population: {init_population}")
                if self._check_time_limit():
                    self._log("Terminated: Time limit reached.")
                    break
    
                self.current_generation = gen
    
                # Fitness
                init_fitnesses, init_detected_matrix, init_vector_map, singleton_hit = \
                    self.compute_fitness_for_population(init_population)
    
                if singleton_hit:
                    self.best_coverage = 100.0
                    self.best_vector_set = [list(init_vector_map.keys())[-1]]
                    self.detectedFaults = init_detected_matrix[-1]
                    break
    
                if self._time_limit_exceeded or not init_fitnesses:
                    break
    
                # Selection → Crossover → Mutation → New Population
                parents = self.stage_iv_roulette_wheel_selection(init_fitnesses, init_population)
                children = self.stage_v_crossover(parents)
                mutated_children = self.stage_vi_mutation(children)

                fin_sorted_population, fin_sorted_fitnesses, \
                fin_detected_matrix, fin_vector_map = \
                    self.stage_vii_test_population_generation(init_population, mutated_children)
    
                combined_detected_list = np.any(fin_detected_matrix, axis=0)
                detected_faults = int(np.sum(combined_detected_list))
                fault_coverage = (detected_faults / self.cumulatedFaults) * 100

                
                self._debug(f"BM Coverage: {fault_coverage:.2f}%")
                self._debug(f"BM Best Coverage So Far: {self.best_coverage:.2f}%")
                
                # Minimization
                if not self.skip_minimization:
                    min_set, min_cov = self.stage_viii_minimal_test_set(
                        fin_sorted_population, fin_detected_matrix, fin_vector_map
                    )
                    if min_cov >= fault_coverage:
                        fault_coverage = min_cov
                        test_vectors = min_set
                    else:
                        test_vectors = fin_sorted_population
                else:
                    test_vectors = fin_sorted_population

                
                
                
                # Best update
                if fault_coverage > self.best_coverage:
                    self.best_coverage = fault_coverage
                    self.best_vector_set = test_vectors
                    self.detectedFaults = combined_detected_list

                self._debug(f"AM Coverage: {fault_coverage:.2f}%")
                self._debug(f"AM Best Coverage So Far: {self.best_coverage:.2f}%")
                
                if fault_coverage >= self.threshold:
                    break
    
                init_population = test_vectors[:self.population_size]
    
                gc.collect()
    
            self._log(f"===== RUN {attempt} COMPLETED — Best: {self.best_coverage:.2f}% =====")
    
            # final_result = self.save_results()
            result = self.save_results()
            
            if (final_result is None) or (result["Fault Coverage"] > final_result["Fault Coverage"]):
                final_result = result
    
            # ✅ STOP condition
            if self.best_coverage >= 100.0 and not self.skip_minimization:
                self._log("Stopping early: optimal result achieved.")
                break
    
            # Otherwise retry (until MAX_RUNS)
    
        return final_result
        # ── Save Results ─────────────────────────────────────────────────────────

    def save_results(self):
        self._update_execution_time()

        return {
            "Circuit Name":         self.circuit["Circuit Name"],
            "No of Lines":          self.circuit["No of Lines"],
            "No of Gates":          self.circuit["No of Gates"],
            "Fault Model":           "+".join(self.fault_models),
            "Total Faults":         self.cumulatedFaults,
            "GA Approach":          self.approach,
            "Detected Faults":      int(np.sum(self.detectedFaults)) if self.detectedFaults is not None else 0,
            "Fault Coverage":       self.best_coverage,
            "Test Set Size":        len(self.best_vector_set),
            "Best Vector Set":      self.best_vector_set,
            "Execution Time":       round(self.execution_time, 4),
            "Actual Generations":   self.current_generation + 1,
            "Time Limit Exceeded":  self._time_limit_exceeded,
            "Minimization Skipped": self.skip_minimization,
        }
