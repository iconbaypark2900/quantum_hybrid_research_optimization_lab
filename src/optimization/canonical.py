"""Canonical forms: QUBO and Ising.

Nothing in this repository converted a problem to canonical form until this
module existed. What preceded it was worse than nothing: it returned
`linear_terms: {}`, `quadratic_terms: {}` while logging success and reporting
`method: "automatic_conversion"`. An empty QUBO does not crash. Every circuit
built from one encodes no problem, optimises nothing, and still returns
results -- plausible ones, in range, with no way for a caller to tell.

That is why `to_qubo` refuses to emit an objective with no quadratic terms, and
why `tests/test_canonical_form_oracle.py` checks the term count by name.

SIGN CONVENTION
---------------
Everything here is a **minimisation**. `QUBO.energy(bits)` is a value to be made
small, for every problem type, with no per-problem exceptions.

Max-Cut is naturally a maximisation, so it is negated on the way in:

    cut(x)    =  sum_ij w_ij (x_i + x_j - 2 x_i x_j)
    energy(x) = -cut(x)

so `max_cut == -min_energy`, and `QUBO.cut_value(bits)` exists to spare callers
from getting that minus sign wrong. A sign error here would be invisible
downstream -- it reads as a poor optimisation result, not as a bug.
"""

from dataclasses import dataclass, field
from typing import Dict, Iterable, Sequence, Tuple

import numpy as np

from .problems import MaxCutProblem, PortfolioProblem

__all__ = ["QUBO", "Ising", "maxcut_to_qubo", "portfolio_to_qubo"]

Pair = Tuple[int, int]


@dataclass(frozen=True)
class Ising:
    """Ising form over spins s_i in {-1, +1}.

    energy(s) = sum_i h_i s_i + sum_{i<j} J_ij s_i s_j + offset
    """

    h: Dict[int, float]
    J: Dict[Pair, float]
    offset: float
    n_variables: int

    def energy(self, spins: Sequence[float]) -> float:
        if len(spins) != self.n_variables:
            raise ValueError(
                f"expected {self.n_variables} spins, got {len(spins)}")
        if any(s not in (-1, 1) for s in spins):
            raise ValueError("spins must be -1 or +1")
        e = self.offset
        e += sum(coeff * spins[i] for i, coeff in self.h.items())
        e += sum(coeff * spins[i] * spins[j] for (i, j), coeff in self.J.items())
        return float(e)


@dataclass(frozen=True)
class QUBO:
    """Quadratic unconstrained binary optimisation, as a MINIMISATION.

    energy(x) = sum_i linear_i x_i + sum_{i<j} quadratic_ij x_i x_j + offset
    """

    linear: Dict[int, float]
    quadratic: Dict[Pair, float]
    offset: float
    n_variables: int
    sense: str = field(default="minimise")

    def __post_init__(self):
        if self.sense != "minimise":
            raise ValueError(
                "QUBO is a minimisation by construction; negate on the way in "
                "rather than carrying a sense flag downstream")
        for (i, j) in self.quadratic:
            if i >= j:
                raise ValueError(
                    f"quadratic keys must be ordered pairs i<j, got ({i}, {j}) "
                    "-- otherwise (i,j) and (j,i) silently double-count")

    def energy(self, bits: Sequence[int]) -> float:
        """The value to minimise."""
        if len(bits) != self.n_variables:
            raise ValueError(
                f"expected {self.n_variables} bits, got {len(bits)}")
        if any(b not in (0, 1) for b in bits):
            raise ValueError("bits must be 0 or 1")
        e = self.offset
        e += sum(coeff * bits[i] for i, coeff in self.linear.items())
        e += sum(coeff * bits[i] * bits[j]
                 for (i, j), coeff in self.quadratic.items())
        return float(e)

    def cut_value(self, bits: Sequence[int]) -> float:
        """Max-Cut convenience: the cut this assignment achieves.

        Only meaningful for a QUBO built by `maxcut_to_qubo`, where
        energy == -cut by construction. It exists so that callers never write
        the negation themselves.
        """
        return -self.energy(bits)

    def to_ising(self) -> Ising:
        """Substitute x_i = (1 - s_i) / 2, i.e. s = 1 - 2x.

        Kept here, as the single place the mapping is written, so the two forms
        cannot drift apart.
        """
        h: Dict[int, float] = {i: 0.0 for i in range(self.n_variables)}
        J: Dict[Pair, float] = {}
        offset = self.offset

        for i, a in self.linear.items():
            offset += a / 2.0
            h[i] -= a / 2.0

        for (i, j), b in self.quadratic.items():
            offset += b / 4.0
            h[i] -= b / 4.0
            h[j] -= b / 4.0
            J[(i, j)] = J.get((i, j), 0.0) + b / 4.0

        h = {i: v for i, v in h.items() if v != 0.0}
        J = {k: v for k, v in J.items() if v != 0.0}
        return Ising(h=h, J=J, offset=offset, n_variables=self.n_variables)


