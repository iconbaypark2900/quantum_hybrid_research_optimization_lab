# What this lab does not do yet

This file exists because the alternative was worse. Until now the services below
returned plausible-looking numbers instead of failing, so the gaps were
invisible: you could call every endpoint, get a full result object, and have no
way to tell that nothing had been computed.

They now raise `NotImplementedError` with a message saying what is missing and
what it would take. **A caller that cannot get an answer is inconvenienced; a
caller that gets a fabricated one is misled, and cannot tell.**

## Why this matters more here than in most projects

Under PRD 04 this lab's purpose is to evaluate **quantum advantage against
strong classical baselines**. Every classical baseline returned
`np.random.uniform(...)` as its objective value, runtime and optimality gap. A
quantum result compared against a random number is not a weak finding — it is an
unfalsifiable one, which is the specific failure the research-integrity work in
`financial_alpha_risk_research_lab` exists to prevent.

## Not implemented (raises `NotImplementedError`)

| Component | What it faked | What it needs |
|---|---|---|
| ~~MILP/exact baseline~~ | — | **DONE.** Solves the real graph via linearised MILP; verified against brute force for n = 4..8 |
| ~~heuristic baseline~~ | — | **DONE.** Hill-climbs the real cut value to a genuine local optimum; runtime measured |
| ~~” — metaheuristic baseline~~ | same | **DONE.** Simulated annealing on the real cut value, geometric cooling, seeded and timed. Pinned against brute force, and asserted to accept worsening moves so it is not the greedy baseline under another name |
| ~~” — ML baseline~~ | reported `model_type: "feedforward_nn_simulated"`; there is no model | **REMOVED.** The choice offered here was "train a model, or delete the baseline". There is no meaningful supervised baseline for a single Max-Cut instance, so it was deleted rather than left raising — asking for it now names what exists instead |
| ” — `_evaluate_solution` | **the root fabrication**: returned a made-up function of how many bits were set, minus `np.random.uniform(0, 2)` — never looked at the problem, and was non-deterministic, so the search compared incomparable values | compute the real objective (cut weight / risk-adjusted return) |
| ~~`src/execution_orchestrator_service/service.py`~~ | sampled counts from a binomial with no circuit involved; `execution_time` random; `average_objective_value` from a Hamming-weight formula labelled "Simple example"; advertised a 32-qubit backend that does not exist | **DONE.** Executes on `AerSimulator` with an optional depolarising noise model; refuses a missing circuit rather than downgrading |
| ~~`src/error_mitigation_service/service.py` — ZNE~~ | as described below | **DONE.** Richardson and least-squares linear fits plus unitary folding (`zne.py`), verified against Mitiq; the loop is closed — it produces its own measurements at ≥2 noise factors and refuses a single unamplified run |
| ~~” — CDR~~ | same shape: plausible output, technique never performed | **DONE.** `mitiq.cdr.execute_with_cdr` against a noiseless simulator for the training set; measured to move the estimate toward the true value |
| ” — PEC | same shape: plausible output, technique never performed | **Implemented, and measured not to help.** `mitiq.pec.execute_with_pec` runs, but its representations assume a depolarising convention Aer does not apply — Qiskit's `(1-p)ρ + p·I/2` is Mitiq's ε = 3p/4 on one qubit and 15p/16 on two, and Mitiq applies one ε to both. Bias ≈ +0.07 on a Bell state at 5% noise; more samples shrink the variance and not the bias. Needs representations matched to the channel actually applied |
| ” — VNLE | same shape | not attempted |
| ~~canonical form (QUBO/Ising)~~ | returned an **empty** QUBO (`linear_terms: {}`, `quadratic_terms: {}`) while logging success and reporting `method: "automatic_conversion"` | **DONE.** `src/optimization/canonical.py`. Max-Cut and portfolio to QUBO, with Ising by a single documented substitution. Verified by enumeration against brute force and against the MILP solver for n = 4..8, and on every assignment rather than only the optimum |

## Fixed since this file was written

**`ClassicalMaxCutSolver` now solves.** It was rewritten with the MILP
linearisation described below and verified against brute-force enumeration for
n = 4..8, plus two graphs computable by hand (a 4-cycle cuts all 4 edges; a
triangle cuts only 2, because an odd cycle is not bipartite). Negative weights
are now refused, since the linearisation is exact only while the objective
pushes `y_ij` up.

