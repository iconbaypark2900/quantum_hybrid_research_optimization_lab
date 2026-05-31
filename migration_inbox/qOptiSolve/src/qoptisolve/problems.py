"""
Problem definitions for portfolio optimization and Max-Cut.
"""

import numpy as np
from scipy.stats import wishart
from typing import Dict, List, Tuple, Union
from dataclasses import dataclass


@dataclass
class PortfolioProblem:
    """Portfolio optimization problem definition."""
    
    returns: np.ndarray  # Expected returns for each asset
    covariances: np.ndarray  # Covariance matrix
    risk_free_rate: float = 0.02  # Risk-free rate
    target_return: float = None  # Target portfolio return
    
    def __post_init__(self):
        """Validate input data."""
        if len(self.returns) != len(self.covariances):
            raise ValueError("Returns and covariances must have same length")
        if self.covariances.shape[0] != self.covariances.shape[1]:
            raise ValueError("Covariances must be a square matrix")
    
    @property
    def n_assets(self) -> int:
        """Number of assets in portfolio."""
        return len(self.returns)
    
    def to_qaoa_format(self) -> Dict:
        """Convert to QAOA-compatible format."""
        return {
            'returns': self.returns.tolist(),
            'covariances': self.covariances.tolist(),
            'risk_free_rate': self.risk_free_rate,
            'target_return': self.target_return
        }


@dataclass
class MaxCutProblem:
    """Maximum Cut problem definition."""
    
    edges: List[Tuple[int, int]]  # List of (node1, node2) edges
    weights: List[float] = None  # Optional edge weights
    
    def __post_init__(self):
        """Validate and set default weights."""
        if self.weights is None:
            self.weights = [1.0] * len(self.edges)
        if len(self.edges) != len(self.weights):
            raise ValueError("Edges and weights must have same length")
    
    @property
    def n_nodes(self) -> int:
        """Number of nodes in the graph."""
        nodes = set()
        for edge in self.edges:
            nodes.add(edge[0])
            nodes.add(edge[1])
        return len(nodes)
    
    @property
    def adjacency_matrix(self) -> np.ndarray:
        """Get adjacency matrix representation."""
        n = self.n_nodes
        adj = np.zeros((n, n))
        for (i, j), weight in zip(self.edges, self.weights):
            adj[i, j] = weight
            adj[j, i] = weight
        return adj
    
    def to_qaoa_format(self) -> Dict:
        """Convert to QAOA-compatible format."""
        return {
            'edges': self.edges,
            'weights': self.weights,
            'n_nodes': self.n_nodes
        }


def create_sample_portfolio(n_assets: int = 5, seed: int = 42) -> PortfolioProblem:
    """Create a sample portfolio problem for testing."""
    np.random.seed(seed)
    
    # Generate random returns and covariances
    returns = np.random.normal(0.08, 0.15, n_assets)
    # Sample a random positive-definite covariance matrix from a Wishart distribution
    covariances = wishart(df=n_assets + 2, scale=np.eye(n_assets)).rvs(random_state=seed)
    
    return PortfolioProblem(
        returns=returns,
        covariances=covariances,
        risk_free_rate=0.02,
        target_return=0.10
    )


def create_sample_maxcut(n_nodes: int = 6, edge_prob: float = 0.5, seed: int = 42) -> MaxCutProblem:
    """Create a sample Max-Cut problem for testing."""
    np.random.seed(seed)
    
    edges = []
    weights = []
    
    # Generate random edges
    for i in range(n_nodes):
        for j in range(i + 1, n_nodes):
            if np.random.random() < edge_prob:
                edges.append((i, j))
                weights.append(np.random.uniform(0.5, 2.0))
    
    return MaxCutProblem(edges=edges, weights=weights)
