---
description: Wave 2 — nothing in this lab computes a quantum objective value. The comparison silently substitutes 0.0 for it. This is the missing link the repository is named after.
allowed-tools: Bash, Read, Edit, Write, Grep, Glob
---

## Task

The lab exists to compare a quantum result against a strong classical baseline. Trace
where the quantum number comes from and there isn't one.

`compute_optimality_gaps` reads it like this:

```python
quantum_obj = quantum_result.get('objective_value', 0.0)   # service.py:271
```

A silent `.get` default. **No component in this repository produces that key.** The
execution orchestrator returns counts, probabilities, shot count, qubit count, circuit
depth and timing (`src/execution_orchestrator_service/service.py:187-198`) — no objective
value. So the moment `/qhrol-wire-baselines` routes the demo into this method, the
headline comparison evaluates a real MILP optimum against a hardcoded `0.0`, computes a
gap from it, and reports the result with an interpretation attached.

That is worse than the fabrications already purged. A fabricated number at least looks
like a measurement someone intended to take; this one is a default argument.

## The two halves that never meet

1. **Measurement → objective.** Bitstring counts must be reduced through the problem's
   cost Hamiltonian to a scalar. Nothing does this. The one place a scalar is produced is
   the ZNE path, and it measures the wrong thing (below).
2. **Mitigation is measuring parity, not cost.** `_apply_zne` defaults its observable to
   the parity of the bitstring (`src/error_mitigation_service/service.py:122-124`) — the
   right choice for the Bell-state test that validates the extrapolation, and meaningless
   for an optimisation problem. It then writes the extrapolated parity into
   `mitigated["average_objective_value"]` (`:191`), which is the field name the
   comparison layer reads as the problem's objective.

So the only scalar the quantum side can produce is a noise-mitigated Bell parity, stored
under a name that makes it look like a cut value.

## The third blocker

`main.py:328-332` calls `apply_mitigation(raw_result, technique)` with no `circuit=`
kwarg. The service closes the loop only when a circuit is supplied
(`src/error_mitigation_service/service.py:162`), so `_measure_at_scale_factors` never
runs and the whole closed-loop ZNE machinery — the repository's best work, verified
against Mitiq to 2.66e-15 — is unreachable from the application.

## Steps

1. Implement a cost-Hamiltonian observable: given a QUBO (from `/qhrol-canonical-form`)
   and a measured bitstring, return the objective value. For Max-Cut that is the cut
   weight. Put it beside the QUBO builder so the two cannot drift.
2. Reduce a counts dict to an expectation value under that observable — a shot-weighted
   mean, with the shot count carried through so uncertainty can be computed later.
3. Have the execution orchestrator (or a thin layer above it) return `objective_value` in
   its result, and make `compute_optimality_gaps` **refuse** a quantum result that lacks
   the key rather than defaulting to `0.0`. Follow the repository's established pattern:
   raise with a message saying what is missing and what it would take.
4. Pass the generated circuit and the cost observable from `main.py` Step 4 into
   `apply_mitigation` so the closed ZNE loop actually runs on the problem circuit.
5. Rename or separate the parity path so a Bell-state validation value can never be read
   as a problem objective. `average_objective_value` should mean one thing.
6. Test with an oracle, not a shape check: on a small graph, the expectation value of the
   cost observable over a *known* distribution must equal the hand-computed value; and a
   circuit prepared in a known optimal basis state must return exactly the MILP optimum.

## Acceptance

- `grep -n "get('objective_value', 0.0)" src/hybrid_baseline_service/service.py` returns
  nothing — a missing quantum objective raises.
- A QAOA run on a 4-cycle produces an objective value that the exact solver agrees with
  to within sampling error, and the test states the tolerance and why.
- `apply_mitigation` receives a circuit from `main.py`, and `_measure_at_scale_factors`
  is exercised by the demo path, not only by tests.
- Full suite green.

## Ordering

After `/qhrol-canonical-form` (it needs the QUBO) and before `/qhrol-honest-comparison`
(which reports the number this produces). `/qhrol-wire-baselines` must not be considered
finished until this lands — wiring the comparison without it produces a confident gap
computed against `0.0`.

## Commit convention

Imperative, in the existing style — e.g. "Measure the objective the comparison reads".
**No `Co-Authored-By` or `Claude-Session` trailers.**
