"""
Problem definitions for portfolio optimization and Max-Cut.

Imported from qOptiSolve (migration_inbox/qOptiSolve/src/qoptisolve/problems.py).
"""

import numpy as np
from scipy.stats import wishart
from typing import Dict, List, Tuple, Union
from dataclasses import dataclass


@dataclass
class PortfolioProblem:
    """Portfolio optimization problem definition."""

    returns: np.ndarray
    covariances: np.ndarray
    risk_free_rate: float = 0.02
    target_return: float = None

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

    edges: List[Tuple[int, int]]
    weights: List[float] = None
    num_nodes: int = None

    def __post_init__(self):
        """Validate and set default weights."""
        if self.weights is None:
            self.weights = [1.0] * len(self.edges)
        if len(self.edges) != len(self.weights):
            raise ValueError("Edges and weights must have same length")
        if self.num_nodes is not None and self.num_nodes < self._min_nodes():
            raise ValueError(
                f"num_nodes={self.num_nodes} is smaller than the largest node "
                f"index in edges ({self._min_nodes() - 1})")

    def _min_nodes(self) -> int:
        """Smallest node count consistent with the edge list."""
        return max((max(e) for e in self.edges), default=-1) + 1

    @property
    def n_nodes(self) -> int:
        """Number of nodes in the graph.

        This counted *distinct nodes appearing in an edge*, which silently
        loses isolated nodes: create_sample_maxcut(n_nodes=6, edge_prob=0.2)
        returned a problem reporting 4. Every consumer sizes itself from this
        -- QAOA builds one qubit per node, the MILP solver one variable, the
        brute-force oracle enumerates 2**n -- so all three quietly solved a
        smaller problem than the caller asked for, and none of them could tell.

        It is now the declared count when there is one, and otherwise the
        smallest count consistent with the edge indices (max index + 1, which
        also tolerates a gap in the middle). An isolated node is genuinely
        unrecoverable from an edge list alone, so callers that care must
        declare it -- create_sample_maxcut now does.
        """
        return self.num_nodes if self.num_nodes is not None else self._min_nodes()

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

    returns = np.random.normal(0.08, 0.15, n_assets)
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

    for i in range(n_nodes):
        for j in range(i + 1, n_nodes):
            if np.random.random() < edge_prob:
                edges.append((i, j))
                weights.append(np.random.uniform(0.5, 2.0))

    # num_nodes is passed explicitly: a node can be isolated at this edge
    # probability, and an edge list cannot express that it exists.
    return MaxCutProblem(edges=edges, weights=weights, num_nodes=n_nodes)
