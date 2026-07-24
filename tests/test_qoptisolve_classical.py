"""
Tests for classical optimization solvers.

Ported from qOptiSolve (migration_inbox/qOptiSolve/tests/test_classical.py).
"""

import pytest
import numpy as np
from unittest.mock import Mock, MagicMock, patch
from src.optimization.classical import (
    ClassicalPortfolioSolver, ClassicalMaxCutSolver,
    solve_portfolio_greedy, solve_maxcut_greedy
)
from src.optimization.problems import create_sample_portfolio, create_sample_maxcut


class TestClassicalPortfolioSolver:
    """Test classical portfolio solver (integration tests using real cvxpy)."""

    def setup_method(self):
        """Set up test fixtures."""
        self.solver = ClassicalPortfolioSolver()
        np.random.seed(42)
        returns = np.array([0.06, 0.09, 0.12])
        covariances = np.array([
            [0.04, 0.01, 0.02],
            [0.01, 0.09, 0.03],
            [0.02, 0.03, 0.16]
        ])
        from src.optimization.problems import PortfolioProblem
        self.problem = PortfolioProblem(returns=returns, covariances=covariances,
                                        risk_free_rate=0.02, target_return=0.08)

    def test_portfolio_solve_sharpe(self):
        """Test portfolio solving with Sharpe ratio objective."""
        result = self.solver.solve(self.problem, objective='sharpe')

        assert result['status'] == 'optimal'
        assert result['allocation'] is not None
        assert result['objective_value'] is not None
        assert result['portfolio_return'] is not None
        assert result['portfolio_risk'] is not None

    def test_portfolio_solve_min_risk(self):
        """Test portfolio solving with minimum risk objective."""
        result = self.solver.solve(self.problem, objective='min_risk')

        assert result['status'] == 'optimal'
        assert result['allocation'] is not None
        assert result['objective_value'] is not None

    def test_portfolio_solve_max_return(self):
        """Test portfolio solving with maximum return objective."""
        result = self.solver.solve(self.problem, objective='max_return')

        assert result['status'] == 'optimal'
        assert result['allocation'] is not None
        assert result['objective_value'] is not None

    def test_invalid_objective(self):
        """Test that invalid objective raises error."""
        with pytest.raises(ValueError):
            self.solver.solve(self.problem, objective='invalid')

    def test_portfolio_allocation_sums_to_one(self):
        """Test that optimal allocation sums to 1."""
        result = self.solver.solve(self.problem, objective='min_risk')

        if result['status'] == 'optimal' and result['allocation'] is not None:
            assert abs(np.sum(result['allocation']) - 1.0) < 1e-4


class TestClassicalMaxCutSolver:
    """Test classical Max-Cut solver (small problem, CVXPY boolean)."""

    def setup_method(self):
        """Set up test fixtures."""
        self.solver = ClassicalMaxCutSolver()
        self.problem = create_sample_maxcut(n_nodes=4, seed=42)

    def test_maxcut_solve_returns_dict(self):
        """Test that Max-Cut solver returns a dict with expected keys."""
        result = self.solver.solve(self.problem)

        assert isinstance(result, dict)
        assert 'status' in result
        assert 'partition' in result
        assert 'cut_value' in result

    def test_maxcut_solve_status(self):
        """Test Max-Cut solver status is a known value."""
        result = self.solver.solve(self.problem)

        assert result['status'] in ('optimal', 'infeasible', 'error', 'optimal_inaccurate')


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

        allocation = result['allocation']
        assert np.allclose(np.sum(allocation), 1.0, atol=1e-6)
        assert np.all(allocation >= 0)
        assert np.sum(allocation > 0) <= 3

    def test_maxcut_greedy(self):
        """Test greedy Max-Cut optimization."""
        result = solve_maxcut_greedy(self.maxcut_problem)

        assert result['partition'] is not None
        assert result['cut_value'] is not None
        assert result['method'] == 'greedy'

        partition = result['partition']
        assert np.all(np.logical_or(partition == 0, partition == 1))
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

        assert greedy_result['allocation'] is not None
        assert greedy_result['portfolio_return'] is not None
        assert greedy_result['portfolio_risk'] is not None
        assert greedy_result['method'] == 'greedy'

    def test_maxcut_solver_comparison(self):
        """Test that different Max-Cut solvers can be compared."""
        greedy_result = solve_maxcut_greedy(self.maxcut_problem)

        assert greedy_result['partition'] is not None
        assert greedy_result['cut_value'] is not None
        assert greedy_result['method'] == 'greedy'
