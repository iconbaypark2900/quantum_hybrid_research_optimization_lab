---
description: Wave 1 — remove the ImportError handler that silently swaps all seven services for an empty MockService when one optional dependency is missing.
allowed-tools: Bash, Read, Edit, Write, Grep, Glob
---

## Task

`main.py:127-145` catches `ImportError` around service construction and replaces
**every** service with an empty stub:

```python
except ImportError as e:
    logger.warning(f"Service modules not found, using mock implementations: {e}")
    class MockService:
        def __init__(self, **kwargs):
            pass
    ...
    logger.info("✅ Mock services created for demonstration purposes")
```

`MockService` has no methods. It exists only to be non-`None`, which is exactly
what `get_system_status()` counts — so the mock path reports **7/7 services
active, status operational**, then dies with `AttributeError` on first use.

## Why it triggers, which is the real problem

`src/experiment_registry_rag_service/service.py:10` imports `mlflow` at module
scope. `mlflow` is not needed to solve a Max-Cut instance, run ZNE, or execute a
circuit on Aer. But one missing import anywhere in the service package takes down
the construction of all seven, and the handler converts that into a
demonstration that appears to work.

Verified: on an environment with qiskit, qiskit-aer, mitiq and cvxpy but no
`mlflow`, the entire lab runs as empty mocks and announces itself operational.

## Steps

1. Delete the `MockService` fallback outright. A missing dependency must surface
   as the `ImportError` it is, naming the module.
2. Check the other mock-return paths this handler was propping up — e.g.
   `define_problem` returns `{"status": "mocked", "canonical_form": "mock_form"}`
   when its service is `None`. Grep `main.py` for `mock` and remove each one. A
   pipeline with no service behind it must raise, not return a shaped placeholder
   with a `mock_` prefix that a caller may never inspect.
3. Make the heavy, optional dependencies actually optional rather than
   collectively fatal:
   - Move `import mlflow` and `from langfuse import Langfuse` in
     `src/experiment_registry_rag_service/service.py` inside the methods that use
     them, or guard them and have the service raise a clear error on use.
   - Confirm nothing else in `src/` imports a tracking/serving dependency at
     module scope: `grep -n "^import \|^from " src/*/service.py`.
4. Construct services independently so one failure does not cascade. If the
   registry service cannot be built, the other six should still run and the
   status report should say which one is absent and why.
5. Add a regression test: with `mlflow` unimportable (monkeypatch
   `sys.modules['mlflow'] = None`), constructing the lab must raise or report the
   registry service as unavailable — and must **not** report seven active
   services.

## Acceptance

- `python main.py` in an environment without `mlflow` either fails loudly naming
  `mlflow`, or runs the six services that do not need it and says so.
- No code path in `main.py` returns a dict whose `status` is `"mocked"`.
- `grep -n "MockService" main.py` returns nothing.
- Full suite green: `python -m pytest`.

## Ordering

Land this with or right after `/qhrol-honest-orchestrator` — they are the two
halves of the same defect, and this one is only visible because that one counts
constructors. They are separate commits.

## Commit convention

Imperative, in the existing style — e.g. "Let a missing dependency fail instead
of mocking the whole lab". **No `Co-Authored-By` or `Claude-Session` trailers.**
