"""The comparison must report only what was measured.

Two values in `compute_optimality_gaps` were invented, and both sat on the
headline number of the project:

  - the quantum objective was read with `.get('objective_value', 0.0)`, a
    silent default for a key nothing produced;
  - the confidence interval was the literal `[gap - 0.05, gap + 0.05]`,
    commented `# Simulated CI`.

A confidence interval is the archetypal number a reader takes as a
measurement: it is an explicit quantitative claim about uncertainty. A
constant one is not weak evidence, it is no evidence wearing the costume.
"""
import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.hybrid_baseline_service.service import HybridBaselineService  # noqa: E402


def gaps(quantum, classical):
    return asyncio.run(HybridBaselineService().compute_optimality_gaps(
        quantum, classical))


CLASSICAL = [{"algorithm": "milp", "result": {"objective_value": 10.0}}]


def test_a_missing_quantum_objective_is_refused_not_defaulted():
    """The exact historical failure: a gap computed against 0.0."""
    with pytest.raises(ValueError, match="objective_value"):
        gaps({"shots": 1024}, CLASSICAL)


def test_no_classical_baseline_is_refused():
    with pytest.raises(ValueError, match="nothing to compare"):
        gaps({"objective_value": 8.0}, [{"algorithm": "milp"}])


def test_gap_is_computed_not_asserted():
    out = gaps({"objective_value": 8.0}, CLASSICAL)
    assert out["absolute_gap"] == pytest.approx(-2.0)
    assert out["relative_gap"] == pytest.approx(-0.2)
    assert out["performance_assessment"] == "classical_higher"


def test_there_is_no_constant_interval():
    """Without a measured standard error, no interval is offered at all."""
    out = gaps({"objective_value": 8.0}, CLASSICAL)
    assert "confidence_interval" not in out
    assert "relative_gap_interval_1se" not in out
    assert "not quantified" in out["uncertainty"]


def test_interval_appears_only_when_the_error_was_measured():
    out = gaps({"objective_value": 8.0, "standard_error": 0.5}, CLASSICAL)
    lo, hi = out["relative_gap_interval_1se"]
    assert lo == pytest.approx(-0.2 - 0.05)
    assert hi == pytest.approx(-0.2 + 0.05)
    assert out["quantum_standard_error"] == pytest.approx(0.5)


def test_interval_width_tracks_the_measured_error():
    """The property a constant cannot have."""
    tight = gaps({"objective_value": 8.0, "standard_error": 0.1}, CLASSICAL)
    loose = gaps({"objective_value": 8.0, "standard_error": 1.0}, CLASSICAL)

    def width(o):
        lo, hi = o["relative_gap_interval_1se"]
        return hi - lo

    assert width(loose) == pytest.approx(10 * width(tight))
    # And neither is the retired constant.
    assert width(tight) != pytest.approx(0.1)


def test_significance_is_never_asserted():
    """It said "Significant quantum advantage" from one unseeded run."""
    for obj in (8.0, 10.0, 12.0, 25.0):
        out = gaps({"objective_value": obj}, CLASSICAL)
        text = out["interpretation"].lower()
        assert "significant" not in text.replace("not a significance test", "")
        assert "advantage" not in text
        assert "significance test" in text or "significance" in text


def test_interpretation_states_the_number_it_is_describing():
    out = gaps({"objective_value": 12.0}, CLASSICAL)
    assert "20.00%" in out["interpretation"]
    assert "higher" in out["interpretation"]


def test_provenance_is_carried_into_the_comparison():
    out = gaps({"objective_value": 8.0, "shots": 2048,
                "provenance": {"seed": 3}}, CLASSICAL)
    assert out["shots"] == 2048
    assert out["provenance"] == {"seed": 3}
    assert out["baselines_compared"] == 1


def test_best_classical_is_the_best_not_the_first():
    classical = [
        {"algorithm": "greedy", "result": {"objective_value": 7.0}},
        {"algorithm": "milp", "result": {"objective_value": 10.0}},
    ]
    out = gaps({"objective_value": 8.0}, classical)
    assert out["best_classical_objective"] == pytest.approx(10.0)
    assert out["baselines_compared"] == 2
