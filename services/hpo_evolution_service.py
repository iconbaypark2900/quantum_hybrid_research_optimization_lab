"""DEPRECATED DUPLICATE — do not import. See src/hpo_evolution_service/service.py.

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
    "services/hpo_evolution_service.py is a deprecated duplicate that still fabricates "
    "its results. Import from src.hpo_evolution_service.service instead. "
    "See SCAFFOLDING.md.")

"""
HPO Evolution Service Implementation
"""
import asyncio
import logging
from typing import Dict, Any, Optional, Callable
from pydantic import BaseModel, Field
import numpy as np
import optuna


logger = logging.getLogger(__name__)


class HPOConfig(BaseModel):
    """Configuration for hyperparameter optimization"""
    optimization_target: str = Field(..., description="Target to optimize (e.g., 'energy', 'accuracy')")
    max_trials: int = Field(100, ge=1, le=10000, description="Maximum number of optimization trials")
    algorithm: str = Field("tpe", description="Optimization algorithm (tpe, random, grid, etc.)")
    search_space: Dict[str, Dict[str, Any]] = Field(..., description="Parameter search space")


class HPOEvolutionService:
    """Service for hyperparameter optimization and evolutionary search"""
    
    def __init__(self, optimization_framework: str = "optuna"):
        self.optimization_framework = optimization_framework
        self.study_name = "quantum_hpo_study"
        self.storage_url = "sqlite:///quantum_hpo.db"  # Default storage
        self.studies = {}
        self.results = {}
        
    async def optimize_hyperparameters(
        self, 
        objective_function: Callable, 
        search_space: Dict[str, Dict[str, Any]], 
        n_trials: int = 100
    ):
        """Optimize hyperparameters using evolutionary methods"""
        logger.info(f"Starting hyperparameter optimization with {n_trials} trials")
        
        # Create Optuna study
        study = optuna.create_study(
            direction="minimize",  # or maximize based on objective
            sampler=self._get_sampler(search_space)
        )
        
        # Define the actual objective function that works with Optuna
        def optuna_objective(trial):
            # Sample parameters from search space
            params = {}
            for param_name, param_config in search_space.items():
                param_type = param_config.get("type", "float")
                
                if param_type == "float":
                    low = param_config.get("low", 0.0)
                    high = param_config.get("high", 1.0)
                    step = param_config.get("step")
                    
                    if step:
                        params[param_name] = trial.suggest_float(param_name, low, high, step=step)
                    else:
                        params[param_name] = trial.suggest_float(param_name, low, high)
                
                elif param_type == "int":
                    low = param_config.get("low", 1)
                    high = param_config.get("high", 10)
                    params[param_name] = trial.suggest_int(param_name, low, high)
                
                elif param_type == "categorical":
                    choices = param_config.get("choices", [])
                    params[param_name] = trial.suggest_categorical(param_name, choices)
                
                elif param_type == "discrete":
                    choices = param_config.get("choices", [0.1, 0.2, 0.5, 1.0])
                    params[param_name] = trial.suggest_categorical(param_name, choices)
            
            # Evaluate objective function with sampled parameters
            try:
                result = objective_function(params)
                return result
            except Exception as e:
                logger.error(f"Error in objective function evaluation: {e}")
                # Return a very poor value to penalize invalid configurations
                return float('inf')
        
        # Optimize
        study.optimize(optuna_objective, n_trials=n_trials)
        
        # Extract best result
        best_params = study.best_params
        best_value = study.best_value
        
        # Store results
        optimization_id = f"hpo_{len(self.results) + 1:04d}"
        self.results[optimization_id] = {
            "study": study,
            "best_params": best_params,
            "best_value": best_value,
            "n_trials": n_trials,
            "search_space": search_space,
            "completed_at": asyncio.get_event_loop().time(),
            "trial_results": [trial.value for trial in study.trials if trial.state == optuna.trial.TrialState.COMPLETE]
        }
        
        logger.info(f"Hyperparameter optimization completed. Best value: {best_value}")
        
        return {
            "optimization_id": optimization_id,
            "best_params": best_params,
            "best_value": best_value,
            "n_trials": n_trials,
            "n_completed_trials": len([t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE]),
            "status": "completed",
            "message": f"HPO completed with best value: {best_value:.4f}"
        }
    
    def _get_sampler(self, search_space: Dict[str, Any]):
        """Get appropriate sampler based on search space"""
        # For mixed spaces with discrete and continuous parameters, use TPE
        return optuna.samplers.TPESampler()
    
    async def evolve_circuit_architecture(self, 
                                       evaluation_function: Callable, 
                                       initial_population: list, 
                                       n_generations: int = 50):
        """Evolve quantum circuit architectures using evolutionary methods"""
        logger.info(f"Starting circuit evolution with {n_generations} generations")
        
        # This would implement evolutionary algorithms for circuit structures
        # For now, we'll simulate the process
        
        population = initial_population[:]  # Copy initial population
        best_individual = None
        best_fitness = float('-inf')
        
        history = {
            "generation_best_fitness": [],
            "population_diversity": [],
            "average_fitness": []
        }
        
        for generation in range(n_generations):
            # Evaluate fitness of current population
            fitness_scores = []
            for individual in population:
                try:
                    fitness = evaluation_function(individual)
                    fitness_scores.append(fitness)
                    
                    if fitness > best_fitness:
                        best_fitness = fitness
                        best_individual = individual
                        
                except Exception as e:
                    logger.error(f"Error evaluating individual: {e}")
                    fitness_scores.append(float('-inf'))
            
            # Calculate statistics for this generation
            avg_fitness = sum(fitness_scores) / len(fitness_scores)
            diversity = np.std(fitness_scores) if fitness_scores else 0
            
            history["generation_best_fitness"].append(max(fitness_scores))
            history["average_fitness"].append(avg_fitness)
            history["population_diversity"].append(diversity)
            
            # Selection and reproduction for next generation
            # This is a simplified selection process
            # In a real implementation, this would include crossover and mutation operations
            selected_indices = np.argsort(fitness_scores)[-len(population)//2:]  # Top half
            next_population = []
            
            for idx in selected_indices:
                next_population.append(population[idx])  # Add selected individuals
            
            # Add mutated variants of top performers
            n_mutants = len(population) - len(next_population)
            for i in range(n_mutants):
                # Create mutation of best performer
                if best_individual:
                    mutated = self._mutate_individual(best_individual)
                    next_population.append(mutated)
                else:
                    # Generate random if no best yet
                    next_population.append(self._generate_random_individual())
            
            population = next_population
        
        evolution_id = f"evol_{len(self.results) + 1:04d}"
        self.results[evolution_id] = {
            "best_individual": best_individual,
            "best_fitness": best_fitness,
            "n_generations": n_generations,
            "history": history,
            "final_population": population,
            "completed_at": asyncio.get_event_loop().time()
        }
        
        return {
            "evolution_id": evolution_id,
            "best_individual": best_individual,
            "best_fitness": best_fitness,
            "n_generations": n_generations,
            "status": "completed",
            "message": f"Circuit evolution completed with best fitness: {best_fitness:.4f}"
        }
    
    def _mutate_individual(self, individual: Dict[str, Any]) -> Dict[str, Any]:
        """Apply mutation to an individual circuit configuration"""
        # This would implement specific mutations for quantum circuits
        # For simulation, we'll make minor changes to parameters
        mutated = individual.copy()
        
        # Example mutations
        if isinstance(mutated.get("depth"), int):
            # Slightly vary depth
            mutated["depth"] = max(1, mutated["depth"] + np.random.choice([-1, 0, 1]))
        
        if "learning_rate" in mutated:
            # Slightly vary learning rate
            factor = np.random.uniform(0.8, 1.2)
            mutated["learning_rate"] *= factor
        
        if "initial_state" in mutated and isinstance(mutated["initial_state"], str):
            # Maybe change initial state preparation
            if np.random.random() < 0.1:  # 10% chance to change strategy
                mutated["initial_state"] = np.random.choice(["uniform", "dense", "random"])
        
        return mutated
    
    def _generate_random_individual(self) -> Dict[str, Any]:
        """Generate a random circuit configuration"""
        return {
            "depth": np.random.randint(1, 6),
            "learning_rate": np.random.uniform(0.001, 0.1),
            "initial_state": np.random.choice(["uniform", "dense", "random"]),
            "optimizer": np.random.choice(["adam", "sgd", "rmsprop"]),
            "mixer_type": np.random.choice(["x-mixer", "xy-mixer"]),
            "problem_size": np.random.randint(4, 10)
        }
    
    async def get_optimization_result(self, optimization_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve an optimization result"""
        return self.results.get(optimization_id)
    
    async def list_optimization_results(self) -> Dict[str, Any]:
        """List all optimization results"""
        return {
            "optimization_results": [
                {
                    "optimization_id": oid,
                    "best_value": r["best_value"],
                    "n_trials": r.get("n_trials", 0),
                    "completed_at": r["completed_at"]
                }
                for oid, r in self.results.items()
            ],
            "total_count": len(self.results)
        }
    
    async def run_multi_objective_optimization(
        self, 
        objective_functions: List[Callable], 
        search_space: Dict[str, Dict[str, Any]], 
        n_trials: int = 100
    ):
        """Run multi-objective optimization"""
        logger.info(f"Starting multi-objective optimization with {len(objective_functions)} objectives")
        
        # Create multi-objective study
        study = optuna.multi_objective.create_study(
            directions=["minimize"] * len(objective_functions),  # Assuming minimization for all
            sampler=optuna.multi_objective.samplers.NSGAIISampler()
        )
        
        def multi_objective_optuna(trial):
            # Sample parameters
            params = {}
            for param_name, param_config in search_space.items():
                param_type = param_config.get("type", "float")
                
                if param_type == "float":
                    low = param_config.get("low", 0.0)
                    high = param_config.get("high", 1.0)
                    params[param_name] = trial.suggest_float(param_name, low, high)
                elif param_type == "int":
                    low = param_config.get("low", 1)
                    high = param_config.get("high", 10)
                    params[param_name] = trial.suggest_int(param_name, low, high)
                elif param_type == "categorical":
                    choices = param_config.get("choices", [])
                    params[param_name] = trial.suggest_categorical(param_name, choices)
            
            # Evaluate all objectives
            values = []
            for obj_func in objective_functions:
                try:
                    val = obj_func(params)
                    values.append(val)
                except Exception as e:
                    logger.error(f"Error in objective function: {e}")
                    values.append(float('inf'))  # Penalize invalid configurations
            
            return values
        
        # Optimize
        study.optimize(multi_objective_optuna, n_trials=n_trials)
        
        # Get Pareto front
        pareto_front = study.get_pareto_front_trials()
        
        mo_optimization_id = f"mo_hpo_{len(self.results) + 1:04d}"
        self.results[mo_optimization_id] = {
            "study": study,
            "pareto_front": pareto_front,
            "n_trials": n_trials,
            "n_objectives": len(objective_functions),
            "search_space": search_space,
            "completed_at": asyncio.get_event_loop().time()
        }
        
        return {
            "mo_optimization_id": mo_optimization_id,
            "pareto_front": [{"params": trial.params, "values": trial.values} for trial in pareto_front],
            "n_pareto_solutions": len(pareto_front),
            "n_trials": n_trials,
            "status": "completed",
            "message": f"Multi-objective optimization completed with {len(pareto_front)} Pareto solutions"
        }