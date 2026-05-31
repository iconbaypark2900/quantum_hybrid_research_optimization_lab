"""
Tests for problem definitions.
"""

import pytest
import numpy as np
from qoptisolve.problems import (
    PortfolioProblem, MaxCutProblem, 
    create_sample_portfolio, create_sample_maxcut
)


class TestPortfolioProblem:
    """Test portfolio problem creation and validation."""
    
    def test_portfolio_creation(self):
        """Test basic portfolio problem creation."""
        returns = np.array([0.08, 0.12, 0.15])
        covariances = np.array([
            [0.04, 0.02, 0.01],
            [0.02, 0.09, 0.03],
            [0.01, 0.03, 0.16]
        ])
        
        problem = PortfolioProblem(returns=returns, covariances=covariances)
        
        assert problem.n_assets == 3
        assert problem.risk_free_rate == 0.02
        assert problem.target_return is None
        np.testing.assert_array_equal(problem.returns, returns)
        np.testing.assert_array_equal(problem.covariances, covariances)
    
    def test_portfolio_validation(self):
        """Test portfolio problem validation."""
        returns = np.array([0.08, 0.12])
        covariances = np.array([[0.04, 0.02], [0.02, 0.09]])
        
        # Should work
        problem = PortfolioProblem(returns=returns, covariances=covariances)
        assert problem.n_assets == 2
        
        # Should fail - mismatched dimensions
        with pytest.raises(ValueError):
            PortfolioProblem(returns=returns, covariances=np.eye(3))
        
        # Should fail - non-square covariance
        with pytest.raises(ValueError):
            PortfolioProblem(returns=returns, covariances=np.array([[0.04, 0.02, 0.01]]))
    
    def test_sample_portfolio(self):
        """Test sample portfolio creation."""
        problem = create_sample_portfolio(n_assets=4, seed=42)
        
        assert problem.n_assets == 4
        assert problem.returns.shape == (4,)
        assert problem.covariances.shape == (4, 4)
        assert problem.risk_free_rate == 0.02
        assert problem.target_return == 0.10


class TestMaxCutProblem:
    """Test Max-Cut problem creation and validation."""
    
    def test_maxcut_creation(self):
        """Test basic Max-Cut problem creation."""
        edges = [(0, 1), (1, 2), (2, 0)]
        weights = [1.0, 2.0, 1.5]
        
        problem = MaxCutProblem(edges=edges, weights=weights)
        
        assert problem.n_nodes == 3
        assert len(problem.edges) == 3
        assert len(problem.weights) == 3
        np.testing.assert_array_equal(problem.weights, weights)
    
    def test_maxcut_default_weights(self):
        """Test Max-Cut with default weights."""
        edges = [(0, 1), (1, 2)]
        
        problem = MaxCutProblem(edges=edges)
        
        assert problem.n_nodes == 3
        assert len(problem.edges) == 2
        assert len(problem.weights) == 2
        assert all(w == 1.0 for w in problem.weights)
    
    def test_maxcut_validation(self):
        """Test Max-Cut problem validation."""
        edges = [(0, 1), (1, 2)]
        weights = [1.0, 2.0, 3.0]  # Mismatched
        
        with pytest.raises(ValueError):
            MaxCutProblem(edges=edges, weights=weights)
    
    def test_adjacency_matrix(self):
        """Test adjacency matrix generation."""
        edges = [(0, 1), (1, 2)]
        weights = [1.0, 2.0]
        
        problem = MaxCutProblem(edges=edges, weights=weights)
        adj = problem.adjacency_matrix
        
        assert adj.shape == (3, 3)
        assert adj[0, 1] == 1.0
        assert adj[1, 0] == 1.0
        assert adj[1, 2] == 2.0
        assert adj[2, 1] == 2.0
        assert adj[0, 0] == 0.0  # No self-loops
    
    def test_sample_maxcut(self):
        """Test sample Max-Cut creation."""
        problem = create_sample_maxcut(n_nodes=5, edge_prob=0.6, seed=42)
        
        assert problem.n_nodes == 5
        assert len(problem.edges) > 0
        assert len(problem.weights) == len(problem.edges)
        assert all(w > 0 for w in problem.weights)


class TestProblemSerialization:
    """Test problem serialization to QAOA format."""
    
    def test_portfolio_serialization(self):
        """Test portfolio problem serialization."""
        returns = np.array([0.08, 0.12])
        covariances = np.array([[0.04, 0.02], [0.02, 0.09]])
        
        problem = PortfolioProblem(returns=returns, covariances=covariances)
        qaoa_format = problem.to_qaoa_format()
        
        assert 'returns' in qaoa_format
        assert 'covariances' in qaoa_format
        assert 'risk_free_rate' in qaoa_format
        assert qaoa_format['risk_free_rate'] == 0.02
    
    def test_maxcut_serialization(self):
        """Test Max-Cut problem serialization."""
        edges = [(0, 1), (1, 2)]
        weights = [1.0, 2.0]
        
        problem = MaxCutProblem(edges=edges, weights=weights)
        qaoa_format = problem.to_qaoa_format()
        
        assert 'edges' in qaoa_format
        assert 'weights' in qaoa_format
        assert 'n_nodes' in qaoa_format
        assert qaoa_format['n_nodes'] == 3
