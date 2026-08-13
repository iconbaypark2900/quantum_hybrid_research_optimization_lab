"""Cross-check zne.py against Mitiq, the reference implementation.

WHY THIS FILE EXISTS

`src/error_mitigation_service/zne.py` was hand-written. The PRD says otherwise:
"Mitiq plugged into the execution path (ZNE, PEC, CDR) when enabled". Writing
the maths by hand when the spec names a library is the same mistake, in miniature,
as the deflated-Sharpe implementation inventing a formula the spec told it to take
from a published paper — and that one was wrong in six places while passing 23
invariant checks.

So this file supplies what the maths tests cannot: an INDEPENDENT implementation
to disagree with. `test_zne.py` proves the extrapolators are self-consistent and
exact on polynomials; only Mitiq can show they compute what everyone else means
by "Richardson extrapolation" and "unitary folding".

Result of the first run: agreement to machine precision (worst 2.66e-15 on
Richardson, exactly 0.0 on linear), and folded gate counts identical at every
scale factor tested.

Mitiq remains the right tool for PEC and CDR, which are still unimplemented here
— it provides both, and there is no reason to hand-write those too.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

mitiq = pytest.importorskip("mitiq", reason="Mitiq is the oracle; without it "
                                            "this file cannot check anything")
cirq = pytest.importorskip("cirq")

from mitiq.zne.inference import LinearFactory, RichardsonFactory  # noqa: E402
from mitiq.zne.scaling import fold_global  # noqa: E402

from src.error_mitigation_service.zne import (  # noqa: E402
    fold_gates,
    linear_extrapolate,
    richardson_extrapolate,
)

# (label, scale factors, E(lambda))
CASES = [
    ("linear", [1.0, 2.0], lambda l: 3 - 0.5 * l),
    ("quadratic", [1.0, 2.0, 3.0], lambda l: 2 + 0.3 * l - 0.05 * l ** 2),
    ("cubic", [1.0, 2.0, 3.0, 4.0], lambda l: -1.5 + .4 * l - .07 * l ** 2 + .01 * l ** 3),
    ("exponential decay", [1.0, 2.0, 3.0], lambda l: 2.718281828 ** (-0.15 * l)),
    ("wide spacing", [1.0, 3.0, 5.0], lambda l: 0.9 - 0.08 * l + 0.004 * l ** 2),
]


def mitiq_reduce(factory_cls, scale_factors, values) -> float:
    factory = factory_cls(scale_factors=scale_factors)
    for scale, value in zip(scale_factors, values):
        factory.push({"scale_factor": scale}, value)
    return factory.reduce()


@pytest.mark.parametrize("label,scale_factors,fn", CASES, ids=[c[0] for c in CASES])
def test_richardson_agrees_with_mitiq(label, scale_factors, fn):
    values = [fn(l) for l in scale_factors]
    assert richardson_extrapolate(scale_factors, values) == pytest.approx(
        mitiq_reduce(RichardsonFactory, scale_factors, values), abs=1e-9)


@pytest.mark.parametrize("label,scale_factors,fn", CASES, ids=[c[0] for c in CASES])
def test_linear_agrees_with_mitiq(label, scale_factors, fn):
    values = [fn(l) for l in scale_factors]
    assert linear_extrapolate(scale_factors, values) == pytest.approx(
        mitiq_reduce(LinearFactory, scale_factors, values), abs=1e-9)


def _sample_circuit():
    q = cirq.LineQubit.range(3)
    return cirq.Circuit([cirq.H(q[0]), cirq.CNOT(q[0], q[1]), cirq.CNOT(q[1], q[2]),
                         cirq.rz(0.3)(q[2]), cirq.H(q[1])])


@pytest.mark.parametrize("scale_factor", [1, 3, 5, 7])
def test_folding_multiplies_operation_count_like_mitiq(scale_factor):
    """Both must produce exactly scale_factor x the original operations."""
    circuit = _sample_circuit()
    n_ops = len(list(circuit.all_operations()))
    mitiq_ops = len(list(fold_global(circuit, scale_factor=float(scale_factor))
                         .all_operations()))
    mine_ops = len(fold_gates([f"g{i}" for i in range(n_ops)], scale_factor))
    assert mine_ops == mitiq_ops == scale_factor * n_ops


@pytest.mark.parametrize("scale_factor", [3, 5])
def test_folding_preserves_the_ideal_unitary(scale_factor):
    """The whole premise of unitary folding: G (G^dag G)^n leaves the noiseless
    circuit unchanged while multiplying the noisy operations. If this failed,
    ZNE would be extrapolating a different circuit than the one asked about."""
    import numpy as np

    circuit = _sample_circuit()
    original = circuit.unitary()
    folded = fold_global(circuit, scale_factor=float(scale_factor)).unitary()
    # Equal up to global phase.
    overlap = abs(np.vdot(original.ravel(), folded.ravel())) / (
        np.linalg.norm(original) * np.linalg.norm(folded))
    assert overlap == pytest.approx(1.0, abs=1e-9)


def test_end_to_end_agreement_on_a_decaying_signal():
    """The realistic case: mitigate an exponentially damped expectation value
    and require both routes to land on the same estimate."""
    scale_factors = [1.0, 2.0, 3.0]
    truth = 1.0
    values = [truth * 2.718281828 ** (-0.2 * l) for l in scale_factors]

    mine = richardson_extrapolate(scale_factors, values)
    theirs = mitiq_reduce(RichardsonFactory, scale_factors, values)

    assert mine == pytest.approx(theirs, abs=1e-9)
    # And both must actually improve on the unmitigated value.
    assert abs(mine - truth) < abs(values[0] - truth)
