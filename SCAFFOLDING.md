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
| `src/hybrid_baseline_service/service.py` — MILP/exact baseline | `objective_value`, `runtime`, `optimality_gap`, and `upper_bound`/`lower_bound` — bounds whose entire purpose is rigour — all random; reported `solver: "cplex_simulated"` | a real solver; see the note on `ClassicalMaxCutSolver` below |
| ” — heuristic baseline | the local search was genuine but optimised `_evaluate_solution`, which is fiction; runtime and gap random | a real objective, then keep the search loop |
| ” — metaheuristic baseline | same | a real objective; the GA mechanics in `src/hpo_evolution_service/` are genuine and reusable |
| ” — ML baseline | reported `model_type: "feedforward_nn_simulated"`; there is no model | train a model, or delete the baseline |
| ” — `_evaluate_solution` | **the root fabrication**: returned a made-up function of how many bits were set, minus `np.random.uniform(0, 2)` — never looked at the problem, and was non-deterministic, so the search compared incomparable values | compute the real objective (cut weight / risk-adjusted return) |
| `src/execution_orchestrator_service/service.py` | sampled counts from a binomial with no circuit involved; `execution_time` random; `average_objective_value` from a Hamming-weight formula labelled "Simple example"; advertised a 32-qubit backend that does not exist | run on `qiskit-aer` (pinned in requirements.txt but **not installed** — `./.venv/bin/pip install qiskit qiskit-aer`) |
| `src/error_mitigation_service/service.py` — ZNE | reshaped one distribution by ±15%. The direction is right (it sharpens), but ZNE requires running at **amplified** noise levels and extrapolating, and no amplified run happened. `zne_improvement` was a fixed 5% of the input, independent of the data | noise scaling by unitary folding at λ = 1, 2, 3; Richardson or linear fit; evaluate at λ = 0 |
| ” — PEC, CDR, VNLE | same shape: plausible output, technique never performed | PEC needs a characterised noise model; CDR needs near-Clifford training circuits |
| `src/problem_definition_service/service.py` — canonical form | returned an **empty** QUBO (`linear_terms: {}`, `quadratic_terms: {}`) while logging success and reporting `method: "automatic_conversion"` | build the coefficient maps; `src/optimization/problems.py` already holds real MaxCut edge weights and portfolio covariance |

## Known-broken, not yet fixed

**`src/optimization/classical.py` — `ClassicalMaxCutSolver` does not solve.**
Its objective `x[i]*(1-x[j]) + x[j]*(1-x[i])` is bilinear, so cvxpy rejects it:
*"Problem does not follow DCP rules."* The solver catches the exception, warns,
and returns `{'partition': None, 'cut_value': None, 'status': 'error'}`.

That return is honest, but **the test suite passes anyway** — the tests assert on
shape and status, never that a cut was found. So the lab has a headline solver
that has never solved anything, with green tests over it.

The fix is textbook MILP linearisation: introduce `y_ij ∈ [0,1]` per edge with
`y_ij ≤ x_i + x_j`, `y_ij ≤ 2 − x_i − x_j`, `y_ij ≥ x_i − x_j`, `y_ij ≥ x_j − x_i`,
then maximise `Σ w_ij · y_ij`. That is linear, hence DCP-compliant, and exact for
binary `x`.

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
- `src/optimization/classical.py` — `solve_maxcut_greedy` /
  `solve_portfolio_greedy` are real greedy heuristics. (`ClassicalMaxCutSolver`
  is real in intent but non-functional; see above.)
- `src/hpo_evolution_service/service.py` — genuine GA mechanics. Its randomness
  is algorithmic (mutation, crossover, tournament selection), not fabricated
  results, and should be left alone.
- `migration_inbox/qOptiSolve/` — prior work with its own tests, including real
  QAOA cost and mixing Hamiltonians.

The rule used throughout: **randomness as an algorithmic choice is legitimate;
randomness as a reported result is fabrication.** The test is whether a caller
would read the number as a measurement.
