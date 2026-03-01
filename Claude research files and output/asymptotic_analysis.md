# Asymptotic Analysis of CMGF Genetic Algorithm with Random Search

## Table of Contents
1. [Overview](#overview)
2. [Notation and Parameters](#notation-and-parameters)
3. [Stage-by-Stage Analysis](#stage-by-stage-analysis)
4. [Overall Complexity](#overall-complexity)
5. [Space Complexity](#space-complexity)
6. [Comparative Analysis](#comparative-analysis)
7. [Optimization Opportunities](#optimization-opportunities)

---

## Overview

This document provides a complete asymptotic (Big-O) analysis of the Genetic Algorithm for Complete Missing-Gate Fault (CMGF) detection in Reversible Circuits using Random Search methodology.

---

## Notation and Parameters

| Symbol | Description | Typical Range |
|--------|-------------|---------------|
| **n** | Number of input lines | 3-10 |
| **N** | Number of gates/levels in circuit | 10-100 |
| **P** | Population size | Usually P ≈ n |
| **G** | Number of generations | 50-200 |
| **L** | Initial combination size for test set | L ≈ n/2 |
| **M** | Maximum test set size considered | M ≤ P |
| **V** | Maximum possible input vectors | V = 2^n |

---

## Stage-by-Stage Analysis

### Stage I: Input Parameter Extraction

**Operation:** Initialize circuit parameters (n, N, threshold, etc.)

```
Time Complexity: O(1)
Space Complexity: O(1)
```

**Justification:**
- Simple variable assignments
- No loops or complex operations
- Constant time regardless of input size

---

### Stage II: Test Vector Selection (Random Search)

**Operation:** Randomly select P unique vectors from range [0, 2^n - 1]

```
Time Complexity: O(P)
Space Complexity: O(P)
```

**Detailed Analysis:**

```python
# Pseudocode
available_vectors = [0, 1, 2, ..., 2^n - 1]  # O(2^n) space, O(2^n) time to create
selected = random.sample(available_vectors, P)  # O(P) time
```

**Best Case:** O(P) - Direct random sampling without conflicts
**Average Case:** O(P) - Random sampling with minimal conflicts
**Worst Case:** O(P log P) - If using rejection sampling with many conflicts

**Note:** 
- Creating the full range [0, 2^n - 1] takes O(2^n) time and space
- However, this can be optimized to O(P) by using random integers directly
- Our implementation uses the optimized approach

**Optimized Implementation:**
```
Time: O(P)
Space: O(P)
```

---

### Stage III: Fitness Function Computation

**Operation:** Compute fault coverage for each vector in population

**For a SINGLE vector:**

```python
# Pseudocode for one vector
1. Binary conversion:                     O(n)
2. Compute fault-free output:             O(N × C)  where C = gate operation cost
3. For each gate (N iterations):
   - Simulate CMGF (skip gate):           O(N × C)
   - Compare outputs:                     O(1)
4. Calculate coverage:                    O(1)
```

**Single Vector Complexity:**
```
Time: O(n + N × C + N × (N × C)) = O(n + N²C)
     ≈ O(N²)  (assuming C is constant and N >> n)
```

**For ENTIRE population (P vectors):**
```
Time Complexity: O(P × N²)
Space Complexity: O(P × N)  [storing detected faults for each vector]
```

**Breakdown:**
- Binary conversion for P vectors: O(P × n)
- Fault simulation for P vectors: O(P × N²)
- Storage of detected faults: O(P × N)

---

### Stage IV: Roulette Wheel Selection

**Operation:** Select parent pairs based on fitness-proportional probabilities

```python
# Pseudocode
1. Calculate total fitness:                O(P)
2. Calculate probabilities:                O(P)
3. Select P/2 parent pairs:
   - For each pair:
     * Random selection with weights:     O(P)
   - Total pairs: P/2                     O(P²)
```

**Time Complexity: O(P²)**
**Space Complexity: O(P)**

**Detailed Analysis:**
- Calculating cumulative probabilities: O(P)
- Each weighted random selection: O(P) using linear search
- Total selections: P (for P/2 pairs × 2 parents)
- Total: O(P × P) = O(P²)

**Optimization Note:** 
- Can be reduced to O(P log P) using binary search
- Or O(P) with alias method preprocessing

---

### Stage V: Reproduction and Cross-Over

**Operation:** Generate offspring from parent pairs through crossover

```python
# Pseudocode
For each parent pair (P/2 pairs):
  1. Convert parents to binary:           O(n)
  2. Select crossover point:              O(1)
  3. Create child:                        O(n)
  4. Convert to decimal:                  O(n)
```

**Time Complexity: O(P × n)**
**Space Complexity: O(P × n)**

**Breakdown:**
- Number of pairs: P/2
- Operations per pair: O(n)
- Total: O(P/2 × n) = O(P × n)

---

### Stage VI: Mutation

**Operation:** Apply random bit flips to child vectors

```python
# Pseudocode
For each child (P/2 children):
  1. Calculate mutation probability:      O(1)
  2. Generate random number:              O(1)
  3. If mutate:
     - Convert to binary:                 O(n)
     - Flip random bit:                   O(n)
     - Convert to decimal:                O(n)
```

**Time Complexity: O(P × n)**
**Space Complexity: O(P × n)**

**Breakdown:**
- Number of children: ≈ P/2
- Worst case (all mutate): O(P × n)
- Expected case: O(P_m × n) where P_m = mutation probability × P

---

### Stage VII: Test Population Generation

**Operation:** Combine and sort populations by fitness

```python
# Pseudocode
1. Combine InitPop and ChildPop:          O(P)
2. Remove duplicates:                     O(P log P) or O(P) with hash set
3. Compute fitness for all:               O(P × N²)
4. Sort by fitness:                       O(P log P)
```

**Time Complexity: O(P × N²)**
**Space Complexity: O(P)**

**Note:** Dominated by fitness computation O(P × N²)

---

### Stage VIII: Minimal Test Set Generation

**Operation:** Find smallest combination achieving threshold coverage

```python
# Pseudocode
For L = initial_size to M:                      # O(M - L) iterations
  For each combination of size L:               # C(P, L) combinations
    1. Compute combined coverage:               O(L × N²)
    2. Check threshold:                         O(1)
```

**Time Complexity: O(∑[L to M] C(P, L) × L × N²)**

**Worst Case Analysis:**

In the worst case, we try all combinations:
```
∑[L=1 to P] C(P, L) × L × N² = O(2^P × P × N²)
```

**However, in practice:**
- Algorithm often finds solution with small L (typically L ≈ n/2)
- Early termination when threshold is met
- Practical combinations checked: O(C(P, L) × L × N²)

**Best Case:** O(C(P, L) × L × N²) where L is small
**Average Case:** O(C(P, n) × n × N²)
**Worst Case:** O(2^P × P × N²)

**Space Complexity: O(P × N)**

---

### Stage IX: Filial Generation (Recursion)

**Operation:** Prepare next generation's initial population

```python
# Pseudocode
1. Select best vectors from FinPop:       O(P)
2. Fill remaining with random search:     O(P)  [Stage II]
```

**Time Complexity: O(P)**
**Space Complexity: O(P)**

---

### Stage X: Output

**Operation:** Return final test set and coverage

```
Time Complexity: O(1)
Space Complexity: O(M)  where M is test set size
```

---

## Overall Complexity

### Per Generation Complexity

Summing all stages executed in one generation:

```
T_generation = T_II + T_III + T_IV + T_V + T_VI + T_VII + T_VIII + T_IX

             = O(P) + O(P×N²) + O(P²) + O(P×n) + O(P×n) + O(P×N²) + O(C(P,L)×L×N²) + O(P)
             
             = O(P×N² + P² + C(P,L)×L×N²)
```

**Dominant Terms:**
- If Stage VIII is quick (small L, early success): **O(P × N²)**
- If Stage VIII explores many combinations: **O(C(P,L) × L × N²)**

### Total Algorithm Complexity

Running for G generations:

```
T_total = G × T_generation

        = O(G × (P×N² + C(P,L)×L×N²))
```

**Typical Case (L is small, ≈ n/2):**
```
T_total = O(G × P × N²)
```

**Worst Case (exploring many combinations):**
```
T_total = O(G × 2^P × P × N²)
```

---

## Complete Complexity Summary

### Time Complexity

| Scenario | Complexity | Conditions |
|----------|------------|------------|
| **Best Case** | **O(G × P × N²)** | Early convergence, small test sets found quickly |
| **Average Case** | **O(G × P × N² + G × C(P,n) × n × N²)** | Typical behavior with moderate combination search |
| **Worst Case** | **O(G × 2^P × P × N²)** | Exhaustive combination search needed |

### Practical Complexity

Given typical parameters:
- P ≈ n (population size equals input lines)
- L ≈ n/2 (initial combination size)
- N >> n (gates much more than inputs)
- G ≈ 50-200 (reasonable generation count)

**Expected Complexity:**
```
T = O(G × n × N²)
```

**With concrete numbers (n=3, N=17, G=50, P=3):**
```
T ≈ 50 × 3 × 17² ≈ 43,350 operations
```

---

## Space Complexity

### Per Generation

```
S_generation = S_population + S_fitness_data + S_children + S_temp

             = O(P) + O(P×N) + O(P) + O(P)
             
             = O(P × N)
```

### Total Space

```
S_total = O(P × N)
```

**Note:** Space does not accumulate across generations (populations are replaced)

### Detailed Space Breakdown

| Component | Space | Description |
|-----------|-------|-------------|
| Population vectors | O(P) | Current population |
| Fitness data (detected faults) | O(P × N) | Set of detected faults per vector |
| Parent pairs | O(P) | Temporary storage |
| Children | O(P) | Temporary storage |
| Test set candidates | O(M) | Where M ≤ P |
| **Total** | **O(P × N)** | Dominated by fitness data |

---

## Comparative Analysis

### Comparison with Exhaustive Search

**Exhaustive Search:**
- Tests all possible combinations of vectors
- Time: O(2^V × V × N²) where V = 2^n
- For n=3: O(2^8 × 8 × N²) = O(2048 × N²)

**GA with Random Search:**
- Time: O(G × P × N²)
- For n=3, G=50, P=3: O(150 × N²)

**Speedup Factor:**
```
Speedup = 2048 / 150 ≈ 13.6×
```

### Scalability Analysis

**How complexity grows with parameters:**

| Parameter | Change | Time Impact | Space Impact |
|-----------|--------|-------------|--------------|
| n (inputs) | +1 | ~2× (exponential in V, linear in P) | ~2× |
| N (gates) | +1 | Linear (N²) | Linear |
| P (population) | +1 | Linear to quadratic | Linear |
| G (generations) | +1 | Linear | Constant |

---

## Asymptotic Bounds

### Lower Bound (Ω)

**Minimum work required:**
- Must evaluate at least one test set: Ω(N)
- Must process population: Ω(P)
- Must simulate faults: Ω(N)

**Therefore:** Ω(P × N)

### Upper Bound (O)

**Maximum work (worst case):**
- Exhaustive combination search: O(2^P)
- Multiple generations: O(G)
- Fault simulation: O(N²)

**Therefore:** O(G × 2^P × N²)

### Tight Bound (Θ)

**For typical execution:**
Θ(G × P × N²)

---

## Optimization Opportunities

### 1. Fitness Computation Caching
**Current:** O(P × N²) per generation
**Optimized:** O(P_new × N²) where P_new = new vectors only

**Potential Savings:** 50-70% in later generations

### 2. Parallel Fitness Evaluation
**Current:** Sequential evaluation
**Optimized:** Parallel across P vectors

**Speedup:** Up to P× with P processors
**New Complexity:** O(G × N²) with P processors

### 3. Roulette Wheel with Binary Search
**Current:** O(P²) for selection
**Optimized:** O(P log P) with binary search

**Improvement:** O(P²) → O(P log P)

### 4. Incremental Coverage Calculation
**Current:** Recalculate coverage for each combination
**Optimized:** Update coverage incrementally

**Stage VIII Improvement:**
```
Current:  O(C(P,L) × L × N²)
Optimized: O(C(P,L) × L × N)
```

### 5. Early Termination in Combination Search
**Current:** May search many combinations
**Optimized:** Stop at first threshold-meeting set

**Expected Improvement:** 2-5× reduction in Stage VIII

### 6. Smart Initialization
**Current:** Pure random selection
**Optimized:** Greedy initial population

**Benefit:** Faster convergence, fewer generations needed

---

## Asymptotic Comparison Table

| Operation | Naive | Current | Optimized |
|-----------|-------|---------|-----------|
| **Random Selection** | O(2^n) | O(P) | O(P) |
| **Fitness (single)** | O(N²) | O(N²) | O(N²) cached |
| **Fitness (population)** | O(P×N²) | O(P×N²) | O(P_new×N²) |
| **Parent Selection** | O(P²) | O(P²) | O(P log P) |
| **Crossover** | O(P×n) | O(P×n) | O(P×n) |
| **Mutation** | O(P×n) | O(P×n) | O(P×n) |
| **Sorting** | O(P log P) | O(P log P) | O(P log P) |
| **Test Set Search** | O(2^P×P×N²) | O(C(P,L)×L×N²) | O(C(P,L)×L×N) |
| **Per Generation** | - | O(P×N²) | O(P_new×N + P log P) |
| **Total** | O(2^V×V×N²) | **O(G×P×N²)** | **O(G×P×N)** |

---

## Practical Performance Estimates

### Example Circuit: 3_17tc (n=3, N=17)

**Parameters:**
- n = 3, N = 17, P = 3, G = 50, L = 2

**Per Generation:**
```
T_gen = P×N² + C(P,L)×L×N²
      = 3×17² + C(3,2)×2×17²
      = 867 + 3×2×289
      = 867 + 1,734
      = 2,601 operations
```

**Total Algorithm:**
```
T_total = G × T_gen
        = 50 × 2,601
        = 130,050 operations
```

**With Optimizations:**
```
T_optimized ≈ 50 × (3×17 + 3×2×17)
           ≈ 50 × (51 + 102)
           ≈ 7,650 operations
```

**Speedup:** ~17×

---

## Conclusion

### Key Findings

1. **Dominant Factor:** Fault simulation (O(N²)) dominates per-vector cost
2. **Scalability:** Algorithm scales well with n and N
3. **Bottleneck:** Combination search in Stage VIII can be exponential
4. **Practical Performance:** Much better than theoretical worst case

### Asymptotic Classification

```
Best Case:     O(G × P × N²)
Average Case:  O(G × P × N² + G × C(P,n) × n × N²)
Worst Case:    O(G × 2^P × P × N²)
Space:         O(P × N)
```

### Recommendations

1. **For small circuits (N < 20):** Current implementation is efficient
2. **For large circuits (N > 50):** Use optimizations (caching, parallel)
3. **For large populations (P > 10):** Optimize parent selection
4. **For deep search (L large):** Use incremental coverage updates

---

## Mathematical Proofs

### Theorem 1: Fitness Computation Complexity

**Statement:** Computing fitness for a single vector requires Θ(N²) operations.

**Proof:**
1. Fault-free output computation: Θ(N) gate evaluations
2. For each of N gates (CMGF simulation):
   - Skip gate i: Θ(N) operations
   - Total: N × Θ(N) = Θ(N²)
3. Comparison and counting: Θ(N)
4. Total: Θ(N²) + Θ(N) + Θ(N) = Θ(N²)

∴ **Fitness computation is Θ(N²)** □

### Theorem 2: Generation Lower Bound

**Statement:** Each generation requires at least Ω(P × N) operations.

**Proof:**
1. Must evaluate fitness for P vectors: Ω(P)
2. Each fitness evaluation requires examining N faults: Ω(N)
3. Cannot skip any vector or fault for correctness
4. Therefore: Ω(P × N)

∴ **Generation complexity is Ω(P × N)** □

### Theorem 3: Combination Search Worst Case

**Statement:** Finding minimal test set can require O(2^P) combinations in worst case.

**Proof:**
1. In worst case, threshold is met only by complete set
2. Algorithm tries combinations of size 1, 2, ..., P
3. Total combinations: ∑[i=1 to P] C(P,i) = 2^P - 1
4. Each requires coverage computation: O(N²)
5. Total: O(2^P × N²)

∴ **Worst case combination search is O(2^P × N²)** □

---

## Appendix: Complexity Notation Reference

| Notation | Name | Meaning |
|----------|------|---------|
| O(f(n)) | Big-O | Upper bound (worst case) |
| Ω(f(n)) | Big-Omega | Lower bound (best case) |
| Θ(f(n)) | Big-Theta | Tight bound (exact order) |
| o(f(n)) | Little-o | Strict upper bound |
| ω(f(n)) | Little-omega | Strict lower bound |

**Example:**
- f(n) = 3n² + 2n + 1
- O(n²) - grows at most as fast as n²
- Ω(n²) - grows at least as fast as n²
- Θ(n²) - grows exactly as fast as n²

---

*End of Asymptotic Analysis*
