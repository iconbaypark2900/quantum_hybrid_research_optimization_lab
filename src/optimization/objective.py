"""Reduce measured bitstring counts to an objective value.

This was the missing link. `compute_optimality_gaps` read the quantum number as

    quantum_obj = quantum_result.get('objective_value', 0.0)

and nothing in the repository produced that key. The execution orchestrator
returns counts, probabilities, shot and qubit counts, circuit depth and timing;
the mitigation path returns a noise-extrapolated Bell parity. Neither is an
objective value for the problem being solved, so any comparison scored a real
MILP optimum against a default argument.

WHICH NUMBER IS "THE" OBJECTIVE
-------------------------------
Two are computed here, and the distinction matters more than it looks:

`expectation_value` -- the shot-weighted mean of the cost over the measured
distribution. This is the standard QAOA figure of merit and the honest one: it
is a property of the state the circuit prepares.

`best_sampled_value` -- the best single outcome observed. It flatters the
method, because it is a maximum over shots: it improves with more shots even
for a circuit that encodes nothing, since enough uniform sampling eventually
hits the optimum of a small instance. `tests/test_objective_oracle.py`
demonstrates exactly that on a Hadamard-only circuit.

So `objective_value` is the expectation. The best sample is reported beside it,
named for what it is, and never as the headline.
"""

from typing import Callable, Dict, Mapping, Sequence, Tuple

from .canonical import QUBO

__all__ = [
    "bits_from_counts_key",
    "cut_observable",
    "expectation_cut",
    "standard_error_of_cut",
    "best_sampled_cut",
    "objective_from_counts",
]


def bits_from_counts_key(key: str, num_qubits: int) -> Tuple[int, ...]:
    """Decode one Qiskit counts key into bits indexed by qubit.

    Qiskit writes the key most-significant-qubit first, so it is reversed here.

    Refuses a key spanning more than one classical register rather than
    concatenating them. That is not hypothetical: the QAOA circuits declared a
    register *and* called measure_all(), which adds a second, and the resulting
    "1000 0000" was silently decoded from the register that was never written.
    Every outcome came back all-zeros. See SCAFFOLDING.md.
    """
    stripped = key.strip()
    if " " in stripped:
        raise ValueError(
            f"counts key {key!r} spans more than one classical register. "
            "Build the circuit with a single register (measure_all() adds one) "
            "-- concatenating them here silently reads the wrong bits.")
    if len(stripped) < num_qubits:
        stripped = stripped.zfill(num_qubits)
    if len(stripped) != num_qubits:
        raise ValueError(
            f"counts key {key!r} has {len(stripped)} bits, expected {num_qubits}")
    return tuple(1 if ch == "1" else 0 for ch in reversed(stripped))


def cut_observable(qubo: QUBO) -> Callable[[str], float]:
    """A bitstring -> cut-value function, for the ZNE measurement path.

    `_measure_at_scale_factors` takes an `observable` of exactly this shape.
    Its default is the parity of the bitstring, which is right for the
    Bell-state validation and meaningless for an optimisation problem -- so
    passing this is what points the mitigation machinery at the actual cost
    Hamiltonian.
    """
    def observable(bitstring: str) -> float:
        return qubo.cut_value(bits_from_counts_key(bitstring, qubo.n_variables))
    return observable


def _validated_counts(counts: Mapping[str, int]) -> Dict[str, int]:
    if not counts:
        raise ValueError(
            "no measurement outcomes: an objective value cannot be computed "
            "from an empty distribution, and returning 0.0 would be indis"
            "tinguishable from a genuine result")
    if any(c < 0 for c in counts.values()):
        raise ValueError("negative shot count")
    if sum(counts.values()) <= 0:
        raise ValueError("counts sum to zero")
    return dict(counts)


def expectation_cut(counts: Mapping[str, int], qubo: QUBO) -> float:
    """Shot-weighted mean cut value over the measured distribution."""
    counts = _validated_counts(counts)
    total = sum(counts.values())
    return sum(
        n * qubo.cut_value(bits_from_counts_key(key, qubo.n_variables))
        for key, n in counts.items()
    ) / total


def standard_error_of_cut(counts: Mapping[str, int], qubo: QUBO) -> float:
    """Standard error of the sampled expectation: sqrt(sample variance / shots).

    This is a real uncertainty, computed from the distribution that was
    actually measured, and it shrinks as 1/sqrt(shots) the way a sampled mean
    must. It replaces a literal `[gap - 0.05, gap + 0.05]` that was commented
    `# Simulated CI` -- a fixed width with no variance, no bootstrap and no
    shot noise behind it, attached to the headline number of the project.

    It quantifies sampling error only. It says nothing about whether the
    circuit prepares a good state, and nothing about hardware noise.
    """
    counts = _validated_counts(counts)
    shots = sum(counts.values())
    mean = expectation_cut(counts, qubo)
    var = sum(
        n * (qubo.cut_value(bits_from_counts_key(key, qubo.n_variables)) - mean) ** 2
        for key, n in counts.items()
    ) / shots
    return (var / shots) ** 0.5


def best_sampled_cut(counts: Mapping[str, int],
                     qubo: QUBO) -> Tuple[Tuple[int, ...], float]:
    """Best single outcome observed, and the bits that achieved it.

    A maximum over shots. See the module docstring for why this is reported
    but not used as the headline number.
    """
    counts = _validated_counts(counts)
    best_bits, best_val = None, float("-inf")
    for key in counts:
        bits = bits_from_counts_key(key, qubo.n_variables)
        val = qubo.cut_value(bits)
        if val > best_val:
            best_bits, best_val = bits, val
    return best_bits, best_val


def objective_from_counts(counts: Mapping[str, int], qubo: QUBO,
                          **provenance) -> Dict[str, object]:
    """Everything a caller needs to read the number and to check it.

    `objective_value` is the expectation, so it is comparable with the
    classical baselines, which report a cut value (a maximisation).

    Extra keyword arguments are recorded verbatim under `provenance`: seed,
    depth, backend, noise model, mitigation. A sampled expectation value
    without its shot count is not a measurement anyone can check.
    """
    counts = _validated_counts(counts)
    best_bits, best_val = best_sampled_cut(counts, qubo)
    shots = sum(counts.values())
    return {
        "objective_value": expectation_cut(counts, qubo),
        "standard_error": standard_error_of_cut(counts, qubo),
        "best_sampled_value": best_val,
        "best_sampled_bits": list(best_bits),
        "shots": shots,
        "distinct_outcomes": len(counts),
        "provenance": dict(provenance),
    }
