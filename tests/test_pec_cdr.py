"""PEC and CDR, via Mitiq.

Both were `NotImplementedError` with the note that hand-writing them would
repeat the mistake SCAFFOLDING.md records about the ZNE maths: the spec named
Mitiq, it was hand-written anyway, and had to be verified against Mitiq
afterwards. So these are Mitiq's implementations.

**CDR works. PEC does not improve accuracy here, and these tests say so.**

That distinction is the point of this file. It would have been easy to assert
`error_after < error_before` for both, discover PEC fails it, and tune
`num_samples` until it passed on one seed. The measurements below are what was
actually found, and the PEC test asserts the mechanism rather than an
improvement that is not there.
"""
import asyncio
import statistics
import sys
from pathlib import Path

import pytest
from qiskit import QuantumCircuit

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.error_mitigation_service.service import ErrorMitigationService  # noqa: E402

NOISE = 0.05
SHOTS = 2048


def bell():
    """Analytic parity <ZZ> = +1, the same fixture the ZNE tests use."""
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    return qc


def mitigate(technique, **kw):
    svc = ErrorMitigationService()
    out = asyncio.run(svc.apply_mitigation(
        {}, technique, circuit=bell(), noise_level=NOISE, shots=SHOTS, **kw))
    assert out.get("status") != "failed", out
    return out["mitigated_results"]


# --- CDR: works, and is asserted to work ----------------------------------

def test_cdr_moves_the_estimate_toward_the_true_value():
    r = mitigate("cdr")
    assert abs(r["average_objective_value"] - 1.0) < abs(r["unmitigated_value"] - 1.0)


def test_cdr_reports_which_library_produced_the_number():
    r = mitigate("cdr")
    assert r["cdr"]["library"] == "mitiq.cdr.execute_with_cdr"
    assert r["mitigation_applied"] == "cdr"
    assert r["cdr"]["num_training_circuits"] == 10


# --- PEC: implemented, and measured not to help ---------------------------

def test_pec_runs_and_reports_its_provenance():
    r = mitigate("pec", num_samples=50)
    assert r["pec"]["library"] == "mitiq.pec.execute_with_pec"
    assert r["pec"]["noise_model"] == "local depolarising"
    assert r["pec"]["num_representations"] > 0
    assert r["mitigation_applied"] == "pec"


def test_pec_variance_shrinks_with_samples_but_the_bias_does_not():
    """The measurement that stops PEC being reported as working.

    PEC's estimator is unbiased only when its representations match the channel
    actually applied. Here they do not: Mitiq applies one epsilon to both one-
    and two-qubit operations, while Qiskit's `depolarizing_error(p, n)` uses a
    different convention for each -- (1-p)rho + p I/2 corresponds to Mitiq's
    epsilon = 3p/4 on one qubit and 15p/16 on two, and no single scalar matches
    both.

    Measured on a Bell state at 5% noise, over 6 random states:

        num_samples=50    mean +1.082   sd 0.083
        num_samples=200   mean +1.061   sd 0.020
        num_samples=500   mean +1.083   sd 0.014
        unmitigated       ~0.953        (error 0.047)

    The spread collapses; the bias does not move. So PEC here is *less*
    accurate than doing nothing, and the honest assertion is about the
    variance, not the accuracy.
    """
    def spread(num_samples):
        vals = [mitigate("pec", num_samples=num_samples, random_state=s)
                ["average_objective_value"] for s in range(4)]
        return statistics.pstdev(vals)

    assert spread(200) < spread(25)


def test_pec_does_not_claim_to_be_mitigated_more_accurately_than_it_is():
    """A guard against someone later asserting the improvement that is absent.

    If PEC is ever corrected so it does beat unmitigated on this fixture, this
    test fails and should be replaced by the improvement assertion CDR has.
    That is the intended way to find out that it started working.
    """
    r = mitigate("pec", num_samples=200, random_state=0)
    mitigated_err = abs(r["average_objective_value"] - 1.0)
    unmitigated_err = abs(r["unmitigated_value"] - 1.0)
    assert mitigated_err > unmitigated_err, (
        "PEC now beats unmitigated on this fixture -- good. Replace this test "
        "with the improvement assertion used for CDR, and update SCAFFOLDING.md.")


# --- both refuse rather than guess ----------------------------------------

@pytest.mark.parametrize("technique", ["pec", "cdr"])
def test_a_missing_circuit_is_refused(technique):
    svc = ErrorMitigationService()
    out = asyncio.run(svc.apply_mitigation({}, technique))
    assert out["status"] == "failed"
    assert "circuit" in str(out.get("error", "")).lower()
