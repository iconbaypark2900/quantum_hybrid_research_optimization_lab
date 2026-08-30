---
description: Wave 2 — connect the comparative pipeline to the classical baselines it claims to compare against. It calls a method that does not exist, and never calls the one that works.
allowed-tools: Bash, Read, Edit, Write, Grep, Glob
---

## Task

Under PRD 04 this lab's stated purpose is evaluating quantum advantage against
strong classical baselines. The comparative pipeline does not reach a classical
baseline at all.

Two facts, both verified:

1. `main.py:245` calls `self.hybrid_baseline_service.compare_quantum_classical(...)`.
   **No such method exists** — anywhere in `src/`, so the pipeline dies with
   `AttributeError`. (It is not the only broken call site in `main.py`: all three
   `log_experiment` calls pass a single dict to a four-argument method. That one belongs
   to `/qhrol-registry-and-hpo-honesty`.)
2. `run_baseline` — the exact MILP solver and the hill-climbing heuristic, the two
   components this repository worked hardest to make real and verified against
   brute force — is called **only from `tests/`**. No application path reaches it.

So the headline claim of the lab is backed by code that only the test suite has
ever run.

## What exists to wire

`src/hybrid_baseline_service/service.py`:

- `run_baseline(problem, algorithm, **kwargs)` (`:83`) — dispatches to `milp`
  (`:137`, exact, brute-force verified) and `heuristics` (`:184`, real local
  optimum, runtime measured). `metaheuristics` (`:229`) and `machine_learning`
  (`:237`) raise, correctly.
- `compute_optimality_gaps(quantum_result, ...)` (`:265`) — this is the real
  comparison method, and almost certainly what `main.py:245` was reaching for.
- `_interpret_gap(gap, performance)` (`:307`).

## Steps

0. **First, delete the fabricated classical baselines.** Before any wiring, look at
   `main.py:432-447`. The comparative pipeline does not merely fail to call
   `run_baseline` — it invents the classical side outright, in a loop, unconditionally
   and behind no mock guard:

   ```python
   for algo in classical_algorithms:
       logger.info(f"Running classical algorithm: {algo}")
       # Mock classical result
       classical_result = {"algorithm": algo, "result": {
           "objective_value": 0.65,   # Example value
           "runtime": 2.5,            # Example runtime in seconds
           "solution": "classical_solution_placeholder",
           "optimum": 0.70            # Example optimum value
       }, "status": "completed"}
   ```

   It logs "Running classical algorithm: milp" and reports `status: "completed"` having
   run nothing. This is the exact fabrication `SCAFFOLDING.md` opens by declaring purged —
   commit `c15de9a` made the *service* raise, and `main.py` simply stopped asking the
   service. It is the single worst line in the repository and it is what step 1 replaces.

1. Change `main.py:245` to the method that exists. Read `compute_optimality_gaps`
   and match its signature rather than assuming — the call site was written
   against an API that never existed, so do not trust its argument shape either.
2. Have `run_comparative_analysis` actually run the classical side: call
   `run_baseline` for each algorithm named in `config/settings.json`
   (`classical_algorithms`), then feed those results to `compute_optimality_gaps`.
   Right now the config lists four algorithms and the application runs none.
3. Handle the two that raise as *expected absences*, not errors. `metaheuristics`
   and `machine_learning` are honestly unimplemented; the pipeline should report
   the comparison it could make and name the baselines it skipped, rather than
   failing the whole run or silently comparing against fewer baselines than the
   config claims.
4. Trim `config/settings.json` to what runs, or annotate the two that do not — a
   config listing four baselines when two raise is the same class of claim this
   repository has been closing everywhere else.
5. Add a test that the comparative pipeline reaches `run_baseline` and returns a
   gap computed from a real cut value. Assert the gap against a known graph where
   the optimum is hand-computable, not merely that a float came back.

## Acceptance

- `grep -rn "compare_quantum_classical" .` returns nothing.
- Something outside `tests/` calls `run_baseline`.
- The comparative pipeline in `python main.py` completes and reports an
  optimality gap derived from the exact MILP solver.
- The run states which configured baselines were skipped and why.
- Full suite green: `python -m pytest`.

## Ordering

Depends on `/qhrol-canonical-form` for a meaningful *result*, not for reachability. The
comparative pipeline already reaches this code: `run_quantum_experiment_pipeline` wraps
its body in a bare `except Exception` (`main.py:393`) and returns `{"status": "failed"}`
instead of propagating, so the canonical-form `NotImplementedError` is swallowed and
`run_comparative_evaluation_pipeline` carries on to `run_comparative_analysis`
(`main.py:451`) and dies at `main.py:245`. You can therefore fix this command's defect
first and see it work; the numbers only become meaningful once conversion lands.

## Commit convention

Imperative, in the existing style — e.g. "Let the comparison reach the solver it
compares against". **No `Co-Authored-By` or `Claude-Session` trailers.**
