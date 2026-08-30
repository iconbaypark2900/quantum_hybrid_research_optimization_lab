"""Oracle tests for QUBO/Ising conversion.

The failure this replaces was not a wrong answer. It was an *empty* one: the
old conversion returned `linear_terms: {}`, `quadratic_terms: {}` while logging
success and reporting `method: "automatic_conversion"`. Every circuit built
from it encoded no problem and still produced results.

So shape is exactly what must not be tested here. Two independent oracles are
used instead:

  - brute-force enumeration of every bitstring, which shares no code path with
    the conversion, and
  - `ClassicalMaxCutSolver`, whose MILP formulation is itself already verified
    against brute force in `test_baselines_oracle.py`.

If the QUBO agrees with both, on random graphs and on graphs whose answer is
known by hand, it encodes the problem.
"""
import itertools
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.optimization.canonical import (  # noqa: E402
    QUBO,
    maxcut_to_qubo,
    portfolio_to_qubo,
    default_portfolio_penalty,
)
from src.optimization.classical import ClassicalMaxCutSolver  # noqa: E402
from src.optimization.problems import (  # noqa: E402
    MaxCutProblem,
    PortfolioProblem,
    create_sample_maxcut,
    create_sample_portfolio,
)


def all_bitstrings(n):
    return itertools.product([0, 1], repeat=n)


def brute_force_maxcut(problem: MaxCutProblem) -> float:
    """The oracle: obviously correct, and independent of the conversion."""
    return max(
        sum(w for (i, j), w in zip(problem.edges, problem.weights)
            if bits[i] != bits[j])
        for bits in all_bitstrings(problem.n_nodes)
    )


# --- the QUBO must encode the problem, not merely have the right shape -----

@pytest.mark.parametrize("n_nodes", [4, 5, 6, 7, 8])
def test_qubo_minimum_is_the_maxcut_optimum(n_nodes):
    """min energy over every assignment == -(max cut), by enumeration."""
    problem = create_sample_maxcut(n_nodes=n_nodes, edge_prob=0.6)
    qubo = maxcut_to_qubo(problem)

    best = min(qubo.energy(bits) for bits in all_bitstrings(qubo.n_variables))
    assert -best == pytest.approx(brute_force_maxcut(problem))


@pytest.mark.parametrize("n_nodes", [4, 5, 6, 7, 8])
def test_qubo_agrees_with_the_verified_milp_solver(n_nodes):
    """The second oracle, and one that is itself pinned to brute force."""
    problem = create_sample_maxcut(n_nodes=n_nodes, edge_prob=0.6)
    qubo = maxcut_to_qubo(problem)

    best = min(qubo.energy(bits) for bits in all_bitstrings(qubo.n_variables))
    milp = ClassicalMaxCutSolver().solve(problem)
    assert milp["status"] == "optimal", milp
    assert -best == pytest.approx(milp["cut_value"])


@pytest.mark.parametrize("n_nodes", [4, 5, 6, 7, 8])
def test_every_assignment_agrees_edge_for_edge(n_nodes):
    """Not just the optimum: the QUBO must value *every* assignment correctly.

    A conversion can land the right minimum while mis-scoring the interior,
    which would leave a sampled expectation value wrong even when the argmin
    is right.
    """
    problem = create_sample_maxcut(n_nodes=n_nodes, edge_prob=0.6)
    qubo = maxcut_to_qubo(problem)

    for bits in all_bitstrings(qubo.n_variables):
        direct = sum(w for (i, j), w in zip(problem.edges, problem.weights)
                     if bits[i] != bits[j])
        assert qubo.cut_value(bits) == pytest.approx(direct)


# --- graphs whose answer is known by hand ----------------------------------

def test_four_cycle_cuts_every_edge():
    """A 4-cycle is bipartite, so the alternating partition cuts all four."""
    qubo = maxcut_to_qubo(MaxCutProblem(edges=[(0, 1), (1, 2), (2, 3), (3, 0)]))
    best = min(qubo.energy(b) for b in all_bitstrings(4))
    assert -best == pytest.approx(4.0)
    assert qubo.cut_value([0, 1, 0, 1]) == pytest.approx(4.0)


