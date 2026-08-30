---
description: Wave 2 — the two services the honesty pass never reached: the registry has no SCAFFOLDING row and plants a fabricated accuracy, and the HPO service reports a Gaussian process it does not have.
allowed-tools: Bash, Read, Edit, Write, Grep, Glob
---

## Task

`SCAFFOLDING.md` accounts for five of the seven services. Two were never examined, and
both fabricate.

## 1. The experiment registry — 459 lines, zero rows in SCAFFOLDING.md

`grep -ci "experiment_registry" SCAFFOLDING.md` returns **0**. It appears in neither the
not-implemented table nor the "genuinely real" list, so a reader has no signal either way
about the service that is supposed to be the lab's record of what it ran.

Three defects:

- **It has never been called successfully.** `log_experiment` takes four required
  positional arguments (`src/experiment_registry_rag_service/service.py:37-44`:
  `experiment_name`, `run_name`, `parameters`, `metrics`). All three call sites pass a
  single dict — `main.py:260`, `:366`, `:477` — so every one raises
  `TypeError: log_experiment() missing 3 required positional arguments`. The lab's
  experiment record is empty and always has been.
- **A keyword tally is reported as confidence.** `:230` returns
  `min(0.95, sum(relevance_score) / 10.0)` as `"confidence"`. That is a normalised
  keyword-overlap count wearing the name of a calibrated probability.
- **The health check plants a fake result.** `:436` logs a run with
  `metrics={"accuracy": 0.95}` into the registry — which the RAG path then retrieves and
  answers questions from. A self-test that writes fabricated data into the corpus it later
  searches is a fabrication that compounds.

## 2. The HPO service — invented provenance

`SCAFFOLDING.md` says of this service: *"Its randomness is algorithmic (mutation,
crossover, tournament selection), not fabricated results, and should be left alone."*
That is right about the genetic algorithm and wrong about the Bayesian path.

`src/hpo_evolution_service/service.py:144-148` returns:

```python
"algorithm_specific_params": {
    "acquisition_function": "expected_improvement",
    "gp_kernel": "matern",
    "exploration_exploitation_balance": "adaptive",
}
```

There is no Gaussian process anywhere in `src/`. No Matérn kernel, no acquisition
function. The method's own log line says "Running simulated Bayesian Optimization" and its
docstring describes random sampling with an improvement bias. A caller reading
`algorithm_specific_params` would reasonably cite the method in a paper.

This is the repository's rule applied to **strings** rather than floats: the values are
not random numbers, but a reader takes them as a description of what ran, and they are
not.

## Steps

1. Fix the three `log_experiment` call sites to the real signature, or change the
   signature to take the dict the callers already build. Either is defensible; pick one
   and make the call sites and the definition agree.
2. Add a test that the demo path writes at least one experiment and can read it back. A
   `TypeError` on every call for the life of the project is what an untested integration
   point looks like.
3. Rename `confidence` to what it is (`keyword_overlap_score`, or similar), or compute
   something that earns the name. Do not leave a `0.0-0.95` field called confidence beside
   retrieval results.
4. Remove the fabricated `accuracy: 0.95` from the health check, or write it to a
   namespace the RAG path provably excludes. A smoke test must not contaminate the corpus.
5. Delete `algorithm_specific_params`, or implement Optuna's TPE/GP sampler — it is
   already declared in `requirements.txt` and is the obvious answer. Do not hand-write a
   Gaussian process; that is the mistake `SCAFFOLDING.md` records about the ZNE maths,
   which the Mitiq cross-check exists to atone for.
6. **Add rows for both services to `SCAFFOLDING.md`.** This is the part that matters most.
   The document's value is that its coverage can be trusted, and it currently vouches by
   omission for two services that fabricate. Correct the "should be left alone" sentence
   about HPO while you are there — it is the one place that document is wrong.

## Acceptance

- `grep -c "experiment_registry" SCAFFOLDING.md` is non-zero.
- The demo path logs an experiment and reads it back in a test.
- No field named `confidence` or `accuracy` carries a number nothing measured.
- `grep -rn "gp_kernel\|expected_improvement" src/` returns nothing, or returns code that
  really runs a Gaussian process.
- Full suite green.

## Commit convention

Separate commits per service. Imperative, in the existing style — e.g. "Stop reporting a
Gaussian process the optimiser does not have". **No `Co-Authored-By` or `Claude-Session`
trailers.**
