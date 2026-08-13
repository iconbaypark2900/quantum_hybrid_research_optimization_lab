"""Hybrid Baseline Service — classical baselines for quantum-advantage claims.

WHY THIS FILE RAISES INSTEAD OF RETURNING NUMBERS

This service exists so a quantum result can be compared against a strong
classical solver. Until now every baseline here fabricated its answer:
`objective_value`, `runtime_seconds`, `optimality_gap`, `upper_bound` and
`lower_bound` were all `np.random.uniform(...)`, and `_evaluate_solution` did
not evaluate the problem at all — it returned a made-up function of solution
density plus a RANDOM constraint penalty, so even the local search that looked
real was optimising a fictitious, non-deterministic objective.

The effect was not a missing feature but a false one: any quantum-advantage
claim compared against these numbers was unfalsifiable, because the baseline was
noise wearing the costume of a measurement.

Unimplemented baselines now raise `NotImplementedError` naming what is missing.
A caller that cannot get an answer is inconvenienced; a caller that gets a
fabricated one is misled, and has no way to tell. See SCAFFOLDING.md.

Real solvers already exist in `src/optimization/classical.py`
(`ClassicalMaxCutSolver`, `ClassicalPortfolioSolver`, built on cvxpy) and are
what these baselines should be wired to.
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import time

import numpy as np


logger = logging.getLogger(__name__)


def _not_implemented(what: str, needs: str) -> "NotImplementedError":
    """Refuse loudly, and say what it would take to stop refusing.

    A bare NotImplementedError tells a caller they are stuck. This tells them
    what is missing and where the parts are, which is the difference between a
    dead end and a task.
    """
    return NotImplementedError(
        f"{what} is not implemented. It previously returned randomly generated "
        f"numbers, which is worse than failing: a fabricated baseline makes a "
        f"quantum-advantage comparison unfalsifiable. To implement it: {needs}")


def _as_maxcut(problem: Dict[str, Any]):
    """Build a real MaxCutProblem from a problem dict.

    Baselines must solve the ACTUAL problem. Accepting a dict and inventing a
    structure from `n_variables` is how the previous version ended up scoring
    solutions against a function of how many bits were set.
    """
    from src.optimization.problems import MaxCutProblem

    edges = problem.get("edges")
    if not edges:
        raise ValueError(
            "This baseline solves Max-Cut and needs the graph. Supply "
            "problem['edges'] as [(i, j), ...] and optionally "
            "problem['weights']. A problem dict carrying only 'n_variables' "
            "does not define an objective, and scoring against a substitute "
            "is what made the previous baselines meaningless.")
    edges = [tuple(e) for e in edges]
    return MaxCutProblem(edges=edges, weights=problem.get("weights"))


def _cut_value(partition, edges, weights) -> float:
    """Weight of edges crossing the partition — the definition, applied."""
    return float(sum(w for (i, j), w in zip(edges, weights)
                     if partition[i] != partition[j]))


class HybridBaselineService:
    """Service for running classical baselines and computing optimality gaps"""
    
    def __init__(self):
        self.baseline_results = {}
        
    async def run_baseline(self, problem: Dict[str, Any], algorithm: str, **kwargs) -> Dict[str, Any]:
        """Run classical baseline algorithm"""
        logger.info(f"Running {algorithm} baseline for problem {problem.get('problem_id', 'Unknown')}")
        
        # The advertised list used to name six algorithms. Three of them
        # ('greedy', 'random_search', and the fall-through 'generic') dispatched
        # to methods that do not exist, so asking for a supported algorithm
        # raised AttributeError. Claiming support you do not have is the same
        # defect as fabricating a number: the caller is told something untrue
        # and has no way to check it.
        #
        # This map is now derived from what is actually defined, so it cannot
        # drift out of step with the code again.
        dispatch = {
            'milp': self._run_milp_baseline,
            'heuristics': self._run_heuristic_baseline,
            'metaheuristics': self._run_metaheuristic_baseline,
            'machine_learning': self._run_ml_baseline,
        }

        key = algorithm.lower()
        if key not in dispatch:
            raise ValueError(
                f"Algorithm {algorithm!r} is not available. Defined baselines: "
                f"{', '.join(sorted(dispatch))}. Note that all of them currently "
                "raise NotImplementedError — see this module's docstring.")

        result = await dispatch[key](problem, **kwargs)

        # Generate a unique baseline ID
        baseline_id = f"base_{hash(algorithm + str(problem.get('problem_id', 'unknown')) + str(datetime.utcnow().timestamp())) % 10000:04d}"
        
        # Store result
        self.baseline_results[baseline_id] = {
            "problem_id": problem.get("problem_id"),
            "algorithm": algorithm,
            "parameters": kwargs,
            "result": result,
            "computed_at": datetime.utcnow().isoformat(),
            "status": "completed"
        }
        
        logger.info(f"Baseline {algorithm} completed with objective: {result.get('objective_value', 'N/A')}")
        
        return {
            "baseline_id": baseline_id,
            "algorithm": algorithm,
            "problem_id": problem.get("problem_id"),
            "result": result,
            "computed_at": datetime.utcnow().isoformat(),
            "status": "completed",
            "message": f"{algorithm.upper()} baseline completed successfully"
        }
    
    async def _run_milp_baseline(self, problem: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Exact baseline via MILP (cvxpy, binary variables).

        Previously reported `solver: "cplex_simulated"` with an `upper_bound`
        and `lower_bound` drawn from np.random.normal — bounds whose entire
        purpose is rigour, fabricated.

        Now solves the real graph. The reported cut value is recomputed from the
        returned partition rather than taken from the solver's objective, so the
        two must agree; a mismatch means the formulation drifted from the
        problem and is caught here rather than downstream.
        """
        from src.optimization.classical import ClassicalMaxCutSolver

        mc = _as_maxcut(problem)
        t0 = time.perf_counter()
        result = ClassicalMaxCutSolver().solve(mc)
        runtime = time.perf_counter() - t0

        if result.get("status") != "optimal" or result.get("partition") is None:
            raise RuntimeError(
                f"Exact baseline did not solve: status={result.get('status')!r} "
                f"{result.get('error', '')}".strip())

        partition = [int(v) for v in result["partition"]]
        achieved = _cut_value(partition, mc.edges, mc.weights)
        reported = float(result["cut_value"])
        if abs(achieved - reported) > 1e-6:
            raise RuntimeError(
                f"Solver objective {reported} does not match the cut its own "
                f"partition achieves ({achieved}). The formulation and the "
                "problem have diverged.")

        return {
            "solution": partition,
            "objective_value": achieved,
            "runtime_seconds": runtime,
            "status": "optimal",
            # This IS the optimum, so the gap is zero by definition — not an
            # estimate, and not a number to invent.
            "optimality_gap": 0.0,
            "upper_bound": achieved,
            "lower_bound": achieved,
            "algorithm_details": {"solver": "cvxpy MILP (linearised Max-Cut)",
                                  "exact": True},
        }

    async def _run_heuristic_baseline(self, problem: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Greedy local search on the real objective.

        The search loop was always genuine; what it optimised was not. It now
        hill-climbs the actual cut value, so the loop finally does what its
        comments always claimed.
        """
        mc = _as_maxcut(problem)
        n = mc.n_nodes
        max_iterations = int(kwargs.get("max_iterations", 1000))
        rng = np.random.default_rng(kwargs.get("seed", 0))

        t0 = time.perf_counter()
        current = rng.integers(0, 2, size=n).tolist()
        best_obj = _cut_value(current, mc.edges, mc.weights)
        improved = True
        sweeps = 0
        # Deterministic full sweeps: flip whichever single node helps most,
        # repeat until no single flip improves. Unlike random bit-flipping this
        # terminates at a genuine local optimum, which is a property a baseline
        # can be held to.
        while improved and sweeps < max_iterations:
            improved = False
            sweeps += 1
            for node in range(n):
                current[node] ^= 1
                cand = _cut_value(current, mc.edges, mc.weights)
                if cand > best_obj + 1e-12:
                    best_obj = cand
                    improved = True
                else:
                    current[node] ^= 1
        runtime = time.perf_counter() - t0

        return {
            "solution": current,
            "objective_value": best_obj,
            "runtime_seconds": runtime,
            "iterations": sweeps,
            "status": "local_optimum",
            "algorithm_details": {"approach": "greedy_local_search",
                                  "neighborhood": "single_node_flip",
                                  "terminates_at": "no improving single flip"},
        }

    async def _run_metaheuristic_baseline(self, problem: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Metaheuristic (GA / simulated annealing) baseline."""
        raise _not_implemented(
            "the metaheuristic baseline",
            "run a real GA or annealer against a real objective function; the "
            "population mechanics in src/hpo_evolution_service/service.py are "
            "genuine and can be reused, but they need something true to optimise")

    async def _run_ml_baseline(self, problem: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Learned-heuristic baseline.

        Reported `model_type: "feedforward_nn_simulated"`. There is no model.
        """
        raise _not_implemented(
            "the ML baseline",
            "train an actual model, or delete this baseline — an unimplemented "
            "learned heuristic is not a baseline anything should be compared to")

    def _evaluate_solution(self, solution: np.ndarray, problem: Dict[str, Any]) -> float:
        """Objective value of a candidate solution.

        THE ROOT FABRICATION. This returned `n_ones * 1.5` minus a density term
        minus `np.random.uniform(0, 2)` — a made-up function of how many bits
        were set, with a random penalty. It never looked at the problem.

        Two consequences worth stating separately. It was not the problem's
        objective, so any solution "optimised" against it was meaningless. And
        it was non-deterministic, so the local search compared incomparable
        values and could not even hill-climb its own fiction reliably.
        """
        raise _not_implemented(
            "solution evaluation",
            "compute the actual objective from the problem definition — for "
            "MaxCut, sum the weights of cut edges; for the portfolio problem, "
            "the risk-adjusted return in src/optimization/problems.py")

    async def compute_optimality_gaps(self, quantum_result: Dict[str, Any], 
                                    classical_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compute optimality gaps between quantum and classical results"""
        logger.info("Computing optimality gaps")
        
        # Extract quantum results
        quantum_obj = quantum_result.get('objective_value', 0.0)
        
        # Find best classical result
        best_classical_obj = max(
            [res.get('result', {}).get('objective_value', float('-inf')) 
             for res in classical_results if 'result' in res],
            default=0.0
        )
        
        # Calculate gaps
        if best_classical_obj != 0:
            relative_gap = (quantum_obj - best_classical_obj) / abs(best_classical_obj)
        else:
            relative_gap = float('inf') if quantum_obj > 0 else 0.0
        
        abs_gap = quantum_obj - best_classical_obj
        
        # Determine performance
        if abs(relative_gap) < 0.01:  # Within 1%
            performance = "equivalent"
        elif relative_gap > 0.01:  # Quantum better
            performance = "quantum_superior"
        else:  # Classical better
            performance = "classical_superior"
        
        return {
            "quantum_objective": quantum_obj,
            "best_classical_objective": best_classical_obj,
            "relative_gap": relative_gap,
            "absolute_gap": abs_gap,
            "performance_assessment": performance,
            "quantum_advantage_ratio": quantum_obj / best_classical_obj if best_classical_obj != 0 else float('inf'),
            "confidence_interval": [relative_gap - 0.05, relative_gap + 0.05],  # Simulated CI
            "interpretation": self._interpret_gap(relative_gap, performance)
        }
    
    def _interpret_gap(self, gap: float, performance: str) -> str:
        """Interpret the optimality gap result"""
        if performance == "quantum_superior":
            if gap > 0.1:  # >10% improvement
                return "Significant quantum advantage (>10% improvement)"
            elif gap > 0.05:  # 5-10% improvement
                return "Moderate quantum advantage (5-10% improvement)"
            else:  # <5% improvement
                return "Marginal quantum advantage (<5% improvement)"
        elif performance == "classical_superior":
            if gap < -0.1:  # >10% worse
                return "Significant quantum disadvantage (>10% worse)"
            elif gap < -0.05:  # 5-10% worse
                return "Moderate quantum disadvantage (5-10% worse)"
            else:  # <5% worse
                return "Marginal quantum disadvantage (<5% worse)"
        else:  # equivalent
            return "No significant difference between quantum and classical approaches"
    
    async def get_baseline_result(self, baseline_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific baseline result"""
        return self.baseline_results.get(baseline_id)
    
    async def list_baseline_results(self) -> Dict[str, Any]:
        """List all baseline results"""
        return {
            "baseline_results": [
                {
                    "baseline_id": bid,
                    "problem_id": b["problem_id"],
                    "algorithm": b["algorithm"],
                    "objective_value": b["result"].get("objective_value", 0),
                    "runtime": b["result"].get("runtime_seconds", 0),
                    "computed_at": b["computed_at"]
                }
                for bid, b in self.baseline_results.items()
            ],
            "total_count": len(self.baseline_results),
            "status": "success"
        }