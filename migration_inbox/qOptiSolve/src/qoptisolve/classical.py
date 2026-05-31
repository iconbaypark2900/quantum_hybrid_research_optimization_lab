"""
Classical optimization solvers for comparison with QAOA.
"""

import numpy as np
import cvxpy as cp
from typing import Dict, List, Tuple
import warnings


class ClassicalPortfolioSolver:
    """Classical portfolio optimization solver using convex optimization."""
    
    def __init__(self):
        """Initialize classical solver."""
        pass
    
    def solve(self, problem: 'PortfolioProblem', objective: str = 'sharpe') -> Dict:
        """
        Solve portfolio optimization using classical methods.
        
        Args:
            problem: Portfolio problem instance
            objective: Optimization objective ('sharpe', 'min_risk', 'max_return')
            
        Returns:
            Dictionary with solution and metadata
        """
        n_assets = problem.n_assets
        
        # Decision variables
        weights = cp.Variable(n_assets)
        
        # Constraints
        constraints = [
            cp.sum(weights) == 1,  # Budget constraint
            weights >= 0  # Long-only constraint
        ]
        
        if problem.target_return is not None:
            constraints.append(weights @ problem.returns >= problem.target_return)
        
        # Objective function
        if objective == 'sharpe':
            # Convex surrogate: minimize variance subject to meeting target return
            # This avoids non-DCP Sharpe ratio maximization.
            # Ensure a target return exists; if not, use a reasonable default above risk-free.
            if problem.target_return is None:
                est_target = float(0.5 * (np.max(problem.returns) + problem.risk_free_rate))
                constraints.append(weights @ problem.returns >= est_target)
            objective_func = cp.quad_form(weights, problem.covariances)
            
        elif objective == 'min_risk':
            # Minimize portfolio variance (sqrt is monotonic, so minimizing var is equivalent and DCP-friendly)
            objective_func = cp.quad_form(weights, problem.covariances)
            
        elif objective == 'max_return':
            # Maximize portfolio return
            objective_func = -cp.sum(weights @ problem.returns)
            
        else:
            raise ValueError(f"Unknown objective: {objective}")
        
        # Solve problem
        prob = cp.Problem(cp.Minimize(objective_func), constraints)
        
        try:
            prob.solve()
            
            if prob.status == 'optimal':
                solution = {
                    'allocation': weights.value,
                    'status': 'optimal',
                    'objective_value': None,  # filled below
                    'portfolio_return': float(np.dot(weights.value, problem.returns)),
                    'portfolio_risk': float(np.sqrt(max(0.0, weights.value.T @ problem.covariances @ weights.value)))
                }
                # Report an interpretable objective value depending on chosen objective
                if objective == 'sharpe':
                    denom = solution['portfolio_risk'] + 1e-9
                    solution['objective_value'] = (solution['portfolio_return'] - problem.risk_free_rate) / denom
                elif objective == 'min_risk':
                    solution['objective_value'] = solution['portfolio_risk']
                elif objective == 'max_return':
                    solution['objective_value'] = solution['portfolio_return']
            else:
                solution = {
                    'allocation': None,
                    'status': prob.status,
                    'objective_value': None,
                    'portfolio_return': None,
                    'portfolio_risk': None
                }
                
        except Exception as e:
            warnings.warn(f"Classical solver failed: {e}")
            solution = {
                'allocation': None,
                'status': 'error',
                'objective_value': None,
                'portfolio_return': None,
                'portfolio_risk': None,
                'error': str(e)
            }
        
        return solution


