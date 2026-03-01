"""
Utility functions for CMGF GA Analysis and Visualization
"""

import matplotlib.pyplot as plt
from typing import List, Dict
import json


class CMGFAnalyzer:
    """Analyzer for CMGF test results"""
    
    def __init__(self):
        self.generation_data = []
    
    def log_generation(self, generation: int, best_fitness: float, 
                      test_set: List[int], coverage: float):
        """Log data for a generation"""
        self.generation_data.append({
            'generation': generation,
            'best_fitness': best_fitness,
            'test_set_size': len(test_set),
            'coverage': coverage
        })
    
    def plot_convergence(self, save_path: str = None):
        """Plot convergence curve"""
        if not self.generation_data:
            print("No data to plot")
            return
        
        generations = [d['generation'] for d in self.generation_data]
        coverages = [d['coverage'] for d in self.generation_data]
        
        plt.figure(figsize=(10, 6))
        plt.plot(generations, coverages, marker='o', linewidth=2, markersize=6)
        plt.xlabel('Generation', fontsize=12)
        plt.ylabel('Fault Coverage (%)', fontsize=12)
        plt.title('GA Convergence - CMGF Detection', fontsize=14, fontweight='bold')
        plt.grid(True, alpha=0.3)
        plt.ylim(0, 105)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
    
    def save_results(self, test_set: List[int], coverage: float, 
                    circuit_name: str, filename: str = "results.json"):
        """Save results to JSON file"""
        results = {
            'circuit_name': circuit_name,
            'test_set_decimal': test_set,
            'test_set_binary': [bin(v) for v in test_set],
            'final_coverage': coverage,
            'generation_history': self.generation_data
        }
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"Results saved to {filename}")


def display_test_vectors(test_set: List[int], n: int, circuit_name: str = ""):
    """Display test vectors in a formatted table"""
    print(f"\n{'='*60}")
    print(f"Test Vectors for {circuit_name}")
    print(f"{'='*60}")
    print(f"{'Index':<10}{'Decimal':<15}{'Binary':<15}")
    print(f"{'-'*60}")
    
    for idx, vector in enumerate(test_set):
        binary = format(vector, f'0{n}b')
        print(f"{idx+1:<10}{vector:<15}{binary:<15}")
    
    print(f"{'='*60}")
    print(f"Total Test Vectors: {len(test_set)}")
    print(f"{'='*60}\n")


def compare_algorithms(results: Dict[str, tuple]):
    """
    Compare results from different algorithm runs
    
    Args:
        results: Dict mapping algorithm_name -> (test_set, coverage)
    """
    print(f"\n{'='*80}")
    print(f"Algorithm Comparison")
    print(f"{'='*80}")
    print(f"{'Algorithm':<30}{'Test Set Size':<20}{'Coverage (%)':<20}")
    print(f"{'-'*80}")
    
    for algo_name, (test_set, coverage) in results.items():
        print(f"{algo_name:<30}{len(test_set):<20}{coverage:<20.2f}")
    
    print(f"{'='*80}\n")


def analyze_fault_detection(circuit, test_vectors: List[int]):
    """
    Analyze which faults are detected by each test vector
    
    Args:
        circuit: ReversibleCircuit object
        test_vectors: List of test vectors
    """
    print(f"\n{'='*70}")
    print(f"Fault Detection Analysis")
    print(f"{'='*70}")
    
    all_detected = set()
    
    for vector in test_vectors:
        binary = format(vector, f'0{circuit.n}b')
        fault_free = circuit.compute_output(vector, skip_gate=-1)
        detected = set()
        
        for gate_idx in range(circuit.N):
            faulty = circuit.compute_output(vector, skip_gate=gate_idx)
            if faulty != fault_free:
                detected.add(gate_idx)
        
        all_detected.update(detected)
        
        print(f"Vector {vector} ({binary}): Detects {len(detected)} faults -> {sorted(detected)}")
    
    print(f"{'-'*70}")
    print(f"Total Unique Faults Detected: {len(all_detected)} / {circuit.N}")
    print(f"Coverage: {(len(all_detected) / circuit.N * 100):.2f}%")
    print(f"Undetected Faults: {sorted(set(range(circuit.N)) - all_detected)}")
    print(f"{'='*70}\n")


# Example custom circuit definitions
class ToffoliCircuit:
    """Example: Reversible circuit with Toffoli gates"""
    
    def __init__(self, n: int, gate_configs: List[tuple]):
        """
        Args:
            n: Number of input lines
            gate_configs: List of (control1, control2, target) for each Toffoli gate
        """
        self.n = n
        self.N = len(gate_configs)
        self.gate_configs = gate_configs
        self.circuit_name = f"Toffoli_{n}_{self.N}"
        self.max_vectors = 2 ** n
        self.gates = self._create_toffoli_gates()
    
    def _create_toffoli_gates(self):
        """Create Toffoli gate operations"""
        gates = []
        for ctrl1, ctrl2, target in self.gate_configs:
            def toffoli_gate(x, c1=ctrl1, c2=ctrl2, t=target):
                # Toffoli: flip target if both controls are 1
                if ((x >> c1) & 1) and ((x >> c2) & 1):
                    x ^= (1 << t)
                return x
            gates.append(toffoli_gate)
        return gates
    
    def compute_output(self, input_vector: int, skip_gate: int = -1) -> int:
        """Compute output with optional gate skip for CMGF"""
        state = input_vector
        for gate_idx in range(self.N):
            if gate_idx != skip_gate:
                state = self.gates[gate_idx](state)
        return state


def benchmark_example():
    """Run a benchmark example with the 3_17tc circuit"""
    from cmgf_ga_random_search import CMGFGeneticAlgorithm, ReversibleCircuit
    
    print("\n" + "="*80)
    print("BENCHMARK: 3_17tc Circuit")
    print("="*80 + "\n")
    
    # Create circuit
    circuit = ReversibleCircuit(n=3, N=17, circuit_name="3_17tc")
    
    # Initialize analyzer
    analyzer = CMGFAnalyzer()
    
    # Run GA
    ga = CMGFGeneticAlgorithm(
        circuit=circuit,
        threshold=100.0,
        population_size=3,
        max_generations=100
    )
    
    # Custom run with logging
    init_pop = ga.stage_ii_random_selection()
    
    for generation in range(ga.max_generations):
        ga.current_generation = generation
        
        fitness_data = ga.compute_population_fitness(init_pop)
        parent_pairs = ga.stage_iv_roulette_wheel_selection(fitness_data)
        children = ga.stage_v_crossover(parent_pairs)
        mutated_children = ga.stage_vi_mutation(children)
        fin_pop = ga.stage_vii_test_population_generation(init_pop, mutated_children)
        test_set, coverage = ga.stage_viii_minimal_test_set(fin_pop)
        
        # Log generation data
        analyzer.log_generation(generation, fin_pop[0][1], test_set, coverage)
        
        if coverage >= ga.threshold:
            print(f"\n✓ Threshold met in generation {generation + 1}")
            break
        
        # Prepare next generation
        num_best = max(1, ga.population_size // 2)
        best_vectors = [item[0] for item in fin_pop[:num_best]]
        remaining_slots = ga.population_size - len(best_vectors)
        
        if remaining_slots > 0:
            random_vectors = ga.stage_ii_random_selection(remaining_slots)
            init_pop = best_vectors + random_vectors
        else:
            init_pop = best_vectors
    
    # Display results
    display_test_vectors(test_set, circuit.n, circuit.circuit_name)
    analyze_fault_detection(circuit, test_set)
    
    # Save results
    analyzer.save_results(test_set, coverage, circuit.circuit_name, "3_17tc_results.json")
    
    # Plot convergence (commented out if matplotlib not available)
    # analyzer.plot_convergence("convergence.png")
    
    print(f"\nFinal Results:")
    print(f"  Test Set: {test_set}")
    print(f"  Binary: {[format(v, '03b') for v in test_set]}")
    print(f"  Coverage: {coverage:.2f}%")
    print(f"  Generations: {generation + 1}")


if __name__ == "__main__":
    benchmark_example()
