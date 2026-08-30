"""The environment is a dependency, and it has failed silently before.

Every other test here assumes qiskit, cvxpy and mitiq behave. On the wrong
interpreter one of them does not, and it does not say so: pip cannot build any
real mitiq release on Python 3.12+, so it falls back to `mitiq 0.0.0`, a
placeholder that installs cleanly, imports, and reports a version. It contains
three modules and no `mitiq.zne`.

The result was six failures in `test_zne_vs_mitiq.py` and
`test_zne_end_to_end.py` reading `ModuleNotFoundError: No module named
'mitiq.zne'` -- which looks like broken code. It is a broken environment, and
these tests say so in one line instead.
"""
import sys

import pytest


SUPPORTED = ((3, 10), (3, 12))  # >= 3.10, < 3.12


def test_interpreter_is_in_the_supported_range():
    """Below 3.10 is untested; 3.12 and above cannot install mitiq."""
    lo, hi = SUPPORTED
    assert lo <= sys.version_info[:2] < hi, (
        f"Python {sys.version_info.major}.{sys.version_info.minor} is not supported. "
        f"This project requires >={lo[0]}.{lo[1]},<{hi[0]}.{hi[1]} -- see pyproject.toml. "
        "On 3.12+ mitiq cannot be installed and pip substitutes a placeholder that "
        "has no mitiq.zne, so the extrapolation tests fail for reasons that have "
        "nothing to do with this code."
    )


def test_mitiq_is_not_the_placeholder_release():
    """`mitiq 0.0.0` imports and reports a version. That is the whole problem."""
    mitiq = pytest.importorskip("mitiq")
    assert mitiq.__version__ != "0.0.0", (
        "mitiq resolved to the 0.0.0 placeholder release, which has no zne "
        "submodule. This means pip could not build a real release on this "
        "interpreter -- reinstall on Python 3.10 or 3.11."
    )


def test_mitiq_provides_the_symbols_the_cross_check_needs():
    """The ZNE tests verify hand-written maths against these three.

    Without them the comparison is not weaker, it is absent -- and the failure
    surfaces as a collection error rather than as a missing oracle.
    """
    from mitiq.zne.inference import LinearFactory, RichardsonFactory
    from mitiq.zne.scaling import fold_global

    assert callable(fold_global)
    assert RichardsonFactory is not None and LinearFactory is not None


def test_ply_is_installed_for_mitiqs_qasm_conversion():
    """Not pulled in automatically, and it fails at point of use, not install.

    Mitiq's Qiskit<->Cirq conversion imports cirq.contrib.qasm_import, which
    needs ply. Without it `fold_global` raises ModuleNotFoundError in the middle
    of a test rather than at install time.
    """
    pytest.importorskip("ply")
