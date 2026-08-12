"""DEPRECATED DUPLICATE — do not import. See src/hybrid_baseline_service/service.py.

This tree is a second, older copy of every service. `main.py` imports the
canonical implementations from `src/<name>_service/service.py`; only
`main_orchestrator.py` still imports this one, and it cannot run anyway
(this tree needs `pydantic`, which is not installed in .venv).

It is not merely redundant, it is actively misleading: these copies still
fabricate their results. The version of zero-noise extrapolation in this file's
sibling `error_mitigation_service.py` pushes every probability TOWARD 0.5 —
measured: peak 0.70 -> 0.62, entropy 1.32 -> 1.55 bits — which flattens the
distribution, the opposite of both its own comment ("increasing contrast") and
of what error mitigation does. The copy under src/ at least sharpens.

Importing raises rather than warns, because a warning on a module that
fabricates numbers is not proportionate to the harm of using it by accident.

TO RESOLVE: repoint main_orchestrator.py at the src/ tree, confirm the
constructor signatures line up, then delete this directory. Tracked in
SCAFFOLDING.md.
"""
raise ImportError(
    "services/hybrid_baseline_service.py is a deprecated duplicate that still fabricates "
    "its results. Import from src.hybrid_baseline_service.service instead. "
    "See SCAFFOLDING.md.")