class ClassicalMaxCutSolver:
    """Classical Max-Cut solver using integer programming."""
    
    def __init__(self):
        """Initialize classical solver."""
        pass
    
    def solve(self, problem: 'MaxCutProblem') -> Dict:
        """
        Solve Max-Cut problem using classical methods.
        
        Args:
            problem: Max-Cut problem instance
            
        Returns:
            Dictionary with solution and metadata
        """
        n_nodes = problem.n_nodes
        
        # Decision variables (binary: 0 or 1 for each node)
        x = cp.Variable(n_nodes, boolean=True)
        
        # Objective: maximize cut value
        cut_value = 0
        for (i, j), weight in zip(problem.edges, problem.weights):
            # Edge contributes to cut if nodes are in different partitions
            cut_value += weight * (x[i] * (1 - x[j]) + x[j] * (1 - x[i]))
        
        # No constraints needed for Max-Cut
        
        # Solve problem
        prob = cp.Problem(cp.Maximize(cut_value))
        
        try:
            prob.solve()
            
            if prob.status == 'optimal':
                partition = x.value.astype(int)
                solution = {
                    'partition': partition,
                    'cut_value': prob.value,
                    'status': 'optimal'
                }
            else:
                solution = {
                    'partition': None,
                    'cut_value': None,
                    'status': prob.status
                }
                
        except Exception as e:
            warnings.warn(f"Classical solver failed: {e}")
            solution = {
                'partition': None,
                'cut_value': None,
                'status': 'error',
                'error': str(e)
            }
        
        return solution


def solve_portfolio_greedy(problem: 'PortfolioProblem') -> Dict:
    """
    Solve portfolio optimization using greedy approach.
    
    Args:
        problem: Portfolio problem instance
        
    Returns:
        Dictionary with solution and metadata
    """
    n_assets = problem.n_assets
    
    # Simple greedy: allocate to assets with highest Sharpe ratio
    sharpe_ratios = (problem.returns - problem.risk_free_rate) / np.sqrt(np.diag(problem.covariances))
    
    # Sort by Sharpe ratio and allocate
    sorted_indices = np.argsort(sharpe_ratios)[::-1]
    
    # Equal weight allocation to top assets
    allocation = np.zeros(n_assets)
    top_k = min(3, n_assets)  # Top 3 assets
    allocation[sorted_indices[:top_k]] = 1.0 / top_k
    
    portfolio_return = np.dot(allocation, problem.returns)
    portfolio_risk = np.sqrt(allocation.T @ problem.covariances @ allocation)
    
    return {
        'allocation': allocation,
        'portfolio_return': portfolio_return,
        'portfolio_risk': portfolio_risk,
        'sharpe_ratio': portfolio_return / portfolio_risk if portfolio_risk > 0 else 0,
        'method': 'greedy'
    }


def solve_maxcut_greedy(problem: 'MaxCutProblem') -> Dict:
    """
    Solve Max-Cut problem using greedy approach.
    
    Args:
        problem: Max-Cut problem instance
        
    Returns:
        Dictionary with solution and metadata
    """
    n_nodes = problem.n_nodes
    
    # Simple greedy: start with random partition and improve
    partition = np.random.randint(0, 2, n_nodes)
    
    # Try to improve by moving nodes
    improved = True
    max_iterations = 100
    
    for _ in range(max_iterations):
        if not improved:
            break
            
        improved = False
        
        for node in range(n_nodes):
            # Calculate current cut value
            current_cut = 0
            for (i, j), weight in zip(problem.edges, problem.weights):
                if partition[i] != partition[j]:
                    current_cut += weight
            
            # Try flipping this node
            partition[node] = 1 - partition[node]
            
            # Calculate new cut value
            new_cut = 0
            for (i, j), weight in zip(problem.edges, problem.weights):
                if partition[i] != partition[j]:
                    new_cut += weight
            
            # Keep the flip if it improves
            if new_cut > current_cut:
                improved = True
            else:
                partition[node] = 1 - partition[node]  # Revert
    
    # Calculate final cut value
    final_cut = 0
    for (i, j), weight in zip(problem.edges, problem.weights):
        if partition[i] != partition[j]:
            final_cut += weight
    
    return {
        'partition': partition,
        'cut_value': final_cut,
        'method': 'greedy'
    }
