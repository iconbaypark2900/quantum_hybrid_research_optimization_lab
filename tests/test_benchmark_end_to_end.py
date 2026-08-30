"""The benchmark driver must produce real numbers on both sides.

It replaces a demo that printed "Phase 1 Implementation Complete" and seven
active services while two of its three pipelines were raising, and that
invented the classical side in a loop with a hardcoded objective_value of 0.65.
"""
import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import benchmark  # noqa: E402
from src.optimization.classical import ClassicalMaxCutSolver  # noqa: E402
from src.optimization.problems import create_sample_maxcut  # noqa: E402


@pytest.fixture(scope="module")
def report():
    return asyncio.run(benchmark.run(n_nodes=5, edge_prob=0.6, seed=42,
                                     depth=1, shots=256, noise_level=0.02,
                                     max_iter=5))


def test_classical_side_is_the_verified_exact_optimum(report):
    """Not a placeholder: it must equal what the exact solver independently finds."""
    problem = create_sample_maxcut(n_nodes=5, edge_prob=0.6, seed=42)
    exact = ClassicalMaxCutSolver().solve(problem)
    assert exact["status"] == "optimal"
    assert report["classical"]["exact_milp"]["objective_value"] == pytest.approx(
        exact["cut_value"])


def test_both_classical_baselines_actually_ran(report):
    """The old loop logged "Running classical algorithm" and ran nothing."""
    for name in ("exact_milp", "greedy"):
        entry = report["classical"][name]
        assert entry["runtime_seconds"] > 0.0
    assert (report["classical"]["greedy"]["objective_value"]
            <= report["classical"]["exact_milp"]["objective_value"] + 1e-9)


def test_quantum_side_reports_shots_and_seed(report):
    q = report["quantum"]
    assert q["shots"] == 256
    assert q["provenance"]["seed"] == 42
    assert q["provenance"]["depth"] == 1
    assert q["standard_error"] > 0.0


def test_quantum_expectation_is_not_the_best_sample(report):
    """Reporting the max over shots as the objective would flatter the method."""
    q = report["quantum"]
    assert q["objective_value"] <= q["best_sampled_value"] + 1e-9


def test_zne_uses_the_cost_observable_not_parity(report):
    """Parity lives in [-1, 1]; a cut value on this graph does not."""
    zne = report["zne"]
    assert set(zne["noisy_expectation_at_each_factor"]) == {1.0, 3.0, 5.0}
    assert max(zne["noisy_expectation_at_each_factor"].values()) > 1.0


def test_comparison_carries_measured_uncertainty(report):
    c = report["comparison"]
    assert "confidence_interval" not in c
    assert c["quantum_standard_error"] == pytest.approx(
        report["quantum"]["standard_error"])
    lo, hi = c["relative_gap_interval_1se"]
    assert hi > lo


def test_nothing_in_the_report_is_a_placeholder(report):
    """The retired demo's tell-tale values."""
    flat = str(report)
    for tell in ("0.65", "classical_solution_placeholder", "mocked", "mock_"):
        assert tell not in flat, tell
