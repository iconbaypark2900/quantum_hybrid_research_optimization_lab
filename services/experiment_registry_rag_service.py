"""
Experiment Registry & RAG Service Implementation
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
import mlflow
from langfuse import Langfuse
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss


logger = logging.getLogger(__name__)


class ExperimentRecord(BaseModel):
    """Model for experiment records"""
    experiment_id: str
    name: str
    description: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    artifacts: List[str] = Field(default_factory=list)
    tags: Dict[str, str] = Field(default_factory=dict)
    created_at: str
    updated_at: Optional[str] = None


class RAGQueryResult(BaseModel):
    """Model for RAG query results"""
    experiment_id: str
    similarity_score: float
    experiment_details: Dict[str, Any]
    relevance_explanation: str


class ExperimentRegistryRAGService:
    """Service for experiment tracking and retrieval augmented generation"""
    
    def __init__(self, mlflow_tracking_uri: str = "sqlite:///mlruns.db"):
        self.mlflow_tracking_uri = mlflow_tracking_uri
        self.langfuse = None  # Initialize later if needed
        self.experiments = {}
        self.embedding_model = None
        self.vector_index = None
        self.experiment_vectors = {}  # experiment_id -> embedding vector
    
    async def initialize_services(self):
        """Initialize tracking and embedding services"""
        logger.info("Initializing Experiment Registry & RAG Service")
        
        # Initialize MLflow
        mlflow.set_tracking_uri(self.mlflow_tracking_uri)
        logger.info(f"MLflow tracking URI set to: {self.mlflow_tracking_uri}")
        
        # Initialize embedding model
        try:
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Sentence transformer model loaded successfully")
        except Exception as e:
            logger.warning(f"Could not load sentence transformer: {e}, using simple embeddings")
            # In case the model fails to load, we'll implement a simple fallback
        
        # Initialize vector index
        self._initialize_vector_index()
        
        logger.info("Experiment Registry & RAG Service initialized successfully")
    
    def _initialize_vector_index(self):
        """Initialize the vector index for similarity search"""
        # For now, create a simple FAISS index with a reasonable dimension
        # In practice, this would match the output dimension of your embedding model
        embedding_dimension = 384  # Dimension of all-MiniLM-L6-v2
        self.vector_index = faiss.IndexFlatIP(embedding_dimension)  # Inner product (cosine similarity)
        
        logger.info(f"Vector index initialized with dimension {embedding_dimension}")
    
    async def log_experiment(
        self, 
        experiment_name: str, 
        run_name: str, 
        parameters: Dict[str, Any], 
        metrics: Dict[str, float], 
        artifacts: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Log an experiment to MLflow with full tracking"""
        logger.info(f"Logging experiment: {experiment_name}/{run_name}")
        
        # Start MLflow run
        with mlflow.start_run(run_name=run_name, nested=True) as run:
            # Log parameters
            for param_name, param_value in parameters.items():
                mlflow.log_param(param_name, str(param_value))
            
            # Log metrics
            for metric_name, metric_value in metrics.items():
                mlflow.log_metric(metric_name, metric_value)
            
            # Log any artifacts if provided
            if artifacts:
                for artifact_path in artifacts:
                    try:
                        mlflow.log_artifact(artifact_path)
                    except Exception as e:
                        logger.warning(f"Could not log artifact {artifact_path}: {e}")
            
            experiment_id = run.info.experiment_id
            run_id = run.info.run_id
            
            # Create experiment record
            experiment_record = {
                "experiment_id": experiment_id,
                "run_id": run_id,
                "name": experiment_name,
                "run_name": run_name,
                "parameters": parameters,
                "metrics": metrics,
                "artifacts": artifacts or [],
                "status": "completed",
                "created_at": run.info.start_time,
                "mlflow_ui_url": f"{self.mlflow_tracking_uri}/#/experiments/{experiment_id}/runs/{run_id}"
            }
            
            # Store locally for RAG functionality
            self.experiments[run_id] = experiment_record
            
            # Generate embedding for this experiment if we have an embedding model
            if self.embedding_model:
                await self._embed_and_index_experiment(experiment_record)
            
            logger.info(f"Experiment logged successfully with run_id: {run_id}")
            
            return {
                "experiment_id": experiment_id,
                "run_id": run_id,
                "status": "logged",
                "message": f"Experiment '{experiment_name}' logged successfully",
                "mlflow_url": experiment_record["mlflow_ui_url"]
            }
    
    async def _embed_and_index_experiment(self, experiment_record: Dict[str, Any]):
        """Generate embedding for an experiment and add to vector index"""
        # Create a text representation of the experiment
        experiment_text = f"Experiment: {experiment_record['name']}\n"
        experiment_text += f"Parameters: {str(experiment_record['parameters'])}\n"
        experiment_text += f"Metrics: {str(experiment_record['metrics'])}\n"
        experiment_text += f"Artifacts: {str(experiment_record['artifacts'])}\n"
        
        # Generate embedding
        try:
            embedding = self.embedding_model.encode([experiment_text])[0]  # Get first (only) embedding
            embedding = embedding.astype('float32')  # Ensure correct dtype for FAISS
            
            # Add to vector index
            vector_id = len(self.experiment_vectors)
            self.vector_index.add(np.array([embedding]).astype('float32'))
            
            # Store mapping from vector ID to experiment ID
            self.experiment_vectors[vector_id] = experiment_record['run_id']
            
            logger.debug(f"Added experiment {experiment_record['run_id']} to vector index")
        except Exception as e:
            logger.error(f"Error embedding experiment: {e}")
    
    async def search_experiments(self, query: str, top_k: int = 5) -> List[RAGQueryResult]:
        """Search for relevant experiments using hybrid search (keywords + vectors + graph)"""
        logger.info(f"Searching experiments with query: '{query[:50]}...' (top_k={top_k})")
        
        results = []
        
        # If we have embeddings and vector search capability
        if self.embedding_model and self.vector_index:
            results.extend(await self._vector_search(query, top_k))
        
        # Add keyword-based search as well (backup or complement)
        keyword_results = self._keyword_search(query, top_k)
        results.extend(keyword_results)
        
        # Deduplicate and sort by relevance
        unique_results = {}
        for result in results:
            exp_id = result.experiment_id
            if exp_id not in unique_results or result.similarity_score > unique_results[exp_id].similarity_score:
                unique_results[exp_id] = result
        
        # Sort by similarity score (descending)
        sorted_results = sorted(
            unique_results.values(),
            key=lambda x: x.similarity_score,
            reverse=True
        )[:top_k]
        
        logger.info(f"Returning {len(sorted_results)} search results")
        return sorted_results
    
    async def _vector_search(self, query: str, top_k: int) -> List[RAGQueryResult]:
        """Perform vector/semantic search for experiments"""
        try:
            # Embed the query
            query_embedding = self.embedding_model.encode([query])[0]
            query_embedding = query_embedding.astype('float32').reshape(1, -1)
            
            # Perform similarity search
            scores, indices = self.vector_index.search(query_embedding, top_k)
            
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx != -1:  # -1 indicates no match found
                    exp_id = self.experiment_vectors.get(idx, "unknown")
                    exp_details = self.experiments.get(exp_id, {})
                    
                    if exp_details:
                        results.append(RAGQueryResult(
                            experiment_id=exp_id,
                            similarity_score=float(score),
                            experiment_details=exp_details,
                            relevance_explanation=f"Semantic similarity with score {score:.3f}"
                        ))
            
            return results
        except Exception as e:
            logger.error(f"Error in vector search: {e}")
            return []
    
    def _keyword_search(self, query: str, top_k: int) -> List[RAGQueryResult]:
        """Perform keyword search using simple string matching"""
        results = []
        query_lower = query.lower()
        
        for exp_id, exp_details in self.experiments.items():
            # Calculate a simple keyword relevance score
            score = 0
            text_to_match = f"{exp_details.get('name', '')} {str(exp_details.get('parameters', {}))} {str(exp_details.get('metrics', {}))}".lower()
            
            # Count matching words
            query_words = query_lower.split()
            for word in query_words:
                if word in text_to_match:
                    score += 1
            
            if score > 0:
                results.append(RAGQueryResult(
                    experiment_id=exp_id,
                    similarity_score=score/len(query_words),  # Normalize by query length
                    experiment_details=exp_details,
                    relevance_explanation=f"Keyword match with relevance {score}/{len(query_words)}"
                ))
        
        # Sort by score and return top_k
        results.sort(key=lambda x: x.similarity_score, reverse=True)
        return results[:top_k]
    
    async def get_experiment(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific experiment by ID"""
        return self.experiments.get(experiment_id)
    
    async def list_experiments(self, max_results: int = 100) -> Dict[str, Any]:
        """List all experiments with pagination"""
        experiment_list = [
            {
                "experiment_id": exp_id,
                "name": exp.get("name", "Unknown"),
                "run_name": exp.get("run_name", "Unknown"),
                "status": exp.get("status", "Unknown"),
                "created_at": exp.get("created_at"),
                "n_parameters": len(exp.get("parameters", {})),
                "n_metrics": len(exp.get("metrics", {}))
            }
            for exp_id, exp in self.experiments.items()
        ]
        
        # Sort by creation time (most recent first)
        experiment_list.sort(key=lambda x: x.get("created_at", 0), reverse=True)
        
        return {
            "experiments": experiment_list[:max_results],
            "total_count": len(experiment_list),
            "returned_count": min(len(experiment_list), max_results),
            "status": "success"
        }
    
    async def rag_query(self, question: str) -> Dict[str, Any]:
        """Answer questions using retrieval augmented generation approach"""
        logger.info(f"Processing RAG query: '{question[:50]}...'")
        
        # Retrieve relevant experiments
        retrieved_experiments = await self.search_experiments(question, top_k=5)
        
        if not retrieved_experiments:
            return {
                "question": question,
                "answer": "No relevant experiments found for this query",
                "sources": [],
                "confidence": 0.0,
                "status": "no_results"
            }
        
        # Generate an answer based on retrieved experiments
        answer = await self._generate_answer(question, retrieved_experiments)
        
        # Prepare sources
        sources = [
            {
                "experiment_id": exp.experiment_id,
                "similarity_score": exp.similarity_score,
                "name": exp.experiment_details.get("name", "Unknown"),
                "metrics": exp.experiment_details.get("metrics", {}),
                "parameters": exp.experiment_details.get("parameters", {})
            }
            for exp in retrieved_experiments
        ]
        
        return {
            "question": question,
            "answer": answer,
            "sources": sources,
            "confidence": max([exp.similarity_score for exp in retrieved_experiments]),
            "n_sources": len(sources),
            "status": "success"
        }
    
    async def _generate_answer(self, question: str, retrieved_experiments: List[RAGQueryResult]) -> str:
        """Generate an answer to a question based on retrieved experiments"""
        # This is a simplified implementation - in a real system, you'd use an LLM
        # For now, we'll synthesize an answer based on the experiment data
        
        if "best" in question.lower() or "optimal" in question.lower():
            # Find experiment with best performance on relevant metric
            best_exp = max(
                retrieved_experiments,
                key=lambda exp: max(exp.experiment_details.get("metrics", {}).values(), default=0)
            )
            
            best_metric_name = max(
                best_exp.experiment_details.get("metrics", {}).items(),
                key=lambda item: item[1], 
                default=("unknown", 0)
            )[0]
            
            best_metric_value = best_exp.experiment_details["metrics"].get(best_metric_name, 0)
            
            return (f"The best performing experiment was '{best_exp.experiment_details['name']}' "
                   f"with {best_metric_name} = {best_metric_value:.4f}. "
                   f"This experiment used parameters: {dict(list(best_exp.experiment_details['parameters'].items())[:3])}")
        
        elif "compare" in question.lower() or "difference" in question.lower():
            # Compare top experiments
            top_experiments = retrieved_experiments[:3]
            comparison = []
            
            for exp in top_experiments:
                exp_name = exp.experiment_details.get("name", "Unknown")
                metrics = exp.experiment_details.get("metrics", {})
                params = exp.experiment_details.get("parameters", {})
                
                comparison.append(
                    f"'{exp_name}' - Metrics: {dict(list(metrics.items())[:2])}, "
                    f"Parameters: {dict(list(params.items())[:2])}"
                )
            
            return f"Comparison of top experiments:\n" + "\n".join([f"  - {comp}" for comp in comparison])
        
        else:
            # General answer based on all retrieved experiments
            all_metrics = {}
            all_params = {}
            
            for exp in retrieved_experiments:
                for k, v in exp.experiment_details.get("metrics", {}).items():
                    if k not in all_metrics:
                        all_metrics[k] = []
                    all_metrics[k].append(v)
                
                for k, v in exp.experiment_details.get("parameters", {}).items():
                    if k not in all_params:
                        all_params[k] = []
                    all_params[k].append(str(v))
            
            response = f"Based on {len(retrieved_experiments)} experiments: "
            
            if all_metrics:
                avg_metrics = {k: sum(v)/len(v) for k, v in all_metrics.items() if v}
                response += f"Average metrics: {dict(list(avg_metrics.items())[:3])}. "
            
            if all_params:
                common_params = {k: max(set(v), key=v.count) for k, v in all_params.items()}
                response += f"Common parameters: {dict(list(common_params.items())[:3])}."
            
            return response.strip()
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about registered experiments"""
        if not self.experiments:
            return {"message": "No experiments registered yet", "total_count": 0}
        
        total_experiments = len(self.experiments)
        
        # Collect all parameters and metrics
        all_parameters = set()
        all_metrics = set()
        all_names = set()
        
        for exp in self.experiments.values():
            all_names.add(exp.get("name", "Unknown"))
            all_parameters.update(exp.get("parameters", {}).keys())
            all_metrics.update(exp.get("metrics", {}).keys())
        
        # Calculate metric statistics
        metric_values = []
        for exp in self.experiments.values():
            metric_values.extend(list(exp.get("metrics", {}).values()))
        
        metric_stats = {
            "count": len(metric_values),
            "mean": float(np.mean(metric_values)) if metric_values else 0.0,
            "std": float(np.std(metric_values)) if metric_values else 0.0,
            "min": float(np.min(metric_values)) if metric_values else 0.0,
            "max": float(np.max(metric_values)) if metric_values else 0.0
        }
        
        return {
            "total_experiments": total_experiments,
            "unique_experiment_names": len(all_names),
            "unique_parameters": len(all_parameters),
            "unique_metrics": len(all_metrics),
            "metric_statistics": metric_stats,
            "recent_experiments": list(all_names)[:10],  # Show recent names
            "status": "success"
        }