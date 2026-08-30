---
description: Re-measure the lab against the 2026-08-30 baseline — tests, the demo path, and every open scaffolding claim — and report what has moved.
allowed-tools: Bash, Read, Grep, Glob
---

## Task

Re-measure this repository against the baseline below and report what has
changed. Measure; do not estimate. If a figure cannot be measured right now, say
so and say why — never carry a baseline value forward as if it were current.

This repository exists to distinguish computed numbers from invented ones. A
status command that guesses would be the same failure in miniature.

## Baseline (2026-08-30, HEAD `a466ef8`)

| Metric | Baseline |
|---|---|
| Tests | 79 passed, 0 failed, 0 skipped |
| Verified against | qiskit 2.5.2, mitiq 1.0.0, cvxpy 1.9.2 on Python 3.11 |
| `main.py` demo path | Runs; **2 of 3 pipelines fail, and it reports `operational` anyway** |
| `main_orchestrator.py` | `SyntaxError` at line 114 **on Python < 3.12 only** — parses fine on 3.12+ |
| Services raising `NotImplementedError` | canonical-form conversion; metaheuristic and ML baselines; PEC/CDR/VNLE |
| `services/` duplicate tree | Present, raises `ImportError` on import |
| `run_baseline` callers | Tests, plus `main_orchestrator.py:352` — which does not parse on the supported interpreter, so no runnable path reaches them |
| CI | None (`.github/` does not exist) |
| Python pin | None; `mitiq` cannot install on 3.12+ |
| Unused declared deps | 35 of 52 in `requirements.txt` (17 imported repo-wide, 9 from `src/`) |
| Manifest installable | **No** — `microsoft-presidio` (`:67`) 404s on PyPI; `pytest` undeclared |
| Quantum objective value | Never computed by anything; `compute_optimality_gaps` defaults it to `0.0` |
| Classical baselines in demo | Fabricated inline at `main.py:432-447` (`objective_value: 0.65`) |
| `log_experiment` call sites | All 3 pass one dict to a 4-argument method — `TypeError` every time |
| SCAFFOLDING.md coverage | Silent on the registry service and on the HPO service's invented GP provenance |
| `src/optimization/qaoa.py` | Zero callers, zero collected tests; 57 tests hidden by `pytest.ini` |
| Tracked scratch | 54 of 127 tracked files are `.spark-flow/`, incl. a binary `memory.sqlite` |
| Container path | `docker-compose.yml:142` mounts a `monitoring/` dir that does not exist |

## Steps

1. `git fetch` and report whether the tree is behind `origin/main`, and whether
   it is dirty.
2. Run the suite on a Python 3.11 interpreter and report passed/failed/skipped
   with the actual `qiskit`, `mitiq` and `cvxpy` versions resolved. **If `mitiq`
   reports version `0.0.0`, the environment is wrong, not the code** — that is a
   placeholder release pip falls back to on 3.12+, and it has no `mitiq.zne`
   submodule. Say so rather than reporting six ZNE failures.
3. Run `python main.py` and report, per pipeline, whether it completed or raised
   — and separately, what the closing status block claims. Report both numbers
   even when they disagree. Especially when they disagree.
4. Check each open claim from the table:
   - `python -m py_compile main_orchestrator.py` — **on a 3.11 interpreter**; it compiles
     clean on 3.12+, so checking with the system python proves nothing
   - `grep -rn "raise NotImplementedError" src/`
   - whether `services/` still exists
   - whether anything outside `tests/` calls `run_baseline`
   - whether `.github/workflows/` exists
   - whether `requirements.txt` declares a `python_requires` equivalent, and whether
     `pip install -r requirements.txt` resolves at all
   - whether `compute_optimality_gaps` still defaults the quantum objective to `0.0`
   - whether `main.py:432-447` still fabricates the classical results
   - whether any `log_experiment` call site matches the method's signature
5. Read `SCAFFOLDING.md` and report any row whose status no longer matches the
   code — in either direction. A component that has quietly become real is drift
   too, and it is the kind that makes the honest document look alarmist.

## Output

A delta table — metric, baseline, now, direction — then a list of claims in
`README.md`, `SCAFFOLDING.md` or `config/settings.json` that are no longer
accurate. Do not edit any file; this command only reports.
