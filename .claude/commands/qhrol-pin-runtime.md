---
description: Do next — pin the Python version, trim the manifest to what installs, fix the silent mitiq trap on 3.12+, and add the CI that protects every later change.
allowed-tools: Bash, Read, Edit, Write, Grep, Glob
---

## Task

This repository has no CI (`.github/` does not exist) and no *enforced* Python version
constraint — there is no `pyproject.toml` or `setup.py`. The README now states 3.11 in
prose, but nothing makes that true at install time, and `requirements.txt` still cannot be
installed at all. Both gaps cost real time to rediscover.

## The mitiq trap, which is the sharp one

`requirements.txt` asks for `mitiq>=0.16.0`. On Python 3.12+ **every** real
release fails to build (they pin a numpy that cannot compile on 3.13:
`AttributeError: module 'pkgutil' has no attribute 'ImpImporter'`). Pip does not
stop — it falls back to `mitiq 0.0.0`, a placeholder release that installs
cleanly, imports, reports a version, and contains three modules and no
`mitiq.zne`.

### The paradox this creates

**Resolved in `4971088`.** `mitiq` forces the interpreter below 3.12, while
`main_orchestrator.py:114` (deleted) used a multi-line f-string expression that is a `SyntaxError`
before 3.12 (PEP 701 legalised it there). No single interpreter satisfied both. Since
`mitiq` is a hard external constraint and that file had never run, the file is what gave.
Recorded here because the pin only makes sense with the reason attached — and because a
future file with the same construct would silently reintroduce it on 3.12+.

### The manifest has never installed

Separately, `requirements.txt` cannot be installed by anyone, on any interpreter:
`microsoft-presidio` (`:67`) does not exist on PyPI — it 404s; the real package is
`presidio-analyzer`. And `pytest` is not declared at all, though the suite cannot run
without it. Any CI job that starts `pip install -r requirements.txt` will fail on line 67
before it reaches a single test.

### The symptom

The result is that `tests/test_zne_end_to_end.py` fails six tests with
`ModuleNotFoundError: No module named 'mitiq.zne'`, which reads as a broken
repository. It is not: on Python 3.11 the suite is **79 passed, 0 failed** —
against qiskit 2.5.2 and mitiq 1.0.0, both newer than the pins.

Nothing in the repository tells a reader this. That is the whole defect.

## Steps

1. Declare the supported interpreter. Add a `pyproject.toml` with
   `requires-python = ">=3.10,<3.12"`, so pip enforces what the README asserts.
2. **Trim the manifest to what installs and what is imported.** It declares 52 packages,
   of which nine are imported from `src/`; the shrink deleted everything that pulled in
   the rest. Remove `microsoft-presidio` outright — it does not exist on PyPI — and add
   `pytest`, which the suite needs and which was never declared. The result should be
   roughly ten packages.
3. Add an install-time guard against the placeholder: pin `mitiq>=0.16,!=0.0.0`,
   and add a test asserting `mitiq.zne.scaling.fold_global` imports. A dependency
   that silently degrades to a stub is worth one line of test.
4. Add `.github/workflows/ci.yml`:
   - matrix on 3.10 and 3.11
   - `python -m compileall -q .` — **on the 3.11 job specifically**. It is clean today,
     but it guards against reintroducing a 3.12-only construct; on a 3.12+ job it would
     pass over exactly that and prove nothing.
   - `python -m pytest -q`
   - `PYTHONPATH=. python examples/qoptisolve_usage.py` as a smoke check — currently the
     only runnable entry point, and it needs `PYTHONPATH` set, which is worth catching if
     that ever changes.
5. Record the verified environment somewhere a reader will find it — the actual
   resolved versions the suite passes against, not the floor pins. `qiskit 2.5.2,
   mitiq 1.0.0, cvxpy 1.9.2, Python 3.11.16` as of 2026-08-30.
6. Note in the README that `mitiq` pulls `cirq`, whose Qiskit conversion needs
   `ply` — already correctly noted in `requirements.txt`; make sure that comment
   survives any dependency cleanup, since it documents a failure that only
   appears at point of use.

## Acceptance

- `pip install -r requirements.txt` succeeds on a clean 3.11 checkout — it does not today —
  and the suite runs green. Do not gate on the number 79; later commands add test files, so
  the count will legitimately exceed the baseline.
- An install on 3.13 fails loudly at install or at test collection, naming the
  interpreter — it does not produce six confusing ZNE failures.
- CI runs on push and fails on a file that does not compile.
- The README's stated prerequisites match what CI proves.

## Ordering

Do this next. The shrink deleted everything that imported the heavy half of the manifest,
so the real dependency set is now roughly ten packages — this is much smaller than it was
when the command was written, and it unblocks CI, which protects every later change.

## Commit convention

Imperative, in the existing style — e.g. "Pin the interpreter the tests actually
pass on". **No `Co-Authored-By` or `Claude-Session` trailers.**
