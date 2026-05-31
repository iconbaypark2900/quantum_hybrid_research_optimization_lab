"""
Visualization tools for QAOA results and comparisons.
"""

import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import seaborn as sns


class QAOAVisualizer:
    """Visualization tools for QAOA results."""
    
    def __init__(self, style: str = 'plotly'):
        """
        Initialize visualizer.
        
        Args:
            style: Plotting style ('plotly', 'matplotlib', 'seaborn')
        """
        self.style = style
        
        if style == 'matplotlib':
            plt.style.use('seaborn-v0_8')
        elif style == 'seaborn':
            sns.set_theme()
    
    def plot_portfolio_comparison(self, quantum_result: Dict, classical_result: Dict, 
                                problem: 'PortfolioProblem') -> go.Figure:
        """
        Create portfolio comparison visualization.
        
        Args:
            quantum_result: QAOA solution
            classical_result: Classical solution
            problem: Portfolio problem instance
            
        Returns:
            Plotly figure with comparison
        """
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Asset Allocation', 'Risk-Return Comparison', 
                          'Portfolio Metrics', 'Convergence'),
            specs=[[{"type": "bar"}, {"type": "scatter"}],
                   [{"type": "bar"}, {"type": "scatter"}]]
        )
        
        # Asset allocation comparison
        if quantum_result['allocation'] is not None and classical_result['allocation'] is not None:
            assets = [f'Asset {i+1}' for i in range(problem.n_assets)]
            
            fig.add_trace(
                go.Bar(x=assets, y=quantum_result['allocation'], 
                      name='Quantum (QAOA)', marker_color='blue'),
                row=1, col=1
            )
            
            fig.add_trace(
                go.Bar(x=assets, y=classical_result['allocation'], 
                      name='Classical', marker_color='red'),
                row=1, col=1
            )
        
        # Risk-return scatter
        if quantum_result['allocation'] is not None and classical_result['allocation'] is not None:
            # Calculate metrics for both solutions
            q_return = np.dot(quantum_result['allocation'], problem.returns)
            q_risk = np.sqrt(quantum_result['allocation'].T @ problem.covariances @ quantum_result['allocation'])
            
            c_return = classical_result['portfolio_return']
            c_risk = classical_result['portfolio_risk']
            
            fig.add_trace(
                go.Scatter(x=[q_risk], y=[q_return], mode='markers', 
                          name='Quantum (QAOA)', marker=dict(size=15, color='blue')),
                row=1, col=2
            )
            
            fig.add_trace(
                go.Scatter(x=[c_risk], y=[c_return], mode='markers', 
                          name='Classical', marker=dict(size=15, color='red')),
                row=1, col=2
            )
        
        # Portfolio metrics comparison
        metrics = ['Return', 'Risk', 'Sharpe Ratio']
        quantum_metrics = [
            q_return if 'q_return' in locals() else 0,
            q_risk if 'q_risk' in locals() else 0,
            (q_return - problem.risk_free_rate) / q_risk if 'q_risk' in locals() and q_risk > 0 else 0
        ]
        classical_metrics = [
            c_return if 'c_return' in locals() else 0,
            c_risk if 'c_risk' in locals() else 0,
            (c_return - problem.risk_free_rate) / c_risk if 'c_risk' in locals() and c_risk > 0 else 0
        ]
        
        fig.add_trace(
            go.Bar(x=metrics, y=quantum_metrics, name='Quantum (QAOA)', marker_color='blue'),
            row=2, col=1
        )
        
        fig.add_trace(
            go.Bar(x=metrics, y=classical_metrics, name='Classical', marker_color='red'),
            row=2, col=1
        )
        
        # Convergence plot (if available)
        if 'convergence' in quantum_result:
            fig.add_trace(
                go.Scatter(y=[quantum_result['final_cost']], mode='markers', 
                          name='Final Cost', marker=dict(size=15, color='green')),
                row=2, col=2
            )
        
        fig.update_layout(
            title='Portfolio Optimization: Quantum vs Classical',
            height=800,
            showlegend=True
        )
        
        return fig
    
    def plot_maxcut_comparison(self, quantum_result: Dict, classical_result: Dict, 
                              problem: 'MaxCutProblem') -> go.Figure:
        """
        Create Max-Cut comparison visualization.
        
        Args:
            quantum_result: QAOA solution
            classical_result: Classical solution
            problem: Max-Cut problem instance
            
        Returns:
            Plotly figure with comparison
        """
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Graph Visualization', 'Cut Value Comparison', 
                          'Partition Assignment', 'Solution Quality'),
            specs=[[{"type": "scatter"}, {"type": "bar"}],
                   [{"type": "scatter"}, {"type": "bar"}]]
        )
        
        # Graph visualization
        if quantum_result['partition'] is not None:
            # Create graph layout
            nodes_x = np.random.uniform(0, 10, problem.n_nodes)
            nodes_y = np.random.uniform(0, 10, problem.n_nodes)
            
            # Plot edges
            for (i, j), weight in zip(problem.edges, problem.weights):
                fig.add_trace(
                    go.Scatter(x=[nodes_x[i], nodes_x[j]], y=[nodes_y[i], nodes_y[j]], 
                              mode='lines', line=dict(width=weight*2), 
                              showlegend=False, opacity=0.5),
                    row=1, col=1
                )
            
            # Plot nodes with partition colors
            colors = ['red' if p == 0 else 'blue' for p in quantum_result['partition']]
            fig.add_trace(
                go.Scatter(x=nodes_x, y=nodes_y, mode='markers', 
                          marker=dict(size=20, color=colors), 
                          name='Quantum Partition', showlegend=False),
                row=1, col=1
            )
        
        # Cut value comparison
        cut_values = ['Quantum (QAOA)', 'Classical']
        q_cut = quantum_result.get('cut_value', 0)
        c_cut = classical_result.get('cut_value', 0)
        
        fig.add_trace(
            go.Bar(x=cut_values, y=[q_cut, c_cut], 
                  marker_color=['blue', 'red']),
            row=1, col=2
        )
        
        # Partition assignment
        if quantum_result['partition'] is not None:
            nodes = [f'Node {i}' for i in range(problem.n_nodes)]
            partitions = ['Partition 0' if p == 0 else 'Partition 1' for p in quantum_result['partition']]
            
            fig.add_trace(
                go.Bar(x=nodes, y=quantum_result['partition'], 
                      name='Quantum Partition', marker_color='blue'),
                row=2, col=1
            )
        
        # Solution quality metrics
        if 'final_cost' in quantum_result:
            metrics = ['Cut Value', 'Optimization Cost']
            q_metrics = [q_cut, quantum_result['final_cost']]
            
            fig.add_trace(
                go.Bar(x=metrics, y=q_metrics, name='Quantum Metrics', marker_color='blue'),
                row=2, col=2
            )
        
        fig.update_layout(
            title='Max-Cut Problem: Quantum vs Classical',
            height=800,
            showlegend=True
        )
        
        return fig
    
    def plot_convergence(self, optimization_history: List[float], 
                        title: str = 'Optimization Convergence') -> go.Figure:
        """
        Plot optimization convergence.
        
        Args:
            optimization_history: List of cost values during optimization
            title: Plot title
            
        Returns:
            Plotly figure
        """
        fig = go.Figure()
        
        fig.add_trace(
            go.Scatter(y=optimization_history, mode='lines+markers', 
                      name='Cost Function', line=dict(color='blue'))
        )
        
        fig.update_layout(
            title=title,
            xaxis_title='Iteration',
            yaxis_title='Cost Function Value',
            height=500
        )
        
        return fig
    
    def plot_circuit(self, circuit: 'QuantumCircuit', 
                    title: str = 'QAOA Circuit') -> go.Figure:
        """
        Visualize QAOA circuit.
        
        Args:
            circuit: Quantum circuit to visualize
            title: Plot title
            
        Returns:
            Plotly figure
        """
        # This would require qiskit visualization tools
        # For now, return a placeholder
        fig = go.Figure()
        
        fig.add_annotation(
            text="Circuit visualization requires qiskit visualization tools",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        
        fig.update_layout(
            title=title,
            height=400
        )
        
        return fig


def create_comparison_table(quantum_result: Dict, classical_result: Dict, 
                           problem_type: str, problem=None) -> pd.DataFrame:
    """
    Create a comparison table between quantum and classical results.
    
    Args:
        quantum_result: Quantum solution
        classical_result: Classical solution
        problem_type: Type of problem ('portfolio' or 'maxcut')
        
    Returns:
        Pandas DataFrame with comparison
    """
    if problem_type == 'portfolio':
        # Prepare formatted strings to avoid mixed dtypes in DataFrame columns (Arrow compatibility)
        q_final_cost = quantum_result.get('final_cost', None)
        q_final_cost_str = (f"{q_final_cost:.4f}" if isinstance(q_final_cost, (int, float, np.floating)) else str(q_final_cost) if q_final_cost is not None else 'N/A')

        c_obj = classical_result.get('objective_value', None)
        c_obj_str = (f"{c_obj:.4f}" if isinstance(c_obj, (int, float, np.floating)) else str(c_obj) if c_obj is not None else 'N/A')

        c_ret = classical_result.get('portfolio_return', None)
        c_ret_str = (f"{c_ret:.4f}" if isinstance(c_ret, (int, float, np.floating)) else 'N/A')

        c_risk = classical_result.get('portfolio_risk', None)
        c_risk_str = (f"{c_risk:.4f}" if isinstance(c_risk, (int, float, np.floating)) else 'N/A')

        c_sharpe = None
        if isinstance(c_ret, (int, float, np.floating)) and isinstance(c_risk, (int, float, np.floating)) and c_risk > 0:
            rf = getattr(problem, 'risk_free_rate', 0.0) if problem is not None else 0.0
            c_sharpe = (c_ret - rf) / c_risk
        c_sharpe_str = (f"{c_sharpe:.4f}" if isinstance(c_sharpe, (int, float, np.floating)) else 'N/A')

        data = {
            'Metric': ['Method', 'Objective Value', 'Portfolio Return', 'Portfolio Risk', 'Sharpe Ratio'],
            'Quantum (QAOA)': [
                'QAOA',
                q_final_cost_str,
                f"{np.dot(quantum_result['allocation'], problem.returns):.4f}" if (problem is not None and quantum_result.get('allocation') is not None) else 'N/A',
                f"{np.sqrt(quantum_result['allocation'].T @ problem.covariances @ quantum_result['allocation']):.4f}" if (problem is not None and quantum_result.get('allocation') is not None) else 'N/A',
                (f"{(np.dot(quantum_result['allocation'], problem.returns) - getattr(problem, 'risk_free_rate', 0.0)) / max(1e-12, np.sqrt(quantum_result['allocation'].T @ problem.covariances @ quantum_result['allocation'])):.4f}"
                 if (problem is not None and quantum_result.get('allocation') is not None)
                 else 'N/A')
            ],
            'Classical': [
                'Convex Optimization',
                c_obj_str,
                c_ret_str,
                c_risk_str,
                c_sharpe_str
            ]
        }
    else:  # maxcut
        q_cut = quantum_result.get('cut_value', None)
        q_cut_str = (f"{q_cut:.4f}" if isinstance(q_cut, (int, float, np.floating)) else str(q_cut) if q_cut is not None else 'N/A')

        c_cut = classical_result.get('cut_value', None)
        c_cut_str = (f"{c_cut:.4f}" if isinstance(c_cut, (int, float, np.floating)) else str(c_cut) if c_cut is not None else 'N/A')

        data = {
            'Metric': ['Method', 'Cut Value', 'Partition', 'Status'],
            'Quantum (QAOA)': [
                'QAOA',
                q_cut_str,
                str(quantum_result.get('partition', 'N/A')),
                'Completed'
            ],
            'Classical': [
                'Integer Programming',
                c_cut_str,
                str(classical_result.get('partition', 'N/A')),
                classical_result.get('status', 'N/A')
            ]
        }
    
    return pd.DataFrame(data)
