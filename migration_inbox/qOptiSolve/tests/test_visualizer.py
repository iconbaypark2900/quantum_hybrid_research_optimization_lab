"""
Tests for visualization tools.
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock
from qoptisolve.visualizer import QAOAVisualizer, create_comparison_table
from qoptisolve.problems import create_sample_portfolio, create_sample_maxcut


class TestQAOAVisualizer:
    """Test visualization tools."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.visualizer = QAOAVisualizer()
        self.portfolio_problem = create_sample_portfolio(n_assets=3, seed=42)
        self.maxcut_problem = create_sample_maxcut(n_nodes=4, seed=42)
        
        # Mock results
        self.portfolio_quantum_result = {
            'allocation': np.array([0.4, 0.3, 0.3]),
            'final_cost': -0.8,
            'convergence': 100
        }
        
        self.portfolio_classical_result = {
            'allocation': np.array([0.5, 0.3, 0.2]),
            'portfolio_return': 0.12,
            'portfolio_risk': 0.15,
            'objective_value': 0.7
        }
        
        self.maxcut_quantum_result = {
            'partition': np.array([0, 1, 0, 1]),
            'cut_value': 3.5,
            'final_cost': 2.8
        }
        
        self.maxcut_classical_result = {
            'partition': np.array([1, 0, 1, 0]),
            'cut_value': 3.8,
            'status': 'optimal'
        }
    
    def test_visualizer_initialization(self):
        """Test visualizer initialization."""
        assert self.visualizer.style == 'plotly'
        
        # Test different styles
        viz_matplotlib = QAOAVisualizer(style='matplotlib')
        assert viz_matplotlib.style == 'matplotlib'
        
        viz_seaborn = QAOAVisualizer(style='seaborn')
        assert viz_seaborn.style == 'seaborn'
    
    def test_portfolio_comparison_plot(self):
        """Test portfolio comparison plot creation."""
        fig = self.visualizer.plot_portfolio_comparison(
            self.portfolio_quantum_result,
            self.portfolio_classical_result,
            self.portfolio_problem
        )
        
        # Should return a Plotly figure
        assert fig is not None
        assert hasattr(fig, 'data')
        assert hasattr(fig, 'layout')
        
        # Check layout
        assert fig.layout.title.text == 'Portfolio Optimization: Quantum vs Classical'
        assert fig.layout.height == 800
    
    def test_maxcut_comparison_plot(self):
        """Test Max-Cut comparison plot creation."""
        fig = self.visualizer.plot_maxcut_comparison(
            self.maxcut_quantum_result,
            self.maxcut_classical_result,
            self.maxcut_problem
        )
        
        # Should return a Plotly figure
        assert fig is not None
        assert hasattr(fig, 'data')
        assert hasattr(fig, 'layout')
        
        # Check layout
        assert fig.layout.title.text == 'Max-Cut Problem: Quantum vs Classical'
        assert fig.layout.height == 800
    
    def test_convergence_plot(self):
        """Test convergence plot creation."""
        optimization_history = [1.0, 0.8, 0.6, 0.5, 0.4]
        
        fig = self.visualizer.plot_convergence(
            optimization_history,
            title="Test Convergence"
        )
        
        # Should return a Plotly figure
        assert fig is not None
        assert hasattr(fig, 'data')
        assert hasattr(fig, 'layout')
        
        # Check layout
        assert fig.layout.title.text == "Test Convergence"
        assert fig.layout.height == 500
    
    def test_circuit_plot(self):
        """Test circuit plot creation (placeholder)."""
        mock_circuit = Mock()
        
        fig = self.visualizer.plot_circuit(
            mock_circuit,
            title="Test Circuit"
        )
        
        # Should return a Plotly figure
        assert fig is not None
        assert hasattr(fig, 'data')
        assert hasattr(fig, 'layout')
        
        # Check layout
        assert fig.layout.title.text == "Test Circuit"
        assert fig.layout.height == 400
    
    def test_portfolio_plot_with_none_results(self):
        """Test portfolio plot with None results."""
        none_result = {'allocation': None}
        
        fig = self.visualizer.plot_portfolio_comparison(
            none_result,
            self.portfolio_classical_result,
            self.portfolio_problem
        )
        
        # Should still create a figure
        assert fig is not None
        assert hasattr(fig, 'data')
    
    def test_maxcut_plot_with_none_results(self):
        """Test Max-Cut plot with None results."""
        none_result = {'partition': None}
        
        fig = self.visualizer.plot_maxcut_comparison(
            none_result,
            self.maxcut_classical_result,
            self.maxcut_problem
        )
        
        # Should still create a figure
        assert fig is not None
        assert hasattr(fig, 'data')


