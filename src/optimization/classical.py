"""
Classical optimization solvers for comparison with QAOA.

Imported from qOptiSolve (migration_inbox/qOptiSolve/src/qoptisolve/classical.py).
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
            cp.sum(weights) == 1,
            weights >= 0
        ]

        if problem.target_return is not None:
            constraints.append(weights @ problem.returns >= problem.target_return)

        # Objective function
        if objective == 'sharpe':
            # Convex surrogate: minimize variance subject to meeting target return
            if problem.target_return is None:
                est_target = float(0.5 * (np.max(problem.returns) + problem.risk_free_rate))
                constraints.append(weights @ problem.returns >= est_target)
            objective_func = cp.quad_form(weights, problem.covariances)

        elif objective == 'min_risk':
            objective_func = cp.quad_form(weights, problem.covariances)

        elif objective == 'max_return':
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
                    'objective_value': None,
                    'portfolio_return': float(np.dot(weights.value, problem.returns)),
                    'portfolio_risk': float(np.sqrt(max(0.0, weights.value.T @ problem.covariances @ weights.value)))
                }
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

        # The objective was written directly as
        #     w_ij * (x_i (1 - x_j) + x_j (1 - x_i))
        # which is bilinear, so cvxpy rejected the whole problem as non-DCP
        # ("The objective is not DCP"). The solver then caught the exception,
        # warned, and returned status 'error' — and the test suite passed
        # anyway, because it asserts on shape and status rather than on a cut
        # being found. This solver had therefore never solved anything.
        #
        # Standard MILP linearisation. For binary x, the indicator that edge
        # (i, j) is cut is y_ij = x_i XOR x_j, which these four inequalities
        # pin exactly when maximising a positive-weighted sum:
        #
        #     y_ij <= x_i + x_j          (both 0 -> not cut)
        #     y_ij <= 2 - x_i - x_j      (both 1 -> not cut)
        #     y_ij >= x_i - x_j          (differ -> cut)
        #     y_ij >= x_j - x_i
        #
        # All linear, hence DCP-compliant, and exact rather than a relaxation.
        n_edges = len(problem.edges)
        y = cp.Variable(n_edges)
        constraints = [y >= 0, y <= 1]
        for k, (i, j) in enumerate(problem.edges):
            constraints += [
                y[k] <= x[i] + x[j],
                y[k] <= 2 - x[i] - x[j],
                y[k] >= x[i] - x[j],
                y[k] >= x[j] - x[i],
            ]

        weights = np.asarray(problem.weights, dtype=float)
        if np.any(weights < 0):
            # With a negative weight the maximiser wants y_ij at its LOWER
            # bound, and the two >= constraints no longer pin it to the XOR —
            # the relaxation would report a cut value the partition does not
            # achieve. Refuse rather than return a number that looks fine.
            raise ValueError(
                "ClassicalMaxCutSolver requires non-negative edge weights: the "
                "linearisation above is exact only when the objective pushes "
                "y_ij up. Got weights with minimum "
                f"{weights.min()}.")

        prob = cp.Problem(cp.Maximize(weights @ y), constraints)

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

    sharpe_ratios = (problem.returns - problem.risk_free_rate) / np.sqrt(np.diag(problem.covariances))

    sorted_indices = np.argsort(sharpe_ratios)[::-1]

    allocation = np.zeros(n_assets)
    top_k = min(3, n_assets)
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

    partition = np.random.randint(0, 2, n_nodes)

    improved = True
    max_iterations = 100

    for _ in range(max_iterations):
        if not improved:
            break

        improved = False

        for node in range(n_nodes):
            current_cut = 0
            for (i, j), weight in zip(problem.edges, problem.weights):
                if partition[i] != partition[j]:
                    current_cut += weight

            partition[node] = 1 - partition[node]

            new_cut = 0
            for (i, j), weight in zip(problem.edges, problem.weights):
                if partition[i] != partition[j]:
                    new_cut += weight

            if new_cut > current_cut:
                improved = True
            else:
                partition[node] = 1 - partition[node]

    final_cut = 0
    for (i, j), weight in zip(problem.edges, problem.weights):
        if partition[i] != partition[j]:
            final_cut += weight

    return {
        'partition': partition,
        'cut_value': final_cut,
        'method': 'greedy'
    }
