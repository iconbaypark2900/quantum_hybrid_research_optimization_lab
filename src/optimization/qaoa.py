"""
Quantum Approximate Optimization Algorithm (QAOA) implementation.

Imported from qOptiSolve (migration_inbox/qOptiSolve/src/qoptisolve/qaoa.py).

# SIMULATION ONLY — this module uses Qiskit Aer simulator, not real quantum hardware.
"""

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit_aer import Aer
from qiskit.circuit import Parameter
from typing import Dict, List, Tuple, Callable, Optional, TYPE_CHECKING

from .canonical import maxcut_to_qubo, portfolio_to_qubo

# Optimizers location differs across Qiskit versions; provide robust imports with fallbacks
try:  # Qiskit Algorithms as separate package (newer)
    from qiskit_algorithms.optimizers import SPSA, COBYLA  # type: ignore
except Exception:  # Older Qiskit (pre-1.0)
    try:
        from qiskit.algorithms.optimizers import SPSA, COBYLA  # type: ignore
    except Exception:
        try:
            from scipy.optimize import minimize  # type: ignore
        except Exception:  # pragma: no cover
            minimize = None  # type: ignore

        class COBYLA:  # type: ignore
            def __init__(self, maxiter: int = 100):
                self.maxiter = maxiter

            def minimize(self, fun: Callable[[np.ndarray], float], x0: np.ndarray):
                if minimize is None:
                    best_x = np.array(x0, dtype=float)
                    best_val = float(fun(best_x))
                    for i in range(self.maxiter):
                        candidate = best_x + np.random.uniform(-0.1, 0.1, size=best_x.shape)
                        val = float(fun(candidate))
                        if val < best_val:
                            best_x, best_val = candidate, val
                    return type("Result", (), {"x": best_x, "fun": best_val, "nfev": self.maxiter})
                res = minimize(fun, x0, method="COBYLA", options={"maxiter": self.maxiter})  # type: ignore
                return res

        class SPSA:  # type: ignore
            def __init__(self, maxiter: int = 100):
                self.maxiter = maxiter

            def minimize(self, fun: Callable[[np.ndarray], float], x0: np.ndarray):
                best_x = np.array(x0, dtype=float)
                best_val = float(fun(best_x))
                for i in range(self.maxiter):
                    step = np.random.uniform(-0.2, 0.2, size=best_x.shape)
                    candidate = best_x + step
                    val = float(fun(candidate))
                    if val < best_val:
                        best_x, best_val = candidate, val
                return type("Result", (), {"x": best_x, "fun": best_val, "nfev": self.maxiter})

if TYPE_CHECKING:
    from .problems import PortfolioProblem, MaxCutProblem


