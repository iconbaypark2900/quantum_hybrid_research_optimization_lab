"""
QOptiSolve - Quantum Optimization Solver

A portfolio and graph optimization solver built with quantum algorithms.
"""

__version__ = "0.1.0"
__author__ = "QOptiSolve Team"

from .problems import PortfolioProblem, MaxCutProblem, create_sample_portfolio, create_sample_maxcut
from .qaoa import QAOA
from .classical import (
    ClassicalPortfolioSolver, ClassicalMaxCutSolver,
    solve_portfolio_greedy, solve_maxcut_greedy
)
from .visualizer import QAOAVisualizer, create_comparison_table

__all__ = [
    'PortfolioProblem',
    'MaxCutProblem', 
    'create_sample_portfolio',
    'create_sample_maxcut',
    'QAOA',
    'ClassicalPortfolioSolver',
    'ClassicalMaxCutSolver',
    'solve_portfolio_greedy',
    'solve_maxcut_greedy',
    'QAOAVisualizer',
    'create_comparison_table'
]