class TestComparisonTable:
    """Test comparison table creation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.portfolio_problem = create_sample_portfolio(n_assets=3, seed=42)
        self.maxcut_problem = create_sample_maxcut(n_nodes=4, seed=42)
        
        self.portfolio_quantum_result = {
            'allocation': np.array([0.4, 0.3, 0.3]),
            'final_cost': -0.8
        }
        
        self.portfolio_classical_result = {
            'portfolio_return': 0.12,
            'portfolio_risk': 0.15,
            'objective_value': 0.7
        }
        
        self.maxcut_quantum_result = {
            'partition': np.array([0, 1, 0, 1]),
            'cut_value': 3.5
        }
        
        self.maxcut_classical_result = {
            'partition': np.array([1, 0, 1, 0]),
            'cut_value': 3.8,
            'status': 'optimal'
        }
    
    def test_portfolio_comparison_table(self):
        """Test portfolio comparison table creation."""
        df = create_comparison_table(
            self.portfolio_quantum_result,
            self.portfolio_classical_result,
            'portfolio'
        )
        
        # Should return a DataFrame
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 5  # 5 metrics
        
        # Check columns
        assert 'Metric' in df.columns
        assert 'Quantum (QAOA)' in df.columns
        assert 'Classical' in df.columns
        
        # Check metrics
        metrics = df['Metric'].tolist()
        assert 'Method' in metrics
        assert 'Objective Value' in metrics
        assert 'Portfolio Return' in metrics
        assert 'Portfolio Risk' in metrics
        assert 'Sharpe Ratio' in metrics
    
    def test_maxcut_comparison_table(self):
        """Test Max-Cut comparison table creation."""
        df = create_comparison_table(
            self.maxcut_quantum_result,
            self.maxcut_classical_result,
            'maxcut'
        )
        
        # Should return a DataFrame
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 4  # 4 metrics
        
        # Check columns
        assert 'Metric' in df.columns
        assert 'Quantum (QAOA)' in df.columns
        assert 'Classical' in df.columns
        
        # Check metrics
        metrics = df['Metric'].tolist()
        assert 'Method' in metrics
        assert 'Cut Value' in metrics
        assert 'Partition' in metrics
        assert 'Status' in metrics
    
    def test_comparison_table_values(self):
        """Test that comparison table has correct values."""
        df = create_comparison_table(
            self.portfolio_quantum_result,
            self.portfolio_classical_result,
            'portfolio'
        )
        
        # Check quantum values
        quantum_row = df[df['Metric'] == 'Method']['Quantum (QAOA)'].iloc[0]
        assert quantum_row == 'QAOA'
        
        objective_row = df[df['Metric'] == 'Objective Value']['Quantum (QAOA)'].iloc[0]
        assert objective_row == -0.8
        
        # Check classical values
        classical_row = df[df['Metric'] == 'Method']['Classical'].iloc[0]
        assert classical_row == 'Convex Optimization'
        
        return_row = df[df['Metric'] == 'Portfolio Return']['Classical'].iloc[0]
        assert return_row == 0.12


class TestVisualizationIntegration:
    """Test integration between visualization components."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.visualizer = QAOAVisualizer()
        self.portfolio_problem = create_sample_portfolio(n_assets=3, seed=42)
        self.maxcut_problem = create_sample_maxcut(n_nodes=4, seed=42)
    
    def test_portfolio_visualization_pipeline(self):
        """Test complete portfolio visualization pipeline."""
        # Create mock results
        quantum_result = {
            'allocation': np.array([0.4, 0.3, 0.3]),
            'final_cost': -0.8,
            'convergence': 100
        }
        
        classical_result = {
            'allocation': np.array([0.5, 0.3, 0.2]),
            'portfolio_return': 0.12,
            'portfolio_risk': 0.15,
            'objective_value': 0.7
        }
        
        # Create plot
        fig = self.visualizer.plot_portfolio_comparison(
            quantum_result, classical_result, self.portfolio_problem
        )
        
        # Create table
        df = create_comparison_table(
            quantum_result, classical_result, 'portfolio'
        )
        
        # Both should work
        assert fig is not None
        assert df is not None
        assert len(df) > 0
    
    def test_maxcut_visualization_pipeline(self):
        """Test complete Max-Cut visualization pipeline."""
        # Create mock results
        quantum_result = {
            'partition': np.array([0, 1, 0, 1]),
            'cut_value': 3.5,
            'final_cost': 2.8
        }
        
        classical_result = {
            'partition': np.array([1, 0, 1, 0]),
            'cut_value': 3.8,
            'status': 'optimal'
        }
        
        # Create plot
        fig = self.visualizer.plot_maxcut_comparison(
            quantum_result, classical_result, self.maxcut_problem
        )
        
        # Create table
        df = create_comparison_table(
            quantum_result, classical_result, 'maxcut'
        )
        
        # Both should work
        assert fig is not None
        assert df is not None
        assert len(df) > 0
