---
description: Wave 1 — stop main.py reporting "operational" and "Phase 1 Complete" while its pipelines are failing. The fabrication purge reached the services; it never reached the layer above them.
allowed-tools: Bash, Read, Edit, Write, Grep, Glob
---

## Task

Commit `c15de9a` — "Stop fabricating results: unimplemented services now raise" —
cleaned `src/`. It did not touch `main.py`, which is the only part of this
repository a first-time reader actually runs.

Run `python main.py` today, with every dependency installed. Two of its three
pipelines raise. It then prints:

```
✅ Problem Definition: Active        ... (all seven)
📊 Active Services: 7/7
⚡ System Status: operational
🎉 Phase 1 Implementation Complete!
✅ System architecture validated
✅ Component integration verified
✅ Basic workflows operational
```

Every one of those lines is false, and a reader has no way to tell. This is the
precise failure `SCAFFOLDING.md` was written to eliminate — *"a caller that
cannot get an answer is inconvenienced; a caller that gets a fabricated one is
misled, and cannot tell"* — reproduced one layer up, where it is most visible.

## The defect

`get_system_status()` at `main.py:513-541` builds `service_status` from seven
`is not None` checks on constructor results. `active_services` (`main.py:525`)
counts object references. Nothing in the status path observes whether a pipeline
ran, so `"operational"` at `main.py:529` means only that seven constructors
returned — which they do even when every method on them raises.

The closing banner is worse: `main.py:642` announces "Phase 1 Implementation
Complete!" and `main.py:643-646` add four hardcoded `✅` lines — all five
printed unconditionally, after the failures, with no state behind them at all.

## Steps

1. Make the pipelines record their outcomes. Each `run_*_pipeline` in `main.py`
   already catches its exception and logs `Status: failed` — have it store that
   result on the lab instance rather than only logging it.
2. Rewrite `get_system_status()` so `status` derives from **what ran**, not what
   was constructed. Suggested shape: `operational` only when every enabled
   pipeline completed; `degraded` when some did; `failed` when none did. Keep the
   constructor checks, but report them as what they are — call the field
   `services_constructed`, not `active_services`, so the name cannot be misread
   as a health check.
3. Include the failures in the returned payload. A caller reading the dict must
   be able to see that the quantum pipeline raised `NotImplementedError` on
   canonical-form conversion without re-running anything.
4. Delete the unconditional banner and `✅` lines at `main.py:642-646`. Replace them
   with a summary computed from the recorded outcomes. If two pipelines failed,
   the last thing printed must say so.
5. Do not "fix" this by suppressing the failures or disabling the pipelines in
   `config/settings.json`. The failures must stay visible — but record each as what it
   actually is, because they are not the same kind. The quantum pipeline's is a designed
   refusal: a `NotImplementedError` carrying exactly the message it should. The
   comparative pipeline's is not — `main.py:245` calls
   `self.hybrid_baseline_service.compare_quantum_classical(...)`, a method defined
   nowhere in `src/`, so it dies on `AttributeError`. Supplying that method is
   `/qhrol-wire-baselines`'s job, not this one. The summary is lying, but it is not the
   only thing wrong.
6. Add `tests/test_orchestrator_honesty.py` pinning the invariant: **a run in
   which any pipeline raises cannot produce a status of `operational`, and cannot
   print a line containing "Complete" or "operational" as its final word.**
   Follow the design lesson already recorded in `SCAFFOLDING.md` — assert on the
   reported outcome against known-failing input, not on the shape of the dict.
   Shape tests are what let the non-solving Max-Cut solver pass for months.

## Acceptance

- `python main.py` on a fully-installed 3.11 environment exits reporting
  `degraded`, naming both failing pipelines.
- The status flips to `operational` only when the pipelines actually start working, with
  no edit to the status code. Do not treat that as a gate on this command: the demo path
  has **five** independent blockers, and canonical-form conversion is only the first.
  The others are `execute_circuit` called without `circuit=` (`main.py:305-309`),
  `apply_mitigation` called without `circuit=` (`main.py:328-332`),
  `compare_quantum_classical` not existing (`main.py:245`), and all three
  `log_experiment` call sites passing one dict to a four-argument method. They are owned
  by `/qhrol-canonical-form`, `/qhrol-quantum-objective`, `/qhrol-wire-baselines` and
  `/qhrol-registry-and-hpo-honesty` respectively.
- `tests/test_orchestrator_honesty.py` fails if the summary is restored to a
  hardcoded success.
- Full suite green: `python -m pytest`.

## Commit convention

Imperative, describing the claim being closed rather than the file being edited —
in the style of `c15de9a`. Something like "Stop the demo reporting success over
its own failures". **No `Co-Authored-By` or `Claude-Session` trailers.**