def test_triangle_cannot_cut_every_edge():
    """An odd cycle is not bipartite: at most two of three edges are cut."""
    qubo = maxcut_to_qubo(MaxCutProblem(edges=[(0, 1), (1, 2), (2, 0)]))
    best = min(qubo.energy(b) for b in all_bitstrings(3))
    assert -best == pytest.approx(2.0)


def test_weights_are_carried_not_ignored():
    """A uniform conversion would pass the unweighted cases above."""
    qubo = maxcut_to_qubo(
        MaxCutProblem(edges=[(0, 1), (1, 2)], weights=[5.0, 1.0]))
    assert qubo.cut_value([0, 1, 0]) == pytest.approx(6.0)
    assert qubo.cut_value([0, 1, 1]) == pytest.approx(5.0)
    assert qubo.cut_value([0, 0, 1]) == pytest.approx(1.0)


# --- the specific historical failure ---------------------------------------

@pytest.mark.parametrize("n_nodes", [4, 6, 8])
def test_conversion_is_not_empty(n_nodes):
    """The old conversion returned {} and reported success. Test for it by name."""
    problem = create_sample_maxcut(n_nodes=n_nodes, edge_prob=0.6)
    qubo = maxcut_to_qubo(problem)

    assert len(qubo.quadratic) == len(problem.edges)
    assert len(qubo.linear) > 0
    assert all(c != 0.0 for c in qubo.quadratic.values())


def test_a_graph_with_edges_cannot_convert_to_nothing():
    """Belt and braces: constructing an empty QUBO for a real graph must raise."""
    with pytest.raises(ValueError, match="no quadratic terms|self-loop"):
        maxcut_to_qubo(MaxCutProblem(edges=[(0, 0)]))


def test_quadratic_keys_are_ordered_so_pairs_cannot_double_count():
    with pytest.raises(ValueError, match="i<j"):
        QUBO(linear={}, quadratic={(2, 1): 1.0}, offset=0.0, n_variables=3)


# --- Ising must be the same objective, not a second implementation ---------

@pytest.mark.parametrize("n_nodes", [4, 5, 6])
def test_ising_energy_matches_qubo_energy_under_s_equals_1_minus_2x(n_nodes):
    """s = 1 - 2x. If the two forms disagree anywhere, they have drifted."""
    problem = create_sample_maxcut(n_nodes=n_nodes, edge_prob=0.6)
    qubo = maxcut_to_qubo(problem)
    ising = qubo.to_ising()

    for bits in all_bitstrings(qubo.n_variables):
        spins = [1 - 2 * b for b in bits]
        assert ising.energy(spins) == pytest.approx(qubo.energy(bits))


# --- portfolio ------------------------------------------------------------

@pytest.mark.parametrize("budget", [1, 2, 3])
def test_portfolio_penalty_actually_enforces_the_budget(budget):
    """The only claim made for the default penalty, checked by enumeration.

    A penalty too small does not fail loudly -- it silently returns a portfolio
    of the wrong size that still looks like an answer.
    """
    problem = create_sample_portfolio(n_assets=6, seed=7)
    qubo = portfolio_to_qubo(problem, budget=budget)

    best_bits = min(all_bitstrings(qubo.n_variables), key=qubo.energy)
    assert sum(best_bits) == budget


def test_portfolio_selects_the_better_of_two_obvious_assets():
    """With no covariance, higher return must win at budget 1."""
    problem = PortfolioProblem(
        returns=np.array([0.01, 0.50]),
        covariances=np.eye(2) * 1e-9,
    )
    qubo = portfolio_to_qubo(problem, budget=1, risk_aversion=1.0)
    best = min(all_bitstrings(2), key=qubo.energy)
    assert best == (0, 1)


def test_portfolio_rejects_an_impossible_budget():
    problem = create_sample_portfolio(n_assets=4, seed=1)
    with pytest.raises(ValueError, match="budget"):
        portfolio_to_qubo(problem, budget=9)


def test_default_penalty_is_derived_from_the_instance_not_constant():
    """A constant would be a magic number wearing a function's name."""
    small = PortfolioProblem(returns=np.array([0.1, 0.1]),
                             covariances=np.eye(2) * 0.01)
    large = PortfolioProblem(returns=np.array([10.0, 10.0]),
                             covariances=np.eye(2) * 100.0)
    assert (default_portfolio_penalty(large, 1.0)
            > default_portfolio_penalty(small, 1.0))
