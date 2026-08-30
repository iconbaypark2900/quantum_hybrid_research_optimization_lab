---
description: Wave 2 — src/optimization/qaoa.py is the only real quantum solver in the repo, has zero callers and zero collected tests, and its 57 inherited tests are hidden by pytest.ini.
allowed-tools: Bash, Read, Edit, Write, Grep, Glob
---

## Task

Every defensible quantum-vs-classical number this lab could produce has to come out of
`src/optimization/qaoa.py`. It builds real `QuantumCircuit`s, real cost and mixing
Hamiltonians, and drives SPSA/COBYLA. It is the best quantum code in the repository.

Nothing has ever run it.

- **No callers.** No module outside `migration_inbox/` imports it. Not `main.py`, not the
  circuit generator service, not the execution orchestrator.
- **No collected tests.** `pytest.ini` is `testpaths = tests`, and no file in `tests/`
  imports it. The 79-test suite covers ZNE, the classical baselines, and the qOptiSolve
  problem structures — not this.
- **Its inherited tests are hidden.** `migration_inbox/qOptiSolve/tests/` holds **57 test
  functions** that `testpaths` excludes from every bare `pytest` run.

So the integration commit `1f8aca7` copied the code into `src/optimization/` and left its
tests behind, and `pytest.ini` is what conceals the shortfall. The repository reports 79
green tests over a quantum solver with no coverage at all.

## Why this is the same class of defect as the rest

`SCAFFOLDING.md`'s sharpest lesson is that green tests over untested code are how the
non-solving Max-Cut solver survived for months. Here the tests were not merely weak —
they were configured out of collection, which is the same outcome reached administratively.

Worse: `migration_inbox/qOptiSolve/` is listed under **"What is genuinely real"** in
`SCAFFOLDING.md`, but that tree still contains the original bilinear Max-Cut objective
(`classical.py:135`) that the same document holds up as its most instructive failure —
and its tests mock cvxpy, so they pass over it.

## Steps

1. Decide what `src/optimization/qaoa.py` is for. If `/qhrol-circuit-generator` folds the
   circuit generator service into it, this file becomes load-bearing and needs real
   coverage. If not, it is dead code and should be deleted rather than kept as a
   reassuring artifact.
2. Assuming it is kept, write tests in `tests/` with oracles, following
   `tests/test_baselines_oracle.py`:
   - a QAOA circuit for a known graph has the expected qubit count, and `p` cost layers
     and `p` mixer layers;
   - binding the optimal angles for a hand-solvable instance (a 4-cycle, or a single edge)
     recovers the known optimum within sampling error, with the tolerance stated;
   - the counts decoder maps a bitstring to the same cut value the exact solver computes.
   Check the decoder specifically — it reads a register that the circuit may never measure.
3. Triage the 57 hidden tests before deleting anything. Some cover behaviour `src/` still
   has; port those. Do not simply widen `testpaths` — that would collect a suite written
   against the superseded copy, including tests that mock cvxpy and would pass over a
   broken solver.
4. Then delete `migration_inbox/qOptiSolve/`, and correct the `SCAFFOLDING.md` line that
   vouches for it. Keep the technical paper.
5. Remove `testpaths` or make it explicit that it is a deliberate scope, once nothing is
   hidden behind it.

## Acceptance

- `src/optimization/qaoa.py` has tests in `tests/` that fail if the cost layer stops
  encoding the problem.
- No test file exists outside the collected path, or the ones that do are documented as
  deliberately excluded and why.
- `SCAFFOLDING.md` no longer lists as "genuinely real" a tree containing the solver it
  elsewhere describes as never having solved anything.
- Full suite green.

## Commit convention

Imperative, in the existing style — e.g. "Collect the tests for the solver that has none".
**No `Co-Authored-By` or `Claude-Session` trailers.**
