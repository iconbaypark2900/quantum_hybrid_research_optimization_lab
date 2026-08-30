---
description: Wave 2 — implement QUBO/Ising conversion for real. It is the single blocker: every quantum pipeline in the lab dies on it, and an empty QUBO is what made the old results plausible instead of wrong.
allowed-tools: Bash, Read, Edit, Write, Grep, Glob
---

## Task

`_convert_to_canonical_form` (`src/problem_definition_service/service.py:49-70`)
raises. It is the first call in the quantum pipeline, so both the quantum and
comparative pipelines in `main.py` fail on it — it is the **first** blocker on the demo
path, though not the only one. Once it is fixed, `python main.py` next fails on
`execute_circuit` being called without `circuit=` (`main.py:305-309`) and on
`compare_quantum_classical`, which does not exist (`main.py:245`). Fixing this alone
will not produce a working demo; it will move the failure one step further down.

It is worth reading why it was made to raise. The original returned
`linear_terms: {}`, `quadratic_terms: {}`, `hamiltonian_terms: []` while logging
success and reporting `method: "automatic_conversion"`. Every circuit built from
it encoded no problem at all — and *still produced results*, because the
execution and mitigation layers downstream were happy to run a circuit that
optimised nothing. An empty QUBO does not crash; it quietly makes every
subsequent number meaningless.

## What you have to build on

`src/optimization/problems.py` already holds real, seeded, deterministic
structures — and, importantly, working conversions to build against:

- `MaxCutProblem` (`:45`) — `edges`, `weights`, `adjacency_matrix` (`:68`), and
  `to_qaoa_format()` (`:77`)
- `PortfolioProblem` (`:14`) — expected returns, covariance, and
  `to_qaoa_format()` (`:34`)

`_unreachable_original_conversion` (`:72`) is retained for its classification
logic only. Take the type-dispatch from it; take nothing else.

## Steps

1. Implement Max-Cut → QUBO first; it is the case the repository can already
   check. For an edge `(i, j)` with weight `w`, maximising the cut is
   `Σ w_ij (x_i + x_j - 2 x_i x_j)` — linear terms `w_ij` on each incident
   variable, quadratic term `-2 w_ij` on the pair. Fix a sign convention
   (minimise) and state it in the docstring; a sign error here is invisible
   downstream and will read as a poor result rather than a bug.
2. Implement portfolio → QUBO from the covariance matrix and expected returns,
   with the budget constraint as a penalty term. Make the penalty coefficient an
   explicit parameter with a documented default — not a magic number.
3. Emit Ising alongside QUBO where asked (`s = 1 - 2x`), and keep the mapping in
   one place so the two cannot drift apart.
4. **Pin it with an oracle, following `tests/test_baselines_oracle.py`.** The
   pattern is already established in this repo and it is the only thing that
   distinguishes a working conversion from a plausible one:
   - For n = 4..8, enumerate every bitstring, evaluate the QUBO objective, and
     assert its optimum equals the brute-force cut value.
   - Assert against `ClassicalMaxCutSolver`, which is exact and already verified.
   - Use the hand-computable cases the repo already trusts: a 4-cycle cuts all 4
     edges; a triangle cuts only 2.
   - Assert a non-empty conversion explicitly. `len(quadratic_terms) == len(edges)`.
     The precise historical failure was an empty dict reported as success, so
     test for it by name.
5. Only once the oracle passes, delete `_unreachable_original_conversion` and
   update the `SCAFFOLDING.md` row for canonical form to `DONE`, in the style of
   the MILP and heuristic rows.

## Acceptance

- `python -m pytest tests/test_canonical_form_oracle.py` green, including the
  n = 4..8 enumeration.
- The QUBO optimum agrees with `ClassicalMaxCutSolver` on every generated graph.
- `python main.py` no longer fails on canonical-form conversion.
- Full suite green, and `SCAFFOLDING.md` no longer lists this as not implemented.

## Commit convention

Imperative, in the existing style — e.g. "Build the QUBO the circuits were
supposed to encode". **No `Co-Authored-By` or `Claude-Session` trailers.**
