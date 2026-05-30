"""
Experiment Registry & RAG Service - Minimal Implementation for Phase 3
"""
import asyncio
import logging
from typing import Dict, Any, List
import json
from datetime import datetime
import numpy as np
import mlflow
from langfuse import Langfuse


logger = logging.getLogger(__name__)


class ExperimentRegistryRAGService:
    """Service for experiment tracking and retrieval-augmented generation"""
    
    def __init__(self):
        self.experiments = {}
        self.mlflow_tracking_uri = "sqlite:///mlruns.db"  # Default to SQLite for simplicity
        self.langfuse = None
        
        try:
            mlflow.set_tracking_uri(self.mlflow_tracking_uri)
            logger.info(f"MLflow tracking URI set to: {self.mlflow_tracking_uri}")
        except Exception as e:
            logger.warning(f"Could not initialize MLflow: {e}")
        
        try:
            self.langfuse = Langfuse()
            logger.info("Langfuse initialized successfully")
        except Exception as e:
            logger.warning(f"Could not initialize Langfuse: {e}")
    
    async def log_experiment(
        self,
        experiment_name: str,
        run_name: str,
        parameters: Dict[str, Any],
        metrics: Dict[str, float],
        artifacts: List[str] = None
    ) -> Dict[str, Any]:
        """Log an experiment to tracking system"""
        logger.info(f"Logging experiment: {experiment_name}/{run_name}")
        
        # Use MLflow to log the experiment
        try:
            # Create or get experiment
            experiment = mlflow.get_experiment_by_name(experiment_name)
            if experiment is None:
                experiment_id = mlflow.create_experiment(experiment_name)
                experiment = mlflow.get_experiment(experiment_id)
            else:
                experiment_id = experiment.experiment_id
            
            # Start a new run
            with mlflow.start_run(
                experiment_id=experiment_id,
                run_name=run_name
            ) as run:
                # Log parameters
                for param_name, param_value in parameters.items():
                    mlflow.log_param(param_name, str(param_value))
                
                # Log metrics
                for metric_name, metric_value in metrics.items():
                    mlflow.log_metric(metric_name, metric_value)
                
                # Log artifacts if any
                if artifacts:
                    for artifact_path in artifacts:
                        try:
                            mlflow.log_artifact(artifact_path)
                        except Exception as e:
                            logger.warning(f"Could not log artifact {artifact_path}: {e}")
                
                # Create experiment record
                experiment_record = {
                    "experiment_id": run.info.experiment_id,
                    "run_id": run.info.run_id,
                    "experiment_name": experiment_name,
                    "run_name": run_name,
                    "parameters": parameters,
                    "metrics": metrics,
                    "artifacts": artifacts or [],
                    "status": "logged",
                    "start_time": datetime.fromtimestamp(run.info.start_time / 1000).isoformat(),
                    "end_time": datetime.now().isoformat()
                }
                
                # Store in our local registry
                experiment_id_key = f"{experiment_name}_{run_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                self.experiments[experiment_id_key] = experiment_record
                
                logger.info(f"Experiment logged successfully with run_id: {run.info.run_id}")
                
                return {
                    "experiment_id_key": experiment_id_key,
                    "mlflow_run_id": run.info.run_id,
                    "status": "logged",
                    "message": f"Experiment '{experiment_name}/{run_name}' logged successfully"
                }
        
        except Exception as e:
            logger.error(f"Error logging experiment: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "failed",
                "error": str(e),
                "message": f"Failed to log experiment: {str(e)}"
            }
    
    async def search_experiments(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """Search experiments based on query text"""
        logger.info(f"Searching experiments for query: '{query}' (max_results: {max_results})")
        
        # In a real implementation, this would use OpenSearch/Qdrant/Neo4j
        # For now, we'll do a simple string matching search
        
        results = []
        query_lower = query.lower()
        
        for exp_key, exp_data in self.experiments.items():
            # Score based on how well the query matches experiment content
            score = 0
            
            # Check experiment name
            if query_lower in exp_data.get("experiment_name", "").lower():
                score += 3
            # Check run name
            if query_lower in exp_data.get("run_name", "").lower():
                score += 2
            # Check parameters
            for param_name, param_value in exp_data.get("parameters", {}).items():
                if query_lower in param_name.lower() or query_lower in str(param_value).lower():
                    score += 1
            # Check metrics
            for metric_name in exp_data.get("metrics", {}).keys():
                if query_lower in metric_name.lower():
                    score += 1
        
            if score > 0:
                results.append({
                    "id": exp_key,
                    "experiment_data": exp_data,
                    "relevance_score": score,
                    "match_details": self._extract_matches(exp_data, query_lower)
                })
        
        # Sort by relevance score (descending)
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        # Return top results
        top_results = results[:max_results]
        
        logger.info(f"Found {len(top_results)} relevant experiments")
        
        return {
            "query": query,
            "results": top_results,
            "total_found": len(results),
            "returned_count": len(top_results),
            "status": "success"
        }
    
    def _extract_matches(self, experiment_data: Dict[str, Any], query: str) -> List[str]:
        """Extract specific matches for the query in experiment data"""
        matches = []
        
        # Add matches from different parts of experiment
        if query in experiment_data.get("experiment_name", "").lower():
            matches.append(f"Experiment name: {experiment_data['experiment_name']}")
        
        if query in experiment_data.get("run_name", "").lower():
            matches.append(f"Run name: {experiment_data['run_name']}")
        
        # Check parameters
        for param_name, param_value in experiment_data.get("parameters", {}).items():
            if query in param_name.lower():
                matches.append(f"Parameter name: {param_name}")
            if query in str(param_value).lower():
                matches.append(f"Parameter value: {param_name}={param_value}")
        
        # Check metrics
        for metric_name in experiment_data.get("metrics", {}).keys():
            if query in metric_name.lower():
                matches.append(f"Metric: {metric_name}")
        
        return matches
    
    async def rag_query(self, question: str) -> Dict[str, Any]:
        """Answer questions using retrieval augmented generation approach"""
        logger.info(f"Processing RAG query: '{question[:50]}...'")
        
        # Use search functionality to find relevant experiments
        search_results = await self.search_experiments(question, max_results=5)
        
        if not search_results["results"]:
            return {
                "question": question,
                "answer": "No relevant experiments found for this query",
                "sources": [],
                "confidence": 0.0,
                "status": "no_results_found"
            }
        
        # Generate an answer based on retrieved experiments
        answer = self._generate_answer_from_experiments(question, search_results["results"])
        
        # Format sources
        sources = [
            {
                "experiment_id": result["id"],
                "experiment_name": result["experiment_data"]["experiment_name"],
                "run_name": result["experiment_data"]["run_name"],
                "relevance_score": result["relevance_score"],
                "parameters": result["experiment_data"]["parameters"],
                "metrics": result["experiment_data"]["metrics"]
            }
            for result in search_results["results"]
        ]
        
        return {
            "question": question,
            "answer": answer,
            "sources": sources,
            "confidence": min(0.95, sum(r["relevance_score"] for r in search_results["results"]) / 10.0),  # Normalize confidence
            "n_sources": len(sources),
            "status": "success"
        }
    
    def _generate_answer_from_experiments(self, question: str, relevant_experiments: List[Dict[str, Any]]) -> str:
        """Generate an answer based on relevant experiments"""
        # Analyze the question to understand what kind of information is being requested
        question_lower = question.lower()
        
        if "best" in question_lower or "optimal" in question_lower:
            # Find experiment with best metric
            best_exp = max(relevant_experiments, key=lambda x: max(x["experiment_data"]["metrics"].values(), default=0))
            best_metric = max(best_exp["experiment_data"]["metrics"].values(), default="N/A")
            best_metric_name = max(best_exp["experiment_data"]["metrics"].items(), key=lambda x: x[1], default=("N/A", 0))[0]
            
            return (f"Based on the experiments, the best performing approach was '{best_exp['experiment_data']['experiment_name']}' "
                   f"with '{best_metric_name}' = {best_metric}. This experiment used parameters: "
                   f"{dict(list(best_exp['experiment_data']['parameters'].items())[:3])}.")
        
        elif "compare" in question_lower or "vs" in question_lower or "versus" in question_lower:
            # Compare top experiments
            top_experiments = relevant_experiments[:3]
            comparison = []
            
            for exp in top_experiments:
                exp_name = exp['experiment_data']['experiment_name']
                metrics = exp['experiment_data']['metrics']
                params = exp['experiment_data']['parameters']
                
                comparison.append(
                    f"{exp_name}: Metrics: {dict(list(metrics.items())[:2])}, "
                    f"Params: {dict(list(params.items())[:2])}"
                )
            
            return f"Comparison of top experiments:\n" + "\n".join([f"- {comp}" for comp in comparison])
        
        elif "parameter" in question_lower or "hyperparameter" in question_lower:
            # Return parameter information
            all_params = {}
            for exp in relevant_experiments:
                for param_name, param_value in exp['experiment_data']['parameters'].items():
                    if param_name not in all_params:
                        all_params[param_name] = []
                    all_params[param_name].append(param_value)
            
            if all_params:
                param_summary = ", ".join([f"{k}: {list(set(v))[:3]}" for k, v in all_params.items()][:5])
                return f"Common parameters found in experiments: {param_summary}"
            else:
                return "No parameter information found in relevant experiments."
        
        else:
            # General summary of findings
            total_experiments = len(relevant_experiments)
            avg_metrics = {}
            
            # Calculate average metrics across experiments
            all_metrics = {}
            for exp in relevant_experiments:
                for metric_name, metric_value in exp['experiment_data']['metrics'].items():
                    if metric_name not in all_metrics:
                        all_metrics[metric_name] = []
                    all_metrics[metric_name].append(metric_value)
            
            for metric_name, values in all_metrics.items():
                avg_metrics[metric_name] = np.mean(values)
            
            response = f"Based on {total_experiments} relevant experiments:"
            if avg_metrics:
                response += f" Average metrics: {dict(list(avg_metrics.items())[:3])}."
            
            if len(relevant_experiments) > 0:
                first_exp = relevant_experiments[0]
                response += f" Most relevant experiment: '{first_exp['experiment_data']['experiment_name']}'"
            
            return response
    
    async def list_experiments(self, max_results: int = 50) -> Dict[str, Any]:
        """List all experiments with pagination"""
        logger.info(f"Listing experiments (max_results: {max_results})")
        
        experiment_list = []
        
        for exp_key, exp_data in self.experiments.items():
            experiment_list.append({
                "experiment_id": exp_key,
                "name": exp_data["experiment_name"],
                "run_name": exp_data["run_name"],
                "status": exp_data["status"],
                "created_at": exp_data["start_time"],
                "n_parameters": len(exp_data.get("parameters", {})),
                "n_metrics": len(exp_data.get("metrics", {})),
                "best_metric": max(exp_data.get("metrics", {}).values(), default="N/A")
            })
        
        # Sort by creation time (most recent first)
        experiment_list.sort(key=lambda x: x["created_at"], reverse=True)
        
        return {
            "experiments": experiment_list[:max_results],
            "total_count": len(experiment_list),
            "returned_count": min(len(experiment_list), max_results),
            "status": "success"
        }
    
    async def get_experiment_by_id(self, experiment_id: str) -> Dict[str, Any]:
        """Retrieve a specific experiment by ID"""
        if experiment_id not in self.experiments:
            return {
                "status": "not_found",
                "error": f"Experiment {experiment_id} not found",
                "message": f"Could not find experiment with ID: {experiment_id}"
            }
        
        exp_data = self.experiments[experiment_id]
        
        return {
            "experiment_id": experiment_id,
            "experiment_data": exp_data,
            "status": "found"
        }
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about registered experiments"""
        total_experiments = len(self.experiments)
        
        if total_experiments == 0:
            return {
                "total_experiments": 0,
                "status": "no_experiments"
            }
        
        # Gather statistics
        experiment_types = set()
        parameter_counts = []
        metric_counts = []
        all_parameters = set()
        all_metrics = set()
        
        for exp_data in self.experiments.values():
            exp_name = exp_data["experiment_name"]
            experiment_types.add(exp_name)
            
            params = exp_data.get("parameters", {})
            metrics = exp_data.get("metrics", {})
            
            parameter_counts.append(len(params))
            metric_counts.append(len(metrics))
            
            all_parameters.update(params.keys())
            all_metrics.update(metrics.keys())
        
        # Calculate parameter and metric value statistics
        param_values = []
        metric_values = []
        
        for exp_data in self.experiments.values():
            param_values.extend(list(exp_data.get("parameters", {}).values()))
            metric_values.extend(list(exp_data.get("metrics", {}).values()))
        
        return {
            "total_experiments": total_experiments,
            "unique_experiment_types": len(experiment_types),
            "experiment_types": list(experiment_types),
            "average_parameters_per_experiment": np.mean(parameter_counts) if parameter_counts else 0,
            "average_metrics_per_experiment": np.mean(metric_counts) if metric_counts else 0,
            "total_unique_parameters": len(all_parameters),
            "total_unique_metrics": len(all_metrics),
            "parameter_statistics": {
                "count": len(param_values),
                "type_distribution": {
                    "string": sum(1 for v in param_values if isinstance(v, str)),
                    "numeric": sum(1 for v in param_values if isinstance(v, (int, float))),
                    "other": sum(1 for v in param_values if not isinstance(v, (str, int, float)))
                }
            },
            "metric_statistics": {
                "count": len(metric_values),
                "min_value": float(np.min(metric_values)) if metric_values else 0.0,
                "max_value": float(np.max(metric_values)) if metric_values else 0.0,
                "avg_value": float(np.mean(metric_values)) if metric_values else 0.0,
                "std_value": float(np.std(metric_values)) if metric_values and len(metric_values) > 1 else 0.0
            },
            "status": "success"
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for the experiment registry service"""
        try:
            # Check if MLflow is accessible
            mlflow_ok = True
            try:
                experiment = mlflow.get_experiment_by_name("health_check")
                if experiment is None:
                    mlflow.create_experiment("health_check")
            except Exception:
                mlflow_ok = False
            
            # Check if we can log a dummy experiment
            dummy_ok = True
            try:
                dummy_result = await self.log_experiment(
                    experiment_name="health_check",
                    run_name="dummy_test",
                    parameters={"test": "value"},
                    metrics={"accuracy": 0.95}
                )
                dummy_ok = dummy_result.get("status") == "logged"
            except Exception:
                dummy_ok = False
            
            return {
                "service": "experiment_registry_rag",
                "status": "healthy" if mlflow_ok and dummy_ok else "degraded",
                "checks": {
                    "mlflow_access": mlflow_ok,
                    "logging_capability": dummy_ok
                },
                "timestamp": datetime.utcnow().isoformat(),
                "experiments_count": len(self.experiments)
            }
        
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "service": "experiment_registry_rag",
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }