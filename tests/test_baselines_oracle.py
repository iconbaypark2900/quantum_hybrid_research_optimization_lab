"""Oracle tests for the classical baselines.

An oracle is an answer obtained INDEPENDENTLY of the code under test. For
Max-Cut on a small graph, brute-force enumeration is one: it is obviously
correct, and it does not share any code path with the MILP formulation.

This matters because of what these tests replace. `ClassicalMaxCutSolver` had
never solved anything — its objective was bilinear, cvxpy rejected the problem
as non-DCP, the solver caught the exception and returned `status: 'error'`, and
the existing 22 tests passed throughout, because they assert on shape and status
rather than on a cut being found. Shape tests cannot tell a working solver from
a broken one; an oracle can.

The same lesson, from the financial lab: a deflated-Sharpe implementation wrong
in six places passed 23 invariant checks, and only the paper's published worked
example caught it. Invariants are necessary and not sufficient. Pin a value
someone else computed.
"""
import asyncio
import itertools
import sys
import time
from pathlib import Path

import pytest

# These drive the event loop with asyncio.run rather than pytest.mark.asyncio:
# pytest-asyncio is not installed, and an unregistered marker makes async tests
# silently not run — they report as failures for the wrong reason, or worse,
# pass vacuously in configurations that ignore the coroutine.

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.optimization.classical import ClassicalMaxCutSolver  # noqa: E402
from src.optimization.problems import MaxCutProblem, create_sample_maxcut  # noqa: E402


def brute_force_maxcut(problem: MaxCutProblem) -> float:
    """Exhaustive enumeration — the oracle. Exponential, hence small n only."""
    return max(
        sum(w for (i, j), w in zip(problem.edges, problem.weights) if bits[i] != bits[j])
        for bits in itertools.product([0, 1], repeat=problem.n_nodes)
    )


def cut_value(partition, edges, weights) -> float:
    return float(sum(w for (i, j), w in zip(edges, weights)
                     if partition[i] != partition[j]))


# --- the solver must actually find the optimum -----------------------------

@pytest.mark.parametrize("n_nodes", [4, 5, 6, 7, 8])
def test_exact_solver_matches_brute_force(n_nodes):
    problem = create_sample_maxcut(n_nodes=n_nodes, edge_prob=0.6)
    result = ClassicalMaxCutSolver().solve(problem)
    assert result["status"] == "optimal", result
    assert result["cut_value"] == pytest.approx(brute_force_maxcut(problem))


@pytest.mark.parametrize("n_nodes", [4, 6, 8])
def test_partition_achieves_the_reported_cut(n_nodes):
    """A reported objective the returned partition does not achieve means the
    formulation has drifted from the problem — the failure mode a pure value
    check would miss."""
    problem = create_sample_maxcut(n_nodes=n_nodes, edge_prob=0.6)
    result = ClassicalMaxCutSolver().solve(problem)
    achieved = cut_value(result["partition"], problem.edges, problem.weights)
    assert achieved == pytest.approx(result["cut_value"])


def test_known_graph_by_hand():
    """A 4-cycle with unit weights. Every edge can be cut by alternating around
    the cycle, so the optimum is 4 — computable without any solver at all."""
    problem = MaxCutProblem(edges=[(0, 1), (1, 2), (2, 3), (3, 0)])
    result = ClassicalMaxCutSolver().solve(problem)
    assert result["cut_value"] == pytest.approx(4.0)


def test_triangle_cannot_cut_every_edge():
    """An odd cycle is not bipartite: one edge must stay inside a part. The
    optimum for a unit triangle is 2, not 3 — a case where a solver that
    ignored the constraints would report the wrong, higher number."""
    problem = MaxCutProblem(edges=[(0, 1), (1, 2), (2, 0)])
    result = ClassicalMaxCutSolver().solve(problem)
    assert result["cut_value"] == pytest.approx(2.0)


def test_negative_weights_are_refused_not_silently_relaxed():
    """The linearisation is exact only while the objective pushes y_ij up. With
    a negative weight the bound stops pinning the XOR and the solver would
    report a cut its partition does not achieve."""
    problem = MaxCutProblem(edges=[(0, 1), (1, 2)], weights=[1.0, -2.0])
    with pytest.raises(ValueError, match="non-negative"):
        ClassicalMaxCutSolver().solve(problem)


# --- the service layer must report measurements, not inventions ------------

def test_exact_baseline_is_optimal_and_heuristic_never_beats_it():
    """Ordering invariant, needing no oracle: a heuristic cannot exceed the
    optimum. If it ever does, one of the two is not solving this problem."""
    from src.hybrid_baseline_service.service import HybridBaselineService

    problem = create_sample_maxcut(n_nodes=8, edge_prob=0.6)
    spec = {"problem_id": "t", "edges": [list(e) for e in problem.edges],
            "weights": problem.weights}
    svc = HybridBaselineService()

    exact = asyncio.run(svc.run_baseline(spec, "milp"))["result"]
    heur = asyncio.run(svc.run_baseline(spec, "heuristics"))["result"]

    assert exact["objective_value"] == pytest.approx(brute_force_maxcut(problem))
    assert heur["objective_value"] <= exact["objective_value"] + 1e-9
    assert exact["optimality_gap"] == 0.0


def test_runtime_is_measured_not_generated():
    """Runtime used to be np.random.uniform(0.5, 30.0). A measured duration is
    non-negative and reproducibly small on a graph this size; a sampled one
    would land in [0.5, 30] and vary wildly between identical runs."""
    from src.hybrid_baseline_service.service import HybridBaselineService

    problem = create_sample_maxcut(n_nodes=6, edge_prob=0.6)
    spec = {"problem_id": "t", "edges": [list(e) for e in problem.edges],
            "weights": problem.weights}
    svc = HybridBaselineService()

    r1 = asyncio.run(svc.run_baseline(spec, "heuristics"))["result"]
    r2 = asyncio.run(svc.run_baseline(spec, "heuristics"))["result"]
    assert r1["runtime_seconds"] >= 0
    assert r1["runtime_seconds"] < 5.0
    # Same input, same answer: the objective is deterministic even though the
    # search starts from a seeded random point.
    assert r1["objective_value"] == pytest.approx(r2["objective_value"])


def test_problem_without_a_graph_is_refused():
    """A dict carrying only `n_variables` does not define an objective.
    Accepting it is what let the old baselines score against a substitute."""
    from src.hybrid_baseline_service.service import HybridBaselineService

    with pytest.raises(ValueError, match="edges"):
        asyncio.run(HybridBaselineService().run_baseline(
            {"problem_id": "x", "n_variables": 10}, "milp"))


def test_unimplemented_baselines_raise_rather_than_fabricate():
    from src.hybrid_baseline_service.service import HybridBaselineService

    svc = HybridBaselineService()
    spec = {"problem_id": "t", "edges": [[0, 1], [1, 2]]}
    for algorithm in ("metaheuristics", "machine_learning"):
        with pytest.raises(NotImplementedError):
            asyncio.run(svc.run_baseline(spec, algorithm))
