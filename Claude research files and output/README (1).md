# CMGF Genetic Algorithm with Random Search

Complete Python implementation of a Genetic Algorithm (GA) for detecting Complete Missing-Gate Faults (CMGF) in Reversible Circuits using Random Search methodology.

## Overview

This implementation follows the 10-stage algorithm for automatic test pattern generation:

1. **Stage I**: Input Parameter Extraction
2. **Stage II**: Test Vector Selection (Random Search)
3. **Stage III**: Fitness Function Computation
4. **Stage IV**: Roulette Wheel Selection
5. **Stage V**: Reproduction and Cross-Over
6. **Stage VI**: Mutation
7. **Stage VII**: Test Population Generation
8. **Stage VIII**: Minimal Test Set Generation
9. **Stage IX**: Filial Generation (Recursion)
10. **Stage X**: Output

## Files

- `cmgf_ga_random_search.py` - Main implementation with core GA classes
- `cmgf_utilities.py` - Utility functions for analysis and visualization
- `README.md` - This documentation file

## Installation

```bash
# Required packages
pip install numpy matplotlib --break-system-packages

# Optional for visualization
pip install matplotlib --break-system-packages
```

## Quick Start

### Basic Usage

```python
from cmgf_ga_random_search import ReversibleCircuit, CMGFGeneticAlgorithm

# Create a reversible circuit
circuit = ReversibleCircuit(n=3, N=17, circuit_name="3_17tc")

# Initialize GA
ga = CMGFGeneticAlgorithm(
    circuit=circuit,
    threshold=100.0,  # Target fault coverage
    population_size=3,
    max_generations=50
)

# Run the algorithm
test_set, coverage = ga.run(verbose=True)

print(f"Final Test Set: {test_set}")
print(f"Coverage: {coverage:.2f}%")
```

### Running the Examples

```bash
# Run main example
python cmgf_ga_random_search.py

# Run benchmark with utilities
python cmgf_utilities.py
```

## Class Documentation

### ReversibleCircuit

Represents a reversible circuit for CMGF testing.

**Parameters:**
- `n` (int): Number of input lines
- `N` (int): Number of gates/levels
- `circuit_name` (str): Name identifier for the circuit

**Methods:**
- `compute_output(input_vector, skip_gate=-1)`: Computes circuit output
  - `input_vector`: Input as decimal number
  - `skip_gate`: Gate index to skip for CMGF simulation (-1 for fault-free)

### CMGFGeneticAlgorithm

Main GA implementation for CMGF test generation.

**Parameters:**
- `circuit`: ReversibleCircuit object
- `threshold`: Desired fault coverage percentage (default: 100.0)
- `population_size`: Population size (default: n)
- `max_generations`: Maximum generations (default: 100)

**Key Methods:**

#### Stage II: Random Selection
```python
vectors = ga.stage_ii_random_selection(size=3)
# Returns: [4, 6, 1] - randomly selected unique vectors
```

#### Stage III: Fitness Computation
```python
coverage, detected_faults = ga.stage_iii_fitness_computation(vector=5)
# Returns: (85.7, {0, 2, 5, 8, ...}) - coverage % and detected fault set
```

#### Stage IV: Roulette Wheel Selection
```python
parent_pairs = ga.stage_iv_roulette_wheel_selection(fitness_data)
# Returns: [(4, 6), (1, 4), ...] - parent pairs for crossover
```

#### Stage V: Crossover
```python
children = ga.stage_v_crossover(parent_pairs)
# Returns: [5, 2, ...] - offspring vectors
```

#### Stage VI: Mutation
```python
mutated = ga.stage_vi_mutation(children)
# Returns: [7, 2, ...] - mutated offspring
```

#### Stage VIII: Minimal Test Set
```python
test_set, coverage = ga.stage_viii_minimal_test_set(fin_pop)
# Returns: ([5, 6], 100.0) - minimal test set and coverage
```

## Algorithm Flow

```
┌─────────────────────────────────────────────┐
│  Stage I: Parameter Extraction              │
│  (n=3, N=17, threshold=100%)               │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  Stage II: Random Selection                 │
│  InitPop = {4, 6, 1}                       │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  Stage III: Fitness Computation             │
│  Calculate coverage for each vector         │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  Stage IV: Roulette Wheel Selection         │
│  Select parent pairs based on fitness       │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  Stage V: Crossover                         │
│  Generate offspring from parents            │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  Stage VI: Mutation                         │
│  Apply random bit flips                     │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  Stage VII: Population Generation           │
│  Combine and sort by fitness                │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  Stage VIII: Minimal Test Set               │
│  Find smallest set meeting threshold        │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
              Threshold Met? ──No──┐
                   │                │
                  Yes               │
                   │                │
                   ▼                ▼
              ┌─────────┐    ┌──────────────┐
              │ Output  │    │  Stage IX:   │
              │         │    │  Next Gen    │
              └─────────┘    └──────┬───────┘
                                    │
                                    └─────► Loop back to Stage III
```

## Examples

### Example 1: Circuit 3_17tc

