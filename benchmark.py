#!/usr/bin/env python3
"""Run the quantum-vs-classical Max-Cut benchmark this lab is named after.

Build an instance, solve it exactly, run QAOA on Aer with and without
zero-noise extrapolation, and report the comparison with its provenance.

This replaces a demo harness that reported "Phase 1 Implementation Complete"
and seven active services while two of its three pipelines were raising, and
which invented the classical side outright -- a loop that logged "Running
classical algorithm: milp", reported status "completed", and returned a
hardcoded objective_value of 0.65.

So the rules this script follows are not style preferences. Each corresponds to
a specific failure recorded in SCAFFOLDING.md:

  - No `.get(key, default)` on a measured quantity. If it was not computed,
    raise. The old comparison read the quantum objective with a default of 0.0.
  - No mock or placeholder values under any condition -- not behind an
    ImportError, not behind a None check. A missing dependency fails and names
    itself.
  - The summary derives from what ran. Nothing is printed unconditionally.
  - Every quantum number is reported with its shots and seed.
"""

import argparse
import asyncio
import json
import time

from src.error_mitigation_service.service import ErrorMitigationService
from src.hybrid_baseline_service.service import HybridBaselineService
from src.optimization.canonical import maxcut_to_qubo
from src.optimization.classical import ClassicalMaxCutSolver
from src.optimization.objective import cut_observable, objective_from_counts
from src.optimization.problems import create_sample_maxcut
from src.optimization.qaoa import QAOA


async def run(n_nodes: int, edge_prob: float, seed: int, depth: int,
              shots: int, noise_level: float, max_iter: int) -> dict:
    problem = create_sample_maxcut(n_nodes=n_nodes, edge_prob=edge_prob, seed=seed)
    qubo = maxcut_to_qubo(problem)

    # --- classical, both real and both timed ------------------------------
    baselines = HybridBaselineService()
    spec = {"edges": problem.edges, "weights": problem.weights,
            "n_nodes": problem.n_nodes}
    exact = await baselines.run_baseline(spec, "milp")
    heuristic = await baselines.run_baseline(spec, "heuristics", seed=seed)
    annealed = await baselines.run_baseline(spec, "metaheuristics", seed=seed)

    # --- quantum ----------------------------------------------------------
    qaoa = QAOA(shots=shots)
    t0 = time.perf_counter()
    qaoa_result = qaoa.solve_maxcut(problem, p=depth, max_iter=max_iter)
    qaoa_seconds = time.perf_counter() - t0

    quantum = objective_from_counts(
        qaoa_result["counts"], qubo,
        seed=seed, depth=depth, shots=shots, backend=qaoa.backend_name,
        optimizer_iterations=max_iter, optimizer=qaoa_result["optimizer"],
        warm_start=qaoa_result["warm_start"], noise_model="none (ideal Aer)",
        mitigation="none", runtime_seconds=qaoa_seconds,
    )

    # --- the same observable, under noise, with ZNE ------------------------
    # The mitigation path defaults its observable to bitstring parity, which is
    # right for the Bell-state validation and meaningless for Max-Cut. Passing
    # the cost observable is what points it at the actual Hamiltonian.
    circuit = qaoa.create_maxcut_circuit(problem, p=depth)
    bound = circuit.assign_parameters(
        {p: v for p, v in zip(circuit.parameters, qaoa_result["optimal_params"])})
    mitigated = await ErrorMitigationService().apply_mitigation(
        {}, "zne",
        circuit=bound, observable=cut_observable(qubo),
        scale_factors=(1, 3, 5), noise_level=noise_level, shots=shots,
    )
    if mitigated.get("status") == "failed":
        raise RuntimeError(f"mitigation failed: {mitigated}")

    # --- compare -----------------------------------------------------------
    comparison = await baselines.compute_optimality_gaps(
        quantum, [exact, heuristic, annealed])

    return {
        "problem": {"n_nodes": problem.n_nodes, "n_edges": len(problem.edges),
                    "seed": seed, "edge_prob": edge_prob},
        "classical": {
            "exact_milp": {"objective_value": exact["result"]["objective_value"],
                           "runtime_seconds": exact["result"]["runtime_seconds"]},
            "greedy": {"objective_value": heuristic["result"]["objective_value"],
                       "runtime_seconds": heuristic["result"]["runtime_seconds"]},
            "annealing": {"objective_value": annealed["result"]["objective_value"],
                          "runtime_seconds": annealed["result"]["runtime_seconds"]},
        },
        "quantum": quantum,
        "zne": {
            "noise_level": noise_level,
            "scale_factors": [1, 3, 5],
            "noisy_expectation_at_each_factor":
                mitigated["mitigated_results"]["noise_scaled_values"],
            "zero_noise_estimate":
                mitigated["mitigated_results"]["average_objective_value"],
            "note": "expectation of the cut observable, not bitstring parity",
        },
        "comparison": comparison,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--n-nodes", type=int, default=6)
    ap.add_argument("--edge-prob", type=float, default=0.6)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--depth", type=int, default=1, help="QAOA depth p")
    ap.add_argument("--shots", type=int, default=2048)
    ap.add_argument("--noise-level", type=float, default=0.02)
    ap.add_argument("--max-iter", type=int, default=30)
    args = ap.parse_args()

    report = asyncio.run(run(args.n_nodes, args.edge_prob, args.seed,
                             args.depth, args.shots, args.noise_level,
                             args.max_iter))
    print(json.dumps(report, indent=2, default=float))

    c = report["comparison"]
    q = report["quantum"]
    print(f"\nexact optimum      {report['classical']['exact_milp']['objective_value']:.4f}"
          f"   (MILP, brute-force verified)"
          f"\ngreedy heuristic   {report['classical']['greedy']['objective_value']:.4f}"
          f"\nannealing          {report['classical']['annealing']['objective_value']:.4f}"
          f"\nQAOA expectation   {q['objective_value']:.4f} +/- {q['standard_error']:.4f}"
          f"   ratio {q['objective_value'] / report['classical']['exact_milp']['objective_value']:.3f}"
          f"   ({q['shots']} shots, seed {q['provenance']['seed']}, p={q['provenance']['depth']})"
          f"\nQAOA best sample   {q['best_sampled_value']:.4f}"
          f"   (max over shots -- improves with shots regardless of circuit quality)"
          f"\nZNE zero-noise     {report['zne']['zero_noise_estimate']:.4f}"
          f"   (cut observable at {report['zne']['noise_level']:.0%} depolarising)"
          f"\n\n{c['interpretation']}"
          f"\nuncertainty: {c['uncertainty']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
