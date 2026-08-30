---
description: Wave 3 — pin the Python version, fix the silent mitiq trap on 3.12+, and add the CI that would have caught every defect in the other commands.
allowed-tools: Bash, Read, Edit, Write, Grep, Glob
---

## Task

This repository has no CI (`.github/` does not exist) and no *enforced* Python version
constraint — there is no `pyproject.toml` or `setup.py`, and the two places that do state
a version disagree: `Dockerfile:2` builds on `python:3.11-slim` while `README.md:57` says
"Python 3.9+". Both gaps cost real time to rediscover.

## The mitiq trap, which is the sharp one

`requirements.txt` asks for `mitiq>=0.16.0`. On Python 3.12+ **every** real
release fails to build (they pin a numpy that cannot compile on 3.13:
`AttributeError: module 'pkgutil' has no attribute 'ImpImporter'`). Pip does not
stop — it falls back to `mitiq 0.0.0`, a placeholder release that installs
cleanly, imports, reports a version, and contains three modules and no
`mitiq.zne`.

### The paradox this creates

`mitiq` forces the interpreter **below** 3.12. But `main_orchestrator.py:114` uses a
multi-line f-string expression, which is a `SyntaxError` **before** 3.12 (PEP 701 legalised
it in 3.12). No single interpreter satisfies both. Whatever you pin, one of the two has to
be fixed rather than accommodated — and since `mitiq` is a hard external constraint and
`main_orchestrator.py` has never run, the file is what gives. That makes
`/qhrol-entrypoints` a prerequisite for this command's CI job, not an independent cleanup.

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
   `requires-python = ">=3.10,<3.12"`, or at minimum state it at the top of
   `requirements.txt` and in the README prerequisites — which currently say
   "Python 3.9+", a version the repo does not support.
2. Add an install-time guard against the placeholder: pin `mitiq>=0.16,!=0.0.0`,
   and add a test asserting `mitiq.zne.scaling.fold_global` imports. A dependency
   that silently degrades to a stub is worth one line of test.
3. Add `.github/workflows/ci.yml`:
   - matrix on 3.10 and 3.11
   - `python -m compileall -q .` — **on the 3.11 job specifically**. This catches the
     `main_orchestrator.py` `SyntaxError`, which has been in `main` since the first
     commit but only exists below Python 3.12 (see the paradox above). On a 3.12+ job
     the same command exits 0 and proves nothing.
   - `python -m pytest -q`
   - `python main.py` as a smoke check, asserting a non-zero exit or a
     `degraded` status while pipelines fail. Once `/qhrol-honest-orchestrator`
     lands, this is the check that keeps the demo honest.
4. Record the verified environment somewhere a reader will find it — the actual
   resolved versions the suite passes against, not the floor pins. `qiskit 2.5.2,
   mitiq 1.0.0, cvxpy 1.9.2, Python 3.11` as of 2026-08-30.
5. Note in the README that `mitiq` pulls `cirq`, whose Qiskit conversion needs
   `ply` — already correctly noted in `requirements.txt`; make sure that comment
   survives any dependency cleanup, since it documents a failure that only
   appears at point of use.

## Acceptance

- A clean checkout on 3.11 installs from the manifest with no manual intervention and
  runs the suite green. Do not gate on the number 79 — Waves 1 and 2 each add test files,
  so the count will legitimately exceed the baseline by the time this command runs.
- An install on 3.13 fails loudly at install or at test collection, naming the
  interpreter — it does not produce six confusing ZNE failures.
- CI runs on push and fails on a file that does not compile.
- The README's stated prerequisites match what CI proves.

## Ordering

Runs **after** `/qhrol-entrypoints` (the interpreter pin is only coherent once
`main_orchestrator.py` is resolved) and **before** `/qhrol-true-claims`, which rewrites
the same manifest. All three touch `requirements.txt`; this is the one that establishes
`requires-python` and the `mitiq` guard.

## Commit convention

Imperative, in the existing style — e.g. "Pin the interpreter the tests actually
pass on". **No `Co-Authored-By` or `Claude-Session` trailers.**