`tests/test_baselines_oracle.py` pins this. It was validated by reintroducing
the bilinear objective: 11 of 15 tests fail, and all 15 pass again once
restored.

**Zero-noise extrapolation is half-implemented, honestly.**
`src/error_mitigation_service/zne.py` has the real mathematics — Richardson
extrapolation (exact on polynomials of degree < k, which the tests demand to
machine precision), least-squares linear extrapolation, and unitary folding with
odd scale factors only. On an exponentially decaying signal it reduces the error
against ground truth from 0.139 to 0.0027.

**It is now verified against Mitiq**, which the PRD names for exactly this job
("Mitiq plugged into the execution path (ZNE, PEC, CDR) when enabled", §4.3;
"Add Mitiq", §6 Phase 3). `tests/test_zne_vs_mitiq.py` compares the hand-written
Richardson and linear extrapolators against `RichardsonFactory` and
`LinearFactory` on identical inputs, and the folding against `fold_global`:
agreement to machine precision (worst 2.66e-15), identical folded operation
counts, and folded circuits equal to the original up to global phase.

Writing that maths by hand when the spec named a library was a mistake — the
same one, in miniature, as the deflated-Sharpe implementation inventing a
formula the spec told it to take from a paper. The recovery is that Mitiq is now
an oracle rather than a missed dependency: a deliberately introduced sign error
in the Lagrange basis is caught by the cross-check independently of the maths
tests.

**PEC and CDR should use Mitiq rather than be hand-written.** It implements both,
and there is no reason to repeat the mistake twice more.

**The loop is now closed.** Circuit execution runs on `AerSimulator` with an
optional depolarising noise model, and `_apply_zne` folds the circuit, executes
each scale factor, and extrapolates — producing its own measurements rather than
demanding them. On a Bell state (analytic parity `<ZZ> = +1`) under 3% noise it
lands within 0.0007 of the true value against 0.029 unmitigated, roughly 40x
closer.

One correctness requirement, learned the hard way: **execution must transpile at
`optimization_level=0`.** The default optimiser cancels adjacent inverse gate
pairs, which is exactly what unitary folding inserts. With it enabled, a Bell
circuit folded to lambda = 1, 3, 5, 7 transpiled to 5 operations and depth 3 in
every case — folding did nothing, noise was never amplified, and ZNE reported a
confident mitigated value extrapolated from three measurements of the same
circuit.

No amount of extrapolation maths could catch that: the values were
self-consistent, in range, and the fit exact. Only the physical invariant does —
a circuit with more noisy operations must measure worse — which is now asserted
in `tests/test_zne_end_to_end.py` and verified to fail when the optimisation
level is restored.

## Known-broken, historical record

**A fix that was measured and turned out not to be one** (2026-08-30). Not a shipped
bug — a hypothesis that survived one run and died under a proper one, recorded because
the discipline is the point.

QAOA's approximation ratio on a 6-node instance climbed 0.719 (p=1) → 0.775 (p=3) and
then *fell* to 0.724 at p=4. That is exactly what an optimiser losing a
higher-dimensional landscape looks like, and it is the textbook motivation for INTERP
layer-wise warm starts (Zhou et al. 2020). The warm start was implemented and defaulted
on, with a docstring explaining the failure it fixed.

Repeating over 4 instances × 2 initialisations:

| p | cold | warm |
|---|---|---|
| 2 | 0.759 | 0.767 |
| 4 | 0.765 | **0.738** |
| 6 | 0.785 | **0.771** |

Every difference is inside one standard deviation (~0.05), and warm start is *behind* at
p=4 and p=6. The dip was run-to-run noise. The default was changed to off and the
docstring rewritten to say so. What does help is depth itself, modestly: 0.759 → 0.785
from p=2 to p=6.

The lesson is the same one this repository keeps relearning at a different scale: a
single measurement that agrees with a plausible story is not evidence, and the story
being textbook-correct in general says nothing about whether it is operating here.


**The portfolio QAOA circuit did not encode the portfolio problem** (fixed
2026-08-30). Four defects at once, none visible from the result object:

- the cost layer read only `problem.covariances` and never `problem.returns`, so
  expected return — half the objective — was absent from the circuit;
