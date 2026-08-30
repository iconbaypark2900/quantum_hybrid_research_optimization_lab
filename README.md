# Quantum Hybrid Research & Optimization Lab

A small library of **verified** quantum-classical optimization components: exact and
heuristic Max-Cut baselines, zero-noise extrapolation checked against Mitiq, and circuit
execution on Qiskit Aer. Every number this repository reports is computed. Where something
is not implemented, it raises rather than returning a plausible value.

That second sentence is the whole point, and it was expensive to earn.

## What happened here

This began as a seven-service platform — problem definition, circuit generation, execution,
error mitigation, classical baselines, hyperparameter search, and an MLflow-backed
experiment registry with retrieval. Most of it did not work, and the parts that did not
work returned numbers anyway.

The clearest example: the headline Max-Cut solver had never solved anything. Its objective
was bilinear, so cvxpy rejected it as non-DCP; the solver caught the exception, warned, and
returned `{'cut_value': None, 'status': 'error'}`. **The test suite passed regardless**,
because the tests asserted on shape and status and never on a cut being found. A headline
solver that had never solved, with green tests over it, for as long as it existed.

Fixing that took a change of method, not of code: only an oracle distinguishes a working
solver from a broken one. `tests/test_baselines_oracle.py` now enumerates every partition
for n = 4..8 and checks the solver against brute force.

The rest of the platform was then measured the same way and mostly failed. Rather than
repair seven services, this repository was **shrunk to what is verified**. The deleted code
is in git history at `4971088`; `SCAFFOLDING.md` records what it faked and why it went.

## What is actually here

| Component | Status |
|---|---|
| `src/optimization/problems.py` | Real Max-Cut and portfolio structures, seeded and deterministic |
| `src/optimization/classical.py` | Exact Max-Cut via MILP linearisation, verified against brute force for n = 4..8; real greedy heuristics |
| `src/optimization/canonical.py` | Max-Cut and portfolio to QUBO/Ising, verified by enumeration against two independent oracles |
| `src/optimization/objective.py` | Measured counts reduced through the cost Hamiltonian to an expectation, with a real standard error |
| `src/error_mitigation_service/zne.py` | Richardson and least-squares extrapolation, unitary folding — agrees with Mitiq to 2.66e-15 |
| `src/error_mitigation_service/service.py` | Closed-loop ZNE: folds, executes each scale factor, extrapolates |
| `src/execution_orchestrator_service/service.py` | Aer execution with an optional depolarising noise model |
| `src/hybrid_baseline_service/service.py` | MILP and heuristic baselines are real; metaheuristic and ML raise |
| `src/optimization/qaoa.py` | Max-Cut and portfolio circuits, both built from the QUBO's Ising form so circuit and objective cannot disagree; both recover the brute-force optimum |

**216 tests, all passing.** Verified on Python 3.11.16 against qiskit 2.5.2, mitiq 1.0.0
and cvxpy 1.9.2, and on Python 3.10.21 against qiskit 2.4.2 and mitiq 0.47.0 — the pins in
`pyproject.toml` are floors, and these are what actually resolved.

Two results worth quoting, because they are measurements rather than claims. On an
exponentially decaying signal, extrapolation reduces error against ground truth from 0.139
to 0.0027. On a Bell state under 3% depolarising noise, closed-loop ZNE lands within 0.0007
of the analytic parity against 0.029 unmitigated — roughly 40x closer.

One correctness requirement, learned the hard way: **execution must transpile at
`optimization_level=0`.** The default optimiser cancels the adjacent inverse gate pairs that
unitary folding inserts, so every scale factor collapses to the same circuit, noise is never
amplified, and ZNE reports a confident value extrapolated from three measurements of one
circuit. No amount of extrapolation mathematics catches that — the values are
self-consistent and the fit exact. Only the physical invariant does: a circuit with more
noisy operations must measure worse. It is asserted in `tests/test_zne_end_to_end.py` and
verified to fail when the optimisation level is restored.

## Quick Start

### Prerequisites

**Python 3.10 or 3.11.** Both are verified in CI; they resolve different qiskit and mitiq
releases and the suite passes on each. 3.12 and later will not work, and this is enforced
at install time rather than documented and hoped for:

```
ERROR: Package 'quantum-hybrid-research-optimization-lab' requires a different Python:
3.13.13 not in '<3.12,>=3.10'
```

The reason is `mitiq`. On 3.12+ every real release fails to build, and pip does not stop —
it falls back to a placeholder `mitiq 0.0.0` that installs cleanly, imports, reports a
version, and contains no `mitiq.zne`. Six tests then fail in a way that reads as broken
code rather than a broken environment. `tests/test_environment.py` says so in one line
instead.

```bash
git clone https://github.com/iconbaypark2900/quantum_hybrid_research_optimization_lab.git
cd quantum_hybrid_research_optimization_lab

python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt        # editable install; dependencies live in pyproject.toml

python -m pytest                       # 216 tests
python examples/qoptisolve_usage.py    # portfolio + Max-Cut, real output
python benchmark.py                    # the quantum-vs-classical comparison
```

`benchmark.py` is the entry point: it builds a Max-Cut instance, solves it exactly,
runs QAOA on Aer with and without zero-noise extrapolation, and reports the comparison
with its provenance — seed, shots, depth, backend, noise model.

## What is not implemented

`SCAFFOLDING.md` is the authoritative list — what each component faked, what it would take
to make it real, and which fabrications have since been closed. It is written to be read
before trusting anything here.

Still open: PEC, CDR and VNLE raise rather than pretend, as do the metaheuristic and
machine-learning baselines. QAOA runs at fixed depth with a simple optimiser and is not
competitive with the exact solver — the benchmark reports that plainly rather than
selecting a framing where it wins.

## Drift detection

`tests/test_repository_claims.py` asserts the invariants this repository claims, rather
than leaving them to a checklist someone has to remember. It fails if a measured quantity
is ever read with a numeric default again, if a source module stops being reachable from
any test, if the interpreter bound leaves `pyproject.toml`, or if a second dependency
manifest appears. Each of those corresponds to a defect that shipped here and survived for
months.

## License

Apache-2.0. See `LICENSE`.
