"""
Tests for pipeline integration.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch
from qoptisolve.problems import create_sample_portfolio, create_sample_maxcut
from qoptisolve.qaoa import QAOA
from qoptisolve.classical import ClassicalPortfolioSolver, ClassicalMaxCutSolver
from qoptisolve.visualizer import QAOAVisualizer, create_comparison_table


class TestPortfolioPipeline:
    """Test complete portfolio optimization pipeline."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.problem = create_sample_portfolio(n_assets=3, seed=42)
        self.qaoa = QAOA(shots=100)
        self.classical_solver = ClassicalPortfolioSolver()
        self.visualizer = QAOAVisualizer()
    
    @patch('qoptisolve.qaoa.execute')
    @patch('qoptisolve.qaoa.SPSA')
    @patch('qoptisolve.classical.cp')
    def test_complete_portfolio_pipeline(self, mock_cp, mock_spsa, mock_execute):
        """Test complete portfolio optimization pipeline."""
        # Mock QAOA
        mock_optimizer = Mock()
        mock_optimizer.minimize.return_value = Mock(
            x=np.array([1.0, 2.0]),
            fun=-0.6,
            nfev=80
        )
        mock_spsa.return_value = mock_optimizer
        
        mock_job = Mock()
        mock_job.result.return_value = Mock(
            get_counts=lambda: {'000': 60, '001': 30, '010': 10}
        )
        mock_execute.return_value = mock_job
        
        # Mock classical solver
        mock_weights = Mock()
        mock_weights.value = np.array([0.5, 0.3, 0.2])
        
        mock_problem = Mock()
        mock_problem.solve.return_value = None
        mock_problem.status = 'optimal'
        mock_problem.value = 0.7
        
        mock_cp.Variable.return_value = mock_weights
        mock_cp.Problem.return_value = mock_problem
        mock_cp.Maximize.return_value = "maximize_obj"
        
        # Run QAOA
        quantum_result = self.qaoa.solve_portfolio(
            self.problem, p=1, optimizer='SPSA', max_iter=80
        )
        
        # Run classical solver
        classical_result = self.classical_solver.solve(self.problem, objective='sharpe')
        
        # Create visualization
        fig = self.visualizer.plot_portfolio_comparison(
            quantum_result, classical_result, self.problem
        )
        
        # Create comparison table
        df = create_comparison_table(
            quantum_result, classical_result, 'portfolio'
        )
        
        # Validate results
        assert quantum_result['allocation'] is not None
        assert classical_result['allocation'] is not None
        assert fig is not None
        assert df is not None
        assert len(df) > 0
        
        # Check that we can compare solutions
        assert quantum_result['final_cost'] == -0.6
        assert classical_result['objective_value'] == 0.7
    
    def test_portfolio_problem_creation(self):
        """Test portfolio problem creation and validation."""
        assert self.problem.n_assets == 3
        assert self.problem.returns.shape == (3,)
        assert self.problem.covariances.shape == (3, 3)
        assert self.problem.risk_free_rate == 0.02
        assert self.problem.target_return == 0.10
    
    def test_portfolio_serialization(self):
        """Test portfolio problem serialization."""
        qaoa_format = self.problem.to_qaoa_format()
        
        assert 'returns' in qaoa_format
        assert 'covariances' in qaoa_format
        assert 'risk_free_rate' in qaoa_format
        assert 'target_return' in qaoa_format