- it looped over ordered pairs `(i, j)` and `(j, i)`, applying every coupling twice;
- it emitted a bare `rz` carrying the *pair* coefficient before each CX, adding a
  single-qubit term proportional to the covariance row sum that appears in no
  formulation of the problem;
- there was no budget constraint at all.

Meanwhile `solve_portfolio` scored its samples by a Sharpe ratio. **The circuit and
the scorer were optimising different functions**, and the returned dict — allocation,
final_cost, convergence — looked exactly as it would have if they agreed.

Both now derive from `portfolio_to_qubo`, so they are the same objective by
construction, and the cost layer is a single generic Ising builder shared with
Max-Cut. Max-Cut's circuit is unchanged by that move and provably so: its Ising form
has `h_i = 0` exactly and `J_ij = w_ij/2`, so `rz(2·J·γ)` is the `rz(w·γ)` the
hand-written version emitted — the existing gate-count tests pass untouched.

`tests/test_portfolio_qaoa_oracle.py` pins it against brute-force enumeration.
Reintroducing each of the four defects fails 4, 2, 3 and 6 of its 15 tests.

One test-design note worth keeping: the first version of those tests compared
`str(instruction.operation.params)` on an *unbound* circuit, which compares
`ParameterExpression` object reprs — memory addresses. It passed in isolation and
failed in the full suite. Binding the parameters first compares the coefficients the
circuit actually encodes.

**The comparison scored a real optimum against a default argument** (fixed
2026-08-30). `compute_optimality_gaps` read the quantum number as
`quantum_result.get('objective_value', 0.0)` — a silent default, for a key nothing
in this repository produced. It then computed a relative gap from it, attached an
interpretation, and returned it as the headline result.

Beside it, the confidence interval was the literal
`[relative_gap - 0.05, relative_gap + 0.05]`, commented `# Simulated CI`: a fixed
width with no variance, no bootstrap and no shot noise behind it. A confidence
interval is the archetypal number a reader takes as a measurement — it is an explicit
quantitative claim about uncertainty — and this one was a constant. `_interpret_gap`
completed the picture by returning "Significant quantum advantage (>10% improvement)"
from a single, unseeded, unreplicated run.

All three are gone. The objective is refused when absent, the interval is derived from
a standard error computed over the measured distribution and omitted when there is
none, and the word "significant" is not used until something computes it.
`tests/test_repository_claims.py` fails if a measured quantity is read with a numeric
default again — and it found a second live instance the moment it was written,
`list_baseline_results` reporting an absent objective as `0`.

**QAOA decoded every measurement to all-zeros** (fixed 2026-08-30). The only real
quantum solver in the repository had never been run. The first time it was, on a
4-cycle whose optimum is 4:

```
exact optimum : 4.0
QAOA reported : cut_value 0.0, partition [0 0 0 0], convergence 5
```

The circuits were built as `QuantumCircuit(n, n)` and then measured with
`measure_all()`, which adds a **second** classical register. The counts key was
therefore `"1000 0000"` — the measured register, then the one never written.
`_bits_from_counts_key` stripped the space and took the first `n` bits of the
reversed string, which came from the empty register. So every sampled partition
scored a cut of 0, the optimiser saw a flat landscape, and the result object came
back complete, consistent and confident.

Nothing about that is visible from outside: the dict has the right keys, the value
is a float, `convergence` reports iterations, and `cut_value` genuinely matches the
`partition` beside it — both were simply wrong together. Internal consistency is not
evidence.

`tests/test_qaoa_oracle.py` pins it with an oracle that needs no sampling at all:
prepare a computational basis state, measure it, and require the decoder to return
that exact pattern. Asymmetric patterns are used deliberately, because a reversed or
truncated decoder round-trips `0000` and `1111` and fails only on the rest. Restoring
the two-register construction fails 11 of the 27 tests.

**`MaxCutProblem.n_nodes` silently dropped isolated nodes** (fixed alongside it). It
counted distinct nodes appearing in an edge, so
`create_sample_maxcut(n_nodes=6, edge_prob=0.2)` returned a problem reporting 4.
Every consumer sizes itself from that — QAOA one qubit per node, the MILP solver one
variable, the brute-force oracle `2**n` — so all three solved a smaller problem than
the caller asked for, and none could tell. An isolated node cannot be recovered from
an edge list, so it is now declared explicitly.


