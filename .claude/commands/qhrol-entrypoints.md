---
description: Wave 1 — the entry point the README tells you to run has never compiled. Settle the two entry points and delete the duplicate service tree.
allowed-tools: Bash, Read, Edit, Write, Grep, Glob
---

## Task

`README.md:83` — step 4 of Quick Start — says:

```bash
python main_orchestrator.py
```

That file does not parse:

```
File "main_orchestrator.py", line 114
    logger.info(f"All services initialized: {len([s for s in [
                ^
SyntaxError: unterminated string literal (detected at line 114)
```

`SCAFFOLDING.md` records this file as unrunnable "regardless (needs `pydantic`)".
That is the wrong diagnosis — its imports (`main_orchestrator.py:5-10`) are stdlib only,
so `pydantic` was never the blocker.

**The failure is interpreter-dependent, and that is what makes it dangerous.**
`main_orchestrator.py:114` opens an f-string whose expression spans several lines.
PEP 701 legalised that in **Python 3.12**; before 3.12 it is a `SyntaxError`. So:

| interpreter | `py_compile main_orchestrator.py` |
|---|---|
| 3.11 | **SyntaxError** at line 114 |
| 3.12, 3.13, 3.14 | compiles clean |

Now combine that with `/qhrol-pin-runtime`: `mitiq` cannot be installed on 3.12+, and
`Dockerfile:2` already pins `python:3.11-slim`. **No interpreter satisfies both the
repository's syntax floor and its dependency ceiling.** On every interpreter this project
can actually run on, its README's Quick Start step 4 does not parse — and on the modern
interpreter a casual reader reaches for, the file looks perfectly fine. It is byte-identical
to the version added in the first commit, `a88c838`.

## The situation

- `main.py` — compiles everywhere, imports `src/`, is the real entry point.
- `main_orchestrator.py` — parses only on 3.12+; unrunnable on the supported 3.11.
  It is also the **only** non-test caller of `run_baseline` (`:352`), the exact MILP
  solver — so the repository's one real classical solver is reachable exclusively from a
  file that cannot execute.
- `services/*.py` — an older copy of all seven services. Every module raises
  `ImportError` on import, pointing at `src/`. Confirmed: the duplicate ZNE
  implementation there flattens the distribution rather than sharpening it — it
  is not merely redundant, it is wrong.

## Steps

1. Decide the fate of `main_orchestrator.py`, and prefer deletion. Read it first
   and check whether it holds any pipeline `main.py` lacks — the `run_*_pipeline`
   names in the README's usage examples come from it. Fold anything worth keeping
   into `main.py`; do not repair 28 kB of never-executed code to preserve a
   second entry point nobody has run.
2. If it is kept instead, it must compile **on 3.11** and be exercised by a test in the
   same commit. Note that keeping it makes step 3 unsatisfiable as written:
   `main_orchestrator.py:67-73` is the only thing in the repository that imports
   `services/`, and every module there raises `ImportError` by design. So the "keep it"
   branch also requires repointing those seven imports at `src/` and reconciling the
   constructor signatures. Prefer deletion; if you keep it, do that work in the same
   commit or step 3 cannot proceed.
3. Delete `services/`. The guard commit deliberately left it raising `ImportError`
   rather than removing it, because the live entry point imported it and could
   not be run to verify the change. Once step 1 lands, that reason is gone.
   `grep -rn "from services\|import services" .` must come back empty first.
4. Reconcile the README Quick Start with what exists:
   - the `git clone` line still says `your-org`
   - step 4 must name the entry point that runs
   - the usage examples call `QuantumHybridOrchestrator`; check that class exists
     under that name and that each method shown is real
5. Add `python -m compileall` over every tracked `.py` to the test suite or to CI —
   **pinned to a 3.11 interpreter**. On 3.12+ it exits 0 over this repository today and
   proves nothing. This defect survived three months and two documentation passes because
   nothing ever asked the file to parse, and it will survive a CI job that runs on the
   wrong interpreter for exactly the same reason.

## Acceptance

- Every tracked `.py` compiles **on Python 3.11**: `python3.11 -m compileall -q .` is
  clean. (It is already clean on 3.12+, so running it there is not a check.)
- The command in README Quick Start step 4 runs and produces the status report.
- `services/` is gone, and nothing references it.
- Full suite green: `python -m pytest`.

## Commit convention

Separate commits — retiring the dead entry point and deleting the duplicate tree
are independently reviewable. Imperative, in the existing style. **No
`Co-Authored-By` or `Claude-Session` trailers.**
