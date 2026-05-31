"""
QOptiSolve Streamlit Application
Main entry point for the quantum optimization solver.
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time

# Import our modules
from qoptisolve.problems import (
    PortfolioProblem, MaxCutProblem, 
    create_sample_portfolio, create_sample_maxcut
)
from qoptisolve.qaoa import QAOA
from qoptisolve.classical import (
    ClassicalPortfolioSolver, ClassicalMaxCutSolver,
    solve_portfolio_greedy, solve_maxcut_greedy
)
from qoptisolve.visualizer import QAOAVisualizer, create_comparison_table


def main():
    """Main Streamlit application."""
    st.set_page_config(
        page_title="QOptiSolve - Quantum Optimization Solver",
        page_icon="⚛️",
        layout="wide"
    )
    
    st.title("⚛️ QOptiSolve - Quantum Optimization Solver")
    st.markdown("**Quantum Approximate Optimization Algorithm (QAOA) for Portfolio and Graph Optimization**")
    
    # Sidebar
    st.sidebar.header("Problem Configuration")
    problem_type = st.sidebar.selectbox(
        "Problem Type",
        ["Portfolio Optimization", "Max-Cut Problem"]
    )
    
    # Problem parameters
    if problem_type == "Portfolio Optimization":
        st.sidebar.subheader("Portfolio Parameters")
        n_assets = st.sidebar.slider("Number of Assets", 3, 10, 5)
        risk_free_rate = st.sidebar.number_input("Risk-Free Rate", 0.0, 0.1, 0.02, 0.01)
        target_return = st.sidebar.number_input("Target Return", 0.05, 0.20, 0.10, 0.01)
        
    else:  # Max-Cut
        st.sidebar.subheader("Max-Cut Parameters")
        n_nodes = st.sidebar.slider("Number of Nodes", 4, 12, 6)
        edge_prob = st.sidebar.slider("Edge Probability", 0.2, 0.8, 0.5, 0.1)
    
    # QAOA parameters
    st.sidebar.subheader("QAOA Parameters")
    p_depth = st.sidebar.slider("QAOA Depth (p)", 1, 4, 2)
    shots = st.sidebar.slider("Quantum Shots", 100, 2000, 1000, 100)
    max_iter = st.sidebar.slider("Max Iterations", 50, 200, 100, 10)
    optimizer = st.sidebar.selectbox("Optimizer", ["SPSA", "COBYLA"])
    
    # Create problem instance
    if problem_type == "Portfolio Optimization":
        problem = create_sample_portfolio(n_assets=n_assets, seed=42)
        problem.risk_free_rate = risk_free_rate
        problem.target_return = target_return
    else:
        problem = create_sample_maxcut(n_nodes=n_nodes, edge_prob=edge_prob, seed=42)
    
    # Display problem information
    st.header("Problem Definition")
    if problem_type == "Portfolio Optimization":
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Asset Returns")
            returns_df = pd.DataFrame({
                'Asset': [f'Asset {i+1}' for i in range(problem.n_assets)],
                'Expected Return': problem.returns
            })
            st.dataframe(returns_df, use_container_width=True)
        
        with col2:
            st.subheader("Covariance Matrix")
            cov_df = pd.DataFrame(
                problem.covariances,
                columns=[f'Asset {i+1}' for i in range(problem.n_assets)],
                index=[f'Asset {i+1}' for i in range(problem.n_assets)]
            )
            st.dataframe(cov_df, use_container_width=True)
    else:
        st.subheader("Graph Structure")
        st.write(f"**Nodes:** {problem.n_nodes}")
        st.write(f"**Edges:** {len(problem.edges)}")
        
        edges_df = pd.DataFrame({
            'Edge': [f"({i}, {j})" for i, j in problem.edges],
            'Weight': problem.weights
        })
        st.dataframe(edges_df, use_container_width=True)
    
    # Solve button
    if st.button("🚀 Solve with QAOA", type="primary"):
        with st.spinner("Solving optimization problem..."):
            
            # Initialize solvers
            qaoa = QAOA(shots=shots)
            visualizer = QAOAVisualizer()
            
            if problem_type == "Portfolio Optimization":
                classical_solver = ClassicalPortfolioSolver()
                
                # Solve with QAOA
                st.subheader("⚛️ Quantum Solution (QAOA)")
                quantum_result = qaoa.solve_portfolio(
                    problem, p=p_depth, optimizer=optimizer, max_iter=max_iter
                )
                
                if quantum_result['allocation'] is not None:
                    st.success(f"✅ QAOA completed successfully!")
                    st.write(f"**Final Cost:** {quantum_result['final_cost']:.4f}")
                    st.write(f"**Convergence:** {quantum_result['convergence']} iterations")
                    
                    # Display allocation
                    allocation_df = pd.DataFrame({
                        'Asset': [f'Asset {i+1}' for i in range(problem.n_assets)],
                        'Allocation': quantum_result['allocation']
                    })
                    st.dataframe(allocation_df, use_container_width=True)
                else:
                    st.error("❌ QAOA failed to find solution")
                
                # Solve with classical method
                st.subheader("🖥️ Classical Solution")
                classical_result = classical_solver.solve(problem, objective='sharpe')
                
                if classical_result['allocation'] is not None:
                    st.success(f"✅ Classical solver completed successfully!")
                    st.write(f"**Objective Value:** {classical_result['objective_value']:.4f}")
                    st.write(f"**Portfolio Return:** {classical_result['portfolio_return']:.4f}")
                    st.write(f"**Portfolio Risk:** {classical_result['portfolio_risk']:.4f}")
                else:
                    st.error(f"❌ Classical solver failed: {classical_result.get('status', 'Unknown error')}")
                
                # Comparison
                if quantum_result['allocation'] is not None and classical_result['allocation'] is not None:
                    st.subheader("📊 Solution Comparison")
                    
                    # Create comparison table
                    comparison_df = create_comparison_table(
                        quantum_result, classical_result, 'portfolio', problem
                    )
                    st.dataframe(comparison_df, use_container_width=True)
                    
                    # Create visualization
                    fig = visualizer.plot_portfolio_comparison(
                        quantum_result, classical_result, problem
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
            else:  # Max-Cut
                classical_solver = ClassicalMaxCutSolver()
                
                # Solve with QAOA
                st.subheader("⚛️ Quantum Solution (QAOA)")
                quantum_result = qaoa.solve_maxcut(
                    problem, p=p_depth, optimizer=optimizer, max_iter=max_iter
                )
                
                if quantum_result['partition'] is not None:
                    st.success(f"✅ QAOA completed successfully!")
                    st.write(f"**Cut Value:** {quantum_result['cut_value']:.4f}")
                    st.write(f"**Final Cost:** {quantum_result['final_cost']:.4f}")
                    st.write(f"**Convergence:** {quantum_result['convergence']} iterations")
                    
                    # Display partition
                    partition_df = pd.DataFrame({
                        'Node': [f'Node {i}' for i in range(problem.n_nodes)],
                        'Partition': ['A' if p == 0 else 'B' for p in quantum_result['partition']]
                    })
                    st.dataframe(partition_df, use_container_width=True)
                else:
                    st.error("❌ QAOA failed to find solution")
                
                # Solve with classical method
                st.subheader("🖥️ Classical Solution")
                classical_result = classical_solver.solve(problem)
                
                if classical_result['partition'] is not None:
                    st.success(f"✅ Classical solver completed successfully!")
                    st.write(f"**Cut Value:** {classical_result['cut_value']:.4f}")
                else:
                    st.error(f"❌ Classical solver failed: {classical_result.get('status', 'Unknown error')}")
                
                # Comparison
                if quantum_result['partition'] is not None and classical_result['partition'] is not None:
                    st.subheader("📊 Solution Comparison")
                    
                    # Create comparison table
                    comparison_df = create_comparison_table(
                        quantum_result, classical_result, 'maxcut'
                    )
                    st.dataframe(comparison_df, use_container_width=True)
                    
                    # Create visualization
                    fig = visualizer.plot_maxcut_comparison(
                        quantum_result, classical_result, problem
                    )
                    st.plotly_chart(fig, use_container_width=True)
    
    # Information section
    st.sidebar.markdown("---")
    st.sidebar.markdown("### About QOptiSolve")
    st.sidebar.markdown("""
    QOptiSolve demonstrates quantum optimization using QAOA:
    
    - **Portfolio Optimization**: Find optimal asset allocations
    - **Max-Cut**: Solve graph partitioning problems
    - **Quantum vs Classical**: Compare solution quality
    
    Built with Qiskit and Streamlit.
    """)
    
    st.sidebar.markdown("### Disclaimer")
    st.sidebar.markdown("""
    ⚠️ **Educational purposes only**
    
    Not for production use or financial decisions.
    """)


if __name__ == "__main__":
    main()
