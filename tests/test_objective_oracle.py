"""Oracle tests for reducing counts to an objective value.

The gap this fills: nothing produced `objective_value`, and the comparison read
it with a default of 0.0. A gap computed against a default argument is not a
weak result, it is an unfalsifiable one.

The oracles here are hand-computed distributions. A counts dict is small enough
to work out on paper, so no sampling is needed to know the right answer.
"""
import sys
from pathlib import Path

import pytest
from qiskit import QuantumCircuit, transpile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.optimization.canonical import maxcut_to_qubo  # noqa: E402
from src.optimization.objective import (  # noqa: E402
    best_sampled_cut,
    bits_from_counts_key,
    cut_observable,
    expectation_cut,
    objective_from_counts,
    standard_error_of_cut,
)
from src.optimization.problems import MaxCutProblem  # noqa: E402
from src.optimization.qaoa import QAOA  # noqa: E402

FOUR_CYCLE = MaxCutProblem(edges=[(0, 1), (1, 2), (2, 3), (3, 0)])
QUBO4 = maxcut_to_qubo(FOUR_CYCLE)

# '0101' is little-endian, so it decodes to qubit-indexed (1, 0, 1, 0):
# the alternating partition, which cuts all four edges.
ALTERNATING_KEY = "0101"
ALL_ZERO_KEY = "0000"


def test_the_key_that_the_oracles_below_depend_on():
    """Pin the decoding these hand-computed expectations assume."""
    assert bits_from_counts_key(ALTERNATING_KEY, 4) == (1, 0, 1, 0)
    assert QUBO4.cut_value((1, 0, 1, 0)) == pytest.approx(4.0)
    assert QUBO4.cut_value((0, 0, 0, 0)) == pytest.approx(0.0)


def test_expectation_is_the_shot_weighted_mean():
    """Half at cut 4 and half at cut 0 is a mean of 2, by hand."""
    counts = {ALTERNATING_KEY: 50, ALL_ZERO_KEY: 50}
    assert expectation_cut(counts, QUBO4) == pytest.approx(2.0)


def test_expectation_weights_by_shots_not_by_distinct_outcomes():
    """A conversion that averaged over keys would give 2.0 here too -- so the
    weights are deliberately lopsided."""
    counts = {ALTERNATING_KEY: 90, ALL_ZERO_KEY: 10}
    assert expectation_cut(counts, QUBO4) == pytest.approx(3.6)


def test_a_single_outcome_has_no_sampling_error():
    counts = {ALTERNATING_KEY: 1000}
    assert expectation_cut(counts, QUBO4) == pytest.approx(4.0)
    assert standard_error_of_cut(counts, QUBO4) == pytest.approx(0.0)


def test_standard_error_shrinks_as_one_over_root_shots():
    """The property that distinguishes a real standard error from a constant.

    The replaced value was a literal +/- 0.05 that never moved.
    """
    small = {ALTERNATING_KEY: 50, ALL_ZERO_KEY: 50}
    large = {ALTERNATING_KEY: 5000, ALL_ZERO_KEY: 5000}
    ratio = standard_error_of_cut(small, QUBO4) / standard_error_of_cut(large, QUBO4)
    assert ratio == pytest.approx(10.0, rel=1e-9)   # sqrt(10000/100)


def test_standard_error_matches_the_hand_computed_value():
    """Two equally likely outcomes at 4 and 0: sd = 2, se = 2/sqrt(N)."""
    counts = {ALTERNATING_KEY: 50, ALL_ZERO_KEY: 50}
    assert standard_error_of_cut(counts, QUBO4) == pytest.approx(2.0 / 10.0)


def test_best_sampled_is_reported_but_is_not_the_objective():
    counts = {ALTERNATING_KEY: 1, ALL_ZERO_KEY: 999}
    out = objective_from_counts(counts, QUBO4)
    assert out["best_sampled_value"] == pytest.approx(4.0)
    assert out["objective_value"] == pytest.approx(4.0 / 1000)
    assert out["objective_value"] != out["best_sampled_value"]


def test_best_sample_flatters_a_circuit_that_encodes_nothing():
    """Why the best sample is never the headline number.

    A Hadamard-only circuit knows nothing about the graph. Its best sample
    still climbs to the true optimum as shots increase, purely because uniform
    sampling eventually hits it -- while its expectation stays at the uniform
    average and does not move.
    """
    q = QAOA(shots=4096)
    qc = QuantumCircuit(4)
    qc.h(range(4))
    qc.measure_all()

    few = q.backend.run(transpile(qc, q.backend), shots=8).result().get_counts()
    many = q.backend.run(transpile(qc, q.backend), shots=4096).result().get_counts()

    assert best_sampled_cut(many, QUBO4)[1] == pytest.approx(4.0)
    assert best_sampled_cut(many, QUBO4)[1] >= best_sampled_cut(few, QUBO4)[1]
    # The expectation is not fooled: uniform over 16 states averages to 2.0.
    assert expectation_cut(many, QUBO4) == pytest.approx(2.0, abs=0.25)


def test_empty_distribution_is_refused_not_scored_as_zero():
    with pytest.raises(ValueError, match="empty distribution"):
        expectation_cut({}, QUBO4)


def test_provenance_is_carried_verbatim():
    out = objective_from_counts({ALTERNATING_KEY: 10}, QUBO4,
                                seed=7, depth=2, backend="aer")
    assert out["provenance"] == {"seed": 7, "depth": 2, "backend": "aer"}
    assert out["shots"] == 10


# --- the observable handed to the mitigation path -------------------------

def test_cut_observable_scores_bitstrings_as_the_qubo_does():
    """The mitigation path defaults to bitstring parity, which is meaningless
    for Max-Cut. This is what replaces it."""
    obs = cut_observable(QUBO4)
    assert obs(ALTERNATING_KEY) == pytest.approx(4.0)
    assert obs(ALL_ZERO_KEY) == pytest.approx(0.0)


def test_cut_observable_is_not_parity():
    """'0011' has even weight, so parity would call it +1; its cut is 2."""
    obs = cut_observable(QUBO4)
    assert obs("0011") == pytest.approx(2.0)
