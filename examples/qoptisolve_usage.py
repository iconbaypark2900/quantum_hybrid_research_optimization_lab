#!/usr/bin/env python3
"""
Basic usage example for qOptiSolve modules.

Demonstrates portfolio optimization and Max-Cut using classical and QAOA solvers.
Adapted from qOptiSolve migration_inbox/qOptiSolve/examples/basic_usage.py.

# SIMULATION ONLY — QAOA runs on Qiskit Aer simulator, not real quantum hardware.
"""

import numpy as np
from src.optimization.problems import create_sample_portfolio, create_sample_maxcut
from src.optimization.classical import (
    ClassicalPortfolioSolver,
    ClassicalMaxCutSolver,
    solve_portfolio_greedy,
    solve_maxcut_greedy,
)


def portfolio_optimization_example():
    """Demonstrate portfolio optimization with classical and greedy methods."""
    print("=" * 60)
    print("PORTFOLIO OPTIMIZATION EXAMPLE")
    print("=" * 60)

    problem = create_sample_portfolio(n_assets=5, seed=42)
    print(f"Created portfolio problem with {problem.n_assets} assets")
    print(f"Expected returns: {problem.returns}")
    print(f"Risk-free rate: {problem.risk_free_rate}")

    print("\n--- Solving with Classical (min_risk) ---")
    classical = ClassicalPortfolioSolver()
    result = classical.solve(problem, objective='min_risk')
    print(f"Status: {result['status']}")
    if result['allocation'] is not None:
        print(f"Allocation: {result['allocation']}")
        print(f"Portfolio return: {result['portfolio_return']:.4f}")
        print(f"Portfolio risk: {result['portfolio_risk']:.4f}")

    print("\n--- Solving with Greedy ---")
    greedy_result = solve_portfolio_greedy(problem)
    print(f"Greedy allocation: {greedy_result['allocation']}")
    print(f"Portfolio return: {greedy_result['portfolio_return']:.4f}")
    print(f"Sharpe ratio: {greedy_result['sharpe_ratio']:.4f}")


def maxcut_optimization_example():
    """Demonstrate Max-Cut optimization."""
    print("\n" + "=" * 60)
    print("MAX-CUT OPTIMIZATION EXAMPLE")
    print("=" * 60)

    problem = create_sample_maxcut(n_nodes=6, edge_prob=0.5, seed=42)
    print(f"Created Max-Cut problem with {problem.n_nodes} nodes")
    print(f"Number of edges: {len(problem.edges)}")

    print("\n--- Solving with Greedy ---")
    greedy_result = solve_maxcut_greedy(problem)
    print(f"Greedy partition: {greedy_result['partition']}")
    print(f"Cut value: {greedy_result['cut_value']:.4f}")


if __name__ == '__main__':
    portfolio_optimization_example()
    maxcut_optimization_example()
