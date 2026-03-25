"""
Directed Initialization for Reversible Circuit ATPG
=====================================================
Drop-in replacement for GeneticAlgorithm.stage_ii_TV_selection().

Algorithm reference
-------------------
SELECTION(n, Bt, Bc0..Bck, target) from the directed-initialization paper:

  1. Build a vector with target=0, all controls=1, other lines random  → detects fault on target
  2. Sweep all 2^(k+1)-1 control-bit combinations with target=1       → exercises every control state
  3. Fill remaining budget (up to n-2) with random vectors
  4. Always append all-ones then all-zeros                             → boundary coverage

The method is injected into the GeneticAlgorithm class as a method override;
it replaces (and remains signature-compatible with) the original
stage_ii_TV_selection().
"""

import random
from typing import Optional


# ──────────────────────────────────────────────────────────────────────────────
#  Directed initialization logic (standalone, testable)
# ──────────────────────────────────────────────────────────────────────────────

def directed_initial_population(
    n: int,
    circuit: dict,
    max_no_of_TV: int,
    test_size: Optional[int] = None,
) -> list[int]:
    """
    Generate a directed initial population for the first gate in *circuit*.

    Parameters
    ----------
    n            : number of input lines  (self.n)
    circuit      : the circuit dict — must contain "Gates" list
    max_no_of_TV : upper bound for random vector values  (self.max_no_of_TV)
    test_size    : target population size; defaults to n

    Returns
    -------
    list[int] : population of *test_size* integer-encoded test vectors,
                guaranteed unique where possible.

    Notes
    -----
    *  Line indices are 0-based integers matching the circuit description.
    *  A vector is encoded as an n-bit integer: bit (n-1-i) carries line i.
    *  The helper _pack / _unpack functions below handle the encoding.
    """
    if test_size is None:
        test_size = n

    # ── helper: bit array ↔ integer ──────────────────────────────────────────
    def pack(bits: list[int]) -> int:
        """bits[0] = MSB … bits[n-1] = LSB  →  integer."""
        val = 0
        for b in bits:
            val = (val << 1) | (b & 1)
        return val

    def unpack(v: int) -> list[int]:
        """integer → n-bit list, MSB first."""
        return [(v >> (n - 1 - i)) & 1 for i in range(n)]

    def random_vector() -> int:
        return random.randrange(0, max_no_of_TV)

    # ── extract first gate's controls and target ──────────────────────────────
    gates = circuit.get("Gates", [])
    controls: list[int] = []
    target: Optional[int] = None

    if gates:
        first_gate = gates[0]
        # Support both naming conventions seen in the codebase
        controls = first_gate.get("controls", first_gate.get("Controls", []))
        target   = first_gate.get("target",   first_gate.get("Target",   None))

    # ── degenerate case: no controls or no valid target ───────────────────────
    # (e.g. a plain NOT gate — fall back to original random init + boundary vecs)
    if not controls or target is None or target not in range(n):
        pop = _random_fill(test_size, n, max_no_of_TV)
        return _deduplicate_and_trim(pop, test_size, max_no_of_TV)

    # ─────────────────────────────────────────────────────────────────────────
    # v  = number of "interesting" bits  (|target| + |controls| = 1 + k)
    # ─────────────────────────────────────────────────────────────────────────
    k = len(controls)   # number of control bits
    # v = 1 + k          # paper notation: v = |target| + |controls|

    init_pop: list[int] = []
    m = 1               # 1-based vector counter (paper convention)

    # ── Vector 1 (paper line 17) ──────────────────────────────────────────────
    # target=0, all controls=1, remaining bits random  →  fault-activation vector
    bits = unpack(random_vector())          # random baseline
    bits_idx = _line_to_bit_index(n)       # maps line-id → bit position in MSB-first list
    bits[bits_idx(target)] = 0             # set target low
    for c in controls:
        bits[bits_idx(c)] = 1              # set all controls high
    init_pop.append(pack(bits))
    m += 1

    # ── Vectors 2 … 2^(k+1)−1 (paper lines 19-29) ───────────────────────────
    # target=1, sweep all control-bit combinations (var = 0 … 2^(k+1)-2)
    max_var = (1 << (k + 1)) - 1          # 2^(k+1) - 1  (exclusive upper bound in paper)
    for var in range(max_var - 1):        # j = 1 … 2^v - 2  (paper line 21)
        if m > n - 2:                     # budget guard (paper line 22)
            break

        bits = unpack(random_vector())     # random baseline for non-interesting lines
        bits[bits_idx(target)] = 1        # target=1

        # Assign k+1 bits of *var* to control lines
        # bit 0 of var → controls[0], bit 1 → controls[1], …
        for bit_pos, c in enumerate(controls):
            bits[bits_idx(c)] = (var >> bit_pos) & 1

        init_pop.append(pack(bits))
        m += 1

    # ── Random fill for remaining budget (paper lines 30-32) ─────────────────
    while m <= n - 2:
        init_pop.append(random_vector())
        m += 1

    # ── Boundary vectors (paper lines 33-35) ─────────────────────────────────
    all_ones  = (1 << n) - 1              # 111…1
    all_zeros = 0                         # 000…0
    init_pop.append(all_ones)
    init_pop.append(all_zeros)

    return _deduplicate_and_trim(init_pop, test_size, max_no_of_TV)


