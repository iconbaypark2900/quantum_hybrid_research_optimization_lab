---
description: Wave 1 — implement QUBO/Ising conversion. Nothing in the repository does this, and without it there is no quantum result to compare against anything.
allowed-tools: Bash, Read, Edit, Write, Grep, Glob
---

## Task

Nothing here converts a problem to canonical form. `src/problem_definition_service/` held
the only attempt and was deleted in the shrink, because what it did was worse than
nothing: it returned `linear_terms: {}`, `quadratic_terms: {}`, `hamiltonian_terms: []`
while logging success and reporting `method: "automatic_conversion"`.

That failure mode is worth keeping in mind while you write the replacement. An empty QUBO
does not crash. Every circuit built from it encodes no problem, optimises nothing, and
still returns results — plausible ones, in range, with no way for a caller to tell. The
old code was removed rather than repaired specifically so that nobody inherits its shape.

This is the first thing to build, because everything quantum in this repository is
downstream of it.

## Where it belongs

`src/optimization/`, beside the data it reads — not in a new service package. The shrink
removed the service framing; do not reintroduce it.

`src/optimization/problems.py` already holds real, seeded, deterministic structures with
working conversions to build against:

- `MaxCutProblem` (`:45`) — `edges`, `weights`, `adjacency_matrix` (`:68`),
  `to_qaoa_format()` (`:77`)
- `PortfolioProblem` (`:14`) — expected returns, covariance, `to_qaoa_format()` (`:34`)

## Steps

1. Implement Max-Cut → QUBO first; it is the case this repository can already check. For
   an edge `(i, j)` with weight `w`, maximising the cut is
   `Σ w_ij (x_i + x_j - 2 x_i x_j)` — linear terms `w_ij` on each incident variable, a
   quadratic term `-2 w_ij` on the pair. Fix a sign convention (minimise) and state it in
   the docstring. A sign error here is invisible downstream and reads as a poor result
   rather than a bug.
2. Implement portfolio → QUBO from the covariance matrix and expected returns, with the
   budget constraint as a penalty term. Make the penalty coefficient an explicit parameter
   with a documented default — not a magic number.
3. Emit Ising alongside QUBO where asked (`s = 1 - 2x`), and keep the mapping in one place
   so the two cannot drift apart.
4. **Pin it with an oracle, following `tests/test_baselines_oracle.py`.** That pattern is
   established here and it is the only thing that distinguishes a working conversion from
   a plausible one:
   - For n = 4..8, enumerate every bitstring, evaluate the QUBO objective, and assert its
     optimum equals the brute-force cut value.
   - Assert against `ClassicalMaxCutSolver`, which is exact and already verified.
   - Use the hand-computable cases this repository already trusts: a 4-cycle cuts all four
     edges; a triangle cuts only two, because an odd cycle is not bipartite.
   - Assert the conversion is non-empty, by name: `len(quadratic_terms) == len(edges)`.
     The historical failure was an empty dict reported as success, so test for it directly.
5. Update the `SCAFFOLDING.md` canonical-form row to `DONE`, in the style of the MILP and
   heuristic rows.

## Acceptance

- The QUBO optimum agrees with `ClassicalMaxCutSolver` on every generated graph, for
  n = 4..8, by enumeration.
- A test fails if the conversion returns empty terms.
- `SCAFFOLDING.md` no longer lists canonical form as the blocker.
- Full suite green.

## Ordering

First. `/qhrol-quantum-objective` needs the QUBO to reduce measurements against, and
`/qhrol-benchmark-driver` needs both.

## Commit convention

Imperative, in the existing style — e.g. "Build the QUBO the circuits were supposed to
encode". **No `Co-Authored-By` or `Claude-Session` trailers.**
