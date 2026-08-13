"""End-to-end ZNE: fold a real circuit, execute it under noise, extrapolate.

The oracle is analytic. A Bell state has parity <ZZ> = +1 exactly, so the
mitigated estimate can be checked against a number nobody had to compute with
this code.

THE TEST THAT MATTERS MOST is `test_folding_actually_amplifies_noise`. When this
loop was first wired it produced a confident, plausible, completely empty
result: the qiskit transpiler's default optimisation level cancels adjacent
inverse gate pairs, which is precisely what unitary folding inserts. A Bell
circuit folded to lambda = 1, 3, 5, 7 transpiled to 5 operations and depth 3 in
EVERY case. Folding did nothing, the noise was never amplified, and ZNE
"extrapolated" three measurements of the same circuit — reporting a mitigated
value derived from no information at all.

Nothing in the extrapolation maths could catch that. The values were
self-consistent, in range, and the fit was exact. Only the physical invariant
catches it: a circuit with more noisy operations must measure worse. So that
invariant is asserted here, and it is why `optimization_level=0` is a
correctness requirement rather than a tuning choice.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

pytest.importorskip("qiskit_aer")
pytest.importorskip("mitiq")

import asyncio  # noqa: E402

from qiskit import QuantumCircuit, transpile  # noqa: E402
from qiskit_aer import AerSimulator  # noqa: E402

from src.error_mitigation_service.service import ErrorMitigationService  # noqa: E402
from src.execution_orchestrator_service.service import (  # noqa: E402
    ExecutionOrchestratorService,
)


def bell() -> QuantumCircuit:
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    return qc


# --- execution against analytic truth --------------------------------------

def test_noiseless_bell_state_matches_analytic_probabilities():
    """|00> and |11> at 1/2 each, nothing else. A simulator that disagrees is
    not simulating."""
    result = asyncio.run(ExecutionOrchestratorService().execute_circuit(
        "bell", shots=20000, circuit=bell()))["result"]
    probs = result["probabilities"]
    assert probs.get("00", 0) == pytest.approx(0.5, abs=0.02)
    assert probs.get("11", 0) == pytest.approx(0.5, abs=0.02)
    assert probs.get("01", 0) + probs.get("10", 0) < 0.01


def test_noise_introduces_the_forbidden_outcomes():
    """|01> and |10> have zero amplitude in a Bell state, so their appearance
    is a direct measure that the noise model is active."""
    result = asyncio.run(ExecutionOrchestratorService().execute_circuit(
        "bell", shots=20000, circuit=bell(), noise_level=0.05))["result"]
    probs = result["probabilities"]
    assert probs.get("01", 0) + probs.get("10", 0) > 0.01


def test_execution_time_is_measured():
    result = asyncio.run(ExecutionOrchestratorService().execute_circuit(
        "bell", shots=1000, circuit=bell()))["result"]
    assert 0 < result["execution_time"] < 30


def test_missing_circuit_is_refused_not_downgraded():
    """A circuit_id alone is not enough, and the error must reach the caller
    rather than becoming a soft {'status': 'failed'} dict."""
    with pytest.raises(ValueError, match="circuit"):
        asyncio.run(ExecutionOrchestratorService().execute_circuit("nope", shots=10))


# --- the invariant that caught the empty loop ------------------------------

@pytest.mark.parametrize("scale_factor", [3, 5, 7])
def test_folding_survives_transpilation(scale_factor):
    """Regression: the transpiler must not cancel the folded pairs.

    With default optimisation every scale factor collapsed to the unfolded
    circuit, silently reducing ZNE to noise on the same measurement.
    """
    from mitiq.zne.scaling import fold_global

    folded = fold_global(bell(), scale_factor=float(scale_factor))
    work = folded.copy()
    work.measure_all()
    compiled = transpile(work, AerSimulator(), optimization_level=0)

    baseline = transpile(bell().copy(), AerSimulator(), optimization_level=0)
    assert compiled.depth() > baseline.depth() * 1.5, (
        f"lambda={scale_factor} transpiled to depth {compiled.depth()}, barely "
        f"above the unfolded depth {baseline.depth()} — folding was optimised away")


def test_folding_actually_amplifies_noise():
    """The physical invariant. More noisy operations must measure worse.

    This is the check that no amount of extrapolation maths can supply: the
    fitted values were perfectly self-consistent while measuring nothing.
    """
    svc = ErrorMitigationService()
    measured = asyncio.run(svc._measure_at_scale_factors(
        bell(), scale_factors=(1, 3, 5), noise_level=0.04, shots=16384))

    values = [measured[float(k)] for k in (1, 3, 5)]
    assert values[0] > values[1] > values[2], (
        f"<ZZ> must degrade as noise is amplified, got {values}. Equal values "
        "mean the folding is not reaching the simulator.")


# --- the whole loop --------------------------------------------------------

def test_zne_recovers_the_noiseless_expectation_value():
    """Bell parity is +1 analytically. Mitigation must land closer to it than
    the raw noisy measurement — measured at ~40x on this circuit."""
    out = asyncio.run(ErrorMitigationService().apply_mitigation(
        {}, technique="zne", circuit=bell(),
        scale_factors=(1, 3, 5), noise_level=0.03, shots=32768))
    z = out["mitigated_results"]["zne"]

    raw_error = abs(z["unmitigated_value"] - 1.0)
    zne_error = abs(z["zero_noise_estimate"] - 1.0)
    assert zne_error < raw_error
    assert z["zero_noise_estimate"] == pytest.approx(1.0, abs=0.02)


def test_even_scale_factors_are_refused_end_to_end():
    """An even factor leaves the circuit inverted rather than equivalent."""
    with pytest.raises(ValueError, match="even"):
        asyncio.run(ErrorMitigationService()._measure_at_scale_factors(
            bell(), scale_factors=(1, 2), noise_level=0.01, shots=100))
