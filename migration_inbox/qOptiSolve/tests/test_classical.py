"""
Tests for classical optimization solvers.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch
from qoptisolve.classical import (
    ClassicalPortfolioSolver, ClassicalMaxCutSolver,
    solve_portfolio_greedy, solve_maxcut_greedy
)
from qoptisolve.problems import create_sample_portfolio, create_sample_maxcut


class TestClassicalPortfolioSolver:
    """Test classical portfolio solver."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.solver = ClassicalPortfolioSolver()
        self.problem = create_sample_portfolio(n_assets=3, seed=42)
    
    @patch('qoptisolve.classical.cp')
    def test_portfolio_solve_sharpe(self, mock_cp):
        """Test portfolio solving with Sharpe ratio objective."""
        # Mock CVXPY components
        mock_weights = Mock()
        mock_weights.value = np.array([0.4, 0.3, 0.3])
        
        mock_problem = Mock()
        mock_problem.solve.return_value = None
        mock_problem.status = 'optimal'
        mock_problem.value = 0.8
        
        mock_cp.Variable.return_value = mock_weights
        mock_cp.Problem.return_value = mock_problem
        mock_cp.Maximize.return_value = "maximize_obj"
        
        # Solve
        result = self.solver.solve(self.problem, objective='sharpe')
        
        assert result['status'] == 'optimal'
        assert result['allocation'] is not None
        assert result['objective_value'] == 0.8
        assert result['portfolio_return'] is not None
        assert result['portfolio_risk'] is not None
    
    @patch('qoptisolve.classical.cp')
    def test_portfolio_solve_min_risk(self, mock_cp):
        """Test portfolio solving with minimum risk objective."""
        # Mock CVXPY components
        mock_weights = Mock()
        mock_weights.value = np.array([0.5, 0.3, 0.2])
        
        mock_problem = Mock()
        mock_problem.solve.return_value = None
        mock_problem.status = 'optimal'
        mock_problem.value = 0.15
        
        mock_cp.Variable.return_value = mock_weights
        mock_cp.Problem.return_value = mock_problem
        mock_cp.Minimize.return_value = "minimize_obj"
        
        # Solve
        result = self.solver.solve(self.problem, objective='min_risk')
        
        assert result['status'] == 'optimal'
        assert result['allocation'] is not None
        assert result['objective_value'] == 0.15
    
    @patch('qoptisolve.classical.cp')
    def test_portfolio_solve_max_return(self, mock_cp):
        """Test portfolio solving with maximum return objective."""
        # Mock CVXPY components
        mock_weights = Mock()
        mock_weights.value = np.array([0.6, 0.2, 0.2])
        
        mock_problem = Mock()
        mock_problem.solve.return_value = None
        mock_problem.status = 'optimal'
        mock_problem.value = -0.12
        
        mock_cp.Variable.return_value = mock_weights
        mock_cp.Problem.return_value = mock_problem
        mock_cp.Minimize.return_value = "minimize_obj"
        
        # Solve
        result = self.solver.solve(self.problem, objective='max_return')
        
        assert result['status'] == 'optimal'
        assert result['allocation'] is not None
        assert result['objective_value'] == -0.12
    
    def test_invalid_objective(self):
        """Test that invalid objective raises error."""
        with pytest.raises(ValueError):
            self.solver.solve(self.problem, objective='invalid')
    
    @patch('qoptisolve.classical.cp')
    def test_portfolio_solve_failure(self, mock_cp):
        """Test portfolio solving when optimization fails."""
        # Mock CVXPY components
        mock_weights = Mock()
        mock_weights.value = None
        
        mock_problem = Mock()
        mock_problem.solve.return_value = None
        mock_problem.status = 'infeasible'
        mock_problem.value = None
        
        mock_cp.Variable.return_value = mock_weights
        mock_cp.Problem.return_value = mock_problem
        mock_cp.Maximize.return_value = "maximize_obj"
        
        # Solve
        result = self.solver.solve(self.problem, objective='sharpe')
        
        assert result['status'] == 'infeasible'
        assert result['allocation'] is None
        assert result['objective_value'] is None


class TestClassicalMaxCutSolver:
    """Test classical Max-Cut solver."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.solver = ClassicalMaxCutSolver()
        self.problem = create_sample_maxcut(n_nodes=4, seed=42)
    
    @patch('qoptisolve.classical.cp')
    def test_maxcut_solve_success(self, mock_cp):
        """Test Max-Cut solving when successful."""
        # Mock CVXPY components
        mock_x = Mock()
        mock_x.value = np.array([0, 1, 0, 1])
        
        mock_problem = Mock()
        mock_problem.solve.return_value = None
        mock_problem.status = 'optimal'
        mock_problem.value = 3.5
        
        mock_cp.Variable.return_value = mock_x
        mock_cp.Problem.return_value = mock_problem
        mock_cp.Maximize.return_value = "maximize_obj"
        
        # Solve
        result = self.solver.solve(self.problem)
        
        assert result['status'] == 'optimal'
        assert result['partition'] is not None
        assert result['cut_value'] == 3.5
    
    @patch('qoptisolve.classical.cp')
    def test_maxcut_solve_failure(self, mock_cp):
        """Test Max-Cut solving when optimization fails."""
        # Mock CVXPY components
        mock_x = Mock()
        mock_x.value = None
        
        mock_problem = Mock()
        mock_problem.solve.return_value = None
        mock_problem.status = 'infeasible'
        mock_problem.value = None
        
        mock_cp.Variable.return_value = mock_x
        mock_cp.Problem.return_value = mock_problem
        mock_cp.Maximize.return_value = "maximize_obj"
        
        # Solve
        result = self.solver.solve(self.problem)
        
        assert result['status'] == 'infeasible'
        assert result['partition'] is None
        assert result['cut_value'] is None


class TestGreedySolvers:
    """Test greedy optimization approaches."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.portfolio_problem = create_sample_portfolio(n_assets=4, seed=42)
        self.maxcut_problem = create_sample_maxcut(n_nodes=5, seed=42)
    
    def test_portfolio_greedy(self):
        """Test greedy portfolio optimization."""
        result = solve_portfolio_greedy(self.portfolio_problem)
        
        assert result['allocation'] is not None
        assert result['portfolio_return'] is not None
        assert result['portfolio_risk'] is not None
        assert result['sharpe_ratio'] is not None
        assert result['method'] == 'greedy'
        
        # Check allocation constraints
        allocation = result['allocation']
        assert np.allclose(np.sum(allocation), 1.0, atol=1e-6)
        assert np.all(allocation >= 0)
        
        # Should allocate to top assets
        assert np.sum(allocation > 0) <= 3  # Top 3 assets
    
    def test_maxcut_greedy(self):
        """Test greedy Max-Cut optimization."""
        result = solve_maxcut_greedy(self.maxcut_problem)
        
        assert result['partition'] is not None
        assert result['cut_value'] is not None
        assert result['method'] == 'greedy'
        
        # Check partition constraints
        partition = result['partition']
        assert np.all(np.logical_or(partition == 0, partition == 1))
        
        # Cut value should be non-negative
        assert result['cut_value'] >= 0
    
    def test_greedy_reproducibility(self):
        """Test that greedy solvers are reproducible with same seed."""
        np.random.seed(42)
        result1 = solve_portfolio_greedy(self.portfolio_problem)
        
        np.random.seed(42)
        result2 = solve_portfolio_greedy(self.portfolio_problem)
        
        np.testing.assert_array_equal(result1['allocation'], result2['allocation'])
        assert result1['portfolio_return'] == result2['portfolio_return']
        assert result1['portfolio_risk'] == result2['portfolio_risk']


class TestSolverIntegration:
    """Test integration between different solvers."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.portfolio_problem = create_sample_portfolio(n_assets=3, seed=42)
        self.maxcut_problem = create_sample_maxcut(n_nodes=4, seed=42)
    
    def test_portfolio_solver_comparison(self):
        """Test that different portfolio solvers can be compared."""
        greedy_result = solve_portfolio_greedy(self.portfolio_problem)
        
        # Both should return valid allocations
        assert greedy_result['allocation'] is not None
        assert greedy_result['portfolio_return'] is not None
        assert greedy_result['portfolio_risk'] is not None
        
        # Greedy should be fast but potentially suboptimal
        assert greedy_result['method'] == 'greedy'
    
    def test_maxcut_solver_comparison(self):
        """Test that different Max-Cut solvers can be compared."""
        greedy_result = solve_maxcut_greedy(self.maxcut_problem)
        
        # Should return valid partition
        assert greedy_result['partition'] is not None
        assert greedy_result['cut_value'] is not None
        
        # Greedy should be fast but potentially suboptimal
        assert greedy_result['method'] == 'greedy'
