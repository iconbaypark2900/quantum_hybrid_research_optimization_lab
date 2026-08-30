---
description: Wave 3 — close the claims the README and requirements.txt make that no code backs: OIDC, OPA, Vault, Presidio, FastAPI, 35 unused dependencies, and a manifest that has never installed.
allowed-tools: Bash, Read, Edit, Write, Grep, Glob
---

## Task

`SCAFFOLDING.md` did this job for the service layer and did it well. The
top-level documents were never given the same treatment, and they now make the
largest set of claims in the repository that nothing implements.

## The claims

**README "Security & Governance"** promises OIDC single sign-on, Open Policy
Agent authorization, HashiCorp Vault secret management, and Microsoft Presidio
PHI detection. Measured across every `.py` in the repository:

| Claim | Files referencing it |
|---|---|
| OIDC | 0 |
| Vault | 0 |
| Presidio | 0 |
| FastAPI / uvicorn | 0 |
| OPA | 0 in `src/` |

There is no API layer at all — no FastAPI app, no routes, no server — though three
of the seven services carry `host` and `port` constructor arguments, and the README
describes all seven as though they were deployed.

**`requirements.txt`** declares 52 dependencies. Seventeen are imported anywhere in
the repository, and only nine from `src/`. The other 35 include `tensorflow`, `torch`,
`dwave-ocean-sdk`, `cplex`, `gurobipy`, `pyquil`, `spacy`, `nltk`, `faiss-cpu`, `neo4j`,
`opensearch-py` and `qdrant-client` — a full stack for a system that does not exist.
Installing it is several gigabytes to run a Max-Cut solver.

**Scaffolding artifacts at the root**: `quantum_hybrid_research_optimization.json`,
`.md` and `.xml`, plus `quantum_hybrid_research_optimization_lab_detailed.pdf` —
generated planning documents that predate the code.

## Steps

1. Rewrite the README's "Security & Governance" section as intent, clearly marked
   as not implemented — or delete it. Do not leave a capability table that reads
   as description. Follow the tone `SCAFFOLDING.md` already sets; it is the best
   writing in this repository and the README should match it.
2. Reconcile the README's architecture section with reality. Seven services
   exist as classes; none is served over a port. Either say so plainly or drop
   the service-and-port framing.
3. Split `requirements.txt` into what is installed and what is intended. Note first that
   **this file has never been installable**: `microsoft-presidio` (`:67`) does not exist on
   PyPI at all — it 404s; the real package is `presidio-analyzer` — and `pytest` is not
   declared anywhere, though the suite cannot run without it. Any "install the manifest"
   acceptance gate was unreachable before this command.
   - **Preferred:** a `pyproject.toml` listing the ~10 real imports, and a short
     "Intended stack" section in the README, prose, marked as not installed.
   - **Alternative:** rename to `requirements-intended.txt` with a header stating
     that nothing installs it, and add a real minimal manifest beside it.
   Either way `docker-compose.yml` and `Dockerfile` must be updated to match, and
   checked to see whether they still describe anything that runs.
4. Read the four root scaffolding artifacts. Fold anything the README lacks into
   it, then delete them. Keep the qOptiSolve technical paper — it documents prior
   work with real content behind it.
   Then deal with `.spark-flow/`: **54 of the 127 tracked files are agent-workflow
   bookkeeping** for two completed tasks, including a tracked 16 KB binary
   `memory.sqlite` that git cannot diff or merge. Decide whether that belongs in the
   repository at all; if it does, it is history and belongs under `docs/`. Extend
   `.gitignore` to cover the app's own runtime output (`mlruns.db`, `mlruns/`,
   `.pytest_cache/`) while you are there.
5. Correct `SCAFFOLDING.md`'s own vouching. Its "What is genuinely real" list names
   `migration_inbox/qOptiSolve/` as "prior work with its own tests" — but that tree still
   contains the **exact non-solving Max-Cut solver** the same document holds up as its
   most instructive failure (`classical.py:135`, the bilinear objective cvxpy rejects),
   and its tests mock cvxpy so they pass over it. A document whose credibility rests on
   accurate coverage cannot vouch for code it elsewhere describes as broken.

6. Decide what `migration_inbox/qOptiSolve/` is now. Its code was integrated into
   `src/optimization/` in `1f8aca7`; leaving the original beside the integrated
   copy is the same duplicate-tree problem `services/` created, and it carries a
   second test suite over the superseded copy.
7. Add a `tests/test_config_honesty.py`-style check, as
   `medical_evidence_graph_outcomes_lab` did: assert that anything
   `config/settings.json` lists as enabled is reachable, so a config entry cannot
   quietly outlive its implementation. `config/settings.json` currently advertises
   an `ibm_quantum` QPU backend and four classical algorithms, two of which raise.

## Acceptance

- Every capability the README states in the present tense is either implemented
  or marked as intended.
- `pip install -r <the real manifest>` is enough to run the suite green. Do not gate on
  the number 79 — Waves 1 and 2 each add test files, so the count will legitimately exceed
  the baseline by the time this runs.
- The repository root lists only files a first-time reader needs.
- `grep -rin "oidc\|vault\|presidio" README.md` returns nothing, or returns only
  text inside an explicitly-marked "not implemented" section.
- Full suite green: `python -m pytest`.

## Ordering

Runs **after** `/qhrol-pin-runtime`, which also rewrites the dependency manifest. Preserve
what it establishes: `requires-python`, the `mitiq` placeholder guard, and the CI job. The
two commands collide head-on in `requirements.txt` if run in the other order.

## Commit convention

Separate commits, one per section, describing the claim being closed rather than
the file being edited — e.g. "Retire the dependency manifest nothing installs".
**No `Co-Authored-By` or `Claude-Session` trailers.**
