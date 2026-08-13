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
| ” — metaheuristic baseline | same | a real objective; the GA mechanics in `src/hpo_evolution_service/` are genuine and reusable |
| ” — ML baseline | reported `model_type: "feedforward_nn_simulated"`; there is no model | train a model, or delete the baseline |
| ” — `_evaluate_solution` | **the root fabrication**: returned a made-up function of how many bits were set, minus `np.random.uniform(0, 2)` — never looked at the problem, and was non-deterministic, so the search compared incomparable values | compute the real objective (cut weight / risk-adjusted return) |
| `src/execution_orchestrator_service/service.py` | sampled counts from a binomial with no circuit involved; `execution_time` random; `average_objective_value` from a Hamming-weight formula labelled "Simple example"; advertised a 32-qubit backend that does not exist | run on `qiskit-aer` (pinned in requirements.txt but **not installed** — `./.venv/bin/pip install qiskit qiskit-aer`) |
| `src/error_mitigation_service/service.py` — ZNE | as described below | **PARTLY DONE.** The extrapolation half is implemented and tested (`zne.py`): Richardson and least-squares linear fits, plus unitary folding. It now requires real measurements at ≥2 noise factors and refuses a single unamplified run. Producing those measurements end-to-end still needs circuit execution |
| ” — PEC, CDR, VNLE | same shape: plausible output, technique never performed | PEC needs a characterised noise model; CDR needs near-Clifford training circuits |
| `src/problem_definition_service/service.py` — canonical form | returned an **empty** QUBO (`linear_terms: {}`, `quadratic_terms: {}`) while logging success and reporting `method: "automatic_conversion"` | build the coefficient maps; `src/optimization/problems.py` already holds real MaxCut edge weights and portfolio covariance |

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

`qiskit-aer 0.17.2` and `mitiq 1.0.0` are now installed in `.venv`. What remains
for end-to-end ZNE is wiring circuit execution to Aer so the amplified-noise
measurements are produced rather than demanded from the caller.

## Known-broken, historical record

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

## Duplicate service tree

`services/*.py` is an older copy of every service in `src/`. `main.py` uses
`src/`; `main_orchestrator.py` still imports `services/`, which cannot run in
`.venv` regardless (needs `pydantic`).

The duplicates still fabricate, and one is worse than its counterpart: the
`services/` copy of ZNE pushes probabilities **toward** 0.5 — measured peak
0.70 → 0.62, entropy 1.32 → 1.55 bits — flattening the distribution, the
opposite of its own comment and of what mitigation does. The `src/` copy at
least sharpens.

They now raise `ImportError` on import rather than being deleted, because
deleting a tree that a live entry point imports, without being able to run that
entry point, trades one silent breakage for another.

**To resolve:** repoint `main_orchestrator.py` at `src/`, check the constructor
signatures line up, then delete `services/`.

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
- `src/hpo_evolution_service/service.py` — genuine GA mechanics. Its randomness
  is algorithmic (mutation, crossover, tournament selection), not fabricated
  results, and should be left alone.
- `migration_inbox/qOptiSolve/` — prior work with its own tests, including real
  QAOA cost and mixing Hamiltonians.

The rule used throughout: **randomness as an algorithmic choice is legitimate;
randomness as a reported result is fabrication.** The test is whether a caller
would read the number as a measurement.
