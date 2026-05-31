# QOptiSolve — Quantum Optimization Solver

## Overview

**QOptiSolve** is a portfolio and graph optimization solver built with quantum algorithms. It applies the **Quantum Approximate Optimization Algorithm (QAOA)** to solve combinatorial optimization problems, such as portfolio allocation or Max-Cut, and compares results against classical solvers. QOptiSolve demonstrates the intersection of quantum computing, optimization, and reproducible research in a test-driven framework.

The project highlights:

- **Quantum algorithms** for optimization (QAOA).
- **Comparative analysis** with classical solvers.
- **Visualization** of solution quality and convergence.
- **Test-Driven Development (TDD)** to validate correctness.

---

## Features

- Define optimization problem (portfolio allocation, graph Max-Cut).
- Generate and run QAOA circuits.
- Compare quantum vs. classical solver outputs.
- Visualize convergence and cost landscapes.
- Export results to JSON/CSV.

---

## Installation

```bash
# Clone repository
git clone https://github.com/yourusername/qoptisolve
cd qoptisolve

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## Usage

### Run the Streamlit App

```bash
streamlit run src/app.py
```

### Example Workflow

1. Select problem type: Max-Cut (graph) or Portfolio Optimization.
2. Define problem parameters (graph edges, asset returns/covariances).
3. Run QAOA solver with chosen depth (p).
4. Compare results against classical solver.
5. Visualize convergence plots and optimal allocations/cuts.

---

## Example Output

Problem: Max-Cut on 6-node graph

```
Quantum (QAOA, p=2) — Cut Value: 7.8
Classical Solver — Cut Value: 8.0
```

Visualization: convergence plot showing quantum vs. classical optimization progress.

---

## Testing Strategy

QOptiSolve follows **TDD methodology**:

1. **Unit Tests**: QAOA circuit generation, classical solver logic.
2. **Integration Tests**: full pipeline (problem → quantum/classical → comparison).
3. **Mock Backend Tests**: simulate quantum runs for reproducibility.
4. **UI Snapshot Tests**: dashboard rendering of results.

Run tests:

```bash
pytest -q
```

---

## Project Structure

```
qoptisolve/
├─ src/
│  ├─ qoptisolve/
│  │  ├─ __init__.py
│  │  ├─ problems.py      # Portfolio + Max-Cut definitions
│  │  ├─ qaoa.py          # Quantum algorithm implementation
│  │  ├─ classical.py     # Classical optimization solvers
│  │  ├─ visualizer.py    # Plotting + dashboards
│  └─ app.py              # Streamlit entrypoint
├─ tests/
│  ├─ test_problems.py
│  ├─ test_qaoa.py
│  ├─ test_classical.py
│  └─ test_pipeline.py
├─ requirements.txt
└─ README.md
```

---

## Roadmap

-

---

## License

MIT License. See `LICENSE` file for details.

---

## Disclaimer

QOptiSolve is intended **for educational and demonstration purposes only**. It is **not a production-grade quantum solver** and should not be used for financial or mission-critical optimization decisions.