def _n_nodes_or_refuse(problem: MaxCutProblem) -> int:
    """`MaxCutProblem.n_nodes` counts nodes that appear in an edge.

    An isolated node is therefore not counted, and its index can exceed the
    reported size -- which would silently index past the end of a bit vector.
    Refuse rather than produce an objective over the wrong variable set.
    """
    n = problem.n_nodes
    referenced = {v for edge in problem.edges for v in edge}
    if referenced and max(referenced) >= n:
        raise ValueError(
            f"node index {max(referenced)} exceeds n_nodes={n}. MaxCutProblem "
            "counts only nodes that appear in an edge, so a graph with an "
            "isolated node cannot be indexed consistently. Relabel the nodes "
            "contiguously from 0 before converting.")
    return n


def maxcut_to_qubo(problem: MaxCutProblem) -> QUBO:
    """Max-Cut as a QUBO minimisation.

    For edge (i, j) with weight w, the cut indicator is
    `x_i + x_j - 2 x_i x_j`, which is 1 exactly when the endpoints differ.
    Negated for minimisation, that contributes `-w` to each incident linear
    term and `+2w` to the pair.

    Negative weights are permitted here -- unlike `ClassicalMaxCutSolver`,
    whose MILP linearisation is exact only while the objective pushes y_ij up.
    A QUBO has no such restriction, because nothing is being relaxed.
    """
    n = _n_nodes_or_refuse(problem)

    linear: Dict[int, float] = {}
    quadratic: Dict[Pair, float] = {}

    for (i, j), w in zip(problem.edges, problem.weights):
        if i == j:
            raise ValueError(f"self-loop at node {i} has no cut contribution")
        w = float(w)
        linear[i] = linear.get(i, 0.0) - w
        linear[j] = linear.get(j, 0.0) - w
        key = (i, j) if i < j else (j, i)
        quadratic[key] = quadratic.get(key, 0.0) + 2.0 * w

    if problem.edges and not quadratic:
        raise ValueError(
            "conversion produced no quadratic terms for a graph with edges. "
            "An empty QUBO reported as a success is the exact failure this "
            "module was written to replace.")

    return QUBO(linear=linear, quadratic=quadratic, offset=0.0, n_variables=n)


def default_portfolio_penalty(problem: PortfolioProblem,
                              risk_aversion: float) -> float:
    """A penalty large enough that violating the budget cannot pay.

    Not a magic number: it is an upper bound on how much the unconstrained
    objective can improve by adding or removing a single asset. Adding asset i
    changes the objective by at most its own risk term plus its interactions
    plus its return term, so bounding by the total absolute coefficient mass
    guarantees no single-asset deviation is profitable.

    Callers who know their instance can pass a tighter `penalty`; the tests
    check that this default actually enforces the budget by enumeration, which
    is the only claim being made for it.
    """
    risk_mass = float(np.abs(problem.covariances).sum())
    return_mass = float(risk_aversion * np.abs(problem.returns).sum())
    return max(1.0, risk_mass + return_mass)


def portfolio_to_qubo(problem: PortfolioProblem,
                      budget: int,
                      risk_aversion: float = 1.0,
                      penalty: float = None) -> QUBO:
    """Binary asset selection as a QUBO minimisation.

    Minimises `x^T C x - q mu^T x + P (sum_i x_i - K)^2`, where x_i selects
    asset i, C is the covariance, mu the expected returns, q the risk-aversion
    trade-off and K the budget (number of assets to hold).

    The budget is a hard constraint expressed as a penalty, which is what makes
    the problem unconstrained and therefore encodable. `penalty=None` uses
    `default_portfolio_penalty`, whose reasoning is documented there.
    """
    n = problem.n_assets
    if not 0 <= budget <= n:
        raise ValueError(f"budget {budget} outside 0..{n}")
    if penalty is None:
        penalty = default_portfolio_penalty(problem, risk_aversion)
    if penalty <= 0:
        raise ValueError("penalty must be positive to bind the budget")

    C = np.asarray(problem.covariances, dtype=float)
    mu = np.asarray(problem.returns, dtype=float)

    linear: Dict[int, float] = {}
    quadratic: Dict[Pair, float] = {}

    # x_i^2 == x_i for binary x, so the diagonal of the risk term is linear.
    for i in range(n):
        linear[i] = (float(C[i, i])
                     - risk_aversion * float(mu[i])
                     + penalty * (1.0 - 2.0 * budget))

    for i in range(n):
        for j in range(i + 1, n):
            coeff = 2.0 * float(C[i, j]) + 2.0 * penalty
            if coeff != 0.0:
                quadratic[(i, j)] = coeff

    offset = penalty * float(budget) ** 2
    return QUBO(linear=linear, quadratic=quadratic,
                offset=offset, n_variables=n)
