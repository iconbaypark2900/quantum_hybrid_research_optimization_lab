"""Zero-noise extrapolation: oracle and invariant tests.

The oracle here is mathematics rather than a paper's worked example: Richardson
extrapolation through k points is *exactly* the degree-(k-1) interpolating
polynomial evaluated at zero. So for any polynomial we choose, we know the
answer independently of the implementation, and can demand it to machine
precision.

That is the property the previous implementation could not have had. It reshaped
one distribution and reported a "zne_improvement" of a fixed 5% of the input,
with no amplified run to extrapolate from — a number that could not be checked
against anything, because it was not derived from anything.
"""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.error_mitigation_service.zne import (  # noqa: E402
    extrapolate_to_zero_noise,
    fold_gates,
    linear_extrapolate,
    richardson_extrapolate,
)


# --- oracle: exactness on polynomials --------------------------------------

def test_richardson_is_exact_on_a_linear_function():
    """E(l) = 3 - 0.5l  =>  E(0) = 3, exactly."""
    lam = [1.0, 2.0]
    assert richardson_extrapolate(lam, [3 - 0.5 * l for l in lam]) == pytest.approx(3.0)


def test_richardson_is_exact_on_a_quadratic_with_three_points():
    """E(l) = 2 + 0.3l - 0.05l^2  =>  E(0) = 2, exactly, with three points."""
    lam = [1.0, 2.0, 3.0]
    vals = [2 + 0.3 * l - 0.05 * l ** 2 for l in lam]
    assert richardson_extrapolate(lam, vals) == pytest.approx(2.0, abs=1e-12)


def test_richardson_is_exact_on_a_cubic_with_four_points():
    lam = [1.0, 2.0, 3.0, 4.0]
    vals = [-1.5 + 0.4 * l - 0.07 * l ** 2 + 0.01 * l ** 3 for l in lam]
    assert richardson_extrapolate(lam, vals) == pytest.approx(-1.5, abs=1e-10)


def test_richardson_underfits_a_higher_degree_than_it_has_points_for():
    """Honesty check: two points cannot capture curvature, so the estimate is
    wrong — and should be, since ZNE's polynomial assumption is an assumption.
    A method that appeared exact here would be hiding its own limits."""
    lam = [1.0, 2.0]
    vals = [2 + 0.3 * l - 0.5 * l ** 2 for l in lam]
    assert richardson_extrapolate(lam, vals) != pytest.approx(2.0, abs=1e-6)


def test_linear_extrapolate_recovers_the_intercept():
    lam = [1.0, 2.0, 3.0, 4.0]
    assert linear_extrapolate(lam, [5 - 1.25 * l for l in lam]) == pytest.approx(5.0)


def test_linear_is_more_robust_than_richardson_under_shot_noise():
    """With noisy points, Richardson passes exactly through every one and so
    amplifies the noise; least squares averages it. This is the reason both
    exist, and it is measured rather than asserted."""
    rng = np.random.default_rng(0)
    lam = [1.0, 2.0, 3.0, 4.0, 5.0]
    truth = 1.0
    rich_err, lin_err = [], []
    for _ in range(200):
        vals = [truth - 0.1 * l + rng.normal(0, 0.02) for l in lam]
        rich_err.append(abs(richardson_extrapolate(lam, vals) - truth))
        lin_err.append(abs(linear_extrapolate(lam, vals) - truth))
    assert np.mean(lin_err) < np.mean(rich_err)


# --- the mitigation must actually move toward the truth --------------------

def test_extrapolation_beats_the_unmitigated_value():
    """The point of the exercise. On a decaying signal the lambda=1 measurement
    is biased away from the truth, and the extrapolation must land closer."""
    truth = 1.0
    lam = [1.0, 2.0, 3.0]
    vals = [truth * np.exp(-0.15 * l) for l in lam]
    out = extrapolate_to_zero_noise(lam, vals, method="richardson")
    assert abs(out["zero_noise_estimate"] - truth) < abs(out["unmitigated_value"] - truth)


def test_result_carries_its_inputs_and_states_its_assumption():
    """A mitigated number without its inputs cannot be checked. The previous
    implementation returned exactly that."""
    out = extrapolate_to_zero_noise([1.0, 2.0, 3.0], [0.9, 0.8, 0.7])
    assert out["measured_values"] == [0.9, 0.8, 0.7]
    assert out["scale_factors"] == [1.0, 2.0, 3.0]
    assert "polynomial" in out["assumption"]
    assert out["correction"] == pytest.approx(
        out["zero_noise_estimate"] - out["unmitigated_value"])


def test_noiseless_input_is_left_alone():
    """If the expectation value does not vary with noise there is nothing to
    correct, and mitigation must be the identity rather than an 'improvement'.
    The previous version applied a fixed 5% regardless."""
    out = extrapolate_to_zero_noise([1.0, 2.0, 3.0], [0.42, 0.42, 0.42])
    assert out["zero_noise_estimate"] == pytest.approx(0.42)
    assert out["correction"] == pytest.approx(0.0, abs=1e-12)


# --- refusals --------------------------------------------------------------

def test_a_single_point_is_refused():
    """One measurement is not an extrapolation. Accepting it is what let the
    old code call a reshaped distribution 'ZNE'."""
    with pytest.raises(ValueError, match="two noise levels"):
        richardson_extrapolate([1.0], [0.5])


def test_duplicate_scale_factors_are_refused():
    with pytest.raises(ValueError, match="distinct"):
        richardson_extrapolate([1.0, 1.0], [0.5, 0.6])


# --- unitary folding -------------------------------------------------------

def test_folding_scales_the_gate_count_by_the_factor():
    gates = ["h", "cx", "rz"]
    for factor in (1, 3, 5, 7):
        assert len(fold_gates(gates, factor)) == factor * len(gates)


def test_folding_by_one_is_the_identity():
    gates = ["h", "cx"]
    assert fold_gates(gates, 1) == [("h", False), ("cx", False)]


def test_folded_circuit_has_balanced_inverses():
    """G (G^dag G)^n leaves the ideal unitary unchanged only if every inverse is
    matched by a forward copy. Count them."""
    gates = ["a", "b", "c"]
    folded = fold_gates(gates, 5)
    forward = sum(1 for _, inv in folded if not inv)
    inverse = sum(1 for _, inv in folded if inv)
    assert forward - inverse == len(gates)   # the original pass, unpaired


def test_even_scale_factors_are_refused():
    """An even factor would leave the circuit inverted rather than equivalent —
    a silent correctness bug rather than a missing feature."""
    with pytest.raises(ValueError, match="odd"):
        fold_gates(["h"], 2)
