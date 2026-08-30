"""Oracle tests for the portfolio QAOA path -- the last untested code in src/.

It was wrong in four ways at once, and every one of them was invisible from
the result object:

  - the cost layer read only `problem.covariances` and never
    `problem.returns`, so expected return -- half the objective -- was absent
    from the circuit;
  - it looped over ordered pairs `(i, j)` and `(j, i)`, applying every
    coupling twice;
  - it emitted a bare `rz` carrying the *pair* coefficient before each CX,
    adding a single-qubit term proportional to the covariance row sum that
    appears in no formulation of the problem;
  - there was no budget constraint at all.

Meanwhile `solve_portfolio` scored its samples by a Sharpe ratio. The circuit
and the scorer were optimising different functions, and the returned dict --
allocation, final_cost, convergence -- looked exactly as it would have if they
agreed.

Both now come from `portfolio_to_qubo`, so they are the same objective by
construction. The oracle is brute-force enumeration, which shares no code path
with the circuit.
"""
import itertools
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.optimization.canonical import portfolio_to_qubo  # noqa: E402
from src.optimization.problems import PortfolioProblem, create_sample_portfolio  # noqa: E402
from src.optimization.qaoa import QAOA  # noqa: E402


def rz_angles(qc, gamma=0.7, beta=0.3):
    """The rz rotation angles, with the parameters bound to fixed values.

    Comparing `str(instruction.operation.params)` on an *unbound* circuit
    compares ParameterExpression object reprs, which carry a memory address:
    the comparison is meaningless and passes or fails depending on allocation.
    That is what the first version of these tests did -- it passed in isolation
    and failed in the full suite. Binding first compares the coefficients the
    circuit actually encodes.
    """
    bound = qc.assign_parameters(
        {prm: (gamma if prm.name.startswith("γ") else beta)
         for prm in qc.parameters})
    return [round(float(inst.operation.params[0]), 12)
            for inst in bound.data if inst.operation.name == "rz"]


def brute_force_best(problem, budget, **kw):
    qubo = portfolio_to_qubo(problem, budget=budget, **kw)
    return min(itertools.product([0, 1], repeat=problem.n_assets),
               key=qubo.energy)


# --- the objective must reach the circuit ---------------------------------

def test_expected_returns_reach_the_circuit():
    """The headline bug: returns were never read by the cost layer.

    Two problems identical except for their returns must produce different
    circuits. Under the old implementation they were byte-identical.
    """
    cov = np.eye(3) * 0.05
    low = PortfolioProblem(returns=np.array([0.01, 0.02, 0.03]), covariances=cov)
    high = PortfolioProblem(returns=np.array([0.90, 0.02, 0.03]), covariances=cov)

    q = QAOA()
    a = q.create_portfolio_circuit(low, p=1, budget=1)
    b = q.create_portfolio_circuit(high, p=1, budget=1)

    assert rz_angles(a) != rz_angles(b), "returns do not affect the circuit"


def test_covariance_reaches_the_circuit():
    ret = np.array([0.1, 0.1, 0.1])
    a = QAOA().create_portfolio_circuit(
        PortfolioProblem(returns=ret, covariances=np.eye(3) * 0.05), p=1, budget=1)
    b = QAOA().create_portfolio_circuit(
        PortfolioProblem(returns=ret,
                         covariances=np.array([[0.05, 0.04, 0.0],
                                               [0.04, 0.05, 0.0],
                                               [0.0, 0.0, 0.05]])), p=1, budget=1)
    assert rz_angles(a) != rz_angles(b)


@pytest.mark.parametrize("n_assets,depth", [(4, 1), (4, 2), (5, 1)])
def test_each_pair_is_coupled_once_not_twice(n_assets, depth):
    """The ordered-pair loop applied every coupling twice.

    n(n-1)/2 ZZ blocks per layer, each two CX, plus n single-qubit Z terms.
    """
    problem = create_sample_portfolio(n_assets=n_assets, seed=7)
    qc = QAOA().create_portfolio_circuit(problem, p=depth, budget=2)
    pairs = n_assets * (n_assets - 1) // 2
    ops = qc.count_ops()

    assert qc.num_qubits == n_assets
    assert ops["cx"] == 2 * pairs * depth
    assert ops["rz"] == (pairs + n_assets) * depth
    assert ops["rx"] == n_assets * depth
    assert len(qc.parameters) == 2 * depth


def test_budget_is_required():
    """Binary selection without a budget is not the problem being solved."""
    problem = create_sample_portfolio(n_assets=4, seed=7)
    with pytest.raises(ValueError, match="budget is required"):
        QAOA().create_portfolio_circuit(problem, p=1)


def test_budget_changes_the_circuit():
    """The penalty term is part of the Hamiltonian, not a post-filter."""
    problem = create_sample_portfolio(n_assets=4, seed=7)
    q = QAOA()
    assert (rz_angles(q.create_portfolio_circuit(problem, p=1, budget=1))
            != rz_angles(q.create_portfolio_circuit(problem, p=1, budget=3)))


# --- end to end, against brute force --------------------------------------

@pytest.mark.parametrize("budget", [1, 2, 3])
def test_qaoa_finds_the_brute_force_selection(budget):
    problem = create_sample_portfolio(n_assets=5, seed=7)
    expected = brute_force_best(problem, budget)

    result = QAOA(shots=1024).solve_portfolio(problem, p=1, budget=budget,
                                              max_iter=25)
    assert tuple(int(v) for v in result["allocation"]) == expected


@pytest.mark.parametrize("budget", [1, 2, 3])
def test_the_selection_respects_the_budget(budget):
    problem = create_sample_portfolio(n_assets=5, seed=7)
    result = QAOA(shots=1024).solve_portfolio(problem, p=1, budget=budget,
                                              max_iter=25)
    assert len(result["selected_assets"]) == budget
    assert sum(int(v) for v in result["allocation"]) == budget


def test_reported_energy_matches_the_allocation_it_reports():
    """Circuit and scorer used to optimise different functions."""
    problem = create_sample_portfolio(n_assets=5, seed=7)
    qubo = portfolio_to_qubo(problem, budget=2)
    result = QAOA(shots=1024).solve_portfolio(problem, p=1, budget=2,
                                              max_iter=25)
    recomputed = qubo.energy([int(v) for v in result["allocation"]])
    assert result["objective_energy"] == pytest.approx(recomputed)


def test_higher_return_asset_is_preferred_when_risk_is_equal():
    """A hand-solvable instance: equal risk, one clearly better return."""
    problem = PortfolioProblem(
        returns=np.array([0.01, 0.90, 0.02]),
        covariances=np.eye(3) * 1e-9,
    )
    result = QAOA(shots=1024).solve_portfolio(problem, p=1, budget=1,
                                              risk_aversion=1.0, max_iter=25)
    assert result["selected_assets"] == [1]