**`ClassicalMaxCutSolver` did not solve** (fixed — kept here because the failure
mode is instructive).
Its objective was `x[i]*(1-x[j]) + x[j]*(1-x[i])`, which is bilinear, so cvxpy
rejected it: *"Problem does not follow DCP rules."* The solver caught the
exception, warned, and returned
`{'partition': None, 'cut_value': None, 'status': 'error'}`.

That return was honest, but **the test suite passed anyway** — the tests asserted
on shape and status, never that a cut was found. The lab had a headline solver
that had never solved anything, with green tests over it, for as long as it
existed.

Worth keeping because of what it says about test design: shape tests cannot
distinguish a working solver from a broken one. Only an oracle can, which is why
`tests/test_baselines_oracle.py` now enumerates.

The fix was textbook MILP linearisation: `y_ij ∈ [0,1]` per edge with
`y_ij ≤ x_i + x_j`, `y_ij ≤ 2 − x_i − x_j`, `y_ij ≥ x_i − x_j`, `y_ij ≥ x_j − x_i`,
maximising `Σ w_ij · y_ij` — linear, hence DCP-compliant, and exact for binary `x`.

## Duplicate service tree — resolved

`services/*.py` was an older copy of every service in `src/`, and it fabricated worse
than its counterpart: its ZNE pushed probabilities **toward** 0.5 — measured peak
0.70 → 0.62, entropy 1.32 → 1.55 bits — flattening the distribution, the opposite of
its own comment and of what mitigation does.

It was left raising `ImportError` rather than deleted, because `main_orchestrator.py`
imported it and could not be run to verify the change. Both were deleted in `4971088`:
`main_orchestrator.py` had never parsed on an interpreter this project can use, so the
entry point that blocked the deletion had never worked either.

## What is genuinely real

Not everything here is scaffolding, and the distinction matters when deciding
what to trust:

- `src/optimization/problems.py` — real MaxCut and portfolio problem structures,
  seeded and deterministic.
- `src/optimization/classical.py` — `ClassicalMaxCutSolver` now solves exactly
  and is verified against brute force; `solve_maxcut_greedy` /
  `solve_portfolio_greedy` are real greedy heuristics.
- `src/error_mitigation_service/zne.py` — real Richardson and linear
  extrapolation, and unitary folding.
- `src/optimization/objective.py` — reduces measured counts through the cost
  Hamiltonian to an expectation value, with a standard error computed from the
  distribution actually measured. Reports the best single sample beside it, named for
  what it is: a maximum over shots, which improves with shots even for a circuit that
  encodes nothing.
- `src/hybrid_baseline_service/service.py` — `compute_optimality_gaps` now refuses a
  quantum result carrying no objective value, offers an interval only when one was
  measured, and states the gap without asserting significance.
- `benchmark.py` — the entry point. Builds, solves exactly, runs QAOA with ZNE against
  the cost observable, and reports the comparison with its provenance.
- `src/optimization/canonical.py` — QUBO and Ising conversion, a minimisation by
  construction. Its minimum agrees with brute force and with the verified MILP solver,
  and it values every assignment correctly, not merely the optimum.
- `src/optimization/qaoa.py` — real `QuantumCircuit` construction with genuine cost
  and mixing Hamiltonians, driven by SPSA/COBYLA. Now verified: it recovers the known
  optimum on hand-solvable graphs, never exceeds the exact solver, and its counts
  decoder round-trips prepared basis states. See the historical record below for what
  the first run of it found.
- `src/execution_orchestrator_service/service.py` — real Aer execution, transpiled at
  `optimization_level=0` so folding survives.

An earlier version of this list vouched for `src/hpo_evolution_service/` ("should be
left alone") and for `migration_inbox/qOptiSolve/`. Both claims were wrong. The HPO
service reported `gp_kernel: "matern"` and `acquisition_function:
"expected_improvement"` with no Gaussian process anywhere in the codebase, and the
qOptiSolve tree still contained the exact non-solving bilinear Max-Cut objective this
document holds up as its most instructive failure, with tests that mocked cvxpy so
they passed over it. Both were deleted in the shrink. **A document whose value is that
its coverage can be trusted has to be audited too.**

The rule used throughout: **randomness as an algorithmic choice is legitimate;
randomness as a reported result is fabrication.** The test is whether a caller
would read the number as a measurement.