class TestMaxCutPipeline:
    """Test complete Max-Cut optimization pipeline."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.problem = create_sample_maxcut(n_nodes=4, seed=42)
        self.qaoa = QAOA(shots=100)
        self.classical_solver = ClassicalMaxCutSolver()
        self.visualizer = QAOAVisualizer()
    
    @patch('qoptisolve.qaoa.execute')
    @patch('qoptisolve.qaoa.SPSA')
    @patch('qoptisolve.classical.cp')
    def test_complete_maxcut_pipeline(self, mock_cp, mock_spsa, mock_execute):
        """Test complete Max-Cut optimization pipeline."""
        # Mock QAOA
        mock_optimizer = Mock()
        mock_optimizer.minimize.return_value = Mock(
            x=np.array([1.0, 2.0]),
            fun=-2.5,
            nfev=90
        )
        mock_spsa.return_value = mock_optimizer
        
        mock_job = Mock()
        mock_job.result.return_value = Mock(
            get_counts=lambda: {'0000': 50, '0001': 30, '0010': 20}
        )
        mock_execute.return_value = mock_job
        
        # Mock classical solver
        mock_x = Mock()
        mock_x.value = np.array([0, 1, 0, 1])
        
        mock_problem = Mock()
        mock_problem.solve.return_value = None
        mock_problem.status = 'optimal'
        mock_problem.value = 3.0
        
        mock_cp.Variable.return_value = mock_x
        mock_cp.Problem.return_value = mock_problem
        mock_cp.Maximize.return_value = "maximize_obj"
        
        # Run QAOA
        quantum_result = self.qaoa.solve_maxcut(
            self.problem, p=1, optimizer='SPSA', max_iter=90
        )
        
        # Run classical solver
        classical_result = self.classical_solver.solve(self.problem)
        
        # Create visualization
        fig = self.visualizer.plot_maxcut_comparison(
            quantum_result, classical_result, self.problem
        )
        
        # Create comparison table
        df = create_comparison_table(
            quantum_result, classical_result, 'maxcut'
        )
        
        # Validate results
        assert quantum_result['partition'] is not None
        assert classical_result['partition'] is not None
        assert fig is not None
        assert df is not None
        assert len(df) > 0
        
        # Check that we can compare solutions
        assert quantum_result['final_cost'] == 2.5
        assert classical_result['cut_value'] == 3.0
    
    def test_maxcut_problem_creation(self):
        """Test Max-Cut problem creation and validation."""
        assert self.problem.n_nodes == 4
        assert len(self.problem.edges) > 0
        assert len(self.problem.weights) == len(self.problem.edges)
        assert all(w > 0 for w in self.problem.weights)
    
    def test_maxcut_serialization(self):
        """Test Max-Cut problem serialization."""
        qaoa_format = self.problem.to_qaoa_format()
        
        assert 'edges' in qaoa_format
        assert 'weights' in qaoa_format
        assert 'n_nodes' in qaoa_format
    
    def test_adjacency_matrix(self):
        """Test adjacency matrix generation."""
        adj = self.problem.adjacency_matrix
        
        assert adj.shape == (4, 4)
        assert np.allclose(adj, adj.T)  # Should be symmetric
        assert np.all(np.diag(adj) == 0)  # No self-loops


class TestPipelineRobustness:
    """Test pipeline robustness and error handling."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.portfolio_problem = create_sample_portfolio(n_assets=3, seed=42)
        self.maxcut_problem = create_sample_maxcut(n_nodes=4, seed=42)
        self.qaoa = QAOA(shots=100)
        self.visualizer = QAOAVisualizer()
    
    def test_pipeline_with_invalid_parameters(self):
        """Test pipeline behavior with invalid parameters."""
        # Test with invalid QAOA depth
        with pytest.raises(ValueError):
            self.qaoa.solve_portfolio(
                self.portfolio_problem, optimizer='invalid'
            )
        
        with pytest.raises(ValueError):
            self.qaoa.solve_maxcut(
                self.maxcut_problem, optimizer='invalid'
            )
    
    def test_visualization_with_missing_data(self):
        """Test visualization with missing or incomplete data."""
        # Test with minimal data
        minimal_quantum = {'allocation': np.array([0.5, 0.3, 0.2])}
        minimal_classical = {'allocation': np.array([0.4, 0.4, 0.2])}
        
        # Should not crash
        fig = self.visualizer.plot_portfolio_comparison(
            minimal_quantum, minimal_classical, self.portfolio_problem
        )
        
        assert fig is not None
    
    def test_comparison_table_with_missing_data(self):
        """Test comparison table with missing data."""
        # Test with minimal data
        minimal_quantum = {'allocation': np.array([0.5, 0.3, 0.2])}
        minimal_classical = {'portfolio_return': 0.1, 'portfolio_risk': 0.2}
        
        # Should not crash
        df = create_comparison_table(
            minimal_quantum, minimal_classical, 'portfolio'
        )
        
        assert df is not None
        assert len(df) > 0


class TestPipelinePerformance:
    """Test pipeline performance characteristics."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.portfolio_problem = create_sample_portfolio(n_assets=5, seed=42)
        self.maxcut_problem = create_sample_maxcut(n_nodes=6, seed=42)
        self.qaoa = QAOA(shots=100)
    
    def test_circuit_creation_performance(self):
        """Test that circuit creation is reasonably fast."""
        import time
        
        start_time = time.time()
        circuit = self.qaoa.create_portfolio_circuit(self.portfolio_problem, p=2)
        portfolio_time = time.time() - start_time
        
        start_time = time.time()
        circuit = self.qaoa.create_maxcut_circuit(self.maxcut_problem, p=2)
        maxcut_time = time.time() - start_time
        
        # Should be reasonably fast (less than 1 second)
        assert portfolio_time < 1.0
        assert maxcut_time < 1.0
        
        # Check circuit properties
        assert circuit.num_qubits == 6
        assert circuit.num_clbits == 6
    
    def test_problem_scaling(self):
        """Test that problems scale reasonably."""
        # Test with larger problems
        large_portfolio = create_sample_portfolio(n_assets=10, seed=42)
        large_maxcut = create_sample_maxcut(n_nodes=12, seed=42)
        
        # Should not crash
        assert large_portfolio.n_assets == 10
        assert large_maxcut.n_nodes == 12
        
        # Check that serialization still works
        portfolio_format = large_portfolio.to_qaoa_format()
        maxcut_format = large_maxcut.to_qaoa_format()
        
        assert 'returns' in portfolio_format
        assert 'edges' in maxcut_format
