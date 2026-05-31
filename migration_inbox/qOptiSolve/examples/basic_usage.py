#!/usr/bin/env python3
"""
Basic usage example for QOptiSolve.

This script demonstrates how to use the QOptiSolve library
to solve portfolio optimization and Max-Cut problems.
"""

import numpy as np
from qoptisolve.problems import create_sample_portfolio, create_sample_maxcut
from qoptisolve.qaoa import QAOA
from qoptisolve.classical import ClassicalPortfolioSolver, ClassicalMaxCutSolver
from qoptisolve.visualizer import QAOAVisualizer, create_comparison_table


def portfolio_optimization_example():
    """Demonstrate portfolio optimization with QAOA vs classical methods."""
    print("=" * 60)
    print("PORTFOLIO OPTIMIZATION EXAMPLE")
    print("=" * 60)
    
    # Create a sample portfolio problem
    problem = create_sample_portfolio(n_assets=5, seed=42)
    print(f"Created portfolio problem with {problem.n_assets} assets")
    print(f"Expected returns: {problem.returns}")
    print(f"Risk-free rate: {problem.risk_free_rate}")
    
    # Solve with QAOA
    print("\n--- Solving with QAOA ---")
    qaoa = QAOA(shots=500)  # Reduced shots for faster execution
    
    try:
        quantum_result = qaoa.solve_portfolio(
            problem, p=1, optimizer='SPSA', max_iter=50
        )
        
        if quantum_result['allocation'] is not None:
            print(f"✅ QAOA completed successfully!")
            print(f"Final cost: {quantum_result['final_cost']:.4f}")
            print(f"Convergence: {quantum_result['convergence']} iterations")
            print(f"Allocation: {quantum_result['allocation']}")
        else:
            print("❌ QAOA failed to find solution")
            return
            
    except Exception as e:
        print(f"❌ QAOA failed with error: {e}")
        return
    
    # Solve with classical method
    print("\n--- Solving with Classical Solver ---")
    classical_solver = ClassicalPortfolioSolver()
    
    try:
        classical_result = classical_solver.solve(problem, objective='sharpe')
        
        if classical_result['allocation'] is not None:
            print(f"✅ Classical solver completed successfully!")
            print(f"Objective value: {classical_result['objective_value']:.4f}")
            print(f"Portfolio return: {classical_result['portfolio_return']:.4f}")
            print(f"Portfolio risk: {classical_result['portfolio_risk']:.4f}")
            print(f"Allocation: {classical_result['allocation']}")
        else:
            print(f"❌ Classical solver failed: {classical_result.get('status', 'Unknown error')}")
            return
            
    except Exception as e:
        print(f"❌ Classical solver failed with error: {e}")
        return
    
    # Compare solutions
    print("\n--- Solution Comparison ---")
    comparison_df = create_comparison_table(
        quantum_result, classical_result, 'portfolio'
    )
    print(comparison_df.to_string(index=False))
    
    # Create visualization
    print("\n--- Creating Visualization ---")
    visualizer = QAOAVisualizer()
    fig = visualizer.plot_portfolio_comparison(
        quantum_result, classical_result, problem
    )
    print("✅ Visualization created successfully!")
    print("Note: In a real application, you would display this with fig.show()")


def maxcut_example():
    """Demonstrate Max-Cut optimization with QAOA vs classical methods."""
    print("\n" + "=" * 60)
    print("MAX-CUT OPTIMIZATION EXAMPLE")
    print("=" * 60)
    
    # Create a sample Max-Cut problem
    problem = create_sample_maxcut(n_nodes=6, edge_prob=0.6, seed=42)
    print(f"Created Max-Cut problem with {problem.n_nodes} nodes")
    print(f"Number of edges: {len(problem.edges)}")
    print(f"Edge weights: {problem.weights}")
    
    # Solve with QAOA
    print("\n--- Solving with QAOA ---")
    qaoa = QAOA(shots=500)  # Reduced shots for faster execution
    
    try:
        quantum_result = qaoa.solve_maxcut(
            problem, p=1, optimizer='SPSA', max_iter=50
        )
        
        if quantum_result['partition'] is not None:
            print(f"✅ QAOA completed successfully!")
            print(f"Cut value: {quantum_result['cut_value']:.4f}")
            print(f"Final cost: {quantum_result['final_cost']:.4f}")
            print(f"Convergence: {quantum_result['convergence']} iterations")
            print(f"Partition: {quantum_result['partition']}")
        else:
            print("❌ QAOA failed to find solution")
            return
            
    except Exception as e:
        print(f"❌ QAOA failed with error: {e}")
        return
    
    # Solve with classical method
    print("\n--- Solving with Classical Solver ---")
    classical_solver = ClassicalMaxCutSolver()
    
    try:
        classical_result = classical_solver.solve(problem)
        
        if classical_result['partition'] is not None:
            print(f"✅ Classical solver completed successfully!")
            print(f"Cut value: {classical_result['cut_value']:.4f}")
            print(f"Partition: {classical_result['partition']}")
        else:
            print(f"❌ Classical solver failed: {classical_result.get('status', 'Unknown error')}")
            return
            
    except Exception as e:
        print(f"❌ Classical solver failed with error: {e}")
        return
    
    # Compare solutions
    print("\n--- Solution Comparison ---")
    comparison_df = create_comparison_table(
        quantum_result, classical_result, 'maxcut'
    )
    print(comparison_df.to_string(index=False))
    
    # Create visualization
    print("\n--- Creating Visualization ---")
    visualizer = QAOAVisualizer()
    fig = visualizer.plot_maxcut_comparison(
        quantum_result, classical_result, problem
    )
    print("✅ Visualization created successfully!")
    print("Note: In a real application, you would display this with fig.show()")


def main():
    """Run the examples."""
    print("🚀 QOptiSolve Basic Usage Examples")
    print("This script demonstrates portfolio optimization and Max-Cut solving")
    print("using both quantum (QAOA) and classical methods.\n")
    
    try:
        # Run portfolio optimization example
        portfolio_optimization_example()
        
        # Run Max-Cut example
        maxcut_example()
        
        print("\n" + "=" * 60)
        print("✅ All examples completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Example failed with error: {e}")
        print("This might be due to missing dependencies or configuration issues.")
        print("Make sure you have installed all required packages:")
        print("pip install -r requirements.txt")


if __name__ == "__main__":
    main()