"""
Hybrid Baseline Service Implementation
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
import numpy as np


logger = logging.getLogger(__name__)


class BaselineConfig(BaseModel):
    """Configuration for baseline algorithms"""
    algorithm: str = Field(..., description="Baseline algorithm to run")
    max_iterations: int = Field(1000, ge=1, le=100000, description="Maximum iterations for optimization")
    convergence_tolerance: float = Field(1e-6, gt=0, lt=1.0, description="Convergence tolerance")
    time_limit: float = Field(300, gt=0, description="Time limit in seconds")


class HybridBaselineService:
    """Service for running classical baselines and computing optimality gaps"""
    
    def __init__(self, classical_algorithms: list = None):
        self.classical_algorithms = classical_algorithms or [
            "milp", "heuristics", "metaheuristics", "machine_learning"
        ]
        self.baseline_results = {}
        
    async def run_baseline(self, problem: Dict[str, Any], algorithm: str, **kwargs):
        """Run classical baseline algorithm on problem"""
        logger.info(f"Running {algorithm} baseline on problem {problem.get('problem_id', 'Unknown')}")
        
        # Validate algorithm
        if algorithm not in self.classical_algorithms:
            raise ValueError(f"Unsupported algorithm: {algorithm}. Supported: {self.classical_algorithms}")
        
        # Validate configuration
        config = BaselineConfig(algorithm=algorithm, **kwargs)
        
        # Run the selected algorithm
        result = await self._run_algorithm(problem, algorithm, config)
        
        # Store result
        baseline_id = f"base_{len(self.baseline_results) + 1:04d}"
        self.baseline_results[baseline_id] = {
            "problem_id": problem.get("problem_id"),
            "algorithm": algorithm,
            "configuration": config.dict(),
            "result": result,
            "run_at": asyncio.get_event_loop().time()
        }
        
        logger.info(f"Baseline {algorithm} completed with result: {result['objective_value']}")
        
        return {
            "baseline_id": baseline_id,
            "algorithm": algorithm,
            "problem_id": problem.get('problem_id', 'Unknown'),
            "result": result,
            "metrics": result.get("metrics", {}),
            "status": "completed",
            "message": f"{algorithm.upper()} baseline completed successfully"
        }
    
    async def _run_algorithm(self, problem: Dict[str, Any], algorithm: str, config: BaselineConfig):
        """Run the specific algorithm"""
        if algorithm.lower() == "milp":
            return await self._run_milp_baseline(problem, config)
        elif algorithm.lower() == "heuristics":
            return await self._run_heuristic_baseline(problem, config)
        elif algorithm.lower() == "metaheuristics":
            return await self._run_metaheuristic_baseline(problem, config)
        elif algorithm.lower() == "machine_learning":
            return await self._run_ml_baseline(problem, config)
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")
    
    async def _run_milp_baseline(self, problem: Dict, config: BaselineConfig):
        """Run Mixed Integer Linear Programming baseline"""
        logger.info("Running MILP baseline")
        
        # Simulate solving a QUBO/Ising problem with a classical optimizer
        # Since we don't have the actual problem structure, we'll simulate the result
        
        # Calculate approximate problem size and complexity
        problem_size = problem.get("problem_size", 10)
        
        # Simulate running a classical optimizer
        start_time = asyncio.get_event_loop().time()
        
        # For demonstration, we'll simulate the solution process
        # In a real implementation, this would interface with CPLEX, Gurobi, etc.
        solution = np.random.choice([0, 1], size=problem_size)  # Binary solution vector
        objective_value = np.random.uniform(0, 100)  # Simulated objective value
        
        # Simulate runtime based on problem size
        elapsed_time = np.random.uniform(0.5, 5.0)  # Simulated runtime
        
        return {
            "solution": solution.tolist(),
            "objective_value": objective_value,
            "runtime": elapsed_time,
            "iterations": np.random.randint(100, config.max_iterations // 2),
            "status": "optimal" if np.random.random() > 0.3 else "feasible",
            "gap_to_optimal": np.random.uniform(0.01, 0.05) if np.random.random() > 0.7 else 0.0,
            "metrics": {
                "solution_quality": objective_value,
                "runtime_seconds": elapsed_time,
                "optimality_gap": 0.0,  # Assuming we found optimal solution in simulation
                "convergence": True
            }
        }
    
    async def _run_heuristic_baseline(self, problem: Dict, config: BaselineConfig):
        """Run Heuristic baseline (e.g., greedy, local search)"""
        logger.info("Running Heuristic baseline")
        
        problem_size = problem.get("problem_size", 10)
        
        start_time = asyncio.get_event_loop().time()
        
        # Simulate heuristic algorithm (e.g., greedy approach)
        solution = []  # Build solution greedily
        for i in range(problem_size):
            # Simulate greedy choice
            choice = np.random.choice([0, 1], p=[0.45, 0.55])  # Slightly biased toward 1
            solution.append(choice)
        
        # Calculate objective value (simulated)
        objective_value = sum(solution) * np.random.uniform(5, 15)  # Very simplified
        
        elapsed_time = np.random.uniform(0.1, 1.0)  # Heuristics are usually faster
        
        return {
            "solution": solution,
            "objective_value": objective_value,
            "runtime": elapsed_time,
            "iterations": min(config.max_iterations, len(solution) * 2),
            "status": "feasible",
            "gap_to_optimal": np.random.uniform(0.05, 0.25),  # Heuristics may not find optimal
            "metrics": {
                "solution_quality": objective_value,
                "runtime_seconds": elapsed_time,
                "optimality_gap": np.random.uniform(0.05, 0.25),
                "convergence": True
            }
        }
    
    async def _run_metaheuristic_baseline(self, problem: Dict, config: BaselineConfig):
        """Run Metaheuristic baseline (e.g., genetic algorithm, simulated annealing)"""
        logger.info("Running Metaheuristic baseline")
        
        problem_size = problem.get("problem_size", 10)
        
        start_time = asyncio.get_event_loop().time()
        
        # Simulate metaheuristic process
        population_size = min(50, max(10, problem_size))  # Population size
        generations = min(config.max_iterations // 10, 100)  # Number of generations
        
        # Initialize random population
        population = [np.random.choice([0, 1], size=problem_size) for _ in range(population_size)]
        
        best_solution = None
        best_objective = float('-inf')
        
        # Simulate evolution process
        for gen in range(generations):
            # Evaluate fitness
            for individual in population:
                # Very simplified fitness calculation
                obj_val = np.sum(individual) * np.random.uniform(8, 12)
                if obj_val > best_objective:
                    best_objective = obj_val
                    best_solution = individual.copy()
            
            # Simulate selection, crossover, mutation
            # (In simulation, we'll just continue with some random variation)
            if gen < generations - 1:  # Don't mutate in the last generation
                for i in range(len(population)):
                    if np.random.random() < 0.1:  # 10% chance of mutation
                        idx = np.random.randint(0, problem_size)
                        population[i][idx] = 1 - population[i][idx]  # Flip bit
        
        elapsed_time = np.random.uniform(1.0, 10.0)  # Metaheuristics take more time
        
        return {
            "solution": best_solution.tolist() if best_solution is not None else [],
            "objective_value": float(best_objective),
            "runtime": elapsed_time,
            "iterations": generations,
            "status": "feasible",
            "gap_to_optimal": np.random.uniform(0.02, 0.15),  # Better than simple heuristics
            "metrics": {
                "solution_quality": float(best_objective),
                "runtime_seconds": elapsed_time,
                "optimality_gap": np.random.uniform(0.02, 0.15),
                "convergence": True
            }
        }
    
    async def _run_ml_baseline(self, problem: Dict, config: BaselineConfig):
        """Run Machine Learning baseline"""
        logger.info("Running ML baseline")
        
        problem_size = problem.get("problem_size", 10)
        
        start_time = asyncio.get_event_loop().time()
        
        # Simulate ML model prediction (for QML comparison)
        # This is a placeholder for ML models that could learn to solve optimization problems
        solution = np.random.choice([0, 1], size=problem_size)  # Predicted solution
        objective_value = np.sum(solution) * np.random.uniform(7, 14)  # Calculated objective
        
        elapsed_time = np.random.uniform(0.5, 3.0)  # ML inference time
        
        return {
            "solution": solution.tolist(),
            "objective_value": objective_value,
            "runtime": elapsed_time,
            "iterations": 1,  # ML is often single-pass prediction
            "status": "prediction",
            "gap_to_optimal": np.random.uniform(0.05, 0.3),  # ML performance varies
            "metrics": {
                "solution_quality": objective_value,
                "runtime_seconds": elapsed_time,
                "model_accuracy": np.random.uniform(0.7, 0.95),
                "convergence": True  # ML models give prediction directly
            }
        }
    
    async def compute_optimality_gaps(self, quantum_result: Dict[str, Any], classical_results: List[Dict[str, Any]]):
        """Compute optimality gaps between quantum and classical results"""
        logger.info("Computing optimality gaps")
        
        # Get best classical result for comparison
        best_classical = max(classical_results, key=lambda x: x['result']['objective_value'])
        
        quantum_obj = quantum_result.get('objective_value', 0.0)
        classical_obj = best_classical['result']['objective_value']
        
        # Calculate gap - positive means quantum is better, negative means classical is better
        if classical_obj != 0:
            gap_percentage = (quantum_obj - classical_obj) / abs(classical_obj) * 100
        else:
            gap_percentage = float('inf') if quantum_obj > 0 else 0
        
        return {
            "quantum_objective": quantum_obj,
            "best_classical_objective": classical_obj,
            "optimality_gap_percentage": gap_percentage,
            "quantum_performance": "better" if gap_percentage > 0 else "worse" if gap_percentage < 0 else "equal",
            "absolute_difference": abs(quantum_obj - classical_obj)
        }
    
    async def get_baseline_result(self, baseline_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a baseline result"""
        return self.baseline_results.get(baseline_id)
    
    async def list_baseline_results(self) -> Dict[str, Any]:
        """List all baseline results"""
        return {
            "baseline_results": [
                {
                    "baseline_id": bid, 
                    "algorithm": b["algorithm"], 
                    "problem_id": b["problem_id"],
                    "objective_value": b["result"].get("objective_value", 0)
                }
                for bid, b in self.baseline_results.items()
            ],
            "total_count": len(self.baseline_results),
            "algorithm_distribution": {
                alg: len([b for b in self.baseline_results.values() if b["algorithm"] == alg])
                for alg in self.classical_algorithms
            }
        }