```python
from cmgf_ga_random_search import ReversibleCircuit, CMGFGeneticAlgorithm

# Create the 3_17tc benchmark circuit
circuit = ReversibleCircuit(n=3, N=17, circuit_name="3_17tc")

# Initialize GA
ga = CMGFGeneticAlgorithm(circuit, threshold=100.0, population_size=3)

# Run algorithm
test_set, coverage = ga.run()

# Expected output: {101, 110} or similar with 100% coverage
```

### Example 2: Custom Circuit with Analysis

```python
from cmgf_ga_random_search import ReversibleCircuit, CMGFGeneticAlgorithm
from cmgf_utilities import display_test_vectors, analyze_fault_detection

# Create custom circuit
circuit = ReversibleCircuit(n=4, N=10, circuit_name="custom_4_10")

# Run GA
ga = CMGFGeneticAlgorithm(circuit, threshold=100.0)
test_set, coverage = ga.run(verbose=True)

# Display formatted results
display_test_vectors(test_set, circuit.n, circuit.circuit_name)

# Analyze which faults are detected
analyze_fault_detection(circuit, test_set)
```

### Example 3: Toffoli Gate Circuit

```python
from cmgf_utilities import ToffoliCircuit
from cmgf_ga_random_search import CMGFGeneticAlgorithm

# Define Toffoli gates: (control1, control2, target)
gates = [(0, 1, 2), (1, 2, 0), (0, 2, 1)]

# Create Toffoli circuit
circuit = ToffoliCircuit(n=3, gate_configs=gates)

# Run GA
ga = CMGFGeneticAlgorithm(circuit, threshold=100.0)
test_set, coverage = ga.run()
```

## Understanding the Output

### Generation Output
```
Generation 1:
  InitPop: [4, 6, 1]
  FinPop (top 5): [6, 4, 1, 5, 7]
  Best fitness: 82.35%
  Test Set: [6, 4]
  Coverage: 94.12%
```

- **InitPop**: Initial population for this generation
- **FinPop**: Final population after crossover and mutation
- **Best fitness**: Highest individual vector coverage
- **Test Set**: Current minimal test set candidate
- **Coverage**: Combined coverage of the test set

### Final Output
```
=== Threshold Met in Generation 15 ===
Final Test Set: [5, 6]
Fault Coverage: 100.00%
```

### Binary Representation
```
Test Set (Decimal): [5, 6]
Test Set (Binary): ['101', '110']
```

## Customization

### Custom Gate Operations

```python
class CustomCircuit(ReversibleCircuit):
    def _initialize_gates(self):
        gates = []
        # Define your custom gate operations
        gates.append(lambda x: x ^ 0b101)  # XOR with 101
        gates.append(lambda x: (x << 1) | (x >> 2))  # Shift
        # Add more gates...
        return gates
```

### Custom Fitness Function

```python
class CustomGA(CMGFGeneticAlgorithm):
    def stage_iii_fitness_computation(self, vector):
        # Your custom fitness computation
        coverage, detected = super().stage_iii_fitness_computation(vector)
        # Add penalty for certain vectors
        if vector > 10:
            coverage *= 0.9
        return coverage, detected
```

## Performance Tips

1. **Population Size**: Start with `population_size = n` (number of input lines)
2. **Max Generations**: Use 50-100 for small circuits, 200+ for larger ones
3. **Threshold**: Set to 100% for complete coverage, lower for faster convergence
4. **Random Seed**: Use `random.seed()` for reproducible results

## Algorithm Parameters

| Parameter | Description | Typical Value |
|-----------|-------------|---------------|
| n | Input lines | 3-10 |
| N | Number of gates | 10-100 |
| threshold | Target coverage | 100% |
| population_size | Vectors per generation | n |
| max_generations | Generation limit | 50-200 |
| mutation_prob | Initial mutation rate | 0.3 |

## Troubleshooting

### Issue: Low Coverage
- Increase `max_generations`
- Increase `population_size`
- Check gate definitions

### Issue: Slow Convergence
- Reduce `threshold` temporarily
- Adjust mutation probability decay rate
- Use smaller population initially

### Issue: No Improvement
- Verify circuit gate operations
- Check if threshold is achievable
- Try different random seeds

## Mathematical Formulas

### Fault Coverage
```
Coverage = (Detected Faults / Total Faults) × 100%
         = (|D| / N) × 100%
```

Where:
- D = Set of detected faults
- N = Total number of gates

### Mutation Probability
```
P_mutation(t) = 0.3 × e^(-0.1t)
```

Where t = current generation

### Fitness Proportional Selection
```
P(i) = fitness(i) / Σ fitness(j)
```

## References

This implementation is based on the Genetic Algorithm methodology for Complete Missing-Gate Fault detection in Reversible Circuits using Random Search for test vector selection.

## License

This code is provided for educational and research purposes.

## Contributing

Feel free to extend this implementation with:
- Additional circuit types
- Alternative selection strategies
- Parallel processing
- Visualization enhancements
- Performance optimizations
