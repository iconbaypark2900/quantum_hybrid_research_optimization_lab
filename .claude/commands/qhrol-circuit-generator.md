---
description: Wave 2 — the circuit generator emits JSON descriptions with random angles, not circuits. It is the one fabricating component SCAFFOLDING.md does not list.
allowed-tools: Bash, Read, Edit, Write, Grep, Glob
---

## Task

`src/circuit_generator_service/service.py` builds nested dictionaries describing
what a circuit would look like — `"structure"`, `"cost_layers"`,
`"mixer_layers"`, `"interactions": "all_to_all"` — and fills the parameters with
`np.random.uniform`:

- `:96-97` — QAOA `beta` and `gamma`, random
- `:154` — VQE `theta`, random
- `:270-271` — variational classifier `feature_weights` and `bias_parameters`, random
  (`_generate_variational_classifier`, `:243`; the quantum-kernel generator at `:188` is
  symbolic-only and does not fabricate)

The module imports no `qiskit`. Nothing here is a circuit, and nothing here is
optimised — the angles are drawn, labelled "Mixing angles" and "Cost angles",
and returned as though they were a generated ansatz.

By the rule stated at the bottom of `SCAFFOLDING.md` — *randomness as an
algorithmic choice is legitimate; randomness as a reported result is
fabrication; the test is whether a caller would read the number as a
measurement* — these are fabrication. A caller reads `gamma` as the parameters
of the circuit it asked for.

**This component is not in the `SCAFFOLDING.md` not-implemented table.** Adding
it is part of this task, and is the more important half: the value of that
document is that a reader can trust its coverage.

## The awkward part

`src/optimization/qaoa.py` already builds **real** circuits — `QuantumCircuit`,
`transpile`, `Parameter`, real cost and mixing Hamiltonians, SPSA/COBYLA
optimisers (`:10-20`). The lab has two parallel circuit paths and the service
layer uses the fake one.

## Steps

1. First, before any code: add a row to the `SCAFFOLDING.md` not-implemented
   table for `src/circuit_generator_service/service.py`, in the established
   format — what it fakes, what it needs. Do this even if you go on to fix it in
   the same session; the document's job is to be complete, and a gap in it is
   worse than a gap in the code.
2. Decide whether this service should exist. `src/optimization/qaoa.py` may
   already do everything it claims to. If so, the honest fix is to make the
   service a thin wrapper over it and delete the description-building code —
   not to write a second circuit builder.
3. If it stays, return real `QuantumCircuit` objects built from the QUBO produced
   by `/qhrol-canonical-form`. The cost layer must encode the actual quadratic
   terms; that is the whole point of the component.
4. Take the initial parameters from a stated strategy — a fixed seed, a linear
   ramp, or a documented random draw with the seed returned in the payload.
   Random initialisation is a legitimate algorithmic choice; returning it
   unlabelled as "the circuit's parameters" is not. Make the choice visible in
   the result.
5. Pin it with structural assertions, not shape checks: for a graph with `E`
   edges at depth `p`, assert the circuit contains `p·E` two-qubit cost
   rotations and `p·n` mixer rotations; assert the qubit count equals the node
   count; assert that binding `gamma = 0` leaves the cost layer as identity.
6. Check the same class of defect in the neighbouring service before closing:
   `grep -n "np.random" src/*/service.py`, and for each hit decide whether it is
   an algorithmic choice or a reported result.

## Acceptance

- `SCAFFOLDING.md` accounts for this service, whatever its final state.
- If kept: `generate_circuit` returns something `qiskit` can execute, and the
  execution orchestrator runs it on `AerSimulator` without a translation layer.
- The structural tests fail if the cost layer stops encoding the problem.
- Full suite green: `python -m pytest`.

## Commit convention

Separate commits for the documentation row and the implementation — the first is
valuable even if the second is deferred. Imperative, in the existing style.
**No `Co-Authored-By` or `Claude-Session` trailers.**
