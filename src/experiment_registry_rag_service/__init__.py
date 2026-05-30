"""
Experiment Registry & RAG Service for Quantum Hybrid Research & Optimization Lab

This service handles:
- MLflow-backed registry for circuit definitions, parameters, objectives, and outcomes
- Links to datasets and problem specs
- Hybrid search over prior experiments, notes, plots, and docs
- Answering queries like "What QAOA depth worked best for this class of portfolio problems?"
"""