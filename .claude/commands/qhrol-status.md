---
description: Re-measure the lab against the post-shrink baseline — tests, the open scaffolding claims, and whether SCAFFOLDING.md still matches the code — and report what has moved.
allowed-tools: Bash, Read, Grep, Glob
---

## Task

Re-measure this repository against the baseline below and report what has changed.
Measure; do not estimate. If a figure cannot be measured right now, say so and say why —
never carry a baseline value forward as if it were current.

This repository exists to distinguish computed numbers from invented ones. A status
command that guesses would be the same failure in miniature.

## Baseline (2026-08-30, tip of `shrink-to-verified-core`, after the shrink and the pin)

| Metric | Baseline |
|---|---|
| Tests | 83 passed, 0 failed, 0 skipped |
| Verified against | Python 3.11.16 (qiskit 2.5.2, mitiq 1.0.0, cvxpy 1.9.2) **and** 3.10.21 (qiskit 2.4.2, mitiq 0.47.0) |
| Tracked files | 35 (was 133 before the shrink) |
| `src/` packages | 4 — `optimization`, `error_mitigation_service`, `execution_orchestrator_service`, `hybrid_baseline_service` |
| Entry points | None. A library, its tests, and `examples/qoptisolve_usage.py` (runs from any cwd since the editable install) |
| `compileall` on 3.11 | Clean |
| Canonical form (QUBO/Ising) | **Not implemented anywhere** — the blocker for every quantum result |
| Quantum objective value | Never computed; `compute_optimality_gaps:271` defaults it to `0.0` |
| Confidence interval | Hardcoded `±0.05` at `src/hybrid_baseline_service/service.py:303`, `# Simulated CI` |
| Baselines that raise | metaheuristic, ML |
| `src/optimization/qaoa.py` | Zero callers, zero tests |
| CI | `.github/workflows/ci.yml` — test matrix on 3.10/3.11, plus a compile job pinned to 3.10 |
| Manifest installable | Yes. `pyproject.toml` is the single source of truth; `requirements.txt` is an `-e .[test]` shim |
| Python pin | `requires-python = ">=3.10,<3.12"`, enforced at install: 3.12+ fails naming the interpreter |

## Steps

1. `git fetch` and report whether the tree is behind `origin`, and whether it is dirty.
2. Run the suite on a **Python 3.11** interpreter and report passed/failed/skipped with
   the resolved `qiskit`, `mitiq` and `cvxpy` versions. **If `mitiq` reports version
   `0.0.0`, the environment is wrong, not the code** — that is a placeholder release pip
   falls back to on 3.12+, and it has no `mitiq.zne` submodule. Say so rather than
   reporting six ZNE failures.
3. Run `python examples/qoptisolve_usage.py` and report whether it completes and whether
   its numbers are plausible. It should not need `PYTHONPATH`; if it does, the editable
   install is missing.
4. Check each open claim from the table:
   - `grep -rn "raise NotImplementedError" src/`
   - whether anything converts a problem to QUBO or Ising form
   - whether `compute_optimality_gaps` still defaults the quantum objective to `0.0`
   - whether the `# Simulated CI` literal is still there
   - whether anything imports or tests `src/optimization/qaoa.py`
   - whether CI is still green on both matrix legs, and whether the compile job is still
     pinned below 3.12 — on 3.12+ it passes over exactly the construct it exists to catch
   - whether `pip install -r requirements.txt` still resolves on 3.10 and 3.11, and still
     refuses 3.12+ at install time
5. Read `SCAFFOLDING.md` and report any row whose status no longer matches the code — in
   either direction. A component that has quietly become real is drift too, and it is the
   kind that makes the honest document look alarmist. Note that this document has been
   wrong before, in both directions, so read it against the code rather than trusting it.

## Output

A delta table — metric, baseline, now, direction — then a list of claims in `README.md`
or `SCAFFOLDING.md` that are no longer accurate. Do not edit any file; this command only
reports.
