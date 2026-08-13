"""Zero-noise extrapolation: noise scaling and extrapolation to the zero-noise limit.

ZNE estimates what a circuit would have returned on a noiseless device, without
having one. It has exactly two halves, and the previous implementation had
neither:

  1. NOISE SCALING — run the same logical circuit at deliberately AMPLIFIED
     noise levels lambda = 1, 2, 3, ... Unitary folding does this without any
     device-level control: replacing G with G (G^dag G)^n leaves the ideal
     unitary unchanged while tripling, quintupling, ... the number of noisy
     operations. `fold_gates` below implements it.

  2. EXTRAPOLATION — fit the observed expectation values E(lambda) as a function
     of lambda and evaluate the fit at lambda = 0. `richardson_extrapolate` and
     `linear_extrapolate` below.

What was here before did neither. It reshaped a single distribution by boosting
above-average probabilities 15% and suppressing the rest, then reported a
`zne_improvement` that was a fixed 5% of the input objective — a number
independent of the measurement data entirely. No amplified run ever happened, so
there was nothing to extrapolate from.

Sources:
  Temme, Bravyi & Gambetta (2017), "Error mitigation for short-depth quantum
    circuits", Phys. Rev. Lett. 119, 180509 — quasi-probability and the
    zero-noise extrapolation idea.
  Li & Benjamin (2017), "Efficient variational quantum simulator incorporating
    active error minimization", Phys. Rev. X 7, 021050 — extrapolation to the
    zero-noise limit.
  Giurgica-Tiron et al. (2020), "Digital zero noise extrapolation for quantum
    error mitigation", arXiv:2005.10921 — unitary folding as digital noise
    scaling, which is the method used here.

The extrapolators are exact on polynomials of the appropriate degree, and the
tests pin that: Richardson with k points recovers the constant term of any
degree-(k-1) polynomial exactly. That is an oracle — a value derived from the
mathematics rather than from this code.
"""
from __future__ import annotations

from typing import Sequence

import numpy as np


def fold_gates(gates: Sequence, scale_factor: int) -> list:
    """Amplify noise by unitary folding: G -> G (G^dag G)^n.

    `gates` is any sequence of gate identifiers; each element must carry enough
    information for the caller to invert it. This returns the folded SEQUENCE —
    inversion is the caller's job, because what "inverse" means depends on the
    circuit representation, and guessing would be the same mistake as inventing
    an objective function.

    The identity `(G^dag G) = I` means the ideal circuit is unchanged while the
    number of noisy operations grows by the odd factor `scale_factor`, which is
    exactly what makes the extrapolation meaningful.

    Args:
        gates: the circuit's gate sequence.
        scale_factor: an ODD integer >= 1. Folding produces 2n+1 copies, so only
            odd factors are reachable; an even one would leave the circuit
            inverted rather than equivalent.

    Returns:
        A list of (gate, inverted) tuples of length `scale_factor * len(gates)`.
    """
    if not isinstance(scale_factor, (int, np.integer)) or isinstance(scale_factor, bool):
        raise TypeError(f"scale_factor must be an int, got {type(scale_factor).__name__}")
    if scale_factor < 1 or scale_factor % 2 == 0:
        raise ValueError(
            f"scale_factor must be an odd integer >= 1 (got {scale_factor}). "
            "Folding appends inverse/forward PAIRS, so only 1, 3, 5, ... leave "
            "the ideal unitary unchanged; an even factor would leave the "
            "circuit inverted.")

    folded = [(g, False) for g in gates]
    for _ in range((scale_factor - 1) // 2):
        folded += [(g, True) for g in reversed(gates)]   # G^dag
        folded += [(g, False) for g in gates]            # G
    return folded


def richardson_extrapolate(scale_factors: Sequence[float],
                           values: Sequence[float]) -> float:
    """Extrapolate E(lambda) to lambda = 0 by exact polynomial interpolation.

    With k points, this fits the unique degree-(k-1) polynomial through them and
    evaluates it at zero. It is therefore EXACT whenever the true noise
    dependence is polynomial of degree < k — which is the assumption ZNE rests
    on, and the reason the result is an estimate rather than a measurement.

    Implemented as the Lagrange basis evaluated at 0, which is the closed form
    of Richardson extrapolation and avoids building an ill-conditioned
    Vandermonde system.
    """
    lam = np.asarray(scale_factors, dtype=float)
    vals = np.asarray(values, dtype=float)
    if lam.shape != vals.shape:
        raise ValueError(f"got {lam.size} scale factors and {vals.size} values")
    if lam.size < 2:
        raise ValueError(
            "extrapolation needs at least two noise levels; with one point "
            "there is nothing to extrapolate FROM, which is precisely what the "
            "previous implementation pretended to do")
    if len(set(lam.tolist())) != lam.size:
        raise ValueError(f"scale factors must be distinct, got {lam.tolist()}")
    if np.any(lam <= 0):
        raise ValueError("scale factors must be positive (lambda = 1 is the "
                         "unamplified circuit)")

    # Lagrange basis at x = 0: prod_{m != k} (0 - lam_m) / (lam_k - lam_m)
    total = 0.0
    for k in range(lam.size):
        others = np.delete(lam, k)
        total += vals[k] * np.prod(-others / (lam[k] - others))
    return float(total)


def linear_extrapolate(scale_factors: Sequence[float],
                       values: Sequence[float]) -> float:
    """Least-squares linear fit evaluated at lambda = 0.

    More robust than Richardson when the values carry shot noise: Richardson
    passes exactly through every point, so it amplifies sampling error, while a
    least-squares line averages it. Prefer this with many noisy points, and
    Richardson with few clean ones.
    """
    lam = np.asarray(scale_factors, dtype=float)
    vals = np.asarray(values, dtype=float)
    if lam.size < 2:
        raise ValueError("linear extrapolation needs at least two noise levels")
    if len(set(lam.tolist())) != lam.size:
        raise ValueError(f"scale factors must be distinct, got {lam.tolist()}")
    slope, intercept = np.polyfit(lam, vals, 1)
    return float(intercept)


def extrapolate_to_zero_noise(scale_factors: Sequence[float],
                              values: Sequence[float],
                              method: str = "richardson") -> dict:
    """Estimate the zero-noise expectation value from amplified-noise runs.

    Returns the estimate together with what it was derived from, because a
    mitigated number without its inputs cannot be checked — and an unverifiable
    "mitigated" value is what this module exists to stop producing.
    """
    methods = {"richardson": richardson_extrapolate, "linear": linear_extrapolate}
    if method not in methods:
        raise ValueError(f"unknown method {method!r}; available: {sorted(methods)}")

    estimate = methods[method](scale_factors, values)
    lam = list(map(float, scale_factors))
    vals = list(map(float, values))
    unmitigated = vals[lam.index(min(lam))]
    return {
        "zero_noise_estimate": estimate,
        "unmitigated_value": unmitigated,
        "correction": estimate - unmitigated,
        "scale_factors": lam,
        "measured_values": vals,
        "method": method,
        # Stated, not implied: this is an extrapolation under a polynomial-decay
        # assumption, not a measurement of a noiseless device.
        "assumption": (f"expectation value is polynomial in the noise scale "
                       f"factor to degree {len(lam) - 1}"),
    }
