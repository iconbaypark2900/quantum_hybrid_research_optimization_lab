"""
Main orchestrator for the Quantum Hybrid Research & Optimization Lab
This component coordinates all services and implements the key workflows
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
from pathlib import Path


logger = logging.getLogger(__name__)


class QuantumHybridOrchestrator:
    """Main orchestrator coordinating all services in the Quantum Hybrid Lab"""
    
    def __init__(self, config_path: str = "config/settings.json"):
        self.config = self._load_config(config_path)
        self.services = {}
        self.workflows = {}
        
        # Initialize service instances
        self.problem_definition_service = None
        self.circuit_generator_service = None
        self.execution_orchestrator_service = None
        self.error_mitigation_service = None
        self.hybrid_baseline_service = None
        self.hpo_evolution_service = None
        self.experiment_registry_rag_service = None
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Configuration file not found: {config_path}, using defaults")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "services": {
                "problem_definition_service": {"enabled": True, "host": "localhost", "port": 8001},
                "circuit_generator_service": {"enabled": True, "host": "localhost", "port": 8002},
                "execution_orchestrator_service": {"enabled": True, "host": "localhost", "port": 8003},
                "error_mitigation_service": {"enabled": True},
                "hybrid_baseline_service": {"enabled": True},
                "hpo_evolution_service": {"enabled": True},
                "experiment_registry_rag_service": {"enabled": True}
            },
            "workflows": {
                "define_problem_pipeline": {"enabled": True},
                "quantum_experiment_pipeline": {"enabled": True},
                "hpo_evolution_pipeline": {"enabled": True},
                "comparative_evaluation_pipeline": {"enabled": True}
            }
        }
    
    async def initialize_services(self):
        """Initialize all services based on configuration"""
        logger.info("Initializing services...")
        
        # Import service classes
        from services.problem_definition_service import ProblemDefinitionService
        from services.circuit_generator_service import CircuitGeneratorService
        from services.execution_orchestrator_service import ExecutionOrchestratorService
        from services.error_mitigation_service import ErrorMitigationService
        from services.hybrid_baseline_service import HybridBaselineService
        from services.hpo_evolution_service import HPOEvolutionService
        from services.experiment_registry_rag_service import ExperimentRegistryRAGService
        
        # Initialize each service based on configuration
        if self.config["services"]["problem_definition_service"]["enabled"]:
            self.problem_definition_service = ProblemDefinitionService(
                host=self.config["services"]["problem_definition_service"]["host"],
                port=self.config["services"]["problem_definition_service"]["port"]
            )
            logger.info("✅ Problem Definition Service initialized")
        
        if self.config["services"]["circuit_generator_service"]["enabled"]:
            self.circuit_generator_service = CircuitGeneratorService(
                host=self.config["services"]["circuit_generator_service"]["host"],
                port=self.config["services"]["circuit_generator_service"]["port"]
            )
            logger.info("✅ Circuit Generator Service initialized")
        
        if self.config["services"]["execution_orchestrator_service"]["enabled"]:
            self.execution_orchestrator_service = ExecutionOrchestratorService(
                host=self.config["services"]["execution_orchestrator_service"]["host"],
                port=self.config["services"]["execution_orchestrator_service"]["port"]
            )
            logger.info("✅ Execution Orchestrator Service initialized")
        
        if self.config["services"]["error_mitigation_service"]["enabled"]:
            self.error_mitigation_service = ErrorMitigationService()
            logger.info("✅ Error Mitigation Service initialized")
        
        if self.config["services"]["hybrid_baseline_service"]["enabled"]:
            self.hybrid_baseline_service = HybridBaselineService()
            logger.info("✅ Hybrid Baseline Service initialized")
        
        if self.config["services"]["hpo_evolution_service"]["enabled"]:
            self.hpo_evolution_service = HPOEvolutionService()
            logger.info("✅ HPO Evolution Service initialized")
        
        if self.config["services"]["experiment_registry_rag_service"]["enabled"]:
            self.experiment_registry_rag_service = ExperimentRegistryRAGService()
            await self.experiment_registry_rag_service.initialize_services()
            logger.info("✅ Experiment Registry RAG Service initialized")
        
        logger.info(f"All services initialized: {len([s for s in [
            self.problem_definition_service, 
            self.circuit_generator_service, 
            self.execution_orchestrator_service,
            self.error_mitigation_service,
            self.hybrid_baseline_service,
            self.hpo_evolution_service,
            self.experiment_registry_rag_service
        ] if s is not None])} active services")
    
    async def run_define_problem_pipeline(self, problem_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the define problem pipeline workflow"""
        logger.info("Executing Define Problem Pipeline...")
        
        if not self.problem_definition_service:
            raise RuntimeError("Problem Definition Service not initialized")
        
        try:
            result = await self.problem_definition_service.define_problem(problem_spec)
            logger.info("Define Problem Pipeline completed successfully")
            return {
                "status": "success",
                "pipeline": "define_problem",
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Define Problem Pipeline failed: {e}")
            return {
                "status": "failed",
                "pipeline": "define_problem",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def run_quantum_experiment_pipeline(
        self, 
        problem_id: str, 
        experiment_template: str = "qaoa", 
        backend: str = "simulator", 
        apply_error_mitigation: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute the quantum experiment pipeline"""
        logger.info(f"Executing Quantum Experiment Pipeline for problem {problem_id}")
        
        try:
            # Step 1: Select problem and template (would normally fetch from registry)
            # For now, we'll simulate this step
            
            # Step 2: Generate circuit
            if not self.circuit_generator_service:
                raise RuntimeError("Circuit Generator Service not initialized")
            
            circuit_params = kwargs.get("circuit_parameters", {
                "depth": kwargs.get("depth", 3),
                "problem_size": kwargs.get("problem_size", 4),
                "initial_state": kwargs.get("initial_state", "uniform"),
                "mixer_type": kwargs.get("mixer_type", "x-mixer")
            })
            
            circuit_result = await self.circuit_generator_service.generate_circuit(
                experiment_template, circuit_params
            )
            
            # Step 3: Select backend and execute
            if not self.execution_orchestrator_service:
                raise RuntimeError("Execution Orchestrator Service not initialized")
            
            shots = kwargs.get("shots", 1024)
            execution_result = await self.execution_orchestrator_service.execute_circuit(
                circuit_result["circuit_id"], backend, shots
            )
            
            # Step 4: Apply error mitigation if requested
            mitigation_result = None
            if apply_error_mitigation and self.error_mitigation_service:
                mitigation_result = await self.error_mitigation_service.apply_mitigation(
                    execution_result["result"],
                    technique=kwargs.get("mitigation_technique", "zne")
                )
            
            # Step 5: Compute metrics
            metrics_result = await self._compute_experiment_metrics(
                execution_result, circuit_result, mitigation_result
            )
            
            # Step 6: Log to MLflow/registry
            if self.experiment_registry_rag_service:
                await self.experiment_registry_rag_service.log_experiment(
                    experiment_name=f"quantum_experiment_{problem_id}",
                    run_name=f"run_{experiment_template}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    parameters={
                        "problem_id": problem_id,
                        "template": experiment_template,
                        "backend": backend,
                        "shots": shots,
                        "apply_error_mitigation": apply_error_mitigation
                    },
                    metrics=metrics_result["metrics"],
                    artifacts=[]  # Could include circuit images, reports, etc.
                )
            
            logger.info("Quantum Experiment Pipeline completed successfully")
            return {
                "status": "success",
                "pipeline": "quantum_experiment",
                "problem_id": problem_id,
                "circuit_info": circuit_result,
                "execution_result": execution_result,
                "mitigation_result": mitigation_result,
                "metrics": metrics_result,
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Quantum Experiment Pipeline failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "failed",
                "pipeline": "quantum_experiment", 
                "problem_id": problem_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _compute_experiment_metrics(self, execution_result: Dict[str, Any], 
                                      circuit_result: Dict[str, Any], 
                                      mitigation_result: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Compute metrics for quantum experiment"""
        # Extract relevant values from results
        raw_result = execution_result.get("result", {})
        mitigated_result = mitigation_result.get("mitigated_results", {}) if mitigation_result else raw_result
        
        # Compute basic metrics
        metrics = {
            "raw_execution_time": raw_result.get("execution_time", 0.0),
            "circuit_depth": circuit_result.get("parameters", {}).get("depth", 0),
            "qubit_count": circuit_result.get("qubit_count", 0),
            "shots_used": raw_result.get("shots", 0),
            "raw_energy": raw_result.get("energy", 0.0),
            "mitigated_energy": mitigated_result.get("energy", raw_result.get("energy", 0.0)),
            "raw_noise_level": raw_result.get("noise_level", 0.1),
            "mitigated_noise_level": mitigated_result.get("noise_level", raw_result.get("noise_level", 0.1)),
        }
        
        # Compute derived metrics
        metrics["energy_improvement"] = metrics["raw_energy"] - metrics["mitigated_energy"]
        metrics["noise_reduction"] = metrics["raw_noise_level"] - metrics["mitigated_noise_level"]
        metrics["circuit_efficiency"] = metrics["qubit_count"] * metrics["circuit_depth"] / metrics["raw_execution_time"] if metrics["raw_execution_time"] > 0 else 0
        
        return {
            "metrics": metrics,
            "circuit_info": circuit_result.get("parameters", {}),
            "calculation_timestamp": datetime.now().isoformat()
        }
    
    async def run_hpo_evolution_pipeline(self, optimization_target: str, search_space: Dict[str, Any], n_trials: int = 50):
        """Execute the HPO evolution pipeline"""
        logger.info(f"Executing HPO Evolution Pipeline for target: {optimization_target}")
        
        try:
            if not self.hpo_evolution_service:
                raise RuntimeError("HPO Evolution Service not initialized")
            
            # Define a simple objective function for the optimization
            # In a real implementation, this would connect to the quantum system
            def objective_function(params):
                # Simulate quantum execution based on parameters
                # This is a simplified example - real objective would connect to quantum execution
                circuit_depth = params.get('depth', 3)
                learning_rate = params.get('learning_rate', 0.01)
                
                # Simulate result based on parameters (in reality, this would run actual quantum circuits)
                # Values chosen to illustrate optimization landscape
                base_score = np.random.uniform(0.1, 0.9)
                depth_penalty = circuit_depth * 0.05  # Deeper circuits may have more errors
                lr_adjustment = abs(learning_rate - 0.05) * 2  # Optimal learning rate around 0.05
                
                result = base_score - depth_penalty - lr_adjustment
                return max(0.01, result)  # Ensure positive result
            
            result = await self.hpo_evolution_service.optimize_hyperparameters(
                objective_function, search_space, n_trials
            )
            
            logger.info("HPO Evolution Pipeline completed successfully")
            return {
                "status": "success",
                "pipeline": "hpo_evolution",
                "optimization_target": optimization_target,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"HPO Evolution Pipeline failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "failed",
                "pipeline": "hpo_evolution",
                "optimization_target": optimization_target,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def run_comparative_evaluation_pipeline(self, problem_id: str, quantum_configs: List[Dict[str, Any]], 
                                              classical_algorithms: List[str] = None):
        """Execute the comparative evaluation pipeline"""
        logger.info(f"Executing Comparative Evaluation Pipeline for problem {problem_id}")
        
        if classical_algorithms is None:
            classical_algorithms = ["heuristics", "milp"]  # Default algorithms
        
        try:
            # Run quantum configurations
            quantum_results = []
            for i, config in enumerate(quantum_configs):
                logger.info(f"Running quantum configuration {i+1}/{len(quantum_configs)}")
                
                # Run quantum experiment
                quantum_result = await self.run_quantum_experiment_pipeline(
                    problem_id=problem_id,
                    experiment_template=config.get("template", "qaoa"),
                    backend=config.get("backend", "simulator"),
                    apply_error_mitigation=config.get("apply_error_mitigation", True),
                    **config.get("parameters", {})
                )
                
                quantum_results.append(quantum_result)
            
            # Run classical baselines
            if self.hybrid_baseline_service:
                classical_results = []
                for algorithm in classical_algorithms:
                    logger.info(f"Running classical baseline: {algorithm}")
                    
                    classical_result = await self.hybrid_baseline_service.run_baseline(
                        {"problem_id": problem_id},  # Simplified problem representation
                        algorithm,
                        max_iterations=1000,
                        convergence_tolerance=1e-6
                    )
                    
                    classical_results.append(classical_result)
            else:
                classical_results = []
                logger.warning("Hybrid Baseline Service not available, skipping classical baselines")
            
            # Compare results
            comparison_report = await self._compare_results(quantum_results, classical_results)
            
            # Log comparison to experiment registry
            if self.experiment_registry_rag_service:
                await self.experiment_registry_rag_service.log_experiment(
                    experiment_name=f"comparative_evaluation_{problem_id}",
                    run_name=f"comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    parameters={
                        "problem_id": problem_id,
                        "n_quantum_configs": len(quantum_configs),
                        "classical_algorithms": classical_algorithms,
                        "quantum_configs": quantum_configs
                    },
                    metrics=comparison_report["aggregate_metrics"],
                    artifacts=[json.dumps(comparison_report)]  # Include full report
                )
            
            logger.info("Comparative Evaluation Pipeline completed successfully")
            return {
                "status": "success",
                "pipeline": "comparative_evaluation",
                "problem_id": problem_id,
                "quantum_results": quantum_results,
                "classical_results": classical_results,
                "comparison_report": comparison_report,
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Comparative Evaluation Pipeline failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "failed",
                "pipeline": "comparative_evaluation",
                "problem_id": problem_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _compare_results(self, quantum_results: List[Dict], classical_results: List[Dict]) -> Dict[str, Any]:
        """Compare quantum and classical results"""
        # This is a simplified comparison - in a real implementation, 
        # this would perform detailed statistical comparisons
        
        # Extract relevant metrics
        quantum_metrics = []
        classical_metrics = []
        
        for qr in quantum_results:
            if qr["status"] == "success":
                metrics = qr.get("metrics", {}).get("metrics", {})
                quantum_metrics.append({
                    "energy": metrics.get("mitigated_energy", metrics.get("raw_energy", 0.0)),
                    "execution_time": metrics.get("raw_execution_time", 0.0),
                    "circuit_depth": metrics.get("circuit_depth", 0)
                })
        
        for cr in classical_results:
            if cr["status"] == "success":
                metrics = cr.get("result", {}).get("metrics", {})
                classical_metrics.append({
                    "objective_value": metrics.get("solution_quality", 0.0),
                    "runtime": metrics.get("runtime_seconds", 0.0),
                    "optimality_gap": metrics.get("optimality_gap", 0.0)
                })
        
        # Compute aggregate metrics
        agg_metrics = {}
        
        if quantum_metrics:
            q_energies = [qm["energy"] for qm in quantum_metrics]
            agg_metrics["avg_quantum_energy"] = sum(q_energies) / len(q_energies)
            agg_metrics["min_quantum_energy"] = min(q_energies)
        
        if classical_metrics:
            c_objectives = [cm["objective_value"] for cm in classical_metrics]
            agg_metrics["avg_classical_objective"] = sum(c_objectives) / len(c_objectives) if c_objectives else 0
            agg_metrics["best_classical_objective"] = min(c_objectives) if c_objectives else 0
        
        return {
            "aggregate_metrics": agg_metrics,
            "n_quantum_results": len(quantum_metrics),
            "n_classical_results": len(classical_metrics),
            "performance_comparison": {
                "quantum_advantage_indicators": [],
                "classical_strengths": [],
                "combined_insights": []
            },
            "comparison_timestamp": datetime.now().isoformat()
        }
    
    async def process_query(self, query: str) -> Dict[str, Any]:
        """Process natural language queries about experiments and results"""
        logger.info(f"Processing query: {query}")
        
        if self.experiment_registry_rag_service:
            try:
                result = await self.experiment_registry_rag_service.rag_query(query)
                logger.info("Query processed successfully with RAG")
                return result
            except Exception as e:
                logger.error(f"RAG query failed: {e}")
                # Fall back to simpler search
                return {
                    "question": query,
                    "answer": f"Could not process query due to an error: {str(e)}",
                    "sources": [],
                    "confidence": 0.0,
                    "status": "error"
                }
        else:
            # Simple fallback response
            return {
                "question": query,
                "answer": "Experiment registry not available. Please run some experiments first.",
                "sources": [],
                "confidence": 0.5,  # Medium confidence in fallback
                "status": "fallback"
            }
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        return {
            "status": "operational",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "problem_definition": self.problem_definition_service is not None,
                "circuit_generator": self.circuit_generator_service is not None,
                "execution_orchestrator": self.execution_orchestrator_service is not None,
                "error_mitigation": self.error_mitigation_service is not None,
                "hybrid_baseline": self.hybrid_baseline_service is not None,
                "hpo_evolution": self.hpo_evolution_service is not None,
                "experiment_registry": self.experiment_registry_rag_service is not None
            },
            "workflows": {
                "define_problem_pipeline": self.config["workflows"]["define_problem_pipeline"]["enabled"],
                "quantum_experiment_pipeline": self.config["workflows"]["quantum_experiment_pipeline"]["enabled"],
                "hpo_evolution_pipeline": self.config["workflows"]["hpo_evolution_pipeline"]["enabled"],
                "comparative_evaluation_pipeline": self.config["workflows"]["comparative_evaluation_pipeline"]["enabled"]
            },
            "experiment_count": len(getattr(self.experiment_registry_rag_service, 'experiments', {})) if self.experiment_registry_rag_service else 0
        }


async def main():
    """Main function to run the Quantum Hybrid Orchestrator"""
    logger.info("🚀 Starting Quantum Hybrid Research & Optimization Lab")
    
    # Initialize the orchestrator
    orchestrator = QuantumHybridOrchestrator()
    
    try:
        # Initialize all services
        await orchestrator.initialize_services()
        
        # Show system status
        status = await orchestrator.get_system_status()
        logger.info(f"System Status: {status['status']}")
        logger.info(f"Active Services: {sum(status['services'].values())}/{len(status['services'])}")
        
        # Demonstrate basic functionality with example operations
        logger.info("\n🧪 Demonstrating core workflows...")
        
        # Example 1: Define a problem
        sample_problem = {
            "problem_id": "maxcut_demo_001",
            "name": "Max-Cut Problem Demo",
            "type": "combinatorial_optimization",
            "description": "Sample Max-Cut problem for demonstration",
            "graph_nodes": 8,
            "graph_edges": [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 0), (0, 2), (1, 3)]
        }
        
        # Run the define problem pipeline
        logger.info("\n📝 Running Define Problem Pipeline...")
        problem_result = await orchestrator.run_define_problem_pipeline(sample_problem)
        logger.info(f"Define Problem Pipeline Status: {problem_result['status']}")
        
        # Example 2: Run a quantum experiment
        logger.info("\n⚛️ Running Quantum Experiment Pipeline...")
        experiment_result = await orchestrator.run_quantum_experiment_pipeline(
            problem_id="maxcut_demo_001",
            experiment_template="qaoa",
            backend="simulator",
            depth=3,
            problem_size=4,
            shots=1024
        )
        logger.info(f"Quantum Experiment Pipeline Status: {experiment_result['status']}")
        
        # Example 3: Run HPO evolution
        logger.info("\n🔬 Running HPO Evolution Pipeline...")
        hpo_search_space = {
            "depth": {"type": "int", "low": 1, "high": 5},
            "learning_rate": {"type": "float", "low": 0.001, "high": 0.1},
            "optimizer": {"type": "categorical", "choices": ["adam", "sgd", "rmsprop"]}
        }
        
        hpo_result = await orchestrator.run_hpo_evolution_pipeline(
            optimization_target="minimize_energy",
            search_space=hpo_search_space,
            n_trials=10  # Smaller number for demo
        )
        logger.info(f"HPO Evolution Pipeline Status: {hpo_result['status']}")
        
        # Example 4: Run comparative evaluation
        logger.info("\n⚖️ Running Comparative Evaluation Pipeline...")
        quantum_configs = [
            {"template": "qaoa", "parameters": {"depth": 2, "problem_size": 4}},
            {"template": "qaoa", "parameters": {"depth": 3, "problem_size": 4}}
        ]
        
        comparison_result = await orchestrator.run_comparative_evaluation_pipeline(
            problem_id="maxcut_demo_001",
            quantum_configs=quantum_configs,
            classical_algorithms=["heuristics", "milp"]
        )
        logger.info(f"Comparative Evaluation Pipeline Status: {comparison_result['status']}")
        
        # Example 5: Process a query
        logger.info("\n💬 Testing Query Processing...")
        query_result = await orchestrator.process_query(
            "What was the best quantum configuration for the maxcut problem?"
        )
        logger.info(f"Query processed successfully: {bool(query_result.get('answer'))}")
        
        # Final status
        final_status = await orchestrator.get_system_status()
        logger.info(f"\n📊 Final System Status: {final_status['status']}")
        logger.info(f"Total experiments tracked: {final_status['experiment_count']}")
        
        logger.info("\n✅ Quantum Hybrid Research & Optimization Lab - All Systems Operational!")
        logger.info("🔧 Ready to run quantum-classical hybrid optimization experiments")
        logger.info("🔬 Equipped with HPO, error mitigation, and comparative analysis capabilities")
        
        return orchestrator
        
    except Exception as e:
        logger.error(f"Error in main orchestrator: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(main())