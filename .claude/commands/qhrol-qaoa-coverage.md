---
description: Wave 2 — src/optimization/qaoa.py is the only real quantum solver in the repo, has zero callers and zero collected tests, and its 57 inherited tests are hidden by pytest.ini.
allowed-tools: Bash, Read, Edit, Write, Grep, Glob
---

## Task

Every defensible quantum-vs-classical number this lab could produce has to come out of
`src/optimization/qaoa.py`. It builds real `QuantumCircuit`s, real cost and mixing
Hamiltonians, and drives SPSA/COBYLA. It is the best quantum code in the repository.

Nothing has ever run it.

- **No callers.** Nothing imports it — not the execution orchestrator, not the tests, not
  the usage example. After the shrink it is the only module in `src/` that nothing reaches.
- **No collected tests.** `pytest.ini` is `testpaths = tests`, and no file in `tests/`
  imports it. The 79-test suite covers ZNE, the classical baselines, and the qOptiSolve
  problem structures — not this.
- **Its inherited tests are gone.** `migration_inbox/qOptiSolve/` held 57 test functions
  that `pytest.ini`'s `testpaths = tests` excluded from every bare run, and the shrink
  deleted the tree — it also contained the non-solving bilinear Max-Cut objective, with
  tests that mocked cvxpy so they passed over it. Recover anything useful from `4971088`
  rather than trusting it wholesale.

So the integration commit `1f8aca7` copied the code into `src/optimization/` and left its
tests behind. The repository reports 79 green tests over a quantum solver with no coverage
at all.

## Why this is the same class of defect as the rest

`SCAFFOLDING.md`'s sharpest lesson is that green tests over untested code are how the
non-solving Max-Cut solver survived for months. Here the tests were not merely weak —
they were configured out of collection, which is the same outcome reached administratively.

`SCAFFOLDING.md` now lists this file under "What is genuinely real" with an explicit
caveat that nothing tests or calls it — "promising rather than trusted". This command is
what removes the caveat. Until then, do not cite a number that came out of it.

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
3. The 57 inherited tests are recoverable from `4971088` if useful, but treat them as
   suspect rather than as a starting point: they were written against the superseded copy,
   and some mock cvxpy in a way that would pass over a broken solver. Port behaviour, not
   assertions.
4. Update the `SCAFFOLDING.md` entry to drop the "untested and uncalled" caveat once it
   is no longer true.

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