class QAOA:
    """Quantum Approximate Optimization Algorithm implementation.

    # SIMULATION ONLY — uses Qiskit Aer simulator backend.
    """

    def __init__(self, backend_name: str = 'qasm_simulator', shots: int = 1000):
        """
        Initialize QAOA solver.

        Args:
            backend_name: Quantum backend to use
            shots: Number of shots for measurement
        """
        self.backend_name = backend_name
        self.shots = shots
        self.backend = Aer.get_backend(backend_name)

    def create_portfolio_circuit(self, problem: 'PortfolioProblem', p: int = 1,
                                 budget: int = None, risk_aversion: float = 1.0,
                                 penalty: float = None) -> QuantumCircuit:
        """QAOA circuit for binary portfolio selection.

        `budget` is required: it is the number of assets to hold, and without
        it the problem is not the one being solved. The previous version took
        no budget at all, and its cost layer never read `problem.returns` --
        see `_add_cost_hamiltonian` for what it encoded instead.

        The Hamiltonian comes from `portfolio_to_qubo`, so this circuit and
        `solve_portfolio`'s scoring are the same objective by construction.
        """
        if budget is None:
            raise ValueError(
                "budget is required: binary portfolio selection needs the "
                "number of assets to hold, and the budget penalty is part of "
                "the objective the circuit has to encode")

        n_qubits = problem.n_assets

        # No explicit classical register: measure_all() adds its own ("meas").
        # Declaring one here as well produced a circuit with 2n clbits, only n
        # of which were ever written, and a counts key of the form "1000 0000".
        # _bits_from_counts_key strips the space and takes the first n bits of
        # the reversed string -- which was the never-written register. Every
        # outcome decoded to all-zeros. See tests/test_qaoa_oracle.py.
        qc = QuantumCircuit(n_qubits)
        qc.h(range(n_qubits))

        ising = portfolio_to_qubo(problem, budget=budget,
                                  risk_aversion=risk_aversion,
                                  penalty=penalty).to_ising()

        for layer in range(p):
            gamma = Parameter(f'γ_{layer}')
            self._add_cost_hamiltonian(qc, ising, gamma)

            beta = Parameter(f'β_{layer}')
            self._add_mixing_hamiltonian(qc, beta)

        qc.measure_all()

        return qc

    def create_maxcut_circuit(self, problem: 'MaxCutProblem', p: int = 1) -> QuantumCircuit:
        """
        Create QAOA circuit for Max-Cut problem.

        Args:
            problem: Max-Cut problem instance
            p: QAOA depth parameter

        Returns:
            Quantum circuit implementing QAOA
        """
        n_qubits = problem.n_nodes

        # See create_portfolio_circuit: measure_all() supplies the register.
        qc = QuantumCircuit(n_qubits)
        qc.h(range(n_qubits))

        ising = maxcut_to_qubo(problem).to_ising()

        for layer in range(p):
            gamma = Parameter(f'γ_{layer}')
            self._add_cost_hamiltonian(qc, ising, gamma)

            beta = Parameter(f'β_{layer}')
            self._add_mixing_hamiltonian(qc, beta)

        qc.measure_all()

        return qc

    def _add_cost_hamiltonian(self, qc: QuantumCircuit, ising, gamma: Parameter):
        """exp(-i gamma H_C) for H_C = sum h_i Z_i + sum J_ij Z_i Z_j.

        Driven by the Ising form from src/optimization/canonical.py, so the
        circuit and the objective have a single definition and cannot disagree.

        That is not a tidiness argument. The portfolio cost layer was written
        by hand and encoded something else entirely. It read only
        `covariances` and never `returns`, so expected return -- half the
        objective -- was absent from the circuit. It looped over ordered pairs
        `(i, j)` and `(j, i)`, applying every coupling twice. And it emitted a
        bare `rz` carrying the *pair* coefficient before each CX, adding a
        single-qubit term proportional to the covariance row sum that appears
        in no formulation of the problem. There was no budget constraint at
        all. Meanwhile `solve_portfolio` scored its samples by a Sharpe ratio.
        Circuit and scorer optimised different functions and nothing said so.

        Max-Cut is unaffected by the move: its Ising form has h_i = 0 exactly
        -- the linear and quadratic contributions cancel -- and J_ij = w_ij/2,
        so `rz(2 * J * gamma)` is `rz(w * gamma)`, gate for gate what the
        hand-written version emitted. tests/test_qaoa_oracle.py pins that.
        """
        for i, h in ising.h.items():
            qc.rz(2.0 * h * gamma, i)
        for (i, j), coupling in ising.J.items():
            qc.cx(i, j)
            qc.rz(2.0 * coupling * gamma, j)
            qc.cx(i, j)

    def _add_mixing_hamiltonian(self, qc: QuantumCircuit, beta: Parameter):
        """Add mixing Hamiltonian to circuit."""
        n_qubits = qc.num_qubits
        for i in range(n_qubits):
            qc.rx(2 * beta, i)

    def _bits_from_counts_key(self, key: str, num_qubits: int) -> np.ndarray:
        """Decode a counts key. Delegates to the single shared implementation.

        There were two decoders in this repository and only one was correct.
        `src/optimization/objective.py` holds the canonical one so they cannot
        drift; this wrapper exists only to keep the ndarray return type the
        solvers below already expect.
        """
        from .objective import bits_from_counts_key
        return np.asarray(bits_from_counts_key(key, num_qubits), dtype=int)

    def solve_portfolio(self, problem: 'PortfolioProblem', p: int = 1,
                        budget: int = None, risk_aversion: float = 1.0,
                        penalty: float = None, optimizer: str = 'SPSA',
                        max_iter: int = 100) -> Dict:
        """Solve binary portfolio selection with QAOA.

        Both the circuit and the objective being minimised come from the same
        `portfolio_to_qubo`. Previously they did not: the circuit encoded a
        doubled covariance with a spurious linear term and no returns, while
        this method scored samples by -return/risk. Two different functions,
        optimised against each other, reported as one result.
        """
        qubo = portfolio_to_qubo(problem, budget=budget,
                                 risk_aversion=risk_aversion, penalty=penalty)
        qc = self.create_portfolio_circuit(problem, p, budget=budget,
                                           risk_aversion=risk_aversion,
                                           penalty=penalty)
        param_list = list(qc.parameters)

        def _energies(counts):
            for bitstring, count in counts.items():
                bits = self._bits_from_counts_key(bitstring, problem.n_assets)
                yield qubo.energy(bits), count, bits

        def cost_function(params):
            bound_qc = qc.assign_parameters(
                {par: float(val) for par, val in zip(param_list, params)},
                inplace=False)
            counts = self.backend.run(transpile(bound_qc, self.backend),
                                      shots=self.shots).result().get_counts()
            total = sum(counts.values())
            return sum(e * c for e, c, _ in _energies(counts)) / total

        if optimizer == 'SPSA':
            opt = SPSA(maxiter=max_iter)
        elif optimizer == 'COBYLA':
            opt = COBYLA(maxiter=max_iter)
        else:
            raise ValueError(f"Unknown optimizer: {optimizer}")

        initial_params = np.random.uniform(0, 2 * np.pi, 2 * p)
        result = opt.minimize(cost_function, initial_params)

        final_qc = qc.assign_parameters(
            {par: float(val) for par, val in zip(param_list, result.x)},
            inplace=False)
        final_counts = self.backend.run(transpile(final_qc, self.backend),
                                        shots=self.shots).result().get_counts()

        best_energy, _, best_allocation = min(_energies(final_counts),
                                              key=lambda t: t[0])

        return {
            'allocation': best_allocation,
            'selected_assets': [int(i) for i, b in enumerate(best_allocation) if b],
            'objective_energy': float(best_energy),
            'budget': budget,
            'optimal_params': result.x,
            'convergence': result.nfev,
            'circuit': final_qc,
            'counts': final_counts,
        }

    def solve_maxcut(self, problem: 'MaxCutProblem', p: int = 1,
                     optimizer: str = 'SPSA', max_iter: int = 100) -> Dict:
        """
        Solve Max-Cut problem using QAOA.

        Args:
            problem: Max-Cut problem instance
            p: QAOA depth parameter
            optimizer: Optimization algorithm to use
            max_iter: Maximum optimization iterations

        Returns:
            Dictionary with solution and metadata
        """
        qc = self.create_maxcut_circuit(problem, p)
        param_list = list(qc.parameters)

        def cost_function(params):
            bound_qc = qc.assign_parameters({par: float(val) for par, val in zip(param_list, params)}, inplace=False)
            compiled = transpile(bound_qc, self.backend)
            job = self.backend.run(compiled, shots=self.shots)
            result = job.result()
            counts = result.get_counts()

            total_cost = 0
            total_shots = 0

            for bitstring, count in counts.items():
                partition = self._bits_from_counts_key(bitstring, problem.n_nodes)
                cut_value = 0
                for (i, j), weight in zip(problem.edges, problem.weights):
                    if partition[i] != partition[j]:
                        cut_value += weight
                total_cost += cut_value * count
                total_shots += count

            return -total_cost / total_shots

        if optimizer == 'SPSA':
            opt = SPSA(maxiter=max_iter)
        elif optimizer == 'COBYLA':
            opt = COBYLA(maxiter=max_iter)
        else:
            raise ValueError(f"Unknown optimizer: {optimizer}")

        n_params = 2 * p
        initial_params = np.random.uniform(0, 2 * np.pi, n_params)

        result = opt.minimize(cost_function, initial_params)

        final_qc = qc.assign_parameters({par: float(val) for par, val in zip(param_list, result.x)}, inplace=False)
        final_compiled = transpile(final_qc, self.backend)
        final_job = self.backend.run(final_compiled, shots=self.shots)
        final_result = final_job.result()
        final_counts = final_result.get_counts()

        def cut_value_from_bits(bits: np.ndarray) -> float:
            value = 0.0
            for (i, j), weight in zip(problem.edges, problem.weights):
                if bits[i] != bits[j]:
                    value += weight
            return float(value)

        best_partition = None
        best_cut = float("-inf")
        for bitstring, _count in final_counts.items():
            part = self._bits_from_counts_key(bitstring, problem.n_nodes)
            value = cut_value_from_bits(part)
            if value > best_cut:
                best_cut = value
                best_partition = part

        return {
            'partition': best_partition,
            'cut_value': best_cut,
            'optimal_params': result.x,
            'final_cost': -result.fun,
            'convergence': result.nfev,
            'circuit': final_qc,
            'counts': final_counts
        }
