---
description: Wave 2 — write the one honest entry point this repository should have: build a problem, solve it exactly, run QAOA with mitigation, and compare. Replaces the deleted main.py.
allowed-tools: Bash, Read, Edit, Write, Grep, Glob
---

## Task

The shrink left this repository with no entry point, deliberately. `main.py` was a demo
harness written against an API that never existed, and its comparative pipeline fabricated
the classical side outright — a loop that logged "Running classical algorithm: milp",
reported `status: "completed"`, and invented `objective_value: 0.65`.

What should exist instead is small: **one script that runs the actual benchmark this lab
is named after**, end to end, on real components, and reports only what it measured.

## What it has to do

1. Build a Max-Cut instance from `src/optimization/problems.py` — seeded, so the run is
   reproducible, with the seed reported.
2. Solve it exactly with `ClassicalMaxCutSolver` (MILP, brute-force verified) and with the
   greedy heuristic. Both are real; both measure their own runtime.
3. Convert the instance to QUBO with `src/optimization/canonical.py` (done).
4. Build and run the QAOA circuit on Aer (`src/optimization/qaoa.py` — note it is
   currently untested; `/qhrol-qaoa-coverage` covers that).
5. Reduce the measured counts to an objective value under the cost Hamiltonian
   (`/qhrol-quantum-objective`), with and without ZNE.
6. Report the comparison: exact optimum, heuristic value, quantum value mitigated and
   unmitigated, the optimality gap, and the provenance — seed, shots, depth, backend,
   noise model, mitigation technique.

That is the whole program. It should be readable in one sitting.

## Rules it must follow

These are not style preferences; each corresponds to a specific failure this repository
has already made once.

- **No `.get(key, default)` on a measured quantity.** If a value was not computed, raise.
  The deleted comparison read `quantum_result.get('objective_value', 0.0)` and would have
  reported a confident gap against a default argument.
- **No mock, placeholder or example values, under any condition** — not behind an
  `except ImportError`, not behind an `if service is None`. If a dependency is missing,
  fail and name it. The deleted `main.py` swapped all seven services for an empty
  `MockService` on one missing import and then reported `7/7 services active, operational`.
- **The summary must derive from what ran.** Not from what was constructed, not from a
  hardcoded banner. The deleted demo printed "Phase 1 Implementation Complete" and four
  `✅` lines unconditionally, after two of its three pipelines had raised.
- **Report shots and seed with every quantum number.** A sampled expectation value without
  its shot count is not a measurement anyone can check.

## Steps

1. Write `benchmark.py` at the repository root, or `src/benchmark.py` with a thin
   `__main__`. Keep it under ~150 lines; if it grows past that, the logic belongs in the
   library, not the driver.
2. Make it take the instance size, depth, shots and seed as arguments with documented
   defaults, so a reader can reproduce a reported number exactly.
3. Add a test that runs it on a tiny instance and asserts the exact solver's value is
   reproduced, and that the reported gap is consistent with the two values it is computed
   from. Assert the driver **raises** when the quantum objective is unavailable, rather
   than reporting a gap.
4. Update the README Quick Start to name it, and `SCAFFOLDING.md` if the run reveals
   anything still missing.

## Acceptance

- One command produces a comparison table with real numbers on both sides and its
  provenance.
- `grep -n "mock\|placeholder\|Example value" benchmark.py` returns nothing.
- Removing the quantum objective makes it raise, not report a gap of zero.
- Full suite green.

## Ordering

Last of the science chain: after `/qhrol-quantum-objective` and
`/qhrol-honest-comparison`. It is the thing that makes them visible, so build it only once
the numbers underneath it are real.

## Commit convention

Imperative, in the existing style — e.g. "Run the benchmark this lab is named after".
**No `Co-Authored-By` or `Claude-Session` trailers.**