# ──────────────────────────────────────────────────────────────────────────────
#  Internal helpers
# ──────────────────────────────────────────────────────────────────────────────

def _line_to_bit_index(n: int):
    """
    Return a function that converts a 0-based line ID to its MSB-first bit
    position in an n-bit list.

    The encoding used throughout the GA is:
        bit position i  ←→  line id (n-1-i)
    so line 0 is the MSB (position 0) and line n-1 is the LSB.
    """
    def idx(line_id: int) -> int:
        return n - 1 - line_id
    return idx


def _random_fill(size: int, n: int, max_no_of_TV: int) -> list[int]:
    """Purely random population of *size* integers in [0, max_no_of_TV)."""
    if max_no_of_TV <= 2000:
        # For small circuits prefer unique sampling
        return random.sample(range(max_no_of_TV), min(size, max_no_of_TV))
    return [random.randrange(0, max_no_of_TV) for _ in range(size)]


def _deduplicate_and_trim(
    pop: list[int],
    target_size: int,
    max_no_of_TV: int,
) -> list[int]:
    """
    Remove duplicates from *pop* (preserving order), then pad with fresh
    random vectors if the result is shorter than *target_size*.
    """
    seen: set[int] = set()
    unique: list[int] = []
    for v in pop:
        if v not in seen:
            seen.add(v)
            unique.append(v)

    # Pad with random vectors until we reach target_size
    while len(unique) < target_size:
        v = random.randrange(0, max_no_of_TV)
        if v not in seen:
            seen.add(v)
            unique.append(v)

    return unique[:target_size]


# ──────────────────────────────────────────────────────────────────────────────
#  Monkey-patch helper
# ──────────────────────────────────────────────────────────────────────────────

def patch_ga_with_directed_init(ga_class):
    """
    Inject directed_stage_ii_TV_selection() into *ga_class* and override
    stage_ii_TV_selection so the GA automatically uses directed init.

    Usage
    -----
    from directed_init_patch import patch_ga_with_directed_init
    from genetic_algorithm import GeneticAlgorithm

    patch_ga_with_directed_init(GeneticAlgorithm)   # one-time, at import
    """

    def directed_stage_ii_TV_selection(self, test_size: Optional[int] = None):
        """
        Directed initial population generation (replaces random stage II).

        Generates vectors guaranteed to excite the first gate's target under
        all control-input combinations, then pads with random vectors and
        appends the two mandatory boundary vectors (all-ones, all-zeros).
        """
        if test_size is None:
            test_size = self.n

        pop = directed_initial_population(
            n            = self.n,
            circuit      = self.circuit,
            max_no_of_TV = self.max_no_of_TV,
            test_size    = test_size,
        )

        if self.verbose and not self.sparse_logging:
            print(f"[Directed Init] Generated {len(pop)} vectors "
                  f"(circuit: {self.circuit.get('Circuit Name', '?')}, "
                  f"n={self.n}, first-gate target / controls from gates[0])")

        return pop

    # Preserve original as a fallback
    ga_class._stage_ii_random = ga_class.stage_ii_TV_selection
    ga_class.stage_ii_TV_selection = directed_stage_ii_TV_selection
    return ga_class