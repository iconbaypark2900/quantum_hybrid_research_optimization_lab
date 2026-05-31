# Integration Plan: qOptiSolve → quantum_hybrid_research_optimization_lab

## Status

- Source project: `qOptiSolve`
- Target project: `quantum_hybrid_research_optimization_lab`
- Merge policy: `merge_optimization_algorithms`
- Domain: `quantum_hybrid_optimization`
- Migration inbox: `migration_inbox/qOptiSolve`
- Generated: Sat May 30 09:18:31 PM EDT 2026

## Goal

Integrate useful capabilities from `qOptiSolve` into `quantum_hybrid_research_optimization_lab` without blindly copying scaffolding, duplicate configs, generated artifacts, or obsolete app shells.

## Recommended integration strategy

1. Treat `migration_inbox/qOptiSolve` as a read-only reference snapshot.
2. Review docs and technical papers first.
3. Extract algorithms, domain models, utilities, and tests into target-native modules.
4. Do not import duplicate project scaffolding directly unless the target lacks it.
5. Keep source project archived only after target integration is validated.

## Candidate assets to review

See:

- `docs/merge_plans/qOptiSolve_inventory.md`

## Integration checklist

### Documentation

- [ ] Review source README and technical papers.
- [ ] Move useful architecture notes into target docs.
- [ ] Add a short "Imported from qOptiSolve" note to target docs if useful.

### Source code

- [ ] Identify reusable modules.
- [ ] Decide target-native module location.
- [ ] Copy only selected code, not full app scaffolding.
- [ ] Rename imports and package names to target conventions.
- [ ] Remove duplicated CLI/app entrypoints unless needed.

### Tests

- [ ] Identify source tests worth preserving.
- [ ] Port tests into target test framework.
- [ ] Run target test suite.
- [ ] Add regression tests for imported behavior.

### Dependencies

- [ ] Compare source dependency files with target dependencies.
- [ ] Add only missing runtime dependencies.
- [ ] Avoid duplicate package managers or environment files.

### Security/privacy

- [ ] Confirm no secrets, local env files, or private keys were staged.
- [ ] Review PDFs/sample data for sensitive content before publishing.
- [ ] Remove generated outputs if not needed.

### Finalization

- [ ] Commit integrated target-native code.
- [ ] Leave `migration_inbox/qOptiSolve` until integration is validated.
- [ ] Mark source repo as `merged_to_quantum_hybrid_research_optimization_lab` in Liaison registry.
- [ ] Archive source repo after review.

## Suggested first extraction

Start with optimization modules:

- `src/qoptisolve/classical.py`
- `src/qoptisolve/problems.py`
- `src/qoptisolve/qaoa.py`
- `tests/test_qaoa.py`
- `tests/test_problems.py`
- `examples/basic_usage.py`

Target likely areas:

- classical optimization baselines
- QAOA problem formulation
- optimization test cases
- quantum-hybrid examples
