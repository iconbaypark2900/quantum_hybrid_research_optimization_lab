---
description: Wave 2 — the headline comparison ships a hardcoded ±0.05 confidence interval and calls a single unseeded run "Significant quantum advantage".
allowed-tools: Bash, Read, Edit, Write, Grep, Glob
---

## Task

`compute_optimality_gaps` is the method that produces this lab's headline claim. Two of
the things it returns are invented.

**The confidence interval is a literal.**

```python
"confidence_interval": [relative_gap - 0.05, relative_gap + 0.05],  # Simulated CI
```

`src/hybrid_baseline_service/service.py:303`. A fixed ±0.05, with no variance, no
bootstrap, no shot noise, no repeated runs behind it. A confidence interval is the
archetypal number a reader takes as a measurement — it is an explicit quantitative claim
about uncertainty. The comment `# Simulated CI` is honest to whoever writes the code and
invisible to everyone who reads the output.

**The interpretation asserts significance from one run.** `_interpret_gap` (`:307-325`)
returns strings like "Significant quantum advantage (>10% improvement)" on the basis of a
single, unseeded, unreplicated comparison. Significance is a statistical claim; nothing
here computes one.

By the repository's own rule — *the test is whether a caller would read the number as a
measurement* — both are fabrication, and they sit in the one method whose output is the
entire point of the project.

## Steps

1. Delete the hardcoded interval. Replace it with one of:
   - **a real interval** — repeat the quantum evaluation N times with distinct seeds and
     report the bootstrap or shot-noise interval, with N and the method in the payload; or
   - **no interval**, and a field saying uncertainty is not quantified.
   Do not keep the shape and improve the number later; an interval-shaped field with a
   placeholder inside is exactly the failure this repository was built to stop.
2. Make `_interpret_gap` state only what was computed. If the difference has not been
   tested for significance, it cannot say "significant" — say the gap and its direction.
   Reserve significance language for a path that actually runs a test.
3. Carry provenance into the result: how many shots, how many repetitions, which seed,
   which backend, whether mitigation was applied. A comparison a reader cannot audit is
   not a research artifact.
4. Make the classical side's `runtime` and the quantum side's `execution_time` comparable,
   or stop reporting them side by side. One is a simulator's wall clock including
   transpilation; the other is a MILP solve. A speedup ratio between them would be the
   next fabrication in this sequence.
5. Add a test that a comparison built from a *known* quantum value and a *known* classical
   optimum produces the gap you can compute by hand — and a test that the interval, if
   present, widens when shots are reduced. A constant interval must fail that test.

## Acceptance

- `grep -n "Simulated CI" src/` returns nothing.
- No field in the comparison output is a constant that reads as a measurement.
- The word "significant" appears only where a test was run, or not at all.
- The result payload names its shots, repetitions, seed and backend.
- Full suite green.

## Ordering

After `/qhrol-quantum-objective` — until a real quantum objective exists there is nothing
to put an interval around, and this method is comparing against `0.0`.

## Commit convention

Imperative, in the existing style — e.g. "Stop reporting an interval nothing measured".
**No `Co-Authored-By` or `Claude-Session` trailers.**
